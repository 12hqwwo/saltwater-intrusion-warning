from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.backtest_protocols import (
    TARGET_PATH, WEATHER_MANIFEST, available_date_for, issue_date_for, training_frame,
)

LONG = ROOT / "data/external/tien_manual_long_20261029"
HISTORY = ROOT / "data/external/tien_manual_history_20261029"
RECENT = ROOT / "data/external/tien_multisite_supplement_20261029"
RECENT_TC = ROOT / "data/external/tien_manual_2024_2026_20261029"
KRATIE = ROOT / "data/external/mrc_kratie_discharge_20261029"
STAGE = ["tc_stage_t2", "tc_stage3_t2", "mt_stage_t2", "mt_stage3_t2",
         "vk_stage_t2", "vk_stage3_t2", "vn_stage_t2", "vn_stage3_t2"]
FLOW = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2"]
EXTRA = ROOT / "data/external/ec_feature_research_20261019"
OWN = ["month_sin", "month_cos", "rainfall_mm", "temperature_degC", "wind_source_units",
       "soil_t2", "wind_u_t2", "wind_v_t2", "ec_latest", "ec_previous", "ec_age_months",
       "ec_lag12", "ec_mean3", "ec_mean12"]
UPSTREAM = ["tc_latest", "tc_previous", "tc_age_months", "tc_lag12", "tc_mean3", "tc_mean12"]


def ec_features(series, target, issue, delay, prefix):
    available = pd.Series([available_date_for(t, delay) for t in series.index], index=series.index)
    known = series[(series.index < target) & (available <= issue)]
    last3 = known[known.index >= target - pd.DateOffset(months=3)]
    last12 = known[known.index >= target - pd.DateOffset(months=12)]
    return {f"{prefix}_latest": known.iloc[-1] if len(known) else np.nan,
            f"{prefix}_previous": known.iloc[-2] if len(known) > 1 else np.nan,
            f"{prefix}_age_months": ((target.year-known.index[-1].year)*12 + target.month-known.index[-1].month) if len(known) else np.nan,
            f"{prefix}_lag12": known.get(target-pd.DateOffset(months=12), np.nan),
            f"{prefix}_mean3": last3.mean(),
            f"{prefix}_mean12": last12.mean(),
            f"{prefix}_source_month": known.index[-1] if len(known) else pd.NaT,
            f"{prefix}_available_at": available.loc[known.index[-1]] if len(known) else None}


def build_matrix(delay):
    frame, _ = training_frame(TARGET_PATH, WEATHER_MANIFEST)
    frame = frame[frame.station.isin(['MYTHO', 'TANCHAU'])].copy()
    extra_rows = []
    for station, name in [("MYTHO", "MyTho"), ("TANCHAU", "TanChau")]:
        payload = json.loads((EXTRA / f"era5_extra_{name}.json").read_text(encoding="utf-8"))
        daily = pd.DataFrame(payload["daily"])
        daily["weather_month"] = pd.to_datetime(daily.time).dt.to_period("M").dt.to_timestamp()
        direction = np.deg2rad(daily.wind_direction_10m_dominant)
        daily["wind_u_t2"] = -daily.wind_speed_10m_mean * np.sin(direction)
        daily["wind_v_t2"] = -daily.wind_speed_10m_mean * np.cos(direction)
        grouped = daily.groupby("weather_month")
        month = grouped.agg(soil_t2=("soil_moisture_0_to_100cm_mean", "mean"),
                            wind_u_t2=("wind_u_t2", "mean"), wind_v_t2=("wind_v_t2", "mean"))
        count = grouped.size()
        month.loc[count.to_numpy() != month.index.days_in_month, :] = np.nan
        month["station"] = station
        extra_rows.append(month.reset_index())
    frame = frame.merge(pd.concat(extra_rows), on=["station", "weather_month"], how="left", validate="many_to_one")
    if frame[["soil_t2", "wind_u_t2", "wind_v_t2"]].isna().any().any():
        raise ValueError("Missing complete t-2 ERA5 extra weather")
    source = {s: group.set_index("month_start").conductivity_mS_per_m.sort_index()
              for s, group in frame.groupby("station")}
    rows = []
    for _, row in frame.iterrows():
        target = row.month_start
        issue = issue_date_for(target)
        weather_available = available_date_for(row.weather_month, 5)
        if weather_available > issue:
            raise ValueError("Future weather")
        own = ec_features(source[row.station], target, issue, delay, "ec")
        upstream = ec_features(source["TANCHAU"], target, issue, delay, "tc") if row.station == "MYTHO" else {}
        if any(x[f"{prefix}_available_at"] is not None and x[f"{prefix}_available_at"] > issue
               for prefix, x in [("ec", own), ("tc", upstream)] if x):
            raise ValueError("Future EC")
        rows.append({**row.to_dict(), **own, **upstream, "issue_date": issue,
                     "weather_available_at": weather_available})
    result = pd.DataFrame(rows)
    if result.duplicated(["station", "month_start"]).any():
        raise ValueError("Duplicate station-month")
    return result


