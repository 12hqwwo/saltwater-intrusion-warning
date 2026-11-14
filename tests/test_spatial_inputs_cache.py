"""Cache behavior across concurrent requests, source changes, and day rollover."""
import unittest
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from backend.services import spatial_inputs
from backend.services.workspace import WorkspaceError


class MonthlyInputsCacheTests(unittest.TestCase):
    def setUp(self):
        spatial_inputs.monthly_inputs.cache_clear()
        self.addCleanup(spatial_inputs.monthly_inputs.cache_clear)

    def test_repeated_request_uses_same_build(self):
        data = {'2026-11': {'year_month': '2026-11'}}
        with patch.object(spatial_inputs, 'source_stamp', return_value=('2026-11-14', 'v1')), \
             patch.object(spatial_inputs, '_monthly_inputs', return_value=data) as build:
            self.assertIs(spatial_inputs.monthly_inputs(), data)
            self.assertIs(spatial_inputs.monthly_inputs(), data)
        self.assertEqual(build.call_count, 1)
        self.assertEqual(spatial_inputs.cache_metadata()['cache_status'], 'FRESH')
        self.assertTrue(spatial_inputs.cache_metadata()['built_at'])

    def test_parallel_requests_share_one_build(self):
        started, release = Event(), Event()

        def build():
            started.set()
            self.assertTrue(release.wait(5))
            return {'2026-11': {'year_month': '2026-11'}}

        with patch.object(spatial_inputs, 'source_stamp', return_value=('2026-11-14', 'v1')), \
             patch.object(spatial_inputs, '_monthly_inputs', side_effect=build) as builder:
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = [pool.submit(spatial_inputs.monthly_inputs) for _ in range(5)]
                self.assertTrue(started.wait(5))
                release.set()
                results = [future.result(timeout=5) for future in futures]
        self.assertEqual(builder.call_count, 1)
        self.assertTrue(all(item is results[0] for item in results))

    def test_changed_source_failure_is_explicitly_stale(self):
        data = {'2026-11': {'year_month': '2026-11'}}
        with patch.object(spatial_inputs, 'source_stamp', side_effect=[
                ('2026-11-14', 'v1'), ('2026-11-14', 'v2')]), \
             patch.object(spatial_inputs, '_monthly_inputs', side_effect=[data, ValueError('bad source')]):
            spatial_inputs.monthly_inputs()
            built_at = spatial_inputs.cache_metadata()['built_at']
            self.assertIs(spatial_inputs.monthly_inputs(), data)
        self.assertEqual(spatial_inputs.cache_metadata(),
                         {'cache_status': 'STALE', 'built_at': built_at})

    def test_changed_source_rebuilds_result(self):
        first, second = {'first': {}}, {'second': {}}
        with patch.object(spatial_inputs, 'source_stamp', side_effect=[
                ('2026-11-14', 'v1'), ('2026-11-14', 'v2')]), \
             patch.object(spatial_inputs, '_monthly_inputs', side_effect=[first, second]) as build:
            self.assertIs(spatial_inputs.monthly_inputs(), first)
            self.assertIs(spatial_inputs.monthly_inputs(), second)
        self.assertEqual(build.call_count, 2)

    def test_day_rollover_cannot_serve_stale_forecast(self):
        with patch.object(spatial_inputs, 'source_stamp', side_effect=[
                ('2026-11-14', 'v1'), ('2026-11-15', 'v1')]), \
             patch.object(spatial_inputs, '_monthly_inputs', side_effect=[{}, ValueError('bad source')]):
            spatial_inputs.monthly_inputs()
            with self.assertRaises(WorkspaceError) as result:
                spatial_inputs.monthly_inputs()
        self.assertEqual(result.exception.status_code, 503)

    def test_local_day_is_part_of_real_source_stamp(self):
        with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot'):
            first = spatial_inputs.source_stamp(today='2026-11-14')
            second = spatial_inputs.source_stamp(today='2026-11-15')
        self.assertNotEqual(first, second)
        self.assertEqual(first[0], '2026-11-14')

    def test_timeline_exposes_cache_state(self):
        from backend.services.spatial_simulation import simulation_timeline

        with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot'):
            result = simulation_timeline()
        self.assertEqual(result['cache_status'], 'FRESH')
        self.assertTrue(result['built_at'])


if __name__ == '__main__':
    unittest.main()
