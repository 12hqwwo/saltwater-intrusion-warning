"""Validate first; --apply imports a new immutable snapshot into PostgreSQL/PostGIS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rest(record, keys):
    return {k: v for k, v in record.items() if k not in keys}


def main():
    from run_webgis import load_local_env
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Commit validated snapshot; never deletes old snapshots.')
    args = parser.parse_args()
    from backend.research import validate_bundle
    import psycopg
    from psycopg.types.json import Jsonb
    path = ROOT / 'data/research/workspace.json'
    raw = path.read_bytes()
    sid = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(path.with_name('workspace_manifest.json').read_text(encoding='utf-8-sig'))
    if sid != manifest['sha256']:
        raise ValueError('Snapshot hash mismatch; no import performed.')
    data = validate_bundle(json.loads(raw))
    counts = {k: len(data[k]) for k in ['sources', 'stations', 'observations', 'gates', 'experiments']}
    if not args.apply:
        print(json.dumps(dict(status='VALIDATED_NO_DB_WRITE', snapshot_id=sid, counts=counts)))
        return
    # Standard libpq password/passfile; no password in command line or log.
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'), port=os.getenv('PGPORT', '5432'),
            dbname=os.getenv('PGDATABASE', 'dongthap_gis'), user=os.getenv('PGUSER', 'postgres'),
            connect_timeout=5, options='-c timezone=Asia/Ho_Chi_Minh -c lock_timeout=5000') as conn:
        conn.execute((ROOT / 'sql/04_research_workspace.sql').read_text(encoding='utf-8'))
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('webgis_research_import',))
        existing = conn.execute('SELECT snapshot_id FROM webgis_research.snapshot WHERE snapshot_id=%s', (sid,)).fetchone()
        if existing:
            print(json.dumps(dict(status='ALREADY_IMPORTED', snapshot_id=sid)))
            return
        conn.execute('INSERT INTO webgis_research.snapshot(snapshot_id,metadata) VALUES(%s,%s)', (sid, Jsonb(rest(data, counts))))
        with conn.cursor() as cursor:
            cursor.executemany('INSERT INTO webgis_research.source VALUES(%s,%s,%s)', [(sid, r['source_id'], Jsonb(rest(r, ['source_id']))) for r in data['sources']])
            cursor.executemany('INSERT INTO webgis_research.site VALUES(%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s)',
                [(sid, r['site_code'], r['site_name'], json.dumps(r['geometry']) if r['geometry'] else None, Jsonb(rest(r, ['site_code', 'site_name', 'geometry']))) for r in data['stations']])
            fields = ['site_code', 'observed_date', 'observed_at', 'time_precision', 'ec_mS_m', 'quality_flag', 'source_id']
            cursor.executemany('INSERT INTO webgis_research.ec_observation VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                [(sid, *(r[k] for k in fields), Jsonb(rest(r, fields))) for r in data['observations']])
            cursor.executemany('INSERT INTO webgis_research.gate_catalog VALUES(%s,%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s)',
                [(sid, r['gate_code'], r['gate_name'], r['source_id'], json.dumps(r['geometry']) if r['geometry'] else None, Jsonb(rest(r, ['gate_code', 'gate_name', 'source_id', 'geometry']))) for r in data['gates']])
            cursor.executemany('INSERT INTO webgis_research.experiment VALUES(%s,%s,%s,%s)',
                [(sid, r['experiment_id'], r['site_code'], Jsonb(rest(r, ['experiment_id', 'site_code']))) for r in data['experiments']])
    print(json.dumps(dict(status='COMMITTED', snapshot_id=sid, counts=counts)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # A failed transaction rolls back, including newly inserted rows.
        print(json.dumps(dict(status='FAILED_ROLLED_BACK', error_type=type(exc).__name__,
            message='Kiểm tra quyền tạo schema, PostGIS và các biến PG*. Không có dữ liệu nạp dở được commit.')), file=sys.stderr)
        raise SystemExit(1)
