"""As-of ablation of long MRC water-level histories and robust EC models.

Research-only.  Manual level series are distinct gauges; monthly summaries of
one gauge never substitute for discharge or a verified hydraulic boundary.
"""
from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_upstream_asof import OWN, build_matrix
from scripts.train_multivariate_ec import FEATURES as WEATHER_FEATURES, pipeline as old_pipeline

LONG = ROOT / "data/external/tien_manual_long_20261029"
HISTORY = ROOT / "data/external/tien_manual_history_20261029"
RECENT = ROOT / "data/external/tien_multisite_supplement_20261029"
RECENT_TC = ROOT / "data/external/tien_manual_2024_2026_20261029"
KRATIE = ROOT / "data/external/mrc_kratie_discharge_20261029"
BASE = ROOT / "outputs/ec_upstream_asof_20261029/predictions.csv"
OUT = ROOT / "outputs/ec_long_hydrology_20261029"
STAGE = ["tc_stage_t2", "tc_stage3_t2", "mt_stage_t2", "mt_stage3_t2",
         "vk_stage_t2", "vk_stage3_t2", "vn_stage_t2", "vn_stage3_t2"]
FLOW = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2"]


def monthly_stage(code: str, prefix: str) -> pd.DataFrame:
    paths = [next(folder.glob(f"{code}_Water_Level_Manual_*.csv"))
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
    # The 3-month median ends in t-2 and uses observed months only.
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


def run(delay=5):
    part = data_matrix(delay)
    prior = pd.read_csv(BASE)
    scenario = f"EC_MONTH_END_PLUS_{delay}D"
    prior = prior[(prior.station == "MYTHO") & (prior.scenario == scenario)]
    output = []
    candidates = {
        "RF_tc_stage": ("rf", OWN + STAGE[:2]),
        "RF_all_stage": ("rf", OWN + STAGE),
        "RF_log_tc_stage": ("rf_log", OWN + STAGE[:2]),
        "RF_log_all_stage": ("rf_log", OWN + STAGE),
        "ET_all_stage": ("extra", OWN + STAGE),
        "HGB_log_all_stage": ("hgb_log", OWN + STAGE),
        "RF_log_own": ("rf_log", OWN),
        "RF_kratie": ("rf", OWN + FLOW),
        "RF_tc_stage_kratie": ("rf", OWN + STAGE[:2] + FLOW),
        "ET_all_stage_kratie": ("extra", OWN + STAGE + FLOW),
        "HGB_log_all_stage_kratie": ("hgb_log", OWN + STAGE + FLOW),
    }
    for _, target in part.iterrows():
        year = target.month_start.year
        if year < 2015 or year > 2023:
            continue
        issue = target.issue_date
        train = part[(part.month_start < target.month_start) &
                     (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
                     (part.weather_available_at <= issue)]
        if len(train) < 96:
            raise ValueError("Too few known labels")
        if available_date_for(target.weather_month, 5) > issue:
            raise ValueError("Future water level")
        old = prior[prior.target_month == target.month_start.strftime("%Y-%m-%d")]
        if len(old) == 1:
            old_rf = float(old.iloc[0].old_RF)
            persistence = float(old.iloc[0].Persistence)
            climate = float(old.iloc[0].MonthlyClimatology)
        elif len(old) == 0 and year <= 2018:
            old_rf = max(0.0, float(old_pipeline().fit(
                train[WEATHER_FEATURES], train.conductivity_mS_per_m).predict(
                    target[WEATHER_FEATURES].to_frame().T)[0]))
            persistence = float(train.conductivity_mS_per_m.iloc[-1])
            climate = float(train.loc[train.month_start.dt.month == target.month_start.month,
                                      "conductivity_mS_per_m"].mean())
        else:
            raise ValueError("Cohort mismatch")
        row = dict(target_month=target.month_start.strftime("%Y-%m-%d"), issue_date=str(issue),
                   split="development_2015_2018" if year <= 2018 else
                         "validation_2019_2021" if year <= 2021 else "retrospective_2022_2023",
                   actual=float(target.conductivity_mS_per_m), train_n=len(train),
                   tc_stage_t2=target.tc_stage_t2,
                   RF_old=old_rf, Persistence=persistence, MonthlyClimatology=climate)
        for name, (kind, columns) in candidates.items():
            row[name] = predictor(kind, columns, train, target)
        output.append(row)
        if target.month_start.month == 12:
            print("completed", year, flush=True)
    pred = pd.DataFrame(output)
    if len(pred) != 108 or pred.duplicated("target_month").any():
        raise ValueError("Bad cohort")
    scores = []
    for split, group in pred.groupby("split"):
        for model in ["RF_old", "Persistence", "MonthlyClimatology", *candidates]:
            if group[model].isna().any():
                continue
            err = group[model].to_numpy() - group.actual.to_numpy()
            high = group.actual >= 100
            scores.append(dict(split=split, model=model, n=len(group),
                mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err**2))),
                high_n=int(high.sum()), high_mae=float(np.abs(err[high]).mean()) if high.any() else None))
    output_dir = OUT if delay == 5 else OUT / f"ec_delay_{delay}d"
    output_dir.mkdir(parents=True, exist_ok=True)
    pred.to_csv(output_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(scores).to_csv(output_dir / "metrics.csv", index=False, encoding="utf-8-sig")
    (output_dir / "protocol.json").write_text(json.dumps(dict(issue="day 6 of preceding month",
        ec_delay_days=delay, water_level_month="target t-2", water_level_assumed_delay_days=5,
        kratie_flow_month="target t-2; same-month prior 15-year median for ratio",
        manual_stage_requirement="at least 20 observed daily medians/month; 3-month median at least 2 months",
        target="single monthly My Tho EC sample, not monthly mean", source_qa="UNVERIFIED",
        warning="Historical publication vintage unavailable. Stage is not discharge. 2022-23 retrospective period already inspected."),
        indent=2), encoding="utf-8")
    print(pd.DataFrame(scores).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=int, choices=[5, 35], default=5)
    run(parser.parse_args().delay)
