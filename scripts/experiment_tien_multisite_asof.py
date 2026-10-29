"""Ablate observed My Thuan EC and Tien water levels for My Tho monthly EC.

Issue day 6 of month t-1; all predictors from assumed available records only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for, split_for
from scripts.experiment_ec_upstream_asof import OWN, build_matrix, ec_features, fit_predict

SOURCE = ROOT / "data/external/tien_multisite_20261029_verified"
SUPPLEMENT = ROOT / "data/external/tien_multisite_supplement_20261029"
HISTORY = ROOT / "data/external/tien_manual_history_20261029"
OUT = ROOT / "outputs/tien_multisite_asof_20261029"
PREVIOUS = ROOT / "outputs/ec_upstream_asof_20261029/predictions.csv"
MID = ["mt_latest", "mt_previous", "mt_age_months", "mt_lag12", "mt_mean3", "mt_mean12"]
LEVEL = ["tc_level_mean_t2", "tc_level_range_t2", "mt_level_mean_t2",
         "mt_level_range_t2", "vk_level_mean_t2", "vk_level_range_t2"]
MANUAL = ["tc_manual_median_t2", "tc_manual_range_t2", "mt_manual_median_t2",
          "mt_manual_range_t2", "vk_manual_median_t2", "vk_manual_range_t2"]


def middle_ec():
    path = next(SOURCE.glob("019804_Conductivity_Water Quality_*.csv"))
    frame = pd.read_csv(path)
    frame["month"] = pd.to_datetime(frame.observed_at).dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    if frame.month.duplicated().any() or frame.unit.ne("mS/m").any():
        raise ValueError("My Thuan EC is not one mS/m sample per month")
    return frame.set_index("month").value.sort_index()


def level_monthly():
    pieces = []
    for code, prefix in [("019803", "tc"), ("019804", "mt"), ("985203", "vk")]:
        path = next(SOURCE.glob(f"{code}_Water_Level_Telemetry_*_daily.csv"))
        daily = pd.read_csv(path)
        daily["weather_month"] = pd.to_datetime(daily.date_local).dt.to_period("M").dt.to_timestamp()
        good = daily[daily.n >= 80].copy()
        good["range"] = good.level_max_m-good.level_min_m
        monthly = good.groupby("weather_month").agg(
            complete_days=("n", "size"), mean=("level_mean_m", "mean"),
            daily_range=("range", "mean"))
        monthly.loc[monthly.complete_days < 20, ["mean", "daily_range"]] = np.nan
        monthly = monthly.rename(columns={"mean":f"{prefix}_level_mean_t2",
                                           "daily_range":f"{prefix}_level_range_t2"})
        pieces.append(monthly.drop(columns="complete_days"))
    return pd.concat(pieces, axis=1).reset_index()


def manual_monthly():
    pieces = []
    for code, prefix in [("980601", "tc"), ("019804", "mt"), ("985203", "vk")]:
        files = [next(folder.glob(f"{code}_Water_Level_Manual_*.csv"))
                 for folder in [HISTORY, SUPPLEMENT]]
        frame = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
        if frame.observed_at.duplicated().any() or frame.unit.ne("m").any():
            raise ValueError(f"Bad manual level series {code}")
        at = pd.to_datetime(frame.observed_at)
        frame["date"] = at.dt.date
        daily = frame.groupby("date").agg(n=("value", "size"), median=("value", "median"),
                                          low=("value", "min"), high=("value", "max"))
        daily["range"] = (daily.high - daily.low).where(daily.n >= 2)
        daily["weather_month"] = pd.to_datetime(daily.index).to_period("M").to_timestamp()
        grouped = daily.groupby("weather_month")
        monthly = grouped.agg(days=("median", "size"), range_days=("range", "count"),
                              median=("median", "median"), daily_range=("range", "median"))
        monthly.loc[monthly.days < 20, "median"] = np.nan
        monthly.loc[monthly.range_days < 10, "daily_range"] = np.nan
        monthly = monthly.rename(columns={"median":f"{prefix}_manual_median_t2",
                                          "daily_range":f"{prefix}_manual_range_t2"})
        pieces.append(monthly.drop(columns=["days", "range_days"]))
    return pd.concat(pieces, axis=1).reset_index()


def main():
    mid = middle_ec()
    levels = level_monthly()
    manuals = manual_monthly()
    old = pd.read_csv(PREVIOUS)
    output = []
    for delay, scenario in [(5, "EC_MONTH_END_PLUS_5D"), (35, "EC_MONTH_END_PLUS_35D")]:
        matrix = build_matrix(delay)
        part = matrix[matrix.station.eq("MYTHO")].merge(levels, on="weather_month", how="left", validate="many_to_one")
        part = part.merge(manuals, on="weather_month", how="left", validate="many_to_one")
        for i, row in part.iterrows():
            features = ec_features(mid, row.month_start, row.issue_date, delay, "mt")
            if features["mt_available_at"] is not None and features["mt_available_at"] > row.issue_date:
                raise ValueError("Future My Thuan EC")
            for name in MID:
                part.at[i, name] = features[name]
            part.at[i, "mt_source_month"] = features["mt_source_month"]
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
            matched = old[(old.station == "MYTHO") & (old.scenario == scenario) &
                          (old.target_month == target.month_start.strftime("%Y-%m-%d"))]
            if len(matched) != 1 or matched.iloc[0].actual != target.conductivity_mS_per_m:
                raise ValueError("Comparison cohort mismatch")
            b = matched.iloc[0]
            record = dict(station="MYTHO", scenario=scenario, split=split,
                          target_month=target.month_start.strftime("%Y-%m-%d"),
                          issue_date=str(issue), actual=float(target.conductivity_mS_per_m),
                          mt_source_month=target.mt_source_month.strftime("%Y-%m-%d") if pd.notna(target.mt_source_month) else "",
                          train_n=len(train), RF_own=float(b.RF_own), old_RF=float(b.old_RF),
                          Persistence=float(b.Persistence))
            for name, columns in [("RF_mythuan_ec", OWN+MID),
                                  ("RF_mythuan_ec_levels", OWN+MID+LEVEL),
                                  ("RF_manual_levels", OWN+MANUAL),
                                  ("RF_mythuan_ec_manual", OWN+MID+MANUAL)]:
                record[name] = fit_predict("RF", train[columns],
                                           train.conductivity_mS_per_m, target[columns].to_frame().T)
            output.append(record)
        print("completed", scenario, flush=True)
    pred = pd.DataFrame(output)
    if len(pred) != 120 or pred.duplicated(["scenario", "target_month"]).any():
        raise ValueError("Bad output cohort")
    scores = []
    for (scenario, split), group in pred.groupby(["scenario", "split"]):
        for model in ["old_RF", "RF_own", "RF_mythuan_ec", "RF_mythuan_ec_levels",
                      "RF_manual_levels", "RF_mythuan_ec_manual", "Persistence"]:
            err = group[model].to_numpy()-group.actual.to_numpy()
            scores.append(dict(scenario=scenario, split=split, model=model, n=len(group),
                               mae=float(np.abs(err).mean()),
                               rmse=float(np.sqrt(np.mean(err**2))), bias=float(err.mean())))
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(OUT / "predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(scores).to_csv(OUT / "metrics.csv", index=False, encoding="utf-8-sig")
    (OUT / "protocol.json").write_text(json.dumps(dict(
        issue="day 6 of target-minus-one month", ec_delay_days=[5,35],
        water_level_month="target-minus-two month", water_level_assumed_delay_days=5,
        water_level_month_requirement="at least 20 days each with at least 80 quarter-hour samples; else missing",
        manual_level_requirement="at least 20 days for monthly median; at least 10 days with 2+ samples for daily range median; no gauge-datum merging",
        source="MRC My Thuan EC and Tien water level series; quality remains UNVERIFIED",
        warning="No historical publication vintages or common gauge datum confirmation; water level is not discharge; 2022-23 retrospective period was previously inspected"), indent=2), encoding="utf-8")
    print(pd.DataFrame(scores).to_string(index=False))


if __name__ == "__main__":
    main()
