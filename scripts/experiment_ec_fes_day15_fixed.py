"""Isolated as-of test of FES tide around a fixed day-15 My Tho EC sample.

This reconstructs the astronomical tide at the previously selected offshore
FES ``south`` cell for local days 13–17 of each month. It does not use the
observed EC sample day, which would be unavailable on the forecast issue date.
The FES2022b atlas is a present-day hindcast, not a historical forecast vintage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyfes

from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_extreme_robust import COMPACT, fit_predict
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.experiment_fes_ec import ATLAS, CONFIG, MASK, STATUS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_fes_day15_fixed_20261030"
POINT_REPORT = ROOT / "outputs/fes_ec_multipoint_20261026/summary.json"
FEATURE = "fes_south_days13_17_mean_daily_range_cm"
TZ = "Asia/Ho_Chi_Minh"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def calculate_fes() -> pd.DataFrame:
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    if not (status.get("collection_complete") and status.get("present_constituents") == 34
            and MASK.is_file()):
        raise ValueError("Verified FES2022b atlas is required")
    for item in status["files"]:
        if not (ATLAS / item["file"]).is_file() or item["status"] not in ("VERIFIED_PAIR", "VERIFIED_NETCDF"):
            raise ValueError(f"Missing or unverified FES constituent: {item['file']}")
    point = json.loads(POINT_REPORT.read_text(encoding="utf-8"))["points"]["south"]
    if (abs(point["lon"] - 106.78333333333333) > 1e-9
            or abs(point["lat"] - 10.05) > 1e-9
            or point["four_neighbor_mask_values"] != [0, 0, 0, 0]):
        raise ValueError("The FES south point differs from the validated candidate")
    os.environ["FES_DATA"] = str(ATLAS.resolve())
    config = pyfes.config.load(CONFIG, bbox=(point["lon"] - .2, point["lat"] - .2,
                                           point["lon"] + .2, point["lat"] + .2))
    months = pd.date_range("1985-06-01", "2023-12-01", freq="MS")
    yearly = []
    for year in range(1985, 2024):
        pieces = [pd.date_range(month.replace(day=13).tz_localize(TZ),
                                month.replace(day=18).tz_localize(TZ),
                                freq="h", inclusive="left")
                  for month in months if month.year == year]
        local = pieces[0].append(pieces[1:])
        utc = local.tz_convert("UTC").tz_localize(None).to_numpy(dtype="datetime64[s]")
        n = len(utc)
        tide, long_period, flags = pyfes.evaluate_tide(
            config.models["tide"], utc,
            np.full(n, point["lon"]), np.full(n, point["lat"]), settings=config.settings)
        if not np.isfinite(tide).all() or not np.isfinite(long_period).all() or not np.all(flags == 4):
            raise ValueError(f"FES incomplete or non-native during {year}")
        yearly.append(pd.DataFrame({"time_local": local, "fes_ocean_tide_cm": tide + long_period,
                                    "pyfes_flag": flags}))
        print("FES", year, flush=True)
    hourly = pd.concat(yearly, ignore_index=True)
    if len(hourly) != len(months) * 5 * 24 or hourly.time_local.duplicated().any():
        raise ValueError("Wrong day-13–17 FES hourly coverage")
    hourly["date_local"] = hourly.time_local.dt.date
    daily = hourly.groupby("date_local").fes_ocean_tide_cm.agg(["min", "max", "count"])
    if len(daily) != len(months) * 5 or daily["count"].ne(24).any():
        raise ValueError("Incomplete local FES days")
    daily["fes_daily_range_cm"] = daily["max"] - daily["min"]
    daily = daily.reset_index()[["date_local", "fes_daily_range_cm", "count"]]
    daily["month_start"] = pd.to_datetime(daily.date_local).dt.to_period("M").dt.to_timestamp()
    monthly = daily.groupby("month_start").fes_daily_range_cm.agg(["mean", "count"]).reset_index()
    if (len(monthly) != len(months) or monthly["count"].ne(5).any()
            or not monthly.month_start.eq(months).all()):
        raise ValueError("Bad monthly tide aggregation")
    monthly = monthly.rename(columns={"mean": FEATURE, "count": "fes_daily_count"})
    OUT.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(OUT / "fes_south_hourly_days13_17_1985_2023.csv", index=False)
    daily.to_csv(OUT / "fes_south_daily_days13_17_1985_2023.csv", index=False)
    monthly.to_csv(OUT / "fes_south_feature_days13_17_1985_2023.csv", index=False)
    manifest = {
        "source": "FES2022b ocean_tide_extrapolated, 34 constituents",
        "point": {"lon": point["lon"], "lat": point["lat"], "selection": "south, validated against Vam Kenh tidal range"},
        "feature": FEATURE,
        "definition": "mean of five local-calendar-day hourly max-minus-min ranges, days 13–17 inclusive",
        "sample_day_policy": "fixed at day 15 before reading any target sample date; observed sample dates are never used",
        "timezone": TZ, "unit": "cm", "monthly_rows": len(monthly), "hourly_rows": len(hourly),
        "historical_vintage": "FES2022b atlas is retrospective; not a model vintage available at historical issue dates",
        "data_status": "MODELLED_ASTRONOMICAL_OFFSHORE_TIDE_NOT_EC_OR_OBSERVED_RIVER_STAGE",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (STATUS, CONFIG, MASK, POINT_REPORT)},
        "output_sha256": {p.name: sha(p) for p in (
            OUT / "fes_south_hourly_days13_17_1985_2023.csv",
            OUT / "fes_south_daily_days13_17_1985_2023.csv",
            OUT / "fes_south_feature_days13_17_1985_2023.csv")},
    }
    (OUT / "fes_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return monthly


def score(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, part in pred.groupby("split"):
        month = pd.to_datetime(part.target_month).dt.month
        subsets = {"all": np.ones(len(part), dtype=bool),
                   "dry_dec_apr": month.isin([12, 1, 2, 3, 4]).to_numpy(),
                   "high_ge_100": part.actual.ge(100).to_numpy()}
        for subset, mask in subsets.items():
            if not mask.any():
                continue
            for model in ("RF_compact", "RF_compact_fes_day15"):
                err = (part.loc[mask, model] - part.loc[mask, "actual"]).to_numpy(dtype=float)
                rows.append(dict(split=split, subset=subset, model=model, n=int(mask.sum()),
                                 mae=float(np.abs(err).mean()), rmse=float(np.sqrt(np.mean(err ** 2))),
                                 bias=float(err.mean())))
    return pd.DataFrame(rows)


def evaluate(delay: int, monthly: pd.DataFrame) -> None:
    matrix = data_matrix(delay).merge(monthly, on="month_start", how="left", validate="one_to_one")
    if matrix[FEATURE].isna().any():
        raise ValueError("Missing FES feature for at least one EC label")
    saved_recent = pd.read_csv(ROOT / "outputs/ec_extreme_robust_20261029" / f"predictions_{delay}d.csv")
    saved_history = (pd.read_csv(ROOT / "outputs/ec_compact_history_20261029/predictions_2010_2018.csv")
                     if delay == 5 else None)
    rows = []
    for _, target in matrix[matrix.month_start.dt.year.between(2010, 2023)].iterrows():
        issue = target.issue_date
        train = matrix[(matrix.month_start < target.month_start)
                       & (matrix.month_start.map(lambda t: available_date_for(t, delay)) <= issue)
                       & (matrix.weather_available_at <= issue)]
        if len(train) < 96 or available_date_for(target.weather_month, 5) > issue:
            raise ValueError("Future input or too few as-of labels")
        key = target.month_start.strftime("%Y-%m-%d")
        prior = saved_history if target.month_start.year <= 2018 else saved_recent
        if prior is None:
            base = fit_predict("rf", COMPACT, 1.0, train, target)
        else:
            check = prior.loc[prior.target_month.eq(key)]
            if len(check) != 1 or float(check.iloc[0].actual) != float(target.conductivity_mS_per_m):
                raise ValueError(f"Baseline cohort differs: {key}")
            base = float(check.iloc[0].RF_compact)
        enriched = fit_predict("rf", COMPACT + [FEATURE], 1.0, train, target)
        split = ("history_2010_2018" if target.month_start.year <= 2018 else
                 "validation_2019_2021" if target.month_start.year <= 2021 else
                 "retrospective_2022_2023")
        rows.append(dict(delay_days=delay, target_month=key, issue_date=str(issue), split=split,
                         actual=float(target.conductivity_mS_per_m), train_n=len(train),
                         **{FEATURE: float(target[FEATURE])}, RF_compact=base,
                         RF_compact_fes_day15=enriched))
        if target.month_start.month == 12:
            print("RF", delay, target.month_start.year, flush=True)
    pred = pd.DataFrame(rows)
    if len(pred) != 168 or pred.target_month.duplicated().any() or pred[FEATURE].isna().any():
        raise ValueError("Wrong matched EC cohort")
    metrics = score(pred)
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False)
    metrics.to_csv(OUT / f"metrics_{delay}d.csv", index=False)
    print(metrics.to_string(index=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, choices=[5, 35], required=True)
    args = parser.parse_args()
    feature_path = OUT / "fes_south_feature_days13_17_1985_2023.csv"
    if feature_path.exists():
        monthly = pd.read_csv(feature_path, parse_dates=["month_start"])
        if len(monthly) != 463 or monthly.month_start.duplicated().any() or monthly[FEATURE].isna().any():
            raise ValueError("Existing FES feature file is incomplete")
    else:
        monthly = calculate_fes()
    evaluate(args.delay, monthly)


if __name__ == "__main__":
    main()
