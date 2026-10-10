"""Historical 2/6/12-hour station salinity forecasts using downloaded GFZ data.

Train <=2012, select on 2013, calibrate on 2014, fixed final evaluation 2015-16.
Exact timestamp joins; no interpolation across measurement gaps; no EC conversion.

Run from the repository root:
    python pipelines/models/run_sondoc_forecast.py --observation-delay-hours 2
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import run_forecast_multivariate as core

VERSION = "1.1.0"
HORIZONS = (2, 6, 12)
SPECS = [{"id": "PERSISTENCE"}, {"id": "RF_D6_L10", "depth": 6, "leaf": 10},
         {"id": "RF_D10_L20", "depth": 10, "leaf": 20}]
FEATURES = ["salinity_now", "salinity_lag2h", "salinity_lag4h", "salinity_lag6h", "trend_2h",
            "hour_sin", "hour_cos", "year_sin", "year_cos"]


def read_series(path):
    frame = pd.read_csv(path)
    if not frame.site_code.eq("GFZ_SONDOC").all() or not frame.unit.eq("g/L").all():
        raise ValueError("Unexpected station or unit.")
    if any(pd.Timestamp(value).tzinfo is None for value in frame.observed_at):
        raise ValueError("Observations require explicit timestamp offsets.")
    when = pd.to_datetime(frame.observed_at, utc=True).dt.tz_convert(core.TZ)
    values = pd.to_numeric(frame.salinity_g_per_l, errors="raise")
    if when.duplicated().any() or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid/duplicate observations; run the audited ingestion first.")
    return pd.Series(values.to_numpy(), index=pd.DatetimeIndex(when)).sort_index()


def supervised(series, horizon, observation_delay_hours=0):
    if horizon not in HORIZONS: raise ValueError("Unsupported horizon.")
    if type(observation_delay_hours) is not int or observation_delay_hours not in (0, 2, 6):
        raise ValueError("Use the declared 0, 2 or 6-hour publication-delay scenarios.")
    frame = pd.DataFrame(index=series.index)
    for lag, name in [(0, "salinity_now"), (2, "salinity_lag2h"), (4, "salinity_lag4h"), (6, "salinity_lag6h")]:
        frame[name] = series.reindex(frame.index - pd.Timedelta(hours=lag + observation_delay_hours)).to_numpy()
    frame["last_available_observation_at"] = frame.index - pd.Timedelta(hours=observation_delay_hours)
    frame["target_time"] = frame.index + pd.Timedelta(hours=horizon)
    frame["target_available_at"] = frame.target_time + pd.Timedelta(hours=observation_delay_hours)
    frame["actual"] = series.reindex(pd.DatetimeIndex(frame.target_time)).to_numpy()
    frame["trend_2h"] = frame.salinity_now - frame.salinity_lag2h
    frame["hour_sin"] = np.sin(2 * np.pi * frame.index.hour / 24)
    frame["hour_cos"] = np.cos(2 * np.pi * frame.index.hour / 24)
    frame["year_sin"] = np.sin(2 * np.pi * frame.index.dayofyear / 365.2425)
    frame["year_cos"] = np.cos(2 * np.pi * frame.index.dayofyear / 365.2425)
    # To score a continuous campaign window, require every intervening measurement.
    # These values never enter FEATURES. This conditions evaluation on sampled periods.
    continuous = np.ones(len(frame), dtype=bool)
    for hour in range(2, horizon + 1, 2):
        continuous &= series.reindex(frame.index + pd.Timedelta(hours=hour)).notna().to_numpy()
    return frame.loc[continuous].dropna(subset=FEATURES + ["actual"]).copy()


def fit_predict(train, predict, spec):
    if not len(train) or not len(predict): raise ValueError("Empty split.")
    if train.target_available_at.max() >= predict.index.min(): raise ValueError("Training labels not available before prediction stage.")
    if spec["id"] == "PERSISTENCE": return predict.salinity_now.to_numpy()
    model = RandomForestRegressor(n_estimators=150, max_depth=spec["depth"], min_samples_leaf=spec["leaf"],
                                  random_state=42, n_jobs=1)
    model.fit(train[FEATURES], train.actual)
    return np.maximum(0.0, model.predict(predict[FEATURES]))


def scoring(actual, predicted, lower=None, upper=None):
    errors = np.asarray(predicted) - np.asarray(actual)
    return dict(n=len(errors), mae=float(np.mean(abs(errors))), rmse=float(np.sqrt(np.mean(errors ** 2))),
                bias=float(np.mean(errors)), p95_absolute_error=float(np.quantile(abs(errors), .95)),
                interval_coverage=float(np.mean((actual >= lower) & (actual <= upper))) if lower is not None else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=core.ROOT / "data/external/sources/sondoc/sondoc_observations.csv",
    )
    parser.add_argument("--out", type=Path, default=core.ROOT / "runs/sondoc_forecast")
    parser.add_argument("--observation-delay-hours", type=int, choices=(0, 2, 6), default=0,
                        help="Scenario for measurement/laboratory reporting delay; source does not declare publication times.")
    args = parser.parse_args()
    series = read_series(args.data)
    output = core.new_run(args.out, "SONDOC")
    all_rows, reports = [], []
    for horizon in HORIZONS:
        frame = supervised(series, horizon, args.observation_delay_hours)
        # Both feature timestamps and target timestamps stay inside each temporal stage.
        train = frame.loc[frame.target_available_at.dt.year <= 2012]
        val = frame.loc[(frame.index.year == 2013) & (frame.target_available_at.dt.year == 2013)]
        cal = frame.loc[(frame.index.year == 2014) & (frame.target_available_at.dt.year == 2014)]
        test = frame.loc[(frame.index.year >= 2015) & (frame.target_time.dt.year <= 2016)]
        rankings = [{"spec": spec, **scoring(val.actual, fit_predict(train, val, spec))} for spec in SPECS]
        champion = min(rankings, key=lambda r: (r["mae"], r["spec"]["id"]))["spec"]
        selected_specs = [SPECS[0]] + ([champion] if champion["id"] != "PERSISTENCE" else [])
        for spec in selected_specs:
            calibration_predictions = fit_predict(pd.concat([train, val]), cal, spec)
            errors = np.sort(np.abs(calibration_predictions - cal.actual.to_numpy()))
            rank = int(np.ceil((len(errors) + 1) * .9))
            radius = float(errors[rank - 1]) if 0 < rank <= len(errors) else None
            fitted_train = pd.concat([train, val, cal])
            predicted = fit_predict(fitted_train, test, spec)
            low = np.maximum(0.0, predicted - radius) if radius is not None else None
            high = predicted + radius if radius is not None else None
            for i, (issued, row) in enumerate(test.iterrows()):
                all_rows.append(dict(site_code="GFZ_SONDOC", horizon_hours=horizon, model_id=spec["id"],
                    selected_on_validation=spec["id"] == champion["id"], forecast_origin=issued.isoformat(),
                    target_time=row.target_time.isoformat(), predicted=float(predicted[i]), actual=float(row.actual),
                    lower=float(low[i]) if low is not None else None, upper=float(high[i]) if high is not None else None,
                    salinity_at_issue=float(row.salinity_now), unit="g/L", source_quality="NOT_PROVIDED",
                    last_available_observation_at=row.last_available_observation_at.isoformat(),
                    observation_delay_hours=args.observation_delay_hours,
                    train_last_target=fitted_train.target_time.max().isoformat(),
                    train_last_label_available_at=fitted_train.target_available_at.max().isoformat(),
                    interval_kind="EMPIRICAL_RESIDUAL_BAND_SERIAL_DEPENDENCE_NOT_CERTIFIED",
                    gate_decision_eligible=False))
            stage_scores = [{"period": "2015-2016", **scoring(test.actual.to_numpy(), predicted, low, high)}]
            for year in (2015, 2016):
                mask = test.target_time.dt.year.to_numpy() == year
                stage_scores.append({"period": str(year), **scoring(test.actual.to_numpy()[mask], predicted[mask],
                    low[mask] if low is not None else None, high[mask] if high is not None else None)})
            reports.append(dict(horizon_hours=horizon, model_id=spec["id"], selected_on_validation=spec["id"] == champion["id"],
                counts={"train":len(train), "validation":len(val), "calibration":len(cal), "test":len(test)},
                validation_rankings=rankings, calibration_radius=radius, test_scores=stage_scores))
    pd.DataFrame(all_rows).to_csv(output / "predictions.csv", index=False)
    metrics = [dict(horizon_hours=r["horizon_hours"], model_id=r["model_id"], **s) for r in reports for s in r["test_scores"]]
    pd.DataFrame(metrics).to_csv(output / "metrics.csv", index=False)
    report = dict(schema_version=1, version=VERSION, mode="HISTORICAL_STATION_FORECAST",
        source_doi="10.5880/GFZ.4.4.2024.004", source_sha256=core.sha(args.data), script_sha256=core.sha(__file__),
        station="GFZ_SONDOC", unit="g/L", forecasts=reports, deployment_validated=False,
        source_quality="NOT_PROVIDED", timezone="ASSUMED_ASIA_HO_CHI_MINH",
        observation_delay_hours=args.observation_delay_hours,
        availability_assumption=f"Each campaign measurement becomes available after an assumed {args.observation_delay_hours}-hour delay; historical publication times unknown. This scenario is not a verified source latency.",
        limitations=["Test covers sampled dry-season campaigns only; gaps are not interpolated.",
          "Station forecast only; no validated transfer to a gate or another river branch.",
          "Empirical bands use correlated residuals and a refitted model; nominal 90% coverage is not guaranteed.",
          "Measurement depth protocol, timezone and conflicting Son Doc coordinates need provider confirmation.",
          "No observed gate-state/water-head/outcome dataset; cannot validate actions or counterfactual water outcomes."])
    core.save_json(output / "experiment.json", report)
    # A compact self-contained replay subset: all selected models for 2016, actuals clearly marked.
    replay = [r for r in all_rows if r["selected_on_validation"] and r["target_time"].startswith("2016-")]
    core.save_json(output / "replay.json", dict(metadata=report, records=replay))
    print(pd.DataFrame(metrics).to_string(index=False))
    print(output)


if __name__ == "__main__":
    main()
