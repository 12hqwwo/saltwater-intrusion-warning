"""Systematic feature importance and new feature set experiment for EC prediction.

Key findings from Spearman correlation analysis (full history 1985-2023):
1. wind_u_t2 (rs=-0.710): ERA5 zonal wind at t-2 - MISSING from RF_compact
2. kratie_q_t2 (rs=-0.695): Kratie discharge - already in RF_compact
3. q_low_flag: binary indicator Q<5000 m3/s (rs=+0.651) - MISSING
4. rainfall_mm (rs=-0.621): already in RF_compact
5. tc_stage_t2 (rs=-0.537): already in RF_compact
6. q_tc_ratio (rs=-0.522): Q/stage ratio - MISSING

Physical interpretation:
- wind_u_t2: Easterly winds (negative u) drive stronger tidal intrusion from sea
  (La Nina = stronger easterlies in SE Asia; El Nino = weaker)
- q_low_flag: Threshold nonlinearity - salinity explodes below critical flow threshold
- q_tc_ratio: Proxy for flow-per-unit-water-level (roughness + cross-section proxy)
- ONI lag3: ENSO state 3 months ago predicts Q anomaly in dry season

New feature set tested: RF_enhanced = compact + wind_u + q_low_flag + q_tc_ratio + oni_lag3
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
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import data_matrix

CLI = ROOT / "data/external/climate_indices_20261029/climate_indices_combined.csv"
OUT = ROOT / "outputs/ec_feature_enhanced_20261029"
OUT.mkdir(parents=True, exist_ok=True)

COMPACT = ["month_sin", "month_cos", "rainfall_mm", "kratie_q_t2",
           "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]

# Physics-motivated additions
WIND_FEAT = ["wind_u_t2"]   # Monsoon/trade wind proxy for tidal intrusion
Q_THRESH_FEATS = ["q_low_flag", "q_extremelow"]  # Threshold nonlinearity
INTERACT_FEATS = ["q_tc_ratio", "oni_lag3", "oni3_t2", "enso_warm3"]

ENHANCED = COMPACT + WIND_FEAT + Q_THRESH_FEATS + INTERACT_FEATS

# All available - for RF importance analysis
ALL_FEATS = ENHANCED + ["rainfall_mm", "temperature_degC", "mt_stage_t2",
                         "vk_stage_t2", "vn_stage_t2", "pdo3_t2",
                         "rain_lag2", "rain_low", "dry_low_q"]


def _rf(seed=42, n=150, depth=8, leaf=3, feat=0.75):
    return RandomForestRegressor(n_estimators=n, max_depth=depth,
                                  min_samples_leaf=leaf, max_features=feat,
                                  random_state=seed, n_jobs=-1)


def _pipe(reg):
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        reg
    )


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add physics-motivated derived features (all lagged properly)."""
    df = df.copy()
    # Threshold indicators - critical flow nonlinearity
    df["q_low_flag"]    = (df.kratie_q_t2 < 5000).astype(float)
    df["q_extremelow"]  = (df.kratie_q_t2 < 3000).astype(float)
    df["rain_low"]      = (df.rainfall_mm < 10).astype(float)
    df["dry_low_q"]     = df.rain_low * df.q_low_flag
    df["rain_lag2"]     = df.rainfall_mm.shift(2)
    # Q/stage ratio proxy (cross-section / roughness indicator)
    df["q_tc_ratio"]    = df.kratie_q_t2 / (df.tc_stage_t2.clip(lower=0.01))
    return df


def load_climate(df: pd.DataFrame) -> pd.DataFrame:
    if not CLI.exists():
        print("  WARNING: climate indices not found", flush=True)
        return df
    cli = pd.read_csv(CLI, index_col=0, parse_dates=True).reset_index()
    cli.rename(columns={"index": "month_start"}, inplace=True)
    if "month_start" not in cli.columns:
        cli = cli.rename(columns={cli.columns[0]: "month_start"})
    keep = ["month_start", "oni_lag2", "oni_lag3", "oni3_t2", "pdo3_t2", "enso_warm3", "enso_cold3"]
    keep = [c for c in keep if c in cli.columns]
    return df.merge(cli[keep], on="month_start", how="left")


