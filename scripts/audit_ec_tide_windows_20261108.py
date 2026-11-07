"""Research-only FES window ablation for frozen My Tho EC outages.

All tide windows use fixed calendar dates, never the observed sample date.
FES2022b is a retrospective atlas and was not an available historical vintage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyfes


FEATURES = (
    "fes_daytime_max_13_17_cm",
    "fes_daytime_mean_13_17_cm",
    "fes_first_half_max_cm",
    "fes_early_range_05_12_cm",
)
POINT = (106.78333333333333, 10.05)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tide_features(root: Path) -> pd.DataFrame:
    from scripts.experiment_fes_ec import ATLAS, CONFIG, MASK, STATUS

    status = json.loads(STATUS.read_text(encoding="utf-8"))
    if not (status.get("collection_complete") and status.get("present_constituents") == 34
            and MASK.is_file()):
        raise ValueError("Complete FES2022b atlas required")
    os.environ["FES_DATA"] = str(ATLAS.resolve())
    config = pyfes.config.load(CONFIG, bbox=(POINT[0] - .2, POINT[1] - .2,
                                           POINT[0] + .2, POINT[1] + .2))
    months = pd.date_range("1985-06-01", "2023-12-01", freq="MS")
    rows = []
    for year in range(1985, 2024):
        pieces = [pd.date_range(m.tz_localize("Asia/Ho_Chi_Minh"),
                                (m + pd.DateOffset(days=17)).tz_localize("Asia/Ho_Chi_Minh"),
                                freq="h", inclusive="left") for m in months if m.year == year]
        local = pieces[0].append(pieces[1:])
        utc = local.tz_convert("UTC").tz_localize(None).to_numpy(dtype="datetime64[s]")
        tide, long_period, flags = pyfes.evaluate_tide(
            config.models["tide"], utc,
            np.full(len(utc), POINT[0]), np.full(len(utc), POINT[1]),
            settings=config.settings)
        if not (np.isfinite(tide).all() and np.isfinite(long_period).all()
                and np.all(flags == 4)):
            raise ValueError(f"Incomplete native-ocean FES values in {year}")
        hourly = pd.DataFrame({"time_local": local, "tide_cm": tide + long_period})
        hourly["month_start"] = hourly.time_local.dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
        hourly["day"] = hourly.time_local.dt.day
        hourly["hour"] = hourly.time_local.dt.hour
        for month, part in hourly.groupby("month_start"):
            daytime = part[part.day.between(13, 17) & part.hour.between(7, 16)]
            early = part[part.day.between(5, 12)]
            mid = part[part.day.between(13, 17)]
            daily_early = early.groupby("day").tide_cm.agg(lambda x: x.max() - x.min())
            daily_mid = mid.groupby("day").tide_cm.agg(lambda x: x.max() - x.min())
            if (len(part) != 17 * 24 or len(daytime) != 50 or
                    len(daily_early) != 8 or len(daily_mid) != 5):
                raise ValueError(f"Incomplete fixed window {month}")
            rows.append(dict(month_start=month,
                fes_daytime_max_13_17_cm=float(daytime.tide_cm.max()),
                fes_daytime_mean_13_17_cm=float(daytime.tide_cm.mean()),
                fes_first_half_max_cm=float(part[part.day.le(15)].tide_cm.max()),
                fes_early_range_05_12_cm=float(daily_early.mean()),
                fes_mid_range_13_17_cm=float(daily_mid.mean())))
        print("FES", year, flush=True)
    result = pd.DataFrame(rows).sort_values("month_start").reset_index(drop=True)
    if len(result) != len(months) or not result.month_start.eq(months).all():
        raise ValueError("Wrong FES month coverage")
    reference = pd.read_csv(root / "outputs/ec_fes_day15_fixed_20261030/fes_south_feature_days13_17_1985_2023.csv",
                            parse_dates=["month_start"])
    check = result.merge(reference, on="month_start", validate="one_to_one")
    if (len(check) != len(result) or not np.allclose(
            check.fes_mid_range_13_17_cm,
            check.fes_south_days13_17_mean_daily_range_cm, rtol=0, atol=1e-7)):
        raise ValueError("Reconstructed FES differs from saved 13–17 baseline")
    return result


def sample_day_summary(root: Path) -> dict:
    path = root / "data/raw/ec/mrc/Conductivity.Water Quality@VN_019805_[My Tho].csv"
    with path.open(encoding="utf-8-sig", newline="") as file:
        samples = list(csv.DictReader(file))
    days = np.array([int(row["Timestamp (UTC+07:00)"][8:10]) for row in samples])
    return dict(total=len(days), in_13_17=int(((days >= 13) & (days <= 17)).sum()),
                on_15=int((days == 15).sum()), outside_13_17=int(((days < 13) | (days > 17)).sum()),
                all_midnight=all("T00:00" in row["Timestamp (UTC+07:00)"] for row in samples))


def evaluate(root: Path, monthly: pd.DataFrame, output: Path) -> None:
    from scripts.evaluate_frozen_ec_gap import EXPERIMENTS, freeze_training
    from scripts.evaluate_frozen_ec_gap_remedies import CANDIDATES
    from scripts.experiment_ec_long_hydrology import data_matrix
    from scripts.train_multivariate_ec import pipeline

    saved = pd.read_csv(root / "outputs/frozen_ec_remedies_20261108/predictions.csv")
    base_columns = CANDIDATES["WeatherHydrology"]
    rows = []
    for delay in (5, 35):
        data = data_matrix(delay).merge(monthly, on="month_start", validate="one_to_one")
        for experiment, (start, end) in EXPERIMENTS.items():
            known = freeze_training(data, start, delay)
            future = data[data.month_start.between(start, end)].copy()
            reference = saved[(saved.experiment == experiment) &
                              (saved.ec_delay_days == delay)].sort_values("target_month")
            if (len(future) != len(reference) or
                    future.month_start.dt.strftime("%Y-%m-%d").tolist() != reference.target_month.tolist()):
                raise ValueError("Frozen evaluation cohort mismatch")
            record = pd.DataFrame(dict(experiment=experiment, ec_delay_days=delay,
                target_month=reference.target_month.to_numpy(),
                actual_mS_m=future.conductivity_mS_per_m.to_numpy(),
                reference_ec_mS_m=reference.WeatherHydrology.to_numpy()))
            for name in ("baseline", *FEATURES):
                columns = base_columns + ([] if name == "baseline" else [name])
                model = pipeline().set_params(randomforestregressor__n_jobs=1)
                model.fit(known[columns], known.conductivity_mS_per_m)
                predicted = model.predict(future[columns])
                if name == "baseline":
                    if not np.allclose(predicted, record.reference_ec_mS_m, rtol=0, atol=1e-8):
                        raise ValueError("Baseline differs from frozen published prediction")
                    transformed = model[0].transform(future[columns])
                    trees = np.column_stack([tree.predict(transformed) for tree in model[-1].estimators_])
                    record["tree_p90_mS_m"] = np.percentile(trees, 90, axis=1)
                    record["tree_p95_mS_m"] = np.percentile(trees, 95, axis=1)
                    record["tree_max_mS_m"] = trees.max(axis=1)
                record[name + "_mS_m"] = predicted
            rows.append(record)
            print("RF", experiment, delay, flush=True)
    predictions = pd.concat(rows, ignore_index=True)
    metrics = []
    for (experiment, delay), part in predictions.groupby(["experiment", "ec_delay_days"]):
        for name in ("baseline", *FEATURES):
            err = part[name + "_mS_m"].to_numpy() - part.actual_mS_m.to_numpy()
            metrics.append(dict(experiment=experiment, ec_delay_days=int(delay), model=name,
                n=len(part), mae_mS_m=float(np.abs(err).mean()),
                rmse_mS_m=float(np.sqrt(np.mean(err ** 2))),
                high_ec_mae_mS_m=float(np.abs(err[part.actual_mS_m.ge(100).to_numpy()]).mean())
                    if part.actual_mS_m.ge(100).any() else None))
    output.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(output / "fes_fixed_windows.csv", index=False)
    predictions.to_csv(output / "frozen_predictions.csv", index=False)
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    summary = dict(sample_days=sample_day_summary(root),
                   march_2020=predictions[(predictions.experiment == "gap_2019_2021") &
                                           (predictions.ec_delay_days == 5) &
                                           (predictions.target_month == "2020-03-01")].iloc[0].to_dict(),
                   source_root=str(root),
                   source_sha256={str(path.relative_to(root)).replace("\\", "/"): digest(path)
                       for path in (
                           root / "data/raw/ec/mrc/Conductivity.Water Quality@VN_019805_[My Tho].csv",
                           root / "data/raw/tide/fes2022b/collection_status.json",
                           root / "config/fes2022b_full.yaml",
                           root / "data/research/mrc_ec_monthly_samples.csv",
                           root / "outputs/ec_fes_day15_fixed_20261030/fes_south_feature_days13_17_1985_2023.csv",
                           root / "outputs/frozen_ec_remedies_20261108/predictions.csv",
                           root / "scripts/evaluate_frozen_ec_gap_remedies.py",
                           root / "scripts/train_multivariate_ec.py")},
                   note="FES2022b is retrospective astronomical offshore tide; tree percentiles are not calibrated prediction intervals.")
    (output / "audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False,
                                                  default=str) + "\n", encoding="utf-8")
    print(pd.DataFrame(metrics).to_string(index=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    sys.path.insert(0, str(root))
    output = args.output or root / "outputs/ec_tide_windows_20261108"
    monthly = tide_features(root)
    evaluate(root, monthly, output)


if __name__ == "__main__":
    main()
