"""Error-reduction experiment: compact RF variants + deficit features + adaptive blend.

Candidates tested (all use COMPACT feature base, strict as-of protocol):
  RF_compact        -- baseline (unchanged)
  RF_fine_compact   -- deeper trees (depth=9, leaf=2, 200 estimators)
  GB_compact_huber  -- GradientBoosting Huber loss on COMPACT features
  RF_deficit        -- compact + q_deficit_months + q_range3
  RF_fine_deficit   -- fine-tuned RF + deficit features (primary candidate)
  RF_deficit_w5     -- deficit features + sample_weight=5 for EC>=100
  RF_q75_blend      -- adaptive blend of Q50 and Q75 RF, triggered by q_ratio

Selection criterion: validation_2019_2021 MAE only. No 2022-2023 used for selection.
Research only. deployment_ready=False, gate_decision_eligible=False.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backtest_asof_ec import available_date_for
from scripts.experiment_ec_long_hydrology import data_matrix

OUT = ROOT / "outputs/ec_error_reduction_20261108"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_FILES = (
    "scripts/experiment_ec_error_reduction.py",
    "scripts/experiment_ec_long_hydrology.py",
    "scripts/experiment_ec_upstream_asof.py",
    "scripts/backtest_asof_ec.py",
    "data/research/mrc_ec_monthly_samples.csv",
    "data/external/multivariate_weather/manifest.json",
)
SOURCE_DIRS = (
    "data/external/multivariate_weather",
    "data/external/ec_feature_research_20261019",
    "data/external/mrc_kratie_discharge_20261029",
    "data/external/tien_manual_long_20261029",
    "data/external/tien_manual_history_20261029",
    "data/external/tien_multisite_supplement_20261029",
    "data/external/tien_manual_2024_2026_20261029",
)


def source_checksums():
    files = [ROOT / name for name in SOURCE_FILES]
    files.extend(path for folder in SOURCE_DIRS for path in (ROOT / folder).iterdir()
                 if path.suffix.lower() in {".csv", ".json"})
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(files)}

COMPACT = [
    "month_sin", "month_cos", "rainfall_mm",
    "kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2",
    "tc_stage_t2", "tc_stage3_t2",
]
DRY_MONTHS = {11, 12, 1, 2, 3, 4}


# ---------------------------------------------------------------------------
# Feature engineering: deficit accumulator
# ---------------------------------------------------------------------------

def add_deficit_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add q_deficit_months and q_range3 — both computed on the full series,
    then lagged by 2 months so they're always available at issue-date (day 6
    of the preceding month)."""
    df = df.copy().sort_values("weather_month").reset_index(drop=True)

    q = df["kratie_q_t2"]          # already the t-2 value from data_matrix()
    # Range: max minus min of Q over trailing 3 months
    q_range3 = q.rolling(3, min_periods=2).max() - q.rolling(3, min_periods=2).min()

    # Use ratio-based deficit (more stable than absolute Q)
    ratio = df["kratie_q_ratio_t2"]
    deficit_ratio = ratio.rolling(5, min_periods=2).apply(
        lambda x: float((x < 0.80).sum()) if np.isfinite(x).sum() >= 2 else np.nan,
        raw=True,
    )

    df["q_deficit_months"] = deficit_ratio.values
    df["q_range3"] = q_range3.values
    return df


DEFICIT = COMPACT + ["q_deficit_months", "q_range3"]


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

def _rf_compact():
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        RandomForestRegressor(n_estimators=100, max_depth=7, min_samples_leaf=3,
                              max_features=0.8, random_state=42, n_jobs=1),
    )


def _rf_fine():
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        RandomForestRegressor(n_estimators=200, max_depth=9, min_samples_leaf=2,
                              max_features=0.75, random_state=42, n_jobs=1),
    )


def _gb_huber():
    return make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        GradientBoostingRegressor(loss="huber", alpha=0.90,
                                  n_estimators=200, max_depth=3,
                                  learning_rate=0.03, min_samples_leaf=10,
                                  subsample=0.8, random_state=42),
    )


# ---------------------------------------------------------------------------
# Fit helpers
# ---------------------------------------------------------------------------

