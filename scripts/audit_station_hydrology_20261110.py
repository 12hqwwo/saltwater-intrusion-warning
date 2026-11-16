"""Offline feature screening for Tan Chau/My Thuan; never promotes a model."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import sklearn

from tools.model_training import FEATURES, pipeline, training_frame
from tools.feature_building import monthly_kratie_flow, monthly_stage
from tools.backtest_protocols import available_date_for, issue_date_for

OUT = ROOT / "outputs/station_hydrology_screening_20261110"
WINDOWS = {"2019_2021": ("2019-01-01", "2021-12-01"),
           "2021_2023": ("2021-01-01", "2023-12-01"),
           "2022_2023": ("2022-01-01", "2023-12-01")}
FLOW = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2"]
TC = ["tc_stage_t2", "tc_stage3_t2"]
MT = ["mt_stage_t2", "mt_stage3_t2"]


def scores(actual, prediction):
    error = prediction - actual
    return dict(n=len(error), mae=float(np.abs(error).mean()),
                rmse=float(np.sqrt(np.square(error).mean())), bias=float(error.mean()))


def run():
    registry = ROOT / "data/models/multivariate_registry.json"
    registry_hash = hashlib.sha256(registry.read_bytes()).hexdigest()
    data, _ = training_frame(ROOT / "data/research/mrc_ec_monthly_samples.csv",
                             ROOT / "data/external/multivariate_weather/manifest.json")
    for hydro in (monthly_kratie_flow(), monthly_stage("019803", "tc"),
                  monthly_stage("019804", "mt")):
        data = data.merge(hydro, on="weather_month", how="left", validate="many_to_one")
    old = pd.read_csv(ROOT / "outputs/frozen_ec_gap_20261104/predictions.csv")
    records, predictions, contracts = [], [], {}
    for station in ("TANCHAU", "MYTHUAN"):
        part = data[data.station.eq(station)].sort_values("month_start").copy()
        local = TC if station == "TANCHAU" else MT
        candidates = {"WeatherOnly": FEATURES,
                      "WeatherFlow": FEATURES + FLOW,
                      "WeatherLocalStage": FEATURES + local,
                      "WeatherFlowLocalStage": FEATURES + FLOW + local}
        if station == "MYTHUAN":
            candidates["WeatherTanChauStage"] = FEATURES + TC
            candidates["WeatherFlowTanChauStage"] = FEATURES + FLOW + TC
            candidates["WeatherFlowBothStages"] = FEATURES + FLOW + TC + MT
        contracts[station] = candidates
        for delay in (5, 35):
            for window, (start, end) in WINDOWS.items():
                issue = issue_date_for(pd.Timestamp(start))
                known = part[(part.month_start < pd.Timestamp(start)) &
                    part.month_start.map(lambda m: available_date_for(m, delay) <= issue) &
                    part.weather_month.map(lambda m: available_date_for(m, 5) <= issue)]
                future = part[part.month_start.between(start, end)].copy()
                assert len(future) == len(pd.date_range(start, end, freq="MS"))
                actual = future.conductivity_mS_per_m.to_numpy()
                p90 = float(known.conductivity_mS_per_m.quantile(.9))
                values = {"FrozenPersistence": np.full(len(future), known.conductivity_mS_per_m.iloc[-1]),
                          "MonthlyClimatology": future.month_start.dt.month.map(
                              known.groupby(known.month_start.dt.month).conductivity_mS_per_m.mean()).to_numpy()}
                for name, columns in candidates.items():
                    # Missing historical predictors are imputed using training only.
                    # Every evaluated future month must have complete measured inputs.
                    assert not known[columns].isna().all().any()
                    assert np.isfinite(future[columns].to_numpy()).all()
                    model = pipeline().set_params(randomforestregressor__n_jobs=1)
                    model.fit(known[columns], known.conductivity_mS_per_m)
                    values[name] = model.predict(future[columns])
                reference = old[(old.station == station) & (old.ec_delay_days == delay) &
                                (old.experiment == "gap_" + window)].sort_values("target_month")
                assert np.allclose(actual, reference.actual_mS_m, rtol=0, atol=1e-10)
                assert np.allclose(values["WeatherOnly"], reference.RandomForest, rtol=0, atol=1e-8)
                for name, predicted in values.items():
                    masks = {"all": np.ones(len(future), dtype=bool),
                             "dry_Dec_Apr": future.month_start.dt.month.isin([12, 1, 2, 3, 4]).to_numpy(),
                             "high_training_p90": actual >= p90}
                    for cohort, mask in masks.items():
                        if not mask.any():
                            continue
                        records.append(dict(station=station, delay=delay, window=window,
                            model=name, cohort=cohort, **scores(actual[mask], predicted[mask]),
                            p90=p90, false_high=int(((predicted[mask] >= p90) & (actual[mask] < p90)).sum()),
                            missed_high=int(((predicted[mask] < p90) & (actual[mask] >= p90)).sum()),
                            training_n=len(known), training_through=str(known.month_start.max().date())))
                    for month, a, p in zip(future.month_start, actual, predicted):
                        predictions.append(dict(station=station, delay=delay, window=window,
                            model=name, target_month=str(month.date()), actual=a, predicted=p))
                print(station, delay, window, "complete", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame(predictions).to_csv(OUT / "predictions.csv", index=False)
    source_paths = [Path(__file__), ROOT / "data/research/mrc_ec_monthly_samples.csv",
                    ROOT / "data/external/multivariate_weather/manifest.json"]
    for folder, pattern in [
        ("mrc_kratie_discharge_20261029", "014901_Discharge_Calculated daily discharge_*.csv"),
        ("tien_manual_long_20261029", "019803_Water_Level_Manual_*.csv"),
        ("tien_manual_2024_2026_20261029", "019803_Water_Level_Manual_*.csv"),
        *[(folder, "019804_Water_Level_Manual_*.csv") for folder in
          ("tien_manual_long_20261029", "tien_manual_history_20261029", "tien_multisite_supplement_20261029")]]:
        source_paths.extend(p for p in (ROOT / "data/external" / folder).glob(pattern)
                            if not p.stem.endswith("_daily"))
    protocol = dict(stations=contracts, windows=WINDOWS, ec_delay_days=[5, 35],
        input_lag_months=2, sklearn_version=sklearn.__version__, pandas_version=pd.__version__,
        parameters=dict(trees=300, max_depth=8, min_samples_leaf=3, seed=42),
        evaluation="Fit once before each outage; withheld station EC only used for scoring. Weather-only predictions match existing frozen controls within 1e-8.",
        limitations=["Retrospective screening; periods previously inspected, not blind validation.",
            "Overlapping windows are not independent; do not pool their scores.",
            "Historical publication time assumed month end +5 days for weather/hydrology.",
            "My Thuan stage archive ends in 2023; candidates using it cannot currently serve 2026.",
            "No independent between-station EC used to validate full-axis interpolation."],
        source_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in source_paths},
        output_sha256={name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                       for name in ("metrics.csv", "predictions.csv")})
    (OUT / "protocol.json").write_text(json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8")
    assert hashlib.sha256(registry.read_bytes()).hexdigest() == registry_hash


if __name__ == "__main__":
    run()
