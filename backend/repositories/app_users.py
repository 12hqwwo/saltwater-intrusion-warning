from fastapi import HTTPException
from contextlib import contextmanager
from uuid import uuid4
from backend.repositories.dss_storage import StorageDisabled, auth_read_connection, write_connection


@contextmanager
def auth_connection():
    try:
        with write_connection() as conn:
            yield conn
    except StorageDisabled as exc:
        raise HTTPException(503, 'Đăng nhập cần PostgreSQL và tài khoản ghi DSS đã cấu hình.') from exc


@contextmanager
def auth_read_only_connection():
    try:
        with auth_read_connection() as conn:
            yield conn
    except StorageDisabled as exc:
        raise HTTPException(503, 'Đăng nhập cần PostgreSQL và tài khoản ghi DSS đã cấu hình.') from exc


def find_active_user_by_username(username: str):
    with auth_read_only_connection() as conn:
        return conn.execute('''SELECT user_id,username,display_name,password_hash,role,is_active
            FROM webgis_security.app_user WHERE lower(username)=lower(%s) AND is_active=true''', (username,)).fetchone()


def find_active_user_by_id(user_id: str):
    with auth_read_only_connection() as conn:
        return conn.execute('''SELECT user_id,username,display_name,role,is_active
            FROM webgis_security.app_user WHERE user_id=%s::uuid AND is_active=true''', (user_id,)).fetchone()


def create_pending_user(username: str, display_name: str, password_hash: str):
    with auth_connection() as conn:
        return conn.execute('''INSERT INTO webgis_security.app_user
            (user_id,username,display_name,password_hash,role,is_active,registration_requested_at)
            VALUES (%s,%s,%s,%s,'FIELD_STAFF',false,clock_timestamp()) RETURNING user_id''',
            (uuid4(), username, display_name, password_hash)).fetchone()


def list_pending_users():
    with auth_connection() as conn:
        return conn.execute('''SELECT user_id,username,display_name,created_at
            FROM webgis_security.app_user WHERE role='FIELD_STAFF' AND is_active=false
            AND registration_requested_at IS NOT NULL AND approved_at IS NULL
            ORDER BY registration_requested_at,user_id''').fetchall()


def approve_pending_user(user_id, inspector_id):
    with auth_connection() as conn:
        return conn.execute('''UPDATE webgis_security.app_user
            SET is_active=true,approved_by=%s,approved_at=clock_timestamp()
            WHERE user_id=%s AND role='FIELD_STAFF' AND is_active=false
            AND registration_requested_at IS NOT NULL AND approved_at IS NULL
            RETURNING user_id,username,display_name,role''', (inspector_id, user_id)).fetchone()
