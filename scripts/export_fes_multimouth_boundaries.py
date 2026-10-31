"""Export provisional offshore astronomical-tide series for Tien distributary mouths.

The mouth anchors are published tide-gauge coordinates, not surveyed ocean
boundary locations. Only Cua Tieu's offshore proxy has been checked against
accessible gauge telemetry; other mouth series remain unvalidated candidates.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyfes

from scripts.experiment_fes_ec import ATLAS, CONFIG, MASK, choose_native_ocean_point

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/fes_multimouth_candidates_20261029"
OUTLET_AUDIT = ROOT / "outputs/grit_delta_network_20261029/audit.json"
GAUGE_SOURCE = "https://macau.uni-kiel.de/servlets/MCRFileNodeServlet/dissertation_derivate_00004674/Thanh-Thesis_060213.pdf"
# Thanh, Table 5.1: Binh Dai, An Thuan, Ben Trai tide-gauge locations.
ANCHORS = {
    "cua_dai": (106.711222, 10.197028),
    "ham_luong": (106.605222, 9.966667),
    "co_chien": (106.529000, 9.880889),
}


def main():
    outlets = json.loads(OUTLET_AUDIT.read_text(encoding="utf-8"))["mouth_outlet_candidates"]
    for name, anchor in ANCHORS.items():
        if [outlets[name]["gauge_anchor_lon"], outlets[name]["gauge_anchor_lat"]] != list(anchor):
            raise ValueError(f"GRIT outlet gauge anchor differs for {name}")
    points = {name: choose_native_ocean_point(mask_path=MASK,
              mouth=(outlets[name]["lon"], outlets[name]["lat"])) for name in ANCHORS}
    for item in points.values():
        item["distance_to_grit_outlet_km"] = item.pop("distance_to_mouth_km")
    os.environ["FES_DATA"] = str(ATLAS.resolve())
    xs = np.array([item["lon"] for item in points.values()])
    ys = np.array([item["lat"] for item in points.values()])
    config = pyfes.config.load(CONFIG, bbox=(float(xs.min() - .2), float(ys.min() - .2),
                                           float(xs.max() + .2), float(ys.max() + .2)))
    names = list(points)
    years = []
    for year in range(2019, 2027):
        local = pd.date_range(f"{year}-01-01", f"{year+1}-01-01", freq="h",
                              inclusive="left", tz="Asia/Ho_Chi_Minh")
        utc = local.tz_convert("UTC").tz_localize(None).to_numpy(dtype="datetime64[s]")
        n = len(utc)
        tide, long_period, flags = pyfes.evaluate_tide(
            config.models["tide"], np.tile(utc, len(names)),
            np.repeat(xs, n), np.repeat(ys, n), settings=config.settings)
        if not np.isfinite(tide).all() or not np.isfinite(long_period).all() or not np.all(flags == 4):
            raise ValueError(f"Missing or non-native FES values in {year}")
        years.append(pd.DataFrame({name: (tide + long_period)[i*n:(i+1)*n]
                                   for i, name in enumerate(names)}, index=local))
        print(year, flush=True)
    hourly = pd.concat(years)
    if len(hourly) != 70128 or hourly.isna().any().any() or hourly.index.has_duplicates:
        raise ValueError("Incomplete 2019-2026 hourly series")
    daily = pd.DataFrame({name + "_range_cm": hourly[name].resample("D").max() -
                          hourly[name].resample("D").min() for name in names})
    OUT.mkdir(parents=True, exist_ok=True)
    hourly_path = OUT / "offshore_fes_hourly_2019_2026.csv"
    daily_path = OUT / "offshore_fes_daily_ranges_2019_2026.csv"
    hourly.to_csv(hourly_path, index_label="time_local")
    daily.to_csv(daily_path, index_label="date_local")
    metadata = {
        "anchor_source": GAUGE_SOURCE,
        "anchor_meaning": "published near-mouth tide gauges select provisional GRIT coastal outlets; FES cells selected from those outlets",
        "grit_outlet_audit_sha256": hashlib.sha256(OUTLET_AUDIT.read_bytes()).hexdigest(),
        "points": {name: {"gauge_anchor_lon": ANCHORS[name][0], "gauge_anchor_lat": ANCHORS[name][1],
                          "grit_outlet": outlets[name], **item,
                          "validation": "UNVALIDATED_AT_THIS_MOUTH"}
                   for name, item in points.items()},
        "product": "FES2022b ocean_tide_extrapolated, 34 constituents",
        "timezone": "Asia/Ho_Chi_Minh", "unit": "cm",
        "hourly_rows": len(hourly), "daily_rows": len(daily),
        "datum_policy": "use anomalies and ranges only; no river-gauge absolute level conversion",
        "data_status": "PROVISIONAL_OFFSHORE_ASTRONOMICAL_TIDE_NOT_OBSERVED_RIVER_STAGE",
        "output_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (hourly_path, daily_path)},
    }
    (OUT / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata["points"], indent=2))


if __name__ == "__main__":
    main()
