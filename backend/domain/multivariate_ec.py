"""Persisted monthly EC regression using weather from two calendar months earlier."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import hashlib
import json
import math
from backend.repositories import hydrology_inputs

ROOT = Path(__file__).resolve().parents[2]
WEATHER_AGG = {
    'rainfall_mm': 'sum', 'temperature_degC': 'mean', 'wind_source_units': 'mean',
}
FEATURES = list(WEATHER_AGG) + ['month_sin', 'month_cos']
HYDRO_FEATURES = hydrology_inputs.FEATURES
UNITS = (dict(zip(WEATHER_AGG, ['mm', 'degC', 'm/s'])) |
         {'month_sin': '1', 'month_cos': '1'} | hydrology_inputs.UNITS)
STATIONS = {'MYTHO': ('MyTho', 'MRC_VN_019805', 'Mỹ Tho'),
            'MYTHUAN': ('MyThuan', 'MRC_VN_019804', 'Mỹ Thuận'),
            'TANCHAU': ('TanChau', 'MRC_VN_019803', 'Tân Châu')}
LABELS = {'rainfall_mm': 'Lượng mưa tháng', 'temperature_degC': 'Nhiệt độ trung bình tháng',
          'wind_source_units': 'Tốc độ gió trung bình tháng',
          'month_sin': 'Chu kỳ tháng (sin)', 'month_cos': 'Chu kỳ tháng (cos)'} | hydrology_inputs.LABELS


def normalize_station(station):
    key = station.upper().replace(' ', '').replace('_', '')
    aliases = {'MRCVN019805': 'MYTHO', 'MRCVN019803': 'TANCHAU', 'MRCVN019804': 'MYTHUAN'}
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


@lru_cache(maxsize=8)
def _load_cached_artifact(model_path, model_sha, manifest_raw):
    import joblib
    import sklearn
    manifest = json.loads(manifest_raw)
    if manifest['sklearn_version'] != sklearn.__version__:
        raise ValueError('Model requires scikit-learn ' + manifest['sklearn_version'])
    # Deserialize exactly the bytes that were verified (also avoids a check/load race).
    raw = Path(model_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != model_sha:
        raise ValueError('Model artifact checksum mismatch.')
    model = joblib.load(BytesIO(raw))
    forest = model.steps[-1][1] if hasattr(model, 'steps') else model
    if hasattr(forest, 'n_jobs'):
        forest.n_jobs = 1
    return model, manifest


def load_model(station, registry_path=None):
    station = normalize_station(station)
    registry = json.loads(Path(registry_path or ROOT / 'data/models/multivariate_registry.json').read_text())
    entry = registry['models'][station]
    model_path, manifest_path = ROOT / entry['model_path'], ROOT / entry['manifest_path']
    manifest_raw = manifest_path.read_bytes()
    # Verify on every access, including cache hits: changed/tampered files cannot
    # silently reuse a previously trusted model. Cache only expensive deserialization.
    if (hashlib.sha256(manifest_raw).hexdigest() != entry['manifest_sha256']
            or sha256(model_path) != entry['model_sha256']):
        raise ValueError('Model artifact checksum mismatch.')
    manifest = json.loads(manifest_raw)
    if manifest.get('model_sha256', entry['model_sha256']) != entry['model_sha256']:
        raise ValueError('Model manifest artifact identity mismatch.')
    allowed_orders = [FEATURES, FEATURES + HYDRO_FEATURES] if station == 'MYTHO' else [FEATURES]
    if manifest['feature_order'] not in allowed_orders or manifest['station'] != station:
        raise ValueError('Model feature/station contract mismatch.')
    return _load_cached_artifact(str(model_path.resolve()), entry['model_sha256'], manifest_raw)


def warmup_models():
    """Load registered artifacts only; no weather, database access, or training."""
    failures = {}
    for station in STATIONS:
        try:
            load_model(station)
        except Exception as exc:
            # Optional model failures must not prevent historical API startup.
            failures[station] = type(exc).__name__
    return failures


def ensemble_distribution(model, features):
    """Uncalibrated tree dispersion, not a forecast uncertainty guarantee."""
    import numpy as np
    forest = model.steps[-1][1] if hasattr(model, 'steps') else model
    transformed = model[:-1].transform(features) if hasattr(model, 'steps') and len(model.steps) > 1 else features
    predictions = np.asarray([tree.predict(transformed)[0] for tree in forest.estimators_], dtype=float)
    if not len(predictions) or not np.isfinite(predictions).all() or (predictions < 0).any():
        raise ValueError('Model produced invalid tree EC.')
    quantiles = np.quantile(predictions, [.1, .25, .5, .75, .9])
    return dict(zip(['p10', 'p25', 'p50', 'p75', 'p90'], map(float, quantiles)),
        iqr=float(quantiles[3] - quantiles[1]), std=float(predictions.std()),
        n_estimators=len(predictions), unit='mS/m', method='RANDOM_FOREST_TREE_PREDICTIONS',
        interpretation='Dispersion of individual tree predictions; not a calibrated prediction or confidence interval. Does not include all forecast error.')


def model_catalog(registry_path=None):
    from backend.domain import ec_gap_evaluation
    registry = json.loads(Path(registry_path or ROOT / 'data/models/multivariate_registry.json').read_text())
    items = []
    for station, entry in registry['models'].items():
        path = ROOT / entry['manifest_path']
        if sha256(path) != entry['manifest_sha256']:
            raise ValueError('Model manifest checksum mismatch.')
        manifest = json.loads(path.read_text())
        name, site_code, site_name = STATIONS[station]
        gap_validation = manifest.get('gap_validation')
        if gap_validation is None and registry_path is None and ec_gap_evaluation.INDEX.exists():
            gap_validation = ec_gap_evaluation.summary(station)
        items.append(dict(station=name, site_code=site_code, site_name=site_name,
            model=manifest['model'], model_version=manifest['model_version'],
            trained_through=manifest['training_cutoff'], training_samples=manifest['training_months'],
            metrics=manifest['evaluation']['holdout']['RandomForest'],
            evaluation=manifest['evaluation'], gap_validation=gap_validation,
            historical_evaluation_protocol=manifest.get('evaluation_protocol'), deployment_ready=False,
            features=[dict(name=k, label=LABELS[k], unit=UNITS[k]) for k in manifest['feature_order']],
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
    primary_hydrology = manifest.get('evaluation_protocol_id') == 'FROZEN_EC_HYDROLOGY_PRIMARY_V1'
    columns = (['actual', 'RandomForest', 'FrozenPersistence', 'MonthlyClimatology', 'FrozenSeasonalRepeat']
               if primary_hydrology else
               ['actual', 'RandomForest', 'Persistence', 'SeasonalNaive', 'MonthlyClimatology'])
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
        protocol_id='HISTORICAL', evaluation_protocol=manifest.get('evaluation_protocol'),
        model_version=manifest['model_version'], unit='mS/m', period='2022-01..2023-12',
        evaluation_protocol_id=manifest.get('evaluation_protocol_id'))


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
    if manifest['feature_order'] == FEATURES + HYDRO_FEATURES:
        for key in HYDRO_FEATURES:
            value = weather_features.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Hydrology inputs must be finite monthly values: ' + key)
            values[key] = float(value)
    features = pd.DataFrame([values], columns=manifest['feature_order'])
    prediction = float(model.predict(features)[0])
    distribution = ensemble_distribution(model, features)
    if not math.isfinite(prediction) or prediction < 0:
        raise ValueError('Model produced invalid EC.')
    return dict(station=STATIONS[normalize_station(station)][0], target_month=target.date().isoformat(),
        weather_month=(target - pd.DateOffset(months=2)).date().isoformat(),
        predicted_ec_mS_m=prediction, ensemble_distribution=distribution, unit='mS/m', model='RandomForestRegressor',
        model_version=manifest['model_version'],
        model_provenance=dict(model_sha256=manifest.get('model_sha256'),
            training_input_sha256=manifest.get('input_sha256', {}),
            weather_source_sha256=manifest.get('weather_source_sha256', {})),
        feature_values=values,
        feature_units=UNITS, training_cutoff=manifest['training_cutoff'],
        quality_status='EXPERIMENTAL_SOURCE_EC_UNVERIFIED',
        deployment_ready=False, gate_decision_eligible=False,
        data_kind='MULTIVARIATE_MONTHLY_EC_PREDICTION',
        validation_metrics=manifest['evaluation'],
        availability_assumption=('Complete weather and hydrology from target minus two months; '
            'their historical publication latency is assumed, not independently verified.'
            if manifest['feature_order'] == FEATURES + HYDRO_FEATURES else
            'Complete weather from target minus two months; archive release latency not independently verified.'))
