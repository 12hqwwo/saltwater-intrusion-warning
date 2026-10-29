"""Preserve a narrow, source-traceable salinity subset from the local 8file collection.

This is a salinity (g/L) observation extract, NOT an EC conversion or MRC label.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/8file/06_river_and_interior_salinity_ec_observations_759.csv"
STATIONS = ROOT / "data/8file/02_stations_master_catalog_63.csv"
DEST = ROOT / "data/external/new_data_search_20261029"
TARGETS = {"ST_TIEN_VAMKENH", "ST_TIEN_LONGHAI", "ST_CUATRUNG_RACHMUONG"}
REGIMES = {"PEAK_MORNING_TIDE", "PEAK_AFTERNOON_TIDE", "FIXED_07H00"}


def main() -> None:
    observations = pd.read_csv(SOURCE, encoding="utf-8-sig")
    stations = pd.read_csv(STATIONS, encoding="utf-8-sig")
    filtered = observations.loc[
        (observations["observation_group"] == "RIVER_SALINITY_SERIES")
        & observations["station_code"].isin(TARGETS)
        & observations["obs_date_or_period"].str.startswith("2026-", na=False)
        & observations["measurement_regime"].isin(REGIMES)
        & observations["obs_time_or_phase"].str.fullmatch(r"\d{2}:\d{2}", na=False)
        & observations["source_url"].str.contains("thuyloitiengiang.vn", na=False)
        & observations["salinity_observed_g_l"].notna()
    ].copy()
    assert len(filtered) == 67, f"Unexpected source count: {len(filtered)}"
    assert not filtered.duplicated(
        ["station_code", "obs_date_or_period", "obs_time_or_phase"]
    ).any(), "Duplicate station/timestamp records require manual review"

    filtered = filtered.merge(
        stations[
            ["station_code", "lat_wgs84", "lon_wgs84", "location_status"]
        ],
        on="station_code",
        how="left",
        validate="many_to_one",
    )
    assert filtered["location_status"].eq("EXACT_PLUS_CODE").all()
    filtered["local_datetime_assumed"] = (
        filtered["obs_date_or_period"] + " " + filtered["obs_time_or_phase"]
    )
    filtered["salinity_unit"] = "g/L"
    filtered["value_role"] = "reported_salinity_observation_not_direct_EC"
    filtered["qa_status"] = "source_page_spot_checked_no_instrument_QA"
    columns = [
        "obs_id", "station_code", "station_name", "lat_wgs84", "lon_wgs84",
        "location_status", "local_datetime_assumed", "measurement_regime",
        "salinity_observed_g_l", "salinity_unit", "value_role", "qa_status",
        "source_url", "notes",
    ]
    filtered = filtered[columns].sort_values(["local_datetime_assumed", "station_code"])

    DEST.mkdir(parents=True, exist_ok=True)
    out = DEST / "official_tiengiang_salinity_2026_sep_oct_preserved.csv"
    filtered.to_csv(out, index=False, encoding="utf-8-sig")
    manifest = {
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output": str(out.relative_to(ROOT)).replace("\\", "/"),
        "rows": len(filtered),
        "station_counts": filtered["station_code"].value_counts().to_dict(),
        "unique_dates": filtered["local_datetime_assumed"].str[:10].nunique(),
        "date_start": filtered["local_datetime_assumed"].min(),
        "date_end": filtered["local_datetime_assumed"].max(),
        "source_urls": sorted(filtered["source_url"].unique().tolist()),
        "caveats": [
            "Not EC; no validated salinity-to-EC transformation at high salinity.",
            "Source pages report peak/07:00 salinity; no sensor type, depth, salinity derivation, QA flags, or historical publication timestamp per reading.",
            "Local time is inferred from Vietnamese operator bulletins, not an explicit time-zone field.",
            "Only 12 sampled dates in Sep-Oct 2026; insufficient to calibrate seasonal propagation or validate the 2019-2023 MRC backtest.",
        ],
    }
    (DEST / "official_tiengiang_salinity_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"output": str(out), "rows": len(filtered)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
