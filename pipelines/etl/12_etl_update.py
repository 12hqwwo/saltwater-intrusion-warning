"""ETL v2: EC QA, GloFAS Mỹ Tho status, DAHITI staging, and gate QA.

Raw files are read-only inputs. Derived files are written below ``data/staging``
or ``data/processed``. Missing external sources stay NULL; the pipeline never
copies Tân Châu GloFAS values to Mỹ Tho.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_EC_DIR = RAW_DIR / "ec" / "mrc"
RAW_DAHITI_DIR = RAW_DIR / "dahiti"
RAW_GATE_DIR = RAW_DIR / "gis" / "gates"

EC_OUTPUT_DIR = PROCESSED_DIR / "ec"
GLOFAS_OUTPUT_DIR = PROCESSED_DIR / "glofas"
GATE_OUTPUT_DIR = PROCESSED_DIR / "gis"
DAHITI_STAGING_DIR = STAGING_DIR / "dahiti"

MRC_SNAPSHOT_ID = "MRC_EXPORT_2026-08-31"
DAHITI_VERSION = "API_V2"
GLOFAS_VERSION = "ERA5_V4"
FEATURE_END = "2026-08-31"

STATIONS = {
    "019803": "TanChau",
    "019805": "MyTho",
}


def ensure_output_dirs() -> None:
    for path in (EC_OUTPUT_DIR, GLOFAS_OUTPUT_DIR, GATE_OUTPUT_DIR, DAHITI_STAGING_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _station_code(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)


def load_raw_ec(station_code: str, station_label: str) -> pd.DataFrame:
    """Load exactly one MRC station file and validate its embedded station code."""
    matches = sorted(RAW_EC_DIR.glob(f"*{station_code}*.csv"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one raw EC CSV for {station_label}/{station_code}; found {len(matches)}"
        )

    frame = pd.read_csv(matches[0])
    frame.columns = [column.strip() for column in frame.columns]
    required = {
        "Station Code",
        "Timestamp (UTC+07:00)",
        "Value",
        "Unit",
        "Observed or Estimated",
        "Approval Level",
        "Grade",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{matches[0].name} is missing columns: {sorted(missing)}")

    frame = frame.rename(
        columns={
            "Timestamp (UTC+07:00)": "timestamp",
            "Value": "original_value",
            "Unit": "unit_raw",
            "Observed or Estimated": "obs_type",
            "Approval Level": "source_approval",
            "Grade": "source_grade",
        }
    )
    frame["station_code"] = _station_code(frame["Station Code"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["original_value"] = pd.to_numeric(frame["original_value"], errors="coerce")
    frame["station"] = station_label
    frame["source"] = f"MRC_WRUP_VN_{station_code}"
    frame["snapshot_id"] = MRC_SNAPSHOT_ID
    frame["source_consistent"] = frame["station_code"].eq(station_code)
    return frame[
        [
            "timestamp",
            "station",
            "station_code",
            "source",
            "snapshot_id",
            "original_value",
            "unit_raw",
            "source_approval",
            "source_grade",
            "source_consistent",
            "obs_type",
        ]
    ].copy()


def qa_ec(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply non-destructive, explainable EC QA.

    Statistical extremes and abrupt changes are SUSPECT, not silently corrected
    or rejected. Only impossible/structurally invalid records are REJECTED.
    """
    result = frame.sort_values("timestamp", na_position="last").reset_index(drop=True).copy()
    result["clean_value"] = result["original_value"]
    result["quality_flag"] = "VERIFIED"
    reasons: list[list[str]] = [[] for _ in range(len(result))]

    def add(mask: pd.Series, reason: str, flag: str) -> None:
        for index in result.index[mask.fillna(False)]:
            reasons[index].append(reason)
            current = result.at[index, "quality_flag"]
            priority = {"VERIFIED": 0, "SUSPECT": 1, "MISSING": 2, "REJECTED": 3}
            if priority[flag] > priority[current]:
                result.at[index, "quality_flag"] = flag

    add(result["original_value"].isna(), "NULL_VALUE", "MISSING")
    add(result["timestamp"].isna(), "INVALID_TIMESTAMP", "REJECTED")
    add(~result["source_consistent"], "SOURCE_STATION_CODE_MISMATCH", "REJECTED")
    add(result["unit_raw"].astype(str).str.strip().ne("mS/m"), "UNIT_INCONSISTENT", "SUSPECT")
    add(result["original_value"].lt(0), "NEGATIVE_VALUE", "REJECTED")

    duplicate_later = result.duplicated(["timestamp"], keep="first") & result["timestamp"].notna()
    add(duplicate_later, "TIMESTAMP_DUPLICATE", "REJECTED")

    statistically_eligible = (
        result["original_value"].notna()
        & result["original_value"].ge(0)
        & result["unit_raw"].astype(str).str.strip().eq("mS/m")
        & result["source_consistent"]
    )
    values = result.loc[statistically_eligible, "original_value"]
    if len(values) >= 12:
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr > 0:
            lower = max(0.0, q1 - 3.5 * iqr)
            upper = q3 + 3.5 * iqr
            outlier = statistically_eligible & ~result["original_value"].between(lower, upper)
            add(outlier, f"IQR_OUTLIER[{lower:.3f},{upper:.3f}]", "SUSPECT")

        differences = result.loc[statistically_eligible, "original_value"].diff().abs()
        median_difference = differences.median()
        mad = (differences - median_difference).abs().median()
        jump_limit = max(5.0, median_difference + 6.0 * mad)
        jump_indices = differences.index[differences.gt(jump_limit)]
        jump_mask = pd.Series(False, index=result.index)
        jump_mask.loc[jump_indices] = True
        add(jump_mask, f"ABRUPT_JUMP_GT_{jump_limit:.3f}_MS_PER_M", "SUSPECT")

    result.loc[result["quality_flag"].isin(["REJECTED", "MISSING"]), "clean_value"] = np.nan
    result["qa_reason"] = ["; ".join(items) if items else "PASS" for items in reasons]
    return result


