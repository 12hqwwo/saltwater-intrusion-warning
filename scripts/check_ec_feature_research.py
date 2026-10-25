"""Audit temporal alignment, source immutability and research cohort integrity."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research_ec_features import ALL_FEATURES, EXTERNAL, OUT, ROOT, daily_features, digest, month_end, save_json


def main():
    data = pd.read_csv(OUT / "feature_matrix.csv", parse_dates=["target_month"])
    checks = {}
    assert len(data) == 2000 and not data.duplicated(["station", "target_month", "ec_delay_days"]).any()
    checks["unique_station_month_scenario"] = True
    assert not any(c.startswith("ec_target") for c in ALL_FEATURES)
    origin = pd.to_datetime(data.issue_time, utc=True)
    ec_available = pd.to_datetime(data.ec_latest_available_at, utc=True)
    assert ((ec_available <= origin) | ec_available.isna()).all()
    weather_available = pd.to_datetime(data.weather_assumed_available_at, utc=True)
    assert (weather_available <= origin).all()
    for lag in [2, 3, 6]:
        source = data.target_month - pd.DateOffset(months=lag)
        available = pd.to_datetime([month_end(t) + pd.Timedelta(days=30) for t in source])
        assert ((available < data.target_month) | data[f"nino34_lag{lag}_c"].isna()).all()
    checks["no_future_ec_weather_or_enso_by_declared_delay"] = True
    # Perturb future inputs: an earlier forecast row must remain identical.
    weather = pd.read_csv(ROOT / "data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv", parse_dates=["date"])
    weather = weather[weather.station.eq("MyTho")].copy()
    extra = json.loads((EXTERNAL / "era5_extra_MyTho.json").read_text(encoding="utf-8"))
    date = pd.DatetimeIndex(["2019-05-01"])
    before = daily_features(weather, extra, date)
    weather.loc[weather.date >= "2019-05-01", "precipitation_sum"] = 999999
    after = daily_features(weather, extra, date)
    pd.testing.assert_frame_equal(before, after)
    checks["future_weather_perturbation_does_not_change_past_feature"] = True
    manifest = json.loads((OUT / "data_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["inputs"]:
        assert digest(ROOT / entry["path"]) == entry["sha256"], entry["path"]
    checks["input_hashes_unchanged"] = True
    for filename, years in [("validation_predictions.csv", range(2014, 2020)), ("holdout_predictions.csv", range(2020, 2024))]:
        path = OUT / filename
        if not path.exists(): continue
        p = pd.read_csv(path, parse_dates=["target_month", "train_last_month"])
        assert p.target_month.dt.year.isin(years).all()
        assert (p.train_last_month < pd.to_datetime(p.year.astype(str) + "-01-01")).all()
        train_available = pd.to_datetime([month_end(t) + pd.Timedelta(days=int(d))
            for t, d in zip(p.train_last_month, p.ec_delay_days)])
        assert (train_available < pd.to_datetime(p.year.astype(str) + "-01-01")).all()
        assert not p.duplicated(["station", "ec_delay_days", "target_month", "algorithm", "configuration"]).any()
        for _, group in p.groupby(["station", "ec_delay_days"]):
            cohorts = [tuple(g.target_month.sort_values()) for _, g in group.groupby(["algorithm", "configuration"])]
            assert len(set(cohorts)) == 1
        assert np.isfinite(p[["actual", "prediction"]].to_numpy()).all()
        checks[filename] = dict(rows=len(p), common_cohorts=True, training_precedes_evaluation=True)
    save_json(OUT / "verification.json", checks)
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
