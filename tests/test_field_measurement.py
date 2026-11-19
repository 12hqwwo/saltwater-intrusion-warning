import unittest
from datetime import datetime, timedelta
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from backend.domain.field_measurement import normalize
from backend.main import app
from backend.services import field_measurements as service
from backend.repositories.field_measurements import field_label_from_rows
from backend.repositories import field_measurements as field_repo
from backend.services.workspace import WorkspaceError

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

    def test_review_requires_inspector(self):
        response = TestClient(app).post('/api/v1/field-measurements/00000000-0000-0000-0000-000000000001/review',
            json=dict(decision='APPROVED'))
        self.assertEqual(response.status_code, 401)

    def test_submission_requires_field_staff(self):
        response = TestClient(app).post('/api/v1/field-measurements', json={key: value for key, value in RAW.items() if key != 'submitted_by'})
        self.assertEqual(response.status_code, 401)

    def test_only_approved_list_is_readable_without_login(self):
        with patch.object(service, 'list_measurements', return_value={'items': [], 'status': 'APPROVED'}):
            self.assertEqual(TestClient(app).get('/api/v1/field-measurements?status=APPROVED').status_code, 200)
            self.assertEqual(TestClient(app).get('/api/v1/field-measurements?status=PENDING').status_code, 401)

    def test_public_approved_response_omits_staff_identity(self):
        item = dict(measurement_id='id', longitude=105.8, latitude=10.5, ec_mS_m=150,
                    observed_at=NOW, status='APPROVED', submitted_by='staff',
                    reviewer='inspector', review_note='private', device='meter')
        page = dict(items=[item], total=1, has_more=False, next_cursor=None, status='APPROVED')
        with patch.object(service, 'list_measurements', return_value=page):
            result = TestClient(app).get('/api/v1/field-measurements?status=APPROVED').json()
        self.assertEqual(result['items'][0]['ec_mS_m'], 150)
        for key in ('submitted_by', 'reviewer', 'review_note', 'device'):
            self.assertNotIn(key, result['items'][0])

    def test_keyset_page_exposes_next_cursor_and_total(self):
        first_id = UUID('00000000-0000-0000-0000-000000000002')
        second_id = UUID('00000000-0000-0000-0000-000000000001')
        rows = [dict(measurement_id=first_id, submitted_at=NOW),
                dict(measurement_id=second_id, submitted_at=NOW),
                dict(measurement_id=UUID('00000000-0000-0000-0000-000000000000'), submitted_at=NOW)]
        conn = MagicMock()
        conn.execute.side_effect = [MagicMock(fetchone=MagicMock(return_value={'total': 3})),
                                    MagicMock(fetchall=MagicMock(return_value=rows))]
        with patch.object(field_repo, 'read_connection') as read:
            read.return_value.__enter__.return_value = conn
            result = field_repo.list_measurements('APPROVED', None, limit=2)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['total'], 3)
        self.assertTrue(result['has_more'])
        self.assertEqual(result['next_cursor']['before_measurement_id'], second_id)
        self.assertIn('ORDER BY submitted_at DESC,measurement_id DESC', conn.execute.call_args_list[1].args[0])
        conn.execute.side_effect = [MagicMock(fetchone=MagicMock(return_value={'total': 3})),
                                    MagicMock(fetchall=MagicMock(return_value=[rows[2]]))]
        with patch.object(field_repo, 'read_connection') as read:
            read.return_value.__enter__.return_value = conn
            next_page = field_repo.list_measurements('APPROVED', None, limit=2,
                                                      before=(NOW, second_id))
        self.assertEqual(next_page['items'], [rows[2]])
        self.assertFalse(next_page['has_more'])
        self.assertEqual(conn.execute.call_args_list[-1].args[1][-4:-1], (NOW, NOW, second_id))

    def test_cursor_requires_both_fields_and_timezone(self):
        with self.assertRaises(WorkspaceError):
            service.list_measurements(before_measurement_id=UUID(int=1))
        with self.assertRaises(WorkspaceError):
            service.list_measurements(before_submitted_at=datetime(2026, 11, 14),
                                      before_measurement_id=UUID(int=1))

    def test_self_review_is_rejected(self):
        with patch.object(service.repo, 'insert_review', side_effect=ValueError('Không được duyệt phiếu do chính mình gửi.')):
            with self.assertRaises(WorkspaceError) as caught:
                service.review('measurement-1', 'APPROVED', 'canbo', '')
        self.assertEqual(caught.exception.status_code, 403)

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
