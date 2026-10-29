"""As-of EC ablation using a FES coastal point selected by gauge validation."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import FLOW, STAGE, data_matrix, predictor
from scripts.experiment_ec_no_recent_label import WEATHER

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_fes_validated_20261029"
FES = ROOT / "outputs/fes_ec_offshore_sensitivity_20261026/fes_features_1985_2026.csv"
BASE = WEATHER + FLOW + STAGE[:2]
VARIANTS = {
    "south_midmonth": ["fes_south_midmonth_range_cm"],
    "south_fullmonth": ["fes_south_month_range_cm"],
}


def run(delay):
    matrix = data_matrix(delay)
    tide = pd.read_csv(FES, usecols=["month_start", *dict.fromkeys(sum(VARIANTS.values(), []))],
                       parse_dates=["month_start"])
    if tide.month_start.duplicated().any():
        raise ValueError("Duplicate FES months")
    matrix = matrix.merge(tide, on="month_start", how="left", validate="one_to_one")
    old = pd.read_csv(ROOT / "outputs/ec_long_hydrology_20261029/no_recent_ec" /
                      f"predictions_{delay}d.csv")
    rows = []
    for _, target in matrix[matrix.month_start.dt.year.between(2019, 2023)].iterrows():
        train = matrix[(matrix.month_start < target.month_start) &
                       (matrix.month_start.map(lambda t: available_date_for(t, delay)) <= target.issue_date) &
                       (matrix.weather_available_at <= target.issue_date)]
        if len(train) < 96 or target[list(dict.fromkeys(sum(VARIANTS.values(), [])))].isna().any():
            raise ValueError("Missing FES or training labels")
        match = old[old.target_month == target.month_start.strftime("%Y-%m-%d")]
        if len(match) != 1 or float(match.iloc[0].actual) != float(target.conductivity_mS_per_m):
            raise ValueError("Baseline cohort mismatch")
        row = dict(delay=delay, target_month=target.month_start.strftime("%Y-%m-%d"),
                   split="validation_2019_2021" if target.month_start.year <= 2021 else "retrospective_2022_2023",
                   actual=float(target.conductivity_mS_per_m), RF_hydrology=float(match.iloc[0].RF_flow_stage_no_ec))
        for name, extra in VARIANTS.items():
            row[name] = predictor("rf", BASE + extra, train, target)
        rows.append(row)
        if target.month_start.month == 12:
            print("completed", delay, target.month_start.year, flush=True)
    pred = pd.DataFrame(rows)
    if len(pred) != 60 or pred.duplicated("target_month").any():
        raise ValueError("Wrong cohort")
    scores=[]
    for split, group in pred.groupby("split"):
        for name in ("RF_hydrology", *VARIANTS):
            e = (group[name]-group.actual).to_numpy()
            high = group.actual.ge(100).to_numpy()
            scores.append(dict(delay=delay, split=split, model=name, n=len(group),
                               mae=float(np.abs(e).mean()), rmse=float(np.sqrt(np.mean(e**2))),
                               high_n=int(high.sum()), high_mae=float(np.abs(e[high]).mean()) if high.any() else None))
    OUT.mkdir(parents=True,exist_ok=True)
    pred.to_csv(OUT / f"predictions_{delay}d.csv",index=False)
    pd.DataFrame(scores).to_csv(OUT / f"metrics_{delay}d.csv",index=False)
    print(pd.DataFrame(scores).to_string(index=False))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--delay",type=int,choices=[5,35],required=True)
    run(p.parse_args().delay)
