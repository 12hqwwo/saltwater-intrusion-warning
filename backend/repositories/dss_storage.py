"""Optional PostgreSQL DSS storage; historical observation connections stay read-only."""
from contextlib import contextmanager
import os
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from backend.database import read_connection
from backend.db_security import assert_application_role
from backend.security import actor


class StorageDisabled(Exception):
    pass


def require_writes():
    if os.getenv('WEBGIS_DSS_WRITES_ENABLED', '').lower() != 'true':
        raise StorageDisabled('DSS writes are disabled.')


@contextmanager
def write_connection():
    require_writes()
    if not os.getenv('DSS_PGUSER'):
        raise StorageDisabled('A dedicated DSS_PGUSER is required.')
    with psycopg.connect(host=os.getenv('PGHOST', '127.0.0.1'),
        port=os.getenv('PGPORT', '5432'), dbname=os.getenv('PGDATABASE', 'dongthap_gis'),
        user=os.environ['DSS_PGUSER'],
        **({'password': os.environ['DSS_PGPASSWORD']} if 'DSS_PGPASSWORD' in os.environ else {}),
        connect_timeout=5, row_factory=dict_row, application_name='webgis_dss_write_api',
        options='-c statement_timeout=10000 -c lock_timeout=3000 -c timezone=Asia/Ho_Chi_Minh') as conn:
        assert_application_role(conn)
        conn.execute("SELECT set_config('webgis.actor', %s, true)", (actor.get(),))
        yield conn


def threshold_presets():
    with read_connection() as conn:
        return conn.execute('''SELECT preset_code,usage_purpose,threshold_ms_m,ec_basis,
            allow_intake_below_ms_m,stop_intake_from_ms_m,source_note,evidence_status,
            is_operational_rule FROM dss_reference.ec_threshold_presets
            ORDER BY threshold_ms_m,preset_code''').fetchall()


def save_prediction(prediction):
    with write_connection() as conn:
        return conn.execute('''INSERT INTO dss_reference.multivariate_prediction_log
            (prediction_id,station_key,site_code,target_month,input_month,input_mode,model_version,payload)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING payload AS prediction,saved_at''',
            (prediction['prediction_id'], prediction['station'], prediction['site_code'],
             prediction['target_month'] + '-01', prediction['input_month'] + '-01',
             prediction['input_mode'], prediction['model_version'], Jsonb(prediction))).fetchone()


def predictions(station, target_month, limit, offset):
    clauses, params = [], []
    if station is not None:
        clauses.append('station_key=%s'); params.append(station)
    if target_month is not None:
        clauses.append('target_month=%s'); params.append(target_month + '-01')
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with read_connection() as conn:
        total = conn.execute('SELECT count(*) AS total FROM dss_reference.multivariate_prediction_log' + where, params).fetchone()['total']
        items = conn.execute('SELECT payload AS prediction,saved_at FROM dss_reference.multivariate_prediction_log'
            + where + ' ORDER BY saved_at DESC,prediction_id DESC LIMIT %s OFFSET %s', params + [limit, offset]).fetchall()
    return dict(items=items, total=total, limit=limit, offset=offset)


def prediction(prediction_id):
    with read_connection() as conn:
        return conn.execute('''SELECT payload AS prediction,saved_at
            FROM dss_reference.multivariate_prediction_log WHERE prediction_id=%s''', (prediction_id,)).fetchone()


def save_draft(gate_code, data, policy):
    with write_connection() as conn:
        return conn.execute('''INSERT INTO dss_reference.gate_simulation_drafts
            (gate_code,input_payload,policy_payload) VALUES (%s,%s,%s)
            RETURNING draft_id,gate_code,input_payload AS input,policy_payload AS policy,
            created_at,status,declarations_verified_by_server''', (gate_code, Jsonb(data), Jsonb(policy))).fetchone()


def drafts(gate_code, limit, offset):
    with read_connection() as conn:
        total = conn.execute('SELECT count(*) AS total FROM dss_reference.gate_simulation_drafts WHERE gate_code=%s', (gate_code,)).fetchone()['total']
        items = conn.execute('''SELECT draft_id,gate_code,input_payload AS input,policy_payload AS policy,
            created_at,status,declarations_verified_by_server FROM dss_reference.gate_simulation_drafts
            WHERE gate_code=%s ORDER BY created_at DESC,draft_id DESC LIMIT %s OFFSET %s''', (gate_code, limit, offset)).fetchall()
    return dict(items=items, total=total, limit=limit, offset=offset)
