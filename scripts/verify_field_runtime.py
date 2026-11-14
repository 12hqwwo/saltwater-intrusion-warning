"""Verify staff writer and reviewer inserts without retaining synthetic measurements."""
from pathlib import Path
from uuid import uuid4
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    from psycopg.types.json import Jsonb
    from backend.repositories.dss_storage import write_connection
    from backend.database import read_connection

    measurement_id = uuid4()
    with write_connection() as conn:
        try:
            conn.execute('''INSERT INTO dss_reference.field_measurement
                (measurement_id,geom,ec_mS_m,unit_original,ec_basis,calibrated_at,
                 observed_at,position_kind,device,submitted_by,raw_payload)
                VALUES (%s,ST_SetSRID(ST_MakePoint(105.8,10.5),4326),100,'mS/m',
                        'EC25','2026-11-01','2026-11-14 09:00:00+07','RIVER',
                        'TEST_ROLLBACK','TEST_ROLLBACK',%s)''',
                (measurement_id, Jsonb({'verification_only': True})))
            conn.execute('''INSERT INTO dss_reference.field_measurement_review
                (measurement_id,decision,reviewer,note)
                VALUES (%s,'APPROVED','TEST_ROLLBACK','synthetic')''', (measurement_id,))
            conn.execute('''INSERT INTO dss_reference.field_measurement_review
                (measurement_id,decision,reviewer,note)
                VALUES (%s,'REJECTED','TEST_ROLLBACK','synthetic')''', (measurement_id,))
            print('Writer role accepted a field measurement and append-only review events.')
        finally:
            conn.rollback()
    with read_connection() as conn:
        assert conn.execute('''SELECT 1 FROM dss_reference.v_field_measurement_status
            WHERE measurement_id=%s''', (measurement_id,)).fetchone() is None
    print('Rollback verified: no synthetic field data remains.')


if __name__ == '__main__':
    main()
