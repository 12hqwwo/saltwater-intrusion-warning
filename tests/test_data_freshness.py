import unittest
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.domain.data_freshness import assess
from backend.api import data_freshness
from backend.main import app


class FreshnessTests(unittest.TestCase):
    def test_status_boundary_and_supported_target(self):
        self.assertEqual(assess('2026-10', date(2026, 11, 14))['status'], 'FRESH')
        self.assertEqual(assess('2026-10', date(2026, 11, 14))['next_target_month_supported'], '2026-12')
        self.assertEqual(assess('2026-10', date(2026, 11, 30))['status'], 'DUE')
        self.assertEqual(assess('2026-10', date(2026, 12, 5))['status'], 'DUE')
        self.assertEqual(assess('2026-10', date(2026, 12, 6))['status'], 'STALE')

    def test_weather_report_keeps_retrieval_provenance(self):
        with patch.object(data_freshness, 'get_monthly_weather', return_value=[
            dict(input_month='2026-10', retrieved_at='2026-11-01T00:00:00Z')]):
            result = data_freshness._weather('MyTho', date(2026, 11, 14))
        self.assertEqual(result['retrieved_at'], '2026-11-01T00:00:00Z')
        self.assertIn('assumed', result['availability_basis'])

    def test_api_exposes_freshness_report(self):
        with patch.object(data_freshness, 'report', return_value=dict(as_of='2026-11-14', sources={
                'ERA5_MYTHO': assess('2026-10', date(2026, 11, 14))})):
            response = TestClient(app).get('/api/v1/data-freshness')
        self.assertEqual(response.status_code, 200)
        self.assertIn('ERA5_MYTHO', response.json()['sources'])

    def test_real_report_lists_weather_hydrology_and_frozen_ec(self):
        sources = data_freshness.report(date(2026, 11, 14))['sources']
        self.assertEqual(set(sources), {'ERA5_MYTHO', 'ERA5_TANCHAU', 'ERA5_MYTHUAN',
                                        'KRATIE_Q', 'TANCHAU_STAGE', 'MRC_EC_MYTHO'})
        self.assertEqual(sources['MRC_EC_MYTHO']['status'], 'STALE')


if __name__ == '__main__':
    unittest.main()
