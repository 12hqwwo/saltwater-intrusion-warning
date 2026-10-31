"""Normalize UHSLC research-quality Vung Tau-B (383B) sea level, UTC and mm."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/external/uhslc_vungtau_hourly_20261030/h383b.csv"
OUT = SOURCE.parent


def main() -> None:
    raw = pd.read_csv(SOURCE, header=None, names=["year", "month", "day", "hour", "sea_level_mm"])
    if raw.duplicated(["year", "month", "day", "hour"]).any():
        raise ValueError("Duplicate UHSLC hour")
    raw["time_utc"] = pd.to_datetime(raw[["year", "month", "day", "hour"]], utc=True)
    raw["sea_level_mm"] = raw.sea_level_mm.replace(-32767, float("nan"))
    hourly = raw[["time_utc", "sea_level_mm"]].copy()
    hourly["station"] = "UHSLC_VUNG_TAU_383B"
    hourly["time_local"] = hourly.time_utc.dt.tz_convert("Asia/Ho_Chi_Minh")
    hourly.to_csv(OUT / "vungtau_383b_hourly.csv", index=False)
    hourly["local_date"] = hourly.time_local.dt.date
    daily = hourly.groupby("local_date").sea_level_mm.agg(["count", "min", "max"])
    daily["daily_range_mm"] = daily["max"] - daily["min"]
    daily.loc[daily["count"] < 22, "daily_range_mm"] = float("nan")
    daily = daily.reset_index().rename(columns={"count": "valid_hours"})
    daily.to_csv(OUT / "vungtau_383b_daily_range.csv", index=False)
    daily_max = daily[["local_date", "max", "valid_hours"]].copy()
    daily_max["tide_max_m"] = daily_max["max"] / 1000.0
    daily_max.loc[daily_max.valid_hours < 22, "tide_max_m"] = float("nan")
    daily_max = daily_max.rename(columns={"local_date": "date"})[["date", "tide_max_m"]]
    daily_max["station"] = "VungTau"
    daily_max.to_csv(OUT / "vungtau_383b_daily_max.csv", index=False)
    manifest = {
        "station": "Vung Tau-B",
        "uhslc_id": "383B",
        "source_url": "https://uhslc.soest.hawaii.edu/data/csv/rqds/hourly/h383b.csv",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "unit": "mm relative to station zero",
        "time_source": "UTC; local dates derived with Asia/Ho_Chi_Minh",
        "source_rows": len(raw),
        "missing_sentinel_rows": int(raw.sea_level_mm.isna().sum()),
        "first_time_utc": str(hourly.time_utc.iloc[0]),
        "last_time_utc": str(hourly.time_utc.iloc[-1]),
        "valid_daily_range_min_hours": 22,
        "valid_daily_ranges": int(daily.daily_range_mm.notna().sum()),
        "availability_caution": "Research-quality archive has no historical daily publication vintages; use only pre-issue windows with an explicit assumed delay in forecast backtests.",
        "datum_caution": "Station zero is not a common river gauge datum; do not subtract absolute FES or MRC stage without datum calibration.",
        "mislabelled_legacy_file": "data/raw/tide/uhslc/uhslc_tides_VungTau_id142_daily.csv is UHSLC id142 Langkawi, Malaysia, not Vung Tau.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("source_rows", "missing_sentinel_rows", "valid_daily_ranges", "first_time_utc", "last_time_utc")}, indent=2))


if __name__ == "__main__":
    main()
