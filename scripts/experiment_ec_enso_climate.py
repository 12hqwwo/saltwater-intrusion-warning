"""Experiment: add ENSO/climate indices + log-space RF to reduce EC peak error.

Key ideas from literature (Eslami et al. 2021, Loc et al. 2021):
1. ENSO (ONI) strongly modulates Mekong upstream flow with 2-4 month lag.
2. El Nino -> lower Q Kratie -> higher salinity intrusion.
3. Modelling in log-space reduces right-skew and may improve peak prediction.
4. Quantile RF at 90th percentile provides upper bound for extreme years.

Protocol:
- Same as-of rolling-origin backtest as RF_compact.
- Training on months available at issue date, no 2022-2023 used for selection.
- Candidates: RF_compact (baseline), RF_enso (compact+ONI), RF_log (log-EC),
  RF_enso_log, RF_q90 (quantile 0.9), RF_enso_q90.
- Validation: 2019-2021 (36 months), retrospective check: 2022-2023 (24 months).

Note: ONI is publicly available monthly from NOAA PSL. Lag-2 is minimum safe
lag (published ~4 weeks after month end; we assume available at delay+5 days).
"""
from __future__ import annotations
import json
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
from scripts.experiment_ec_no_recent_label import WEATHER, FLOW, STAGE

OUT = ROOT / "outputs/ec_enso_experiment_20261029"
OUT.mkdir(parents=True, exist_ok=True)

CLIMATE = ROOT / "data/external/climate_indices_20261029/climate_indices_combined.csv"

COMPACT = ["month_sin", "month_cos", "rainfall_mm", "kratie_q_t2",
           "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]

ENSO_FEATS = ["oni_lag2", "oni_lag3", "oni3_t2", "pdo3_t2", "enso_warm3"]

COMPACT_ENSO = COMPACT + ENSO_FEATS


def _rf(n_estimators=100, max_depth=7, min_samples_leaf=3, max_features=0.8, seed=42):
    return RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth,
                                  min_samples_leaf=min_samples_leaf, max_features=max_features,
                                  random_state=seed, n_jobs=-1)


def _pipe(regressor):
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        regressor
    )


def fit_predict_standard(columns, train, target):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    pipe = _pipe(_rf())
    pipe.fit(train[columns], y)
    return max(0.0, float(pipe.predict(target[columns].to_frame().T)[0]))


def fit_predict_log(columns, train, target):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    logy = np.log1p(y)
    pipe = _pipe(_rf())
    pipe.fit(train[columns], logy)
    return max(0.0, float(np.expm1(pipe.predict(target[columns].to_frame().T)[0])))


def fit_predict_quantile90(columns, train, target):
    """Approximate quantile RF: train multiple trees & take 90th pct of leaf predictions."""
    from sklearn.ensemble import RandomForestRegressor as RFR
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    xt = imputer.fit_transform(train[columns])
    xpred = imputer.transform(target[columns].to_frame().T)
    # Fit RF with 200 trees, get all tree predictions -> take 90th pct
    rf = RFR(n_estimators=200, max_depth=7, min_samples_leaf=3,
             max_features=0.8, random_state=42, n_jobs=-1)
    rf.fit(xt, y)
    tree_preds = np.array([t.predict(xpred)[0] for t in rf.estimators_])
    return max(0.0, float(np.percentile(tree_preds, 90)))


def load_climate(part: pd.DataFrame) -> pd.DataFrame:
    if not CLIMATE.exists():
        print(f"  WARNING: {CLIMATE.name} not found; ENSO features will be NaN", flush=True)
        for f in ENSO_FEATS:
            part[f] = np.nan
        return part
    cli = pd.read_csv(CLIMATE, index_col=0, parse_dates=True)
    cli.index.name = "weather_month"
    cli = cli.reset_index()
    part = part.merge(cli[["weather_month"] + ENSO_FEATS], on="weather_month", how="left")
    return part


def evaluate(pred: pd.DataFrame, delay: int) -> pd.DataFrame:
    models = ["RF_compact", "RF_enso", "RF_log", "RF_enso_log", "RF_q90", "RF_enso_q90", "Persistence"]
    rows = []
    for split, group in pred.groupby("split", sort=False):
        month = pd.to_datetime(group.target_month).dt.month
        masks = {
            "all": np.ones(len(group), bool),
            "dry_dec_apr": month.isin([12,1,2,3,4]).to_numpy(),
            "high_ge_100": group.actual.ge(100).to_numpy(),
        }
        for subset, mask in masks.items():
            if not mask.any():
                continue
            for name in models:
                if name not in group.columns:
                    continue
                err = group.loc[mask, name].to_numpy() - group.loc[mask, "actual"].to_numpy()
                rows.append(dict(delay=delay, split=split, subset=subset, model=name,
                                 n=int(mask.sum()), mae=float(np.abs(err).mean()),
                                 rmse=float(np.sqrt(np.mean(err**2))),
                                 bias=float(err.mean())))
    return pd.DataFrame(rows)


def run(delay: int = 5):
    print(f"\n=== delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = load_climate(part)
    print(f"  ENSO coverage: {part[ENSO_FEATS[0]].notna().sum()}/{len(part)} months", flush=True)

    rows = []
    for _, target in part[part.month_start.dt.year.between(2019, 2023)].iterrows():
        issue = target.issue_date
        train = part[
            (part.month_start < target.month_start) &
            (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
            (part.weather_available_at <= issue)
        ]
        if len(train) < 20:
            continue

        # Persistence
        prev_months = part[part.month_start < target.month_start].sort_values("month_start")
        persistence = float(prev_months.conductivity_mS_per_m.iloc[-1]) if len(prev_months) else np.nan

        row = dict(
            delay=delay,
            target_month=target.month_start.strftime("%Y-%m-%d"),
            actual=float(target.conductivity_mS_per_m),
            split=("validation_2019_2021" if target.month_start.year <= 2021
                   else "retrospective_2022_2023"),
            Persistence=persistence,
            RF_compact=fit_predict_standard(COMPACT, train, target),
            RF_enso=fit_predict_standard(COMPACT_ENSO, train, target),
            RF_log=fit_predict_log(COMPACT, train, target),
            RF_enso_log=fit_predict_log(COMPACT_ENSO, train, target),
            RF_q90=fit_predict_quantile90(COMPACT, train, target),
            RF_enso_q90=fit_predict_quantile90(COMPACT_ENSO, train, target),
        )
        rows.append(row)
        if target.month_start.month == 12:
            print(f"  completed {delay}d / {target.month_start.year}", flush=True)

    pred = pd.DataFrame(rows)
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False)

    metrics = evaluate(pred, delay)
    metrics.to_csv(OUT / f"metrics_{delay}d.csv", index=False)

    # Print summary
    print(f"\nMetrics {delay}d:")
    summary = metrics[metrics.subset == "all"].pivot_table(
        index="model", columns="split", values="mae"
    ).round(2)
    print(summary.to_string())
    return pred, metrics


if __name__ == "__main__":
    for d in [5, 35]:
        run(d)
    print("\nDone. Results in outputs/ec_enso_experiment_20261029/")
