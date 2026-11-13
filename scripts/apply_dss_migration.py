"""Apply one checked DSS SQL migration; default is a dry-run plan."""
import argparse
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True, help='Project-relative SQL file directly under sql/.')
    parser.add_argument('--version', required=True, help='Unique migration version.')
    parser.add_argument('--apply', action='store_true', help='Commit migration to PostgreSQL.')
    args = parser.parse_args()
    path = (ROOT / args.file).resolve()
    if path.parent != (ROOT / 'sql').resolve() or path.suffix != '.sql' or path.name.endswith('_down.sql'):
        parser.error('Only forward SQL files directly under sql/ can be applied.')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    print(f'Migration: {args.version}; file={path.relative_to(ROOT)}; sha256={digest}')
    if not args.apply:
        print('Plan only. No database changes.')
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
                                (args.version,)).fetchone()
        if existing:
            if existing[0] != digest:
                raise ValueError('Already applied migration checksum differs; refusing to overwrite schema.')
            print('Already applied with matching checksum; no changes.')
            return
        conn.execute(raw.decode('utf-8'))
        conn.execute('INSERT INTO dss_reference.schema_migrations(version,sha256) VALUES (%s,%s)',
                     (args.version, digest))
    print('Committed DSS migration.')


if __name__ == '__main__':
    main()
