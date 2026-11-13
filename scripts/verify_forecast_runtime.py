"""Check writer grants and ledger triggers with synthetic rows, then roll back."""
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def main():
    load_local_env()
    from psycopg.types.json import Jsonb
    from backend.repositories.dss_storage import write_connection
    from backend.database import read_connection

    slot_id, event_id, issue_id = uuid4(), uuid4(), uuid4()
    scheduled = datetime(2026, 11, 6, 9, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
    with write_connection() as conn:
        try:
            conn.execute('''INSERT INTO dss_reference.forecast_slot
                (slot_id,station_key,target_month,schedule_code,scheduled_at)
                VALUES (%s,'MYTHO',%s,'MONTHLY_D06_PREV',%s)''',
                (slot_id, date(2026, 12, 1), scheduled))
            detected = conn.execute('''INSERT INTO dss_reference.forecast_slot_event
                (event_id,slot_id,event_type,reason_code,detected_at)
                VALUES (%s,%s,'MISSED','JOB_NOT_RUN',%s) RETURNING detected_at''',
                (event_id, slot_id, scheduled)).fetchone()['detected_at']
            issue = conn.execute('''INSERT INTO dss_reference.forecast_issue
                (issue_id,slot_id,input_month,model_version,model_sha256,data_version,
                 predicted_ec_mS_m,payload,issue_status,issued_at)
                VALUES (%s,%s,%s,'TEST_ROLLBACK',%s,%s,24.794,%s,'ON_TIME',%s)
                RETURNING issue_status,issued_at''',
                (issue_id, slot_id, date(2026, 10, 1), 'a'*64, 'b'*64,
                 Jsonb({'verification_only': True}), scheduled)).fetchone()
            assert detected > scheduled and issue['issue_status'] == 'LATE' and issue['issued_at'] > scheduled
            conn.execute('''INSERT INTO dss_reference.forecast_score
                (issue_id,label_protocol_version,observation_ref,obs_source,
                 observed_ec_mS_m,abs_error_mS_m)
                VALUES (%s,'TEST_ROLLBACK','synthetic','MRC',30,5.206)''', (issue_id,))
            print('Writer role and ledger triggers accepted synthetic MISSED, LATE and score rows.')
        finally:
            conn.rollback()
    with read_connection() as conn:
        assert conn.execute('SELECT 1 FROM dss_reference.forecast_slot WHERE slot_id=%s', (slot_id,)).fetchone() is None
    print('Rollback verified: no synthetic ledger rows remain.')


if __name__ == '__main__':
    main()
