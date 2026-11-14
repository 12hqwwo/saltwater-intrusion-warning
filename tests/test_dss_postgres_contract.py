"""Real PostgreSQL column contracts using transaction-local temporary tables only.

Set WEBGIS_TEST_PG_DSN to a test connection with TEMP privilege and PostGIS.
No application table, migration, or production record is changed.
"""
from contextlib import nullcontext
from datetime import date, datetime
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row
from fastapi.testclient import TestClient

from backend.domain.field_measurement import normalize
from backend.domain.forecast_issue import LABEL_PROTOCOL_VERSION, LOCAL_TZ
from backend.main import app
from backend.repositories import field_measurements, forecast_issues
from backend.services import forecast_issues as service


ROOT = Path(__file__).resolve().parents[1]


class TemporaryDssConnection:
    """Run production queries against identically named session-local test tables."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=None):
        query = query.replace('dss_reference.', 'pg_temp.')
        query = query.replace('public.measurement_site', 'pg_temp.measurement_site')
        return self.connection.execute(query, params)


@unittest.skipUnless(os.getenv('WEBGIS_TEST_PG_DSN'), 'Set WEBGIS_TEST_PG_DSN for PostgreSQL contracts')
class PostgresContractTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(os.environ['WEBGIS_TEST_PG_DSN'], row_factory=dict_row,
                                   connect_timeout=5, options='-c statement_timeout=10000')
        self.addCleanup(self.conn.close)
        self.addCleanup(self.conn.rollback)
        for name in ('33_forecast_issue.sql', '35_field_measurement.sql'):
            source = (ROOT / 'sql' / name).read_text(encoding='utf-8')
            for table, definition in re.findall(
                    r'CREATE TABLE dss_reference\.(\w+) \((.*?)\n\);', source, re.S):
                definition = definition.replace('dss_reference.', 'pg_temp.')
                self.conn.execute(f'CREATE TEMP TABLE {table} ({definition}\n) ON COMMIT DROP')
        source = (ROOT / 'sql/35_field_measurement.sql').read_text(encoding='utf-8')
        view = source.split('CREATE VIEW dss_reference.v_field_measurement_status AS', 1)[1].split(';', 1)[0]
        self.conn.execute('CREATE TEMP VIEW v_field_measurement_status AS' +
                          view.replace('dss_reference.', 'pg_temp.'))
        self.conn.execute('''CREATE TEMP TABLE measurement_site
            (site_code text, geom geometry(Point,4326)) ON COMMIT DROP''')
        self.conn.execute('''INSERT INTO pg_temp.measurement_site VALUES
            ('MRC_VN_019805',ST_SetSRID(ST_MakePoint(106.35,10.35),4326))''')
        adapter = TemporaryDssConnection(self.conn)
        for module, name in ((forecast_issues, 'read_connection'),
                             (forecast_issues, 'write_connection'),
                             (field_measurements, 'read_connection'),
                             (field_measurements, 'write_connection'),
                             (service, 'write_connection')):
            mocked = patch.object(module, name, side_effect=lambda: nullcontext(adapter))
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_issue_insert_history_and_scores_preserve_api_units(self):
        now = datetime.now(LOCAL_TZ)
        prediction = dict(station='MyTho', target_month='2026-12', input_month='2026-10',
            input_mode='ARCHIVE', model_version='TEST_TEMP',
            model_provenance=dict(model_sha256='a' * 64),
            input_provenance=dict(sha256='b' * 64), predicted_ec_mS_m=100)
        with patch.object(service.multivariate, 'predict', return_value=prediction):
            issued = service.issue_for_station('MYTHO', '2026-12',
                now=max(now, datetime(2026, 11, 6, 9, tzinfo=LOCAL_TZ)))
        self.assertEqual(issued['predicted_ec_mS_m'], 100)
        row = forecast_issues.existing_issue(TemporaryDssConnection(self.conn), issued['slot_id'])
        self.assertEqual(row['predicted_ec_mS_m'], 100)
        point = forecast_issues.insert_score(issued['issue_id'], dict(
            label_protocol_version=LABEL_PROTOCOL_VERSION, observation_ref='TEMP:MRC',
            obs_source='MRC', observed_ec_mS_m=110, abs_error_mS_m=10))
        self.assertEqual(point['observed_ec_mS_m'], 110)
        self.assertEqual(point['abs_error_mS_m'], 10)
        response = TestClient(app).get('/api/v1/forecast-issues')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['items'][0]['issue']['predicted_ec_mS_m'], 100)
        self.assertEqual(payload['items'][0]['score']['observed_ec_mS_m'], 110)
        self.assertEqual(payload['summary']['by_source']['MRC']['late_mae_mS_m'], 10)
        self.assertIsNone(payload['summary']['by_source']['FIELD_APPROVED']['late_mae_mS_m'])

    def test_field_list_and_monthly_label_preserve_api_units(self):
        now = datetime(2026, 11, 15, 12, tzinfo=LOCAL_TZ)
        for minute, ec in ((0, 100), (40, 110)):
            raw = dict(ec=ec, unit='mS/m', observed_at=f'2026-11-15T09:{minute:02}:00+07:00',
                       longitude=106.35, latitude=10.35, position_kind='RIVER',
                       device='TEMP_METER', submitted_by='TEMP_SUBMITTER', ec_basis='EC25',
                       calibrated_at='2026-11-01', calibration_reference='TEMP_CAL', water_temp_degC=25)
            saved = field_measurements.insert_measurement(normalize(raw, now), raw)
            field_measurements.insert_review(saved['measurement_id'], 'APPROVED', 'TEMP_REVIEWER', '')
        response = TestClient(app).get('/api/v1/field-measurements?status=APPROVED')
        self.assertEqual(response.status_code, 200)
        items = response.json()['items']
        self.assertEqual(sorted(item['ec_mS_m'] for item in items), [100, 110])
        self.assertTrue(all(item['water_temp_degC'] == 25 for item in items))
        label = field_measurements.candidate_field_label('MYTHO', date(2026, 11, 1))
        self.assertEqual(label['observed_ec_mS_m'], 105)
        self.assertEqual(label['obs_source'], 'FIELD_APPROVED')


if __name__ == '__main__':
    unittest.main()
