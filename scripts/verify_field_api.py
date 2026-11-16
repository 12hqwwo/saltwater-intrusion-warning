from datetime import datetime
from pathlib import Path
import sys
from unittest.mock import patch
from zoneinfo import ZoneInfo
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.services import field_measurements as service
    from backend.auth.access_tokens import issue_access_token
    from backend.repositories import app_users

    client = TestClient(app, base_url='http://127.0.0.1')
    payload = dict(ec=150, unit='mS/m', observed_at=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),
                   longitude=105.8, latitude=10.5, position_kind='RIVER',
                   device='TEST_NO_WRITE', ec_basis='EC25',
                   calibrated_at=None, calibration_reference=None, water_temp_degC=None)
    field_user = dict(user_id=UUID('00000000-0000-0000-0000-000000000001'), username='test_field',
                      display_name='Test field', role='FIELD_STAFF')
    inspector = dict(user_id=UUID('00000000-0000-0000-0000-000000000002'), username='test_inspector',
                     display_name='Test inspector', role='INSPECTOR')
    def lookup(user_id):
        return field_user if user_id == str(field_user['user_id']) else inspector
    with patch.object(app_users, 'find_active_user_by_id', side_effect=lookup), \
         patch.object(service, 'submit', return_value=dict(measurement_id='mock', status='PENDING')):
        assert client.post('/api/v1/field-measurements', json=payload).status_code == 401
        assert client.post('/api/v1/field-measurements', json=payload,
            headers={'Authorization': 'Bearer ' + issue_access_token(field_user)}).status_code == 201
    review_url = '/api/v1/field-measurements/00000000-0000-0000-0000-000000000001/review'
    with patch.object(app_users, 'find_active_user_by_id', side_effect=lookup), \
         patch.object(service, 'review', return_value=dict(decision='APPROVED')):
        assert client.post(review_url, json=dict(decision='APPROVED'),
            headers={'Authorization': 'Bearer ' + issue_access_token(field_user)}).status_code == 403
        assert client.post(review_url, json=dict(decision='APPROVED'),
            headers={'Authorization': 'Bearer ' + issue_access_token(inspector)}).status_code == 200
    assert client.get('/api/v1/field-measurements?status=APPROVED').status_code == 200
    print('Field API roles and approved read verified; all writes were mocked.')


if __name__ == '__main__':
    main()
