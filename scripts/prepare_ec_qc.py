"""Create a non-destructive QC ledger for the purchased MRC EC export."""

import argparse
import csv
import io
import json
import statistics
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from verify_mrc_export import verify


ROOT = Path(__file__).resolve().parents[1]
STATIONS = {"019805": "MYTHO", "019803": "TANCHAU"}


def next_month(month):
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def build(zip_path, monthly_path, output_dir):
    check = verify(zip_path, monthly_path)
    if check["missing_in_project"] or check["extra_in_project"] or check["value_or_count_mismatches"]:
        raise ValueError("MRC export and project monthly EC differ")
    observations = {}
    with ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not (name.endswith(".csv") and "Conductivity.Water Quality" in name):
                continue
            with archive.open(name) as raw:
                for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")):
                    station = STATIONS[row["Station Code"]]
                    timestamp = datetime.fromisoformat(row["Timestamp (UTC+07:00)"])
                    key = (station, date(timestamp.year, timestamp.month, 1))
                    if key in observations:
                        raise ValueError(f"Multiple source samples in month {key}; review aggregation first")
                    observations[key] = row
    monthly = {}
    with monthly_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            monthly[(row["station"], date.fromisoformat(row["month_start"]))] = row
    for station in STATIONS.values():
        dates = sorted(month for site, month in monthly if site == station)
        for before, after in zip(dates, dates[1:]):
            if next_month(before) != after:
                raise ValueError(f"Missing month for {station}: {before} to {after}")

    by_station_calendar = {}
    for station in STATIONS.values():
        for month_num in range(1, 13):
            values = [float(row["conductivity_mS_per_m"]) for (site, month), row in monthly.items()
                      if site == station and month.month == month_num]
            by_station_calendar[(station, month_num)] = statistics.median(values)
    rows = []
    counts = Counter()
    for (station, month), record in sorted(monthly.items()):
        original = observations[(station, month)]
        value = Decimal(record["conductivity_mS_per_m"])
        if not value.is_finite() or value < 0:
            raise ValueError(f"Invalid EC: {station} {month}")
        median = by_station_calendar[(station, month.month)]
        ratio = float(value) / median if median else None
        flags = []
        if ratio is not None and ratio >= 3:
            flags.append("HIGH_VS_CALENDAR_MEDIAN_REVIEW_ONLY")
        if original["Observed or Estimated"] != "O":
            flags.append("ESTIMATED_SOURCE")
        counts.update(flags)
        rows.append(dict(station=station, month_start=month.isoformat(),
            sample_timestamp_local=original["Timestamp (UTC+07:00)"],
            ec_original_mS_m=str(value), ec_for_model_mS_m=str(value),
            calendar_month_median_mS_m=round(median, 6),
            ratio_to_calendar_month_median=round(ratio, 4) if ratio is not None else "",
            source_match="EXACT", source_observation_type=original["Observed or Estimated"],
            source_approval=original["Approval Level"], source_grade=original["Grade"],
            qc_flag=";".join(flags), action="KEEP_VALUE"))
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = output_dir / "ec_qc_review.csv"
    with ledger.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(source_zip_sha256=check["zip_sha256"], records=len(rows),
                   missing_or_mismatched=0, duplicate_months=0, missing_months=0,
                   negative_or_nonfinite=0, flag_counts=dict(counts),
                   model_value_changed=0,
                   note="Calendar median flags are retrospective review markers, not deletion or model features.")
    (output_dir / "ec_qc_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--monthly", type=Path, default=ROOT / "data/research/mrc_ec_monthly_samples.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/multivariate_error_audit_20261029")
    args = parser.parse_args()
    print(json.dumps(build(args.zip_path, args.monthly, args.output_dir), indent=2))