def _predict(model, train, target, cols, high_weight=1.0):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    avail = [c for c in cols if c in train.columns and c in target.index]
    if not avail:
        return np.nan
    weights = np.where(y >= 100, high_weight, 1.0)
    if hasattr(model[-1], "n_estimators"):
        # RF / GB — pass sample_weight
        step_name = type(model[-1]).__name__.lower()
        wkey = f"{step_name}__sample_weight"
        model.fit(train[avail], y, **{wkey: weights})
    else:
        model.fit(train[avail], y)
    return max(0.0, float(model.predict(target[avail].to_frame().T)[0]))


def _predict_q75(train, target, cols):
    """Return 75th-percentile of tree ensemble predictions."""
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    avail = [c for c in cols if c in train.columns and c in target.index]
    imp = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    xt = imp.fit_transform(train[avail])
    xp = imp.transform(target[avail].to_frame().T)
    rf = RandomForestRegressor(n_estimators=200, max_depth=7, min_samples_leaf=3,
                               max_features=0.8, random_state=42, n_jobs=1)
    rf.fit(xt, y)
    tree_preds = np.array([t.predict(xp)[0] for t in rf.estimators_])
    return max(0.0, float(np.percentile(tree_preds, 75)))


# ---------------------------------------------------------------------------
# Adaptive Q75 blend
# ---------------------------------------------------------------------------

