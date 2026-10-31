"""Multi-point FES2022b tide features and an isolated My Tho EC forecast.

Run: .venv-api/Scripts/python.exe scripts/experiment_fes_ec_multipoint.py
No served model, registry, map, or gate policy is changed by this experiment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import pyfes
import joblib
import sklearn

from backend.domain.multivariate_ec import FEATURES, predict_month
from backend.repositories.multivariate_inputs import get_monthly_weather
from scripts.experiment_fes_ec import (
    ATLAS, CONFIG, MASK, MOUTH, STATUS, choose_native_ocean_point, metrics, pipeline, sha256,
    training_frame,
)

OUT = ROOT / "outputs/fes_ec_offshore_sensitivity_20261026"
TARGET_MONTH = pd.Timestamp("2026-11-01")
# These three geographic targets are fixed before seeing EC results. Each is
# snapped to a native-ocean 2x2 FES cell; none is treated as a river station.
TARGETS = {
    "near": MOUTH,
    "ese": (106.85, 10.17),
    "south": (106.76, 10.10),
}
CANDIDATES = {
    "near_month": ["fes_near_month_range_cm"],
    "near_midmonth": ["fes_near_midmonth_range_cm"],
    "ese_midmonth": ["fes_ese_midmonth_range_cm"],
    "south_midmonth": ["fes_south_midmonth_range_cm"],
    "coastal_mean_midmonth": ["fes_coastal_mean_midmonth_range_cm"],
}


def select_points():
    points = {}
    for name, target in TARGETS.items():
        item = choose_native_ocean_point(mask_path=MASK, mouth=target)
        item["target_lon"], item["target_lat"] = target
        item["distance_to_cua_tieu_mouth_km"] = float(111.2 * np.hypot(
            (item["lon"] - MOUTH[0]) * np.cos(np.deg2rad(MOUTH[1])),
            item["lat"] - MOUTH[1]))
        points[name] = item
    coordinates = {(item["lon"], item["lat"]) for item in points.values()}
    if len(coordinates) != len(points):
        raise ValueError("Distinct FES coastal targets resolved to the same grid cell.")
    return points


def tide_features(points, first, last):
    os.environ["FES_DATA"] = str(ATLAS.resolve())
    names = list(points)
    xs = np.array([points[name]["lon"] for name in names])
    ys = np.array([points[name]["lat"] for name in names])
    config = pyfes.config.load(CONFIG, bbox=(float(xs.min() - .2), float(ys.min() - .2),
                                           float(xs.max() + .2), float(ys.max() + .2)))
    rows = []
    for month in pd.date_range(first, last, freq="MS"):
        start = month.tz_localize("Asia/Ho_Chi_Minh")
        stop = (month + pd.DateOffset(months=1)).tz_localize("Asia/Ho_Chi_Minh")
        local_hours = pd.date_range(start, stop, freq="h", inclusive="left")
        utc = local_hours.tz_convert("UTC").tz_localize(None).to_numpy(dtype="datetime64[s]")
        n = len(utc)
        tide, long_period, flags = pyfes.evaluate_tide(
            config.models["tide"], np.tile(utc, len(names)),
            np.repeat(xs, n), np.repeat(ys, n), settings=config.settings)
        if not np.isfinite(tide).all() or not np.isfinite(long_period).all() or not np.all(flags == 4):
            raise ValueError(f"FES interpolation is incomplete or non-native at {month:%Y-%m}.")
        row = {"month_start": month, "hourly_count_per_point": n, "min_pyfes_flag": int(flags.min())}
        for i, name in enumerate(names):
            levels = pd.Series((tide + long_period)[i*n:(i+1)*n], index=local_hours)
            daily = levels.resample("D").agg(["min", "max"])
            if len(daily) != month.days_in_month or daily.isna().any().any():
                raise ValueError(f"Missing FES local day at {month:%Y-%m} {name}.")
            ranges = daily["max"] - daily["min"]
            row[f"fes_{name}_month_range_cm"] = float(ranges.mean())
            row[f"fes_{name}_midmonth_range_cm"] = float(ranges.loc[ranges.index.day.isin(range(9, 16))].mean())
        row["fes_coastal_mean_midmonth_range_cm"] = float(np.mean(
            [row[f"fes_{name}_midmonth_range_cm"] for name in names]))
        rows.append(row)
    return pd.DataFrame(rows)


def compare(frame):
    frame = frame.sort_values("month_start")
    if frame.month_start.duplicated().any() or frame[list(FEATURES) + list(dict.fromkeys(
            col for cols in CANDIDATES.values() for col in cols))].isna().any().any():
        raise ValueError("Incomplete or duplicated paired modeling cohort.")
    truth = frame.set_index("month_start").conductivity_mS_per_m
    predictions, evaluation = [], {}
    for split, begin, end in (("validation", "2019-01-01", "2022-01-01"),
                              ("holdout", "2022-01-01", "2024-01-01")):
        train = frame[frame.month_start < begin]
        test = frame[(frame.month_start >= begin) & (frame.month_start < end)]
        if len(test) != (36 if split == "validation" else 24):
            raise ValueError(f"Unexpected {split} month count.")
        model_cols = {"weather_month": FEATURES, **{name: FEATURES + cols for name, cols in CANDIDATES.items()}}
        output = {name: pipeline().fit(train[cols], train.conductivity_mS_per_m).predict(test[cols])
                  for name, cols in model_cols.items()}
        for i, (_, item) in enumerate(test.iterrows()):
            target = item.month_start
            previous = truth[truth.index <= target - pd.DateOffset(months=2)]
            predictions.append(dict(split=split, target_month=target.date().isoformat(),
                                    actual_ec_mS_m=float(item.conductivity_mS_per_m),
                                    **{name: float(values[i]) for name, values in output.items()},
                                    persistence_t_minus_2=float(previous.iloc[-1]),
                                    seasonal_naive=float(truth.get(target - pd.DateOffset(months=12))),
                                    monthly_climatology=float(train.loc[train.month_start.dt.month == target.month,
                                                                         "conductivity_mS_per_m"].mean())))
        cohort = pd.DataFrame([item for item in predictions if item["split"] == split])
        evaluation[split] = {name: metrics(cohort.actual_ec_mS_m, cohort[name]) for name in
                             [*model_cols, "persistence_t_minus_2", "seasonal_naive", "monthly_climatology"]}
    winner = min(CANDIDATES, key=lambda name: evaluation["validation"][name]["mae_mS_m"])
    return pd.DataFrame(predictions), evaluation, winner


def forecast(frame, tide, winner):
    current = tide.loc[tide.month_start.eq(TARGET_MONTH)]
    if len(current) != 1:
        raise ValueError("Missing unique target-month FES feature.")
    weather_month = TARGET_MONTH - pd.DateOffset(months=2)
    weather = [row for row in get_monthly_weather("MYTHO", require_verified_wind=True)
               if row["input_month"] == weather_month.strftime("%Y-%m")]
    if len(weather) != 1:
        raise ValueError("Target t-2 weather month is unavailable or unverified.")
    source = weather[0]
    values = {name: float(source[name]) for name in FEATURES[:3]}
    values["month_sin"] = float(np.sin(2 * np.pi * TARGET_MONTH.month / 12))
    values["month_cos"] = float(np.cos(2 * np.pi * TARGET_MONTH.month / 12))
    values.update({name: float(current.iloc[0][name]) for name in CANDIDATES[winner]})
    final = pipeline().fit(frame[FEATURES + CANDIDATES[winner]], frame.conductivity_mS_per_m)
    estimate = float(final.predict(pd.DataFrame([values], columns=FEATURES + CANDIDATES[winner]))[0])
    existing = predict_month("MYTHO", TARGET_MONTH, {name: values[name] for name in FEATURES[:3]})
    return dict(target_month=TARGET_MONTH.date().isoformat(), station="MYTHO",
                selected_tide_variant=winner, selected_on="2019-2021 validation MAE only",
                predicted_ec_mS_m=estimate, existing_served_model_ec_mS_m=existing["predicted_ec_mS_m"],
                feature_values=values, feature_units={**{name: unit for name, unit in
                    zip(FEATURES, ["mm", "degC", "m/s", "1", "1"])},
                    **{name: "cm" for name in CANDIDATES[winner]}},
                weather_input_month=weather_month.strftime("%Y-%m"),
                source_ec_training_cutoff=frame.month_start.max().date().isoformat(),
                quality_status="EXPERIMENTAL_UNVERIFIED_NO_POST_2023_EC_VALIDATION",
                deployment_ready=False, gate_decision_eligible=False), final


def main():
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    if not (status.get("collection_complete") and status.get("present_constituents") == 34 and MASK.is_file()):
        raise ValueError("Complete FES2022b atlas and mask required.")
    for item in status["files"]:
        if not (ATLAS / item["file"]).is_file() or item["status"] not in ("VERIFIED_PAIR", "VERIFIED_NETCDF"):
            raise ValueError(f"Missing or unverified atlas file: {item['file']}")
    points = select_points()
    frame, _ = training_frame(ROOT / "data/research/mrc_ec_monthly_samples.csv",
                              ROOT / "data/external/multivariate_weather/manifest.json")
    frame = frame[frame.station.eq("MYTHO")].copy()
    tide = tide_features(points, frame.month_start.min(), TARGET_MONTH)
    paired = frame.merge(tide, on="month_start", how="left", validate="one_to_one")
    predictions, evaluation, winner = compare(paired)
    future, final_model = forecast(paired, tide, winner)
    OUT.mkdir(parents=True, exist_ok=True)
    tide.to_csv(OUT / "fes_features_1985_2026.csv", index=False)
    predictions.to_csv(OUT / "paired_predictions.csv", index=False)
    pd.DataFrame([{
        "station": future["station"], "target_month": future["target_month"],
        "experimental_fes_ec_mS_m": future["predicted_ec_mS_m"],
        "existing_weather_ec_mS_m": future["existing_served_model_ec_mS_m"],
        "fes_variant": future["selected_tide_variant"],
        "weather_input_month": future["weather_input_month"],
        "quality_status": future["quality_status"],
    }]).to_csv(OUT / "forecast_2026_11.csv", index=False)
    joblib.dump(final_model, OUT / "experimental_model.joblib")
    report = dict(status="RESEARCH_ONLY_NOT_DEPLOYED", points=points, feature_variants=CANDIDATES,
                  data_definition="Hourly FES ocean tide, local daily max-min range; midmonth is days 9-15 inclusive",
                  source="FES2022b extrapolated atlas; 2x2 native-ocean nodes selected at each point",
                  pyfes_version=pyfes.__version__, sklearn_version=sklearn.__version__,
                  model_feature_order=FEATURES + CANDIDATES[winner],
                  experimental_model_sha256=sha256(OUT / "experimental_model.joblib"),
                  collection_status_sha256=sha256(STATUS),
                  fes_config_sha256=sha256(CONFIG), evaluation=evaluation, selection=winner,
                  selection_rule="Lowest 2019-2021 validation MAE among five predeclared FES variants; holdout not used for selection",
                  baseline="Served RF weather+month features; same train/test months, RF parameters, and weather data",
                  limitations=["EC labels are monthly samples, mostly day 15, not monthly means",
                               "FES is predicted astronomical ocean tide; no local gauge or estuarine validation",
                               "FES2022b and revised ERA5 were not available in their present forms at historical issue times",
                               "2022-2023 holdout has previously been examined and is not a new blind test",
                               "No MRC EC after 2023 for verifying current forecasts",
                               "No gate-specific EC, water level, or operation inference"],
                  forecast=future, deployment_ready=False, gate_decision_eligible=False)
    (OUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(points=points, evaluation=evaluation, selection=winner, forecast=future),
                     ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
