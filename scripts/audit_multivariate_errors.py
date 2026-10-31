"""Reproduce the fixed EC forecast error audit without refitting a model."""

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_mrc_export import verify as verify_mrc_export


VERSION = "20261023T041813Z"
MODELS = ("RandomForest", "Persistence", "SeasonalNaive", "MonthlyClimatology")
SPLITS = {"validation": date(2019, 1, 1), "holdout": date(2022, 1, 1)}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def percentile_nearest_rank(values, percentile):
    """Nearest-rank percentile, fixed from the pre-split training labels."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Empty training sample")
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def metrics(rows, model):
    errors = [float(row[model]) - float(row["actual"]) for row in rows]
    return dict(n=len(errors), mae_mS_m=sum(map(abs, errors)) / len(errors),
                rmse_mS_m=math.sqrt(sum(error * error for error in errors) / len(errors)),
                bias_mS_m=sum(errors) / len(errors))


def month_shift(month, delta):
    index = month.year * 12 + month.month - 1 + delta
    return date(index // 12, index % 12 + 1, 1)


def season_for_month(month):
    return "dry" if month in (12, 1, 2, 3, 4) else "non_dry"


def audit(root, version, output_dir, top_n=15, mrc_zip=None):
    mrc_check = None
    if mrc_zip is not None:
        mrc_check = verify_mrc_export(mrc_zip, root / "data/research/mrc_ec_monthly_samples.csv")
        if (mrc_check["missing_in_project"] or mrc_check["extra_in_project"]
                or mrc_check["value_or_count_mismatches"]):
            raise ValueError("Project monthly EC does not match the supplied MRC export")
    labels = {}
    for row in read_csv(root / "data/research/mrc_ec_monthly_samples.csv"):
        key = (row["station"], date.fromisoformat(row["month_start"]))
        if key in labels:
            raise ValueError(f"Duplicate target label: {key}")
        labels[key] = row

    predictions = []
    manifests = {}
    for station in ("MYTHO", "TANCHAU"):
        directory = root / "runs/multivariate_ec" / station.lower() / version
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        source = directory / "predictions.csv"
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != manifest["predictions_sha256"]:
            raise ValueError(f"Predictions hash mismatch: {source}")
        if (manifest["station"] != station or manifest["weather_lag_months"] != 2
                or set(manifest["source_qa_counts"]) != {"UNVERIFIED"}):
            raise ValueError(f"Unexpected model manifest: {station}")
        manifests[station] = manifest
        predictions.extend(read_csv(source))

    seen = set()
    for row in predictions:
        station, split = row["station"], row["split"]
        target = date.fromisoformat(row["target_month"])
        key = (station, split, target)
        if key in seen or split not in SPLITS:
            raise ValueError(f"Duplicate or invalid prediction: {key}")
        seen.add(key)
        label = labels.get((station, target))
        if label is None or not math.isclose(float(label["conductivity_mS_per_m"]), float(row["actual"]), abs_tol=1e-9):
            raise ValueError(f"Prediction/target mismatch: {key}")
        if any(not math.isfinite(float(row[model])) for model in MODELS):
            raise ValueError(f"Nonfinite model prediction: {key}")
        train_values = [float(source["conductivity_mS_per_m"]) for (site, month), source in labels.items()
                        if site == station and month < SPLITS[split]]
        threshold = percentile_nearest_rank(train_values, 0.90)
        actual = float(row["actual"])
        row["threshold_mS_m"] = threshold
        row["high_ec"] = actual >= threshold
        row["season"] = season_for_month(target.month)
        row["sample_count"] = int(label["sample_count"])
        row["abs_error"] = abs(float(row["RandomForest"]) - actual)

    by_station_split = defaultdict(list)
    for row in predictions:
        by_station_split[(row["station"], row["split"])].append(row)

    top_rows, season_rows, high_rows = [], [], []
    for (station, split), cohort in sorted(by_station_split.items()):
        if len(cohort) != (36 if split == "validation" else 24):
            raise ValueError(f"Unexpected evaluation cohort: {station} {split}: {len(cohort)}")
        for model in MODELS:
            observed = metrics(cohort, model)
            expected = manifests[station]["evaluation"][split][model]
            if observed["n"] != expected["n"] or any(
                not math.isclose(observed[field], expected[field], rel_tol=1e-10)
                for field in ("mae_mS_m", "rmse_mS_m")
            ):
                raise ValueError(f"Manifest evaluation mismatch: {station} {split} {model}")
        ranked = sorted(cohort, key=lambda row: (-row["abs_error"], row["target_month"]))
        for rank, row in enumerate(ranked[:top_n], 1):
            target = date.fromisoformat(row["target_month"])
            prior = labels.get((station, month_shift(target, -1)))
            following = labels.get((station, month_shift(target, 1)))
            input_month = month_shift(target, -2)
            following_month = month_shift(input_month, 1)
            assumed_available = following_month - timedelta(days=1) + timedelta(days=5)
            top_rows.append(dict(station=station, split=split, rank=rank, target_month=target.isoformat(),
                season=row["season"], high_ec=row["high_ec"], high_ec_threshold_mS_m=row["threshold_mS_m"],
                actual_mS_m=row["actual"], random_forest_mS_m=row["RandomForest"],
                signed_error_mS_m=float(row["RandomForest"]) - float(row["actual"]),
                abs_error_mS_m=row["abs_error"], persistence_abs_error_mS_m=abs(float(row["Persistence"]) - float(row["actual"])),
                seasonal_naive_abs_error_mS_m=abs(float(row["SeasonalNaive"]) - float(row["actual"])),
                climatology_abs_error_mS_m=abs(float(row["MonthlyClimatology"]) - float(row["actual"])),
                prior_month_ec_mS_m=prior["conductivity_mS_per_m"] if prior else "",
                next_month_ec_mS_m=following["conductivity_mS_per_m"] if following else "",
                sample_count=row["sample_count"], source_qa="UNVERIFIED",
                weather_input_month=input_month.isoformat(), assumed_weather_available_at=assumed_available.isoformat(),
                source_review="MATCHED_MRC_EXPORT" if mrc_check else "PENDING"))
        for season in ("dry", "non_dry"):
            subset = [row for row in cohort if row["season"] == season]
            for model in MODELS:
                season_rows.append(dict(station=station, split=split, season=season, model=model, **metrics(subset, model)))
        for segment, select in (("high_ec", True), ("other_ec", False)):
            subset = [row for row in cohort if row["high_ec"] == select]
            for model in MODELS:
                high_rows.append(dict(station=station, split=split, segment=segment,
                                      high_ec_threshold_mS_m=cohort[0]["threshold_mS_m"], model=model,
                                      **metrics(subset, model)))

    write_csv(output_dir / "top_errors.csv", top_rows, list(top_rows[0]))
    write_csv(output_dir / "season_metrics.csv", season_rows, list(season_rows[0]))
    write_csv(output_dir / "high_ec_metrics.csv", high_rows, list(high_rows[0]))
    summary = {"version": version, "top_n_per_station_split": top_n, "evaluated_months": len(predictions),
               "dry_months": [12, 1, 2, 3, 4], "high_ec_rule": "actual >= nearest-rank 90th percentile of pre-split training EC",
               "thresholds_mS_m": {f"{station}/{split}": cohort[0]["threshold_mS_m"]
                                   for (station, split), cohort in sorted(by_station_split.items())}}
    if mrc_check:
        summary["mrc_export_check"] = mrc_check
    (output_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/multivariate_error_audit_20261029")
    parser.add_argument("--top-n", type=int, default=15)
    parser.add_argument("--mrc-zip", type=Path, help="Optional purchased MRC ZIP for exact source reconciliation")
    args = parser.parse_args()
    if not 10 <= args.top_n <= 15:
        parser.error("--top-n must be between 10 and 15")
    print(json.dumps(audit(args.root, args.version, args.output_dir, args.top_n, args.mrc_zip), indent=2))
