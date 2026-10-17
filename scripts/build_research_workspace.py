"""Build the sourced WebGIS snapshot; --fit reproduces monthly EC backtests.

No download, DB write, EC imputation, salinity conversion or hourly resampling.
Run from repository root: python scripts/build_research_workspace.py --fit
"""
from __future__ import annotations
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RAW = ROOT / 'data/external/ec_recovery_20261011'
OUT = ROOT / 'data/research'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def number(value):
    x = float(value)
    if not math.isfinite(x) or x < 0:
        raise ValueError('EC must be finite and nonnegative.')
    return x


def compile_data():
    manifest = read_json(RAW / 'ec_recovery_manifest.json')
    for entry in manifest['datasets']:
        if digest(RAW / entry['file']) != entry['sha256']:
            raise ValueError('Input hash mismatch: ' + entry['file'])
    stations, observations, sources = [], [], {}
    for source in manifest['sources']:
        sources[source['source_id']] = dict(source, provider='RIA2', reference='Bản tin quan trắc vùng nuôi cá tra', source_id=source['source_id'])
        original = RAW / source['file']
        sources[source['source_id']]['local_original_status'] = (
            'HASH_VERIFIED' if original.is_file() and digest(original) == source['sha256']
            else 'ORIGINAL_NOT_VERIFIED_LOCALLY')
    ria = rows(RAW / 'ec_dongthap_ria2_2025.csv')
    mrc = rows(RAW / 'ec_mrc_rechecked_20261011.csv')
    for code in sorted({r['site_code'] for r in ria}):
        group = [r for r in ria if r['site_code'] == code]
        first = group[0]
        lat, lon = float(first['latitude_source']), float(first['longitude_source'])
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError('Source coordinate out of range.')
        stations.append(dict(site_code=code, site_name=first['site_name_source'], provider='RIA2',
            study_role='Điểm quan trắc trong bản tin Đồng Tháp', admin_label_source=first['admin_label_source'],
            geometry=None, source_coordinates=[lon, lat], coordinate_crs=first['coordinate_crs'],
            location_status=first['location_review_flag'], location_reference='Tọa độ in trong bản tin; chưa xác nhận CRS.',
            time_precision='DATE_ONLY', sampling_label='4 đợt cách nhau 14 ngày',
            hourly_validation_eligible=False, model_status='TOO_FEW_SAMPLES'))
        for r in group:
            value = number(r['conductivity_mS_per_m'])
            if not math.isclose(value, number(r['ec_value_source']) / 10, abs_tol=1e-9):
                raise ValueError('Unit conversion mismatch.')
            date.fromisoformat(r['observed_date'])
            if r['time_precision'] != 'DATE_ONLY' or r['gate_decision_eligible'].lower() != 'false':
                raise ValueError('Unexpected observation eligibility.')
            observations.append(dict(site_code=code, observed_date=r['observed_date'], observed_at=None,
                time_precision='DATE_ONLY', ec_mS_m=value, original_value=number(r['ec_value_source']),
                original_unit=r['ec_unit_source'], unit='mS/m', quality_flag=r['quality_flag'],
                ec_temperature_basis=r['ec_temperature_basis'], water_temperature_degC=float(r['water_temperature_degC']),
                source_id=r['source_id'], source_locator=r['source_locator'], source_sha256=r['source_sha256'],
                gate_decision_eligible=False))
    for code, short, name, role in [('MRC_VN_019805', 'MYTHO', 'Mỹ Tho', 'Trạm lịch sử khu vực Tiền Giang'),
                                    ('MRC_VN_019803', 'TANCHAU', 'Tân Châu', 'Trạm thượng lưu tham chiếu; không đồng nhất với điểm Đồng Tháp')]:
        group = [r for r in mrc if r['site_code'] == code]
        kml = next((ROOT / 'data/raw/gis/spatial').glob('*' + code[-6:] + '*'))
        xml = ET.parse(kml)
        coord = xml.find('.//{http://www.opengis.net/kml/2.2}Point/{http://www.opengis.net/kml/2.2}coordinates')
        lon, lat, *_ = map(float, coord.text.strip().split(','))
        source_id = 'MRC_EC_' + code[-6:]
        first = group[0]
        sources[source_id] = dict(source_id=source_id, provider='MRC', url=first['source_url'],
            sha256=first['source_sha256'], retrieved_at=first['retrieved_at'], reference='Conductivity / Water Quality / ' + name)
        stations.append(dict(site_code=code, model_station=short, site_name=name, provider='MRC', study_role=role,
            admin_label_source=None, geometry=dict(type='Point', coordinates=[lon, lat]), source_coordinates=[lon, lat],
            coordinate_crs='EPSG:4326 (KML)', location_status='REPORTED',
            location_reference=kml.name + '; sha256=' + digest(kml), time_precision='SOURCE_TIMESTAMP',
            sampling_label='Chuỗi mẫu theo tháng; có tháng thiếu', hourly_validation_eligible=False, model_status='HISTORICAL_MONTHLY_BACKTEST'))
        for r in group:
            if r['unit'] != 'mS/m' or r['quality_flag'] != 'UNVERIFIED':
                raise ValueError('Unexpected MRC unit or quality flag.')
            stamp = datetime.fromisoformat(r['observed_at'])
            observations.append(dict(site_code=code, observed_date=str(stamp.date()), observed_at=stamp.isoformat(),
                time_precision='SOURCE_TIMESTAMP', ec_mS_m=number(r['value']), original_value=number(r['value']),
                original_unit='mS/m', unit='mS/m', quality_flag=r['quality_flag'],
                ec_temperature_basis=r['ec_temperature_basis'], water_temperature_degC=None,
                source_id=source_id, source_locator='MRC corrected data timestamp ' + stamp.isoformat(),
                source_sha256=r['source_sha256'], gate_decision_eligible=False))
    supplement = read_json(ROOT / 'data/metadata/ria2_issue12_transcription.json')
    if digest(ROOT / supplement['file']) != supplement['sha256']:
        raise ValueError('Supplemental RIA2 original checksum mismatch.')
    download_manifest = read_json((ROOT / supplement['file']).parent / 'manifest.json')
    original = next(r for r in download_manifest if r.get('sha256') == supplement['sha256'])
    sources[supplement['source_id']] = dict(source_id=supplement['source_id'], provider='RIA2',
        url=supplement['url'], sha256=supplement['sha256'], retrieved_at=original['fetched_at'],
        reference=supplement['reference'], extraction=supplement['extraction'],
        local_original_status='HASH_VERIFIED')
    for code, day, ec, lat, lon, page, row in supplement['rows']:
        site = next(s for s in stations if s['site_code'] == code)
        if site['provider'] != 'RIA2' or site['source_coordinates'] != [lon, lat]:
            raise ValueError('Supplemental station identity requires review.')
        date.fromisoformat(day)
        observations.append(dict(site_code=code, observed_date=day, observed_at=None,
            time_precision='DATE_ONLY', ec_mS_m=number(ec)/10, original_value=number(ec),
            original_unit='µS/cm', unit='mS/m', quality_flag='SOURCE_REPORTED_METHOD_UNVERIFIED',
            ec_temperature_basis='UNKNOWN', water_temperature_degC=28.0,
            source_id=supplement['source_id'], source_locator=f'PDF page {page}, data row {row}; unit page 1',
            source_sha256=supplement['sha256'], gate_decision_eligible=False))
        site['sampling_label'] = '5 đợt lấy mẫu; có khoảng trống giữa các đợt'
    observations.sort(key=lambda r: (r['site_code'], r['observed_date']))
    keys = [(r['site_code'], r['observed_date']) for r in observations]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate site/date; review before aggregation.')
    for site in stations:
        group = [r for r in observations if r['site_code'] == site['site_code']]
        dates = [date.fromisoformat(r['observed_date']) for r in group]
        gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
        site.update(observation_count=len(group), first_observed_date=str(min(dates)), last_observed_date=str(max(dates)),
            latest_ec_mS_m=group[-1]['ec_mS_m'], median_gap_days=statistics.median(gaps) if gaps else None,
            max_gap_days=max(gaps) if gaps else None, unit='mS/m')
    catalog = read_json(ROOT / 'data/metadata/gate_catalog_reviewed.json')
    if digest(ROOT / catalog['source']['file']) != catalog['source']['sha256']:
        raise ValueError('Gate catalog source changed.')
    sources[catalog['source']['source_id']] = catalog['source']
    return stations, observations, list(sources.values()), catalog


