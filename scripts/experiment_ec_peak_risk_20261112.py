"""Research: season-memory discharge features and EC exceedance probability.

Frozen-EC protocol as in ``evaluate_frozen_ec_gap_remedies`` (My Tho EC after
the first issue is used only for scoring).  Hypotheses from Apel et al. 2020
(NHESS 20:1609).

Availability rules (all ASSUMED; no source publishes historical vintages)
* Each source has its own lag scenario: EC {5, 35} days, weather {5, 35},
  Kratie discharge + Tan Chau stage {5, 35, 90} days after month end.
* For every target month (training and test rows alike) the issue date is
  day 6 of target-1.  Each source uses its *latest month whose month end + lag
  <= issue*; with lag 5 this is t-2, with lag 35 t-3, with lag 90 t-5.  All
  rolling means, same-month medians and season windows end at that month, so a
  feature never uses a month that is unavailable under the scenario.
* ONI (NOAA PSL) labels a 3-month mean by its centre month.  ``oni_t4`` (centre
  target-4) needs SST through target-3.  PSL/CPC values are revised and no
  vintage exists, so ONI is reported as an unverified-vintage input and also
  ablated (``...NoONI``).

Writes only to ``outputs/ec_peak_risk_20261112/``.  Changes no registry/model.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain.multivariate_ec import FEATURES  # noqa: E402
from backend.repositories.multivariate_inputs import (  # noqa: E402
    CANONICAL, EXTERNAL, get_monthly_weather)
from tools.backtest_protocols import available_date_for, issue_date_for  # noqa: E402
from scripts.evaluate_frozen_ec_gap import EXPERIMENTS, freeze_training  # noqa: E402
from scripts.evaluate_mythuan_three_station import score  # noqa: E402
from tools.feature_building import (  # noqa: E402
    EXTRA, HISTORY, KRATIE, LONG, RECENT, RECENT_TC, data_matrix,
    monthly_kratie_flow, monthly_stage)
from tools.model_training import pipeline  # noqa: E402

OUTPUT = ROOT / "outputs/ec_peak_risk_20261112"
ONI = ROOT / "data/external/climate_indices_20261029/oni_monthly.csv"
PROTOCOL = "FROZEN_EC_PEAK_RISK_RESEARCH_V2"
WEATHER = ["rainfall_mm", "temperature_degC", "wind_source_units"]
HYDRO = ["kratie_q_t2", "kratie_q3_t2", "kratie_q_ratio_t2", "tc_stage_t2", "tc_stage3_t2"]
SEASON_Q = ["kratie_dry_deficit_t2", "kratie_wet_ratio_last"]
SEASON = SEASON_Q + ["oni_t4"]
REGRESSORS = {"WeatherHydrology": FEATURES + HYDRO,
              "WeatherHydrologySeason": FEATURES + HYDRO + SEASON,
              "WeatherHydrologySeasonNoONI": FEATURES + HYDRO + SEASON_Q}
CLASS_FEATURES = {"LogitSeason": ["month_sin", "month_cos"] + SEASON,
                  "RFClassSeason": FEATURES + HYDRO + SEASON}
EC_LAGS, WEATHER_LAGS, HYDRO_LAGS = (5, 35), (5, 35), (5, 35, 90)
THRESHOLD = 150.0  # WATCH reference level (data-contracts.md), not a gate rule.
DIAG = 100.0
CODE = ["scripts/experiment_ec_peak_risk_20261112.py", "tools/feature_building.py",
        "scripts/experiment_ec_upstream_asof.py", "tools/backtest_protocols.py",
        "scripts/evaluate_frozen_ec_gap.py", "scripts/evaluate_mythuan_three_station.py",
        "tools/model_training.py", "backend/repositories/multivariate_inputs.py",
        "backend/domain/multivariate_ec.py"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def anchor_month(target, lag):
    """Latest source month published (month end + lag) on or before the issue date."""
    issue = issue_date_for(target)
    month = pd.Timestamp(target) - pd.DateOffset(months=2)
    while available_date_for(month, lag) > issue:
        month -= pd.DateOffset(months=1)
    return month


def kratie_monthly():
    path = next(KRATIE.glob("014901_Discharge_Calculated daily discharge_*.csv"))
    frame = pd.read_csv(path, usecols=["observed_at", "value", "unit"])
    if frame.unit.ne("m^3/s").any() or (frame.value < 0).any():
        raise ValueError("Bad Kratie source")
    frame["day"] = pd.to_datetime(frame.observed_at).dt.date
    daily = frame.groupby("day").value.mean()
    month = pd.to_datetime(daily.index).to_period("M").to_timestamp()
    stats = daily.groupby(month).agg(["mean", "count"])
    index = pd.date_range("1985-01-01", "2026-10-01", freq="MS")
    return stats["mean"].where(stats["count"] >= 20).reindex(index)


def season_features(q):
    """Indexed by anchor month; uses months <= anchor and earlier-year medians only."""
    prior_median = pd.Series(index=q.index, dtype=float)
    for m in range(1, 13):
        part = q[q.index.month == m]
        prior_median.loc[part.index] = part.shift(1).rolling(15, min_periods=5).median().values
    log_ratio = np.log((q / prior_median).clip(0.05, 20))
    deficit = pd.Series(index=q.index, dtype=float)
    for w in q.index:
        if w.month in (11, 12, 1, 2, 3, 4, 5, 6):
            start = pd.Timestamp(w.year - (w.month < 11), 11, 1)
            window = log_ratio[start:w]
            deficit[w] = window.mean() if window.notna().any() else np.nan
    wet = {}
    for year in range(q.index.year.min(), q.index.year.max() + 1):
        part = q[pd.Timestamp(year, 7, 1):pd.Timestamp(year, 10, 1)]
        wet[year] = part.mean() if part.notna().sum() >= 3 else np.nan
    wet = pd.Series(wet)
    wet_ratio = wet / wet.shift(1).rolling(15, min_periods=5).median()
    # A Jul-Oct season counts only once its October is the anchor or earlier.
    wet_last = [wet_ratio.get(w.year if w.month >= 10 else w.year - 1, np.nan) for w in q.index]
    return pd.DataFrame({"kratie_dry_deficit_t2": deficit.values,
                         "kratie_wet_ratio_last": wet_last}, index=q.index)


def hydro_table():
    flow = monthly_kratie_flow().set_index("weather_month")
    stage = monthly_stage("019803", "tc").set_index("weather_month")
    table = flow.join(stage, how="outer").join(season_features(kratie_monthly()), how="left")
    return table[HYDRO + SEASON_Q]


def weather_table():
    rows = pd.DataFrame(get_monthly_weather("MYTHO", require_verified_wind=True))
    rows = rows[rows.complete.astype(bool)]
    rows["month"] = pd.to_datetime(rows.input_month)
    return rows.set_index("month")[WEATHER]


def oni_table():
    oni = pd.read_csv(ONI, parse_dates=["month_start"]).set_index("month_start").oni
    return oni


def scenario_frame(base, ec_lag, weather_lag, hydro_lag, hydro, weather, oni):
    frame = base.drop(columns=WEATHER + HYDRO).copy()
    frame["weather_anchor"] = [anchor_month(t, weather_lag) for t in frame.month_start]
    frame["hydro_anchor"] = [anchor_month(t, hydro_lag) for t in frame.month_start]
    frame = frame.join(weather, on="weather_anchor").join(hydro, on="hydro_anchor")
    frame["oni_t4"] = (frame.month_start - pd.DateOffset(months=4)).map(oni)
    # freeze_training checks weather availability through ``weather_month``.
    frame["weather_month"] = frame["weather_anchor"]
    frame["ec_lag"], frame["weather_lag"], frame["hydro_lag"] = ec_lag, weather_lag, hydro_lag
    return frame


def classifiers():
    return {
        "LogitSeason": lambda: make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                             LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000)),
        "RFClassSeason": lambda: make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(
            n_estimators=300, max_depth=4, min_samples_leaf=3, class_weight="balanced_subsample",
            random_state=42, n_jobs=1)),
    }


def run(output=OUTPUT):
    hydro, weather, oni = hydro_table(), weather_table(), oni_table()
    rows = []
    for ec_lag in EC_LAGS:
        base = data_matrix(ec_lag)
        for weather_lag, hydro_lag in itertools.product(WEATHER_LAGS, HYDRO_LAGS):
            frame = scenario_frame(base, ec_lag, weather_lag, hydro_lag, hydro, weather, oni)
            if weather_lag == 5 and hydro_lag == 5:
                # The anchored tables must reproduce the published t-2 matrix exactly.
                for column in WEATHER + HYDRO:
                    a, b = frame[column].to_numpy(float), base[column].to_numpy(float)
                    if not np.allclose(a, b, equal_nan=True):
                        raise ValueError(f"Anchored {column} differs from published matrix")
            for experiment, (start, end) in EXPERIMENTS.items():
                known = freeze_training(frame, start, ec_lag)
                future = frame[frame.month_start.between(start, end)].copy()
                if len(future) != len(pd.date_range(start, end, freq="MS")):
                    raise ValueError("Incomplete cohort")
                if known.month_start.max() >= future.month_start.min():
                    raise ValueError("Overlap")
                for row in future.itertuples():
                    issue = issue_date_for(row.month_start)
                    if (available_date_for(row.weather_anchor, weather_lag) > issue or
                            available_date_for(row.hydro_anchor, hydro_lag) > issue):
                        raise ValueError("Input unavailable at issue")
                y = known.conductivity_mS_per_m.to_numpy()
                out = future[["month_start", "weather_anchor", "hydro_anchor"] + SEASON].copy()
                out["missing_test_inputs"] = future[FEATURES + HYDRO + SEASON_Q].isna().sum(axis=1).to_numpy()
                for name, cols in REGRESSORS.items():
                    model = pipeline().set_params(randomforestregressor__n_jobs=1).fit(known[cols], y)
                    out[name] = model.predict(future[cols])
                label = (y >= THRESHOLD).astype(int)
                for name, factory in classifiers().items():
                    model = factory().fit(known[CLASS_FEATURES[name]], label)
                    out["p150_" + name] = model.predict_proba(future[CLASS_FEATURES[name]])[:, 1]
                out["p150_climatology"] = [
                    float((known.loc[known.month_start.dt.month == m, "conductivity_mS_per_m"] >= THRESHOLD).mean())
                    for m in future.month_start.dt.month]
                out["actual_mS_m"] = future.conductivity_mS_per_m.to_numpy()
                out["experiment"] = experiment
                out["ec_lag"], out["weather_lag"], out["hydro_lag"] = ec_lag, weather_lag, hydro_lag
                out["frozen_ec_through"] = known.month_start.max().date().isoformat()
                out["n_train"], out["n_train_pos150"] = len(known), int(label.sum())
                rows.append(out)
                print(experiment, ec_lag, weather_lag, hydro_lag, flush=True)
    pred = pd.concat(rows, ignore_index=True).rename(columns={"month_start": "target_month"})
    keys = ["experiment", "ec_lag", "weather_lag", "hydro_lag"]
    metrics = []
    for key, g in pred.groupby(keys):
        meta = dict(zip(keys, key))
        actual = g.actual_mS_m.to_numpy()
        for cohort, mask in {"all": np.ones(len(g), bool),
                             "dry_Dec_Apr": g.target_month.dt.month.isin([12, 1, 2, 3, 4]).to_numpy(),
                             "high_EC_100": actual >= DIAG}.items():
            if not mask.any():
                continue
            a = actual[mask]
            for name in REGRESSORS:
                p = g[name].to_numpy()[mask]
                metrics.append(dict(**meta, cohort=cohort, model=name, **score(a, p),
                                    missed_high_100=int(((p < DIAG) & (a >= DIAG)).sum()),
                                    false_alerts_100=int(((p >= DIAG) & (a < DIAG)).sum())))
            event = (a >= THRESHOLD).astype(int)
            for name in ["p150_LogitSeason", "p150_RFClassSeason", "p150_climatology"]:
                p = g[name].to_numpy()[mask]
                metrics.append(dict(**meta, cohort=cohort, model=name, n=int(mask.sum()),
                                    events_150=int(event.sum()),
                                    brier=float(brier_score_loss(event, p, labels=[0, 1])),
                                    hits_p05=int(((p >= 0.5) & (event == 1)).sum()),
                                    false_alarms_p05=int(((p >= 0.5) & (event == 0)).sum())))
    metrics = pd.DataFrame(metrics)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    pred.to_csv(output / "predictions.csv", index=False)
    metrics.to_csv(output / "metrics.csv", index=False)
    data = [ROOT / "data/research/mrc_ec_monthly_samples.csv", ONI, CANONICAL,
            EXTERNAL / "manifest.json", *sorted(EXTERNAL.glob("era5_*.json")),
            EXTRA / "era5_extra_MyTho.json", EXTRA / "era5_extra_TanChau.json",
            next(KRATIE.glob("014901_Discharge_Calculated daily discharge_*.csv"))]
    data += [next(folder.glob("019803_Water_Level_Manual_*.csv")) for folder in (LONG, RECENT_TC)]
    data += [next(folder.glob(f"{code}_Water_Level_Manual_*.csv"))
             for code in ("019804", "985203", "980601") for folder in (LONG, HISTORY, RECENT)]
    sources = [p for p in data if p.exists()] + [ROOT / p for p in CODE]
    manifest = dict(
        schema_version=2, protocol_id=PROTOCOL, station="MYTHO", experiments=EXPERIMENTS,
        lag_scenarios_days=dict(ec=list(EC_LAGS), weather=list(WEATHER_LAGS), hydrology=list(HYDRO_LAGS)),
        issue_rule="Day 6 of target-1 (local calendar).",
        anchor_rule="Each source uses its latest month with month_end + lag <= issue; lag 5 -> t-2, 35 -> t-3, 90 -> t-5. Rolling/season features end at that month; same-month medians use earlier years only.",
        oni_rule="ONI centred on target-4 (needs SST through target-3). No vintage; revisions unknown. Ablated by ...NoONI.",
        unit="mS/m", event_threshold_mS_m=THRESHOLD, regressors=REGRESSORS,
        classifier_features=CLASS_FEATURES,
        limitations=["All lags are assumptions; no historical publication timestamps exist for EC, Kratie, Tan Chau or ONI.",
                     "Source files were downloaded in 2026 and may contain later revisions (e.g. Kratie rating curves).",
                     "All three windows were inspected before; not a blind test.",
                     "150 mS/m is a visual reference level, not an irrigation or gate rule.",
                     "No deployed model, registry or WebGIS output is changed."],
        sklearn_version=sklearn.__version__, pandas_version=pd.__version__, numpy_version=np.__version__,
        source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
        output_sha256={n: sha(output / n) for n in ("predictions.csv", "metrics.csv")})
    (output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    return pred, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.output)
