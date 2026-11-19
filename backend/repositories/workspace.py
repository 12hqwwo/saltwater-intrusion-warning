"""Read-only workspace files and explicit PostgreSQL access."""
from functools import lru_cache
from datetime import date
from statistics import median
import csv
import hashlib
import json
import os
import psycopg
import time
from pathlib import Path
from backend.domain.workspace import validate_bundle
from backend.database import read_connection, STATIONS_SQL
from backend.schemas import LOCAL_TZ

ROOT = Path(__file__).resolve().parents[2]


class WorkspaceUnavailable(ValueError):
    pass


@lru_cache(maxsize=2)
def _file_bundle(path, stamp, manifest_stamp):
    file = Path(path)
    if file.stat().st_size > 8_000_000:
        raise ValueError('Research snapshot exceeds size limit.')
    raw = file.read_bytes()
    manifest = json.loads(
        file.with_name('workspace_manifest.json').read_text(encoding='utf-8-sig')
    )
    if hashlib.sha256(raw).hexdigest() != manifest['sha256']:
        raise ValueError('Research snapshot integrity check failed.')
    return validate_bundle(json.loads(raw))


def load_bundle():
    mode = os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot').lower()
    try:
        if mode not in {'snapshot', 'postgres'}:
            raise ValueError('WEBGIS_RESEARCH_MODE must be snapshot or postgres.')
        path = Path(
            os.getenv('WEBGIS_RESEARCH_FILE', str(ROOT / 'data/research/workspace.json'))
        ).resolve()
        bundle = _file_bundle(
            str(path),
            path.stat().st_mtime_ns,
            path.with_name('workspace_manifest.json').stat().st_mtime_ns,
        )
        if mode == 'postgres':
            return _postgres_cached_bundle(str(path), path.stat().st_mtime_ns,
                                           path.with_name('workspace_manifest.json').stat().st_mtime_ns,
                                           bundle_stamp())
        return dict(bundle, storage_mode='snapshot', observation_source='RESEARCH_SNAPSHOT',
                    dataset_selection='BUNDLED_SNAPSHOT')
    except (OSError, ValueError, KeyError, TypeError, psycopg.Error) as exc:
        raise WorkspaceUnavailable(
            f'Workspace {mode} unavailable; check the configured source and bundle manifest. No fallback was used.'
        ) from exc


