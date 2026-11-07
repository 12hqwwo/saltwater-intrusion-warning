"""Research-only My Tho EC ablation of suggested model and recent-input variants.

Freeze My Tho EC before each outage; assume daily external inputs publish five
days after observation. No later My Tho EC enters a fit or a feature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


RECENT = ("q_min7_asof", "q_delta7_asof", "tc_stage_min7_asof", "tc_stage_delta7_asof")
LABELS = ("baseline", "regime_weighted", "regime_weighted_085", "regime_gb_weighted", "rf_log",
          "rf_log_smear", "ridge_inverse_q_residual_rf", "rf_recent_daily")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def daily_series(path: Path, agg: str) -> pd.Series:
    frame = pd.read_csv(path, usecols=["observed_at", "value"])
    frame["date"] = pd.to_datetime(frame.observed_at).dt.date
    if not np.isfinite(frame.value.to_numpy(dtype=float)).all():
        raise ValueError(f"Invalid daily values in {path}")
    grouped = frame.groupby("date").value
    return (grouped.mean() if agg == "mean" else grouped.median()).sort_index()


def recent_daily_features(root: Path, months: pd.Series) -> pd.DataFrame:
    from scripts.backtest_asof_ec import issue_date_for

    qpath = next((root / "data/external/mrc_kratie_discharge_20261029").glob(
        "014901_Discharge_Calculated daily discharge_*.csv"))
    stagepath = next((root / "data/external/tien_manual_long_20261029").glob(
        "019803_Water_Level_Manual_*.csv"))
    q, stage = daily_series(qpath, "mean"), daily_series(stagepath, "median")
    records = []
    for month in months:
        issue = issue_date_for(month)
        # Publication hour and forecast issue hour are unknown. Leave one full
        # day of margin beyond the assumed five-day source delay.
        cutoff = issue - timedelta(days=6)
        dates7 = [cutoff - timedelta(days=offset) for offset in range(6, -1, -1)]
        previous7 = [cutoff - timedelta(days=offset) for offset in range(13, 6, -1)]
        qlast, qprev = q.reindex(dates7), q.reindex(previous7)
        slast, sprev = stage.reindex(dates7), stage.reindex(previous7)
        complete = all(series.notna().all() for series in (qlast, qprev, slast, sprev))
        records.append(dict(month_start=month, issue_date=issue.isoformat(),
            recent_cutoff=cutoff.isoformat(), recent_complete=bool(complete),
            q_min7_asof=float(qlast.min()) if complete else np.nan,
            q_delta7_asof=float(qlast.mean() - qprev.mean()) if complete else np.nan,
            tc_stage_min7_asof=float(slast.min()) if complete else np.nan,
            tc_stage_delta7_asof=float(slast.mean() - sprev.mean()) if complete else np.nan))
    result = pd.DataFrame(records)
    if result.month_start.duplicated().any():
        raise ValueError("Duplicate target month")
    return result


def forest():
    from scripts.train_multivariate_ec import pipeline
    return pipeline().set_params(randomforestregressor__n_jobs=1)


def fit_forest(train: pd.DataFrame, future: pd.DataFrame, columns: list[str],
               y: np.ndarray, weight: np.ndarray | None = None) -> np.ndarray:
    model = forest()
    args = {"randomforestregressor__sample_weight": weight} if weight is not None else {}
    model.fit(train[columns], y, **args)
    return np.maximum(0, model.predict(future[columns]))


def log_candidates(known: pd.DataFrame, future: pd.DataFrame, columns: list[str]):
    y = known.conductivity_mS_per_m.to_numpy(dtype=float)
    z = np.log1p(y)
    ncal = max(36, int(round(len(known) * .2)))
    early, calibration = known.iloc[:-ncal], known.iloc[-ncal:]
    calibrator = forest().fit(early[columns], np.log1p(early.conductivity_mS_per_m))
    residual = np.log1p(calibration.conductivity_mS_per_m.to_numpy()) - calibrator.predict(calibration[columns])
    smear = float(np.exp(residual).mean())
    fitted = forest().fit(known[columns], z)
    log_forecast = fitted.predict(future[columns])
    return np.maximum(0, np.expm1(log_forecast)), np.maximum(0, np.exp(log_forecast) * smear - 1), smear


def inverse_q_hybrid(known: pd.DataFrame, future: pd.DataFrame, columns: list[str]):
    def add_inverse(frame):
        copy = frame.copy()
        if copy.kratie_q_t2.isna().any() or (copy.kratie_q_t2 <= 0).any():
            raise ValueError("Inverse Q needs complete positive Kratie flow")
        copy["inverse_q_1000"] = 1000.0 / copy.kratie_q_t2
        return copy
    known, future = add_inverse(known), add_inverse(future)
    physical = ["inverse_q_1000", "tc_stage_t2", "rainfall_mm", "month_sin", "month_cos"]
    model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0))
    y = known.conductivity_mS_per_m.to_numpy(dtype=float)
    model.fit(known[physical], np.log1p(y))
    base_train = np.expm1(model.predict(known[physical]))
    base_future = np.expm1(model.predict(future[physical]))
    residual = forest().fit(known[columns], y - base_train)
    return np.maximum(0, base_future + residual.predict(future[columns]))


def conformal_upper(known: pd.DataFrame, future: pd.DataFrame,
                    baseline: np.ndarray, columns: list[str]):
    # A chronological split is an empirical audit; time-series exchangeability
    # and a formal future-coverage guarantee are not established.
    ncal = min(120, max(36, len(known) // 4))
    early, calibration = known.iloc[:-ncal], known.iloc[-ncal:]
    model = forest().fit(early[columns], early.conductivity_mS_per_m)
    errors = (calibration.conductivity_mS_per_m.to_numpy(dtype=float) -
              model.predict(calibration[columns]))
    dry = calibration.month_start.dt.month.isin([12, 1, 2, 3, 4]).to_numpy()
    dry_errors = errors[dry]
    if len(dry_errors) < 15:
        raise ValueError("Too few dry-season calibration labels")
    rank = min(len(dry_errors), int(np.ceil((len(dry_errors) + 1) * .9))) - 1
    q = max(0.0, float(np.sort(dry_errors)[rank]))
    upper = baseline + q
    return upper, q, len(dry_errors)


def evaluate(root: Path, output: Path) -> None:
    from scripts.evaluate_frozen_ec_gap import EXPERIMENTS, freeze_training
    from scripts.evaluate_frozen_ec_gap_remedies import CANDIDATES
    from scripts.experiment_ec_long_hydrology import data_matrix

    original = pd.read_csv(root / "outputs/frozen_ec_remedies_20261108/predictions.csv")
    columns = CANDIDATES["WeatherHydrology"]
    months = data_matrix(5).month_start
    recent = recent_daily_features(root, months)
    output.mkdir(parents=True, exist_ok=True)
    recent.to_csv(output / "recent_daily_features.csv", index=False)
    rows, calib = [], []
    for delay in (5, 35):
        frame = data_matrix(delay).merge(recent, on="month_start", validate="one_to_one")
        for experiment, (start, end) in EXPERIMENTS.items():
            known = freeze_training(frame, start, delay)
            future = frame[frame.month_start.between(start, end)].copy()
            published = original[(original.experiment == experiment) &
                                 (original.ec_delay_days == delay)].sort_values("target_month")
            if (len(future) != len(published) or
                    future.month_start.dt.strftime("%Y-%m-%d").tolist() != published.target_month.tolist() or
                    not np.allclose(future.conductivity_mS_per_m, published.actual_mS_m, rtol=0, atol=1e-8)):
                raise ValueError("Frozen cohort differs from published research")
            y = known.conductivity_mS_per_m.to_numpy(dtype=float)
            baseline = fit_forest(known, future, columns, y)
            if not np.allclose(baseline, published.WeatherHydrology, rtol=0, atol=1e-8):
                raise ValueError("RF baseline differs from published frozen model")
            weighted = fit_forest(known, future, columns, y,
                                  np.where(y >= 100, 5.0, 1.0))
            trigger = (future.month_start.dt.month.isin([1, 2, 3, 4, 5]).to_numpy() &
                       future.kratie_q_ratio_t2.lt(.75).to_numpy())
            switched = np.where(trigger, weighted, baseline)
            trigger_085 = (future.month_start.dt.month.isin([1, 2, 3, 4, 5]).to_numpy() &
                           future.kratie_q_ratio_t2.lt(.85).to_numpy())
            switched_085 = np.where(trigger_085, weighted, baseline)
            gb = make_pipeline(SimpleImputer(strategy="median"),
                               GradientBoostingRegressor(loss="huber", alpha=.9,
                                   n_estimators=200, max_depth=3,
                                   learning_rate=.03, min_samples_leaf=10,
                                   subsample=.8, random_state=42))
            gb.fit(known[columns], y)
            switched_gb = np.where(trigger, weighted, np.maximum(0, gb.predict(future[columns])))
            log_raw, log_smear, smear = log_candidates(known, future, columns)
            hybrid = inverse_q_hybrid(known, future, columns)
            recent_raw = fit_forest(known, future, columns + list(RECENT), y)
            recent_pred = np.where(future.recent_complete.to_numpy(), recent_raw, baseline)
            upper, correction, calibration_n = conformal_upper(known, future, baseline, columns)
            record = pd.DataFrame(dict(experiment=experiment, ec_delay_days=delay,
                target_month=published.target_month.to_numpy(),
                actual_mS_m=future.conductivity_mS_per_m.to_numpy(),
                q_ratio=future.kratie_q_ratio_t2.to_numpy(),
                recent_complete=future.recent_complete.to_numpy(),
                regime_trigger=trigger, regime_trigger_085=trigger_085, baseline=baseline,
                regime_weighted=switched, regime_weighted_085=switched_085,
                regime_gb_weighted=switched_gb,
                rf_log=log_raw, rf_log_smear=log_smear,
                ridge_inverse_q_residual_rf=hybrid, rf_recent_daily=recent_pred,
                conformal_upper=upper))
            rows.append(record)
            calib.append(dict(experiment=experiment, ec_delay_days=delay,
                log_smear_factor=smear, dry_calibration_n=calibration_n,
                conformal_correction_mS_m=correction,
                regime_trigger_months=int(trigger.sum()),
                regime_trigger_085_months=int(trigger_085.sum()),
                recent_train_complete=int(known.recent_complete.sum()),
                recent_train_total=len(known)))
            print("completed", experiment, delay, flush=True)
    predictions = pd.concat(rows, ignore_index=True)
    score = []
    for (experiment, delay), part in predictions.groupby(["experiment", "ec_delay_days"]):
        actual = part.actual_mS_m.to_numpy(dtype=float)
        for name in LABELS:
            forecast = part[name].to_numpy(dtype=float)
            errors = forecast - actual
            high = actual >= 100
            score.append(dict(experiment=experiment, ec_delay_days=int(delay), model=name,
                n=len(part), mae_mS_m=float(np.abs(errors).mean()),
                rmse_mS_m=float(np.sqrt(np.mean(errors ** 2))),
                bias_mS_m=float(errors.mean()),
                high_n=int(high.sum()),
                high_mae_mS_m=float(np.abs(errors[high]).mean()) if high.any() else None,
                false_alerts_100=int(((forecast >= 100) & ~high).sum()),
                missed_high_100=int(((forecast < 100) & high).sum())))
    predictions.to_csv(output / "predictions.csv", index=False)
    pd.DataFrame(score).to_csv(output / "metrics.csv", index=False)
    pd.DataFrame(calib).to_csv(output / "calibration.csv", index=False)
    interval = []
    for (experiment, delay), part in predictions.groupby(["experiment", "ec_delay_days"]):
        dry = part.target_month.str.slice(5, 7).astype(int).isin([12, 1, 2, 3, 4])
        for label, cohort in (("all", part), ("dry_dec_apr", part[dry])):
            interval.append(dict(experiment=experiment, ec_delay_days=int(delay), subset=label,
                n=len(cohort), upper_coverage=float((cohort.actual_mS_m <= cohort.conformal_upper).mean()),
                mean_upper_minus_point_mS_m=float((cohort.conformal_upper-cohort.baseline).mean())))
    pd.DataFrame(interval).to_csv(output / "interval_audit.csv", index=False)
    sources = [root / "data/research/mrc_ec_monthly_samples.csv",
               root / "data/external/multivariate_weather/manifest.json",
               root / "outputs/frozen_ec_remedies_20261108/predictions.csv",
               next((root / "data/external/mrc_kratie_discharge_20261029").glob(
                   "014901_Discharge_Calculated daily discharge_*.csv")),
               next((root / "data/external/tien_manual_long_20261029").glob(
                   "019803_Water_Level_Manual_*.csv"))]
    manifest = dict(protocol="FROZEN_MYTHO_MATH_PHYSICS_RESEARCH_V1",
        issue="day 6 of month before target", daily_assumed_publication_lag_days=5,
        recent_window="7 complete daily values ending issue minus 6 days, plus previous 7 days; one-day intraday buffer beyond assumed 5-day source delay",
        recent_missing_rule="If either 7-day window lacks complete Kratie or Tan Chau data, use published baseline for that target month",
        cohort="My Tho EC frozen before each 24/36-month outage; weather/hydrology t-2 otherwise unchanged",
        candidates=list(LABELS), regime_rule="Jan-May and Kratie t-2 ratio <0.75 or <0.85: RF weight5; normal: RF or GB Huber",
        log_smear="chronological last 20 percent of known labels estimate exp(log1p residual) factor; RF refit on all known",
        conformal="last up-to-120 known months as chronological calibration, dry-season positive residual 90th percentile; empirical only",
        limitations=["Source publication vintages are unknown; day +5 is an assumption.",
                     "All three historical windows were already inspected; no blind model selection.",
                     "Time-series exchangeability is unverified; conformal upper is not a formal future-coverage guarantee.",
                     "Research only; no deployed model, forecast UI, or gate rule changes."],
        sklearn_version=sklearn.__version__,
        source_sha256={path.relative_to(root).as_posix(): sha(path) for path in sources},
        output_sha256={name: sha(output / name) for name in ("predictions.csv", "metrics.csv", "calibration.csv", "interval_audit.csv", "recent_daily_features.csv")})
    (output / "protocol.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(pd.DataFrame(score).query("ec_delay_days == 5").to_string(index=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    sys.path.insert(0, str(root))
    evaluate(root, args.output or root / "outputs/ec_math_physics_20261108")


if __name__ == "__main__":
    main()
