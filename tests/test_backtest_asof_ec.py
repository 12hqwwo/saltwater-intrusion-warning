import unittest
from datetime import date

from scripts.backtest_asof_ec import available_date_for, issue_date_for, split_for


class AsOfBacktestDates(unittest.TestCase):
    def test_first_validation_forecast_excludes_december_label(self):
        issue = issue_date_for(date(2019, 1, 1))
        self.assertEqual(issue, date(2018, 12, 6))
        self.assertEqual(available_date_for(date(2018, 11, 1), 5), date(2018, 12, 5))
        self.assertGreater(available_date_for(date(2018, 12, 1), 5), issue)
        self.assertGreater(available_date_for(date(2018, 11, 1), 35), issue)

    def test_year_boundary_and_splits(self):
        self.assertEqual(issue_date_for(date(2022, 1, 1)), date(2021, 12, 6))
        self.assertEqual(split_for(date(2022, 1, 1)), "historical_2022_2023")
        self.assertIsNone(split_for(date(2024, 1, 1)))


if __name__ == "__main__":
    unittest.main()
