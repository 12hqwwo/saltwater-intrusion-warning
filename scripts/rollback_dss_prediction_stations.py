"""Reverse migration 32 only if no saved MyThuan predictions exist."""
import argparse
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env

VERSION = '32_dss_prediction_stations'
FORWARD = ROOT / 'sql/32_dss_prediction_stations.sql'
REVERSE = ROOT / 'sql/32_dss_prediction_stations_down.sql'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Commit rollback; default is plan only.')
    args = parser.parse_args()
    digest = hashlib.sha256(FORWARD.read_bytes()).hexdigest()
    print(f'Rollback: {VERSION}; forward sha256={digest}')
    if not args.apply:
        print('Plan only. Will refuse rollback if any MyThuan prediction is saved.')
        return
    load_local_env()
    import psycopg
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'),
            port=os.getenv('PGPORT', '5432'), dbname=os.getenv('PGDATABASE', 'dongthap_gis'),
            user=os.getenv('PGUSER', 'postgres'), connect_timeout=5,
            application_name='webgis_dss_migration',
            options='-c statement_timeout=30000 -c lock_timeout=5000') as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('webgis_dss_migration'))")
        existing = conn.execute('SELECT sha256 FROM dss_reference.schema_migrations WHERE version=%s',
                                (VERSION,)).fetchone()
        if existing is None or existing[0] != digest:
            raise ValueError('Migration 32 is not recorded with this checksum; refusing rollback.')
        conn.execute(REVERSE.read_text(encoding='utf-8'))
        conn.execute('DELETE FROM dss_reference.schema_migrations WHERE version=%s', (VERSION,))
    print('Committed rollback. No prediction rows were removed.')


if __name__ == '__main__':
    main()
