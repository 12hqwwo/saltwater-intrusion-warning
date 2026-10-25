"""Provision restricted runtime roles and audit logging; default is a plan only."""
import argparse
import csv
import hashlib
import io
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_webgis import load_local_env


def protect(path, directory=False):
    if os.name == 'nt':
        result = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'], capture_output=True, text=True, check=True)
        sid = next(csv.reader(io.StringIO(result.stdout)))[1]
        permission = '(OI)(CI)F' if directory else 'F'
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                        '*' + sid + ':' + permission, '*S-1-5-18:' + permission],
                       capture_output=True, check=True)
    else:
        path.chmod(0o700 if directory else 0o600)


def update_env(path, values):
    lines = path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else []
    remaining = dict(values)
    result = []
    for line in lines:
        key = line.partition('=')[0].strip()
        if key in values:
            if key in remaining:
                result.append(key + '=' + remaining.pop(key))
        else:
            result.append(line)
    result.extend(key + '=' + value for key, value in remaining.items())
    path.write_text('\n'.join(result) + '\n', encoding='utf-8')
    protect(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    private = ROOT / '.security'
    if private.is_symlink() or (ROOT / '.env').is_symlink():
        raise ValueError('Refusing symlinked local security paths.')
    print('Plan: create webgis_reader and webgis_writer without administrative privileges;')
    print('grant read access and append-only DSS access, add audit triggers, protect local credentials,')
    print('and enable PostgreSQL forecast/draft storage. Observation rows remain unchanged.')
    if not args.apply:
        print('No changes. Use --apply to install.')
        return
    load_local_env()
    import psycopg
    from psycopg import sql
    private.mkdir(exist_ok=True)
    protect(private, True)
    env_path = ROOT / '.env'
    backup = private / 'env.before-hardening'
    if env_path.exists() and not backup.exists():
        backup.write_bytes(env_path.read_bytes()); protect(backup)
    connection = dict(host=os.getenv('PGHOST', '127.0.0.1'), port=os.getenv('PGPORT','5432'),
                      dbname=os.getenv('PGDATABASE','dongthap_gis'), user=os.getenv('PGUSER','postgres'),
                      connect_timeout=5, application_name='webgis_security_setup')
    passwords = {}
    migration = ROOT / 'sql/31_database_security.sql'
    digest = hashlib.sha256(migration.read_bytes()).hexdigest()
    # Restore files if SQL execution, file writes, or the transaction commit fails.
    managed = [env_path]
    originals = {path: path.read_bytes() if path.exists() else None for path in managed}
    try:
        with psycopg.connect(**connection) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('webgis_security_setup'))")
            if os.getenv('DSS_PGUSER') == 'webgis_dss_writer' and os.getenv('DSS_PGPASSWORD'):
                old = conn.execute("SELECT 1 FROM pg_roles WHERE rolname='webgis_dss_writer'").fetchone()
                new = conn.execute("SELECT 1 FROM pg_roles WHERE rolname='webgis_writer'").fetchone()
                if old and not new:
                    conn.execute('ALTER ROLE webgis_dss_writer RENAME TO webgis_writer')
            for table in ['gate_simulation_drafts', 'multivariate_prediction_log', 'ec_threshold_presets']:
                if conn.execute('SELECT to_regclass(%s)', ('dss_reference.' + table,)).fetchone()[0] is None:
                    raise ValueError('Install scripts/apply_dss_storage.py --apply first.')
            for role, key in [('webgis_reader','WEBGIS_DB_PASSWORD'), ('webgis_writer','DSS_PGPASSWORD')]:
                exists = conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
                if exists:
                    if os.getenv(key) is None or os.getenv('WEBGIS_DB_USER') != 'webgis_reader':
                        raise ValueError('Existing role is not managed by this setup; refusing to replace credentials.')
                    passwords[key] = os.environ[key]
                else:
                    passwords[key] = secrets.token_urlsafe(36)
                    conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 12 PASSWORD {}').format(sql.Identifier(role), sql.Literal(passwords[key])))
                memberships = conn.execute('SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)', (role,)).fetchone()
                if memberships:
                    raise ValueError('Runtime role has unexpected memberships; remove them explicitly before setup.')
                elevated = conn.execute('''SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
                    OR EXISTS(SELECT 1 FROM pg_database WHERE datdba=r.oid)
                    OR EXISTS(SELECT 1 FROM pg_class WHERE relowner=r.oid)
                    OR EXISTS(SELECT 1 FROM pg_namespace WHERE nspowner=r.oid)
                    FROM pg_roles r WHERE rolname=%s''', (role,)).fetchone()[0]
                if elevated:
                    raise ValueError('Runtime role has unexpected administrative privileges or ownership.')
                conn.execute(sql.SQL('ALTER ROLE {} SET statement_timeout = 10000').format(sql.Identifier(role)))
                conn.execute(sql.SQL('ALTER ROLE {} SET lock_timeout = 3000').format(sql.Identifier(role)))
                conn.execute(sql.SQL('ALTER ROLE {} SET idle_in_transaction_session_timeout = 30000').format(sql.Identifier(role)))
                conn.execute(sql.SQL('ALTER ROLE {} SET search_path = pg_catalog, public, dss_reference').format(sql.Identifier(role)))
            conn.execute('ALTER ROLE webgis_reader SET default_transaction_read_only = on')
            conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            conn.execute('REVOKE INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER ON ALL TABLES IN SCHEMA public,dss_reference FROM PUBLIC')
            conn.execute(sql.SQL('REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(connection['dbname'])))
            conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO webgis_reader,webgis_writer').format(sql.Identifier(connection['dbname'])))
            conn.execute('REVOKE ALL ON ALL TABLES IN SCHEMA public,dss_reference FROM webgis_reader,webgis_writer')
            conn.execute('GRANT USAGE ON SCHEMA public,dss_reference TO webgis_reader,webgis_writer')
            conn.execute('GRANT SELECT ON ALL TABLES IN SCHEMA public TO webgis_reader')
            conn.execute('GRANT SELECT ON dss_reference.ec_threshold_presets,dss_reference.gate_simulation_drafts,dss_reference.multivariate_prediction_log TO webgis_reader')
            conn.execute('GRANT SELECT,INSERT ON dss_reference.gate_simulation_drafts,dss_reference.multivariate_prediction_log TO webgis_writer')
            sequence = conn.execute("SELECT pg_get_serial_sequence('dss_reference.gate_simulation_drafts','draft_id')").fetchone()[0]
            conn.execute(sql.SQL('GRANT USAGE ON SEQUENCE {} TO webgis_writer').format(sql.Identifier(*sequence.split('.'))))
            if conn.execute("SELECT to_regnamespace('webgis_research')").fetchone()[0] is not None:
                conn.execute('GRANT USAGE ON SCHEMA webgis_research TO webgis_reader')
                conn.execute('GRANT SELECT ON ALL TABLES IN SCHEMA webgis_research TO webgis_reader')
            conn.execute('CREATE SCHEMA IF NOT EXISTS webgis_security')
            conn.execute('REVOKE ALL ON SCHEMA webgis_security FROM PUBLIC')
            conn.execute('CREATE TABLE IF NOT EXISTS webgis_security.migrations(version text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz DEFAULT now())')
            existing = conn.execute('SELECT sha256 FROM webgis_security.migrations WHERE version=%s', ('31_database_security',)).fetchone()
            if existing:
                if existing[0] != digest:
                    raise ValueError('Security migration checksum mismatch.')
            else:
                conn.execute(migration.read_text(encoding='utf-8'))
                conn.execute('INSERT INTO webgis_security.migrations VALUES (%s,%s,now())', ('31_database_security', digest))
            conn.execute('GRANT USAGE ON SCHEMA webgis_security TO webgis_reader')
            conn.execute('GRANT SELECT ON webgis_security.audit_log TO webgis_reader')
            # Persist generated credentials before commit: a failed file write rolls back the DB transaction.
            credentials = dict(passwords, WEBGIS_DB_USER='webgis_reader', DSS_PGUSER='webgis_writer',
                               WEBGIS_SECURITY_ENABLED='true', WEBGIS_RESEARCH_MODE='postgres',
                               WEBGIS_ALLOWED_HOSTS='127.0.0.1,localhost,[::1]',
                               WEBGIS_DSS_WRITES_ENABLED='true')
            update_env(env_path, credentials)
    except BaseException:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
                protect(path)
        raise
    print('Security installed. Runtime credentials are in the protected, Git-ignored .env.')
    print('PostgreSQL history/draft writes enabled. Restart the server; no UI login is required.')


if __name__ == '__main__':
    main()