def bundle_stamp():
    """Cheap version marker for the sources used by the monthly simulation."""
    mode = os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot').lower()
    path = Path(os.getenv('WEBGIS_RESEARCH_FILE', str(ROOT / 'data/research/workspace.json'))).resolve()
    manifest = path.with_name('workspace_manifest.json')
    files = tuple((str(file), file.stat().st_mtime_ns, file.stat().st_size)
                  for file in (path, manifest))
    if mode == 'snapshot':
        return (mode, files)
    if mode != 'postgres':
        raise ValueError('WEBGIS_RESEARCH_MODE must be snapshot or postgres.')
    return _postgres_stamp_for_bucket(int(time.monotonic() // 30), files,
                                      os.getenv('WEBGIS_WORKSPACE_DATASETS', '{}'))


@lru_cache(maxsize=2)
def _postgres_stamp_for_bucket(bucket, files, selection):
    with read_connection() as conn:
        version = conn.execute('''
            SELECT version FROM public.workspace_cache_version WHERE singleton = true
        ''').fetchone()
    if version is None:
        raise ValueError('Workspace cache version is missing; apply migration 40.')
    return ('postgres', files, selection, version['version'])


@lru_cache(maxsize=2)
def _postgres_cached_bundle(path, stamp, manifest_stamp, version):
    return _postgres_bundle(_file_bundle(path, stamp, manifest_stamp))


def _snapshot_reference_points(bundle, database_site_codes, database_source_codes):
    """Keep RIA2 bulletin points visible without presenting them as DB measurements."""
    stations = [dict(station, observation_source='RESEARCH_SNAPSHOT_RIA2',
                     reference_only=True)
                for station in bundle['stations']
                if station['site_code'].startswith('RIA2_')
                and station['site_code'] not in database_site_codes]
    codes = {station['site_code'] for station in stations}
    observations = [dict(row, observation_source='RESEARCH_SNAPSHOT_RIA2')
                    for row in bundle['observations'] if row['site_code'] in codes]
    source_ids = {row['source_id'] for row in observations}
    sources = [source for source in bundle['sources']
               if source['source_id'] in source_ids
               and source['source_id'] not in database_source_codes]
    if source_ids - database_source_codes - {source['source_id'] for source in sources}:
        raise ValueError('RIA2 reference point source is missing from the snapshot.')
    return stations, observations, sources


def _latest_display_observation(rows):
    return next((row for row in reversed(rows)
                 if row['observed_or_estimated'] == 'O'
                 and row['quality_flag'] in ('VALIDATED', 'UNVERIFIED')), None)


def _postgres_bundle(bundle):
    stations, observations, datasets = [], [], []
    bundle_stations = {station['site_code']: station for station in bundle.get('stations', [])}
    # Keep one immutable dataset per site; never blend overlapping imports.
    wanted = json.loads(os.getenv('WEBGIS_WORKSPACE_DATASETS', '{}'))
    if not isinstance(wanted, dict) or any(not isinstance(v, str) for v in wanted.values()):
        raise ValueError('WEBGIS_WORKSPACE_DATASETS must map site codes to dataset codes.')
    with read_connection() as conn:
        site_rows = conn.execute(STATIONS_SQL).fetchall()
        if set(wanted) - {s['site_code'] for s in site_rows}:
            raise ValueError('Configured dataset selection references an unknown station.')
        site_ids = {row['site_code']: row['site_id'] for row in conn.execute('''
            SELECT site_code, site_id FROM public.measurement_site
            WHERE site_code = ANY(%s)''', ([site['site_code'] for site in site_rows],)).fetchall()}
        sources = conn.execute('''SELECT source_code AS source_id, source_code,
            source_name, source_type, reference FROM public.data_source
            WHERE NOT is_demo ORDER BY source_code''').fetchall()
        for source in sources:
            source.update(provider=source['source_code'],
                url=source['reference'] if source['reference'].startswith('https://') else None)
        available_by_site = {site_id: [] for site_id in site_ids.values()}
        if site_ids:
            for dataset in conn.execute('''SELECT sites.site_id, d.dataset_id, d.dataset_code,
                d.sha256, d.source_filename, d.imported_at, src.source_code,
                d.metadata->>'time_precision' AS time_precision
                FROM unnest(%s::bigint[]) AS sites(site_id)
                CROSS JOIN public.source_dataset d
                JOIN public.data_source src ON src.source_id=d.source_id
                WHERE d.dataset_kind='RAW_EC'
                  AND NOT d.is_demo AND NOT src.is_demo
                  AND EXISTS (SELECT 1 FROM public.conductivity_observation o
                              WHERE o.site_id=sites.site_id AND o.dataset_id=d.dataset_id)
                ORDER BY d.imported_at DESC,d.dataset_code''',
                (list(site_ids.values()),)).fetchall():
                available_by_site[dataset['site_id']].append(dataset)
        selected_by_site = {}
        for site in site_rows:
            available = available_by_site[site_ids[site['site_code']]]
            selected = next((d for d in available if d['dataset_code'] == wanted[site['site_code']]), None) if site['site_code'] in wanted else next(iter(available), None)
            if site['site_code'] in wanted and selected is None:
                raise ValueError('Configured RAW_EC dataset is unavailable for this station.')
            selected_by_site[site['site_code']] = selected
        rows_by_pair = {}
        pairs = {(site_ids[code], dataset['dataset_id']) for code, dataset in selected_by_site.items() if dataset}
        if pairs:
            for row in conn.execute('''SELECT o.site_id,o.dataset_id,o.ec_observation_id,o.source_row,o.observed_at,
                conductivity_ms_per_m,unit,observed_or_estimated,quality_flag,
                approval_level,grade,source_label FROM public.conductivity_observation o
                JOIN unnest(%s::bigint[], %s::bigint[]) AS selected(site_id,dataset_id)
                  ON selected.site_id = o.site_id AND selected.dataset_id = o.dataset_id
                ORDER BY o.site_id,o.observed_at,o.ec_observation_id''',
                ([pair[0] for pair in sorted(pairs)], [pair[1] for pair in sorted(pairs)])).fetchall():
                pair = (row['site_id'], row['dataset_id'])
                if pair in pairs:
                    rows_by_pair.setdefault(pair, []).append(row)
        for site in site_rows:
            fallback = bundle_stations.get(site['site_code'], {})
            site_id = site_ids[site['site_code']]
            available = available_by_site[site_id]
            selected = selected_by_site[site['site_code']]
            rows = rows_by_pair.get((site_id, selected['dataset_id']), []) if selected else []
            if selected:
                datasets.append(dict({key: value for key, value in selected.items()
                                      if key not in {'site_id', 'time_precision'}},
                    site_code=site['site_code'], selected=True,
                    observation_count=len(rows),
                    first_observation=rows[0]['observed_at'] if rows else None,
                    last_observation=rows[-1]['observed_at'] if rows else None,
                    observed_rows=sum(row['observed_or_estimated'] == 'O' for row in rows),
                    estimated_rows=sum(row['observed_or_estimated'] == 'E' for row in rows),
                    unverified_rows=sum(row['quality_flag'] == 'UNVERIFIED' for row in rows),
                    validated_rows=sum(row['quality_flag'] == 'VALIDATED' for row in rows),
                    suspect_rows=sum(row['quality_flag'] == 'SUSPECT' for row in rows),
                    invalid_rows=sum(row['quality_flag'] == 'INVALID' for row in rows)))
            precision = selected['time_precision'] if selected else None
            date_only = precision == 'DATE_ONLY'
            station_rows = []
            for row in rows:
                local_time = row['observed_at'].astimezone(LOCAL_TZ)
                station_rows.append(dict({key: value for key, value in row.items() if key != 'site_id'}, site_code=site['site_code'],
                    observed_at=None if date_only else local_time.isoformat(), observed_date=local_time.date().isoformat(),
                    time_precision='DATE_ONLY' if date_only else 'SOURCE_TIMESTAMP', ec_mS_m=float(row['conductivity_ms_per_m']),
                    source_id=site['source_code'], source_sha256=selected['sha256'],
                    dataset_code=selected['dataset_code'], dataset_id=selected['dataset_id'],
                    source_locator=f"{selected['source_filename']}:row {row['source_row']}",
                    ec_temperature_basis='UNKNOWN', water_temperature_degC=None,
                    gate_decision_eligible=False))
            observations.extend(station_rows)
            dates = [date.fromisoformat(row['observed_date']) for row in station_rows]
            gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
            latest_observed = _latest_display_observation(station_rows)
            stations.append(dict(site, provider=site['source_code'], unit='mS/m',
                observation_source='POSTGRESQL_PUBLIC_RAW_EC', reference_only=False,
                model_station=fallback.get('model_station'), chainage_km=fallback.get('chainage_km'),
                axial_ratio=fallback.get('axial_ratio'),
                # Reference coordinates remain separate from verified DB geometry.
                source_coordinates=site.get('source_coordinates') or fallback.get('source_coordinates'),
                admin_label_source=site.get('admin_label_source') or fallback.get('admin_label_source'),
                coordinate_crs=site.get('coordinate_crs') or fallback.get('coordinate_crs'),
                location_reference=site.get('location_reference') or fallback.get('location_reference'),
                study_role='Quan trắc EC lịch sử; chưa đủ căn cứ vận hành cống',
                sampling_label='Mẫu EC nguồn PostgreSQL; giữ cờ O/E, không nội suy',
                max_gap_days=max(gaps, default=0), median_gap_days=median(gaps) if gaps else 0,
                observation_count=len(rows), first_observed_date=station_rows[0]['observed_date'] if rows else None,
                last_observed_date=latest_observed['observed_date'] if latest_observed else None,
                latest_ec_mS_m=latest_observed['ec_mS_m'] if latest_observed else None,
                latest_ec_quality_flag=latest_observed['quality_flag'] if latest_observed else None,
                selected_dataset_code=selected['dataset_code'] if selected else None,
                available_dataset_codes=[d['dataset_code'] for d in available],
                model_status='HISTORICAL_DATA_ONLY', hourly_validation_eligible=False,
                gate_decision_eligible=False, time_precision='DATE_ONLY' if date_only else 'SOURCE_TIMESTAMP'))
    reference_stations, reference_observations, reference_sources = _snapshot_reference_points(
        bundle, {station['site_code'] for station in stations},
        {source['source_id'] for source in sources})
    stations.extend(reference_stations)
    observations.extend(reference_observations)
    sources.extend(reference_sources)
    return dict(bundle, stations=stations, observations=observations,
        sources=sources, artifact_sources=bundle['sources'], datasets=datasets,
        storage_mode='postgres', observation_source=(
            'POSTGRESQL_RAW_EC_AND_RIA2_SNAPSHOT_REFERENCES' if reference_stations
            else 'POSTGRESQL_PUBLIC_RAW_EC'),
        artifact_source='RESEARCH_SNAPSHOT',
        dataset_selection='EXPLICIT_PER_SITE_OR_LATEST_IMPORTED_RAW_EC',
        notes=list(bundle['notes']) + [
            'PostgreSQL public RAW_EC observations; latest import per site unless WEBGIS_WORKSPACE_DATASETS pins a dataset. Historical EC is not operational gate evidence.',
            'RIA2 points not imported into PostgreSQL are shown from the hash-verified project snapshot as reference points; their coordinates have unconfirmed CRS.'
        ])


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding='utf-8-sig'))


