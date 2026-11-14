"""Migration 32 is additive and its reverse refuses to discard MyThuan records."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PredictionStationMigrationTests(unittest.TestCase):
    def test_forward_extends_both_station_checks(self):
        sql = (ROOT / 'sql/32_dss_prediction_stations.sql').read_text(encoding='utf-8')
        self.assertIn("'MyThuan'", sql)
        self.assertIn("'MRC_VN_019804'", sql)
        self.assertIn('multivariate_prediction_log_station_key_check', sql)
        self.assertIn('multivariate_prediction_log_check1', sql)
        self.assertIn('current_database()', sql)
        self.assertNotIn('DROP TABLE', sql.upper())

    def test_reverse_checks_for_saved_mythuan_rows(self):
        sql = (ROOT / 'sql/32_dss_prediction_stations_down.sql').read_text(encoding='utf-8')
        self.assertIn("WHERE station_key = 'MyThuan'", sql)
        self.assertIn('Cannot roll back station constraints', sql)
        self.assertIn('current_database()', sql)
        self.assertNotIn('DELETE FROM DSS_REFERENCE.MULTIVARIATE_PREDICTION_LOG', sql.upper())


if __name__ == '__main__':
    unittest.main()
