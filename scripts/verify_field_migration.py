"""Check migration 35 and latest-review semantics, always rolling back synthetic rows."""
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    import psycopg
    from psycopg.types.json import Jsonb
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'),
                         port=os.getenv('PGPORT', '5432'),
                         dbname=os.getenv('PGDATABASE', 'dongthap_gis'),
                         user=os.getenv('PGUSER', 'postgres'), connect_timeout=5) as conn:
        try:
            if conn.execute("SELECT to_regclass('dss_reference.field_measurement')").fetchone()[0] is None:
                conn.execute((ROOT / 'sql/35_field_measurement.sql').read_text('utf-8'))
            measurement_id = uuid4()
            conn.execute('''INSERT INTO dss_reference.field_measurement
                (measurement_id,geom,ec_mS_m,unit_original,ec_basis,calibrated_at,
                 observed_at,position_kind,device,submitted_by,raw_payload)
                VALUES (%s,ST_SetSRID(ST_MakePoint(105.8,10.5),4326),100,'mS/m',
                        'EC25','2026-11-01','2026-11-14 09:00:00+07','RIVER',
                        'TEST_ROLLBACK','TEST_ROLLBACK',%s)''',
                (measurement_id, Jsonb({'verification_only': True})))
            def status():
                return conn.execute('''SELECT status FROM dss_reference.v_field_measurement_status
                    WHERE measurement_id=%s''', (measurement_id,)).fetchone()[0]
            assert status() == 'PENDING'
            conn.execute('''INSERT INTO dss_reference.field_measurement_review
                (measurement_id,decision,reviewer,note)
                VALUES (%s,'APPROVED','TEST_ROLLBACK','synthetic')''', (measurement_id,))
            assert status() == 'APPROVED'
            conn.execute('''INSERT INTO dss_reference.field_measurement_review
                (measurement_id,decision,reviewer,note)
                VALUES (%s,'REJECTED','TEST_ROLLBACK','synthetic')''', (measurement_id,))
            assert status() == 'REJECTED'
            print('Migration 35 and latest-review view verified with rollback-only synthetic rows.')
        finally:
            conn.rollback()


if __name__ == '__main__':
    main()
