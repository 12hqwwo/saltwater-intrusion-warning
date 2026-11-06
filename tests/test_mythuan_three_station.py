"""Regression checks for the offline three-station comparison and leakage rules."""
import unittest
import hashlib
import json
from datetime import date

import numpy as np
import pandas as pd

from scripts.evaluate_mythuan_three_station import (
    OUTPUT, ROOT, endpoint_interpolation, geometry, interpolation_benchmark,
    known_training_rows, load_targets, score,
)


class AvailabilityChecks(unittest.TestCase):
    def test_january_forecast_respects_both_release_delays(self):
        data = pd.DataFrame({
            "month_start": pd.to_datetime(["2021-09-01", "2021-10-01", "2021-11-01", "2021-12-01", "2022-01-01"]),
            "weather_available_at": [date(2021, 8, 5), date(2021, 9, 5), date(2021, 10, 5), date(2021, 11, 5), date(2021, 12, 5)],
        })
        short = known_training_rows(data, pd.Timestamp("2022-01-01"), 5)
        long = known_training_rows(data, pd.Timestamp("2022-01-01"), 35)
        self.assertEqual(short.month_start.max(), pd.Timestamp("2021-11-01"))
        self.assertEqual(long.month_start.max(), pd.Timestamp("2021-10-01"))

    def test_unavailable_weather_is_excluded_even_when_label_is_old(self):
        data = pd.DataFrame({"month_start": pd.to_datetime(["2021-09-01"]),
                             "weather_available_at": [date(2022, 1, 1)]})
        self.assertTrue(known_training_rows(data, pd.Timestamp("2022-01-01"), 5).empty)


class SpatialComparisonChecks(unittest.TestCase):
    def test_linear_uses_along_river_fraction_and_idw_is_distinct(self):
        self.assertAlmostEqual(endpoint_interpolation(10, 110, 0.75), 85)
        self.assertAlmostEqual(endpoint_interpolation(10, 110, 0.75, 2), 100)
        self.assertEqual(endpoint_interpolation(10, 110, 0), 10)
        self.assertEqual(endpoint_interpolation(10, 110, 1), 110)

    def test_invalid_values_are_not_silently_imputed(self):
        for args in [(10, 20, -0.1), (10, 20, 1.1), (-1, 20, 0.5), (10, np.nan, 0.5)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                endpoint_interpolation(*args)

    def test_third_anchor_uses_out_of_sample_forecast_not_actual(self):
        data = pd.DataFrame([
            dict(station=station, ec_delay_days=5, split="historical_2022_2023", target_month="2022-01-01",
                 actual_mS_m=actual, RandomForest=forecast, sample_date=sample_date)
            for station, actual, forecast, sample_date in [
                ("TANCHAU", 10, 12, "2022-01-15"),
                ("MYTHUAN", 20, 25, "2022-01-16"),
                ("MYTHO", 110, 100, "2022-01-15"),
            ]
        ])
        row = interpolation_benchmark(data, 0.75).iloc[0]
        self.assertEqual(row.THREE_FORECAST_ANCHOR, 25)
        self.assertEqual(row.actual_mS_m, 20)
        self.assertEqual(row.TWO_OBSERVED_LINEAR, 85)
        self.assertEqual(row.TWO_FORECAST_LINEAR, 78)
        self.assertFalse(row.all_three_same_sample_date)
        with self.assertRaises(ValueError):
            interpolation_benchmark(data.iloc[:2], 0.75)

    def test_metric_formula_and_missing_cohort_rejection(self):
        result = score([10, 20], [13, 16])
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["mae_mS_m"], 3.5)
        self.assertAlmostEqual(result["rmse_mS_m"], np.sqrt(12.5))
        for actual, predicted in [([], []), ([1], [np.nan]), ([1, 2], [1])]:
            with self.assertRaises(ValueError):
                score(actual, predicted)


