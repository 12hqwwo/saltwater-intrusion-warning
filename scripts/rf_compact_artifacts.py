"""Repackage sourced RF_compact backtests and compute the archived next forecast.

Historical predictions remain the original research outputs. Dates and training
coverage are reconstructed and checked against their as-of inputs; packaging
never invents predictions, evaluation scores, or a replacement model chart.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import tempfile

import numpy as np
import pandas as pd
import sklearn

from backend.repositories.multivariate_inputs import get_weather_input
from scripts.backtest_asof_ec import available_date_for, issue_date_for
from scripts.experiment_ec_extreme_robust import COMPACT, fit_predict
from scripts.experiment_ec_long_hydrology import (
    data_matrix, monthly_kratie_flow, monthly_stage,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/ec_extreme_robust_20261029"
PARAMETERS = dict(n_estimators=100, max_depth=7, min_samples_leaf=3,
                  max_features=0.8, random_state=42)
MODELS = {"Persistence": "Persistence", "MonthlyClimatology": "Monthly Climatology",
          "RF_compact": "RF_compact"}
LOCAL_TZ = timezone(timedelta(hours=7))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp(day):
    # Inputs record a calendar date only; midnight is a serialization convention.
    return datetime.combine(day, time.min, LOCAL_TZ).isoformat()


def known_rows(matrix, target, delay):
    issue = issue_date_for(pd.Timestamp(target))
    return matrix[(matrix.month_start < target) &
                  (matrix.month_start.map(lambda m: available_date_for(m, delay)) <= issue) &
                  (matrix.weather_available_at <= issue)].sort_values("month_start")


def metadata(train, target, delay, weather_month):
    target = pd.Timestamp(target)
    issue = issue_date_for(target)
    if train.empty:
        raise ValueError("No labels available at the forecast issue date.")
    weather_available = available_date_for(weather_month, 5)
    latest = train.month_start.max()
    last_release = max(available_date_for(m, delay) for m in train.month_start)
    feature_release = max(weather_available, max(train.weather_available_at))
    if max(last_release, feature_release) > issue:
        raise ValueError("Forecast uses inputs unavailable at its issue date.")
    latest_source = max(latest, pd.Timestamp(weather_month))
    return dict(forecast_origin=timestamp(issue), target_month=target.date().isoformat(),
                origin_time_precision="DATE_ONLY_MIDNIGHT_CONVENTION",
                horizon=1, station="MYTHO", unit="mS/m", n_train_samples=len(train),
                train_last_target_month=latest.date().isoformat(),
                max_train_target_available_at=timestamp(last_release),
                max_feature_available_at=timestamp(feature_release),
                weather_month=pd.Timestamp(weather_month).date().isoformat(),
                latest_source_month=latest_source.date().isoformat(),
                age_latest_months=int((target.year-latest_source.year)*12+target.month-latest_source.month),
                ec_age_months=int((target.year-latest.year)*12+target.month-latest.month))


def historical_predictions(source, matrix, delay):
    """Preserve source values, rejecting mismatched cohorts or as-of metadata."""
    if delay not in (5, 35) or source.target_month.duplicated().any():
        raise ValueError("Invalid delay or duplicate source target month.")
    rows = []
    for _, original in source.iterrows():
        target = pd.Timestamp(original.target_month)
        selected = matrix[matrix.month_start.eq(target)]
        if len(selected) != 1:
            raise ValueError("Source target not present exactly once in the input matrix.")
        observed = selected.iloc[0]
        train = known_rows(matrix, target, delay)
        issue = issue_date_for(target)
        if (pd.Timestamp(original.issue_date).date() != issue or len(train) != original.train_n
                or not math.isclose(float(original.actual), float(observed.conductivity_mS_per_m),
                                    rel_tol=0, abs_tol=1e-9)):
            raise ValueError("Source prediction does not match training count, label or issue date.")
        climate = train[train.month_start.dt.month.eq(target.month)].conductivity_mS_per_m.mean()
        for column, expected in [("Persistence", train.conductivity_mS_per_m.iloc[-1]),
                                 ("MonthlyClimatology", climate)]:
            if not math.isclose(float(original[column]), float(expected), rel_tol=0, abs_tol=1e-8):
                raise ValueError("Source baseline does not match available training labels.")
        for column in MODELS:
            if not math.isfinite(float(original[column])) or float(original[column]) < 0:
                raise ValueError("Invalid source prediction.")
        if original.split != "retrospective_2022_2023":
            continue
        common = metadata(train, target, delay, observed.weather_month)
        for column, label in MODELS.items():
            row = dict(common, stage="test", model=label, candidate_id=column,
                       actual=float(original.actual), predicted=float(original[column]),
                       actual_available_at=timestamp(available_date_for(target, delay)),
                       status="SUCCESS", label_available_for_evaluation=True,
                       in_common_cohort=True)
            if column != "RF_compact":
                latest = train.month_start.max()
                row.update(latest_source_month=latest.date().isoformat(),
                           age_latest_months=common["ec_age_months"],
                           max_feature_available_at=timestamp(available_date_for(latest, delay)))
            rows.append(row)
    if not rows:
        raise ValueError("No retrospective evaluation rows.")
    return pd.DataFrame(rows)


def error_metrics(part):
    errors = part.predicted.to_numpy(dtype=float) - part.actual.to_numpy(dtype=float)
    if not len(errors) or not np.isfinite(errors).all():
        raise ValueError("Cannot score empty or nonfinite predictions.")
    return dict(eval_samples=len(errors), mae_mS_m=float(np.abs(errors).mean()),
                rmse_mS_m=float(np.sqrt(np.mean(errors**2))))


def make_metrics(predictions):
    rows = []
    for (stage, model), part in predictions.groupby(["stage", "model"], sort=False):
        months = sorted(part.target_month.tolist())
        if len(months) != len(set(months)):
            raise ValueError("Duplicate model/month evaluation row.")
        score = error_metrics(part)
        for cohort in ("model_available", "common"):
            rows.append(dict(stage=stage, model=model, cohort=cohort, **score,
                             target_months_with_actual=len(months),
                             evaluation_label_cutoff=max(part.actual_available_at),
                             coverage_fraction=1.0,
                             evaluation_months_sha256=hashlib.sha256(",".join(months).encode()).hexdigest()))
    return rows


def make_high_ec_metrics(predictions, threshold):
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Invalid training P90 threshold.")
    return [dict(model=model, train_p90_mS_m=float(threshold), **error_metrics(part))
            for model, part in predictions[predictions.actual.ge(threshold)].groupby("model", sort=False)]


def next_forecast(matrix, delay):
    """Fit the actual source algorithm for the month after the last EC label."""
    target = matrix.month_start.max() + pd.DateOffset(months=1)
    weather_month = target - pd.DateOffset(months=2)
    weather = get_weather_input("MYTHO", target.strftime("%Y-%m"))
    if weather["input_month"] != weather_month.strftime("%Y-%m") or not weather["complete"]:
        raise ValueError("Next forecast requires complete t-2 weather.")
    values = dict(month_sin=float(np.sin(2*np.pi*target.month/12)),
                  month_cos=float(np.cos(2*np.pi*target.month/12)),
                  rainfall_mm=float(weather["rainfall_mm"]))
    for frame in (monthly_kratie_flow(), monthly_stage("019803", "tc")):
        chosen = frame[frame.weather_month.eq(weather_month)]
        if len(chosen) != 1:
            raise ValueError("Missing next-forecast upstream inputs.")
        values.update({k:float(v) for k,v in chosen.iloc[0].items() if k != "weather_month"})
    if not all(np.isfinite(values[key]) for key in COMPACT):
        raise ValueError("Incomplete next-forecast predictors.")
    features = pd.Series(values)
    train = known_rows(matrix, target, delay)
    common = metadata(train, target, delay, weather_month)
    predicted = float(fit_predict("rf", COMPACT, 1.0, train, features))
    if not math.isfinite(predicted) or predicted < 0:
        raise ValueError("Estimator returned an invalid forecast.")
    climate = float(train[train.month_start.dt.month.eq(target.month)].conductivity_mS_per_m.mean())
    predictions = []
    for candidate, value in [("Persistence", float(train.conductivity_mS_per_m.iloc[-1])),
                             ("MonthlyClimatology", climate), ("RF_compact", predicted)]:
        row = dict(common, stage="next_after_last_observation", model=MODELS[candidate],
                   candidate_id=candidate, actual=None, actual_available_at=None,
                   predicted=value, status="SUCCESS")
        if candidate != "RF_compact":
            row.update(latest_source_month=train.month_start.max().date().isoformat(),
                       age_latest_months=common["ec_age_months"],
                       max_feature_available_at=common["max_train_target_available_at"])
        predictions.append(row)
    selected = next(row for row in predictions if row["candidate_id"] == "RF_compact")
    return dict(data_kind="experimental_next_after_last_observation", selected_model="RF_compact",
                target_month=common["target_month"], forecast_origin=common["forecast_origin"],
                availability_mode="assumed_month_end_plus_lag", quality_status="EXPERIMENTAL",
                deployment_ready=False, selected_prediction=selected, all_predictions=predictions,
                feature_values={key: values[key] for key in COMPACT},
                feature_order=COMPACT, model_parameters=PARAMETERS,
                software=dict(scikit_learn=sklearn.__version__), weather_source=weather,
                note="Computed from source RF_compact algorithm under assumed availability; archived research forecast, not a forecast for today.")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def plot_predictions(predictions, output):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    figure, axes = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={"height_ratios": [3, 1]})
    first = predictions[predictions.candidate_id.eq("RF_compact")]
    axes[0].plot(pd.to_datetime(first.target_month), first.actual, "o-", label="Observed EC", color="#173b45")
    for candidate, label in MODELS.items():
        part = predictions[predictions.candidate_id.eq(candidate)]
        axes[0].plot(pd.to_datetime(part.target_month), part.predicted, label=label)
    axes[0].set(title="MYTHO: retrospective 2022-2023 | RF_compact (100 trees)", ylabel="EC (mS/m)")
    axes[0].legend(); axes[0].grid(alpha=.2)
    scores = [row for row in make_metrics(predictions) if row["cohort"] == "common"]
    axes[1].barh([r["model"] for r in scores], [r["mae_mS_m"] for r in scores])
    axes[1].set_xlabel("Retrospective MAE (mS/m), same target months")
    figure.tight_layout()
    figure.savefig(output, dpi=150, metadata={"Software": "RF_compact artifact builder"})
    plt.close(figure)


def build_run(delay, output_dir=None):
    if delay not in (5, 35):
        raise ValueError("EC release assumption must be 5 or 35 days.")
    run_id = "MYTHO_RF_COMPACT_20261030" if delay == 5 else "MYTHO_RF_COMPACT_LAG30_20261030"
    destination = Path(output_dir) if output_dir is not None else ROOT / "runs/local_ec_backtest" / run_id
    source_file = SOURCE / f"predictions_{delay}d.csv"
    source = pd.read_csv(source_file)
    if len(source) != 60 or source.split.value_counts().to_dict() != {
            "validation_2019_2021": 36, "retrospective_2022_2023": 24}:
        raise ValueError("Expected the original 36 validation and 24 retrospective months.")
    matrix = data_matrix(delay)
    packed = historical_predictions(source, matrix, delay)
    metrics = make_metrics(packed)
    initial = known_rows(matrix, pd.Timestamp(source.target_month.min()), delay)
    threshold = float(initial.conductivity_mS_per_m.quantile(.9))
    high = make_high_ec_metrics(packed, threshold)
    validation = source[source.split.eq("validation_2019_2021")]
    validation_mae = lambda name: float(np.abs(validation[name]-validation.actual).mean())
    primary_file = SOURCE / "predictions_5d.csv"
    primary_source = pd.read_csv(primary_file)
    primary_validation = primary_source[primary_source.split.eq("validation_2019_2021")]
    primary_mae = lambda name: float(np.abs(primary_validation[name]-primary_validation.actual).mean())
    candidates = ["RF_compact", "RF_compact_weight3", "RF_compact_weight8", "RF_full_weight3", "ET_compact_weight3"]
    selected = min(candidates, key=primary_mae)
    if selected != "RF_compact":
        raise ValueError("Source validation selection changed; review before publishing.")
    selection = dict(selected_model=selected, selected_on="validation", validation_metric="mae_mS_m",
                     validation_mae=validation_mae(selected), persistence_validation_mae=validation_mae("Persistence"),
                     selection_protocol="Frozen choice from primary +5-day validation; +35 days is a sensitivity evaluation",
                     primary_availability_lag_days=5, primary_validation_mae=primary_mae(selected),
                     evaluation_availability_lag_days=delay)
    common = [row for row in metrics if row["cohort"] == "common"]
    compact = next(row for row in common if row["model"] == "RF_compact")
    persistence = next(row for row in common if row["model"] == "Persistence")
    assessment = dict(selected_on_validation=selected, selected_test_mae_mS_m=compact["mae_mS_m"],
                      persistence_test_mae_mS_m=persistence["mae_mS_m"],
                      selected_beats_persistence_on_test=compact["mae_mS_m"] < persistence["mae_mS_m"],
                      mae_skill_vs_persistence=1-compact["mae_mS_m"]/persistence["mae_mS_m"],
                      deployment_ready=False,
                      note="Retrospective 2022-2023 period was previously inspected; lower overall MAE is not independent operational validation.")
    forecast = next_forecast(matrix, delay)
    target_file = ROOT / "data/research/mrc_ec_monthly_samples.csv"
    source_paths = [source_file, primary_file, SOURCE / f"protocol_{delay}d.json", target_file,
                    ROOT / "scripts/experiment_ec_extreme_robust.py",
                    ROOT / "scripts/experiment_ec_long_hydrology.py",
                    ROOT / "scripts/backtest_asof_ec.py",
                    ROOT / "data/external/multivariate_weather/manifest.json",
                    ROOT / "data/external/mrc_kratie_discharge_20261029/014901_Discharge_Calculated daily discharge_22a8130e.csv",
                    ROOT / "data/external/tien_manual_long_20261029/019803_Water_Level_Manual_3bd17f3a.csv",
                    ROOT / "data/external/tien_manual_2024_2026_20261029/019803_Water_Level_Manual_3bd17f3a.csv"]
    split_rows = [dict(split="train", start=initial.month_start.min().date().isoformat(),
                       end=initial.month_start.max().date().isoformat(),
                       calendar_months=int((initial.month_start.max().year-initial.month_start.min().year)*12+
                                           initial.month_start.max().month-initial.month_start.min().month+1),
                       actual_months=len(initial))]
    for name, label in [("validation_2019_2021", "validation"), ("retrospective_2022_2023", "test")]:
        group = source[source.split.eq(name)]
        split_rows.append(dict(split=label, start=group.target_month.min(), end=group.target_month.max(),
                               calendar_months=len(group), actual_months=len(group)))
    manifest = dict(status="COMPLETED", run_id=run_id, script_version="4.0.0",
                    script_sha256=digest(__file__), created_at_utc=datetime.now(timezone.utc).isoformat(),
                    config=dict(station="MYTHO", validation_months=len(validation), test_months=packed.target_month.nunique(),
                                min_train_samples=96, min_eval_months=6, trees=PARAMETERS["n_estimators"],
                                seed=PARAMETERS["random_state"], availability_lag_days=delay, **{
                                    k:v for k,v in PARAMETERS.items() if k not in {"n_estimators", "random_state"}}),
                    input=dict(file_name=target_file.name, sha256=digest(target_file), station="MYTHO",
                               target_column="conductivity_mS_per_m", unit="mS/m", input_station_rows=len(matrix),
                               calendar_months=int((matrix.month_start.max().year-matrix.month_start.min().year)*12+
                                                   matrix.month_start.max().month-matrix.month_start.min().month+1),
                               observed_target_months=len(matrix), last_target_month=matrix.month_start.max().date().isoformat(),
                               trailing_calendar_months_without_ec=0, availability_mode="assumed_month_end_plus_lag",
                               availability_lag_days=delay, source_quality_validation="not_performed; retain upstream quality flags"),
                    software=dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__, scikit_learn=sklearn.__version__),
                    protocol=dict(target="Single MRC EC sample in the target month, mS/m; no target imputation",
                                  forecast_origin="Day 6 of preceding month; calendar dates serialized at local midnight (+07:00)",
                                  horizon="One calendar month ahead", features=COMPACT,
                                  evaluation="Saved rolling-origin as-of predictions; availability dates are assumptions, historical vintages unavailable",
                                  validation="Candidate frozen on primary +5-day 2019-2021 validation; +35-day sensitivity retains that choice",
                                  test="Previously inspected retrospective 2022-2023",
                                  high_ec_definition="Actual >= fixed P90 of labels available at first validation issue",
                                  high_ec_reference_issue=timestamp(issue_date_for(pd.Timestamp(source.target_month.min())))),
                    historical_prediction_status="REPACKED_SOURCE_PREDICTIONS_NOT_RETRAINED",
                    source_sha256={p.relative_to(ROOT).as_posix():digest(p) for p in source_paths},
                    limitations=["Historical publication timestamps and source vintages are unavailable; release lags are assumed.",
                                 "Previously inspected retrospective evaluation, not a new blind holdout.",
                                 "No observed EC after 2023 to validate current forecasts; monthly samples do not describe hourly peaks.",
                                 "Extreme EC is still underpredicted; upstream predictors do not validate gate connectivity or salt propagation.",
                                 "Repackaged source predictions retain their original values; software lists the current packaging/next-forecast environment."],
                    high_ec_metrics=high, selection=selection, test_assessment=assessment, test_common_metrics=common)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Complete every output before replacing an existing packaged run.
    with tempfile.TemporaryDirectory(prefix="rf-compact-", dir=destination.parent) as directory:
        staging = Path(directory)
        packed.to_csv(staging / "predictions.csv", index=False)
        pd.DataFrame(metrics).to_csv(staging / "metrics.csv", index=False)
        pd.DataFrame(high, columns=["model", "train_p90_mS_m", "eval_samples", "mae_mS_m", "rmse_mS_m"]).to_csv(staging / "high_ec_metrics.csv", index=False)
        pd.DataFrame(split_rows).to_csv(staging / "split_manifest.csv", index=False)
        write_json(staging / "selection.json", selection)
        write_json(staging / "next_forecast.json", forecast)
        plot_predictions(packed, staging / "forecast_chart.png")
        manifest["output_sha256"] = {p.name:digest(p) for p in sorted(staging.iterdir())}
        manifest["chart_source_predictions_sha256"] = manifest["output_sha256"]["predictions.csv"]
        write_json(staging / "run_manifest.json", manifest)
        destination.mkdir(parents=True, exist_ok=True)
        for path in staging.iterdir():
            path.replace(destination / path.name)
    return manifest
