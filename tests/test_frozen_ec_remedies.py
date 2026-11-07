"""As-of feature and integrity checks for research-only outage remedies."""
import hashlib
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from backend.domain import ec_gap_evaluation, ec_gap_remedies
from scripts.evaluate_frozen_ec_gap_remedies import (
    CANDIDATES, OUTPUT, forecast_candidates, neighbor_asof_features,
)


class MeanModel:
    def __init__(self, fits):
        self.fits = fits

    def fit(self, x, y):
        self.fits.append((x.copy(), y.copy()))
        self.value = float(y.mean())
        return self

    def predict(self, x):
        return np.repeat(self.value, len(x))


class RemedyChecks(unittest.TestCase):
    def test_neighbor_ec_follows_issue_cutoff_and_ignores_target_station(self):
        months = pd.to_datetime(["2022-01-01", "2022-02-01"])
        records = pd.DataFrame([
            dict(station=station, month_start=month, conductivity_mS_per_m=value)
            for station, base in (("MYTHUAN", 10), ("TANCHAU", 20), ("MYTHO", 1000))
            for month, value in (("2021-10-01", base), ("2021-11-01", base + 1),
                                 ("2021-12-01", base + 2), ("2022-01-01", base + 3))
        ])
        five = neighbor_asof_features(months, records, 5)
        slow = neighbor_asof_features(months, records, 35)
        self.assertEqual(five.mythuan_source_month.tolist(), ["2021-11-01", "2021-12-01"])
        self.assertEqual(slow.mythuan_source_month.tolist(), ["2021-10-01", "2021-11-01"])
        self.assertEqual(five.tanchau_ec_asof.tolist(), [21, 22])
        changed = records.copy()
        changed.loc[changed.station.eq("MYTHO"), "conductivity_mS_per_m"] = 1e9
        pd.testing.assert_frame_equal(five, neighbor_asof_features(months, changed, 5))

    def test_prediction_rejects_withheld_labels_and_fits_once_per_fixed_candidate(self):
        months = pd.date_range("2016-01-01", "2022-02-01", freq="MS")
        data = pd.DataFrame(dict(month_start=months,
            weather_month=months - pd.DateOffset(months=2),
            ec_delay_days=5, conductivity_mS_per_m=np.arange(len(months)) + 10.))
        for feature in set(sum(CANDIDATES.values(), [])):
            data[feature] = 2. if feature != "month_sin" else .5
        for station in ("mythuan", "tanchau"):
            data[station + "_source_month"] = (months - pd.DateOffset(months=2)).strftime("%Y-%m-01")
        known = data[data.month_start < "2022-01-01"]
        future = data[data.month_start >= "2022-01-01"].drop(columns="conductivity_mS_per_m")
        fits = []
        predicted = forecast_candidates(known, future, model_factory=lambda: MeanModel(fits))
        self.assertEqual(len(fits), len(CANDIDATES))
        self.assertEqual(len(predicted), 2)
        for features, labels in fits:
            self.assertTrue(set(features.columns).issubset(set(sum(CANDIDATES.values(), []))))
            self.assertTrue((labels < 1e9).all())
        with self.assertRaisesRegex(ValueError, "Withheld target"):
            forecast_candidates(known, data[data.month_start >= "2022-01-01"])
        future.loc[future.index[0], "mythuan_source_month"] = "2022-01-01"
        with self.assertRaisesRegex(ValueError, "unavailable"):
            forecast_candidates(known, future, model_factory=lambda: MeanModel([]))

    def test_published_metrics_match_checked_artifact(self):
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text("utf-8"))
        root = Path(__file__).resolve().parents[1]
        for relative, digest in manifest["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest)
        for name, digest in manifest["output_sha256"].items():
            self.assertEqual(hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest(), digest)
        study = ec_gap_remedies.summary("gap_2022_2023", 5)
        self.assertFalse(study["deployment_ready"])
        self.assertEqual(set(study["metrics"]), set(CANDIDATES))
        self.assertAlmostEqual(study["metrics"]["WeatherOnly"]["mae_mS_m"], 18.385278, places=5)
        self.assertLess(study["metrics"]["WeatherHydrology"]["rmse_mS_m"],
                        study["metrics"]["WeatherOnly"]["rmse_mS_m"])
        self.assertEqual(ec_gap_evaluation.records("MYTHO", "gap_2022_2023", 5)["remedy_research"], study)
        self.assertIsNone(ec_gap_evaluation.records("TANCHAU", "gap_2022_2023", 5)["remedy_research"])
        with self.assertRaises(ValueError):
            ec_gap_remedies.summary("unknown", 5)


if __name__ == "__main__":
    unittest.main()
