"""History validation 2010-2018 for enhanced feature set."""
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
from scripts.experiment_ec_feature_enhanced import (
    COMPACT, ENHANCED, add_derived_features, load_climate, fit_predict, fit_predict_q90
)

OUT = ROOT / "outputs/ec_feature_enhanced_history_20261029"
OUT.mkdir(parents=True, exist_ok=True)


def run(delay: int = 5):
    print(f"\n=== Enhanced History Validation 2010-2018 delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = load_climate(part)
    part = add_derived_features(part)

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

        prev = part[(part.month_start < target.month_start) &
                    (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue)].sort_values("month_start")
        persistence = float(prev.conductivity_mS_per_m.iloc[-1]) if len(prev) else np.nan

        row = dict(
            target_month=target.month_start.strftime("%Y-%m-%d"),
            actual=float(target.conductivity_mS_per_m),
            year=target.month_start.year,
            dry=bool(target.month_start.month in [12,1,2,3,4]),
            high=bool(target.conductivity_mS_per_m >= 100),
            Persistence=persistence,
            RF_compact=fit_predict(COMPACT, train, target),
            RF_enhanced=fit_predict(ENHANCED, train, target),
            RF_enhanced_w5=fit_predict(ENHANCED, train, target, high_weight=5.0),
            RF_compact_q90=fit_predict_q90(COMPACT, train, target),
            RF_enhanced_q90=fit_predict_q90(ENHANCED, train, target),
        )
        rows.append(row)
        if target.month_start.month == 12:
            print(f"  {target.month_start.year} done", flush=True)

    pred = pd.DataFrame(rows)
    pred.to_csv(OUT / f"predictions_2010_2018_{delay}d.csv", index=False)

    models = ["RF_compact","RF_enhanced","RF_enhanced_w5","RF_compact_q90","RF_enhanced_q90","Persistence"]
    rows2 = []
    for subset_name, mask in [
        ("all", np.ones(len(pred), bool)),
        ("dry_dec_apr", pred.dry.to_numpy()),
        ("high_ge_100", pred.high.to_numpy()),
    ]:
        if not mask.any(): continue
        for m in models:
            err = pred.loc[mask, m].to_numpy() - pred.loc[mask,"actual"].to_numpy()
            rows2.append(dict(subset=subset_name, model=m, n=int(mask.sum()),
                              mae=round(float(np.abs(err).mean()),4),
                              rmse=round(float(np.sqrt(np.mean(err**2))),4),
                              bias=round(float(err.mean()),4)))
    metrics = pd.DataFrame(rows2)
    metrics.to_csv(OUT / f"metrics_2010_2018_{delay}d.csv", index=False)
    print(f"\nHistory metrics {delay}d:")
    print(metrics.to_string(index=False))
    return pred, metrics


if __name__ == "__main__":
    run(5)
