"""As-of ablation of long MRC water-level histories and robust EC models.

Research-only.  Manual level series are distinct gauges; monthly summaries of
one gauge never substitute for discharge or a verified hydraulic boundary.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.backtest_protocols import available_date_for
from tools.feature_building import FLOW, OWN, STAGE, data_matrix, predictor
from tools.model_training import FEATURES as WEATHER_FEATURES, pipeline as old_pipeline

BASE = ROOT / "outputs/ec_upstream_asof_20261029/predictions.csv"
OUT = ROOT / "outputs/ec_long_hydrology_20261029"


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=int, choices=[5, 35], default=5)
    run(parser.parse_args(argv).delay)


if __name__ == "__main__":
    main()
