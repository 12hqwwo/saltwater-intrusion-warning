"""Small as-of ablation of boosted trees for My Tho without recent EC features."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import FLOW, STAGE, data_matrix
from scripts.experiment_ec_no_recent_label import WEATHER

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_boosting_20261029"
COLS = WEATHER + FLOW + STAGE[:2]


def candidate(name):
    if name == "XGB_raw":
        model = XGBRegressor(n_estimators=100, max_depth=2, learning_rate=.04,
            subsample=.8, colsample_bytree=.8, reg_lambda=10, objective="reg:squarederror",
            random_state=42, n_jobs=1)
    elif name == "XGB_log":
        model = XGBRegressor(n_estimators=100, max_depth=2, learning_rate=.04,
            subsample=.8, colsample_bytree=.8, reg_lambda=10, objective="reg:squarederror",
            random_state=42, n_jobs=1)
    elif name == "LGBM_raw":
        model = LGBMRegressor(n_estimators=100, max_depth=3, num_leaves=7,
            learning_rate=.04, min_child_samples=20, reg_lambda=10,
            verbosity=-1, random_state=42, n_jobs=1)
    else:
        raise ValueError(name)
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), model)


def run(delay):
    part = data_matrix(delay)
    old = pd.read_csv(ROOT / "outputs/ec_long_hydrology_20261029/no_recent_ec" /
                      f"predictions_{delay}d.csv")
    names = ("XGB_raw", "XGB_log", "LGBM_raw")
    rows = []
    for _, target in part[part.month_start.dt.year.between(2019, 2023)].iterrows():
        train = part[(part.month_start < target.month_start) &
                     (part.month_start.map(lambda t: available_date_for(t, delay)) <= target.issue_date) &
                     (part.weather_available_at <= target.issue_date)]
        assert len(train) >= 96
        actual = float(target.conductivity_mS_per_m)
        row = dict(delay=delay, target_month=target.month_start.strftime("%Y-%m-%d"), actual=actual,
                   split="validation_2019_2021" if target.month_start.year <= 2021 else "retrospective_2022_2023")
        matched = old.loc[old.target_month == row["target_month"]]
        assert len(matched) == 1 and float(matched.iloc[0].actual) == actual
        row["RF_old"] = float(matched.iloc[0].RF_old)
        row["RF_flow_stage_no_ec"] = float(matched.iloc[0].RF_flow_stage_no_ec)
        for name in names:
            model = candidate(name)
            y = train.conductivity_mS_per_m.to_numpy()
            model.fit(train[COLS], np.log1p(y) if name.endswith("log") else y)
            pred = float(model.predict(target[COLS].to_frame().T)[0])
            row[name] = max(0.0, float(np.expm1(pred)) if name.endswith("log") else pred)
        rows.append(row)
        if target.month_start.month == 12:
            print("completed", delay, target.month_start.year, flush=True)
    pred = pd.DataFrame(rows)
    assert len(pred) == 60 and not pred.duplicated("target_month").any()
    metrics = []
    for split, group in pred.groupby("split"):
        for name in ("RF_old", "RF_flow_stage_no_ec", *names):
            e = (group[name] - group.actual).to_numpy()
            high = group.actual.ge(100).to_numpy()
            metrics.append(dict(delay=delay, split=split, model=name, n=len(group),
                mae=float(np.abs(e).mean()), rmse=float(np.sqrt(np.mean(e**2))),
                high_n=int(high.sum()), high_mae=float(np.abs(e[high]).mean()) if high.any() else None))
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False)
    pd.DataFrame(metrics).to_csv(OUT / f"metrics_{delay}d.csv", index=False)
    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, choices=[5, 35], required=True)
    run(parser.parse_args().delay)
