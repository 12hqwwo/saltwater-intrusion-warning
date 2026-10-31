"""Validate ENSO+log models on 2010-2018 history (108 months rolling-origin).

Same protocol as scripts/validate_ec_compact_history.py but adds ENSO features
and log-space variants. Used only to check that adding ENSO does not degrade
performance on the long historical period.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.experiment_ec_enso_climate import (
    COMPACT, COMPACT_ENSO, ENSO_FEATS, load_climate,
    fit_predict_standard, fit_predict_log
)

OUT = ROOT / "outputs/ec_enso_history_20261029"
OUT.mkdir(parents=True, exist_ok=True)


def run(delay: int = 5):
    print(f"\n=== History validation 2010-2018 delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = load_climate(part)

    rows = []
    for _, target in part[part.month_start.dt.year.between(2010, 2018)].iterrows():
        issue = target.issue_date
        train = part[
            (part.month_start < target.month_start) &
            (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
            (part.weather_available_at <= issue)
        ]
        if len(train) < 20:
            continue

        prev_months = part[part.month_start < target.month_start].sort_values("month_start")
        persistence = float(prev_months.conductivity_mS_per_m.iloc[-1]) if len(prev_months) else np.nan

        row = dict(
            target_month=target.month_start.strftime("%Y-%m-%d"),
            actual=float(target.conductivity_mS_per_m),
            year=target.month_start.year,
            dry=bool(target.month_start.month in [12,1,2,3,4]),
            high=bool(target.conductivity_mS_per_m >= 100),
            Persistence=persistence,
            RF_compact=fit_predict_standard(COMPACT, train, target),
            RF_enso=fit_predict_standard(COMPACT_ENSO, train, target),
            RF_log=fit_predict_log(COMPACT, train, target),
            RF_enso_log=fit_predict_log(COMPACT_ENSO, train, target),
        )
        rows.append(row)
        if target.month_start.month == 12:
            print(f"  {target.month_start.year} done", flush=True)

    pred = pd.DataFrame(rows)
    pred.to_csv(OUT / f"predictions_2010_2018_{delay}d.csv", index=False)

    models = ["RF_compact", "RF_enso", "RF_log", "RF_enso_log", "Persistence"]
    metric_rows = []
    for subset_name, mask in [
        ("all", np.ones(len(pred), bool)),
        ("dry_dec_apr", pred.dry.to_numpy()),
        ("high_ge_100", pred.high.to_numpy()),
    ]:
        if not mask.any():
            continue
        for m in models:
            err = pred.loc[mask, m].to_numpy() - pred.loc[mask, "actual"].to_numpy()
            metric_rows.append(dict(subset=subset_name, model=m, n=int(mask.sum()),
                                    mae=float(np.abs(err).mean()),
                                    rmse=float(np.sqrt(np.mean(err**2))),
                                    bias=float(err.mean())))

    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(OUT / f"metrics_2010_2018_{delay}d.csv", index=False)
    print(f"\nHistory metrics {delay}d (all):")
    print(metrics[metrics.subset == "all"].to_string(index=False))
    return pred, metrics


if __name__ == "__main__":
    run(5)
