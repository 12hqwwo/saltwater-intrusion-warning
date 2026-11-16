import os
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
import jwt

from backend.auth.access_tokens import issue_access_token
from backend.auth.password_hashing import hash_password, verify_password
from backend.main import app
from backend.repositories import app_users
from backend.services import field_measurements, forecast_issues
from backend.domain.gate_intake_rules import DEFAULT_PROFILE


USER_ID = UUID('00000000-0000-0000-0000-000000000123')


class AuthTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, WEBGIS_AUTH_SECRET='test-secret-' * 5)
        env.start(); self.addCleanup(env.stop)
        self.client = TestClient(app)
        self.user = {'user_id': USER_ID, 'username': 'staff', 'display_name': 'Cán bộ A',
                     'role': 'FIELD_STAFF', 'is_active': True, 'password_hash': hash_password('correct-password')}

    def test_password_hashing_and_login(self):
        self.assertTrue(verify_password('correct-password', self.user['password_hash']))
        self.assertFalse(verify_password('wrong-password', self.user['password_hash']))
        with patch.object(app_users, 'find_active_user_by_username', return_value=self.user), \
             patch.object(app_users, 'find_active_user_by_id', return_value=self.user):
            response = self.client.post('/api/v1/auth/login', json={'username': 'staff', 'password': 'correct-password'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['user']['role'], 'FIELD_STAFF')
            token = response.json()['access_token']
            self.assertEqual(self.client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code, 200)
            self.assertEqual(self.client.post('/api/v1/auth/login', json={'username': 'staff', 'password': 'wrong'}).status_code, 401)

    def test_expired_bad_signature_and_disabled_user(self):
        token = issue_access_token(self.user)
        with patch.object(app_users, 'find_active_user_by_id', return_value=None):
            self.assertEqual(self.client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code, 401)
        self.assertEqual(self.client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer bad.token.value'}).status_code, 401)
        expired = jwt.encode({'sub': str(USER_ID), 'username': 'staff', 'role': 'FIELD_STAFF', 'iat': 1, 'exp': 2},
                             os.environ['WEBGIS_AUTH_SECRET'], algorithm='HS256')
        self.assertEqual(self.client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {expired}'}).status_code, 401)

    def test_login_unavailable_without_postgresql_writer(self):
        with patch.dict(os.environ, WEBGIS_DSS_WRITES_ENABLED='false'):
            result = self.client.post('/api/v1/auth/login', json={'username': 'staff', 'password': 'correct-password'})
        self.assertEqual(result.status_code, 503)

    def test_roles_cover_all_write_endpoints(self):
        token = issue_access_token(self.user)
        with patch.object(app_users, 'find_active_user_by_id', return_value=self.user):
            headers = {'Authorization': f'Bearer {token}'}
            self.assertEqual(self.client.post('/api/v1/forecast-issues', headers=headers, json={}).status_code, 403)
            self.assertEqual(self.client.post('/api/v1/field-measurements/00000000-0000-0000-0000-000000000001/review',
                                              headers=headers, json={'decision': 'APPROVED'}).status_code, 403)
            self.assertEqual(self.client.post('/api/v1/workspace/gate-drafts', headers=headers, json={}).status_code, 422)

    def test_inspector_can_review_and_issue_but_cannot_submit(self):
        inspector = self.user | {'username': 'inspector', 'role': 'INSPECTOR'}
        token = issue_access_token(inspector)
        headers = {'Authorization': f'Bearer {token}'}
        with patch.object(app_users, 'find_active_user_by_id', return_value=inspector), \
             patch.object(field_measurements, 'review', return_value={'decision': 'APPROVED'}) as reviewed, \
             patch.object(forecast_issues, 'issue_month', return_value={'status': 'ok'}):
            response = self.client.post('/api/v1/field-measurements/00000000-0000-0000-0000-000000000001/review',
                                        headers=headers, json={'decision': 'APPROVED'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(reviewed.call_args.args[2], 'inspector')
            self.assertEqual(self.client.post('/api/v1/forecast-issues', headers=headers,
                                              json={'target_month': '2026-12'}).status_code, 201)
            self.assertEqual(self.client.post('/api/v1/field-measurements', headers=headers, json={}).status_code, 403)

    def test_guest_gate_result_is_reduced_and_custom_profile_is_forbidden(self):
        payload = {'measurement': {}, 'now_iso': '2026-11-17T10:00:00+07:00'}
        result = self.client.post('/api/v1/gate-screening/evaluate', json=payload)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(set(result.json()), {'status', 'statusTitle', 'summaryReason'})
        changed = dict(DEFAULT_PROFILE, maxExteriorEcMsM=200)
        self.assertEqual(self.client.post('/api/v1/gate-screening/evaluate',
                                          json=payload | {'profile': changed}).status_code, 403)


if __name__ == '__main__':
    unittest.main()
