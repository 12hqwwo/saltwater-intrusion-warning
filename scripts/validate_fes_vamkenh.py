"""Validate offshore FES tide shape against Vam Kenh telemetry, not datum."""
from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyfes

from scripts.experiment_fes_ec import ATLAS, CONFIG

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/fes_vamkenh_validation_20261029"
POINTS = {k: (v["lon"], v["lat"]) for k,v in json.loads(
    (ROOT / "outputs/fes_ec_multipoint_20261026/summary.json").read_text()
)["points"].items()}


def observed_hourly():
    folders = [ROOT / "data/external/tien_multisite_20261029_verified",
               ROOT / "data/external/tien_multisite_supplement_20261029"]
    files = [p for folder in folders for p in folder.glob("985203_Water_Level_Telemetry_*.csv")
             if "observed_at" in p.open(encoding="utf-8-sig").readline()]
    if len(files) != 2:
        raise ValueError("Need historical and recent raw Vam Kenh telemetry files")
    frame = pd.concat([pd.read_csv(p, usecols=["observed_at", "value", "unit", "quality_flag"])
                       for p in files], ignore_index=True)
    if frame.unit.ne("m").any() or frame.observed_at.duplicated().any():
        raise ValueError("Bad telemetry units or timestamps")
    frame.index = pd.to_datetime(frame.observed_at, utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
    # Use the hourly median when at least two quarter-hour samples exist.
    hourly = frame.value.resample("h").agg(["median", "count"])
    return hourly["median"].where(hourly["count"] >= 2).rename("obs_cm") * 100


def predicted_hourly():
    os.environ["FES_DATA"] = str(ATLAS.resolve())
    xs = np.array([p[0] for p in POINTS.values()])
    ys = np.array([p[1] for p in POINTS.values()])
    config = pyfes.config.load(CONFIG, bbox=(float(xs.min()-.2), float(ys.min()-.2),
                                           float(xs.max()+.2), float(ys.max()+.2)))
    frames = []
    for year in range(2019, 2027):
        local = pd.date_range(f"{year}-01-01", f"{year+1}-01-01", freq="h",
                              inclusive="left", tz="Asia/Ho_Chi_Minh")
        utc = local.tz_convert("UTC").tz_localize(None).to_numpy(dtype="datetime64[s]")
        n = len(utc)
        tide, long_period, flags = pyfes.evaluate_tide(
            config.models["tide"], np.tile(utc, len(xs)),
            np.repeat(xs, n), np.repeat(ys, n), settings=config.settings)
        if not np.isfinite(tide).all() or not np.all(flags == 4):
            raise ValueError(f"FES nonnative or missing in {year}")
        frame = pd.DataFrame(index=local)
        for i, name in enumerate(POINTS):
            frame[name] = (tide + long_period)[i*n:(i+1)*n]
        frames.append(frame)
        print("FES", year, flush=True)
    return pd.concat(frames)


def metrics(obs, tide):
    paired = pd.concat([obs,tide], axis=1).dropna()
    if len(paired) < 1000:
        return dict(n=len(paired), corr=None, anomaly_mae_cm=None)
    corr = float(paired.iloc[:,0].corr(paired.iloc[:,1]))
    return dict(n=len(paired), corr=corr,
                anomaly_mae_cm=float((paired.iloc[:,0]-paired.iloc[:,1]).abs().mean()))


def main():
    obs = observed_hourly()
    fes = predicted_hourly()
    joined = fes.join(obs, how="left")
    joined["split"] = np.select([joined.index.year <= 2021, joined.index.year <= 2023],
                                ["selection_2019_2021", "check_2022_2023"],
                                default="recent_2024_2026")
    rows = []
    daily_rows = []
    for split, group in joined.groupby("split"):
        # Both series are centered by their own daily means; no datum conversion.
        obs_anom = group.obs_cm - group.obs_cm.groupby(group.index.date).transform("mean")
        for point in POINTS:
            tide = group[point]
            tide_anom = tide - tide.groupby(group.index.date).transform("mean")
            for lag in range(0,7):
                # Positive lag means river gauge tide follows offshore FES.
                shifted = tide_anom.shift(lag, freq="h")
                result = metrics(obs_anom, shifted)
                rows.append(dict(split=split, point=point, lag_hours=lag, **result))
            # Daily ranges, using >=20 observed hourly medians and all 24 FES hours.
            oh = group.obs_cm.resample("D").agg(["min","max","count"])
            th = tide.resample("D").agg(["min","max","count"])
            days = pd.DataFrame({"obs_range_cm":(oh["max"]-oh["min"]).where(oh["count"]>=20),
                                 "fes_range_cm":(th["max"]-th["min"]).where(th["count"]==24)}).dropna()
            for day, item in days.iterrows():
                daily_rows.append(dict(date=day.date().isoformat(),split=split,point=point,
                                       obs_range_cm=float(item.obs_range_cm),
                                       fes_range_cm=float(item.fes_range_cm)))
            rows.append(dict(split=split,point=point,lag_hours="daily_range",n=len(days),
                corr=float(days.obs_range_cm.corr(days.fes_range_cm)),
                anomaly_mae_cm=float((days.obs_range_cm-days.fes_range_cm).abs().mean()),
                mean_obs_cm=float(days.obs_range_cm.mean()),mean_fes_cm=float(days.fes_range_cm.mean())))
    result = pd.DataFrame(rows)
    daily = pd.DataFrame(daily_rows)
    calibrated = []
    for point, data in daily.groupby("point"):
        train = data[data.split == "selection_2019_2021"]
        test = data[data.split == "check_2022_2023"]
        recent = data[data.split == "recent_2024_2026"]
        factor = float(np.sum(train.fes_range_cm*train.obs_range_cm) /
                       np.sum(train.fes_range_cm**2))
        for split, part in (("selection_2019_2021",train),("check_2022_2023",test),
                            ("recent_2024_2026",recent)):
            calibrated.append(dict(point=point,split=split,n=len(part),
                factor=factor,raw_mae_cm=float((part.fes_range_cm-part.obs_range_cm).abs().mean()),
                scaled_mae_cm=float((factor*part.fes_range_cm-part.obs_range_cm).abs().mean())))
    OUT.mkdir(parents=True,exist_ok=True)
    result.to_csv(OUT / "metrics.csv",index=False)
    daily.to_csv(OUT / "daily_ranges.csv",index=False)
    pd.DataFrame(calibrated).to_csv(OUT / "range_calibration.csv",index=False)
    south_factor = next(item["factor"] for item in calibrated
                        if item["point"] == "south" and item["split"] == "selection_2019_2021")
    boundary = joined[["south"]].rename(columns={"south":"fes_ocean_tide_cm"})
    boundary["fes_daily_mean_cm"] = boundary.fes_ocean_tide_cm.groupby(boundary.index.date).transform("mean")
    boundary["tidal_anomaly_cm"] = boundary.fes_ocean_tide_cm - boundary.fes_daily_mean_cm
    boundary["scaled_vamkenh_tidal_anomaly_cm"] = south_factor * boundary.tidal_anomaly_cm
    boundary.to_csv(OUT / "south_hourly_boundary_2019_2026.csv",index_label="time_local")
    grouped = boundary.fes_ocean_tide_cm.resample("D").agg(["min","max","mean"])
    grouped["fes_daily_range_cm"] = grouped["max"] - grouped["min"]
    grouped["scaled_vamkenh_daily_range_cm"] = south_factor * grouped.fes_daily_range_cm
    grouped.to_csv(OUT / "south_daily_boundary_2019_2026.csv",index_label="date_local")
    source_files = [ROOT / "data/raw/tide/fes2022b/collection_status.json", CONFIG,
        ROOT / "outputs/fes_ec_multipoint_20261026/summary.json",
        ROOT / "data/external/tien_multisite_20261029_verified/985203_Water_Level_Telemetry_9305ab16.csv",
        ROOT / "data/external/tien_multisite_supplement_20261029/985203_Water_Level_Telemetry_9305ab16.csv"]
    (OUT / "manifest.json").write_text(json.dumps(dict(
        point="south", longitude=POINTS["south"][0], latitude=POINTS["south"][1],
        source_product="FES2022b ocean_tide_extrapolated, 34 components, pyfes native four-node cell",
        gauge="MRC Vam Kenh 985203 Water Level Telemetry, quality UNVERIFIED",
        calibration_factor=south_factor, calibration_target="daily tidal range only, cm",
        data_status="MODELLED_ASTRONOMICAL_TIDE_BOUNDARY_NOT_OBSERVED_RIVER_STAGE",
        hourly_rows=len(boundary), daily_rows=len(grouped),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in source_files},
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [OUT / "south_hourly_boundary_2019_2026.csv",
                                 OUT / "south_daily_boundary_2019_2026.csv"]}),
        indent=2),encoding="utf-8")
    (OUT / "protocol.json").write_text(json.dumps(dict(
        gauge="MRC Vam Kenh 985203 Water Level Telemetry, UNVERIFIED",
        source="FES2022b extrapolated ocean tide, 3 native 2x2 ocean cells",
        timezone="Asia/Ho_Chi_Minh", unit="cm", datum_policy="daily demean; no absolute datum matching",
        gauge_hourly_requirement="at least 2 quarter-hour samples",
        gauge_day_requirement="at least 20 valid hourly medians",
        selection="2019-2021 only", independent_check="2022-2023 and 2024-2026",
        boundary_files="south_hourly_boundary_2019_2026.csv and south_daily_boundary_2019_2026.csv",
        boundary_meaning="Astronomical ocean tide and scaled tidal anomaly/range, not absolute river stage",
        caveat="FES is offshore astronomical tide; gauge includes river flow and meteorological residual; no salt transport calibration"),
        indent=2),encoding="utf-8")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