def adaptive_q75_blend(rf_mean: float, rf_p75: float,
                        q_ratio: float, month: int) -> float:
    """Blend the RF mean and the 75th percentile of its tree predictions.

    Blend weight w increases as q_ratio falls below 0.80, but only during
    dry season (months 11-4).  w is capped at 0.50 so the blend never
    exceeds the Q75 estimate entirely.
    """
    if month not in DRY_MONTHS or np.isnan(q_ratio):
        return rf_mean
    deficit_signal = max(0.0, 1.0 - q_ratio)        # 0 when normal, 1 when no flow
    w = min(0.50, deficit_signal * 0.70)              # cap at 50 %
    return (1 - w) * rf_mean + w * rf_p75


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run(delay: int = 5):
    print(f"\n=== EC error-reduction experiment  delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = add_deficit_features(part)

    rows = []
    for _, target in part[part.month_start.dt.year.between(2019, 2023)].iterrows():
        issue = target.issue_date
        train = part[
            (part.month_start < target.month_start) &
            (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
            (part.weather_available_at <= issue)
        ]
        if len(train) < 96:
            raise ValueError(f"Too few training rows ({len(train)}) for {target.month_start}")
        if available_date_for(target.weather_month, 5) > issue:
            raise ValueError("Future water-level used")

        q_ratio = float(target.kratie_q_ratio_t2) if not pd.isna(target.kratie_q_ratio_t2) else np.nan
        tmonth = int(target.month_start.month)

        # Persistence baseline
        prev = part[
            (part.month_start < target.month_start) &
            (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue)
        ].sort_values("month_start")
        persistence = float(prev.conductivity_mS_per_m.iloc[-1]) if len(prev) else np.nan

        # --- Candidates ---
        c_rf      = _predict(_rf_compact(), train, target, COMPACT)
        c_fine    = _predict(_rf_fine(),    train, target, COMPACT)
        c_gb      = _predict(_gb_huber(),   train, target, COMPACT)
        c_deficit = _predict(_rf_compact(), train, target, DEFICIT)
        c_fine_d  = _predict(_rf_fine(),    train, target, DEFICIT)
        c_def_w5  = _predict(_rf_compact(), train, target, DEFICIT, high_weight=5.0)

        # Adaptive Q75 blend (uses COMPACT features)
        p75       = _predict_q75(train, target, COMPACT)
        c_blend   = adaptive_q75_blend(c_rf, p75, q_ratio, tmonth)

        rows.append(dict(
            delay_days=delay,
            target_month=target.month_start.strftime("%Y-%m-%d"),
            issue_date=str(issue),
            split=("validation_2019_2021" if target.month_start.year <= 2021
                   else "retrospective_2022_2023"),
            actual=float(target.conductivity_mS_per_m),
            train_n=len(train),
            q_ratio=q_ratio,
            Persistence=persistence,
            RF_compact=c_rf,
            RF_fine_compact=c_fine,
            GB_compact_huber=c_gb,
            RF_deficit=c_deficit,
            RF_fine_deficit=c_fine_d,
            RF_deficit_w5=c_def_w5,
            RF_q75_blend=c_blend,
        ))

        if target.month_start.month == 12:
            print(f"  completed {delay}d / {target.month_start.year}", flush=True)

    pred = pd.DataFrame(rows)
    if len(pred) != 60 or pred.target_month.duplicated().any():
        raise ValueError(f"Expected 60 unique months, got {len(pred)}")

    # --- Metrics ---
    candidates = ["RF_compact", "RF_fine_compact", "GB_compact_huber",
                  "RF_deficit", "RF_fine_deficit", "RF_deficit_w5",
                  "RF_q75_blend", "Persistence"]
    metrics = []
    for split, group in pred.groupby("split", sort=False):
        month = pd.to_datetime(group.target_month).dt.month
        masks = {
            "all": np.ones(len(group), bool),
            "dry_dec_apr": month.isin([12, 1, 2, 3, 4]).to_numpy(),
            "high_ge_100": group.actual.ge(100).to_numpy(),
        }
        for subset, mask in masks.items():
            if not mask.any():
                continue
            for name in candidates:
                if name not in group.columns:
                    continue
                err = group.loc[mask, name].to_numpy() - group.loc[mask, "actual"].to_numpy()
                metrics.append(dict(
                    delay_days=delay, split=split, subset=subset, model=name,
                    n=int(mask.sum()),
                    mae=round(float(np.abs(err).mean()), 4),
                    rmse=round(float(np.sqrt(np.mean(err ** 2))), 4),
                    bias=round(float(err.mean()), 4),
                ))

    pred.to_csv(OUT / f"predictions_{delay}d.csv", index=False, encoding="utf-8-sig")
    mdf = pd.DataFrame(metrics)
    mdf.to_csv(OUT / f"metrics_{delay}d.csv", index=False, encoding="utf-8-sig")

    # --- Summary print ---
    print(f"\n--- Validation 2019–2021 (all months) ---")
    val = mdf[(mdf.split == "validation_2019_2021") & (mdf.subset == "all")]
    print(val[["model", "n", "mae", "rmse", "bias"]].sort_values("mae").to_string(index=False))

    print(f"\n--- Validation 2019–2021 (EC >= 100) ---")
    hi = mdf[(mdf.split == "validation_2019_2021") & (mdf.subset == "high_ge_100")]
    print(hi[["model", "n", "mae", "rmse"]].sort_values("mae").to_string(index=False))

    print(f"\n--- Retrospective 2022–2023 (all months) ---")
    ret = mdf[(mdf.split == "retrospective_2022_2023") & (mdf.subset == "all")]
    print(ret[["model", "n", "mae", "rmse"]].sort_values("mae").to_string(index=False))

    # Save protocol
    (OUT / f"protocol_{delay}d.json").write_text(json.dumps(dict(
        issue="day 6 of preceding month",
        ec_delay_days=delay,
        sklearn_version=sklearn.__version__,
        pandas_version=pd.__version__,
        source_sha256=source_checksums(),
        candidates=candidates,
        new_features=["q_deficit_months (5-month rolling count of ratio<0.80)",
                      "q_range3 (3-month Q range)"],
        blend_rule="q75_blend: RF mean mixed with tree-prediction p75; weight=(1-q_ratio)*0.70 capped at 0.50, only dry season months",
        selection_rule="validation_2019_2021 MAE only",
        retrospective="2022-2023 previously inspected; not used for selection",
        deployment_ready=False,
        gate_decision_eligible=False,
        limitation="No EC observations after 2023; extreme EC (03/2020: 692 mS/m) "
                   "remains underpredicted due to training distribution ceiling",
    ), indent=2), encoding="utf-8")

    return pred, mdf


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=int, choices=[5, 35], default=5)
    args = parser.parse_args()
    run(args.delay)
    print(f"\nDone. Results in outputs/ec_error_reduction_20261108/")
