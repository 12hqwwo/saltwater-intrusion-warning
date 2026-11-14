"""Execute migration 33 inside a transaction and always roll it back."""
from pathlib import Path
import os
import sys
from uuid import uuid4
from datetime import date, datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    import psycopg
    from psycopg.types.json import Jsonb
    sql = (ROOT / 'sql/33_forecast_issue.sql').read_text('utf-8')
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'),
                         port=os.getenv('PGPORT', '5432'),
                         dbname=os.getenv('PGDATABASE', 'dongthap_gis'),
                         user=os.getenv('PGUSER', 'postgres'),
                         connect_timeout=5) as conn:
        try:
            if conn.execute("SELECT to_regclass('dss_reference.forecast_slot')").fetchone()[0]:
                print('Migration 33 is already installed; run scripts/verify_forecast_runtime.py for live-role checks.')
                return
            conn.execute(sql)
            for table in ('forecast_slot', 'forecast_slot_event', 'forecast_issue', 'forecast_score'):
                assert conn.execute('SELECT to_regclass(%s)', ('dss_reference.' + table,)).fetchone()[0]
            slot_id, event_id, issue_id = uuid4(), uuid4(), uuid4()
            scheduled = datetime(2026, 11, 6, 9, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
            conn.execute('''INSERT INTO dss_reference.forecast_slot
                (slot_id,station_key,target_month,schedule_code,scheduled_at)
                VALUES (%s,'MYTHO',%s,'MONTHLY_D06_PREV',%s)''',
                (slot_id, date(2026, 12, 1), scheduled))
            event = conn.execute('''INSERT INTO dss_reference.forecast_slot_event
                (event_id,slot_id,event_type,reason_code,detected_at)
                VALUES (%s,%s,'MISSED','JOB_NOT_RUN',%s) RETURNING detected_at''',
                (event_id, slot_id, scheduled)).fetchone()[0]
            assert event > scheduled, 'detected_at was backdated'
            issued = conn.execute('''INSERT INTO dss_reference.forecast_issue
                (issue_id,slot_id,input_month,model_version,model_sha256,data_version,
                 predicted_ec_mS_m,payload,issue_status,issued_at)
                VALUES (%s,%s,%s,'v1',%s,%s,24.794,%s,'ON_TIME',%s)
                RETURNING issue_status,issued_at''',
                (issue_id, slot_id, date(2026, 10, 1), 'a'*64, 'b'*64,
                 Jsonb({}), scheduled)).fetchone()
            assert issued[0] == 'LATE' and issued[1] > scheduled
            conn.execute('''INSERT INTO dss_reference.forecast_score
                (issue_id,label_protocol_version,observation_ref,obs_source,
                 observed_ec_mS_m,abs_error_mS_m)
                VALUES (%s,'MONTHLY_EC_LABEL_V1_20261114','MRC:2026-12','MRC',30,5.206)''',
                (issue_id,))
            print('Migration 33, MISSED + LATE slot and one score verified in a rollback-only transaction.')
        finally:
            conn.rollback()


if __name__ == '__main__':
    main()
