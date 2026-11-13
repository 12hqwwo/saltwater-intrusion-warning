import unittest
from datetime import datetime, timedelta
from datetime import date
from unittest.mock import patch
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from backend.domain.field_measurement import normalize
from backend.main import app
from backend.services import field_measurements as service
from backend.repositories.field_measurements import field_label_from_rows

NOW = datetime(2026, 11, 14, 10, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
RAW = dict(ec=1500, unit='µS/cm', observed_at='2026-11-14T09:00:00+07:00',
           longitude=105.8, latitude=10.5, position_kind='RIVER', device='EC-meter 01',
           submitted_by='Cán bộ A', ec_basis='EC25', calibrated_at='2026-11-01')


class FieldMeasurementTests(unittest.TestCase):
    def test_microsiemens_converted(self):
        self.assertAlmostEqual(normalize(RAW, NOW)['ec_mS_m'], 150.0)

    def test_all_units(self):
        for unit, value in [('mS/m', 100), ('dS/m', 1), ('mS/cm', 1), ('µS/cm', 1000)]:
            self.assertAlmostEqual(normalize(RAW | dict(unit=unit, ec=value), NOW)['ec_mS_m'], 100)

    def test_high_value_flagged_not_rejected(self):
        self.assertIn('REVIEW_HIGH', normalize(RAW | dict(ec=1500, unit='mS/m'), NOW, 20)['flags'])

    def test_submit_flags_against_nearest_station_month_median(self):
        normalized = normalize(RAW, NOW)
        with patch.object(service, 'normalize', return_value=normalized), \
             patch.object(service.repo, 'historical_month_median', return_value=20) as median, \
             patch.object(service.repo, 'insert_measurement', return_value={
                 'measurement_id': 'field-1', 'submitted_at': NOW,
             }) as inserted:
            result = service.submit(RAW)
        median.assert_called_once_with(105.8, 10.5, normalized['observed_at'])
        self.assertIn('REVIEW_HIGH', inserted.call_args.args[0]['flags'])
        self.assertIn('REVIEW_HIGH', result['flags'])

    def test_future_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, 'FUTURE_TIMESTAMP'):
            normalize(RAW | dict(observed_at=(NOW + timedelta(hours=1)).isoformat()), NOW)

    def test_negative_and_unknown_unit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'EC_OUT_OF_RANGE'):
            normalize(RAW | dict(ec=-1), NOW)
        with self.assertRaisesRegex(ValueError, 'UNIT_UNKNOWN'):
            normalize(RAW | dict(unit='ppm'), NOW)

    def test_field_label_flags_do_not_block_submission(self):
        value = normalize(RAW | dict(ec_basis='RAW', calibrated_at=None), NOW)
        self.assertIn('NO_EC25', value['flags'])
        self.assertIn('CALIBRATION_UNVERIFIED', value['flags'])

    def test_review_requires_separate_configured_key(self):
        import os
        with patch.dict(os.environ, WEBGIS_REVIEW_API_KEY='', WEBGIS_WRITE_API_KEY='submit-secret'):
            response = TestClient(app).post('/api/v1/field-measurements/00000000-0000-0000-0000-000000000001/review',
                headers={'x-api-key': 'submit-secret'}, json=dict(decision='APPROVED', reviewer='A'))
        self.assertEqual(response.status_code, 503)

    def test_submission_requires_internal_key(self):
        import os
        with patch.dict(os.environ, WEBGIS_WRITE_API_KEY=''):
            response = TestClient(app).post('/api/v1/field-measurements', json=RAW)
        self.assertEqual(response.status_code, 503)
        with patch.dict(os.environ, WEBGIS_WRITE_API_KEY='submit-secret'), \
             patch.object(service, 'submit', return_value={'measurement_id': 'x', 'status': 'PENDING'}) as saved:
            response = TestClient(app).post('/api/v1/field-measurements',
                headers={'x-api-key': 'submit-secret'}, json=RAW)
        self.assertEqual(response.status_code, 201)
        saved.assert_called_once()

    def test_only_approved_list_is_readable_without_review_key(self):
        import os
        with patch.dict(os.environ, WEBGIS_REVIEW_API_KEY=''), \
             patch.object(service, 'list_measurements', return_value={'items': [], 'status': 'APPROVED'}):
            self.assertEqual(TestClient(app).get('/api/v1/field-measurements?status=APPROVED').status_code, 200)
            self.assertEqual(TestClient(app).get('/api/v1/field-measurements?status=PENDING').status_code, 503)

    def test_equivalent_field_label_requires_two_calibrated_agreeing_samples(self):
        base = dict(ec_basis='EC25', position_kind='RIVER', calibrated_at=date(2026, 11, 1),
                    calibration_reference='CAL-001')
        rows = [base | dict(measurement_id='a', observed_at=datetime(2026, 11, 15, 9,
                tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')), ec_mS_m=100),
                base | dict(measurement_id='b', observed_at=datetime(2026, 11, 15, 9, 40,
                tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')), ec_mS_m=110)]
        label = field_label_from_rows(rows, date(2026, 11, 1))
        self.assertEqual(label['observed_ec_mS_m'], 105)
        self.assertEqual(label['obs_source'], 'FIELD_APPROVED')
        self.assertIsNone(field_label_from_rows(rows[:1], date(2026, 11, 1)))
        self.assertIsNone(field_label_from_rows([rows[0], rows[1] | dict(ec_mS_m=150)], date(2026, 11, 1)))
        self.assertIsNone(field_label_from_rows([rows[0], rows[1] | dict(calibration_reference=None)], date(2026, 11, 1)))


if __name__ == '__main__':
    unittest.main()
