"""Create a research EC forecast using measured upstream flow, without recent EC."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.repositories.multivariate_inputs import get_weather_input
from scripts.experiment_ec_long_hydrology import (
    FLOW, STAGE, data_matrix, fit_candidate_model, monthly_kratie_flow, monthly_stage,
)
from scripts.experiment_ec_no_recent_label import WEATHER

TARGET = pd.Timestamp("2026-11-01")
WEATHER_MONTH = TARGET - pd.DateOffset(months=2)
EXTRA = ROOT / "data/external/ec_hydrology_current_20261029/era5_extra_MyTho_2026-09.json"
OUT = ROOT / "outputs/ec_hydrology_forecast_20261029"
COLUMNS = WEATHER + FLOW + STAGE[:2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_row():
    weather = get_weather_input("MYTHO", TARGET.strftime("%Y-%m"))
    if weather["input_month"] != WEATHER_MONTH.strftime("%Y-%m") or not weather["complete"]:
        raise ValueError("Current weather is not the required complete month t-2")
    if weather["assumed_available_at"] > "2026-10-06":
        raise ValueError("Weather would be unavailable at planned issue date")
    payload = json.loads(EXTRA.read_text(encoding="utf-8"))
    daily = pd.DataFrame(payload["daily"])
    if len(daily) != 30 or daily.time.min() != "2026-09-01" or daily.time.max() != "2026-09-30":
        raise ValueError("ERA5 extra month incomplete")
    direction = np.deg2rad(daily.wind_direction_10m_dominant)
    values = dict(month_sin=float(np.sin(2*np.pi*TARGET.month/12)),
                  month_cos=float(np.cos(2*np.pi*TARGET.month/12)),
                  rainfall_mm=float(weather["rainfall_mm"]),
                  temperature_degC=float(weather["temperature_degC"]),
                  wind_source_units=float(weather["wind_source_units"]),
                  soil_t2=float(daily.soil_moisture_0_to_100cm_mean.mean()),
                  wind_u_t2=float((-daily.wind_speed_10m_mean*np.sin(direction)).mean()),
                  wind_v_t2=float((-daily.wind_speed_10m_mean*np.cos(direction)).mean()))
    for frame in [monthly_kratie_flow(), monthly_stage("019803", "tc")]:
        selected = frame[frame.weather_month == WEATHER_MONTH]
        if len(selected) != 1:
            raise ValueError("No upstream hydrology for target month")
        values.update({k:float(v) for k,v in selected.iloc[0].items() if k != "weather_month"})
    if not all(np.isfinite(values[key]) for key in COLUMNS):
        raise ValueError("Incomplete current hydrology predictors")
    return pd.DataFrame([values])[COLUMNS], weather


def main():
    train = data_matrix(5)
    if train.month_start.max() != pd.Timestamp("2023-12-01"):
        raise ValueError("Unexpected EC training cutoff")
    current, weather = current_row()
    model, transformed = fit_candidate_model("rf", COLUMNS, train)
    if transformed:
        raise ValueError("Unexpected target transform")
    prediction = max(0.0, float(model.predict(current)[0]))
    results = pd.concat([pd.read_csv(ROOT / "outputs/ec_long_hydrology_20261029/no_recent_ec" /
                                      f"predictions_{delay}d.csv") for delay in [5,35]])
    result = {}
    for delay in [5,35]:
        cohort = results[results.delay == delay]
        result[str(delay)] = {split: dict(n=len(group),
            mae_mS_m=float(np.abs(group.RF_flow_stage_no_ec-group.actual).mean()),
            old_rf_mae_mS_m=float(np.abs(group.RF_old-group.actual).mean()))
            for split,group in cohort.groupby("split")}
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT / "mytho_no_recent_ec_model.joblib")
    pd.DataFrame([dict(station="MYTHO", target_month=TARGET.strftime("%Y-%m"),
        forecast_generated_at_utc=datetime.now(timezone.utc).isoformat(),
        hypothetical_issue_date="2026-10-06", weather_month="2026-09",
        predicted_ec_mS_m=prediction, status="RESEARCH_FORECAST_NO_POST_2023_EC_VALIDATION",
        model="RF_flow_stage_no_ec")]).to_csv(OUT / "forecast_2026_11.csv", index=False)
    sources = [ROOT / "data/research/mrc_ec_monthly_samples.csv", EXTRA,
        ROOT / "data/external/mrc_kratie_discharge_20261029/014901_Discharge_Calculated daily discharge_22a8130e.csv",
        ROOT / "data/external/tien_manual_long_20261029/019803_Water_Level_Manual_3bd17f3a.csv",
        ROOT / "data/external/tien_manual_2024_2026_20261029/019803_Water_Level_Manual_3bd17f3a.csv"]
    (OUT / "manifest.json").write_text(json.dumps(dict(
        model="RandomForestRegressor", parameters=dict(n_estimators=100, max_depth=7,
            min_samples_leaf=3, max_features=.8, random_state=42),
        feature_order=COLUMNS, feature_values=current.iloc[0].to_dict(),
        predicted_ec_mS_m=prediction, training_rows=len(train), training_through="2023-12",
        target_definition="one MRC EC sample in target month, not monthly mean",
        backtest=result, weather_source=weather, source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
        model_sha256=sha(OUT / "mytho_no_recent_ec_model.joblib"),
        warning="Research forecast. No observed EC after 2023, no historical publication vintages, MRC Q and level grades UNVERIFIED; no validated salt propagation or gate decision."),
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"predicted EC {prediction:.3f} mS/m; model saved to {OUT}")


if __name__ == "__main__":
    main()