def fit_predict(columns, train, target, high_weight=1.0, seed=42):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    w = np.where(y >= 100, high_weight, 1.0)
    avail = [c for c in columns if c in train.columns]
    pipe = _pipe(_rf(seed=seed))
    wkey = "randomforestregressor__sample_weight"
    pipe.fit(train[avail], y, **{wkey: w})
    return max(0.0, float(pipe.predict(target[avail].to_frame().T)[0]))


def fit_predict_q90(columns, train, target):
    """Quantile 90th percentile via tree ensemble."""
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    avail = [c for c in columns if c in train.columns]
    imp = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    xt = imp.fit_transform(train[avail])
    xp = imp.transform(target[avail].to_frame().T)
    rf = RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=3,
                                max_features=0.75, random_state=42, n_jobs=-1)
    rf.fit(xt, y)
    preds = np.array([t.predict(xp)[0] for t in rf.estimators_])
    return max(0.0, float(np.percentile(preds, 90)))


def evaluate(pred: pd.DataFrame, delay: int) -> pd.DataFrame:
    models = [c for c in pred.columns if c not in
              ["delay","target_month","actual","split","issue_date"]]
    rows = []
    for split, grp in pred.groupby("split", sort=False):
        month = pd.to_datetime(grp.target_month).dt.month
        masks = {
            "all": np.ones(len(grp), bool),
            "dry_dec_apr": month.isin([12,1,2,3,4]).to_numpy(),
            "high_ge_100": grp.actual.ge(100).to_numpy(),
        }
        for subset, mask in masks.items():
            if not mask.any():
                continue
            for m in models:
                if m not in grp.columns:
                    continue
                err = grp.loc[mask, m].to_numpy() - grp.loc[mask, "actual"].to_numpy()
                rows.append(dict(delay=delay, split=split, subset=subset, model=m,
                                 n=int(mask.sum()), mae=round(float(np.abs(err).mean()),4),
                                 rmse=round(float(np.sqrt(np.mean(err**2))),4),
                                 bias=round(float(err.mean()),4)))
    return pd.DataFrame(rows)


def run(delay: int = 5):
    print(f"\n=== Feature-Enhanced EC Experiment  delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = load_climate(part)
    part = add_derived_features(part)

    # Validate features present
    avail = [c for c in ENHANCED if c in part.columns]
    missing = [c for c in ENHANCED if c not in part.columns]
    print(f"  Enhanced features: {len(avail)}/{len(ENHANCED)} available", flush=True)
    if missing:
        print(f"  Missing: {missing}", flush=True)

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
    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False)
    metrics = evaluate(pred, delay)
    metrics.to_csv(OUT / f"metrics_{delay}d.csv", index=False)

    print(f"\n--- Metrics {delay}d (all): ---")
    piv = metrics[metrics.subset == "all"].pivot_table(
        index="model", columns="split", values="mae"
    ).round(2)
    print(piv.to_string())
    print(f"\n--- Metrics {delay}d (dry_dec_apr / val 2019-2021): ---")
    dry = metrics[(metrics.subset=="dry_dec_apr") & (metrics.split=="validation_2019_2021")]
    print(dry[["model","n","mae","rmse"]].sort_values("mae").to_string(index=False))
    print(f"\n--- Metrics {delay}d (EC>=100 / val 2019-2021): ---")
    hi = metrics[(metrics.subset=="high_ge_100") & (metrics.split=="validation_2019_2021")]
    print(hi[["model","n","mae","rmse"]].sort_values("mae").to_string(index=False))
    return pred, metrics


if __name__ == "__main__":
    for d in [5, 35]:
        run(d)
    print("\nAll done. Outputs in outputs/ec_feature_enhanced_20261029/")
