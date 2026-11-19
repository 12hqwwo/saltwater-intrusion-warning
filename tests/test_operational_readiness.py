import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import psycopg

from backend.main import app, lifespan
from backend.repositories import workspace


class OperationalReadinessTests(unittest.TestCase):
    def test_readiness_checks_database_only_in_postgres_mode(self):
        with patch('backend.main.Repository.health', return_value={'database_name': 'dongthap_gis'}) as check:
            with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot'):
                response = TestClient(app).get('/api/v1/ready')
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()['database_checked'])
                check.assert_not_called()
            with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='postgres'):
                response = TestClient(app).get('/api/v1/ready')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['database_checked'])
                check.assert_called_once()

    def test_readiness_fails_when_postgres_is_unavailable(self):
        with patch.dict(os.environ, WEBGIS_RESEARCH_MODE='postgres'), \
             patch('backend.main.Repository.health', side_effect=psycopg.OperationalError('offline')):
            self.assertEqual(TestClient(app).get('/api/v1/ready').status_code, 503)

    def test_lifespan_closes_auth_pool(self):
        async def exercise():
            async with lifespan(app):
                pass
        with patch('backend.domain.multivariate_ec.warmup_models', return_value={}), \
             patch('backend.repositories.dss_storage.close_auth_read_pool') as close_auth, \
             patch('backend.repositories.dss_storage.close_write_pool'), \
             patch('backend.database.close_read_pool'), \
             patch.dict(os.environ, WEBGIS_RESEARCH_MODE='snapshot', WEBGIS_DSS_WRITES_ENABLED='false'):
            asyncio.run(exercise())
            close_auth.assert_called_once()

    def test_workspace_stamp_reads_single_version_row(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {'version': 17}
        with patch.object(workspace, 'read_connection') as read:
            read.return_value.__enter__.return_value = conn
            workspace._postgres_stamp_for_bucket.cache_clear()
            stamp = workspace._postgres_stamp_for_bucket(100, (), '{}')
        self.assertEqual(stamp[-1], 17)
        self.assertEqual(conn.execute.call_count, 1)
        self.assertIn('workspace_cache_version', conn.execute.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
