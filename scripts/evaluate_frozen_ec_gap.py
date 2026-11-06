"""Reproduce a multi-year EC outage while weather continues to arrive monthly.

Fit once at the first issue date; later EC is accessible only to the scorer.
Existing rolling-origin evidence and deployed model artifacts are never replaced.
No model/feature selection is performed using these already-inspected periods.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain.multivariate_ec import FEATURES
from backend.domain.river_interpolation import MY_THUAN_KM, MY_THUAN_RATIO, interpolate_anchors
from scripts.backtest_asof_ec import available_date_for, issue_date_for
from scripts.evaluate_mythuan_three_station import score
from scripts.train_multivariate_ec import pipeline, training_frame

PROTOCOL = "FROZEN_EC_WEATHER_ONLY_V1"
OUTPUT = ROOT / "outputs/frozen_ec_gap_20261104"
EXPERIMENTS = {
    "gap_2019_2021": ("2019-01-01", "2021-12-01"),
    "gap_2021_2023": ("2021-01-01", "2023-12-01"),
    "gap_2022_2023": ("2022-01-01", "2023-12-01"),
}
PRIMARY = "gap_2021_2023"
MODELS = ("RandomForest", "FrozenPersistence", "MonthlyClimatology",
          "FrozenSeasonalRepeat", "SeasonalityOnlyRF")
STATIONS = ("TANCHAU", "MYTHUAN", "MYTHO")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def freeze_training(data, first_target, ec_delay_days):
    """The frozen EC set obeys the same issue/availability rule as production."""
    issue = issue_date_for(pd.Timestamp(first_target))
    available = data.month_start.map(lambda m: available_date_for(m, ec_delay_days))
    weather_available = data.weather_month.map(lambda m: available_date_for(m, 5))
    return data[(data.month_start < pd.Timestamp(first_target)) & (available <= issue)
                & (weather_available <= issue)].sort_values("month_start").copy()


def forecast_gap(known, weather_features, model_factory=pipeline):
    """Predict without receiving any post-cutoff EC labels, including for baselines."""
    required = ["month_start", "weather_month"] + FEATURES
    known = known.sort_values('month_start').copy()
    future = weather_features[required].sort_values("month_start").copy()
    if known.empty or future.empty or len(known) < 24:
        raise ValueError("A frozen experiment requires training history and forecast months")
    if known.month_start.duplicated().any() or future.month_start.duplicated().any():
        raise ValueError("Duplicate station/month in frozen experiment")
    if known.month_start.max() >= future.month_start.min():
        raise ValueError("Frozen labels overlap the withheld period")
    if not np.isfinite(known[FEATURES + ["conductivity_mS_per_m"]].to_numpy(dtype=float)).all():
        raise ValueError("Training data must be finite")
    if not np.isfinite(future[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Forecast weather must be complete and finite")
    if not (future.weather_month == future.month_start - pd.DateOffset(months=2)).all():
        raise ValueError("Forecast weather must come from target minus two months")
    for row in future.itertuples():
        if available_date_for(row.weather_month, 5) > issue_date_for(row.month_start):
            raise ValueError("Forecast weather is unavailable at issue time")
    target = "conductivity_mS_per_m"
    # The ablation uses the identical fixed RF parameters, with only calendar features.
    rf = model_factory().fit(known[FEATURES], known[target])
    calendar = model_factory().fit(known[["month_sin", "month_cos"]], known[target])
    future["RandomForest"] = rf.predict(future[FEATURES])
    future["SeasonalityOnlyRF"] = calendar.predict(future[["month_sin", "month_cos"]])
    future["FrozenPersistence"] = float(known[target].iloc[-1])
    climate = known.groupby(known.month_start.dt.month)[target].mean()
    latest_by_month = known.groupby(known.month_start.dt.month)[target].last()
    future["MonthlyClimatology"] = future.month_start.dt.month.map(climate)
    future["FrozenSeasonalRepeat"] = future.month_start.dt.month.map(latest_by_month)
    lookup = known.set_index("month_start")[target]
    future["SeasonalNaive"] = [lookup.get(m - pd.DateOffset(months=12), np.nan) for m in future.month_start]
    future["seasonal_naive_available"] = future.SeasonalNaive.notna()
    future["seasonal_naive_source_month"] = future.month_start - pd.DateOffset(months=12)
    if not np.isfinite(future[list(MODELS)].to_numpy()).all():
        raise ValueError("Every full-period method must cover the same finite cohort")
    return future


def station_metrics(predictions):
    records = []
    keys = ["experiment", "ec_delay_days", "station"]
    for values, group in predictions.groupby(keys):
        metadata = dict(zip(keys, values))
        cohorts = {"all": group}
        cohorts.update({f"year_{year}": part for year, part in group.groupby(group.target_month.dt.year)})
        cohorts.update({f"gap_year_{year}": part for year, part in group.groupby(group.gap_year)})
        cohorts["dry_Dec_Apr"] = group[group.target_month.dt.month.isin([12, 1, 2, 3, 4])]
        cohorts["high_ec_training_p90"] = group[group.actual_mS_m >= group.training_p90_mS_m]
        for cohort, rows in cohorts.items():
            if rows.empty:
                continue
            for model in MODELS:
                records.append(dict(**metadata, cohort=cohort, model=model,
                                    **score(rows.actual_mS_m, rows[model])))
    return pd.DataFrame(records)


def spatial_predictions(predictions):
    """Measure the midpoint only; observed endpoints are a retrospective reference."""
    records = []
    for (experiment, delay, month), rows in predictions.groupby(["experiment", "ec_delay_days", "target_month"]):
        stations = rows.set_index("station")
        if set(stations.index) != set(STATIONS) or len(stations) != 3:
            raise ValueError("Spatial scores require the same three-station month cohort")
        tc, mt, my = (stations.loc[s] for s in STATIONS)
        records.append(dict(experiment=experiment, ec_delay_days=delay, target_month=month,
            gap_year=mt.gap_year, actual_mS_m=mt.actual_mS_m,
            TWO_OBSERVED_LINEAR=(1 - MY_THUAN_RATIO) * tc.actual_mS_m + MY_THUAN_RATIO * my.actual_mS_m,
            TWO_FORECAST_LINEAR=(1 - MY_THUAN_RATIO) * tc.RandomForest + MY_THUAN_RATIO * my.RandomForest,
            THREE_FORECAST_ANCHOR=interpolate_anchors(MY_THUAN_KM,
                [(0, tc.RandomForest), (MY_THUAN_KM, mt.RandomForest), (125, my.RandomForest)])))
    return pd.DataFrame(records)


def spatial_metrics(predictions):
    records = []
    for (experiment, delay), group in predictions.groupby(["experiment", "ec_delay_days"]):
        cohorts = {"all": group}
        cohorts.update({f"year_{year}": rows for year, rows in group.groupby(group.target_month.dt.year)})
        for cohort, rows in cohorts.items():
            for method in ("TWO_OBSERVED_LINEAR", "TWO_FORECAST_LINEAR", "THREE_FORECAST_ANCHOR"):
                records.append(dict(experiment=experiment, ec_delay_days=delay, cohort=cohort,
                                    method=method, **score(rows.actual_mS_m, rows[method])))
    return pd.DataFrame(records)


def run(output=OUTPUT):
    target_path = ROOT / "data/research/mrc_ec_monthly_samples.csv"
    frame, weather_hashes = training_frame(target_path, ROOT / "data/external/multivariate_weather/manifest.json")
    records, availability = [], []
    for experiment, (start, end) in EXPERIMENTS.items():
        months = pd.date_range(start, end, freq="MS")
        for delay in (5, 35):
            for station in STATIONS:
                data = frame[frame.station.eq(station)].sort_values("month_start")
                known = freeze_training(data, start, delay)
                selected = data[data.month_start.isin(months)]
                if len(selected) != len(months) or set(selected.month_start) != set(months):
                    raise ValueError(f"Missing withheld EC/weather: {station} {experiment}")
                # Hide all withheld targets before calling any forecasting code.
                future = forecast_gap(known, selected[["month_start", "weather_month"] + FEATURES])
                truth = selected.set_index("month_start").conductivity_mS_per_m
                future["actual_mS_m"] = future.month_start.map(truth)
                future = future.rename(columns={"month_start": "target_month"})
                future["experiment"], future["station"], future["ec_delay_days"] = experiment, station, delay
                future["first_issue_date_local"] = issue_date_for(pd.Timestamp(start)).isoformat()
                future["issue_date_local"] = future.target_month.map(lambda m: issue_date_for(m).isoformat())
                future["weather_assumed_available_at"] = future.weather_month.map(lambda m: available_date_for(m, 5).isoformat())
                future["last_training_ec_month"] = known.month_start.max().date().isoformat()
                future["last_training_ec_available_at"] = available_date_for(known.month_start.max(), delay).isoformat()
                future["training_months"] = len(known)
                future["training_p90_mS_m"] = float(np.quantile(known.conductivity_mS_per_m, .9, method="inverted_cdf"))
                future["evaluation_month_index"] = np.arange(1, len(future) + 1)
                cutoff = known.month_start.max()
                future["gap_month"] = ((future.target_month.dt.year - cutoff.year) * 12
                                       + future.target_month.dt.month - cutoff.month)
                future["gap_year"] = (future.gap_month - 1) // 12 + 1
                future["refit_count"] = 1
                records.append(future)
                for year, group in future.groupby(future.target_month.dt.year):
                    availability.append(dict(experiment=experiment, ec_delay_days=delay, station=station,
                        year=int(year), total_months=len(group), direct_seasonal_naive_available_months=int(group.seasonal_naive_available.sum())))
                print(experiment, delay, station, "frozen through", future.last_training_ec_month.iloc[0], flush=True)
    predictions = pd.concat(records, ignore_index=True)
    metrics = station_metrics(predictions)
    spatial = spatial_predictions(predictions)
    spatial_scores = spatial_metrics(spatial)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in (("predictions.csv", predictions), ("metrics.csv", metrics),
                       ("interpolation_predictions.csv", spatial), ("interpolation_metrics.csv", spatial_scores),
                       ("baseline_availability.csv", pd.DataFrame(availability))):
        data.to_csv(output / name, index=False)
    sources = [target_path, Path(__file__), ROOT / "scripts/train_multivariate_ec.py",
               ROOT / "scripts/backtest_asof_ec.py", ROOT / "backend/domain/multivariate_ec.py",
               ROOT / "scripts/evaluate_mythuan_three_station.py",
               ROOT / "scripts/run_future_forecast_2024_2026.py",
               ROOT / "backend/repositories/multivariate_inputs.py",
               ROOT / "backend/domain/river_interpolation.py",
               ROOT / "data/external/multivariate_weather/manifest.json",
               ROOT / "data/external/mythuan_weather_20261104/manifest.json"]
    registry = json.loads((ROOT / "data/models/multivariate_registry.json").read_text("utf-8"))
    manifest = dict(schema_version=1, protocol_id=PROTOCOL, primary_experiment=PRIMARY,
        experiments={key: dict(start=start[:7], end=end[:7]) for key, (start, end) in EXPERIMENTS.items()},
        ec_delay_days=[5, 35], primary_ec_delay_days=5, unit="mS/m", stations=list(STATIONS),
        forecast_rule="Issue day 6 of t-1; complete ERA5 weather t-2 assumed available month-end +5 days.",
        freeze_rule="Fit each station once with EC and weather available at the first issue; never update from withheld EC.",
        calendar_rule="Target month sin/cos is known in advance. No EC lag feature or spatial target label is used.",
        weather_scope="Weather continues arriving at each monthly issue; this is not a 36-month forecast issued all at once.",
        gap_length_note="gap_month counts calendar months since the last frozen EC label; first target is two months later under +5-day availability. Evaluation windows contain 24 or 36 scored months.",
        parameters=dict(n_estimators=300, max_depth=8, min_samples_leaf=3, random_state=42),
        full_period_models=list(MODELS),
        direct_seasonal_naive="Available only when target-12 EC belongs to the frozen training set; never included in full-period ranking.",
        frozen_seasonal_repeat="Repeat the latest known EC for each calendar month from the frozen training set; no new EC is used.",
        seasonality_ablation="Same fixed RF with month sin/cos only; isolates the observed benefit or cost of adding weather.",
        retrospective_reference="TWO_OBSERVED_LINEAR uses withheld endpoint observations only as an offline reference, never a deployable gap method.",
        spatial_scope="Scores at My Thuan only; not independent validation of every river segment or gate.",
        limitations=["Historical EC publication dates and vintage ERA5 releases are unknown; +5/+35-day delays are assumptions.",
            "These historical periods were previously inspected; this is a retrospective deployment simulation, not a fresh blind test.",
            "Overlapping experiments are reported separately, never pooled as independent evidence.",
            "No observed EC in 2024-2026 is available to validate the actual gap estimates.",
            "EC targets retain UNVERIFIED quality and UNKNOWN temperature basis; one sample/month is not a continuous monthly mean."],
        sklearn_version=sklearn.__version__,
        deployed_model_sha256={key: entry["model_sha256"] for key, entry in registry["models"].items()},
        deployment_archive_sha256=sha(ROOT / 'data/models/future_ec_forecast_2024_2026.csv'),
        input_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
        weather_source_sha256=weather_hashes,
        output_sha256={p.name: sha(p) for p in sorted(output.glob("*.csv"))})
    write_json(output / "run_manifest.json", manifest)
    return manifest


def publish(output=OUTPUT):
    """Point the API at auditable evidence without changing deployed model weights."""
    output = Path(output)
    manifest = json.loads((output / "run_manifest.json").read_text("utf-8"))
    write_json(ROOT / "data/models/frozen_ec_gap_evaluation.json", dict(schema_version=1,
        protocol_id=PROTOCOL, run_manifest_path=(output / "run_manifest.json").relative_to(ROOT).as_posix(),
        run_manifest_sha256=sha(output / "run_manifest.json"),
        primary_experiment=PRIMARY, primary_ec_delay_days=5,
        deployed_model_sha256=manifest["deployed_model_sha256"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.output)
    if args.publish:
        publish(args.output)
    print("Frozen EC gap evidence:", args.output)