class RepositoryEvidenceChecks(unittest.TestCase):
    def test_original_targets_and_matched_evaluation_coverage(self):
        targets = load_targets()
        mid = targets[targets.station.eq("MYTHUAN")]
        self.assertEqual(len(mid), 451)
        self.assertEqual(mid.sample_date.max(), "2023-12-15")
        self.assertTrue(mid.quality_flag.eq("UNVERIFIED").all())
        for station, group in targets.groupby("station"):
            with self.subTest(station=station):
                selected = group[group.month_start.between("2022-01-01", "2023-12-01")]
                self.assertEqual(len(selected), 24)
                self.assertFalse(selected.month_start.duplicated().any())

    def test_geographic_projection_is_inside_existing_endpoints(self):
        axis = geometry()
        self.assertEqual(axis["coordinate"], [105.9263229, 10.27532005])
        self.assertGreater(axis["along_river_fraction"], 0)
        self.assertLess(axis["along_river_fraction"], 1)
        self.assertAlmostEqual(axis["chainage_km"] / 125, axis["along_river_fraction"])


class GeneratedEvidenceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (OUTPUT / "run_manifest.json").exists():
            raise unittest.SkipTest("Run offline evaluation first to check its generated artifacts")
        cls.manifest = json.loads((OUTPUT / "run_manifest.json").read_text("utf-8"))
        cls.predictions = pd.read_csv(OUTPUT / "predictions.csv")

    def test_source_and_output_hashes_are_reproducible(self):
        for relative, expected in self.manifest["input_sha256"].items():
            with self.subTest(source=relative):
                current = ROOT / relative
                if hashlib.sha256(current.read_bytes()).hexdigest() != expected:
                    current = OUTPUT / 'source_snapshots' / relative
                self.assertEqual(hashlib.sha256(current.read_bytes()).hexdigest(), expected)
        for filename, expected in self.manifest["output_sha256"].items():
            with self.subTest(output=filename):
                self.assertEqual(hashlib.sha256((OUTPUT / filename).read_bytes()).hexdigest(), expected)

    def test_all_forecasts_use_only_issue_time_information(self):
        data = self.predictions
        self.assertEqual(len(data), 360)
        self.assertFalse(data.duplicated(["station", "ec_delay_days", "target_month"]).any())
        self.assertTrue((pd.to_datetime(data.last_training_ec_available_at) <= pd.to_datetime(data.issue_date_local)).all())
        self.assertTrue((pd.to_datetime(data.weather_available_at) <= pd.to_datetime(data.issue_date_local)).all())
        self.assertTrue((pd.to_datetime(data.last_training_ec_month) < pd.to_datetime(data.target_month)).all())
        for _, group in data[data.split.eq("historical_2022_2023")].groupby(["station", "ec_delay_days"]):
            self.assertEqual(len(group), 24)
            self.assertEqual(group.target_month.min(), "2022-01-01")
            self.assertEqual(group.target_month.max(), "2023-12-01")

    def test_saved_spatial_benchmark_uses_only_forecast_at_third_anchor(self):
        spatial = pd.read_csv(OUTPUT / "interpolation_predictions.csv")
        mid = self.predictions[self.predictions.station.eq("MYTHUAN")]
        paired = spatial.merge(mid, on=["ec_delay_days", "split", "target_month"], validate="one_to_one")
        self.assertEqual(len(paired), 120)
        np.testing.assert_allclose(paired.THREE_FORECAST_ANCHOR, paired.RandomForest, rtol=0, atol=1e-12)
        self.assertFalse(np.allclose(paired.THREE_FORECAST_ANCHOR, paired.actual_mS_m_x))
        ratio = self.manifest["geometry"]["along_river_fraction"]
        np.testing.assert_allclose(paired.TWO_OBSERVED_LINEAR,
            (1 - ratio) * paired.tan_chau_actual + ratio * paired.my_tho_actual, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
