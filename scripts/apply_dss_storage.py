"""Explicit additive DSS migration, checksum tracked and atomic; no model training."""
import argparse
import hashlib
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply in one database transaction; default prints plan only.')
    args = parser.parse_args()
    path = ROOT / 'sql/30_dss_storage.sql'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    print('Migration: 30_dss_storage; sha256=' + digest)
    if not args.apply:
        print('Plan only. Creates three dss_reference tables and three explicitly unverified EC comparison examples. No public changes.')
        return
    load_local_env()
    import os
    import psycopg
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'), port=os.getenv('PGPORT', '5432'),
        dbname=os.getenv('PGDATABASE', 'dongthap_gis'), user=os.getenv('PGUSER', 'postgres'),
        connect_timeout=5, application_name='webgis_dss_migration',
        options='-c statement_timeout=30000 -c lock_timeout=5000') as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('webgis_dss_migration'))")
        conn.execute('CREATE SCHEMA IF NOT EXISTS dss_reference')
        conn.execute('''CREATE TABLE IF NOT EXISTS dss_reference.schema_migrations
            (version text PRIMARY KEY,sha256 char(64) NOT NULL,applied_at timestamptz NOT NULL DEFAULT now())''')
        existing = conn.execute('SELECT sha256 FROM dss_reference.schema_migrations WHERE version=%s', ('30_dss_storage',)).fetchone()
        if existing:
            if existing[0] != digest:
                raise ValueError('Already applied migration checksum differs; do not overwrite existing schema.')
            print('Already applied with matching checksum; no changes.')
            return
        conn.execute(raw.decode('utf-8'))
        conn.execute('INSERT INTO dss_reference.schema_migrations(version,sha256) VALUES (%s,%s)', ('30_dss_storage', digest))
    print('Committed DSS migration. Existing public tables were not modified.')


if __name__ == '__main__':
    main()
