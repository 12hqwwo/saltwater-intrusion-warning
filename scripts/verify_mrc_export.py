"""Read-only comparison of a purchased MRC ZIP with the project's monthly EC CSV."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
STATIONS = {"019805": "MYTHO", "019803": "TANCHAU"}


def verify(zip_path, monthly_path):
    source = defaultdict(list)
    grades = Counter()
    approvals = Counter()
    with ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist()
                     if name.endswith(".csv") and "Conductivity.Water Quality" in name]
        if len(csv_names) != 2:
            raise ValueError(f"Expected two MRC conductivity CSVs; found {len(csv_names)}")
        for name in csv_names:
            with archive.open(name) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                for row in reader:
                    station = STATIONS.get(row["Station Code"])
                    if station is None or row["Unit"] != "mS/m" or row["Parameter"] != "Conductivity":
                        raise ValueError(f"Unexpected station, unit or parameter in {name}")
                    month = row["Timestamp (UTC+07:00)"][:7] + "-01"
                    source[(station, month)].append(Decimal(row["Value"]))
                    grades[row["Grade"]] += 1
                    approvals[row["Approval Level"]] += 1

    target = {}
    with monthly_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["station"], row["month_start"])
            if key in target:
                raise ValueError(f"Duplicate project month: {key}")
            target[key] = row

    missing = sorted(set(source) - set(target))
    extra = sorted(set(target) - set(source))
    different = []
    for key in sorted(set(source) & set(target)):
        values = source[key]
        mean = sum(values) / len(values)
        row = target[key]
        if int(row["sample_count"]) != len(values) or abs(Decimal(row["conductivity_mS_per_m"]) - mean) > Decimal("0.000000001"):
            different.append({"station": key[0], "month": key[1], "mrc_mean": str(mean),
                              "project_value": row["conductivity_mS_per_m"], "mrc_n": len(values),
                              "project_n": row["sample_count"]})
    return {"zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "source_records": sum(len(values) for values in source.values()),
            "source_months": len(source), "project_months": len(target),
            "source_months_by_station": dict(Counter(site for site, _ in source)),
            "grade_counts": dict(grades), "approval_counts": dict(approvals),
            "missing_in_project": missing, "extra_in_project": extra, "value_or_count_mismatches": different}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--monthly", type=Path, default=ROOT / "data/research/mrc_ec_monthly_samples.csv")
    args = parser.parse_args()
    result = verify(args.zip_path, args.monthly)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["missing_in_project"] or result["extra_in_project"] or result["value_or_count_mismatches"]:
        raise SystemExit(1)
