"""Read-only workspace files and explicit PostgreSQL access."""
from functools import lru_cache
from datetime import date
from statistics import median
import csv
import hashlib
import json
import os
import psycopg
from pathlib import Path
from backend.domain.workspace import validate_bundle
from backend.database import read_connection, STATIONS_SQL, DATASETS_SELECT, DATASETS_GROUP
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
            return _postgres_bundle(bundle)
        return dict(bundle, storage_mode='snapshot', observation_source='RESEARCH_SNAPSHOT',
                    dataset_selection='BUNDLED_SNAPSHOT')
    except (OSError, ValueError, KeyError, TypeError, psycopg.Error) as exc:
        raise WorkspaceUnavailable(
            f'Workspace {mode} unavailable; check the configured source and bundle manifest. No fallback was used.'
        ) from exc


def _postgres_bundle(bundle):
    stations, observations, datasets = [], [], []
    # Keep one immutable dataset per site; never blend overlapping imports.
    wanted = json.loads(os.getenv('WEBGIS_WORKSPACE_DATASETS', '{}'))
    if not isinstance(wanted, dict) or any(not isinstance(v, str) for v in wanted.values()):
        raise ValueError('WEBGIS_WORKSPACE_DATASETS must map site codes to dataset codes.')
    with read_connection() as conn:
        site_rows = conn.execute(STATIONS_SQL).fetchall()
        if set(wanted) - {s['site_code'] for s in site_rows}:
            raise ValueError('Configured dataset selection references an unknown station.')
        sources = conn.execute('''SELECT source_code AS source_id, source_code,
            source_name, source_type, reference FROM public.data_source
            WHERE NOT is_demo ORDER BY source_code''').fetchall()
        for source in sources:
            source.update(provider=source['source_code'],
                url=source['reference'] if source['reference'].startswith('https://') else None)
        for site in site_rows:
            site_id = conn.execute('SELECT site_id FROM public.measurement_site WHERE site_code=%s',
                                   (site['site_code'],)).fetchone()['site_id']
            available = conn.execute(DATASETS_SELECT + DATASETS_GROUP, (site_id,)).fetchall()
            selected = next((d for d in available if d['dataset_code'] == wanted[site['site_code']]), None) if site['site_code'] in wanted else next(iter(available), None)
            if site['site_code'] in wanted and selected is None:
                raise ValueError('Configured RAW_EC dataset is unavailable for this station.')
            for dataset in available:
                datasets.append(dict(dataset, site_code=site['site_code'], selected=dataset is selected))
            rows = conn.execute('''SELECT ec_observation_id, source_row, observed_at,
                conductivity_ms_per_m, unit, observed_or_estimated, quality_flag,
                approval_level, grade, source_label FROM public.conductivity_observation
                WHERE site_id=%s AND dataset_id=%s ORDER BY observed_at, ec_observation_id''',
                (site_id, selected['dataset_id'])).fetchall() if selected else []
            precision = conn.execute(
                "SELECT metadata->>'time_precision' AS time_precision FROM public.source_dataset WHERE dataset_id=%s",
                (selected['dataset_id'],),
            ).fetchone()['time_precision'] if selected else None
            date_only = precision == 'DATE_ONLY'
            station_rows = []
            for row in rows:
                local_time = row['observed_at'].astimezone(LOCAL_TZ)
                station_rows.append(dict(row, site_code=site['site_code'],
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
            stations.append(dict(site, provider=site['source_code'], unit='mS/m',
                study_role='Quan trắc EC lịch sử; chưa đủ căn cứ vận hành cống',
                sampling_label='Quan trắc nguồn PostgreSQL; không nội suy',
                max_gap_days=max(gaps, default=0), median_gap_days=median(gaps) if gaps else 0,
                observation_count=len(rows), first_observed_date=station_rows[0]['observed_date'] if rows else None,
                last_observed_date=station_rows[-1]['observed_date'] if rows else None,
                latest_ec_mS_m=station_rows[-1]['ec_mS_m'] if rows else None,
                selected_dataset_code=selected['dataset_code'] if selected else None,
                available_dataset_codes=[d['dataset_code'] for d in available],
                model_status='HISTORICAL_DATA_ONLY', hourly_validation_eligible=False,
                gate_decision_eligible=False, time_precision='DATE_ONLY' if date_only else 'SOURCE_TIMESTAMP'))
    return dict(bundle, stations=stations, observations=observations,
        sources=sources, artifact_sources=bundle['sources'], datasets=datasets,
        storage_mode='postgres', observation_source='POSTGRESQL_PUBLIC_RAW_EC',
        artifact_source='RESEARCH_SNAPSHOT',
        dataset_selection='EXPLICIT_PER_SITE_OR_LATEST_IMPORTED_RAW_EC',
        notes=list(bundle['notes']) + ['PostgreSQL public RAW_EC observations; latest import per site unless WEBGIS_WORKSPACE_DATASETS pins a dataset. Historical EC is not operational gate evidence.'])


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

