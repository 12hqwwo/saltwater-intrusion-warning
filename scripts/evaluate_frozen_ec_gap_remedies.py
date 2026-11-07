"""Research ablation for a long My Tho EC outage with timely external inputs.

The target station's post-freeze EC is passed only to scoring. Neighbour EC is
an explicit separate-station-continues-reporting assumption. Historical
publication vintages are unavailable, so +5/+35 day availability is assumed.
No result here changes a deployed model or authorizes a gate decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from backend.domain.multivariate_ec import FEATURES
from backend.domain import ec_gap_evaluation
from scripts.backtest_asof_ec import available_date_for, issue_date_for
from scripts.evaluate_frozen_ec_gap import EXPERIMENTS, freeze_training
from scripts.evaluate_mythuan_three_station import score
from scripts.experiment_ec_long_hydrology import (
    KRATIE, LONG, RECENT_TC, data_matrix,
)
from scripts.train_multivariate_ec import pipeline

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/frozen_ec_remedies_20261108"
PROTOCOL = "FROZEN_EC_REMEDY_RESEARCH_V1"
NEIGHBORS = ("MYTHUAN", "TANCHAU")
HYDRO = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2",
         "tc_stage_t2", "tc_stage3_t2"]
NEIGHBOR = ["mythuan_ec_asof", "tanchau_ec_asof"]
CANDIDATES = {
    "WeatherOnly": FEATURES,
    "WeatherHydrology": FEATURES + HYDRO,
    "WeatherNeighborEC": FEATURES + NEIGHBOR,
    "WeatherHydrologyNeighborEC": FEATURES + HYDRO + NEIGHBOR,
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def neighbor_asof_features(months, samples, delay):
    """Use only another station's latest EC available at each issue date."""
    months = pd.Series(pd.to_datetime(months)).reset_index(drop=True)
    samples = samples[samples.station.isin(NEIGHBORS)].copy()
    samples["month_start"] = pd.to_datetime(samples.month_start)
    if months.duplicated().any() or samples.duplicated(["station", "month_start"]).any():
        raise ValueError("Duplicate target or neighboring station month")
    if samples.conductivity_mS_per_m.isna().any() or (samples.conductivity_mS_per_m < 0).any():
        raise ValueError("Invalid neighboring EC")
    result = pd.DataFrame({"month_start": months})
    for station in NEIGHBORS:
        prefix = station.lower()
        source = samples[samples.station.eq(station)].sort_values("month_start")
        if source.empty:
            raise ValueError(f"Missing neighboring station: {station}")
        values, source_months = [], []
        for target in months:
            issue = issue_date_for(target)
            known = source[(source.month_start < target) &
                           source.month_start.map(lambda month: available_date_for(month, delay) <= issue)]
            if known.empty:
                values.append(np.nan)
                source_months.append(None)
            else:
                latest = known.iloc[-1]
                values.append(float(latest.conductivity_mS_per_m))
                source_months.append(latest.month_start.date().isoformat())
        result[prefix + "_ec_asof"] = values
        result[prefix + "_source_month"] = source_months
    return result


def forecast_candidates(known, future, model_factory=None):
    """Fit once at the first issue, with no withheld target in future features."""
    if "conductivity_mS_per_m" in future or "actual_mS_m" in future:
        raise ValueError("Withheld target cannot enter prediction input")
    if known.empty or future.empty or known.month_start.max() >= future.month_start.min():
        raise ValueError("Frozen training and forecast periods overlap or are empty")
    if future.month_start.duplicated().any() or known.month_start.duplicated().any():
        raise ValueError("Duplicate prediction month")
    if not (future.weather_month == future.month_start - pd.DateOffset(months=2)).all():
        raise ValueError("Weather must be from target minus two months")
    for row in future.itertuples():
        issue = issue_date_for(row.month_start)
        if available_date_for(row.weather_month, 5) > issue:
            raise ValueError("Weather unavailable at issue")
        for station in NEIGHBORS:
            source_month = getattr(row, station.lower() + "_source_month")
            if pd.notna(source_month) and source_month and available_date_for(pd.Timestamp(source_month), int(row.ec_delay_days)) > issue:
                raise ValueError("Neighbor EC unavailable at issue")
    if not np.isfinite(known["conductivity_mS_per_m"]).all():
        raise ValueError("Training target must be finite")
    model_factory = model_factory or (lambda: pipeline().set_params(randomforestregressor__n_jobs=1))
    output = future[["month_start", "weather_month", "ec_delay_days"] +
                    [station.lower() + "_source_month" for station in NEIGHBORS]].copy()
    for name, features in CANDIDATES.items():
        if known[features].isna().all().any():
            raise ValueError(f"Training feature has no evidence: {name}")
        if not np.isfinite(future[FEATURES].to_numpy(dtype=float)).all():
            raise ValueError("Weather features must be complete")
        if not np.isfinite(future[[feature for feature in features if feature in HYDRO + NEIGHBOR]].to_numpy(dtype=float)).all():
            raise ValueError(f"Candidate lacks current external input: {name}")
        model = model_factory().fit(known[features], known["conductivity_mS_per_m"])
        values = model.predict(future[features])
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Invalid candidate prediction")
        output[name] = values
    return output


