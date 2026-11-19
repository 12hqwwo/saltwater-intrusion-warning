import os
import unittest
from unittest.mock import patch, MagicMock
import psycopg
from fastapi.testclient import TestClient
from backend.main import app
from backend.db_security import assert_application_role
from backend.repositories import dss_storage as dss_store
from backend.repositories.dss_storage import write_connection, StorageDisabled
from backend.auth.access_tokens import issue_access_token
from backend.repositories import app_users
from uuid import UUID


class SecurityTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, WEBGIS_SECURITY_ENABLED='true', WEBGIS_RESEARCH_MODE='snapshot')
        env.start(); self.addCleanup(env.stop)
        self.client = TestClient(app)

    def test_local_ui_requires_no_login_and_responses_are_not_cached(self):
        response = self.client.get('/api/v1/workspace/summary')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.post('/api/v1/workspace/gate-drafts', json={}).status_code, 401)

    def test_map_documents_allow_origin_referrer_for_external_tiles(self):
        response = self.client.get('/workspace.html')
        self.assertEqual(response.headers['referrer-policy'], 'strict-origin-when-cross-origin')
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(response.headers['x-frame-options'], 'DENY')

    def test_write_endpoints_require_login(self):
        for url in ['/api/v1/workspace/gate-drafts', '/api/v1/workspace/multivariate/history',
                    '/api/v1/multivariate/history', '/api/v1/forecast-issues']:
            self.assertEqual(self.client.post(url, json={}).status_code, 401)
        self.assertEqual(self.client.get('/api/v1/workspace/summary').status_code, 200)

    def test_write_key_does_not_replace_login(self):
        with patch.dict(os.environ, WEBGIS_WRITE_API_KEY='test-key'):
            for url in ['/api/v1/workspace/gate-drafts', '/api/v1/workspace/multivariate/history',
                        '/api/v1/research/gate-drafts', '/api/v1/research/multivariate/history',
                        '/api/v1/multivariate/history']:
                with self.subTest(url=url):
                    self.assertEqual(self.client.post(url, json={}).status_code, 401)
                    self.assertEqual(self.client.post(url, json={}, headers={'X-API-Key': 'wrong'}).status_code, 401)
                    expected = 404 if '/research/' in url else 401
                    self.assertEqual(self.client.post(url, json={}, headers={'X-API-Key': 'test-key'}).status_code, expected)

    def test_signed_user_can_write_without_api_key(self):
        user = {'user_id': UUID('00000000-0000-0000-0000-000000000123'), 'username': 'staff',
                'display_name': 'Cán bộ', 'role': 'FIELD_STAFF', 'is_active': True}
        with patch.dict(os.environ, WEBGIS_WRITE_API_KEY='test-key', WEBGIS_AUTH_SECRET='test-secret-' * 5), \
             patch.object(app_users, 'find_active_user_by_id', return_value=user):
            token = issue_access_token(user)
            headers = {'Authorization': f'Bearer {token}'}
            self.assertEqual(self.client.post('/api/v1/workspace/gate-drafts', json={}, headers=headers).status_code, 422)
            self.assertEqual(self.client.post('/api/v1/workspace/multivariate/history', json={}, headers=headers).status_code, 422)

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
        with patch.dict(os.environ, env, clear=True), patch.object(dss_store, 'open_write_pool') as pool:
            with self.assertRaises(StorageDisabled):
                with write_connection():
                    self.fail('must not connect')
            pool.assert_not_called()

    def test_writer_binds_application_actor(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {'elevated': False}
        with patch.dict(os.environ, WEBGIS_DSS_WRITES_ENABLED='true', DSS_PGUSER='webgis_writer'), \
             patch.object(dss_store, 'open_write_pool') as pool:
            pool.return_value.connection.return_value.__enter__.return_value = conn
            with write_connection():
                pass
            self.assertEqual(dss_store._write_config()[3], 'webgis_writer')
            self.assertIn("SELECT set_config('webgis.actor', %s, true)", conn.execute.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
