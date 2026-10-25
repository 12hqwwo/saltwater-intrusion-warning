"""Persisted monthly EC regression using weather from two calendar months earlier."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
WEATHER_AGG = {
    'rainfall_mm': 'sum', 'temperature_degC': 'mean', 'wind_source_units': 'mean',
}
FEATURES = list(WEATHER_AGG) + ['month_sin', 'month_cos']
UNITS = dict(zip(WEATHER_AGG, ['mm', 'degC', 'm/s'])) | {'month_sin': '1', 'month_cos': '1'}
STATIONS = {'MYTHO': ('MyTho', 'MRC_VN_019805', 'Mỹ Tho'),
            'TANCHAU': ('TanChau', 'MRC_VN_019803', 'Tân Châu')}
LABELS = {'rainfall_mm': 'Lượng mưa tháng', 'temperature_degC': 'Nhiệt độ trung bình tháng',
          'wind_source_units': 'Tốc độ gió trung bình tháng',
          'month_sin': 'Chu kỳ tháng (sin)', 'month_cos': 'Chu kỳ tháng (cos)'}


def normalize_station(station):
    key = station.upper().replace(' ', '').replace('_', '')
    aliases = {'MRCVN019805': 'MYTHO', 'MRCVN019803': 'TANCHAU'}
    key = aliases.get(key, key)
    if key not in STATIONS:
        raise ValueError('Unknown model station.')
    return key


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def monthly_weather(frame):
    import pandas as pd
    frame = frame.copy()
    frame['station'] = frame['station'].str.upper()
    frame['date'] = pd.to_datetime(frame['date'])
    if frame.duplicated(['station', 'date']).any():
        raise ValueError('Duplicate weather station/day.')
    frame['weather_month'] = frame['date'].dt.to_period('M').dt.to_timestamp()
    grouped = frame.groupby(['station', 'weather_month'])
    result = grouped.agg(WEATHER_AGG)
    counts = grouped[list(WEATHER_AGG)].count()
    days = result.index.get_level_values('weather_month').days_in_month
    # Incomplete months must not masquerade as complete precipitation totals.
    for column in WEATHER_AGG:
        result.loc[counts[column].to_numpy() != days, column] = float('nan')
    return result.reset_index()


def load_model(station, registry_path=None):
    import joblib
    import sklearn
    station = normalize_station(station)
    registry = json.loads(Path(registry_path or ROOT / 'data/models/multivariate_registry.json').read_text())
    entry = registry['models'][station]
    model_path, manifest_path = ROOT / entry['model_path'], ROOT / entry['manifest_path']
    if sha256(manifest_path) != entry['manifest_sha256'] or sha256(model_path) != entry['model_sha256']:
        raise ValueError('Model artifact checksum mismatch.')
    manifest = json.loads(manifest_path.read_text())
    if manifest['sklearn_version'] != sklearn.__version__:
        raise ValueError('Model requires scikit-learn ' + manifest['sklearn_version'])
    if manifest['feature_order'] != FEATURES or manifest['station'] != station:
        raise ValueError('Model feature/station contract mismatch.')
    return joblib.load(model_path), manifest


def model_catalog(registry_path=None):
    registry = json.loads(Path(registry_path or ROOT / 'data/models/multivariate_registry.json').read_text())
    items = []
    for station, entry in registry['models'].items():
        path = ROOT / entry['manifest_path']
        if sha256(path) != entry['manifest_sha256']:
            raise ValueError('Model manifest checksum mismatch.')
        manifest = json.loads(path.read_text())
        name, site_code, site_name = STATIONS[station]
        items.append(dict(station=name, site_code=site_code, site_name=site_name,
            model=manifest['model'], model_version=manifest['model_version'],
            trained_through=manifest['training_cutoff'], training_samples=manifest['training_months'],
            metrics=manifest['evaluation']['holdout']['RandomForest'],
            evaluation=manifest['evaluation'], deployment_ready=False,
            features=[dict(name=k, label=LABELS[k], unit=UNITS[k]) for k in FEATURES],
            feature_importance=[dict(name=k, label=LABELS[k], importance=v)
                for k, v in manifest['feature_importance'].items()]))
    return items


def evaluation_records(station, registry_path=None):
    import pandas as pd
    station = normalize_station(station)
    registry = json.loads(Path(registry_path or ROOT / 'data/models/multivariate_registry.json').read_text())
    entry = registry['models'][station]
    manifest_path = ROOT / entry['manifest_path']
    if sha256(manifest_path) != entry['manifest_sha256']:
        raise ValueError('Model manifest checksum mismatch.')
    manifest = json.loads(manifest_path.read_text())
    path = manifest_path.with_name('predictions.csv')
    if sha256(path) != manifest['predictions_sha256']:
        raise ValueError('Evaluation prediction checksum mismatch.')
    frame = pd.read_csv(path)
    columns = ['actual', 'RandomForest', 'Persistence', 'SeasonalNaive', 'MonthlyClimatology']
    selected = frame.loc[frame['split'] == 'holdout'].copy()
    selected = selected[selected[columns].apply(lambda column: column.map(
        lambda value: isinstance(value, (int, float)) and math.isfinite(value))).all(axis=1)]
    selected = selected.sort_values('target_month')
    metrics = manifest['evaluation']['holdout']
    if (selected.empty or selected['target_month'].duplicated().any()
            or not selected['station'].eq(station).all()
            or not selected['target_month'].between('2022-01-01', '2023-12-31').all()
            or any(len(selected) != metrics[key]['n'] for key in columns[1:])):
        raise ValueError('Evaluation cohort does not match reported metrics.')
    name, site_code, _ = STATIONS[station]
    return dict(items=selected[['target_month'] + columns].to_dict('records'),
        metrics=metrics, station=name, site_code=site_code,
        model_version=manifest['model_version'], unit='mS/m', period='2022-01..2023-12')


def predict_month(station, target_month, weather_features, registry_path=None):
    import pandas as pd
    target = pd.Timestamp(target_month)
    if target.day != 1 or target.tzinfo is not None:
        raise ValueError('target_month must be a timezone-free calendar month start.')
    values = {}
    for key in WEATHER_AGG:
        value = weather_features[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Weather inputs must be finite numeric monthly aggregates: ' + key)
        values[key] = float(value)
    values.update(month_sin=math.sin(2 * math.pi * target.month / 12),
                  month_cos=math.cos(2 * math.pi * target.month / 12))
    model, manifest = load_model(station, registry_path)
    prediction = float(model.predict(pd.DataFrame([values], columns=FEATURES))[0])
    if not math.isfinite(prediction) or prediction < 0:
        raise ValueError('Model produced invalid EC.')
    return dict(station=STATIONS[normalize_station(station)][0], target_month=target.date().isoformat(),
        weather_month=(target - pd.DateOffset(months=2)).date().isoformat(),
        predicted_ec_mS_m=prediction, unit='mS/m', model='RandomForestRegressor',
        model_version=manifest['model_version'], feature_values=values,
        feature_units=UNITS, training_cutoff=manifest['training_cutoff'],
        quality_status='EXPERIMENTAL_SOURCE_EC_UNVERIFIED',
        deployment_ready=False, gate_decision_eligible=False,
        data_kind='MULTIVARIATE_MONTHLY_EC_PREDICTION',
        validation_metrics=manifest['evaluation'],
        availability_assumption='Complete weather from target minus two months; archive release latency not independently verified.')
