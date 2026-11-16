from fastapi import HTTPException
from contextlib import contextmanager
from backend.repositories.dss_storage import StorageDisabled, write_connection


@contextmanager
def auth_connection():
    try:
        with write_connection() as conn:
            yield conn
    except StorageDisabled as exc:
        raise HTTPException(503, 'Đăng nhập cần PostgreSQL và tài khoản ghi DSS đã cấu hình.') from exc


def find_active_user_by_username(username: str):
    with auth_connection() as conn:
        return conn.execute('''SELECT user_id,username,display_name,password_hash,role,is_active
            FROM webgis_security.app_user WHERE username=%s AND is_active=true''', (username,)).fetchone()


def find_active_user_by_id(user_id: str):
    with auth_connection() as conn:
        return conn.execute('''SELECT user_id,username,display_name,role,is_active
            FROM webgis_security.app_user WHERE user_id=%s::uuid AND is_active=true''', (user_id,)).fetchone()
