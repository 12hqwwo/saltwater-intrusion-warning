"""Audit packaged research predictions against their actual as-of evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import rf_compact_artifacts as artifacts
from scripts.backtest_asof_ec import available_date_for, issue_date_for
from scripts.experiment_ec_extreme_robust import COMPACT
from scripts.experiment_ec_long_hydrology import data_matrix


class CompactArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = data_matrix(5)
        cls.sources = {
            delay: pd.read_csv(artifacts.ROOT / "outputs/ec_extreme_robust_20261029" /
                               f"predictions_{delay}d.csv")
            for delay in (5, 35)
        }

    def test_historical_rows_preserve_source_predictions_and_release_dates(self):
        for delay, source in self.sources.items():
            packed = artifacts.historical_predictions(source, self.matrix, delay)
            compact = packed[packed.candidate_id.eq("RF_compact")]
            self.assertFalse(compact.empty)
            for _, row in compact.iterrows():
                with self.subTest(delay=delay, target=row.target_month):
                    target = pd.Timestamp(row.target_month)
                    original = source[pd.to_datetime(source.target_month).eq(target)].iloc[0]
                    origin = pd.Timestamp(row.forecast_origin)
                    self.assertEqual(origin.date(), pd.Timestamp(original.issue_date).date())
                    self.assertEqual(row.predicted, original.RF_compact)
                    known = self.matrix[
                        self.matrix.month_start.map(lambda m: available_date_for(m, delay))
                        <= origin.date()]
                    self.assertEqual(row.n_train_samples, len(known))
                    self.assertEqual(pd.Timestamp(row.train_last_target_month), known.month_start.max())
                    self.assertLessEqual(pd.Timestamp(row.max_train_target_available_at), origin)
                    self.assertLessEqual(pd.Timestamp(row.max_feature_available_at), origin)
                    self.assertEqual(pd.Timestamp(row.actual_available_at).date(),
                                     available_date_for(target, delay))

    def test_changed_source_labels_and_training_counts_are_rejected(self):
        for column in ("actual", "train_n"):
            changed = self.sources[5].copy()
            changed.loc[:, column] += 1
            with self.subTest(column=column), self.assertRaises(ValueError):
                artifacts.historical_predictions(changed, self.matrix, 5)

    def test_metrics_are_computed_from_packaged_predictions(self):
        packed = artifacts.historical_predictions(self.sources[5], self.matrix, 5)
        metrics = artifacts.make_metrics(packed)
        self.assertTrue(metrics)
        for metric in metrics:
            rows = packed[packed.model.eq(metric["model"]) & packed.stage.eq(metric["stage"])]
            errors = rows.predicted.to_numpy() - rows.actual.to_numpy()
            self.assertEqual(metric["eval_samples"], len(rows))
            self.assertAlmostEqual(metric["mae_mS_m"], np.abs(errors).mean())
            self.assertAlmostEqual(metric["rmse_mS_m"], np.sqrt(np.mean(errors ** 2)))

    def test_one_high_ec_sample_has_equal_mae_and_rmse(self):
        packed = artifacts.historical_predictions(self.sources[5], self.matrix, 5)
        single = packed[packed.target_month.eq(packed.target_month.iloc[0])].copy()
        single.loc[:, "actual"] = 100.0
        single.loc[:, "predicted"] = 80.0
        metrics = artifacts.make_high_ec_metrics(single, 90.0)
        self.assertTrue(metrics)
        for row in metrics:
            self.assertEqual(row["eval_samples"], 1)
            self.assertAlmostEqual(row["mae_mS_m"], 20.0)
            self.assertAlmostEqual(row["rmse_mS_m"], 20.0)

    def test_next_forecast_calls_estimator_with_only_available_training_labels(self):
        for delay in (5, 35):
            with self.subTest(delay=delay), patch.object(artifacts, "fit_predict", return_value=47.125) as fit:
                result = artifacts.next_forecast(self.matrix, delay)
                fit.assert_called_once()
                kind, columns, weight, train, target = fit.call_args.args
                self.assertEqual((kind, columns, weight), ("rf", COMPACT, 1.0))
                row = result["selected_prediction"]
                self.assertEqual(row["predicted"], 47.125)
                target_month = pd.Timestamp(row["target_month"])
                issue = issue_date_for(target_month)
                self.assertEqual(target_month, pd.Timestamp("2024-01-01"))
                self.assertEqual(pd.Timestamp(row["forecast_origin"]).date(), issue)
                self.assertTrue(all(available_date_for(m, delay) <= issue for m in train.month_start))
                self.assertEqual(len(train), 462 if delay == 5 else 461)
                self.assertEqual(pd.Timestamp(row["train_last_target_month"]), train.month_start.max())
                self.assertAlmostEqual(float(target["rainfall_mm"]), 128.8)
                self.assertAlmostEqual(float(target["tc_stage_t2"]), 1.9425)
                self.assertAlmostEqual(float(target["kratie_q_t2"]), 10732.8832943)

    def test_generated_artifacts_record_real_hashes_and_frozen_primary_selection(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(artifacts, "data_matrix", return_value=self.matrix), \
                patch.object(artifacts, "fit_predict", return_value=47.125), \
                patch.object(artifacts, "plot_predictions", wraps=artifacts.plot_predictions) as plot:
            destination = Path(directory) / "sensitivity"
            manifest = artifacts.build_run(35, destination)
            saved = json.loads((destination / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, manifest)
            self.assertEqual(manifest["historical_prediction_status"],
                             "REPACKED_SOURCE_PREDICTIONS_NOT_RETRAINED")
            self.assertEqual(set(manifest["output_sha256"]), {
                "predictions.csv", "metrics.csv", "high_ec_metrics.csv",
                "split_manifest.csv", "selection.json", "next_forecast.json", "forecast_chart.png"})
            for name, expected in manifest["output_sha256"].items():
                self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), expected)
            for name, expected in manifest["source_sha256"].items():
                self.assertEqual(hashlib.sha256((artifacts.ROOT / name).read_bytes()).hexdigest(), expected)
            self.assertEqual(manifest["chart_source_predictions_sha256"],
                             manifest["output_sha256"]["predictions.csv"])
            self.assertTrue((destination / "forecast_chart.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            plot.assert_called_once()
            chart_rows = plot.call_args.args[0]
            saved_rows = pd.read_csv(destination / "predictions.csv")
            pd.testing.assert_frame_equal(chart_rows.reset_index(drop=True), saved_rows,
                                          check_dtype=False, check_exact=False)
            selection = manifest["selection"]
            primary = self.sources[5].query("split == 'validation_2019_2021'")
            sensitivity = self.sources[35].query("split == 'validation_2019_2021'")
            self.assertLess((sensitivity.RF_compact_weight3 - sensitivity.actual).abs().mean(),
                            (sensitivity.RF_compact - sensitivity.actual).abs().mean())
            self.assertEqual(selection["selected_model"], "RF_compact")
            self.assertEqual(selection["primary_availability_lag_days"], 5)
            self.assertEqual(selection["evaluation_availability_lag_days"], 35)
            self.assertAlmostEqual(selection["primary_validation_mae"],
                                   (primary.RF_compact - primary.actual).abs().mean())
            self.assertIn("primary +5-day", selection["selection_protocol"])


if __name__ == "__main__":
    unittest.main()
