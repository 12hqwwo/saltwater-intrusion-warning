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
from tools.backtest_protocols import available_date_for, split_for
from tools.feature_building import OWN, UPSTREAM, build_matrix

OUT = ROOT / "outputs/ec_upstream_asof_20261029"
BASELINE = ROOT / "outputs/multivariate_ec_asof_20261029/asof_predictions.csv"

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
