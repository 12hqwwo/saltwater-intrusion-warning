"""Availability checks for lagged station EC in the upstream experiment."""

import unittest

import pandas as pd

from scripts.experiment_ec_upstream_asof import ec_features
from scripts.backtest_asof_ec import issue_date_for


class AvailabilityTest(unittest.TestCase):
    def test_december_measurement_is_not_known_for_january_forecast(self):
        series = pd.Series([10.0, 20.0, 30.0], index=pd.to_datetime(
            ["2018-10-01", "2018-11-01", "2018-12-01"]))
        target = pd.Timestamp("2019-01-01")
        issue = issue_date_for(target)

        quick = ec_features(series, target, issue, 5, "tc")
        slow = ec_features(series, target, issue, 35, "tc")

        self.assertEqual(quick["tc_latest"], 20.0)
        self.assertEqual(quick["tc_source_month"], pd.Timestamp("2018-11-01"))
        self.assertEqual(slow["tc_latest"], 10.0)
        self.assertEqual(slow["tc_source_month"], pd.Timestamp("2018-10-01"))
        self.assertLessEqual(quick["tc_available_at"], issue)
        self.assertLessEqual(slow["tc_available_at"], issue)


if __name__ == "__main__":
    unittest.main()
