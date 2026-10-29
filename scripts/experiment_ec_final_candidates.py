"""Final candidate search: combine best features with best algorithms.

After ablation study identifies best feature additions from 2010-2018,
test those features with:
1. RF_compact_q90 (already best for extremes)  
2. GradientBoosting with Huber loss (robust to outliers)
3. Stacking: RF median + RF q90 for alert system

Key insight: q90 significantly outperforms mean models for extremes.
The question is which features most help q90 specifically.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor,
    HistGradientBoostingRegressor
)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.experiment_ec_feature_enhanced import add_derived_features, load_climate

OUT = ROOT / "outputs/ec_final_candidates_20261029"
OUT.mkdir(parents=True, exist_ok=True)

# Compact baseline
COMPACT = ["month_sin", "month_cos", "rainfall_mm", "kratie_q_t2",
           "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]

# Best physics additions identified from correlation analysis
COMPACT_PLUS = COMPACT + ["wind_u_t2", "q_low_flag", "oni_lag3"]


def _q90_prediction(columns, train, target):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    avail = [c for c in columns if c in train.columns]
    imp = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    xt = imp.fit_transform(train[avail])
    xp = imp.transform(target[avail].to_frame().T)
    rf = RandomForestRegressor(n_estimators=300, max_depth=8, min_samples_leaf=2,
                                max_features=0.7, random_state=42, n_jobs=-1)
    rf.fit(xt, y)
    preds = np.array([t.predict(xp)[0] for t in rf.estimators_])
    return max(0.0, float(np.percentile(preds, 90)))


def _q50_prediction(columns, train, target):
    """Median of per-tree mean predictions; not a calibrated quantile forest."""
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    avail = [c for c in columns if c in train.columns]
    imp = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    xt = imp.fit_transform(train[avail])
    xp = imp.transform(target[avail].to_frame().T)
    rf = RandomForestRegressor(n_estimators=300, max_depth=8, min_samples_leaf=2,
                                max_features=0.7, random_state=42, n_jobs=-1)
    rf.fit(xt, y)
    preds = np.array([t.predict(xp)[0] for t in rf.estimators_])
    return max(0.0, float(np.percentile(preds, 50)))


def _rf_mean(columns, train, target, w_high=3.0):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    w = np.where(y >= 100, w_high, 1.0)
    avail = [c for c in columns if c in train.columns]
    pipe = make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        RandomForestRegressor(n_estimators=150, max_depth=7, min_samples_leaf=3,
                               max_features=0.75, random_state=42, n_jobs=-1)
    )
    pipe.fit(train[avail], y, randomforestregressor__sample_weight=w)
    return max(0.0, float(pipe.predict(target[avail].to_frame().T)[0]))


def _hgb_huber(columns, train, target):
    """HistGradientBoosting with Huber-like quantile loss robust to outliers."""
    y = np.log1p(train.conductivity_mS_per_m.to_numpy(dtype=float))
    avail = [c for c in columns if c in train.columns]
    model = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.5,
        max_iter=200, max_leaf_nodes=15,
        min_samples_leaf=10, l2_regularization=1.0,
        random_state=42
    )
    model.fit(train[avail], y)
    return max(0.0, float(np.expm1(model.predict(target[avail].to_frame().T)[0])))


def evaluate(pred: pd.DataFrame, delay: int) -> pd.DataFrame:
    models = [c for c in pred.columns if c not in ["delay","target_month","actual","split"]]
    rows = []
    for split, grp in pred.groupby("split", sort=False):
        month = pd.to_datetime(grp.target_month).dt.month
        masks = {
            "all": np.ones(len(grp), bool),
            "dry_dec_apr": month.isin([12,1,2,3,4]).to_numpy(),
            "high_ge_100": grp.actual.ge(100).to_numpy(),
        }
        for subset, mask in masks.items():
            if not mask.any(): continue
            for m in models:
                err = grp.loc[mask, m].to_numpy() - grp.loc[mask, "actual"].to_numpy()
                rows.append(dict(delay=delay, split=split, subset=subset, model=m,
                                 n=int(mask.sum()),
                                 mae=round(float(np.abs(err).mean()),3),
                                 rmse=round(float(np.sqrt(np.mean(err**2))),3),
                                 bias=round(float(err.mean()),3)))
    return pd.DataFrame(rows)


def run(delay=5):
    print(f"\n=== Final Candidates delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = load_climate(part)
    part = add_derived_features(part)

    rows = []
    for _, target in part[part.month_start.dt.year.between(2019, 2023)].iterrows():
        issue = target.issue_date
        train = part[
            (part.month_start < target.month_start) &
            (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
            (part.weather_available_at <= issue)
        ]
        if len(train) < 20: continue

        prev = part[(part.month_start < target.month_start) &
                    (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue)].sort_values("month_start")
        persistence = float(prev.conductivity_mS_per_m.iloc[-1]) if len(prev) else np.nan

        row = dict(
            delay=delay,
            target_month=target.month_start.strftime("%Y-%m-%d"),
            actual=float(target.conductivity_mS_per_m),
            split=("validation_2019_2021" if target.month_start.year <= 2021
                   else "retrospective_2022_2023"),
            Persistence=persistence,
            # Median predictors
            RF_compact=_rf_mean(COMPACT, train, target, w_high=1.0),
            RF_plus_mean=_rf_mean(COMPACT_PLUS, train, target, w_high=1.0),
            RF_compact_w3=_rf_mean(COMPACT, train, target, w_high=3.0),
            RF_plus_w3=_rf_mean(COMPACT_PLUS, train, target, w_high=3.0),
            HGB_huber=_hgb_huber(COMPACT, train, target),
            HGB_plus_huber=_hgb_huber(COMPACT_PLUS, train, target),
            # Q50 and Q90 of per-tree means; empirical coverage must be audited.
            RF_compact_q50=_q50_prediction(COMPACT, train, target),
            RF_plus_q50=_q50_prediction(COMPACT_PLUS, train, target),
            RF_compact_q90=_q90_prediction(COMPACT, train, target),
            RF_plus_q90=_q90_prediction(COMPACT_PLUS, train, target),
        )
        rows.append(row)
        if target.month_start.month == 12:
            print(f"  {target.month_start.year} done", flush=True)

    pred = pd.DataFrame(rows)
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False)
    metrics = evaluate(pred, delay)
    metrics.to_csv(OUT / f"metrics_{delay}d.csv", index=False)

    print(f"\n--- All (val 2019-2021) ---")
    val = metrics[(metrics.split=="validation_2019_2021") & (metrics.subset=="all")]
    print(val[["model","n","mae","rmse"]].sort_values("mae").to_string(index=False))
    print(f"\n--- Dry Season (val 2019-2021) ---")
    dry = metrics[(metrics.split=="validation_2019_2021") & (metrics.subset=="dry_dec_apr")]
    print(dry[["model","n","mae","rmse"]].sort_values("mae").to_string(index=False))
    print(f"\n--- EC>=100 (val 2019-2021) ---")
    hi = metrics[(metrics.split=="validation_2019_2021") & (metrics.subset=="high_ge_100")]
    print(hi[["model","n","mae","rmse"]].sort_values("mae").to_string(index=False))
    return pred, metrics


if __name__ == "__main__":
    for d in [5, 35]:
        run(d)
    print("\nAll done. Outputs in outputs/ec_final_candidates_20261029/")
