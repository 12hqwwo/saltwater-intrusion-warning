"""Leakage-controlled monthly EC feature and upstream ablation, issue day 6.

Research only: source snapshots have no historical publication vintages.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import (
    TARGET_PATH, WEATHER_MANIFEST, available_date_for, issue_date_for,
    split_for, training_frame,
)

OUT = ROOT / "outputs/ec_upstream_asof_20261029"
EXTRA = ROOT / "data/external/ec_feature_research_20261019"
BASELINE = ROOT / "outputs/multivariate_ec_asof_20261029/asof_predictions.csv"
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


def fit_predict(algorithm, x_train, y_train, x_test):
    if algorithm == "RF":
        model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                              RandomForestRegressor(n_estimators=100, max_depth=6,
                                                    min_samples_leaf=4, random_state=42, n_jobs=-1))
    else:
        model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                              StandardScaler(), Ridge(alpha=100.0))
    model.fit(x_train, y_train)
    return max(0.0, float(model.predict(x_test)[0]))


def run():
    all_predictions = []
    old = pd.read_csv(BASELINE)
    for delay, scenario in [(5, "EC_MONTH_END_PLUS_5D"), (35, "EC_MONTH_END_PLUS_35D")]:
        matrix = build_matrix(delay)
        for station, part in matrix.groupby("station"):
            part = part.sort_values("month_start")
            for _, target in part.iterrows():
                split = split_for(target.month_start.date())
                if split is None:
                    continue
                issue = target.issue_date
                train = part[(part.month_start < target.month_start) &
                             (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
                             (part.weather_available_at <= issue)]
                if len(train) < 96:
                    raise ValueError("Too few training labels")
                baseline = old[(old.station == station) & (old.scenario == scenario) &
                               (old.target_month == target.month_start.strftime("%Y-%m-%d"))]
                if len(baseline) != 1:
                    raise ValueError("Missing matched baseline")
                b = baseline.iloc[0]
                if b.issue_date_local != str(issue) or b.actual_mS_m != target.conductivity_mS_per_m:
                    raise ValueError("Protocol or target mismatch")
                record = dict(station=station, scenario=scenario, split=split,
                              target_month=target.month_start.strftime("%Y-%m-%d"), issue_date=str(issue),
                              actual=float(target.conductivity_mS_per_m), train_n=len(train),
                              last_train_month=train.month_start.max().strftime("%Y-%m-%d"),
                              tc_source_month=(target.tc_source_month.strftime("%Y-%m-%d") if station == "MYTHO" and pd.notna(target.tc_source_month) else ""),
                              old_RF=float(b.RandomForest), Persistence=float(b.Persistence),
                              SeasonalNaive=float(b.SeasonalNaive), MonthlyClimatology=float(b.MonthlyClimatology))
                for algorithm in ["RF", "RIDGE"]:
                    record[f"{algorithm}_own"] = fit_predict(algorithm, train[OWN],
                        train.conductivity_mS_per_m, target[OWN].to_frame().T)
                    if station == "MYTHO":
                        cols = OWN + UPSTREAM
                        record[f"{algorithm}_upstream"] = fit_predict(algorithm, train[cols],
                            train.conductivity_mS_per_m, target[cols].to_frame().T)
                all_predictions.append(record)
            print("completed", station, scenario, flush=True)
    pred = pd.DataFrame(all_predictions)
    if len(pred) != 240:
        raise ValueError("Wrong prediction cohort")
    model_cols = ["old_RF", "Persistence", "SeasonalNaive", "MonthlyClimatology",
                  "RF_own", "RIDGE_own", "RF_upstream", "RIDGE_upstream"]
    scores = []
    for (station, scenario, split), group in pred.groupby(["station", "scenario", "split"]):
        for model in model_cols:
            if group[model].isna().any():
                continue
            e = group[model].to_numpy()-group.actual.to_numpy()
            scores.append(dict(station=station, scenario=scenario, split=split, model=model,
                               n=len(group), mae=float(np.abs(e).mean()),
                               rmse=float(np.sqrt(np.mean(e**2))), bias=float(e.mean()),
                               dry_mae=float(np.abs(e[group.target_month.str.slice(5,7).astype(int).isin([12,1,2,3,4])]).mean())))
    metrics = pd.DataFrame(scores)
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(OUT / "predictions.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT / "metrics.csv", index=False, encoding="utf-8-sig")
    selection = metrics[metrics.split == "validation"].sort_values(["station", "scenario", "mae", "model"]).groupby(["station", "scenario"]).first().reset_index()
    selection.to_csv(OUT / "selection.csv", index=False, encoding="utf-8-sig")
    (OUT / "protocol.json").write_text(json.dumps(dict(issue="day 6 of preceding month",
        ec_delay_days=[5,35], weather_delay_days=5, weather_month="target t-2",
        validation="2019-2021", retrospective_check="2022-2023 previously inspected",
        feature_source="MRC EC + ERA5 manifest + ERA5 extra; upstream is lagged Tan Chau EC only",
        warning="No observed travel-time calibration, branch flow, contemporaneous salinity or historical source vintages. Upstream ablation is not proof of physical propagation."), indent=2), encoding="utf-8")
    print("SELECTION\n", selection[["station","scenario","model","mae"]].to_string(index=False))
    print("RETROSPECTIVE\n", metrics[metrics.split != "validation"][["station","scenario","model","mae"]].to_string(index=False))
    return pred, metrics


if __name__ == "__main__":
    run()
