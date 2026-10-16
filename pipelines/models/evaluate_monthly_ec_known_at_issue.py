"""Monthly EC one-step rolling evaluation using only prior EC and calendar month.

The earlier 14_model_baseline.py RF uses observed weather/DAHITI from the
target month. This separate run excludes those unavailable future-month
features and leaves prior outputs intact. No screening FES4 tide is joined.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import runpy

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer


ROOT = Path(__file__).resolve().parents[2]
BASELINE_SCRIPT = ROOT / "pipelines/models/14_model_baseline.py"
FEATURES = ROOT / "data/features/10_monthly_feature_v2.csv"
OUT = ROOT / "data/models/temporal_ec_known_at_issue_2022_2023"
STATIONS = ("TanChau", "MyTho")
TRAIN_END, VALIDATION_END, TEST_END = "2018-12", "2021-12", "2023-12"
RF_FEATURES = ("ec_lag_1", "ec_lag_2", "ec_lag_3", "ec_lag_12", "month")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def score(rows: list[dict], model: str, station: str) -> dict:
    selected = [row for row in rows if row["station"] == station and row["model"] == model
                and row["observed_ms_m"] != "" and row["predicted_ms_m"] != ""]
    error = np.asarray([float(row["predicted_ms_m"]) - float(row["observed_ms_m"])
                        for row in selected], dtype=float)
    return {"station": station, "model": model, "n_test": len(selected),
            "MAE_ms_m": round(float(np.mean(abs(error))), 4) if len(error) else "",
            "RMSE_ms_m": round(float(np.sqrt(np.mean(error ** 2))), 4) if len(error) else "",
            "train_end": TRAIN_END, "validation_end": VALIDATION_END,
            "test_end": TEST_END, "protocol": "rolling_one_step_previous_observed_EC"}


def main() -> None:
    old = runpy.run_path(str(BASELINE_SCRIPT))
    data = pd.read_csv(FEATURES)
    output = []
    for station in STATIONS:
        frame = data[data["location_id"].eq(station)].sort_values("year_month").copy()
        frame["date"] = pd.to_datetime(frame["year_month"], format="%Y-%m")
        history = frame[frame["year_month"].le(VALIDATION_END)].copy()
        test = frame[frame["year_month"].gt(VALIDATION_END) & frame["year_month"].le(TEST_END)].copy()
        if len(test) != 24 or any(col not in frame for col in RF_FEATURES):
            raise RuntimeError(f"Unexpected monthly test/feature structure at {station}")
        # EC lags are previous verified targets; current-month weather and
        # satellite values are excluded because they are unknown at issue time.
        training = history[history["ec_target"].notna()].copy()
        imputer = SimpleImputer(strategy="median")
        x_train = imputer.fit_transform(training[list(RF_FEATURES)])
        x_test = imputer.transform(test[list(RF_FEATURES)])
        forest = RandomForestRegressor(n_estimators=300, max_depth=8,
                                       min_samples_leaf=2, random_state=42, n_jobs=1)
        forest.fit(x_train, training["ec_target"])
        rf = forest.predict(x_test)
        sarima, status = old["run_sarima_rolling"](
            history.set_index("date")["ec_target"], test)
        if status != "OK":
            raise RuntimeError(f"SARIMA failed at {station}: {status}")
        naive = test["ec_lag_12"].to_numpy(dtype=float)
        actual = test["ec_target"].to_numpy(dtype=float)
        comparable = np.isfinite(actual) & np.isfinite(naive) & np.isfinite(sarima) & np.isfinite(rf)
        for i, (_, row) in enumerate(test.iterrows()):
            for model_name, predicted in (("SeasonalNaive", naive[i]),
                                          ("SARIMA", sarima[i]),
                                          ("RandomForestPriorEC", rf[i])):
                output.append({"station": station, "year_month": row["year_month"],
                               "model": model_name,
                               "observed_ms_m": round(float(actual[i]), 6) if comparable[i] else "",
                               "predicted_ms_m": round(float(predicted), 6) if comparable[i] else "",
                               "in_common_evaluation": bool(comparable[i])})
    metrics = [score(output, model, station) for station in STATIONS
               for model in ("SeasonalNaive", "SARIMA", "RandomForestPriorEC")]
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "temporal_predictions.csv", output)
    write_csv(OUT / "temporal_metrics.csv", metrics)
    (OUT / "manifest.json").write_text(json.dumps({
        "source_features": str(FEATURES), "source_model_script": str(BASELINE_SCRIPT),
        "train_window": f"1985-01..{TRAIN_END}",
        "validation_window": f"2019-01..{VALIDATION_END}",
        "final_initial_fit_through": VALIDATION_END,
        "test_window": f"2022-01..{TEST_END}",
        "forecast_horizon": "one month ahead; previous month's observed EC assumed available at issue time",
        "rf_allowed_features": RF_FEATURES,
        "rf_excluded": "target-month rainfall, temperature, wind, DAHITI, discharge, FES tide",
        "tide_screening_joined": False,
        "target_rule": "Only non-null verified EC in existing feature table; no imputed target evaluated",
        "comparison_rule": "All models scored on exactly the same valid target months per station",
        "mrc_source_grade": "Raw - Not Yet Reviewed / Unverified data in source metadata; internal VERIFIED denotes pipeline QA only",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
