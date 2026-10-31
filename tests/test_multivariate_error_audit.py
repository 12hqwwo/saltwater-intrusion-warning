import math
import unittest

from scripts.audit_multivariate_errors import metrics, month_shift, percentile_nearest_rank, season_for_month
from datetime import date


class MultivariateErrorAuditTests(unittest.TestCase):
    def test_nearest_rank_threshold_uses_only_supplied_training_values(self):
        self.assertEqual(percentile_nearest_rank(list(range(1, 11)), 0.9), 9)
        self.assertEqual(percentile_nearest_rank([2, 2, 8, 8], 0.9), 8)

    def test_error_metrics_keep_bias_sign(self):
        rows = [{"actual": "10", "RandomForest": "8"}, {"actual": "20", "RandomForest": "14"}]
        result = metrics(rows, "RandomForest")
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["mae_mS_m"], 4)
        self.assertEqual(result["bias_mS_m"], -4)
        self.assertTrue(math.isclose(result["rmse_mS_m"], math.sqrt(20)))

    def test_two_month_weather_lag_across_year(self):
        self.assertEqual(month_shift(date(2022, 1, 1), -2), date(2021, 11, 1))

    def test_dry_season_ends_in_april(self):
        self.assertEqual(season_for_month(12), "dry")
        self.assertEqual(season_for_month(4), "dry")
        self.assertEqual(season_for_month(5), "non_dry")


if __name__ == "__main__":
    unittest.main()