def monthly_stage(code: str, prefix: str) -> pd.DataFrame:
    paths = [next(path for path in folder.glob(f"{code}_Water_Level_Manual_*.csv")
                  if not path.stem.endswith("_daily"))
             for folder in ([LONG, RECENT_TC] if code == "019803" else [LONG, HISTORY, RECENT])]
    frame = pd.concat([pd.read_csv(path, usecols=["observed_at", "value", "unit"])
                       for path in paths], ignore_index=True)
    if frame.observed_at.duplicated().any() or frame.unit.ne("m").any():
        raise ValueError(f"Bad manual level source {code}")
    local = pd.to_datetime(frame.observed_at)
    frame["day"] = local.dt.date
    daily = frame.groupby("day").value.median().to_frame("stage")
    daily["month"] = pd.to_datetime(daily.index).to_period("M").to_timestamp()
    grouped = daily.groupby("month").stage
    monthly = grouped.agg(["median", "count"])
    monthly["median"] = monthly["median"].where(monthly["count"] >= 20)
    index = pd.date_range("1985-01-01", "2026-10-01", freq="MS")
    stage = monthly["median"].reindex(index)
    stage3 = stage.rolling(3, min_periods=2).median()
    return pd.DataFrame({"weather_month": index, f"{prefix}_stage_t2": stage.values,
                         f"{prefix}_stage3_t2": stage3.values})


def monthly_kratie_flow() -> pd.DataFrame:
    path = next(KRATIE.glob("014901_Discharge_Calculated daily discharge_*.csv"))
    frame = pd.read_csv(path, usecols=["observed_at", "value", "unit"])
    if frame.observed_at.duplicated().any() or frame.unit.ne("m^3/s").any() or (frame.value < 0).any():
        raise ValueError("Bad Kratie discharge source")
    at = pd.to_datetime(frame.observed_at)
    frame["day"] = at.dt.date
    daily = frame.groupby("day").value.mean().to_frame("q")
    daily["month"] = pd.to_datetime(daily.index).to_period("M").to_timestamp()
    monthly = daily.groupby("month").q.agg(["mean", "count"])
    index = pd.date_range("1985-01-01", "2026-10-01", freq="MS")
    q = monthly["mean"].where(monthly["count"] >= 20).reindex(index)
    q3 = q.rolling(3, min_periods=2).mean()
    prior_same_month = pd.Series(index=index, dtype=float)
    for month in range(1, 13):
        series = q[q.index.month == month]
        prior_same_month.loc[series.index] = series.shift(1).rolling(15, min_periods=5).median().values
    ratio = (q / prior_same_month).clip(0, 5)
    return pd.DataFrame({"weather_month": index, "kratie_q_t2": q.values,
                         "kratie_q3_t2": q3.values, "kratie_q_ratio_t2": ratio.values})


def data_matrix(delay=5):
    matrix = build_matrix(delay)
    part = matrix[matrix.station.eq("MYTHO")].copy()
    for code, prefix in [("019803", "tc"), ("019804", "mt"),
                         ("985203", "vk"), ("980601", "vn")]:
        part = part.merge(monthly_stage(code, prefix), on="weather_month", how="left", validate="many_to_one")
    part = part.merge(monthly_kratie_flow(), on="weather_month", how="left", validate="many_to_one")
    return part.sort_values("month_start").reset_index(drop=True)


def fit_candidate_model(kind, columns, train):
    x = train[columns]
    y = train.conductivity_mS_per_m.to_numpy()
    if kind == "rf":
        base = RandomForestRegressor(n_estimators=100, max_depth=7,
            min_samples_leaf=3, max_features=0.8, random_state=42, n_jobs=-1)
        transform = False
    elif kind == "rf_log":
        base = RandomForestRegressor(n_estimators=100, max_depth=7,
            min_samples_leaf=3, max_features=0.8, random_state=42, n_jobs=-1)
        transform = True
    elif kind == "extra":
        base = ExtraTreesRegressor(n_estimators=100, max_depth=7,
            min_samples_leaf=3, max_features=0.8, random_state=42, n_jobs=-1)
        transform = False
    elif kind == "hgb_log":
        base = HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=8,
            min_samples_leaf=15, l2_regularization=10.0, random_state=42)
        transform = True
    else:
        raise ValueError(kind)
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True,
                                       keep_empty_features=True), base)
    model.fit(x, np.log1p(y) if transform else y)
    return model, transform


def predictor(kind, columns, train, target):
    model, transform = fit_candidate_model(kind, columns, train)
    xt = target[columns].to_frame().T
    value = float(model.predict(xt)[0])
    return max(0.0, float(np.expm1(value)) if transform else value)
