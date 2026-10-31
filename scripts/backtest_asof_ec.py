"""Monthly rolling-origin EC backtest with explicit issue-time availability assumptions."""

import csv
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.train_multivariate_ec import FEATURES, pipeline, training_frame


OUTPUT = ROOT / "outputs/multivariate_ec_asof_20261029"
TARGET_PATH = ROOT / "data/research/mrc_ec_monthly_samples.csv"
WEATHER_MANIFEST = ROOT / "data/external/multivariate_weather/manifest.json"
SCENARIOS = {"EC_MONTH_END_PLUS_5D": 5, "EC_MONTH_END_PLUS_35D": 35}
MODELS = ("RandomForest", "Persistence", "SeasonalNaive", "MonthlyClimatology")


def issue_date_for(target_month):
    """Forecast month t is issued on day 6 of month t-1 (local calendar)."""
    month = target_month.date() if hasattr(target_month, "date") else target_month
    previous = date(month.year - (month.month == 1), (month.month - 2) % 12 + 1, 1)
    return date(previous.year, previous.month, 6)


def available_date_for(month_start, lag_days):
    """Assumed publication on month end plus lag_days, inclusive at issue date."""
    first = pd.Timestamp(month_start)
    return (first + pd.offsets.MonthEnd(0) + pd.Timedelta(days=lag_days)).date()


def split_for(target):
    if date(2019, 1, 1) <= target < date(2022, 1, 1):
        return "validation"
    if date(2022, 1, 1) <= target < date(2024, 1, 1):
        return "historical_2022_2023"
    return None


def scores(rows, model):
    errors = np.array([float(row[model]) - float(row["actual_mS_m"]) for row in rows])
    return dict(n=len(errors), mae_mS_m=float(np.mean(np.abs(errors))),
                rmse_mS_m=float(np.sqrt(np.mean(errors ** 2))),
                bias_mS_m=float(np.mean(errors)))


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def run(output_dir=OUTPUT):
    frame, _ = training_frame(TARGET_PATH, WEATHER_MANIFEST)
    frame["weather_available_at"] = frame.weather_month.map(lambda month: available_date_for(month, 5))
    predictions = []
    for station, station_rows in frame.groupby("station", sort=True):
        data = station_rows.sort_values("month_start").copy()
        for scenario, ec_lag_days in SCENARIOS.items():
            data["ec_available_at"] = data.month_start.map(lambda month: available_date_for(month, ec_lag_days))
            for _, target_row in data.iterrows():
                target = target_row.month_start.date()
                split = split_for(target)
                if split is None:
                    continue
                issue = issue_date_for(target)
                weather_date = target_row.weather_available_at
                if weather_date > issue:
                    raise ValueError(f"Weather future leakage: {station} {target}")
                known = data[(data.month_start < target_row.month_start)
                             & (data.ec_available_at <= issue)
                             & (data.weather_available_at <= issue)]
                if len(known) < 24:
                    raise ValueError(f"Too few known training labels: {station} {target}")
                if not (known.ec_available_at <= issue).all():
                    raise ValueError(f"EC future leakage: {station} {target}")
                model = pipeline().fit(known[FEATURES], known.conductivity_mS_per_m)
                rf = float(model.predict(target_row[FEATURES].to_frame().T)[0])
                past_year = data[data.month_start == target_row.month_start - pd.DateOffset(months=12)]
                seasonal = (float(past_year.iloc[0].conductivity_mS_per_m)
                            if len(past_year) and past_year.iloc[0].ec_available_at <= issue else np.nan)
                same_month = known[known.month_start.dt.month == target.month]
                climate = float(same_month.conductivity_mS_per_m.mean()) if len(same_month) else np.nan
                ordered_ec = np.sort(known.conductivity_mS_per_m.to_numpy())
                high_threshold = float(ordered_ec[math.ceil(0.9 * len(ordered_ec)) - 1])
                predictions.append(dict(station=station, scenario=scenario, split=split,
                    target_month=target.isoformat(), issue_date_local=issue.isoformat(),
                    weather_month=target_row.weather_month.date().isoformat(),
                    weather_assumed_available_at=weather_date.isoformat(),
                    ec_lag_days_after_month_end=ec_lag_days, training_months=len(known),
                    last_training_ec_month=known.month_start.iloc[-1].date().isoformat(),
                    last_training_ec_assumed_available_at=known.ec_available_at.iloc[-1].isoformat(),
                    high_ec_threshold_training_p90_mS_m=high_threshold,
                    actual_mS_m=float(target_row.conductivity_mS_per_m),
                    RandomForest=rf, Persistence=float(known.conductivity_mS_per_m.iloc[-1]),
                    SeasonalNaive=seasonal, MonthlyClimatology=climate))
    if len(predictions) != 240:
        raise ValueError(f"Expected 240 predictions, got {len(predictions)}")
    if any(not all(np.isfinite(row[model]) for model in MODELS) for row in predictions):
        raise ValueError("Incomplete baseline cohort")
    summary = []
    for station in ("MYTHO", "TANCHAU"):
        for scenario in SCENARIOS:
            for split in ("validation", "historical_2022_2023"):
                cohort = [r for r in predictions if (r["station"], r["scenario"], r["split"]) == (station, scenario, split)]
                if len(cohort) != (36 if split == "validation" else 24):
                    raise ValueError(f"Wrong cohort: {station} {scenario} {split}")
                for segment in ("all", "dry_Dec_Apr", "outside_dry_May_Nov", "high_ec"):
                    selected = [r for r in cohort if segment == "all" or
                        (segment == "high_ec" and r["actual_mS_m"] >= r["high_ec_threshold_training_p90_mS_m"]) or
                        (segment in ("dry_Dec_Apr", "outside_dry_May_Nov") and
                         ((date.fromisoformat(r["target_month"]).month in (12, 1, 2, 3, 4)) == (segment == "dry_Dec_Apr")))]
                    if not selected:
                        continue
                    for model in MODELS:
                        summary.append(dict(station=station, scenario=scenario, split=split,
                                            segment=segment, model=model, **scores(selected, model)))
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "asof_predictions.csv", predictions)
    write_csv(output_dir / "asof_metrics.csv", summary)
    metadata = dict(issue_rule="day 6 of preceding month, Asia/Ho_Chi_Minh",
        weather_rule="target month t uses complete ERA5 month t-2, assumed available month end + 5 days",
        ec_scenarios=SCENARIOS, model_parameters=dict(n_estimators=300, max_depth=8,
            min_samples_leaf=3, random_state=42), sklearn_version=sklearn.__version__,
        target_sha256=hashlib.sha256(TARGET_PATH.read_bytes()).hexdigest(),
        weather_manifest_sha256=hashlib.sha256(WEATHER_MANIFEST.read_bytes()).hexdigest(),
        limitation="Retrospective source versions and historical EC publication dates are unknown. 2022-2023 has already been inspected; do not call it a fresh blind holdout.")
    (output_dir / "protocol.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return predictions, summary


if __name__ == "__main__":
    predictions, summary = run()
    print(f"Saved {len(predictions)} predictions and {len(summary)} metric rows to {OUTPUT}")
    for row in summary:
        if row["segment"] == "all" and row["model"] == "RandomForest":
            print(row["station"], row["scenario"], row["split"], round(row["mae_mS_m"], 3))
