import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.experiment_ec_feature_enhanced import load_climate, add_derived_features

# Load prediction records and merge with hydro features
for delay in [5, 35]:
    p = pd.read_csv(f"outputs/ec_final_candidates_20261029/predictions_{delay}d.csv")
    dm = data_matrix(delay)
    dm = load_climate(dm)
    dm["target_month"] = dm.month_start.dt.strftime("%Y-%m-%d")
    merged = pd.merge(p, dm[["target_month", "kratie_q_t2", "tc_stage_t2", "rainfall_mm", "oni_lag3"]], on="target_month", how="left")
    
    # Define adaptive weight w_risk in [0, 1]
    # In wet season (months 6-11), risk = 0
    month = pd.to_datetime(merged.target_month).dt.month
    is_dry = month.isin([12, 1, 2, 3, 4, 5])
    
    # Upstream stress: when kratie_q_t2 is low (< 3500 m3/s) or oni_lag3 > 0.5
    q_norm = (merged.kratie_q_t2.clip(lower=1500, upper=4000) - 1500) / (4000 - 1500)
    flow_stress = 1.0 - q_norm # 1 when Q=1500, 0 when Q>=4000
    
    oni_stress = (merged.oni_lag3.clip(lower=0.0, upper=2.0)) / 2.0
    
    # Combined risk score during dry season
    risk = np.where(is_dry, 0.4 * flow_stress + 0.3 * oni_stress + 0.3, 0.0)
    risk = np.clip(risk, 0.0, 0.85) # max weight to q90 is 0.85
    
    # Adaptive Ensemble:
    # Blend HGB_plus_huber (or RF_compact_q50) with RF_compact_q90
    merged["Adaptive_Q50_Q90"] = (1.0 - risk) * merged["RF_compact_q50"] + risk * merged["RF_compact_q90"]
    merged["Adaptive_Huber_Q90"] = (1.0 - risk) * merged["HGB_plus_huber"] + risk * merged["RF_compact_q90"]
    
    print(f"\n==================== ADAPTIVE ENSEMBLE delay={delay}d ====================")
    for split in ["validation_2019_2021", "retrospective_2022_2023"]:
        sub = merged[merged.split == split]
        print(f"\n--- Split: {split} (n={len(sub)}) ---")
        
        candidates = ["Persistence", "RF_compact", "RF_compact_q90", "HGB_plus_huber", 
                      "Adaptive_Q50_Q90", "Adaptive_Huber_Q90"]
        res = []
        for m in candidates:
            err = sub[m] - sub["actual"]
            mae_all = np.abs(err).mean()
            rmse_all = np.sqrt(np.mean(err**2))
            
            dry_mask = pd.to_datetime(sub.target_month).dt.month.isin([12, 1, 2, 3, 4])
            dry_err = err[dry_mask]
            mae_dry = np.abs(dry_err).mean() if len(dry_err) else np.nan
            rmse_dry = np.sqrt(np.mean(dry_err**2)) if len(dry_err) else np.nan
            
            hi_mask = sub.actual >= 100
            hi_err = err[hi_mask]
            mae_hi = np.abs(hi_err).mean() if hi_mask.any() else np.nan
            rmse_hi = np.sqrt(np.mean(hi_err**2)) if hi_mask.any() else np.nan
            
            res.append({
                "model": m,
                "all_mae": round(mae_all, 2),
                "all_rmse": round(rmse_all, 2),
                "dry_mae": round(mae_dry, 2),
                "dry_rmse": round(rmse_dry, 2),
                "high_mae": round(mae_hi, 2) if hi_mask.any() else "-",
                "high_rmse": round(rmse_hi, 2) if hi_mask.any() else "-"
            })
        print(pd.DataFrame(res).to_string(index=False))
