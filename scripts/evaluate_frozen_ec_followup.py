"""Research-only follow-up to the frozen My Tho EC outage ablation.

The candidate set is fixed before this run. Each candidate fits once before
the outage. Later My Tho EC is used only for scoring, and no publication
vintage or independent blind period is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend.domain.multivariate_ec import FEATURES
from scripts.evaluate_frozen_ec_gap import EXPERIMENTS, freeze_training
from scripts.evaluate_frozen_ec_gap_remedies import (
    HYDRO, NEIGHBOR, ROOT, OUTPUT as PRIOR_OUTPUT,
    forecast_candidates, metrics as prior_metrics, neighbor_asof_features,
)
from scripts.experiment_ec_long_hydrology import KRATIE, LONG, RECENT_TC, data_matrix
from scripts.train_multivariate_ec import pipeline

OUTPUT = ROOT / "outputs/frozen_ec_followup_20261108"
PROTOCOL = "FROZEN_EC_FOLLOWUP_RESEARCH_V1"
NEW_CANDIDATES = {
    "HydroMyThuanEC": FEATURES + HYDRO + ["mythuan_ec_asof"],
    "HydroTanChauEC": FEATURES + HYDRO + ["tanchau_ec_asof"],
    "HydroRidge": FEATURES + HYDRO,
    "HydroRidgeResidualRF": FEATURES + HYDRO,
}
ALL_CANDIDATES = ["WeatherOnly", "WeatherHydrology", "WeatherNeighborEC",
                  "WeatherHydrologyNeighborEC", *NEW_CANDIDATES]


def sha(path):
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix == ".py":
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def ridge_model():
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                         StandardScaler(), Ridge(alpha=10.0))


def predict_extensions(known, future):
    """Predict predeclared additions on the same as-of cohort as the prior study."""
    if "conductivity_mS_per_m" in future or "actual_mS_m" in future:
        raise ValueError("Withheld My Tho EC cannot enter prediction input")
    # The published protocol checks issue dates, source months and complete
    # future inputs before any model receives the withheld period.
    output = forecast_candidates(known, future)
    if len(output) != len(future) or not output.month_start.equals(future.month_start):
        raise ValueError("Prior candidate cohort does not match follow-up")
    y = known.conductivity_mS_per_m.to_numpy(dtype=float)
    if not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("Invalid training labels")
    for name in ("HydroMyThuanEC", "HydroTanChauEC"):
        features = NEW_CANDIDATES[name]
        if not np.isfinite(future[features].to_numpy(dtype=float)).all():
            raise ValueError(f"Unavailable input for {name}")
        model = pipeline().set_params(randomforestregressor__n_jobs=1)
        output[name] = model.fit(known[features], y).predict(future[features])
    features = NEW_CANDIDATES["HydroRidge"]
    if not np.isfinite(future[features].to_numpy(dtype=float)).all():
        raise ValueError("Unavailable hydrology input")
    linear = ridge_model().fit(known[features], y)
    output["HydroRidge"] = np.maximum(0, linear.predict(future[features]))
    residual = y - linear.predict(known[features])
    forest = pipeline().set_params(randomforestregressor__n_jobs=1)
    forest.fit(known[features], residual)
    output["HydroRidgeResidualRF"] = np.maximum(
        0, linear.predict(future[features]) + forest.predict(future[features]))
    if not np.isfinite(output[ALL_CANDIDATES].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite follow-up forecast")
    return output


def run(output=OUTPUT):
    target = ROOT / "data/research/mrc_ec_monthly_samples.csv"
    samples = pd.read_csv(target, parse_dates=["month_start"])
    prior = pd.read_csv(PRIOR_OUTPUT / "predictions.csv")
    all_predictions = []
    for delay in (5, 35):
        frame = data_matrix(delay)
        frame = frame.merge(neighbor_asof_features(frame.month_start, samples, delay),
                            on="month_start", validate="one_to_one")
        frame["ec_delay_days"] = delay
        for experiment, (start, end) in EXPERIMENTS.items():
            known = freeze_training(frame, start, delay)
            future = frame[frame.month_start.between(start, end)].copy()
            if len(future) != len(pd.date_range(start, end, freq="MS")):
                raise ValueError("Incomplete follow-up cohort")
            inputs = future[["month_start", "weather_month", "ec_delay_days"] +
                            FEATURES + HYDRO + NEIGHBOR +
                            ["mythuan_source_month", "tanchau_source_month"]].copy()
            result = predict_extensions(known, inputs)
            published = prior[(prior.experiment == experiment) &
                              (prior.ec_delay_days == delay)].sort_values("target_month")
            if (len(published) != len(result) or
                    published.target_month.tolist() !=
                    result.month_start.dt.strftime("%Y-%m-%d").tolist() or
                    not np.allclose(result[["WeatherOnly", "WeatherHydrology",
                                            "WeatherNeighborEC", "WeatherHydrologyNeighborEC"]],
                                    published[["WeatherOnly", "WeatherHydrology",
                                               "WeatherNeighborEC", "WeatherHydrologyNeighborEC"]],
                                    rtol=0, atol=1e-8)):
                raise ValueError("Follow-up no longer matches published baseline")
            result["target_month"] = result.pop("month_start")
            result["actual_mS_m"] = future.conductivity_mS_per_m.to_numpy()
            result["experiment"] = experiment
            result["frozen_ec_through"] = known.month_start.max().date().isoformat()
            all_predictions.append(result)
    predictions = pd.concat(all_predictions, ignore_index=True)
    scores = prior_metrics(predictions)
    # The older scorer deliberately emits only its original four methods.
    extra = []
    for (experiment, delay), group in predictions.groupby(["experiment", "ec_delay_days"]):
        cohorts = {"all": group,
                   "dry_Dec_Apr": group[group.target_month.dt.month.isin([12, 1, 2, 3, 4])],
                   "high_EC_100": group[group.actual_mS_m >= 100]}
        for cohort, part in cohorts.items():
            if part.empty:
                continue
            actual = part.actual_mS_m.to_numpy(dtype=float)
            for name in NEW_CANDIDATES:
                forecast = part[name].to_numpy(dtype=float)
                errors = forecast - actual
                extra.append(dict(experiment=experiment, ec_delay_days=int(delay),
                    cohort=cohort, model=name, n=len(part),
                    mae_mS_m=float(np.abs(errors).mean()),
                    rmse_mS_m=float(np.sqrt(np.mean(errors ** 2))),
                    bias_mS_m=float(errors.mean()),
                    false_alerts_100=int(((forecast >= 100) & (actual < 100)).sum()),
                    missed_high_100=int(((forecast < 100) & (actual >= 100)).sum()),
                    actual_peak_mS_m=float(actual.max()),
                    predicted_peak_mS_m=float(forecast.max())))
    scores = pd.concat([scores, pd.DataFrame(extra)], ignore_index=True)
    scores["model"] = pd.Categorical(scores.model, ALL_CANDIDATES, ordered=True)
    scores = scores.sort_values(["experiment", "ec_delay_days", "cohort", "model"])
    scores["model"] = scores.model.astype(str)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output / "predictions.csv", index=False)
    scores.to_csv(output / "metrics.csv", index=False)
    sources = [target, ROOT / "data/external/multivariate_weather/manifest.json",
        next(KRATIE.glob("014901_Discharge_Calculated daily discharge_*.csv")),
        next(LONG.glob("019803_Water_Level_Manual_*.csv")),
        next(RECENT_TC.glob("019803_Water_Level_Manual_*.csv")),
        PRIOR_OUTPUT / "run_manifest.json", PRIOR_OUTPUT / "predictions.csv",
        ROOT / "scripts/evaluate_frozen_ec_gap_remedies.py",
        ROOT / "scripts/evaluate_frozen_ec_gap.py",
        ROOT / "scripts/experiment_ec_long_hydrology.py",
        ROOT / "scripts/backtest_asof_ec.py",
        ROOT / "scripts/train_multivariate_ec.py", Path(__file__)]
    manifest = dict(schema_version=1, protocol_id=PROTOCOL, station="MYTHO",
        experiments=EXPERIMENTS, ec_delay_days=[5, 35], unit="mS/m",
        candidates=NEW_CANDIDATES, controls=ALL_CANDIDATES[:4],
        ridge_alpha=10.0, residual_rf_parameters=dict(n_estimators=300,
            max_depth=8, min_samples_leaf=3, random_state=42),
        ridge_rule="Median-impute and standardize features; fit Ridge on pre-gap EC. Hybrid RF fits in-sample Ridge residuals before the gap. Clip predictions at zero.",
        asof_rule="Same day-6 issue, weather/hydrology t-2 and separate-station EC +5/+35 day assumptions as FROZEN_EC_REMEDY_RESEARCH_V1.",
        limitations=["All test windows were already inspected; no blind validation or automatic model selection.",
            "Historical input publication dates remain assumptions, not verified vintages.",
            "Downstream EC stations have no complete matching 2019–2023 monthly series in this dataset.",
            "No candidate changes the deployed model or establishes a gate decision."],
        sklearn_version=sklearn.__version__,
        hash_rule="Python source CRLF is normalized to LF before SHA-256; data and output files use raw bytes.",
        source_sha256={str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in sources},
        output_sha256={name: sha(output / name) for name in ("predictions.csv", "metrics.csv")})
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(run(args.output).query("cohort == 'all' and ec_delay_days == 5")[[
        "experiment", "model", "mae_mS_m", "rmse_mS_m",
        "false_alerts_100", "missed_high_100"]].to_string(index=False))
