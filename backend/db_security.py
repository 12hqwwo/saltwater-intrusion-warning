"""Reject administrator/owner credentials in application connections."""
import psycopg


def assert_application_role(conn):
    row = conn.execute('''WITH RECURSIVE memberships(oid) AS (
        SELECT oid FROM pg_roles WHERE rolname=session_user
        UNION SELECT m.roleid FROM pg_auth_members m JOIN memberships p ON m.member=p.oid
    ) SELECT EXISTS(SELECT 1 FROM pg_roles r JOIN memberships m USING(oid)
        WHERE left(r.rolname,3)='pg_' OR r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls
        OR EXISTS(SELECT 1 FROM pg_database d WHERE d.datdba=r.oid AND d.datname=current_database())
        OR EXISTS(SELECT 1 FROM pg_namespace n WHERE n.nspowner=r.oid
            AND n.nspname IN ('public','dss_reference','webgis_security','webgis_research'))
        OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
            WHERE c.relowner=r.oid AND n.nspname IN ('public','dss_reference','webgis_security','webgis_research'))
    ) AS elevated''').fetchone()
    if row['elevated']:
        raise psycopg.errors.InsufficientPrivilege('Application database roles must not be administrators, owners, or members of privileged roles.')
