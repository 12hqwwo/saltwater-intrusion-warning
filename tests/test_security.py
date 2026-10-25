"""Optional API key, browser write protection and database credential boundaries."""
import os
import unittest
from unittest.mock import patch, MagicMock
import psycopg
from fastapi.testclient import TestClient
from backend.main import app
from backend.db_security import assert_application_role
from backend.repositories.dss_storage import write_connection, StorageDisabled


class SecurityTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, WEBGIS_SECURITY_ENABLED='true',
                         WEBGIS_WRITE_API_KEY='', WEBGIS_RESEARCH_MODE='snapshot')
        env.start(); self.addCleanup(env.stop)
        self.client = TestClient(app)

    def test_local_ui_requires_no_login_and_responses_are_not_cached(self):
        response = self.client.get('/api/v1/workspace/summary')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.post('/api/v1/workspace/gate-drafts', json={}).status_code, 422)

    def test_map_documents_allow_origin_referrer_for_external_tiles(self):
        # Middleware also handles HTML/static responses, including this 404.
        # Suppressing cross-origin Referer causes OSM policy-blocked tile images.
        response = self.client.get('/workspace.html')
        self.assertEqual(response.headers['referrer-policy'], 'strict-origin-when-cross-origin')
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(response.headers['x-frame-options'], 'DENY')

    def test_api_key_is_optional_but_enforced_when_configured(self):
        with patch.dict(os.environ, WEBGIS_WRITE_API_KEY='test-key'):
            for path in ['gate-drafts', 'multivariate/history']:
                url = '/api/v1/workspace/' + path
                self.assertEqual(self.client.post(url, json={}).status_code, 401)
                self.assertEqual(self.client.post(url, json={}, headers={'X-API-Key': 'wrong'}).status_code, 401)
                self.assertEqual(self.client.post(url, json={}, headers={'X-API-Key': 'test-key'}).status_code, 422)
            self.assertEqual(self.client.get('/api/v1/workspace/summary').status_code, 200)

    def test_cross_site_write_and_untrusted_hosts_denied(self):
        url = '/api/v1/workspace/gate-drafts'
        for headers in [{'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}]:
            self.assertEqual(self.client.post(url, json={}, headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/app-health', headers={'Host': 'evil.example'}).status_code, 400)

    def test_role_guard_rejects_elevated_accounts(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {'elevated': True}
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            assert_application_role(conn)
        conn.execute.return_value.fetchone.return_value = {'elevated': False}
        assert_application_role(conn)

    def test_writer_never_falls_back_to_administrator(self):
        env = dict(os.environ, WEBGIS_DSS_WRITES_ENABLED='true', PGUSER='postgres')
        env.pop('DSS_PGUSER', None)
        with patch.dict(os.environ, env, clear=True), patch('psycopg.connect') as connect:
            with self.assertRaises(StorageDisabled):
                with write_connection():
                    self.fail('must not connect')
            connect.assert_not_called()

    def test_writer_binds_application_actor(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {'elevated': False}
        with patch.dict(os.environ, WEBGIS_DSS_WRITES_ENABLED='true', DSS_PGUSER='webgis_writer'), patch('psycopg.connect') as connect:
            connect.return_value.__enter__.return_value = conn
            with write_connection():
                pass
            self.assertEqual(connect.call_args.kwargs['user'], 'webgis_writer')
            self.assertIn("SELECT set_config('webgis.actor', %s, true)", conn.execute.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
