import pandas as pd
import numpy as np

# Load predictions from final candidates
p5 = pd.read_csv("outputs/ec_final_candidates_20261029/predictions_5d.csv")
p35 = pd.read_csv("outputs/ec_final_candidates_20261029/predictions_35d.csv")

for label, p in [("delay=5d", p5), ("delay=35d", p35)]:
    print(f"\n==================== {label} ====================")
    # Let's test combinations of Q50 and Q90
    # 1. Simple Average: 0.5*q50 + 0.5*q90
    p["Ensemble_50_90"] = 0.5 * p["RF_compact_q50"] + 0.5 * p["RF_compact_q90"]
    # 2. Risk-weighted: 0.3*q50 + 0.7*q90
    p["Ensemble_Risk70"] = 0.3 * p["RF_compact_q50"] + 0.7 * p["RF_compact_q90"]
    # 3. Huber + Q90 blend
    p["Ensemble_Huber_Q90"] = 0.5 * p["HGB_plus_huber"] + 0.5 * p["RF_compact_q90"]
    
    # Evaluate across subsets
    for split in ["validation_2019_2021", "retrospective_2022_2023"]:
        sub = p[p.split == split]
        print(f"\n--- Split: {split} (n={len(sub)}) ---")
        
        candidates = ["Persistence", "RF_compact", "RF_compact_q50", "RF_compact_q90", 
                      "HGB_plus_huber", "Ensemble_50_90", "Ensemble_Huber_Q90"]
        
        res = []
        for m in candidates:
            err = sub[m] - sub["actual"]
            mae_all = np.abs(err).mean()
            rmse_all = np.sqrt(np.mean(err**2))
            
            # dry season
            dry_mask = pd.to_datetime(sub.target_month).dt.month.isin([12, 1, 2, 3, 4])
            dry_err = err[dry_mask]
            mae_dry = np.abs(dry_err).mean() if len(dry_err) else np.nan
            rmse_dry = np.sqrt(np.mean(dry_err**2)) if len(dry_err) else np.nan
            
            # high EC (>=100)
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