def run_ec_qa() -> pd.DataFrame:
    frames = []
    for station_code, station_label in STATIONS.items():
        frames.append(qa_ec(load_raw_ec(station_code, station_label)))

    full = pd.concat(frames, ignore_index=True).sort_values(["station", "timestamp"])
    report_columns = [
        "timestamp",
        "station",
        "station_code",
        "source",
        "snapshot_id",
        "original_value",
        "clean_value",
        "unit_raw",
        "quality_flag",
        "qa_reason",
        "source_approval",
        "source_grade",
        "obs_type",
    ]
    report = full[report_columns].copy()
    report.to_csv(EC_OUTPUT_DIR / "02_ec_qa_report.csv", index=False, encoding="utf-8-sig")
    report.to_csv(EC_OUTPUT_DIR / "03_ec_clean.csv", index=False, encoding="utf-8-sig")
    print("EC QA summary")
    print(pd.crosstab(report["station"], report["quality_flag"]).to_string())
    return report


def write_missing_glofas_mytho() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write explicit NULL products because no validated Mỹ Tho cell is available."""
    note = (
        "No validated MyTho main-river cell/upstream_area is available; "
        "the TanChau grid is outside MyTho and was not copied."
    )
    daily_dates = pd.date_range("1985-01-01", FEATURE_END, freq="D")
    daily = pd.DataFrame(
        {
            "date": daily_dates,
            "location_id": "MyTho",
            "discharge_m3s": np.nan,
            "source": "Copernicus_GloFAS",
            "version": GLOFAS_VERSION,
            "snapshot_id": "NOT_DOWNLOADED",
            "grid_lat": np.nan,
            "grid_lon": np.nan,
            "upstream_area_km2": np.nan,
            "quality_flag": "MISSING",
            "note": note,
        }
    )
    monthly_dates = pd.period_range("1985-01", "2026-08", freq="M").astype(str)
    monthly = pd.DataFrame(
        {
            "year_month": monthly_dates,
            "location_id": "MyTho",
            "discharge_mean": np.nan,
            "discharge_min": np.nan,
            "discharge_max": np.nan,
            "discharge_p10": np.nan,
            "discharge_p90": np.nan,
            "source": "Copernicus_GloFAS",
            "version": GLOFAS_VERSION,
            "snapshot_id": "NOT_DOWNLOADED",
            "grid_lat": np.nan,
            "grid_lon": np.nan,
            "upstream_area_km2": np.nan,
            "quality_flag": "MISSING",
            "note": note,
        }
    )
    daily.to_csv(GLOFAS_OUTPUT_DIR / "07_glofas_mytho_daily.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(GLOFAS_OUTPUT_DIR / "08_glofas_mytho_monthly.csv", index=False, encoding="utf-8-sig")
    return daily, monthly


def run_dahiti() -> dict[str, pd.DataFrame]:
    summary_path = RAW_DAHITI_DIR / "dahiti_download_summary.json"
    downloaded_at = "UNKNOWN"
    if summary_path.exists():
        downloaded_at = json.loads(summary_path.read_text(encoding="utf-8"))["downloaded_at"]
    snapshot_id = f"DAHITI_{downloaded_at.replace(' ', 'T').replace(':', '')}"

    results: dict[str, pd.DataFrame] = {}
    files = {
        "MyTho": RAW_DAHITI_DIR / "dahiti_waterlevel_MyTho_id3316.csv",
        "TanChau": RAW_DAHITI_DIR / "dahiti_waterlevel_TanChau_id627.csv",
    }
    for station, path in files.items():
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["water_level_m"] = pd.to_numeric(frame["water_level_m"], errors="coerce")
        frame = frame.dropna(subset=["date", "water_level_m"]).sort_values("date")
        frame["year_month"] = frame["date"].dt.to_period("M").astype(str)
        monthly = frame.groupby("year_month", as_index=False).agg(
            dahiti_wl_mean=("water_level_m", "mean"),
            dahiti_wl_min=("water_level_m", "min"),
            dahiti_wl_max=("water_level_m", "max"),
            dahiti_obs_count=("water_level_m", "count"),
        )
        monthly["station"] = station
        monthly["dahiti_available"] = True
        monthly["source"] = "DAHITI"
        monthly["version"] = DAHITI_VERSION
        monthly["snapshot_id"] = snapshot_id
        monthly["quality_flag"] = "VERIFIED"
        monthly.to_csv(DAHITI_STAGING_DIR / f"dahiti_{station}_monthly.csv", index=False)
        results[station] = monthly
    return results


def classify_gate_status(status: object) -> str:
    text = str(status or "").strip().lower()
    if text.startswith("direct_"):
        return "OFFICIAL"
    if text.startswith("derived_"):
        return "VERIFIED_MAP_PIN"
    if text.startswith("candidate_"):
        return "CANDIDATE"
    return "UNKNOWN"


def run_gate_qa() -> pd.DataFrame:
    master = RAW_GATE_DIR / "Dong_Thap_Sluice_Gates_WEBGIS_Master.xlsx"
    if not master.exists():
        raise FileNotFoundError(f"Missing gate master workbook: {master}")
    source = pd.read_excel(master, sheet_name="Master_All")
    method = source["coordinate_status"].map(classify_gate_status)
    ready = method.isin(["OFFICIAL", "VERIFIED_MAP_PIN"])

    output = pd.DataFrame(
        {
            "gate_code": source["record_id"],
            "gate_name": source["gate_name"],
            "latitude": source["latitude"].where(ready),
            "longitude": source["longitude"].where(ready),
            "candidate_latitude": source["candidate_latitude"].where(method.eq("CANDIDATE")),
            "candidate_longitude": source["candidate_longitude"].where(method.eq("CANDIDATE")),
            "coordinate_method": method,
            "webgis_ready": ready,
            "confidence_note": source["verification_note"],
            "source": source["source_scope"],
            "source_id": source["source_file"],
            "snapshot_id": "GATE_MASTER_2026-10-02",
            "is_primary_coord": ready,
        }
    )
    output.to_csv(GATE_OUTPUT_DIR / "09_gate_coordinate_qa.csv", index=False, encoding="utf-8-sig")
    print("Gate QA summary")
    print(output["coordinate_method"].value_counts().to_string())
    return output


def main() -> None:
    ensure_output_dirs()
    print(f"ETL run: {datetime.now().isoformat(timespec='seconds')}")
    run_ec_qa()
    write_missing_glofas_mytho()
    run_dahiti()
    run_gate_qa()
    print("ETL completed")


if __name__ == "__main__":
    main()
