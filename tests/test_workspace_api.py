"""Regression checks for scientific labels and read-only API compatibility."""
import csv
import io
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.domain.gates import evaluate
from run_gate_advisor import evaluate as cli_evaluate


class WorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        environment = dict(os.environ)
        environment['WEBGIS_RESEARCH_MODE'] = 'snapshot'
        environment.pop('WEBGIS_RESEARCH_FILE', None)
        self.environment = patch.dict(os.environ, environment, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app)

    def test_legacy_and_canonical_routes_share_contract(self):
        for path in ['summary', 'stations', 'gates', 'future-forecast']:
            legacy = self.client.get('/api/v1/research/' + path)
            canonical = self.client.get('/api/v1/workspace/' + path)
            self.assertEqual(legacy.status_code, 200, legacy.text)
            self.assertEqual(legacy.json(), canonical.json())

    def test_invalid_gate_cannot_be_promoted_by_client_declarations(self):
        payload = {'policy': {'schema_version': 999, 'gate_code': 'G1',
                              'approval': {'status': 'APPROVED', 'reference': 'client'}},
                   'input': {'schema_version': 999, 'gate_code': 'G1', 'mode': 'INTAKE',
                             'coordinates_verified': True, 'functional_confirmed': True,
                             'current_state': 'CLOSED',
                             'operating_status': {'water_demand': True},
                             'hydrological_evidence': {'connected': True, 'reference': 'client'},
                             'observations': {name: {'value': 1, 'vertical_datum': 'client',
                                                    'quality_flag': 'VALIDATED', 'source_reference': 'client'}
                                              for name in ['outside_quality', 'inside_quality', 'outside_level', 'inside_level']}}}
        result = self.client.post('/api/v1/workspace/gate-evaluation', json=payload).json()
        self.assertEqual(result['status'], 'INVALID_INPUT')
        self.assertIsNone(result['recommendation'])
        self.assertFalse(result['declarations_verified_by_server'])
        self.assertIsNone(result['actuator_command'])

        # Even complete client declarations cannot establish server verification.
        for item in payload.values():
            item.update(schema_version=1, is_demo=False)
        result = self.client.post('/api/v1/workspace/gate-evaluation', json=payload).json()
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
        self.assertTrue(all(item['declared_present'] for item in result['checklist']))
        self.assertFalse(result['declarations_verified_by_server'])
        self.assertIsNone(result['recommendation'])

    def test_missing_gate_evidence_stays_unverified(self):
        item = {'schema_version': 1, 'is_demo': False, 'gate_code': 'G1'}
        response = self.client.post('/api/v1/workspace/gate-evaluation', json={'policy': item, 'input': item})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
        self.assertIn('SERVER_VERIFIED_GATE_EVIDENCE', result['missing_evidence'])
        self.assertIsNone(result['recommendation'])
        self.assertFalse(result['declarations_verified_by_server'])
        self.assertIs(cli_evaluate, evaluate)

    def test_unknown_station_is_not_safe_empty_forecast(self):
        response = self.client.get('/api/v1/workspace/future-forecast?station=does-not-exist')
        self.assertEqual(response.status_code, 404)

    def test_estimates_expose_scope_without_risk_claim(self):
        result = self.client.get('/api/v1/workspace/monthly-estimates?station=my_tho').json()
        self.assertEqual(result['data_kind'], 'RETROSPECTIVE_WEATHER_ESTIMATE')
        self.assertFalse(result['live_forecast_available'])
        self.assertFalse(result['gate_decision_eligible'])
        self.assertIsNone(result['issued_at'])
        self.assertIsNone(result['validation_metrics'])
        self.assertNotIn('risk_level', result)
        self.assertEqual({row['station'] for row in result['items']}, {'MyTho'})

    def test_export_respects_selected_station_and_carries_scope(self):
        response = self.client.get('/api/v1/workspace/monthly-estimates/export?station=TanChau')
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(response.text)))
        self.assertTrue(rows)
        self.assertEqual({row['station'] for row in rows}, {'TanChau'})
        self.assertEqual({row['data_kind'] for row in rows}, {'RETROSPECTIVE_WEATHER_ESTIMATE'})

    def test_nonfinite_artifact_returns_controlled_error(self):
        rows = [dict(station='MyTho', year_month='2024-01', model='RF',
                     predicted_ec_mS_m='nan', rainfall_mm='1', temperature_degC='20', wind_m_s='1')]
        with patch('backend.services.forecasts.estimate_rows', return_value=rows):
            response = self.client.get('/api/v1/workspace/monthly-estimates')
        self.assertEqual(response.status_code, 503)

    def test_empty_estimate_export_returns_controlled_error(self):
        with patch('backend.services.forecasts.estimate_rows', return_value=[]):
            response = self.client.get('/api/v1/workspace/monthly-estimates/export')
        self.assertEqual(response.status_code, 503)

    def test_missing_template_returns_controlled_error(self):
        with patch('backend.services.workspace.store.read_json', side_effect=FileNotFoundError):
            response = self.client.get('/api/v1/workspace/gate-template/input')
        self.assertEqual(response.status_code, 503)

    def test_malformed_template_returns_controlled_error(self):
        with patch('backend.services.workspace.store.read_json', return_value={'observations': ['invalid']}):
            response = self.client.get('/api/v1/workspace/gate-template/input?gate_code=G1')
        self.assertEqual(response.status_code, 503)

    def test_intake_canonical_and_legacy_reads_match(self):
        for suffix in ['', '/coverage', '/measurement-points']:
            with self.subTest(suffix=suffix):
                canonical = self.client.get('/api/v1/workspace/intake' + suffix)
                legacy = self.client.get('/api/v1/research/intake' + suffix)
                self.assertEqual(canonical.status_code, 200, canonical.text)
                self.assertEqual(canonical.json(), legacy.json())
                if suffix != '/measurement-points':
                    self.assertFalse(canonical.json()['training_eligible'])

    def test_intake_observation_pagination_preserves_review_status(self):
        points = self.client.get('/api/v1/workspace/intake/measurement-points').json()
        point = next(item['key'] for item in points['items'] if item['records'] >= 2)
        params = dict(point=point, limit=2, offset=0)
        first = self.client.get('/api/v1/workspace/intake/observations', params=params)
        self.assertEqual(first.status_code, 200, first.text)
        data = first.json()
        self.assertEqual(data['status'], 'REVIEW_ONLY')
        self.assertEqual(len(data['items']), 2)
        for row in data['items']:
            self.assertFalse(row['training_eligible'])
            self.assertFalse(row['gate_decision_eligible'])
        params.update(offset=1, limit=1)
        second = self.client.get('/api/v1/workspace/intake/observations', params=params)
        legacy = self.client.get('/api/v1/research/intake/observations', params=params)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json(), legacy.json())
        self.assertEqual(second.json()['items'], data['items'][1:])
        self.assertEqual(second.json()['total'], data['total'])
        params['offset'] = data['total']
        self.assertEqual(
            self.client.get('/api/v1/workspace/intake/observations', params=params).json()['items'],
            [],
        )


if __name__ == '__main__':
    unittest.main()
