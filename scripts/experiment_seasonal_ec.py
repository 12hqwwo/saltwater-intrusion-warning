"""Compare pooled and dry/non-dry Random Forest fits on historical EC splits."""

import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd

from train_multivariate_ec import FEATURES, ROOT, pipeline, training_frame


VERSION = "20261023T041813Z"
OUT = ROOT / "outputs/multivariate_error_audit_20261029/seasonal_split_comparison.csv"
SPLITS = (("validation", "2019-01-01", "2022-01-01"),
          ("holdout", "2022-01-01", "2024-01-01"))


def season(month):
    return "dry" if month in (12, 1, 2, 3, 4) else "non_dry"


def score(actual, predicted):
    diff = np.asarray(predicted, dtype=float) - np.asarray(actual, dtype=float)
    return (float(np.mean(np.abs(diff))), float(np.sqrt(np.mean(diff ** 2))),
            float(np.mean(diff)))


def run():
    frame, _ = training_frame(ROOT / "data/research/mrc_ec_monthly_samples.csv",
                              ROOT / "data/external/multivariate_weather/manifest.json")
    frame["season"] = frame.month_start.dt.month.map(season)
    rows = []
    for station, data in frame.groupby("station"):
        saved = pd.read_csv(ROOT / "runs/multivariate_ec" / station.lower() / VERSION / "predictions.csv")
        for split, start, end in SPLITS:
            train = data[data.month_start < start]
            test = data[(data.month_start >= start) & (data.month_start < end)].copy()
            if len(test) != (36 if split == "validation" else 24):
                raise ValueError(f"Unexpected cohort: {station} {split}")
            pooled = pipeline().fit(train[FEATURES], train.conductivity_mS_per_m)
            test["pooled_refit"] = pooled.predict(test[FEATURES])
            for label in ("dry", "non_dry"):
                fit = train[train.season == label]
                selected = test[test.season == label]
                seasonal = pipeline().fit(fit[FEATURES], fit.conductivity_mS_per_m)
                test.loc[selected.index, "seasonal_fit"] = seasonal.predict(selected[FEATURES])
            test["target_month"] = test.month_start.dt.strftime("%Y-%m-%d")
            joined = test.merge(saved[saved.split == split], on="target_month", validate="one_to_one")
            if len(joined) != len(test) or not np.allclose(joined.conductivity_mS_per_m, joined.actual):
                raise ValueError(f"Saved prediction cohort mismatch: {station} {split}")
            threshold = float(np.sort(train.conductivity_mS_per_m)[math.ceil(0.9 * len(train)) - 1])
            for segment in ("all", "dry", "non_dry", "high_ec"):
                if segment == "all":
                    subset = joined
                elif segment == "high_ec":
                    subset = joined[joined.actual >= threshold]
                else:
                    subset = joined[joined.season == segment]
                for name, column in (("current_rf", "RandomForest"), ("pooled_refit", "pooled_refit"),
                                     ("seasonal_fit", "seasonal_fit"), ("persistence", "Persistence"),
                                     ("seasonal_naive", "SeasonalNaive"), ("climatology", "MonthlyClimatology")):
                    mae, rmse, bias = score(subset.actual, subset[column])
                    rows.append(dict(station=station, split=split, segment=segment, model=name,
                                     n=len(subset), train_n_pooled=len(train),
                                     train_n_dry=int((train.season == "dry").sum()),
                                     train_n_non_dry=int((train.season == "non_dry").sum()),
                                     high_ec_threshold_mS_m=threshold, mae_mS_m=mae,
                                     rmse_mS_m=rmse, bias_mS_m=bias))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows to {OUT}")
    for row in rows:
        if row["split"] == "holdout" and row["model"] in ("pooled_refit", "seasonal_fit"):
            print(row["station"], row["segment"], row["model"], row["n"], round(row["mae_mS_m"], 3))


if __name__ == "__main__":
    run()
