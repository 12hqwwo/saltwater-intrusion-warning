"""Verify downloaded MRC files and summarize observed coverage without gap filling."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [ROOT / "data/external/tien_multisite_20261029_verified",
          ROOT / "data/external/tien_multisite_supplement_20261029",
          ROOT / "data/external/tien_manual_history_20261029",
          ROOT / "data/external/tien_manual_long_20261029",
          ROOT / "data/external/tien_manual_2024_2026_20261029",
          ROOT / "data/external/tien_ec_extended_20261029",
          ROOT / "data/external/mrc_kratie_discharge_20261029"]
OUT = ROOT / "outputs/tien_multisite_audit_20261029"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for folder in INPUTS:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["errors"]:
            raise ValueError(f"Source download errors: {folder}")
        for entry in manifest["downloads"]:
            if sha(folder / entry["file"]) != entry["sha256"]:
                raise ValueError(f"Raw checksum mismatch: {entry['file']}")
        for series in manifest["series"]:
            path = folder / series["file"]
            if sha(path) != series["extracted_sha256"]:
                raise ValueError(f"Extracted checksum mismatch: {path}")
            frame = pd.read_csv(path)
            if len(frame) != series["downloaded_rows"] or frame.observed_at.duplicated().any():
                raise ValueError(f"Rows or timestamps mismatch: {path}")
            at = pd.to_datetime(frame.observed_at, utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
            if (frame.value < 0).any() and series["parameter"] == "Conductivity":
                raise ValueError(f"Negative EC: {path}")
            period = (at.dt.year >= 2019) & (at.dt.year <= 2023)
            dates = at[period].dt.normalize()
            daily_counts = dates.value_counts()
            eligible = int((daily_counts >= 80).sum()) if series["label"] == "Telemetry" else None
            months = set(at[period].dt.strftime("%Y-%m"))
            dates_recent = at[(at.dt.year >= 2024) & (at.dt.year <= 2026)].dt.normalize()
            rows.append(dict(source_folder=folder.name, file=path.name,
                station_code=series["station_code"], station=series["station_name"],
                parameter=series["parameter"], series_label=series["label"], unit=series["unit"],
                rows=len(frame), rows_2019_2023=int(period.sum()),
                days_2019_2023=len(daily_counts), days_2024_2026=dates_recent.nunique(),
                days_at_least_80_samples=eligible,
                months_2019_2023=len(months),
                min_value=float(frame.value.min()) if len(frame) else None,
                max_value=float(frame.value.max()) if len(frame) else None,
                quality_flags="|".join(sorted(frame.quality_flag.dropna().unique())),
                first=str(at.min()) if len(frame) else None,
                last=str(at.max()) if len(frame) else None))
    summary = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "series_coverage.csv", index=False, encoding="utf-8-sig")
    (OUT / "checks.json").write_text(json.dumps(dict(
        all_raw_checksums_match=True, all_extracted_checksums_match=True,
        all_row_counts_match=True, no_duplicate_timestamps=True,
        negative_ec_absent=True, series=len(summary),
        note="No interpolation, gauge datum conversion, EC-to-salinity conversion or publication-vintage inference"
    ), ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary[["station", "parameter", "series_label", "rows", "days_2019_2023",
                   "days_at_least_80_samples", "months_2019_2023"]].to_string(index=False))


if __name__ == "__main__":
    main()
