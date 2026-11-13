import json
import csv
import hashlib
import math
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.domain.gate_intake_rules import evaluate
from backend.main import app


CASES = json.loads((Path(__file__).parent / 'fixtures/gate_intake_cases.json').read_text('utf-8'))


class GateIntakeParityTests(unittest.TestCase):
    def test_p90_candidate_is_reproducible_and_not_active(self):
        root = Path(__file__).parents[1]
        candidate = json.loads((root / 'data/models/gate_alert_reference_candidate_20261114.json').read_text('utf-8'))
        source = root / candidate['alert_reference']['source']
        self.assertEqual(candidate['status'], 'CANDIDATE_NOT_ACTIVE')
        self.assertIsNone(candidate['effective_at'])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), candidate['alert_reference']['source_sha256'])
        with source.open(encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        values = sorted(float(row['conductivity_mS_per_m']) for row in rows
                        if row['station'] == 'MYTHO' and row['month_start'] <= '2023-12-01')
        self.assertEqual(len(values), candidate['alert_reference']['label_count'])
        self.assertEqual(values[math.ceil(.9 * len(values)) - 1], candidate['alert_reference']['p90_mS_m'])

    def test_fixture_cases_match_expected_status_and_checks(self):
        for case in CASES['cases']:
            with self.subTest(case=case['id']):
                measurement = CASES['base_measurement'] | case['measurement']
                result = evaluate(measurement, forecast_context=case['context'], now_iso=CASES['now_iso'])
                self.assertEqual(result['status'], case['expected'])
                self.assertTrue(result['requiresOperatorReview'])
                self.assertIsNone(result['actuatorCommand'])
                self.assertEqual(len(result['rule_profile_hash']), 64)
                self.assertEqual(len(result['input_hash']), 64)
                self.assertIn('SAMPLE_FRESHNESS', {item['id'] for item in result['checks']})

    def test_endpoint_is_stateless_and_limits_body(self):
        payload = dict(measurement=CASES['base_measurement'], forecast_context={}, now_iso=CASES['now_iso'])
        response = TestClient(app).post('/api/v1/gate-screening/evaluate', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ELIGIBLE_FOR_REVIEW')
        payload['unexpected'] = 'field'
        self.assertEqual(TestClient(app).post('/api/v1/gate-screening/evaluate', json=payload).status_code, 422)
        payload.pop('unexpected')
        payload['measurement']['measuredBy'] = 'x' * 66000
        self.assertEqual(TestClient(app).post('/api/v1/gate-screening/evaluate', json=payload).status_code, 413)


if __name__ == '__main__':
    unittest.main()