def metrics(predictions):
    records = []
    for (experiment, delay), group in predictions.groupby(["experiment", "ec_delay_days"]):
        cohorts = {"all": group,
                   "dry_Dec_Apr": group[group.target_month.dt.month.isin([12, 1, 2, 3, 4])],
                   "high_EC_100": group[group.actual_mS_m >= 100]}
        for cohort, part in cohorts.items():
            if part.empty:
                continue
            for name in CANDIDATES:
                actual, predicted = part.actual_mS_m.to_numpy(), part[name].to_numpy()
                high = actual >= 100
                records.append(dict(experiment=experiment, ec_delay_days=int(delay), cohort=cohort,
                    model=name, **score(actual, predicted),
                    false_alerts_100=int(((predicted >= 100) & ~high).sum()),
                    missed_high_100=int(((predicted < 100) & high).sum()),
                    actual_peak_mS_m=float(actual.max()),
                    predicted_peak_mS_m=float(predicted.max())))
    return pd.DataFrame(records)


def run(output=OUTPUT):
    targets_path = ROOT / "data/research/mrc_ec_monthly_samples.csv"
    samples = pd.read_csv(targets_path, parse_dates=["month_start"])
    predictions = []
    for delay in (5, 35):
        frame = data_matrix(delay)
        asof = neighbor_asof_features(frame.month_start, samples, delay)
        frame = frame.merge(asof, on="month_start", validate="one_to_one")
        frame["ec_delay_days"] = delay
        for experiment, (start, end) in EXPERIMENTS.items():
            known = freeze_training(frame, start, delay)
            future = frame[frame.month_start.between(start, end)].copy()
            expected = len(pd.date_range(start, end, freq="MS"))
            if len(future) != expected:
                raise ValueError("Incomplete frozen evaluation cohort")
            future_inputs = future[["month_start", "weather_month", "ec_delay_days"] +
                FEATURES + HYDRO + NEIGHBOR +
                [station.lower() + "_source_month" for station in NEIGHBORS]]
            result = forecast_candidates(known, future_inputs)
            existing = ec_gap_evaluation.records("MYTHO", experiment, delay)
            published = np.array([row["RandomForest"] for row in existing["items"]])
            if not np.allclose(result.WeatherOnly.to_numpy(), published, rtol=0, atol=1e-8):
                raise ValueError("Weather-only control differs from published frozen protocol")
            result["target_month"] = result.pop("month_start")
            result["actual_mS_m"] = future.conductivity_mS_per_m.to_numpy()
            result["experiment"] = experiment
            result["frozen_ec_through"] = known.month_start.max().date().isoformat()
            predictions.append(result)
            print(experiment, delay, "known through", result.frozen_ec_through.iloc[0], flush=True)
    prediction_frame = pd.concat(predictions, ignore_index=True)
    score_frame = metrics(prediction_frame)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    prediction_frame.to_csv(output / "predictions.csv", index=False)
    score_frame.to_csv(output / "metrics.csv", index=False)
    sources = [targets_path, ROOT / "data/external/multivariate_weather/manifest.json",
        next(KRATIE.glob("014901_Discharge_Calculated daily discharge_*.csv")),
        next(LONG.glob("019803_Water_Level_Manual_*.csv")),
        next(RECENT_TC.glob("019803_Water_Level_Manual_*.csv")),
        Path(__file__)]
    manifest = dict(schema_version=1, protocol_id=PROTOCOL, station="MYTHO",
        experiments=EXPERIMENTS, ec_delay_days=[5, 35], unit="mS/m",
        candidates=CANDIDATES, model_parameters=dict(n_estimators=300, max_depth=8,
            min_samples_leaf=3, random_state=42),
        target_rule="My Tho EC withheld after the first issue; used only for scoring.",
        neighbor_rule="My Thuan and Tan Chau are assumed to keep reporting; use only the latest EC available at each issue under the +5/+35 day delay.",
        hydro_rule="Kratie discharge and Tan Chau manual stage use target t-2. Source publication vintage is unknown; complete months are assumed available after 5 days.",
        weather_rule="Complete ERA5 target t-2 is assumed available after 5 days. No archived t-1 or t weather forecast vintage exists.",
        threshold_note="100 mS/m is a diagnostic EC threshold, not an irrigation or gate standard.",
        limitations=["All three historical windows have been inspected; no blind test is claimed.",
            "A neighbor EC outage would make the neighbor candidates unavailable.",
            "Historical publication timestamps are assumed, not verified.",
            "This analysis does not change deployed model weights or establish operational reliability."],
        sklearn_version=sklearn.__version__,
        source_sha256={str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in sources},
        output_sha256={name: sha(output / name) for name in ("predictions.csv", "metrics.csv")})
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return score_frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    print(run(arguments.output).query("cohort == 'all'")[[
        "experiment", "ec_delay_days", "model", "mae_mS_m", "rmse_mS_m",
        "false_alerts_100", "missed_high_100"]].to_string(index=False))
