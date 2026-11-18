"""Repeatable local API timings with real PostgreSQL and per-request SQL counts.

Run from the repository root: .venv/Scripts/python.exe -m scripts.benchmark_api
The script reads the existing .env and never changes database records.
"""
import argparse
import math
import os
from statistics import median
from time import perf_counter
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from run_webgis import load_local_env


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()
    if args.samples < 2:
        parser.error('--samples must be at least 2')
    load_local_env()
    os.environ['WEBGIS_RESEARCH_MODE'] = 'postgres'
    from backend.auth.access_tokens import issue_access_token
    from backend.main import app
    from backend.repositories.dss_storage import auth_read_connection

    with auth_read_connection() as conn:
        user = conn.execute('''SELECT user_id, username, display_name, role
            FROM webgis_security.app_user WHERE is_active=true
            AND role IN ('FIELD_STAFF', 'INSPECTOR') ORDER BY user_id LIMIT 1''').fetchone()
    if user is None:
        raise RuntimeError('An active staff/inspector account is required for the predict benchmark.')
    headers = {'Authorization': 'Bearer ' + issue_access_token(user)}
    endpoints = [
        ('simulation/frame', 'GET', '/api/v1/workspace/simulation/frame',
         {'params': {'year_month': '2025-01'}}),
        ('stations', 'GET', '/api/v1/stations', {}),
        ('multivariate/predict', 'POST', '/api/v1/multivariate/predict',
         {'headers': headers, 'json': {'station': 'TanChau', 'target_month': '2026-12',
                                      'input_mode': 'MANUAL', 'rainfall_mm': 100.0,
                                      'temperature_degC': 28.0, 'wind_source_units': 2.0}}),
    ]
    original_execute = psycopg.Connection.execute
    sql_count = 0

    def counted_execute(connection, *args, **kwargs):
        nonlocal sql_count
        sql_count += 1
        return original_execute(connection, *args, **kwargs)

    with TestClient(app, base_url='http://127.0.0.1') as client:
        for label, method, path, options in endpoints:
            times, counts = [], []
            with patch.object(psycopg.Connection, 'execute', counted_execute):
                for index in range(args.samples + 1):
                    sql_count = 0
                    start = perf_counter()
                    response = client.request(method, path, **options)
                    duration_ms = (perf_counter() - start) * 1000
                    if response.status_code != 200:
                        raise RuntimeError(f'{label}: HTTP {response.status_code}: {response.text[:300]}')
                    if index:
                        times.append(duration_ms)
                        counts.append(sql_count)
            print(f'{label}: samples={len(times)} p50_ms={median(times):.2f} '
                  f'p95_ms={percentile(times, .95):.2f} '
                  f'sql_p50={median(counts):g} sql_max={max(counts)}')


if __name__ == '__main__':
    main()
