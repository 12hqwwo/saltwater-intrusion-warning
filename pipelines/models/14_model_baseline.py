"""Compare Seasonal Naive, SARIMA, and Random Forest with a time split.

Evaluation uses monthly rows from 2022-01 through 2023-12. Missing or SUSPECT
EC targets are excluded from metrics, never imputed. A candidate model is
accepted only when its MAE is below the station's Seasonal Naive baseline.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd


warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
FEATURE_FILE = ROOT / "data" / "features" / "10_monthly_feature_v2.csv"
OUTPUT_FILE = ROOT / "data" / "models" / "15_model_comparison.csv"

TRAIN_END = "2018-12"
VALIDATION_END = "2021-12"
TEST_END = "2023-12"
EVALUATION_PROTOCOL = "time_split_rolling_one_step_features"


def load_features(station: str) -> pd.DataFrame:
    frame = pd.read_csv(FEATURE_FILE)
    frame = frame[frame["location_id"].eq(station)].sort_values("year_month").copy()
    frame["year_month_dt"] = pd.to_datetime(frame["year_month"], format="%Y-%m")
    return frame


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int]:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    actual = y_true[mask]
    predicted = y_pred[mask]
    if not len(actual):
        return {"n_test": 0, "MAE": np.nan, "RMSE": np.nan}
    return {
        "n_test": int(len(actual)),
        "MAE": round(float(np.mean(np.abs(actual - predicted))), 4),
        "RMSE": round(float(np.sqrt(np.mean((actual - predicted) ** 2))), 4),
    }


def run_sarima_rolling(history: pd.Series, test: pd.DataFrame) -> tuple[np.ndarray, str]:
    """One-step rolling forecasts; missing observations remain missing in state updates."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        monthly_history = history.asfreq("MS")
        model = SARIMAX(
            monthly_history,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 0, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fitted = model.fit(disp=False, maxiter=200)
        predictions: list[float] = []
        for _, row in test.iterrows():
            forecast = np.asarray(fitted.forecast(steps=1)).reshape(-1)
            predictions.append(float(forecast[0]) if len(forecast) else np.nan)
            # ndarray avoids pandas column-name mismatches across statsmodels versions.
            update = np.asarray([row["ec_target"]], dtype=float)
            fitted = fitted.append(update, refit=False)
        return np.asarray(predictions), "OK"
    except Exception as exc:  # retain a diagnostic row instead of fabricating metrics
        return np.full(len(test), np.nan), f"ERROR: {type(exc).__name__}: {exc}"


def eligible_rf_features(train: pd.DataFrame) -> list[str]:
    columns = [
        "ec_lag_1",
        "ec_lag_2",
        "ec_lag_3",
        "ec_lag_12",
        "month",
        "rainfall",
        "temperature",
        "wind",
        "dahiti",
    ]
    if (
        "discharge_quality_flag" in train
        and train["discharge_quality_flag"].eq("VERIFIED").any()
    ):
        columns.extend(["discharge_mean", "discharge_max"])
    if "tide_quality_flag" in train and train["tide_quality_flag"].eq("VERIFIED").any():
        columns.extend(["tide_mean", "tide_max", "tide_range"])
    return [column for column in columns if column in train and train[column].notna().any()]


def run_random_forest(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, str, int]:
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.impute import SimpleImputer

        features = eligible_rf_features(train)
        training_rows = train[train["ec_target"].notna()].copy()
        if len(training_rows) < 24 or not features:
            return np.full(len(test), np.nan), "ERROR: insufficient training data/features", len(features)
        imputer = SimpleImputer(strategy="median")
        x_train = imputer.fit_transform(training_rows[features])
        x_test = imputer.transform(test[features])
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            random_state=42,
            # A single worker is deterministic and avoids Windows sandbox process errors.
            n_jobs=1,
        )
        model.fit(x_train, training_rows["ec_target"])
        return model.predict(x_test), "OK", len(features)
    except Exception as exc:
        return np.full(len(test), np.nan), f"ERROR: {type(exc).__name__}: {exc}", 0


def result_row(
    model: str,
    station: str,
    actual: np.ndarray,
    predicted: np.ndarray,
    train_n: int,
    validation_n: int,
    status: str,
    feature_count: int,
) -> dict[str, object]:
    return {
        "model": model,
        "station": station,
        **compute_metrics(actual, predicted),
        "train_n": train_n,
        "validation_n": validation_n,
        "test_window_rows": len(actual),
        "train_end": TRAIN_END,
        "validation_end": VALIDATION_END,
        "test_end": TEST_END,
        "evaluation_protocol": EVALUATION_PROTOCOL,
        "feature_count": feature_count,
        "run_status": status,
    }


def run_station(station: str) -> list[dict[str, object]]:
    frame = load_features(station)
    train = frame[frame["year_month"].le(TRAIN_END)]
    validation = frame[
        frame["year_month"].gt(TRAIN_END) & frame["year_month"].le(VALIDATION_END)
    ]
    train_validation = frame[frame["year_month"].le(VALIDATION_END)]
    test = frame[
        frame["year_month"].gt(VALIDATION_END) & frame["year_month"].le(TEST_END)
    ].copy()
    actual = test["ec_target"].to_numpy(dtype=float)
    train_n = int(train["ec_target"].notna().sum())
    validation_n = int(validation["ec_target"].notna().sum())

    naive_predictions = test["ec_lag_12"].to_numpy(dtype=float)
    history = train_validation.set_index("year_month_dt")["ec_target"]
    sarima_predictions, sarima_status = run_sarima_rolling(history, test)
    rf_predictions, rf_status, feature_count = run_random_forest(train_validation, test)

    # Compare every successful model on exactly the same verified target months.
    prediction_sets = [naive_predictions]
    if sarima_status == "OK":
        prediction_sets.append(sarima_predictions)
    if rf_status == "OK":
        prediction_sets.append(rf_predictions)
    common_mask = np.isfinite(actual)
    for predictions in prediction_sets:
        common_mask &= np.isfinite(predictions)
    comparable_actual = np.where(common_mask, actual, np.nan)

    rows = []
    for model_name, predictions, status, count in (
        ("SeasonalNaive", naive_predictions, "OK", 1),
        ("SARIMA", sarima_predictions, sarima_status, 1),
        ("RandomForest", rf_predictions, rf_status, feature_count),
    ):
        rows.append(
            result_row(
                model_name,
                station,
                comparable_actual,
                predictions,
                train_n,
                validation_n,
                status,
                count,
            )
        )

    baseline_mae = rows[0]["MAE"]
    baseline_rmse = rows[0]["RMSE"]
    for row in rows:
        mae = row["MAE"]
        rmse = row["RMSE"]
        is_candidate = row["model"] != "SeasonalNaive"
        better = bool(
            is_candidate
            and np.isfinite(float(mae))
            and np.isfinite(float(rmse))
            and np.isfinite(float(baseline_mae))
            and np.isfinite(float(baseline_rmse))
            and float(mae) < float(baseline_mae)
            and float(rmse) < float(baseline_rmse)
        )
        row["better_than_baseline"] = better
        row["accepted"] = better and row["run_status"] == "OK"
    return rows


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for station in ("TanChau", "MyTho"):
        rows.extend(run_station(station))
    output = pd.DataFrame(rows)
    output.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(output.to_string(index=False))
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
