"""Offline chronological evaluation and final fit; never train in the API."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import sklearn
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error
from backend.domain.multivariate_ec import FEATURES, UNITS, sha256
from backend.repositories.multivariate_inputs import get_monthly_weather


def pipeline():
    return make_pipeline(SimpleImputer(strategy='median'), RandomForestRegressor(
        n_estimators=300, max_depth=8, min_samples_leaf=3, random_state=42, n_jobs=-1))


def training_frame(target_path, weather_path):
    targets = pd.read_csv(target_path, parse_dates=['month_start'])
    if targets.duplicated(['station', 'month_start']).any():
        raise ValueError('Duplicate target month.')
    provenance = json.loads(weather_path.read_text(encoding='utf-8'))
    # The shared adapter validates every source and selects whole monthly versions.
    # Repeated archive refreshes can overlap historical chunks without splicing days.
    weather_rows = [row for station in sorted(targets['station'].unique())
        for row in get_monthly_weather(station, require_verified_wind=True)]
    weather = pd.DataFrame(weather_rows)
    if weather.empty:
        raise ValueError('No verified monthly weather available.')
    weather['station'] = weather['station'].str.upper()
    weather['weather_month'] = pd.to_datetime(weather['input_month'])
    weather = weather[['station', 'weather_month'] + list(UNITS)[:3]]
    weather_hashes = {}
    for source in provenance['retrievals']:
        path = weather_path.parent / source['file']
        weather_hashes[str(path.relative_to(ROOT)).replace('\\', '/')] = source['sha256']
    targets['weather_month'] = targets['month_start'] - pd.DateOffset(months=2)
    frame = targets.merge(weather, on=['station', 'weather_month'], how='left', validate='many_to_one')
    if frame[list(UNITS)[:3]].isna().any().any():
        raise ValueError('Training requires complete source weather coverage for every target t-2 month.')
    frame['month_sin'] = np.sin(2 * np.pi * frame.month_start.dt.month / 12)
    frame['month_cos'] = np.cos(2 * np.pi * frame.month_start.dt.month / 12)
    return frame, weather_hashes


def train():
    target_path = ROOT / 'data/research/mrc_ec_monthly_samples.csv'
    weather_path = ROOT / 'data/external/multivariate_weather/manifest.json'
    frame, weather_hashes = training_frame(target_path, weather_path)
    source_bundle = json.loads((ROOT / 'data/research/workspace.json').read_text(encoding='utf-8'))
    registry = dict(schema_version=1, models={})
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for station, data in frame.groupby('station'):
        data = data.sort_values('month_start').copy()
        y = 'conductivity_mS_per_m'
        if not np.isfinite(data[y]).all() or (data[y] < 0).any():
            raise ValueError('Invalid target EC.')
        initial = data[data.month_start < '2019-01-01']
        if initial[FEATURES].isna().all().any():
            raise ValueError('A feature is wholly missing in training.')
        fitted = pipeline().fit(initial[FEATURES], initial[y])
        records, evaluation = [], {}
        lookup = data.set_index('month_start')[y]
        for split, start, end in [('validation', '2019-01-01', '2022-01-01'),
                                   ('holdout', '2022-01-01', '2024-01-01')]:
            train_rows = data[data.month_start < start]
            if split == 'holdout':
                fitted = pipeline().fit(train_rows[FEATURES], train_rows[y])
            selected = data[(data.month_start >= start) & (data.month_start < end)]
            predictions = fitted.predict(selected[FEATURES])
            for (_, row), predicted in zip(selected.iterrows(), predictions):
                target = row.month_start
                # Baselines share the weather model's two-month input latency.
                prior = lookup[lookup.index <= target - pd.DateOffset(months=2)]
                seasonal = lookup.get(target - pd.DateOffset(months=12), np.nan)
                climate = train_rows.loc[train_rows.month_start.dt.month == target.month, y].mean()
                records.append(dict(split=split, station=station, target_month=target.date().isoformat(),
                    actual=row[y], RandomForest=predicted,
                    Persistence=prior.iloc[-1] if len(prior) else np.nan,
                    SeasonalNaive=seasonal, MonthlyClimatology=climate))
            cohort = pd.DataFrame([r for r in records if r['split'] == split]).dropna()
            evaluation[split] = {model: dict(n=len(cohort),
                mae_mS_m=float(mean_absolute_error(cohort.actual, cohort[model])),
                rmse_mS_m=float(np.sqrt(mean_squared_error(cohort.actual, cohort[model]))))
                for model in ['RandomForest', 'Persistence', 'SeasonalNaive', 'MonthlyClimatology']}
        final = pipeline().fit(data[FEATURES], data[y])
        out = ROOT / 'runs/multivariate_ec' / station.lower() / version
        out.mkdir(parents=True, exist_ok=False)
        model_path = out / 'model.joblib'
        joblib.dump(final, model_path)
        pd.DataFrame(records).to_csv(out / 'predictions.csv', index=False)
        manifest = dict(schema_version=1, model_version=version, station=station,
            model='RandomForestRegressor', sklearn_version=sklearn.__version__,
            feature_order=FEATURES, feature_units=UNITS, weather_lag_months=2,
            training_cutoff=data.month_start.max().date().isoformat(),
            training_months=len(data), source_sample_count=int(data.sample_count.sum()),
            target_unit='mS/m', target_quality='UNVERIFIED_SOURCE_QA_NOT_PROMOTED',
            source_qa_counts=pd.Series([r['quality_flag'] for r in source_bundle['observations']
                if r['site_code'] == {'MYTHO': 'MRC_VN_019805', 'TANCHAU': 'MRC_VN_019803'}[station]]).value_counts().to_dict(),
            source_observation_bundle_sha256=sha256(ROOT / 'data/research/workspace.json'),
            input_sha256={str(p.relative_to(ROOT)): sha256(p) for p in [target_path, weather_path]},
            weather_source_sha256=weather_hashes,
            parameters=dict(n_estimators=300, max_depth=8, min_samples_leaf=3, random_state=42),
            selection='Fixed parameters before validation; holdout not used for selection.',
            evaluation=evaluation, evaluation_protocol='Train <=2018 for validation 2019-2021; train <=2021 for holdout 2022-2023. Baseline inputs available through target minus two months. Final model refit on all labels.',
            feature_importance=dict(zip(FEATURES, map(float, final[-1].feature_importances_))),
            missing_training_features=data[FEATURES].isna().sum().to_dict(),
            deployment_ready=False, weather_unit_note='Open-Meteo ERA5 daily mean 10m wind in explicit m/s; monthly arithmetic mean.',
            spatial_note='Weather grid coordinates differ from EC sampling coordinates.',
            model_sha256=sha256(model_path))
        manifest['predictions_sha256'] = sha256(out / 'predictions.csv')
        manifest_path = out / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        registry['models'][station] = dict(model_path=str(model_path.relative_to(ROOT)).replace('\\', '/'),
            manifest_path=str(manifest_path.relative_to(ROOT)).replace('\\', '/'),
            model_sha256=sha256(model_path), manifest_sha256=sha256(manifest_path))
        print(station, len(data), evaluation['holdout'], flush=True)
    (ROOT / 'data/models/multivariate_registry.json').write_text(json.dumps(registry, indent=2), encoding='utf-8')


if __name__ == '__main__':
    train()
