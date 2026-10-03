"""Regression checks for silent data and station identity mismatches."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit_local_data as audit


class AuditTests(unittest.TestCase):
    def test_same_row_count_does_not_hide_changed_ec(self):
        raw = {"MYTHO": [{"observed_at": "2023-12-15T00:00:00+07:00", "conductivity_ms_per_m": 15.4}]}
        master = [{"area_code": "MYTHO", "month_start": "2023-12-01", "conductivity_ms_per_m": 15.5}]
        self.assertEqual(len(audit.compare_monthly_ec(raw, master)), 1)

    def test_missing_month_is_not_a_valid_match(self):
        raw = {"MYTHO": [{"observed_at": "2023-12-15T00:00:00+07:00", "conductivity_ms_per_m": 15.4}]}
        self.assertEqual(len(audit.compare_monthly_ec(raw, [])), 1)

    def test_extra_calendar_month_with_no_ec_is_allowed(self):
        raw = {"MYTHO": [{"observed_at": "2023-12-15T00:00:00+07:00", "conductivity_ms_per_m": 15.4}]}
        master = [{"area_code": "MYTHO", "month_start": "2023-12-01", "conductivity_ms_per_m": 15.4},
                  {"area_code": "MYTHO", "month_start": "2024-01-01", "conductivity_ms_per_m": None}]
        self.assertEqual(audit.compare_monthly_ec(raw, master), [])

    def test_wrong_station_or_nonfinite_coordinates_are_rejected(self):
        source = audit.ROOT / "data/raw/spatial/Conductivity.Water Quality@VN_019805_[My Tho]__station-location.kml"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "station.kml"
            for changed in [source.read_text().replace("VN_019805", "VN_019803"),
                            source.read_text().replace("106.3529997", "nan")]:
                with self.subTest(kml=changed):
                    candidate.write_text(changed, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        audit.station_feature(candidate, "019805")


if __name__ == "__main__":
    unittest.main()
