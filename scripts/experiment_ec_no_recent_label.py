"""Backtest My Tho EC using hydrology and weather without recent EC predictors.

This addresses the operational gap after the last MRC EC sample in 2023.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import OUT as PARENT, FLOW, STAGE, data_matrix, predictor
from scripts.experiment_ec_upstream_asof import OWN

OUT = PARENT / "no_recent_ec"
WEATHER = [x for x in OWN if not x.startswith("ec_")]
CANDIDATES = {
    "RF_flow_no_ec": ("rf", WEATHER + FLOW),
    "RF_flow_stage_no_ec": ("rf", WEATHER + FLOW + STAGE[:2]),
    "ET_flow_stage_no_ec": ("extra", WEATHER + FLOW + STAGE[:2]),
    "HGB_flow_stage_no_ec": ("hgb_log", WEATHER + FLOW + STAGE[:2]),
}


def run(delay: int):
    part = data_matrix(delay)
    old = pd.read_csv(PARENT / ("predictions.csv" if delay == 5 else f"ec_delay_{delay}d/predictions.csv"))
    output = []
    for _, target in part.iterrows():
        if target.month_start.year < 2019:
            continue
        issue = target.issue_date
        train = part[(part.month_start < target.month_start) &
                     (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
                     (part.weather_available_at <= issue)]
        matched = old[old.target_month == target.month_start.strftime("%Y-%m-%d")]
        if len(matched) != 1 or float(matched.iloc[0].actual) != target.conductivity_mS_per_m:
            raise ValueError("Cohort mismatch")
        row = dict(delay=delay, target_month=target.month_start.strftime("%Y-%m-%d"),
                   issue_date=str(issue), actual=float(target.conductivity_mS_per_m),
                   split="validation_2019_2021" if target.month_start.year <= 2021 else "retrospective_2022_2023",
                   RF_old=float(matched.iloc[0].RF_old),
                   RF_with_recent_ec=float(matched.iloc[0].RF_tc_stage_kratie))
        for name, (kind, columns) in CANDIDATES.items():
            row[name] = predictor(kind, columns, train, target)
        output.append(row)
        if target.month_start.month == 12:
            print("completed", delay, target.month_start.year, flush=True)
    pred = pd.DataFrame(output)
    if len(pred) != 60 or pred.duplicated("target_month").any():
        raise ValueError("Wrong cohort")
    score = []
    for split, group in pred.groupby("split"):
        for model in ["RF_old", "RF_with_recent_ec", *CANDIDATES]:
            err = group[model].to_numpy() - group.actual.to_numpy()
            score.append(dict(delay=delay, split=split, model=model, n=len(group),
                mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err**2)))))
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(score).to_csv(OUT / f"metrics_{delay}d.csv", index=False, encoding="utf-8-sig")
    (OUT / f"protocol_{delay}d.json").write_text(json.dumps(dict(
        issue="day 6 of preceding month", ec_delay_days=delay,
        features=CANDIDATES, ec_predictor_policy="No target-station EC values or derived EC lags in X",
        limitation="Historical EC publication vintages unknown; source weather reanalysis vintages unknown; no measured EC after 2023"),
        indent=2), encoding="utf-8")
    print(pd.DataFrame(score).to_string(index=False))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--delay", type=int, choices=[5, 35], default=5)
    run(p.parse_args().delay)
