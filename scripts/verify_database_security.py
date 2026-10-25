"""Verify real role grants with rolled-back writes; emit no credentials."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env
import psycopg
from psycopg.rows import dict_row
from backend.db_security import assert_application_role


def main():
    load_local_env()
    base = dict(host=os.getenv('PGHOST', '127.0.0.1'), port=os.getenv('PGPORT', '5432'),
                dbname=os.getenv('PGDATABASE', 'dongthap_gis'), connect_timeout=5, row_factory=dict_row)
    result = {'checks': [], 'writes_rolled_back': True}

    def denied(conn, query):
        try:
            with conn.transaction():
                conn.execute(query)
        except psycopg.errors.InsufficientPrivilege:
            return
        raise AssertionError('Expected PostgreSQL permission denial: ' + query)

    for role, password in [(os.environ['WEBGIS_DB_USER'], os.environ['WEBGIS_DB_PASSWORD']),
                           (os.environ['DSS_PGUSER'], os.environ['DSS_PGPASSWORD'])]:
        with psycopg.connect(**base, user=role, password=password) as conn:
            # Test ACLs independently of the reader's default read-only transaction.
            conn.read_only = False
            assert_application_role(conn)
            for query in [
                'INSERT INTO public.conductivity_observation DEFAULT VALUES',
                'UPDATE public.conductivity_observation SET source_row=source_row WHERE false',
                'DELETE FROM public.conductivity_observation WHERE false',
                'TRUNCATE public.conductivity_observation',
                'UPDATE dss_reference.gate_simulation_drafts SET gate_code=gate_code WHERE false',
                'DELETE FROM dss_reference.multivariate_prediction_log WHERE false',
                'INSERT INTO webgis_security.audit_log DEFAULT VALUES',
                'DELETE FROM webgis_security.audit_log WHERE false',
                'CREATE TABLE public.security_permission_probe(id int)',
                'CREATE TEMP TABLE security_permission_probe(id int)',
            ]:
                denied(conn, query)
            if role == 'webgis_reader':
                result['observation_count'] = conn.execute('SELECT count(*) AS n FROM public.conductivity_observation').fetchone()['n']
                denied(conn, 'INSERT INTO dss_reference.gate_simulation_drafts DEFAULT VALUES')
            else:
                denied(conn, 'SELECT * FROM public.conductivity_observation LIMIT 0')
                with conn.transaction(force_rollback=True):
                    conn.execute("SELECT set_config('webgis.actor','SECURITY_VERIFICATION',true)")
                    conn.execute('''INSERT INTO dss_reference.gate_simulation_drafts(gate_code,input_payload,policy_payload)
                        VALUES ('SECURITY_CHECK','{"gate_code":"SECURITY_CHECK","schema_version":1}',
                        '{"gate_code":"SECURITY_CHECK","schema_version":1}')''')
            result['checks'].append({'role': role, 'non_admin': True, 'forbidden_operations_denied': True})

    # Inspect the actual writer's trigger within one administrator rollback.
    with psycopg.connect(**base, user=os.getenv('PGUSER', 'postgres')) as conn:
        with conn.transaction(force_rollback=True):
            conn.execute('SET LOCAL SESSION AUTHORIZATION webgis_writer')
            conn.execute("SELECT set_config('webgis.actor','SECURITY_VERIFICATION',true)")
            row = conn.execute('''INSERT INTO dss_reference.gate_simulation_drafts(gate_code,input_payload,policy_payload)
                VALUES ('SECURITY_CHECK','{"gate_code":"SECURITY_CHECK","schema_version":1}',
                '{"gate_code":"SECURITY_CHECK","schema_version":1}') RETURNING draft_id''').fetchone()
            conn.execute('RESET SESSION AUTHORIZATION')
            audit = conn.execute('''SELECT database_actor,application_actor FROM webgis_security.audit_log
                WHERE table_name='dss_reference.gate_simulation_drafts' AND record_id=%s''', (str(row['draft_id']),)).fetchone()
            assert audit == {'database_actor': 'webgis_writer', 'application_actor': 'SECURITY_VERIFICATION'}
            result['audit_trigger_verified'] = True
    target = ROOT / 'docs/database-security-verification.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
