"""Package the verified My Thuan target model and append its sourced observations."""
from __future__ import annotations
import csv
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / 'outputs/mythuan_three_station_20261104'
SOURCE = ROOT / 'data/external/tien_multisite_20261029_verified'
WEATHER = ROOT / 'data/external/mythuan_weather_20261104'
SOURCE_FILE = SOURCE / '019804_Conductivity_Water Quality_4c105414.csv'
VERSION = '20261104T_MYTHUAN_3STATION'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def mythuan_records():
    info = next(r for r in json.loads((SOURCE / 'manifest.json').read_text('utf-8'))['series'] if r['file'] == SOURCE_FILE.name)
    if sha(SOURCE_FILE) != info['extracted_sha256']:
        raise ValueError('My Thuan source checksum mismatch')
    raw = list(csv.DictReader(SOURCE_FILE.open(encoding='utf-8-sig', newline='')))
    if len(raw) != 451 or any(r['unit'] != 'mS/m' or r['quality_flag'] != 'UNVERIFIED' or r['ec_temperature_basis'] != 'UNKNOWN' for r in raw):
        raise ValueError('Unexpected My Thuan source contract')
    sid = 'MRC_EC_019804'
    observations = [dict(site_code='MRC_VN_019804', observed_date=r['observed_at'][:10],
        observed_at=None, source_observed_at=r['observed_at'], time_precision='DATE_ONLY',
        ec_mS_m=float(r['value']), original_value=float(r['value']), original_unit='mS/m', unit='mS/m',
        quality_flag=r['quality_flag'], ec_temperature_basis=r['ec_temperature_basis'], water_temperature_degC=None,
        source_id=sid, source_locator=f'{SOURCE_FILE.relative_to(ROOT).as_posix()}:row {i}',
        source_sha256=sha(SOURCE_FILE), gate_decision_eligible=False) for i, r in enumerate(raw, 2)]
    if len({r['observed_date'][:7] for r in observations}) != 451:
        raise ValueError('Duplicate My Thuan target month')
    dates = [datetime.fromisoformat(r['observed_date']) for r in observations]
    gaps = [(b-a).days for a, b in zip(dates, dates[1:])]
    station = dict(site_code='MRC_VN_019804', model_station='MYTHUAN', site_name='Mỹ Thuận', provider='MRC',
        study_role='Trạm trung lưu sông Tiền; điểm neo thứ ba',
        geometry=dict(type='Point', coordinates=[105.9263229, 10.27532005]),
        source_coordinates=[105.9263229, 10.27532005], coordinate_crs='EPSG:4326 (MRC inventory latitude/longitude)',
        location_status='REPORTED', location_reference='MRC station inventory 019804; source manifest retained',
        time_precision='DATE_ONLY', sampling_label='Một mẫu EC/tháng; giữ các tháng khuyết',
        hourly_validation_eligible=False, model_status='HISTORICAL_MONTHLY_BACKTEST',
        observation_count=451, first_observed_date=observations[0]['observed_date'],
        last_observed_date=observations[-1]['observed_date'], latest_ec_mS_m=observations[-1]['ec_mS_m'],
        median_gap_days=statistics.median(gaps), max_gap_days=max(gaps), unit='mS/m',
        chainage_km=85.217605, axial_ratio=0.68174084, gate_decision_eligible=False)
    source = dict(source_id=sid, provider='MRC', url='https://portal.mrcmekong.org/time-series',
        reference='Conductivity / Water Quality / My Thuan / 019804', sha256=sha(SOURCE_FILE),
        file=SOURCE_FILE.relative_to(ROOT).as_posix(), retrieved_at='2026-10-28T20:37:58.367604+00:00')
    return station, observations, source


