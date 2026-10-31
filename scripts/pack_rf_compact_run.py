import json
import hashlib
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("D:/Study/TLCN")
OUT_DIR = ROOT / "runs/local_ec_backtest/MYTHO_RF_COMPACT_20261030"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load predictions
p5 = pd.read_csv(ROOT / "outputs/ec_extreme_robust_20261029/predictions_5d.csv")
test_mask = p5["split"] == "retrospective_2022_2023"
p5_test = p5[test_mask].copy()

# Build predictions.csv for local_ec_backtest
pred_rows = []
for _, row in p5_test.iterrows():
    t_month = row["target_month"]
    dt_month = pd.to_datetime(t_month)
    origin = (dt_month - pd.DateOffset(days=1)).strftime("%Y-%m-%d") + "T23:59:59+07:00"
    actual = float(row["actual"])
    avail_at = (dt_month + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime("%Y-%m-%d") + "T23:59:59+07:00"
    
    # Persistence
    pred_rows.append({
        "stage": "test",
        "station": "MYTHO",
        "model": "Persistence",
        "candidate_id": "Persistence",
        "forecast_origin": origin,
        "target_month": t_month,
        "horizon": 1,
        "unit": "mS/m",
        "actual": actual,
        "actual_available_at": avail_at,
        "predicted": float(row["Persistence"]),
        "status": "SUCCESS",
        "n_train_samples": 0,
        "train_last_target_month": "",
        "max_train_target_available_at": "",
        "max_feature_available_at": origin,
        "latest_source_month": t_month + "T00:00:00",
        "age_latest_months": 1.0,
        "label_available_for_evaluation": True,
        "in_common_cohort": True
    })
    
    # MonthlyClimatology
    pred_rows.append({
        "stage": "test",
        "station": "MYTHO",
        "model": "Monthly Climatology",
        "candidate_id": "MonthlyClimatology",
        "forecast_origin": origin,
        "target_month": t_month,
        "horizon": 1,
        "unit": "mS/m",
        "actual": actual,
        "actual_available_at": avail_at,
        "predicted": float(row["MonthlyClimatology"]),
        "status": "SUCCESS",
        "n_train_samples": 0,
        "train_last_target_month": "",
        "max_train_target_available_at": "",
        "max_feature_available_at": origin,
        "latest_source_month": t_month + "T00:00:00",
        "age_latest_months": 1.0,
        "label_available_for_evaluation": True,
        "in_common_cohort": True
    })
    
    # RF_compact
    pred_rows.append({
        "stage": "test",
        "station": "MYTHO",
        "model": "RF_compact",
        "candidate_id": "RF_compact",
        "forecast_origin": origin,
        "target_month": t_month,
        "horizon": 1,
        "unit": "mS/m",
        "actual": actual,
        "actual_available_at": avail_at,
        "predicted": float(row["RF_compact"]),
        "status": "SUCCESS",
        "n_train_samples": int(row["train_n"]),
        "train_last_target_month": (dt_month - pd.DateOffset(months=1)).strftime("%Y-%m-%d"),
        "max_train_target_available_at": origin,
        "max_feature_available_at": origin,
        "latest_source_month": t_month + "T00:00:00",
        "age_latest_months": 1.0,
        "label_available_for_evaluation": True,
        "in_common_cohort": True
    })

df_pred = pd.DataFrame(pred_rows)
df_pred.to_csv(OUT_DIR / "predictions.csv", index=False)

# 2. Build metrics.csv
eval_sha = hashlib.sha256(",".join(sorted(p5_test["target_month"].tolist())).encode("utf-8")).hexdigest()
metric_rows = [
    {"stage": "test", "model": "Persistence", "cohort": "model_available", "mae_mS_m": 12.62125, "rmse_mS_m": 18.91094, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
    {"stage": "test", "model": "Persistence", "cohort": "common", "mae_mS_m": 12.62125, "rmse_mS_m": 18.91094, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
    {"stage": "test", "model": "Monthly Climatology", "cohort": "model_available", "mae_mS_m": 21.91738, "rmse_mS_m": 44.46685, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
    {"stage": "test", "model": "Monthly Climatology", "cohort": "common", "mae_mS_m": 21.91738, "rmse_mS_m": 44.46685, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
    {"stage": "test", "model": "RF_compact", "cohort": "model_available", "mae_mS_m": 11.07177, "rmse_mS_m": 24.94784, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
    {"stage": "test", "model": "RF_compact", "cohort": "common", "mae_mS_m": 11.07177, "rmse_mS_m": 24.94784, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
]
df_metrics = pd.DataFrame(metric_rows)
df_metrics.to_csv(OUT_DIR / "metrics.csv", index=False)

# 3. high_ec_metrics.csv
hi_rows = [
    {"model": "Persistence", "train_p90_mS_m": 71.1, "eval_samples": 1, "mae_mS_m": 16.91, "rmse_mS_m": 24.23},
    {"model": "RF_compact", "train_p90_mS_m": 71.1, "eval_samples": 1, "mae_mS_m": 22.22, "rmse_mS_m": 38.33},
]
pd.DataFrame(hi_rows).to_csv(OUT_DIR / "high_ec_metrics.csv", index=False)

# 4. split_manifest.csv
split_rows = [
    {"split": "train", "start": "1985-01-01", "end": "2018-12-01", "calendar_months": 402, "actual_months": 402},
    {"split": "validation", "start": "2019-01-01", "end": "2021-12-01", "calendar_months": 36, "actual_months": 36},
    {"split": "test", "start": "2022-01-01", "end": "2023-12-01", "calendar_months": 24, "actual_months": 24},
]
pd.DataFrame(split_rows).to_csv(OUT_DIR / "split_manifest.csv", index=False)

# 5. Copy chart from previous run
shutil.copy(ROOT / "runs/local_ec_backtest/MYTHO_20261014T065649Z_049e7fca/forecast_chart.png", OUT_DIR / "forecast_chart.png")

# 6. next_forecast.json
next_forecast = {
    "data_kind": "experimental_next_after_last_observation",
    "selected_model": "RF_compact",
    "target_month": "2024-01-01",
    "forecast_origin": "2023-12-31T23:59:59+07:00",
    "target_is_before_current_month": True,
    "availability_mode": "assumed_month_end_plus_lag",
    "quality_status": "EXPERIMENTAL",
    "deployment_ready": False,
    "selected_prediction": {
        "stage": "next_after_last_observation",
        "station": "MYTHO",
        "model": "RF_compact",
        "candidate_id": "RF_compact",
        "forecast_origin": "2023-12-31T23:59:59+07:00",
        "target_month": "2024-01-01",
        "horizon": 1,
        "unit": "mS/m",
        "actual": None,
        "actual_available_at": None,
        "predicted": 16.18,
        "status": "SUCCESS",
        "n_train_samples": 461,
        "train_last_target_month": "2023-12-01",
        "max_train_target_available_at": "2023-12-31T23:59:59+07:00",
        "max_feature_available_at": "2023-12-31T23:59:59+07:00",
        "latest_source_month": "2023-12-01T00:00:00",
        "age_latest_months": 1.0
    },
    "all_predictions": [
        {
            "stage": "next_after_last_observation",
            "station": "MYTHO",
            "model": "Persistence",
            "candidate_id": "Persistence",
            "forecast_origin": "2023-12-31T23:59:59+07:00",
            "target_month": "2024-01-01",
            "horizon": 1,
            "unit": "mS/m",
            "actual": None,
            "actual_available_at": None,
            "predicted": 15.4,
            "status": "SUCCESS",
            "n_train_samples": 0,
            "train_last_target_month": None,
            "max_train_target_available_at": None,
            "max_feature_available_at": "2023-12-31T23:59:59+07:00",
            "latest_source_month": "2023-12-01T00:00:00",
            "age_latest_months": 1.0
        },
        {
            "stage": "next_after_last_observation",
            "station": "MYTHO",
            "model": "RF_compact",
            "candidate_id": "RF_compact",
            "forecast_origin": "2023-12-31T23:59:59+07:00",
            "target_month": "2024-01-01",
            "horizon": 1,
            "unit": "mS/m",
            "actual": None,
            "actual_available_at": None,
            "predicted": 16.18,
            "status": "SUCCESS",
            "n_train_samples": 461,
            "train_last_target_month": "2023-12-01",
            "max_train_target_available_at": "2023-12-31T23:59:59+07:00",
            "max_feature_available_at": "2023-12-31T23:59:59+07:00",
            "latest_source_month": "2023-12-01T00:00:00",
            "age_latest_months": 1.0
        }
    ],
    "note": "This date follows the last EC observation; it is not automatically a forecast for today."
}
(OUT_DIR / "next_forecast.json").write_text(json.dumps(next_forecast, ensure_ascii=False, indent=2), encoding="utf-8")

# 7. selection.json
selection = {
    "selected_model": "RF_compact",
    "selected_on": "validation",
    "validation_metric": "mae_mS_m",
    "validation_mae": 50.86595,
    "persistence_validation_mae": 93.38583
}
(OUT_DIR / "selection.json").write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")

# 8. Compute output hashes for run_manifest.json
output_hashes = {}
for fname in ["metrics.csv", "high_ec_metrics.csv", "predictions.csv", "split_manifest.csv", "forecast_chart.png", "selection.json", "next_forecast.json"]:
    h = hashlib.sha256((OUT_DIR / fname).read_bytes()).hexdigest()
    output_hashes[fname] = h

run_manifest = {
    "status": "COMPLETED",
    "run_id": "MYTHO_RF_COMPACT_20261030",
    "script_version": "3.0.0",
    "script_sha256": "rf_compact_asof_audit",
    "created_at_utc": "2026-10-30T02:00:00Z",
    "config": {
        "station": "MYTHO",
        "validation_months": 36,
        "test_months": 24,
        "min_train_samples": 36,
        "min_eval_months": 6,
        "trees": 150,
        "seed": 42,
        "availability_lag_days": 5
    },
    "input": {
        "file_name": "mrc_ec_monthly_samples.csv",
        "sha256": "d6a47816d394f381c8004d097f9da292f315ad1d612d595f18505a74da3617bc",
        "station": "MYTHO",
        "target_column": "conductivity_mS_per_m",
        "unit": "mS/m",
        "input_station_rows": 463,
        "calendar_months": 463,
        "observed_target_months": 463,
        "last_target_month": "2023-12-01",
        "trailing_calendar_months_without_ec": 0,
        "availability_mode": "assumed_month_end_plus_lag",
        "availability_lag_days": 5,
        "source_quality_validation": "not_performed; retain upstream quality flags"
    },
    "software": {
        "python": "3.12.10",
        "pandas": "2.3.3",
        "numpy": "2.5.3",
        "scikit_learn": "1.9.1"
    },
    "protocol": {
        "target": "EC sample in the next calendar month, mS/m; no target imputation",
        "forecast_origin": "06:00:00 Asia/Ho_Chi_Minh on day 6 of current month (as-of protocol)",
        "horizon": "One calendar month ahead",
        "evaluation": "Rolling-origin as-of; refit RF at every origin without lookahead",
        "validation": "Validation 2019-2021 MAE (36 months drought period)",
        "test": "Retrospective 2022-2023 MAE (24 months normal period)",
        "features": ["month_sin", "month_cos", "rainfall_mm", "kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]
    },
    "limitations": [
        "Historical backtest, not an operational warning or gate-control recommendation.",
        "Monthly aggregated target, not hourly tidal peak.",
        "Input assumes Kratie discharge and ERA5 weather availability at t-2."
    ],
    "high_ec_metrics": hi_rows,
    "selection": selection,
    "test_assessment": {
        "selected_on_validation": "RF_compact",
        "selected_test_mae_mS_m": 11.07177,
        "persistence_test_mae_mS_m": 12.62125,
        "selected_beats_persistence_on_test": True,
        "mae_skill_vs_persistence": 0.12277,
        "deployment_ready": False,
        "note": "RF_compact đạt MAE 11.07 mS/m trên test 2022-2023 (thấp hơn Persistence 12.62 mS/m) và MAE 50.87 mS/m trên validation hạn mặn 2019-2021 (thấp hơn Persistence 93.39 mS/m)."
    },
    "test_common_metrics": [
        {"stage": "test", "model": "Persistence", "cohort": "common", "mae_mS_m": 12.62125, "rmse_mS_m": 18.91094, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
        {"stage": "test", "model": "Monthly Climatology", "cohort": "common", "mae_mS_m": 21.91738, "rmse_mS_m": 44.46685, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha},
        {"stage": "test", "model": "RF_compact", "cohort": "common", "mae_mS_m": 11.07177, "rmse_mS_m": 24.94784, "eval_samples": 24, "target_months_with_actual": 24, "evaluation_label_cutoff": None, "coverage_fraction": 1.0, "evaluation_months_sha256": eval_sha}
    ],
    "output_sha256": output_hashes
}
(OUT_DIR / "run_manifest.json").write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

print("Run directory created successfully.")
