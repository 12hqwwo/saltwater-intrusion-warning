"""Generate clearly labeled partial-FES monthly tide screening, 1985–2023.

Only four of FES2022b's 34 ocean constituents are locally available. This
output must not be merged into the verified feature table or called full
FES2022b tide. PyFES performs atlas interpolation and its default inference
and long-period calculation. Times are evaluated in UTC and grouped by
calendar month in Asia/Ho_Chi_Minh (UTC+07:00).
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import numpy as np
import pyfes


ROOT = Path(__file__).resolve().parents[1]
FES_DATA = ROOT / "data/raw/tide/fes2022b/ocean_tide_extrapolated"
CONFIG = ROOT / "config/fes2022b_four_constituents.yaml"
POINTS = ROOT / "data/processed/tide/04_tide_points_checked.geojson"
LATEST = ROOT / "data/processed/tide/04_tide_points_candidates_UPDATED_20261010.csv"
OUT = ROOT / "data/processed/tide/fes4_screening"
START_YEAR, END_YEAR = 1985, 2023


def main() -> None:
    os.environ["FES_DATA"] = str(FES_DATA)
    with LATEST.open(newline="", encoding="utf-8-sig") as handle:
        latest = {row["point_code"]: row for row in csv.DictReader(handle)}
    points = json.loads(POINTS.read_text(encoding="utf-8-sig"))["features"]
    if len(points) != 3 or set(latest) != {feat["properties"]["point_code"] for feat in points}:
        raise RuntimeError("Expected exactly the three current tide candidates")
    for feature in points:
        code = feature["properties"]["point_code"]
        lon, lat = map(float, feature["geometry"]["coordinates"])
        row = latest[code]
        if abs(lat - float(row["grid_lat"])) > 1e-5 or abs(lon - float(row["grid_lon"])) > 1e-5:
            raise RuntimeError(f"Stale candidate coordinate: {code}")
        if feature["properties"].get("fes_four_constituents_check") != "PASS_FILE_SAMPLE":
            raise RuntimeError(f"Unverified FES constituent sample: {code}")
    if any(not (FES_DATA / f"{name}_fes2022.nc").exists() for name in ("m2", "s2", "k1", "o1")):
        raise RuntimeError("One or more FES constituent atlases are absent")

    config = pyfes.config.load(str(CONFIG), bbox=(106.8, 10.1, 107.0, 10.35))
    model = config.models["tide"]
    rows = []
    for feature in points:
        code = feature["properties"]["point_code"]
        lon, lat = map(float, feature["geometry"]["coordinates"])
        for year in range(START_YEAR, END_YEAR + 1):
            start_utc = np.datetime64(f"{year - 1}-12-31T17:00")
            end_utc = np.datetime64(f"{year}-12-31T17:00")
            times = np.arange(start_utc, end_utc, np.timedelta64(1, "h"))
            short_cm, long_cm, flags = pyfes.evaluate_tide(
                model, times, np.full(times.shape, lon), np.full(times.shape, lat),
                settings=config.settings)
            tide_m = (short_cm + long_cm) / 100.0
            if not np.isfinite(tide_m).all() or np.any(flags <= 0):
                raise RuntimeError(f"Undefined or extrapolated PyFES evaluation: {code}, {year}")
            local_month = (times + np.timedelta64(7, "h")).astype("datetime64[M]")
            for month in np.unique(local_month):
                values = tide_m[local_month == month]
                rows.append({
                    "point_code": code, "year_month": str(month),
                    "latitude": lat, "longitude": lon,
                    "tide_mean_m": round(float(values.mean()), 6),
                    "tide_max_m": round(float(values.max()), 6),
                    "tide_min_m": round(float(values.min()), 6),
                    "tide_range_m": round(float(values.max() - values.min()), 6),
                    "hour_count": int(values.size),
                    "min_pyfes_flag": int(flags[local_month == month].min()),
                    "quality_status": "SCREENING_FES4_NOT_FULL_FES2022B",
                })
    if len(rows) != 3 * (END_YEAR - START_YEAR + 1) * 12:
        raise RuntimeError("Monthly output row count mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "fes4_screening_monthly_1985_2023.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "manifest.json").write_text(json.dumps({
        "source_model": "FES2022b ocean_tide_extrapolated",
        "model_constituents_present": ["M2", "S2", "K1", "O1"],
        "full_model_constituent_count": 34,
        "pyfes_version": pyfes.__version__,
        "pyfes_settings": "Default FESSettings: spline inference and long-period equilibrium",
        "output_status": "SCREENING_ONLY_NOT_FULL_FES2022B_NOT_VALIDATED_AT_ESTUARY",
        "points_status": "REVIEW; mask, 3x3 native ocean, and GEBCO screening passed; coastline, datum, and tidal representativeness not independently approved",
        "time_evaluation": "UTC hourly; monthly aggregation Asia/Ho_Chi_Minh UTC+07:00",
        "start_year": START_YEAR, "end_year": END_YEAR,
        "not_joined_to_verified_features": True,
        "config": str(CONFIG), "points": str(POINTS), "output": str(output),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "points": [f["properties"]["point_code"] for f in points],
                      "pyfes": pyfes.__version__, "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
