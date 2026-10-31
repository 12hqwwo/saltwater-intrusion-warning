"""Isolated FES2022b tidal-feature experiment for monthly My Tho EC.

Run with the project's API environment::

    .venv-api/Scripts/python.exe scripts/experiment_fes_ec.py

This does not replace the served model or alter the gate simulation. FES is
astronomical ocean tide, not measured river tide, EC, or salinity.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import netCDF4
import numpy as np
import pandas as pd
import pyfes
from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.domain.multivariate_ec import FEATURES
from scripts.train_multivariate_ec import pipeline, training_frame


ATLAS = ROOT / "data/raw/tide/fes2022b/ocean_tide_extrapolated"
MASK = ATLAS / "mask_fes2022B.nc"
STATUS = ROOT / "data/raw/tide/fes2022b/collection_status.json"
CONFIG = ROOT / "config/fes2022b_full.yaml"
OUTPUT = ROOT / "outputs/fes_ec_experiment_20261026"
MOUTH = (106.7503834, 10.2635303)
TIDE_FEATURE = "fes_mean_daily_range_cm"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_native_ocean_point(mask_path: Path = MASK, mouth=MOUTH,
                              exclude=(), minimum_separation_km=0.0):
    """Find nearest cell center with four *native-ocean* surrounding nodes."""
    with netCDF4.Dataset(mask_path) as ds:
        meaning = ds.variables["mask"].long_name
        if "0=Ocean native data" not in meaning:
            raise ValueError("Unknown FES mask meaning; do not infer native data.")
        lon = np.asarray(ds.variables["lon"][:])
        lat = np.asarray(ds.variables["lat"][:])
        ii = np.flatnonzero((lon >= mouth[0] - 0.5) & (lon <= mouth[0] + 0.5))
        jj = np.flatnonzero((lat >= mouth[1] - 0.5) & (lat <= mouth[1] + 0.5))
        if len(ii) < 2 or len(jj) < 2:
            raise ValueError("FES grid does not cover the Cua Tieu search area.")
        block = np.asarray(ds.variables["mask"][jj[0]:jj[-1] + 1, ii[0]:ii[-1] + 1])
        native = ((block[:-1, :-1] == 0) & (block[1:, :-1] == 0)
                  & (block[:-1, 1:] == 0) & (block[1:, 1:] == 0))
        rows, cols = np.where(native)
        if not len(rows):
            raise ValueError("No four-node native-ocean point near Cua Tieu.")
        x = (lon[ii[0] + cols] + lon[ii[0] + cols + 1]) / 2
        y = (lat[jj[0] + rows] + lat[jj[0] + rows + 1]) / 2
        km = 111.2 * np.sqrt(((x - mouth[0]) * np.cos(np.deg2rad(mouth[1]))) ** 2
                             + (y - mouth[1]) ** 2)
        for used in exclude:
            separation = 111.2 * np.sqrt(((x - used["lon"]) * np.cos(np.deg2rad(mouth[1]))) ** 2
                                         + (y - used["lat"]) ** 2)
            km = np.where(separation >= minimum_separation_km, km, np.inf)
        best = int(np.argmin(km))
        if not np.isfinite(km[best]) or km[best] > 30:
            raise ValueError("Nearest native-ocean point is too far from Cua Tieu.")
        return dict(lon=float(x[best]), lat=float(y[best]),
                    distance_to_mouth_km=float(km[best]),
                    four_neighbor_mask_values=[0, 0, 0, 0],
                    selection="nearest four-native-node cell center within 0.5 degrees")


def predict_monthly_tide(point, first_month, last_month):
    """Mean of local-calendar-day hourly max-min ranges for each target month."""
    os.environ["FES_DATA"] = str(ATLAS.resolve())
    box = (point["lon"] - 0.2, point["lat"] - 0.2,
           point["lon"] + 0.2, point["lat"] + 0.2)
    config = pyfes.config.load(CONFIG, bbox=box)
    rows = []
    for month in pd.date_range(first_month, last_month, freq="MS"):
        start = month.tz_localize("Asia/Ho_Chi_Minh")
        stop = (month + pd.DateOffset(months=1)).tz_localize("Asia/Ho_Chi_Minh")
        local_hours = pd.date_range(start, stop, freq="h", inclusive="left")
        utc_hours = local_hours.tz_convert("UTC").tz_localize(None).to_numpy(dtype="datetime64[s]")
        count = len(utc_hours)
        tide, long_period, flags = pyfes.evaluate_tide(
            config.models["tide"], utc_hours,
            np.full(count, point["lon"]), np.full(count, point["lat"]),
            settings=config.settings)
        if not np.isfinite(tide).all() or not np.isfinite(long_period).all() or not np.all(flags > 0):
            raise ValueError(f"Invalid FES output for {month:%Y-%m}; do not impute tide.")
        # Both returned components are in cm. The daily range is insensitive
        # to the arbitrary absolute water-level datum.
        levels = pd.Series(tide + long_period, index=local_hours)
        daily = levels.resample("D").agg(["min", "max"])
        if len(daily) != month.days_in_month or daily.isna().any().any():
            raise ValueError(f"Incomplete local-day FES coverage: {month:%Y-%m}.")
        rows.append(dict(month_start=month, **{TIDE_FEATURE: float((daily["max"] - daily["min"]).mean())},
                         hourly_count=count, min_pyfes_flag=int(flags.min())))
    return pd.DataFrame(rows)


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    return dict(n=len(actual), mae_mS_m=float(mean_absolute_error(actual, predicted)),
                rmse_mS_m=float(np.sqrt(mean_squared_error(actual, predicted))))


def evaluate(frame):
    """Reproduce the served RF folds, changing only the added FES feature."""
    frame = frame.sort_values("month_start").copy()
    if frame[TIDE_FEATURE].isna().any() or frame[FEATURES].isna().any().any():
        raise ValueError("Incomplete paired cohort; FES and base must use identical months.")
    if frame.month_start.duplicated().any():
        raise ValueError("Duplicate target month after FES join.")
    y = "conductivity_mS_per_m"
    lookup = frame.set_index("month_start")[y]
    rows = []
    report = {}
    for name, begin, end in (("validation", "2019-01-01", "2022-01-01"),
                             ("holdout", "2022-01-01", "2024-01-01")):
        train = frame[frame.month_start < begin]
        test = frame[(frame.month_start >= begin) & (frame.month_start < end)]
        if len(test) != (36 if name == "validation" else 24):
            raise ValueError(f"Wrong {name} cohort; comparison must stay paired.")
        base = pipeline().fit(train[FEATURES], train[y]).predict(test[FEATURES])
        plus_cols = FEATURES + [TIDE_FEATURE]
        plus = pipeline().fit(train[plus_cols], train[y]).predict(test[plus_cols])
        cohort = []
        for (_, row), b, p in zip(test.iterrows(), base, plus):
            target = row.month_start
            prior = lookup[lookup.index <= target - pd.DateOffset(months=2)]
            seasonal = lookup.get(target - pd.DateOffset(months=12), np.nan)
            climate = train.loc[train.month_start.dt.month == target.month, y].mean()
            cohort.append(dict(split=name, target_month=target.date().isoformat(),
                               actual_ec_mS_m=float(row[y]),
                               rf_weather_month=float(b), rf_weather_month_fes=float(p),
                               persistence_t_minus_2=float(prior.iloc[-1]),
                               seasonal_naive=float(seasonal), monthly_climatology=float(climate),
                               **{TIDE_FEATURE: float(row[TIDE_FEATURE])}))
        data = pd.DataFrame(cohort)
        rows.extend(cohort)
        report[name] = {column: metrics(data.actual_ec_mS_m, data[column])
                        for column in ("rf_weather_month", "rf_weather_month_fes",
                                       "persistence_t_minus_2", "seasonal_naive", "monthly_climatology")}
        report[name]["fes_vs_weather_mae_change_pct"] = 100 * (
            report[name]["rf_weather_month_fes"]["mae_mS_m"] /
            report[name]["rf_weather_month"]["mae_mS_m"] - 1)
    return pd.DataFrame(rows), report


def main():
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    if not (status.get("collection_complete") and status.get("present_constituents") == 34
            and status.get("mask_required") and MASK.is_file()):
        raise ValueError("FES atlas is not complete and verified.")
    for item in status["files"]:
        if not (ATLAS / item["file"]).is_file() or item["status"] not in ("VERIFIED_PAIR", "VERIFIED_NETCDF"):
            raise ValueError(f"Missing or unverified FES file: {item['file']}")
    point = choose_native_ocean_point()
    frame, _ = training_frame(ROOT / "data/research/mrc_ec_monthly_samples.csv",
                              ROOT / "data/external/multivariate_weather/manifest.json")
    frame = frame[frame.station.eq("MYTHO")].copy()
    tide = predict_monthly_tide(point, frame.month_start.min(), frame.month_start.max())
    paired = frame.merge(tide, on="month_start", how="left", validate="one_to_one")
    predictions, evaluation = evaluate(paired)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tide.to_csv(OUTPUT / "fes_monthly_feature.csv", index=False)
    predictions.to_csv(OUTPUT / "paired_predictions.csv", index=False)
    result = dict(status="RESEARCH_ONLY_NOT_DEPLOYED", point=point,
                  point_mask_source=str(MASK.relative_to(ROOT)).replace("\\", "/"),
                  feature=TIDE_FEATURE, feature_definition="mean of hourly daily max-min ranges over each local calendar month",
                  feature_unit="cm", timezone="Asia/Ho_Chi_Minh", source="FES2022b extrapolated atlas, native-ocean cells only",
                  pyfes_version=pyfes.__version__, collection_status_sha256=sha256(STATUS),
                  config_sha256=sha256(CONFIG), target_sha256=sha256(ROOT / "data/research/mrc_ec_monthly_samples.csv"),
                  folds="train through 2018, validate 2019-2021; train through 2021, retrospective holdout 2022-2023",
                  evaluation=evaluation,
                  caution="Monthly EC is a sample, not a monthly EC mean. FES is predicted astronomical ocean tide, not measured river tide or EC. Previously examined holdout is not a fresh blind test. No local tide-gauge validation.",
                  deployment_ready=False, gate_decision_eligible=False)
    (OUTPUT / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(point=point, evaluation=evaluation), indent=2))


if __name__ == "__main__":
    main()
