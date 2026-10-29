"""Fit the validation-selected compact My Tho EC model as a research artifact."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from scripts.experiment_ec_extreme_robust import COMPACT
from scripts.experiment_ec_long_hydrology import data_matrix
from scripts.forecast_mytho_ec_hydrology import current_row

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ec_compact_candidate_20261029"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    train = data_matrix(5)
    if len(train) != 463 or train.month_start.max() != pd.Timestamp("2023-12-01"):
        raise ValueError("Unexpected training target coverage")
    current, weather = current_row()
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True,
                                        keep_empty_features=True),
                          RandomForestRegressor(n_estimators=100, max_depth=7,
                              min_samples_leaf=3, max_features=.8,
                              random_state=42, n_jobs=-1))
    model.fit(train[COMPACT], train.conductivity_mS_per_m)
    prediction = max(0.0, float(model.predict(current[COMPACT])[0]))
    OUT.mkdir(parents=True, exist_ok=True)
    artifact = OUT / "mytho_rf_compact.joblib"
    joblib.dump(model, artifact)
    reloaded = joblib.load(artifact)
    if not np.isclose(reloaded.predict(current[COMPACT])[0], prediction, atol=1e-9):
        raise ValueError("Reloaded artifact forecast differs")
    source = [ROOT / "data/research/mrc_ec_monthly_samples.csv",
              ROOT / "data/external/multivariate_weather/manifest.json",
              ROOT / "data/external/ec_feature_research_20261019/era5_extra_MyTho.json",
              ROOT / "data/external/mrc_kratie_discharge_20261029/014901_Discharge_Calculated daily discharge_22a8130e.csv",
              ROOT / "data/external/tien_manual_long_20261029/019803_Water_Level_Manual_3bd17f3a.csv",
              ROOT / "data/external/tien_manual_2024_2026_20261029/019803_Water_Level_Manual_3bd17f3a.csv",
              ROOT / "data/external/ec_hydrology_current_20261029/era5_extra_MyTho_2026-09.json",
              ROOT / "scripts/experiment_ec_extreme_robust.py",
              ROOT / "scripts/experiment_ec_long_hydrology.py",
              ROOT / "scripts/backtest_asof_ec.py"]
    scores = {}
    for delay in [5,35]:
        frame = pd.read_csv(ROOT / "outputs/ec_extreme_robust_20261029" / f"metrics_{delay}d.csv")
        scores[str(delay)] = frame[(frame.subset.isin(["all", "dry_dec_apr", "high_ge_100"])) &
                                   (frame.model.isin(["RF_old", "RF_flow_stage_no_ec", "RF_compact", "Persistence"]))].to_dict(orient="records")
    manifest = dict(model="RF_compact", version="research-2026-10-29",
        sklearn_version=sklearn.__version__,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        feature_order=COMPACT, feature_values=current[COMPACT].iloc[0].to_dict(),
        hyperparameters=dict(n_estimators=100,max_depth=7,min_samples_leaf=3,
                             max_features=.8,random_state=42),
        train_rows=len(train), train_end="2023-12", target="single My Tho EC sample in target month, mS/m",
        hypothetical_issue_date="2026-10-06", target_month="2026-11",
        predicted_ec_mS_m=prediction, weather_source=weather,
        validation_selection="RF_compact has lowest overall MAE among tested compact/weighted candidates on 2019-2021 under primary +5d release assumption",
        retrospective_status="2022-2023 previously inspected; not blind holdout",
        source_sha256={str(path.relative_to(ROOT)):sha(path) for path in source},
        artifact_sha256=sha(artifact), backtest_metrics=scores,
        deployment_ready=False, gate_decision_eligible=False,
        limitations=["No EC observations after 2023 to validate 2026 prediction",
                     "No historical source vintages or actual EC publication timestamps",
                     "Extreme EC still badly underpredicted; no new extreme months in 2022-2023",
                     "Upstream Q/stage features are predictors, not validated salt propagation"])
    (OUT / "manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    pd.DataFrame([dict(target_month="2026-11", station="MYTHO",
        ec_mS_m=prediction, model="RF_compact", status="RESEARCH_ONLY_UNVALIDATED_2026")]).to_csv(
            OUT / "forecast_2026_11.csv",index=False)
    print(f"research forecast EC 2026-11: {prediction:.3f} mS/m")


if __name__ == "__main__":
    main()
