#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate GloFAS v4 cells for Tân Châu and Mỹ Tho.

Place this file at:
    pipelines/etl/15_validate_glofas_cells.py

Required project files:
    data/raw/glofas/aux/v4/uparea_glofas_v4_0.nc
    data/raw/glofas/aux/v4/ldd_glofas_v4_0.nc
    data/raw/glofas/tanchau/*.nc

Optional:
    data/raw/glofas/mytho/*.nc

Outputs:
    data/processed/glofas/glofas_candidates_TanChau.csv
    data/processed/glofas/glofas_candidates_TanChau.geojson
    data/processed/glofas/glofas_candidates_MyTho.csv
    data/processed/glofas/glofas_candidates_MyTho.geojson
    data/processed/glofas/glofas_static_screening_summary.csv

The script DOES NOT automatically mark a cell VERIFIED.
It only prepares evidence for QGIS/manual validation.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "glofas"
AUX = RAW / "aux" / "v4"
OUT = ROOT / "data" / "processed" / "glofas"

UPAREA_FILE = AUX / "uparea_glofas_v4_0.nc"
LDD_FILE = AUX / "ldd_glofas_v4_0.nc"

STATIONS = {
    "TanChau": {
        "lat": 10.80062008,
        "lon": 105.2480164,
        "discharge_dir": RAW / "tanchau",
        "radius_km": 20.0,
    },
    "MyTho": {
        "lat": 10.35912163,
        "lon": 106.3529997,
        "discharge_dir": RAW / "mytho",
        "radius_km": 30.0,
    },
}

LDD_DIRECTION = {
    1: "SW",
    2: "S",
    3: "SE",
    4: "W",
    5: "PIT",
    6: "E",
    7: "NW",
    8: "N",
    9: "NE",
    255: "MISSING",
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def open_aux():
    if not UPAREA_FILE.exists():
        raise FileNotFoundError(UPAREA_FILE)
    if not LDD_FILE.exists():
        raise FileNotFoundError(LDD_FILE)

    up = xr.open_dataset(UPAREA_FILE, decode_times=False)
    ldd = xr.open_dataset(LDD_FILE, decode_times=False)

    up_lat = "latitude" if "latitude" in up.coords else "lat"
    up_lon = "longitude" if "longitude" in up.coords else "lon"
    ldd_lat = "latitude" if "latitude" in ldd.coords else "lat"
    ldd_lon = "longitude" if "longitude" in ldd.coords else "lon"

    return up, ldd, up_lat, up_lon, ldd_lat, ldd_lon


def aux_value(ds, var: str, lat_name: str, lon_name: str, lat: float, lon: float):
    value = ds[var].sel({lat_name: lat, lon_name: lon}, method="nearest").item()
    if isinstance(value, np.generic):
        value = value.item()
    return value


def discharge_grid_stats(folder: Path) -> pd.DataFrame:
    files = sorted(folder.glob("*.nc"))
    if not files:
        return pd.DataFrame()

    sums = None
    counts = None
    totals = 0
    lats = None
    lons = None

    for file in files:
        with xr.open_dataset(file, decode_times=False) as ds:
            var = "avg_dis" if "avg_dis" in ds.data_vars else list(ds.data_vars)[0]
            lat_name = "latitude" if "latitude" in ds.coords else "lat"
            lon_name = "longitude" if "longitude" in ds.coords else "lon"

            data = np.asarray(ds[var].values, dtype="float64")
            if data.ndim != 3:
                raise ValueError(f"{file}: expected discharge array [time, lat, lon], got {data.shape}")

            if lats is None:
                lats = np.asarray(ds[lat_name].values, dtype=float)
                lons = np.asarray(ds[lon_name].values, dtype=float)
                sums = np.zeros((len(lats), len(lons)), dtype=float)
                counts = np.zeros((len(lats), len(lons)), dtype=np.int64)
            else:
                if not np.allclose(lats, np.asarray(ds[lat_name].values, dtype=float)):
                    raise ValueError(f"{file}: latitude grid changed")
                if not np.allclose(lons, np.asarray(ds[lon_name].values, dtype=float)):
                    raise ValueError(f"{file}: longitude grid changed")

            valid = np.isfinite(data)
            sums += np.nansum(data, axis=0)
            counts += valid.sum(axis=0)
            totals += data.shape[0]

    rows = []
    for j, lat in enumerate(lats):
        for i, lon in enumerate(lons):
            n = int(counts[j, i])
            rows.append(
                {
                    "grid_lat": float(lat),
                    "grid_lon": float(lon),
                    "mean_discharge_m3s": float(sums[j, i] / n) if n else np.nan,
                    "valid_timesteps": n,
                    "total_timesteps": int(totals),
                    "missing_fraction": float(1 - n / totals) if totals else np.nan,
                }
            )
    return pd.DataFrame(rows)


def static_candidates(
    station: str,
    lat0: float,
    lon0: float,
    radius_km: float,
    up,
    ldd,
    up_lat: str,
    up_lon: str,
    ldd_lat: str,
    ldd_lon: str,
) -> pd.DataFrame:
    lats = np.asarray(up[up_lat].values, dtype=float)
    lons = np.asarray(up[up_lon].values, dtype=float)

    # ~0.05° GloFAS grid. Search a generous index window.
    iy = int(np.argmin(np.abs(lats - lat0)))
    ix = int(np.argmin(np.abs(lons - lon0)))
    half = int(math.ceil(radius_km / 4.5)) + 3

    rows = []
    for j in range(max(0, iy - half), min(len(lats), iy + half + 1)):
        for i in range(max(0, ix - half), min(len(lons), ix + half + 1)):
            lat = float(lats[j])
            lon = float(lons[i])
            dist = haversine_km(lat0, lon0, lat, lon)
            if dist > radius_km:
                continue

            uparea = float(up["uparea"].values[j, i])
            fill = up["uparea"].attrs.get("_FillValue")
            if fill is not None and np.isclose(uparea, float(fill)):
                uparea = np.nan
            if uparea < 0:
                uparea = np.nan

            ldd_code = int(
                ldd["ldd"].sel({ldd_lat: lat, ldd_lon: lon}, method="nearest").item()
            )

            rows.append(
                {
                    "station": station,
                    "station_lat": lat0,
                    "station_lon": lon0,
                    "grid_lat": lat,
                    "grid_lon": lon,
                    "distance_km": dist,
                    "upstream_area_m2": uparea,
                    "upstream_area_km2": uparea / 1e6 if np.isfinite(uparea) else np.nan,
                    "ldd_code": ldd_code,
                    "ldd_direction": LDD_DIRECTION.get(ldd_code, "UNKNOWN"),
                    "selection_status": "REVIEW",
                }
            )
    return pd.DataFrame(rows)


def merge_discharge(static: pd.DataFrame, discharge: pd.DataFrame) -> pd.DataFrame:
    if discharge.empty:
        out = static.copy()
        out["mean_discharge_m3s"] = np.nan
        out["valid_timesteps"] = 0
        out["total_timesteps"] = 0
        out["missing_fraction"] = np.nan
        out["discharge_available"] = False
        return out

    # When discharge data exists, only cells present in the downloaded discharge grid matter.
    out = discharge.merge(
        static,
        on=["grid_lat", "grid_lon"],
        how="left",
        validate="one_to_one",
    )
    out["discharge_available"] = True
    return out


def to_geojson(df: pd.DataFrame, path: Path) -> None:
    features = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, (np.floating, float)) and (np.isnan(v) or np.isinf(v)):
                clean[k] = None
            elif isinstance(v, np.generic):
                clean[k] = v.item()
            else:
                clean[k] = v

        features.append(
            {
                "type": "Feature",
                "properties": clean,
                "geometry": {
                    "type": "Point",
                    "coordinates": [clean["grid_lon"], clean["grid_lat"]],
                },
            }
        )
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def rank_for_review(df: pd.DataFrame, max_rows: int = 30) -> pd.DataFrame:
    # No automatic winner: keep nearest cells and largest-upstream-area cells.
    if df.empty:
        return df

    nearest = df.sort_values(["distance_km"]).head(15)
    largest = df.sort_values(["upstream_area_m2", "distance_km"], ascending=[False, True]).head(15)
    out = (
        pd.concat([nearest, largest], ignore_index=True)
        .drop_duplicates(["grid_lat", "grid_lon"])
        .sort_values(["distance_km", "upstream_area_m2"], ascending=[True, False])
        .head(max_rows)
        .reset_index(drop=True)
    )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    up, ldd, up_lat, up_lon, ldd_lat, ldd_lon = open_aux()

    summary_rows = []

    for station, cfg in STATIONS.items():
        static = static_candidates(
            station,
            cfg["lat"],
            cfg["lon"],
            cfg["radius_km"],
            up,
            ldd,
            up_lat,
            up_lon,
            ldd_lat,
            ldd_lon,
        )

        discharge = discharge_grid_stats(cfg["discharge_dir"])

        if not discharge.empty:
            # Discharge grid may be smaller than static search radius.
            # Attach auxiliary values exactly to those discharge cells.
            rows = []
            for rec in discharge.to_dict(orient="records"):
                lat = rec["grid_lat"]
                lon = rec["grid_lon"]
                uparea = aux_value(up, "uparea", up_lat, up_lon, lat, lon)
                ldd_code = int(aux_value(ldd, "ldd", ldd_lat, ldd_lon, lat, lon))
                rec.update(
                    {
                        "station": station,
                        "station_lat": cfg["lat"],
                        "station_lon": cfg["lon"],
                        "distance_km": haversine_km(cfg["lat"], cfg["lon"], lat, lon),
                        "upstream_area_m2": float(uparea),
                        "upstream_area_km2": float(uparea) / 1e6,
                        "ldd_code": ldd_code,
                        "ldd_direction": LDD_DIRECTION.get(ldd_code, "UNKNOWN"),
                        "selection_status": "REVIEW",
                        "discharge_available": True,
                    }
                )
                rows.append(rec)
            candidates = pd.DataFrame(rows).sort_values("distance_km")
        else:
            candidates = rank_for_review(static)
            candidates["mean_discharge_m3s"] = np.nan
            candidates["valid_timesteps"] = 0
            candidates["total_timesteps"] = 0
            candidates["missing_fraction"] = np.nan
            candidates["discharge_available"] = False

        csv_path = OUT / f"glofas_candidates_{station}.csv"
        geojson_path = OUT / f"glofas_candidates_{station}.geojson"
        candidates.to_csv(csv_path, index=False, encoding="utf-8-sig")
        to_geojson(candidates, geojson_path)

        nearest = candidates.sort_values("distance_km").iloc[0]
        largest = candidates.sort_values("upstream_area_m2", ascending=False).iloc[0]

        summary_rows.append(
            {
                "station": station,
                "discharge_files_present": bool(list(cfg["discharge_dir"].glob("*.nc"))),
                "candidate_count": len(candidates),
                "nearest_grid_lat": nearest["grid_lat"],
                "nearest_grid_lon": nearest["grid_lon"],
                "nearest_distance_km": nearest["distance_km"],
                "nearest_upstream_area_km2": nearest["upstream_area_km2"],
                "largest_grid_lat": largest["grid_lat"],
                "largest_grid_lon": largest["grid_lon"],
                "largest_upstream_area_km2": largest["upstream_area_km2"],
                "largest_distance_km": largest["distance_km"],
            }
        )

        print(f"\n=== {station} ===")
        cols = [
            "grid_lat", "grid_lon", "distance_km", "upstream_area_km2",
            "ldd_code", "ldd_direction", "mean_discharge_m3s",
            "missing_fraction", "selection_status",
        ]
        print(candidates[cols].head(30).to_string(index=False))
        print(f"Wrote: {csv_path}")
        print(f"Wrote: {geojson_path}")

    summary = pd.DataFrame(summary_rows)
    summary_path = OUT / "glofas_static_screening_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"\nWrote: {summary_path}")

    up.close()
    ldd.close()


if __name__ == "__main__":
    main()
