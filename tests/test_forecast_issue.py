import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from backend.domain.forecast_issue import (LABEL_PROTOCOL_VERSION, build_issue, schedule, score)
from backend.services import forecast_issues as service
from backend.services.workspace import WorkspaceError
from backend.main import app

PRED = dict(station='MyTho', target_month='2026-12', input_month='2026-10',
    input_mode='ARCHIVE', model_version='v1',
    model_provenance=dict(model_sha256='a' * 64),
    input_provenance=dict(source='ERA5', sha256='b' * 64),
    hydrology_provenance=None, predicted_ec_mS_m=24.794)
ISSUED = datetime(2026, 11, 6, 9, 10, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
OBS = dict(obs_source='MRC', equivalent_monthly_label=True,
    label_protocol_version=LABEL_PROTOCOL_VERSION, observation_ref='MRC:2026-12',
    observed_at='2026-12-15T09:00:00+07:00', observed_ec_mS_m=30.0)


class ForecastIssueDomainTests(unittest.TestCase):
    def test_schedule_is_day_six_previous_month(self):
        self.assertEqual(schedule('2027-01').isoformat(), '2026-12-06T09:00:00+07:00')

    def test_build_issue_pins_model_and_data_identity(self):
        issue = build_issue(PRED, ISSUED)
        self.assertEqual(issue['model_sha256'], 'a' * 64)
        self.assertEqual(issue['input_month'], '2026-10')
        self.assertEqual(issue['station_key'], 'MYTHO')
        self.assertEqual(len(issue['data_version']), 64)

    def test_score_rejects_pending_outside_month_and_non_equivalent(self):
        issue = build_issue(PRED, ISSUED)
        self.assertIsNone(score(issue, OBS | dict(observed_at='2027-01-02T08:00:00+07:00')))
        self.assertIsNone(score(issue, OBS | dict(obs_source='FIELD_PENDING')))
        self.assertIsNone(score(issue, OBS | dict(equivalent_monthly_label=False)))

    def test_score_abs_error(self):
        self.assertAlmostEqual(score(build_issue(PRED, ISSUED), OBS)['abs_error_mS_m'], 5.206)


class ForecastIssueServiceTests(unittest.TestCase):
    def test_predeployment_schedule_cannot_be_backfilled(self):
        with self.assertRaises(WorkspaceError) as caught:
            service.issue_month('2026-12')
        self.assertEqual(caught.exception.status_code, 422)

    def test_api_contract_exposes_issue_and_history(self):
        with patch.object(service, 'issue_month', return_value=dict(items=[])):
            response = TestClient(app).post('/api/v1/forecast-issues', json={'target_month': '2026-12'})
        self.assertEqual(response.status_code, 201)
        with patch.object(service, 'list_issues', return_value=dict(items=[], summary={})):
            response = TestClient(app).get('/api/v1/forecast-issues')
        self.assertEqual(response.status_code, 200)

    def _storage(self, db_now):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {'now': db_now}
        return conn

    def test_second_issue_same_slot_conflicts(self):
        conn = self._storage(ISSUED)
        with patch.object(service.multivariate, 'predict', return_value=PRED), \
             patch.object(service, 'write_connection') as connection, \
             patch.object(service.repo, 'insert_slot', return_value={'slot_id': 'slot'}), \
             patch.object(service.repo, 'existing_issue', return_value={'issue_id': 'old'}):
            connection.return_value.__enter__.return_value = conn
            with self.assertRaises(WorkspaceError) as caught:
                service.issue_for_station('MYTHO', '2026-12', ISSUED)
        self.assertEqual(caught.exception.status_code, 409)

    def test_missing_inputs_records_missed(self):
        conn = self._storage(ISSUED)
        with patch.object(service.multivariate, 'predict', side_effect=WorkspaceError(422, 'Chưa đủ khí tượng')), \
             patch.object(service, 'write_connection') as connection, \
             patch.object(service.repo, 'insert_slot', return_value={'slot_id': 'slot'}), \
             patch.object(service.repo, 'existing_issue', return_value=None), \
             patch.object(service.repo, 'insert_missed') as missed:
            connection.return_value.__enter__.return_value = conn
            result = service.issue_for_station('MYTHO', '2026-12', ISSUED)
        self.assertEqual(result['status'], 'MISSED')
        self.assertEqual(result['http_status'], 422)
        missed.assert_called_once_with(conn, 'slot', 'MISSING_INPUT')

    def test_late_issue_records_job_not_run_at_real_detection(self):
        db_now = datetime(2026, 11, 14, 10, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
        conn = self._storage(db_now)
        with patch.object(service.multivariate, 'predict', return_value=PRED), \
             patch.object(service, 'write_connection') as connection, \
             patch.object(service.repo, 'insert_slot', return_value={'slot_id': 'slot'}), \
             patch.object(service.repo, 'existing_issue', return_value=None), \
             patch.object(service.repo, 'insert_missed') as missed, \
             patch.object(service.repo, 'insert_issue', return_value=dict(issue_id='new',
                 issue_status='LATE', predicted_ec_mS_m=24.794, issued_at=db_now)):
            connection.return_value.__enter__.return_value = conn
            result = service.issue_for_station('MYTHO', '2026-12', db_now)
        self.assertEqual(result['status'], 'LATE')
        missed.assert_called_once_with(conn, 'slot', 'JOB_NOT_RUN')
        self.assertEqual(result['issued_at'], db_now)

    def test_due_audit_only_marks_unissued_slot(self):
        conn = self._storage(ISSUED)
        with patch.object(service, 'write_connection') as connection, \
             patch.object(service.repo, 'insert_slot', side_effect=[{'slot_id': 'a'}, {'slot_id': 'b'}, {'slot_id': 'c'}]), \
             patch.object(service.repo, 'existing_issue', side_effect=[{'issue_status': 'ON_TIME'}, None, None]), \
             patch.object(service.repo, 'insert_missed', return_value={'event_id': 'new'}) as missed:
            connection.return_value.__enter__.return_value = conn
            result = service.audit_due('2027-01', datetime(2026, 12, 7, 9, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')))
        self.assertTrue(result['due'])
        self.assertEqual(result['items'][0]['status'], 'ON_TIME')
        self.assertEqual(missed.call_count, 2)

    def test_late_scores_are_excluded_from_primary_mae(self):
        base = dict(slot_id='slot', station_key='MYTHO', target_month='2026-12-01',
            schedule_code='MONTHLY_D06_PREV', scheduled_at=ISSUED,
            event_id=None, event_type=None, reason_code=None, detected_at=None,
            issue_id='issue', input_month='2026-10-01', model_version='v1',
            model_sha256='a'*64, data_version='b'*64, predicted_ec_mS_m=24.794,
            issued_at=ISSUED, score_id=1, label_protocol_version=LABEL_PROTOCOL_VERSION,
            observation_ref='ref', obs_source='MRC', observed_ec_mS_m=30,
            abs_error_mS_m=5.206, scored_at=ISSUED)
        with patch.object(service.repo, 'list_slots', return_value=[base | dict(issue_status='ON_TIME'),
                                                                    base | dict(issue_status='LATE', score_id=2)]):
            result = service.list_issues()
        self.assertEqual(result['summary']['on_time_n_scored'], 1)
        self.assertEqual(result['summary']['late_n_scored'], 1)
        self.assertAlmostEqual(result['summary']['on_time_mae_mS_m'], 5.206)


if __name__ == '__main__':
    unittest.main()