def estimate_rows():
    path = ROOT / 'data/models/future_ec_forecast_2024_2026.csv'
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def database_gates():
    # Explicit endpoint: the UI invokes it only when the user selects PostgreSQL.
    with read_connection() as conn:
        result = conn.execute(
            '''SELECT g.gate_code, g.gate_name, g.waterway_name, g.is_active,
            ST_AsGeoJSON(g.geom)::jsonb AS geometry, s.source_code, s.reference AS source_reference
            FROM public.irrigation_gate g JOIN public.data_source s USING(source_id)
            WHERE NOT g.is_demo AND NOT s.is_demo ORDER BY g.gate_code'''
        ).fetchall()
    return dict(
        items=result,
        source='POSTGRESQL',
        note='is_active là trạng thái danh mục, không phải trạng thái mở/đóng.',
    )


def candidate_stations(gate_code: str, radius_km: float = 50):
    with read_connection() as conn:
        gate = conn.execute(
            '''SELECT g.gate_id, ST_AsGeoJSON(g.geom)::jsonb AS geometry
            FROM public.irrigation_gate g JOIN public.data_source src USING(source_id)
            WHERE g.gate_code=%s AND NOT g.is_demo AND NOT src.is_demo''',
            (gate_code,),
        ).fetchone()
        if not gate:
            raise LookupError('Gate not found in PostgreSQL.')
        items = conn.execute(
            '''SELECT s.site_code,s.site_name,s.location_status,
            ST_AsGeoJSON(s.geom)::jsonb AS geometry,
            ST_Distance(s.geom::geography,g.geom::geography) AS distance_m,
            s.location_reference
            FROM public.measurement_site s CROSS JOIN public.irrigation_gate g
            JOIN public.data_source src ON src.source_id=s.source_id
            WHERE g.gate_id=%s AND NOT s.is_demo AND NOT src.is_demo AND s.geom IS NOT NULL
              AND ST_DWithin(s.geom::geography,g.geom::geography,%s)
            ORDER BY distance_m,s.site_code LIMIT 5''',
            (gate['gate_id'], radius_km * 1000),
        ).fetchall()
    return dict(
        gate_code=gate_code,
        gate_geometry=gate['geometry'],
        radius_km=radius_km,
        items=items,
        hydrological_link_validated=False,
        method='ST_DWithin and ST_Distance on geography; metres',
        note=(
            'Khoảng cách chỉ sàng lọc trạm ứng viên. Cần kiểm chứng cùng nhánh sông, '
            'truyền triều/mặn và sai khác thực đo trước khi đại diện cho cống.'
        ),
    )

