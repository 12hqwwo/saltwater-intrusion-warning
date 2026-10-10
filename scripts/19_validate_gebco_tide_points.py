#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEBCO independent bathymetry screening for the three TLCN FES2022b tide candidates.

This is a SCREEN, not final shoreline / datum / representation verification.
Keep validation_status=REVIEW. Do not create final 04_tide_points.geojson here.

From D:\\Study\\TLCN:
    .\\.venv-api\\Scripts\\python.exe .\\scripts\\19_validate_gebco_tide_points.py `
        --gebco .\\data\\raw\\gis\\bathymetry\\GEBCO_2026_subset.nc

Optional: --tid .\\data\\raw\\gis\\bathymetry\\GEBCO_2026_TID_subset.nc
Requires Python packages already used by step 18: xarray and numpy.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "processed" / "tide"
INPUT = DIRECTORY / "04_tide_points_checked.geojson"
LATEST_CSV = DIRECTORY / "04_tide_points_candidates_UPDATED_20261010.csv"
OUTPUT = DIRECTORY / "04_tide_points_gebco_review.geojson"
CSV_OUTPUT = DIRECTORY / "04_tide_points_gebco_validation.csv"
EXPECTED_CODES = {"TIDE_CUA_TIEU", "TIDE_MIDDLE", "TIDE_CUA_DAI"}


def resolve_path(value: str | Path) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (ROOT / p)


def fail(message: str) -> None:
    raise SystemExit("ERROR: " + message)


def select_names(ds: xr.Dataset, preferred: tuple[str, ...]) -> tuple[str, str, str]:
    lat = next((k for k in ("lat", "latitude", "y") if k in ds.coords), None)
    lon = next((k for k in ("lon", "longitude", "x") if k in ds.coords), None)
    var = next((k for k in preferred if k in ds.data_vars), None)
    if lat is None or lon is None or var is None:
        fail(f"Unsupported NetCDF structure: coords={list(ds.coords)}, vars={list(ds.data_vars)}")
    if lat not in ds[var].dims or lon not in ds[var].dims or ds[var].ndim != 2:
        fail(f"Variable {var!r} must have exactly two spatial dimensions ({lat}, {lon})")
    return lat, lon, var


def sample(ds: xr.Dataset, preferred: tuple[str, ...], lat: float, lon: float) -> dict:
    lat_name, lon_name, var_name = select_names(ds, preferred)
    ys = np.asarray(ds.coords[lat_name].values, dtype=float)
    xs = np.asarray(ds.coords[lon_name].values, dtype=float)
    if ys.ndim != 1 or xs.ndim != 1 or not np.isfinite(ys).all() or not np.isfinite(xs).all():
        fail("NetCDF coordinates must be valid 1D lat/lon arrays")
    if not (min(ys) <= lat <= max(ys) and min(xs) <= lon <= max(xs)):
        fail(f"Point ({lat}, {lon}) lies outside GEBCO subset extent: "
             f"latitude {min(ys)}..{max(ys)}, longitude {min(xs)}..{max(xs)}")
    yi, xi = int(np.argmin(abs(ys - lat))), int(np.argmin(abs(xs - lon)))
    distance = max(abs(float(ys[yi]) - lat), abs(float(xs[xi]) - lon))
    # GEBCO native grid is 15 arc-seconds (~0.004167 deg).
    if distance > 0.01:
        fail(f"Nearest cell is too far ({distance:.6f} degrees) at point ({lat}, {lon}). "
             "Use a GEBCO native-resolution subset containing your points.")
    val = float(ds[var_name].isel({lat_name: yi, lon_name: xi}).values)
    neighborhood = np.asarray(ds[var_name].isel({
        lat_name: slice(max(0, yi - 1), min(len(ys), yi + 2)),
        lon_name: slice(max(0, xi - 1), min(len(xs), xi + 2)),
    }).values, dtype=float)
    good = np.isfinite(neighborhood)
    return {
        "value": val,
        "center_lon": float(xs[xi]),
        "center_lat": float(ys[yi]),
        "neighbor_finite": int(good.sum()),
        "neighbor_negative": int(np.logical_and(good, neighborhood < 0).sum()),
        "neighbor_cells": int(neighborhood.size),
    }


def verify_latest_coordinates(features: list[dict]) -> None:
    if not LATEST_CSV.exists():
        fail(f"Latest point inventory is missing: {LATEST_CSV}. "
             "Cannot rule out using stale FES candidate coordinates.")
    with LATEST_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        latest = {r["point_code"]: r for r in csv.DictReader(f)}
    codes = {f["properties"]["point_code"] for f in features}
    if codes != EXPECTED_CODES or set(latest) != EXPECTED_CODES:
        fail(f"Expected exactly three named tide points; got GeoJSON={codes}, CSV={set(latest)}")
    for feature in features:
        props = feature["properties"]
        code = props["point_code"]
        expected = latest[code]
        lon, lat = [float(v) for v in feature["geometry"]["coordinates"]]
        exp_lat, exp_lon = float(expected["grid_lat"]), float(expected["grid_lon"])
        if abs(lat - exp_lat) > 1e-5 or abs(lon - exp_lon) > 1e-5:
            fail(f"STALE POINT {code}: GeoJSON ({lat:.9f}, {lon:.9f}) != "
                 f"latest CSV ({exp_lat:.9f}, {exp_lon:.9f}). "
                 "Replace 04_tide_points_candidates.geojson with the updated copy "
                 "and RE-RUN step 18 before step 19.")
        if props.get("fes_four_constituents_check") != "PASS_FILE_SAMPLE":
            fail(f"{code}: step 18 has not passed for UPDATED coordinates. Re-run step 18.")
        for pkey, csvkey in (("m2_amplitude_cm", "m2_amplitude_cm"),
                             ("m2_phase_deg", "m2_phase_deg")):
            if not math.isclose(float(props[pkey]), float(expected[csvkey]), abs_tol=0.05):
                fail(f"{code}: latest CSV and verified FES file sample disagree on {pkey}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gebco", required=True, help="Path to a local GEBCO subset NetCDF containing the three points")
    parser.add_argument("--tid", help="Optional GEBCO Type Identifier grid NetCDF for the SAME release")
    args = parser.parse_args()
    gebco_file = resolve_path(args.gebco)
    tid_file = resolve_path(args.tid) if args.tid else None
    if not gebco_file.is_file():
        fail(f"Missing GEBCO NetCDF file: {gebco_file}. Download a REGIONAL subset first.")
    if tid_file is not None and not tid_file.is_file():
        fail(f"Missing GEBCO TID NetCDF: {tid_file}")
    if not INPUT.is_file():
        fail(f"Missing step-18 output: {INPUT}. Run script 18 first.")
    payload = json.loads(INPUT.read_text(encoding="utf-8-sig"))
    features = payload.get("features")
    if not isinstance(features, list) or len(features) != 3:
        fail("Step-18 output should contain exactly three FeatureCollection features")
    # Critical guard: step 18 in the supplied repository reads an OLD canonical GeoJSON.
    verify_latest_coordinates(features)
    with LATEST_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        latest = {r["point_code"]: r for r in csv.DictReader(f)}
    rows: list[dict] = []
    with xr.open_dataset(gebco_file) as gebco:
        tid_data = xr.open_dataset(tid_file) if tid_file else None
        try:
            for feature in features:
                props = feature["properties"]
                code = props["point_code"]
                lon, lat = map(float, feature["geometry"]["coordinates"])
                cell = sample(gebco, ("elevation", "z", "Band1"), lat, lon)
                elevation = cell["value"]
                if not math.isfinite(elevation):
                    status = "REVIEW_GEBCO_MISSING"
                elif elevation >= 0:
                    status = "REVIEW_NONNEGATIVE_ELEVATION"
                else:
                    status = "PASS_NEGATIVE_BATHY_SAMPLE"
                notes: list[str] = []
                if status != "PASS_NEGATIVE_BATHY_SAMPLE":
                    notes.append("GEBCO center is not a negative finite bathymetry value")
                if cell["neighbor_finite"] != 9:
                    notes.append("GEBCO complete 3x3 neighborhood not available")
                elif cell["neighbor_negative"] < 9:
                    notes.append("GEBCO 3x3 includes nonnegative cells; review shoreline carefully")
                if math.isfinite(elevation) and -5 <= elevation < 0:
                    notes.append("Shallow depth <=5 m; GEBCO coastal uncertainty may be material")
                recorded = latest[code].get("gebco_elevation_m", "")
                if recorded.strip():
                    old_elevation = float(recorded)
                    if math.isfinite(elevation) and abs(old_elevation - elevation) > 2:
                        notes.append(f"Current GEBCO sample differs >2 m from 2026-10-10 QGIS CSV ({old_elevation} m)")
                tid_val = None
                if tid_data is not None:
                    raw_tid = sample(tid_data, ("tid", "TID", "type_identifier", "z", "Band1"), lat, lon)["value"]
                    if math.isfinite(raw_tid):
                        tid_val = int(raw_tid)
                        if tid_val == 40:
                            notes.append("TID 40 is modeled/satellite-gravity-guided interpolation, not direct sounding")
                        if (latest[code].get("gebco_tid") or "").strip() and tid_val != int(latest[code]["gebco_tid"]):
                            notes.append("TID differs from updated CSV; check GEBCO release and grid")
                props["gebco_bathy_screen"] = status
                props["gebco_elevation_m_sampled"] = elevation if math.isfinite(elevation) else None
                props["gebco_grid_center_lon"] = cell["center_lon"]
                props["gebco_grid_center_lat"] = cell["center_lat"]
                props["gebco_neighbor_negative_3x3"] = cell["neighbor_negative"]
                props["gebco_neighbor_cells_3x3"] = cell["neighbor_cells"]
                props["gebco_source_filename"] = gebco_file.name
                props["gebco_tid_sampled"] = tid_val
                props["gebco_bathy_notes"] = "; ".join(notes) or "Negative bathymetric model cell; coast and role still unverified"
                props["validation_status"] = "REVIEW"
                props["coastline_verified"] = False
                # Deliberately do not modify coastline_check or model_datum_check.
                rows.append({
                    "point_code": code,
                    "latitude": lat,
                    "longitude": lon,
                    "fes_four_constituents_check": props["fes_four_constituents_check"],
                    "gebco_elevation_m": props["gebco_elevation_m_sampled"],
                    "gebco_tid_sampled": tid_val if tid_val is not None else "NOT_SAMPLED",
                    "gebco_3x3_negative_count": cell["neighbor_negative"],
                    "gebco_3x3_cell_count": cell["neighbor_cells"],
                    "gebco_bathy_screen": status,
                    "validation_status": "REVIEW",
                    "notes": props["gebco_bathy_notes"],
                })
                print(f"{code} => {status}, elevation={elevation:.1f} m, still REVIEW")
        finally:
            if tid_data is not None:
                tid_data.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Saved:", OUTPUT)
    print("Saved:", CSV_OUTPUT)
    print("IMPORTANT: Negative GEBCO elevation != shoreline VERIFIED. Validate coastline, representative role, and FES datum separately.")


if __name__ == "__main__":
    main()
