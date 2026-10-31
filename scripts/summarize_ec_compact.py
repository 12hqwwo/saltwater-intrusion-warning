"""Recompute matched MAE and the 15 largest compact-model errors."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/ec_extreme_robust_20261029"
OUT = ROOT / "outputs/ec_compact_summary_20261029"
MODELS = ["RF_old", "RF_flow_stage_no_ec", "RF_compact", "RF_compact_weight8",
          "Persistence", "MonthlyClimatology"]


def main():
    metrics = []
    largest = []
    sources = {}
    for delay in [5,35]:
        path = SOURCE / f"predictions_{delay}d.csv"
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        p = pd.read_csv(path)
        if len(p) != 60 or p.target_month.duplicated().any() or p[MODELS + ["actual"]].isna().any().any():
            raise ValueError("Incomplete matched cohort")
        dates = pd.to_datetime(p.target_month)
        p["month"] = dates.dt.month
        p["year"] = dates.dt.year
        for split, group in p.groupby("split"):
            subsets = {"all": np.ones(len(group),dtype=bool),
                       "dry_dec_apr":group.month.isin([12,1,2,3,4]).to_numpy(),
                       "high_ge_100":group.actual.ge(100).to_numpy()}
            for subset, mask in subsets.items():
                if not mask.any():
                    continue
                for model in MODELS:
                    e=group.loc[mask,model].to_numpy()-group.loc[mask,"actual"].to_numpy()
                    metrics.append(dict(delay_days=delay,split=split,subset=subset,model=model,
                        n=int(mask.sum()),mae_mS_m=float(np.abs(e).mean()),
                        rmse_mS_m=float(np.sqrt(np.mean(e*e))),bias_mS_m=float(e.mean())))
            ranked = group.copy()
            ranked["compact_error_mS_m"] = ranked.RF_compact-ranked.actual
            ranked["compact_abs_error_mS_m"] = ranked.compact_error_mS_m.abs()
            ranked["hydrology_abs_error_mS_m"] = (ranked.RF_flow_stage_no_ec-ranked.actual).abs()
            for _, row in ranked.nlargest(15,"compact_abs_error_mS_m").iterrows():
                largest.append(dict(delay_days=delay,split=split,target_month=row.target_month,
                    season="DRY" if row.month in [12,1,2,3,4] else "WET",
                    high_ec=bool(row.actual>=100),actual_ec_mS_m=row.actual,
                    compact_ec_mS_m=row.RF_compact,compact_error_mS_m=row.compact_error_mS_m,
                    compact_abs_error_mS_m=row.compact_abs_error_mS_m,
                    hydrology_ec_mS_m=row.RF_flow_stage_no_ec,
                    hydrology_abs_error_mS_m=row.hydrology_abs_error_mS_m,
                    persistence_ec_mS_m=row.Persistence))
    OUT.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(metrics).to_csv(OUT/"matched_metrics.csv",index=False)
    pd.DataFrame(largest).to_csv(OUT/"largest_15_errors_per_split.csv",index=False)
    (OUT/"manifest.json").write_text(json.dumps(dict(source_sha256=sources,
        subsets="dry=December-April; high EC>=100 mS/m; same months per model",
        selection="primary +5d validation overall MAE only; 2022-2023 previously inspected",
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [OUT/"matched_metrics.csv",OUT/"largest_15_errors_per_split.csv"]}),
        indent=2),encoding="utf-8")
    print(pd.DataFrame(metrics).query("model in ['RF_old','RF_flow_stage_no_ec','RF_compact','Persistence']").to_string(index=False))


if __name__ == "__main__":
    main()