def archive_audit_inputs():
    """Keep exact historical inputs when mutable application inputs evolve."""
    manifest = json.loads((AUDIT / 'run_manifest.json').read_text('utf-8'))
    for relative in ('data/research/mrc_ec_monthly_samples.csv', 'scripts/train_multivariate_ec.py', 'scripts/backtest_asof_ec.py'):
        expected = manifest['input_sha256'][relative]
        archive = AUDIT / 'source_snapshots' / relative
        if archive.exists() and sha(archive) == expected:
            continue
        current = ROOT / relative
        raw = current.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raw = subprocess.check_output(['git', 'show', 'HEAD:' + relative], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Cannot preserve original evaluation source: ' + relative)
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(raw)


def integrate_data():
    import pandas as pd
    from backend.domain.workspace import validate_bundle
    station, observations, source = mythuan_records()
    path = ROOT / 'data/research/workspace.json'
    bundle = json.loads(path.read_text('utf-8'))
    bundle['stations'] = [s for s in bundle['stations'] if s['site_code'] != station['site_code']] + [station]
    bundle['observations'] = sorted([r for r in bundle['observations'] if r['site_code'] != station['site_code']] + observations,
                                    key=lambda r: (r['site_code'], r['observed_date']))
    bundle['sources'] = [s for s in bundle['sources'] if s['source_id'] != source['source_id']] + [source]
    bundle['generated_at'] = datetime.now(timezone.utc).isoformat()
    validate_bundle(bundle)
    write(path, bundle)
    target_path = path.with_name('mrc_ec_monthly_samples.csv')
    targets = pd.read_csv(target_path)
    targets = pd.concat([targets[targets.station.ne('MYTHUAN')], pd.DataFrame([
        dict(station='MYTHUAN', month_start=r['observed_date'][:7] + '-01',
             conductivity_mS_per_m=r['ec_mS_m'], sample_count=1,
             quality_flag=r['quality_flag'], ec_temperature_basis=r['ec_temperature_basis']) for r in observations])], ignore_index=True)
    qa = {(s['model_station'], r['observed_date'][:7] + '-01'): r
          for s in bundle['stations'] if s.get('model_station')
          for r in bundle['observations'] if r['site_code'] == s['site_code']}
    for column in ('quality_flag', 'ec_temperature_basis'):
        targets[column] = [qa[(r.station, r.month_start)].get(column, 'UNKNOWN') for r in targets.itertuples()]
    targets.sort_values(['station', 'month_start']).to_csv(target_path, index=False)
    manifest_path = path.with_name('workspace_manifest.json')
    manifest = json.loads(manifest_path.read_text('utf-8'))
    manifest.update(sha256=sha(path), generated_at=bundle['generated_at'], observations=len(bundle['observations']),
        stations=len(bundle['stations']), monthly_input_sha256=sha(target_path),
        integration_builder='scripts/integrate_mythuan.py', integration_builder_sha256=sha(__file__),
        mythuan_source_sha256=sha(SOURCE_FILE))
    write(manifest_path, manifest)


def register_model():
    import joblib
    import numpy as np
    import pandas as pd
    import sklearn
    from backend.domain.multivariate_ec import FEATURES, UNITS
    from scripts.backtest_asof_ec import available_date_for
    model_dir = ROOT / 'runs/multivariate_ec/mythuan' / VERSION
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / 'model.joblib'
    shutil.copyfile(AUDIT / 'mythuan_model.joblib', model_path)
    evaluated = pd.read_csv(AUDIT / 'predictions.csv')
    evaluated = evaluated[evaluated.station.eq('MYTHUAN') & evaluated.ec_delay_days.eq(5)].copy()
    targets = pd.read_csv(AUDIT / 'targets.csv')
    targets = targets[targets.station.eq('MYTHUAN')].set_index('month_start').conductivity_mS_per_m
    evaluated['SeasonalNaive'] = evaluated.target_month.map(lambda m: targets.get((pd.Timestamp(m) - pd.DateOffset(years=1)).strftime('%Y-%m-%d'), np.nan))
    evaluated['actual'] = evaluated.actual_mS_m
    evaluated['split'] = evaluated.split.replace({'historical_2022_2023': 'holdout'})
    evaluated.to_csv(model_dir / 'predictions.csv', index=False)
    evaluation = {}
    for split, group in evaluated.groupby('split'):
        evaluation[split] = {}
        for method in ('RandomForest', 'Persistence', 'SeasonalNaive', 'MonthlyClimatology'):
            error = group[method] - group.actual
            evaluation[split][method] = dict(n=len(group), mae_mS_m=float(error.abs().mean()), rmse_mS_m=float(np.sqrt((error**2).mean())))
    model = joblib.load(model_path)
    weather_manifest = json.loads((WEATHER / 'manifest.json').read_text('utf-8'))
    manifest = dict(schema_version=1, model_version=VERSION, station='MYTHUAN', model='RandomForestRegressor',
        sklearn_version=sklearn.__version__, feature_order=FEATURES, feature_units=UNITS, weather_lag_months=2,
        training_cutoff='2023-12-01', training_months=451, source_sample_count=451,
        target_unit='mS/m', target_quality='UNVERIFIED_SOURCE_QA_NOT_PROMOTED', source_qa_counts={'UNVERIFIED':451},
        model_sha256=sha(model_path), predictions_sha256=sha(model_dir / 'predictions.csv'),
        input_sha256={SOURCE_FILE.relative_to(ROOT).as_posix():sha(SOURCE_FILE)},
        weather_source_sha256={(WEATHER / r['file']).relative_to(ROOT).as_posix():r['sha256'] for r in weather_manifest['retrievals']},
        evaluation=evaluation, evaluation_protocol='Rolling-origin as-of issue day 6 of t-1; EC +5 days, ERA5 t-2 +5 days; retrospective 2022-2023, not a new blind holdout',
        feature_importance=dict(zip(FEATURES, map(float, model[-1].feature_importances_))),
        parameters=dict(n_estimators=300,max_depth=8,min_samples_leaf=3,random_state=42),
        deployment_ready=False, reference_evaluation='outputs/mythuan_three_station_20261104/run_manifest.json')
    write(model_dir / 'manifest.json', manifest)
    registry_path = ROOT / 'data/models/multivariate_registry.json'
    registry = json.loads(registry_path.read_text('utf-8'))
    registry['models']['MYTHUAN'] = dict(model_path=model_path.relative_to(ROOT).as_posix(),
        manifest_path=(model_dir / 'manifest.json').relative_to(ROOT).as_posix(),
        model_sha256=sha(model_path), manifest_sha256=sha(model_dir / 'manifest.json'))
    write(registry_path, registry)


def extend_forecasts():
    from scripts.run_future_forecast_2024_2026 import run_future_forecast
    run_future_forecast()


if __name__ == '__main__':
    archive_audit_inputs()
    integrate_data()
    register_model()
    extend_forecasts()
    print('Integrated MYTHUAN: 451 observations, registered target model, complete three-station forecast months.')
