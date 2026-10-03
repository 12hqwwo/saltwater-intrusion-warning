"""Build ``monthly_feature_v2`` at one location x one month grain.

Only QA-VERIFIED EC is eligible as a target. Tân Châu discharge is never
copied into Mỹ Tho rows. FES2022 tide columns remain NULL until the required
FES outputs exist.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURE_DIR = DATA_DIR / "features"

EC_FILE = PROCESSED_DIR / "ec" / "03_ec_clean.csv"
TIDE_FILE = PROCESSED_DIR / "tide" / "06_tide_monthly.csv"
METEO_FILE = RAW_DIR / "meteorology" / "openmeteo" / "openmeteo_all_stations_daily.csv"
GLOFAS_DIR = RAW_DIR / "glofas" / "tanchau"
OUTPUT_FILE = FEATURE_DIR / "10_monthly_feature_v2.csv"

FEATURE_MONTHS = pd.period_range("1985-01", "2026-08", freq="M").astype(str)
TRAIN_TARGET_END = "2023-12"
TANCHAU_LAT = 10.80062008
TANCHAU_LON = 105.2480164


def load_ec_monthly() -> pd.DataFrame:
    frame = pd.read_csv(EC_FILE)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["year_month"] = frame["timestamp"].dt.strftime("%Y-%m")
    verified = frame[
        frame["quality_flag"].eq("VERIFIED")
        & frame["clean_value"].notna()
        & frame["timestamp"].notna()
    ].copy()
    monthly = verified.groupby(["station", "year_month"], as_index=False).agg(
        ec_target=("clean_value", "mean"),
        ec_n=("clean_value", "count"),
        ec_source=("source", "first"),
        ec_snapshot_id=("snapshot_id", "first"),
    )
    monthly["ec_quality_flag"] = "VERIFIED"
    return monthly


def load_glofas_tanchau() -> pd.DataFrame:
    """Extract the nearest Tân Châu grid cell; retain unverified-cell provenance."""
    records: list[dict[str, object]] = []
    selected_cell: tuple[float, float] | None = None
    for path in sorted(GLOFAS_DIR.glob("glofas_*.nc")):
        with xr.open_dataset(path) as dataset:
            if "avg_dis" not in dataset.data_vars:
                continue
            lat_name = "latitude" if "latitude" in dataset.coords else "lat"
            lon_name = "longitude" if "longitude" in dataset.coords else "lon"
            time_name = next((name for name in dataset.coords if "time" in name.lower()), None)
            if time_name is None:
                continue
            point = dataset["avg_dis"].sel(
                {lat_name: TANCHAU_LAT, lon_name: TANCHAU_LON}, method="nearest"
            )
            cell = (
                float(point[lat_name].values),
                float(point[lon_name].values),
            )
            if selected_cell is None:
                selected_cell = cell
            elif cell != selected_cell:
                raise ValueError(f"GloFAS grid cell changed across snapshots: {selected_cell} vs {cell}")
            times = pd.to_datetime(dataset[time_name].values).ravel()
            values = np.asarray(point.values).ravel()
            records.extend(
                {"date": timestamp, "discharge_m3s": float(value)}
                for timestamp, value in zip(times, values)
                if not np.isnan(value)
            )

    if not records or selected_cell is None:
        return pd.DataFrame()
    daily = pd.DataFrame(records).sort_values("date").drop_duplicates("date")
    daily["year_month"] = daily["date"].dt.to_period("M").astype(str)
    monthly = daily.groupby("year_month", as_index=False).agg(
        discharge_mean=("discharge_m3s", "mean"),
        discharge_max=("discharge_m3s", "max"),
    )
    monthly["discharge_source"] = "Copernicus_GloFAS"
    monthly["discharge_version"] = "ERA5_V4"
    monthly["discharge_snapshot_id"] = "TANCHAU_1985_2023_FILES"
    monthly["discharge_quality_flag"] = "SUSPECT"
    monthly["discharge_grid_lat"] = selected_cell[0]
    monthly["discharge_grid_lon"] = selected_cell[1]
    return monthly


def load_dahiti() -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    for station in ("TanChau", "MyTho"):
        path = STAGING_DIR / "dahiti" / f"dahiti_{station}_monthly.csv"
        if path.exists():
            result[station] = pd.read_csv(path)
    return result


def load_fes_tide() -> pd.DataFrame:
    """Load only the required FES product; UHSLC is not substituted for FES."""
    if not TIDE_FILE.exists():
        return pd.DataFrame()
    frame = pd.read_csv(TIDE_FILE)
    required = {"year_month", "tide_mean", "tide_max", "tide_range", "model_name"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{TIDE_FILE} lacks required columns: {sorted(required - set(frame.columns))}")
    if not frame["model_name"].astype(str).str.contains("FES2022", case=False).all():
        raise ValueError("06_tide_monthly.csv is not exclusively sourced from FES2022")
    aggregations = {
        "tide_mean": "mean",
        "tide_max": "max",
        "tide_range": "mean",
    }
    monthly = frame.groupby("year_month", as_index=False).agg(aggregations)
    monthly["tide_source"] = "FES2022b_PyFES"
    monthly["tide_snapshot_id"] = frame.get("snapshot_id", pd.Series(["UNKNOWN"])).iloc[0]
    monthly["tide_quality_flag"] = "VERIFIED"
    return monthly


def load_meteorology() -> pd.DataFrame:
    """Use one canonical file to avoid multiplying duplicated downloads."""
    frame = pd.read_csv(METEO_FILE)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date", "station"])
    duplicate_keys = frame.duplicated(["station", "date"]).sum()
    if duplicate_keys:
        raise ValueError(f"Canonical Open-Meteo file has {duplicate_keys} duplicate station/date rows")
    frame["year_month"] = frame["date"].dt.to_period("M").astype(str)
    monthly = frame.groupby(["station", "year_month"], as_index=False).agg(
        rainfall=("precipitation_sum", "sum"),
        temperature=("temperature_2m_mean", "mean"),
        wind=("windspeed_10m_max", "mean"),
    )
    monthly["meteorology_source"] = "Open-Meteo_ERA5-Land"
    monthly["meteorology_snapshot_id"] = "OPENMETEO_2026-09-02"
    monthly["meteorology_quality_flag"] = "VERIFIED"
    return monthly


def build_station_features(
    station: str,
    ec: pd.DataFrame,
    glofas_tanchau: pd.DataFrame,
    dahiti: dict[str, pd.DataFrame],
    tide: pd.DataFrame,
    meteo: pd.DataFrame,
) -> pd.DataFrame:
    frame = pd.DataFrame({"location_id": station, "year_month": FEATURE_MONTHS})
    station_ec = ec[ec["station"].eq(station)].drop(columns="station")
    frame = frame.merge(station_ec, on="year_month", how="left", validate="one_to_one")

    frame["ec_lag_1"] = frame["ec_target"].shift(1)
    frame["ec_lag_2"] = frame["ec_target"].shift(2)
    frame["ec_lag_3"] = frame["ec_target"].shift(3)
    frame["ec_lag_12"] = frame["ec_target"].shift(12)
    parsed_month = pd.to_datetime(frame["year_month"], format="%Y-%m")
    frame["month"] = parsed_month.dt.month
    frame["season"] = frame["month"].map(
        {
            12: "dry", 1: "dry", 2: "dry", 3: "dry",
            4: "transition", 5: "transition",
            6: "wet", 7: "wet", 8: "wet", 9: "wet", 10: "wet", 11: "wet",
        }
    )

    station_meteo = meteo[meteo["station"].eq(station)].drop(columns="station")
    frame = frame.merge(station_meteo, on="year_month", how="left", validate="one_to_one")

    if station == "TanChau" and not glofas_tanchau.empty:
        frame = frame.merge(glofas_tanchau, on="year_month", how="left", validate="one_to_one")
    else:
        for column in (
            "discharge_mean", "discharge_max", "discharge_source", "discharge_version",
            "discharge_snapshot_id", "discharge_quality_flag", "discharge_grid_lat",
            "discharge_grid_lon",
        ):
            frame[column] = np.nan
        frame["discharge_quality_flag"] = "MISSING"

    station_dahiti = dahiti.get(station, pd.DataFrame())
    if not station_dahiti.empty:
        keep = [
            "year_month", "dahiti_wl_mean", "dahiti_available", "source",
            "snapshot_id", "quality_flag",
        ]
        station_dahiti = station_dahiti[keep].rename(
            columns={
                "dahiti_wl_mean": "dahiti",
                "source": "dahiti_source",
                "snapshot_id": "dahiti_snapshot_id",
                "quality_flag": "dahiti_quality_flag",
            }
        )
        frame = frame.merge(station_dahiti, on="year_month", how="left", validate="one_to_one")
    else:
        frame["dahiti"] = np.nan
        frame["dahiti_available"] = False
        frame["dahiti_source"] = np.nan
        frame["dahiti_snapshot_id"] = np.nan
        frame["dahiti_quality_flag"] = "MISSING"
    frame["dahiti_available"] = frame["dahiti_available"].fillna(False).astype(bool)
    frame["dahiti_quality_flag"] = frame["dahiti_quality_flag"].fillna("MISSING")

    if not tide.empty:
        frame = frame.merge(tide, on="year_month", how="left", validate="one_to_one")
    else:
        frame["tide_mean"] = np.nan
        frame["tide_max"] = np.nan
        frame["tide_range"] = np.nan
        frame["tide_source"] = np.nan
        frame["tide_snapshot_id"] = np.nan
        frame["tide_quality_flag"] = "MISSING"

    frame["split_type"] = "inference_only"
    train_mask = frame["year_month"].le(TRAIN_TARGET_END) & frame["ec_target"].notna()
    frame.loc[train_mask, "split_type"] = "train_candidate"
    frame["feature_snapshot_id"] = "MONTHLY_FEATURE_V2_2026-10-03"
    return frame


def main() -> None:
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    ec = load_ec_monthly()
    glofas = load_glofas_tanchau()
    dahiti = load_dahiti()
    tide = load_fes_tide()
    meteo = load_meteorology()
    output = pd.concat(
        [
            build_station_features(station, ec, glofas, dahiti, tide, meteo)
            for station in ("TanChau", "MyTho")
        ],
        ignore_index=True,
    )
    if output.duplicated(["location_id", "year_month"]).any():
        raise ValueError("monthly_feature_v2 grain violation")
    output.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUTPUT_FILE} ({len(output)} rows)")
    print(output.groupby("location_id")[["ec_target", "discharge_mean", "tide_mean", "dahiti"]].count())


if __name__ == "__main__":
    main()
