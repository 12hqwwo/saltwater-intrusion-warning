"""Feature importance analysis + optimal compact set with wind_u.

Hypothesis: wind_u is strong signal (Spearman -0.71) but RF overselects it.
Need to find which SUBSET of new features actually helps on validation.

Strategy:
- Ablation study: add one feature at a time to COMPACT
- Use 2010-2018 rolling-origin for feature selection (not val 2019-2021)
- Measure impact on dry season and EC-high months specifically
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
from scripts.experiment_ec_feature_enhanced import add_derived_features, load_climate

OUT = ROOT / "outputs/ec_feature_ablation_20261029"
OUT.mkdir(parents=True, exist_ok=True)

COMPACT = ["month_sin", "month_cos", "rainfall_mm", "kratie_q_t2",
           "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]

# Individual additions to test
ADD_FEATS = {
    "+wind_u": ["wind_u_t2"],
    "+q_low": ["q_low_flag"],
    "+q_extreme": ["q_extremelow"],
    "+q_tc_ratio": ["q_tc_ratio"],
    "+oni_lag3": ["oni_lag3"],
    "+oni3": ["oni3_t2"],
    "+wind+qlow": ["wind_u_t2", "q_low_flag"],
    "+wind+oni": ["wind_u_t2", "oni_lag3"],
    "+wind+qlow+oni": ["wind_u_t2", "q_low_flag", "oni_lag3"],
    "+wind+qlow+qtc+oni": ["wind_u_t2", "q_low_flag", "q_tc_ratio", "oni_lag3"],
}


def _fit_predict(columns, train, target):
    y = train.conductivity_mS_per_m.to_numpy(dtype=float)
    avail = [c for c in columns if c in train.columns]
    pipe = make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        RandomForestRegressor(n_estimators=150, max_depth=7, min_samples_leaf=3,
                               max_features=0.75, random_state=42, n_jobs=-1)
    )
    pipe.fit(train[avail], y)
    return max(0.0, float(pipe.predict(target[avail].to_frame().T)[0]))


def run_ablation(delay=5):
    print(f"\n=== Ablation Study 2010-2018 delay={delay}d ===", flush=True)
    part = data_matrix(delay)
    part = load_climate(part)
    part = add_derived_features(part)

    configs = {"RF_compact": COMPACT}
    for name, extra in ADD_FEATS.items():
        configs[name] = COMPACT + extra

    result_rows = []
    for _, target in part[part.month_start.dt.year.between(2010, 2018)].iterrows():
        issue = target.issue_date
        train = part[
            (part.month_start < target.month_start) &
            (part.month_start.map(lambda t: available_date_for(t, delay)) <= issue) &
            (part.weather_available_at <= issue)
        ]
        if len(train) < 20:
            continue

        row = dict(
            target_month=target.month_start.strftime("%Y-%m-%d"),
            actual=float(target.conductivity_mS_per_m),
            year=target.month_start.year,
            dry=bool(target.month_start.month in [12,1,2,3,4]),
            high=bool(target.conductivity_mS_per_m >= 100),
        )
        for cname, cols in configs.items():
            row[cname] = _fit_predict(cols, train, target)
        result_rows.append(row)

        if target.month_start.month == 12:
            print(f"  {target.month_start.year} done", flush=True)

    pred = pd.DataFrame(result_rows)
    pred.to_csv(OUT / f"ablation_2010_2018_{delay}d.csv", index=False)

    # Summarize
    rows = []
    for model in configs.keys():
        for subset, mask in [
            ("all", np.ones(len(pred), bool)),
            ("dry", pred.dry.to_numpy()),
            ("high", pred.high.to_numpy()),
        ]:
            if not mask.any(): continue
            err = pred.loc[mask, model].to_numpy() - pred.loc[mask, "actual"].to_numpy()
            rows.append(dict(model=model, subset=subset, n=int(mask.sum()),
                             mae=round(float(np.abs(err).mean()),3),
                             rmse=round(float(np.sqrt(np.mean(err**2))),3)))
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / f"ablation_summary_{delay}d.csv", index=False)

    print(f"\n--- Ablation summary {delay}d (dry MAE) ---")
    dry_sum = summary[summary.subset=="dry"].sort_values("mae")
    print(dry_sum[["model","n","mae","rmse"]].to_string(index=False))
    print(f"\n--- Ablation summary {delay}d (high EC MAE) ---")
    hi_sum = summary[summary.subset=="high"].sort_values("mae")
    print(hi_sum[["model","n","mae","rmse"]].to_string(index=False))
    print(f"\n--- Ablation summary {delay}d (all) ---")
    all_sum = summary[summary.subset=="all"].sort_values("mae")
    print(all_sum[["model","n","mae","rmse"]].to_string(index=False))
    return pred, summary


if __name__ == "__main__":
    run_ablation(5)
    print("\nDone. Outputs in outputs/ec_feature_ablation_20261029/")