def monthly_master(observations):
    """Mean of samples inside each calendar month; not a continuous monthly mean."""
    import pandas as pd
    df = pd.DataFrame([r for r in observations if r['site_code'].startswith('MRC_')])
    df['station'] = df.site_code.map({'MRC_VN_019805': 'MYTHO', 'MRC_VN_019803': 'TANCHAU'})
    df['month_start'] = df.observed_date.str.slice(0, 7) + '-01'
    table = df.groupby(['station', 'month_start'], as_index=False).agg(conductivity_mS_per_m=('ec_mS_m', 'mean'), sample_count=('ec_mS_m', 'count'))
    if not table.sample_count.eq(1).all():
        raise ValueError('Expected one EC sample per month; revise target definition before aggregating multiple samples.')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'mrc_ec_monthly_samples.csv'
    table.to_csv(path, index=False)
    return path


def experiments(registry):
    import pandas as pd
    outputs = []
    for entry in registry:
        path = ROOT / entry['path']
        manifest = read_json(path / 'run_manifest.json')
        if manifest['status'] != 'COMPLETED':
            raise ValueError('Incomplete experiment.')
        for name, expected in manifest['output_sha256'].items():
            if digest(path / name) != expected:
                raise ValueError('Experiment artifact hash mismatch: ' + name)
        predictions = pd.read_csv(path / 'predictions.csv')
        # Convert pandas missing values to JSON null, never NaN.
        records = json.loads(predictions.to_json(orient='records'))
        outputs.append(dict(experiment_id=entry['experiment_id'], station=manifest['config']['station'],
            site_code='MRC_VN_019805' if manifest['config']['station'] == 'MYTHO' else 'MRC_VN_019803',
            availability_lag_days=manifest['config']['availability_lag_days'], unit='mS/m', horizon='1 calendar month',
            selected_model=manifest['selection']['selected_model'], selected_on='validation',
            metrics=manifest['test_common_metrics'], assessment=manifest['test_assessment'],
            high_ec_metrics=manifest.get('high_ec_metrics', []),
            protocol=manifest['protocol'], limitations=manifest['limitations'],
            predictions=records, artifact_path=entry['path'], input_sha256=manifest['input']['sha256'], deployment_ready=False))
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fit', action='store_true')
    args = parser.parse_args()
    stations, observations, sources, catalog = compile_data()
    master = monthly_master(observations)
    registry_path = OUT / 'experiment_registry.json'
    if args.fit:
        from run_monthly_ec import Config, run_experiment
        registry = []
        for station in ['MYTHO', 'TANCHAU']:
            for lag in [0, 30]:
                path = run_experiment(master, ROOT / 'runs/local_ec_backtest', Config(station=station, availability_lag_days=lag))
                registry.append(dict(experiment_id=f'{station}_MONTHLY_LAG{lag}', path=path.relative_to(ROOT).as_posix()))
        write_json(registry_path, registry)
    registry = read_json(registry_path) if registry_path.exists() else []
    bundle = dict(schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
        mode='RESEARCH_SNAPSHOT', unit='mS/m', stations=stations, observations=observations, sources=sources,
        gates=catalog['items'], gate_catalog_scope=catalog['source']['scope'], experiments=experiments(registry),
        live_forecast_available=False, gate_advice_available=False,
        notes=['Dữ liệu quan trắc có nguồn; cờ chất lượng được giữ nguyên.',
            'EC theo tháng phục vụ kiểm chứng hồi cứu; không đánh giá được horizon 2/6/12 giờ.',
            '40 mẫu RIA2 là bản trích kế thừa Step08; xem local_original_status trước khi trích dẫn. Chưa đủ chuỗi để huấn luyện riêng mỗi điểm.',
            'Tọa độ RIA2 chưa rõ CRS; chỉ hiện khi bật lớp tọa độ tham khảo.',
            'Ngưỡng EC theo công trình và mực nước hai phía chưa có trong các nguồn này.'])
    write_json(OUT / 'workspace.json', bundle)
    write_json(OUT / 'workspace_manifest.json', dict(schema_version=1, sha256=digest(OUT / 'workspace.json'),
        file='workspace.json', builder_sha256=digest(__file__), generated_at=bundle['generated_at'],
        observations=len(observations), stations=len(stations), catalog_gates=len(catalog['items']),
        experiments=len(bundle['experiments']), monthly_input_sha256=digest(master)))
    print(json.dumps(dict(snapshot=str(OUT / 'workspace.json'), rows=len(observations), stations=len(stations), experiments=len(registry))))


if __name__ == '__main__':
    main()
