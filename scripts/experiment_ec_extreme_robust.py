"""Controlled as-of My Tho EC ablation: compact hydrology and high-EC weighting.

No 2022-2023 result is used to choose a candidate. Research only; historical
release dates and 2024+ EC observations are unavailable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.experiment_ec_no_recent_label import WEATHER, FLOW, STAGE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_extreme_robust_20261029"
FULL = WEATHER + FLOW + STAGE[:2]
COMPACT = ["month_sin", "month_cos", "rainfall_mm", "kratie_q_t2",
           "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]
CANDIDATES = {
    "RF_compact": ("rf", COMPACT, 1.0),
    "RF_compact_weight3": ("rf", COMPACT, 3.0),
    "RF_compact_weight8": ("rf", COMPACT, 8.0),
    "RF_full_weight3": ("rf", FULL, 3.0),
    "ET_compact_weight3": ("extra", COMPACT, 3.0),
}


def fit_predict(kind, columns, high_weight, train, target):
    cls = RandomForestRegressor if kind == "rf" else ExtraTreesRegressor
    regressor = cls(n_estimators=100, max_depth=7, min_samples_leaf=3,
                    max_features=.8, random_state=42, n_jobs=-1)
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True,
                                        keep_empty_features=True), regressor)
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    weights = np.where(y >= 100, high_weight, 1.0)
    weight_key = "randomforestregressor__sample_weight" if kind == "rf" else "extratreesregressor__sample_weight"
    model.fit(train[columns], y, **{weight_key: weights})
    return max(0.0, float(model.predict(target[columns].to_frame().T)[0]))


def evaluate(pred):
    rows = []
    models = ["RF_old", "RF_flow_stage_no_ec", "Persistence", "MonthlyClimatology", *CANDIDATES]
    for split, part in pred.groupby("split", sort=False):
        month = pd.to_datetime(part.target_month).dt.month
        masks = {"all": np.ones(len(part), dtype=bool),
                 "dry_dec_apr": month.isin([12,1,2,3,4]).to_numpy(),
                 "high_ge_100": part.actual.ge(100).to_numpy()}
        for subset, mask in masks.items():
            if not mask.any():
                continue
            for name in models:
                err = part.loc[mask, name].to_numpy() - part.loc[mask, "actual"].to_numpy()
                rows.append(dict(split=split, subset=subset, model=name, n=int(mask.sum()),
                                 mae=float(np.abs(err).mean()),
                                 rmse=float(np.sqrt(np.mean(err**2))), bias=float(err.mean())))
    return pd.DataFrame(rows)


def run(delay):
    part = data_matrix(delay)
    baseline = pd.read_csv(ROOT / "outputs/ec_long_hydrology_20261029/no_recent_ec" /
                           f"predictions_{delay}d.csv")
    old = pd.read_csv(ROOT / "outputs/ec_upstream_asof_20261029/predictions.csv")
    scenario = f"EC_MONTH_END_PLUS_{delay}D"
    old = old[(old.station == "MYTHO") & (old.scenario == scenario)]
    rows = []
    for _, target in part[part.month_start.dt.year.between(2019,2023)].iterrows():
        issue = target.issue_date
        train = part[(part.month_start < target.month_start) &
                     (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
                     (part.weather_available_at <= issue)]
        if len(train) < 96 or available_date_for(target.weather_month, 5) > issue:
            raise ValueError("Training uses unavailable labels or weather")
        key = target.month_start.strftime("%Y-%m-%d")
        base = baseline[baseline.target_month == key]
        prior = old[old.target_month == key]
        if len(base) != 1 or len(prior) != 1 or float(base.iloc[0].actual) != target.conductivity_mS_per_m:
            raise ValueError("Unmatched evaluation cohort")
        if str(issue) != str(prior.iloc[0].issue_date):
            raise ValueError("Issue date mismatch")
        row = dict(delay_days=delay, target_month=key, issue_date=str(issue),
                   split="validation_2019_2021" if target.month_start.year <= 2021 else "retrospective_2022_2023",
                   actual=float(target.conductivity_mS_per_m), train_n=len(train),
                   RF_old=float(base.iloc[0].RF_old),
                   RF_flow_stage_no_ec=float(base.iloc[0].RF_flow_stage_no_ec),
                   Persistence=float(prior.iloc[0].Persistence),
                   MonthlyClimatology=float(prior.iloc[0].MonthlyClimatology))
        for name, (kind, cols, weight) in CANDIDATES.items():
            row[name] = fit_predict(kind, cols, weight, train, target)
        rows.append(row)
        if target.month_start.month == 12:
            print(delay, target.month_start.year, flush=True)
    pred = pd.DataFrame(rows)
    if len(pred) != 60 or pred.target_month.duplicated().any():
        raise ValueError("Expected exactly 60 monthly predictions")
    metrics = evaluate(pred)
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False)
    metrics.to_csv(OUT / f"metrics_{delay}d.csv", index=False)
    (OUT / f"protocol_{delay}d.json").write_text(json.dumps(dict(
        issue="day 6 of preceding month", ec_delay_days=delay,
        target="single My Tho EC sample in target month, mS/m",
        features={name:cols for name,(_,cols,_) in CANDIDATES.items()},
        high_weight_threshold_mS_m=100, high_weights=[1,3,8],
        selection="2019-2021 only", retrospective="2022-2023 previously inspected",
        limitation="No new extreme-EC months in 2022-2023; no 2024+ observed EC; no measured salt travel time"),
        indent=2), encoding="utf-8")
    print(metrics[(metrics.split == "validation_2019_2021") & metrics.subset.isin(["all","high_ge_100"])][["subset","model","n","mae"]].to_string(index=False))
    return pred, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, choices=[5,35], required=True)
    run(parser.parse_args().delay)
