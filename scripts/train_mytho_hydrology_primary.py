"""Fit the selected My Tho weather + hydrology RF as the primary forecast artifact.

The choice was made after inspecting historical outage windows. This script
preserves their research status and does not claim blind operational validation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from backend.domain.multivariate_ec import FEATURES, HYDRO_FEATURES, UNITS
from backend.repositories.hydrology_inputs import source_paths
from backend.repositories.multivariate_inputs import get_monthly_weather
from scripts.evaluate_frozen_ec_gap import OUTPUT as GAP_OUTPUT
from scripts.evaluate_frozen_ec_gap_remedies import OUTPUT as REMEDY_OUTPUT
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.train_multivariate_ec import pipeline

ROOT = Path(__file__).resolve().parents[1]
VERSION = "20261108T_HYDROLOGY_PRIMARY_V1"
OUTPUT = ROOT / "runs/multivariate_ec/mytho" / VERSION
ORDER = FEATURES + HYDRO_FEATURES
METHODS = ("RandomForest", "FrozenPersistence", "MonthlyClimatology",
           "FrozenSeasonalRepeat")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluation_rows(experiment, split):
    remedies = pd.read_csv(REMEDY_OUTPUT / "predictions.csv")
    frozen = pd.read_csv(GAP_OUTPUT / "predictions.csv")
    remedies = remedies[(remedies.experiment == experiment) &
                        (remedies.ec_delay_days == 5)].sort_values("target_month")
    frozen = frozen[(frozen.station == "MYTHO") &
                    (frozen.experiment == experiment) &
                    (frozen.ec_delay_days == 5)].sort_values("target_month")
    if (len(remedies) != (24 if split == "holdout" else 36) or
            remedies.target_month.tolist() != frozen.target_month.tolist() or
            not np.allclose(remedies.actual_mS_m, frozen.actual_mS_m, rtol=0, atol=1e-8)):
        raise ValueError("Frozen evaluation cohorts do not match")
    return pd.DataFrame(dict(split=split, station="MYTHO",
        target_month=remedies.target_month.to_numpy(),
        actual=remedies.actual_mS_m.to_numpy(),
        RandomForest=remedies.WeatherHydrology.to_numpy(),
        FrozenPersistence=frozen.FrozenPersistence.to_numpy(),
        MonthlyClimatology=frozen.MonthlyClimatology.to_numpy(),
        FrozenSeasonalRepeat=frozen.FrozenSeasonalRepeat.to_numpy()))


def metrics(rows):
    actual = rows.actual.to_numpy(dtype=float)
    result = {}
    for method in METHODS:
        forecast = rows[method].to_numpy(dtype=float)
        if not np.isfinite(forecast).all():
            raise ValueError("Incomplete frozen evaluation method: " + method)
        error = forecast - actual
        result[method] = dict(n=len(rows), mae_mS_m=float(np.abs(error).mean()),
                              rmse_mS_m=float(np.sqrt(np.mean(error ** 2))))
    return result


def train():
    data = data_matrix(5)
    if (data.month_start.max() != pd.Timestamp("2023-12-01") or
            data.month_start.duplicated().any() or len(data) < 400 or
            not np.isfinite(data.conductivity_mS_per_m.to_numpy(dtype=float)).all() or
            data[ORDER].isna().all().any()):
        raise ValueError("Invalid My Tho training cohort")
    validation = evaluation_rows("gap_2019_2021", "validation")
    holdout = evaluation_rows("gap_2022_2023", "holdout")
    primary_gap = evaluation_rows("gap_2021_2023", "primary_gap")
    evaluated = pd.concat([validation, holdout], ignore_index=True)
    assessment = dict(validation=metrics(validation), holdout=metrics(holdout))
    gap_metrics = metrics(primary_gap)
    model = pipeline().set_params(randomforestregressor__n_jobs=1)
    model.fit(data[ORDER], data.conductivity_mS_per_m)
    # The serving adapter must produce the same hydro values as the study.
    from backend.repositories.hydrology_inputs import _matrix, _signature
    serving = _matrix(_signature())
    joined = data[["weather_month"] + HYDRO_FEATURES].merge(
        serving, on="weather_month", suffixes=("_study", "_serving"), validate="many_to_one")
    if len(joined) != len(data):
        raise ValueError("Hydrology serving coverage differs from training")
    for key in HYDRO_FEATURES:
        left = joined[key + "_study"].to_numpy(dtype=float)
        right = joined[key + "_serving"].to_numpy(dtype=float)
        if not np.allclose(left, right, rtol=0, atol=1e-10, equal_nan=True):
            raise ValueError("Hydrology serving transform differs: " + key)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    model_path = OUTPUT / "model.joblib"
    joblib.dump(model, model_path)
    evaluated.to_csv(OUTPUT / "predictions.csv", index=False)
    target_path = ROOT / "data/research/mrc_ec_monthly_samples.csv"
    weather_manifest = ROOT / "data/external/multivariate_weather/manifest.json"
    source_files = [target_path, weather_manifest, *source_paths(),
                    REMEDY_OUTPUT / "run_manifest.json", REMEDY_OUTPUT / "predictions.csv",
                    GAP_OUTPUT / "run_manifest.json", GAP_OUTPUT / "predictions.csv"]
    weather_source_hashes = {row["source"]: row["sha256"]
        for row in get_monthly_weather("MYTHO")}
    manifest = dict(schema_version=1, model_version=VERSION, station="MYTHO",
        model="RandomForestRegressor", sklearn_version=sklearn.__version__,
        feature_order=ORDER, feature_units={key: UNITS[key] for key in ORDER},
        weather_lag_months=2, hydrology_lag_months=2,
        training_cutoff=data.month_start.max().date().isoformat(),
        training_months=len(data), source_sample_count=int(data.sample_count.sum()),
        target_unit="mS/m", target_quality="UNVERIFIED_SOURCE_QA_NOT_PROMOTED",
        input_sha256={path.relative_to(ROOT).as_posix(): sha(path) for path in source_files},
        weather_source_sha256=weather_source_hashes,
        parameters=dict(n_estimators=300, max_depth=8, min_samples_leaf=3, random_state=42),
        selection="Selected by user after inspected retrospective windows; no blind model selection claim.",
        evaluation=assessment, evaluation_protocol_id="FROZEN_EC_HYDROLOGY_PRIMARY_V1",
        evaluation_protocol="Fit once before a 24/36-month My Tho EC outage; weather and hydrology t-2 assumed available month end +5d. Withheld EC used only for scoring.",
        gap_validation=dict(protocol_id="FROZEN_EC_HYDROLOGY_PRIMARY_V1",
            experiment="gap_2021_2023", period="2021-01..2023-12", ec_delay_days=5,
            metrics=gap_metrics, freeze_rule="My Tho EC labels locked at first issue; model fitted once before outage.",
            data_kind="RETROSPECTIVE_RESEARCH", deployment_ready=False),
        feature_importance=dict(zip(ORDER, map(float, model[-1].feature_importances_))),
        missing_training_features=data[ORDER].isna().sum().astype(int).to_dict(),
        primary_for_forecast=True, deployment_ready=False,
        availability_note="Historical weather/hydrology publication times are assumed, not verified; require complete current t-2 source months.",
        model_sha256=sha(model_path), predictions_sha256=sha(OUTPUT / "predictions.csv"))
    manifest_path = OUTPUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
        allow_nan=False) + "\n", encoding="utf-8")
    registry_path = ROOT / "data/models/multivariate_registry.json"
    registry = json.loads(registry_path.read_text("utf-8"))
    registry["models"]["MYTHO"] = dict(
        model_path=model_path.relative_to(ROOT).as_posix(),
        manifest_path=manifest_path.relative_to(ROOT).as_posix(),
        model_sha256=sha(model_path), manifest_sha256=sha(manifest_path))
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print("My Tho hydrology primary", len(data), assessment, flush=True)


if __name__ == "__main__":
    train()
