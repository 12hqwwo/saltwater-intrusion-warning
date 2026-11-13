"""Check staff API keys with mocked writes; do not retain a field submission."""
from datetime import datetime
from pathlib import Path
import os
import sys
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.services import field_measurements as service

    client = TestClient(app, base_url='http://127.0.0.1')
    payload = dict(ec=150, unit='mS/m', observed_at=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),
                   longitude=105.8, latitude=10.5, position_kind='RIVER',
                   device='TEST_NO_WRITE', submitted_by='TEST_NO_WRITE', ec_basis='EC25',
                   calibrated_at=None, calibration_reference=None, water_temp_degC=None)
    with patch.object(service, 'submit', return_value=dict(measurement_id='mock', status='PENDING')):
        assert client.post('/api/v1/field-measurements', json=payload).status_code == 401
        assert client.post('/api/v1/field-measurements', json=payload,
            headers={'X-API-Key': os.environ['WEBGIS_WRITE_API_KEY']}).status_code == 201
    review_url = '/api/v1/field-measurements/00000000-0000-0000-0000-000000000001/review'
    with patch.object(service, 'review', return_value=dict(decision='APPROVED')):
        assert client.post(review_url, json=dict(decision='APPROVED', reviewer='TEST_NO_WRITE'),
            headers={'X-API-Key': os.environ['WEBGIS_WRITE_API_KEY']}).status_code == 401
        assert client.post(review_url, json=dict(decision='APPROVED', reviewer='TEST_NO_WRITE'),
            headers={'X-API-Key': os.environ['WEBGIS_REVIEW_API_KEY']}).status_code == 200
    assert client.get('/api/v1/field-measurements?status=APPROVED').status_code == 200
    print('Field API submit/review keys and approved read verified; all writes were mocked.')


if __name__ == '__main__':
    main()
