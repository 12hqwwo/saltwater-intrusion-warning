from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from psycopg.errors import UniqueViolation
from uuid import UUID

from backend.auth.access_tokens import TOKEN_LIFETIME_SECONDS, issue_access_token
from backend.auth.current_user import AuthenticatedUser, require_role
from backend.auth.password_hashing import hash_password, verify_password
from backend.auth.roles import Role
from backend.repositories import app_users
import os


router = APIRouter(prefix='/auth', tags=['Đăng nhập'])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3, max_length=64, pattern=r'^[A-Za-z0-9._-]+$')
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=1024)


def public_user(user):
    return {'username': user['username'], 'display_name': user['display_name'], 'role': user['role']}


@router.post('/register', status_code=201)
def register(payload: RegistrationRequest):
    if os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot').lower() != 'postgres':
        raise HTTPException(503, 'Đăng ký chỉ khả dụng khi dùng PostgreSQL.')
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(422, 'Tên hiển thị không được để trống.')
    try:
        app_users.create_pending_user(payload.username, display_name, hash_password(payload.password))
    except UniqueViolation as exc:
        raise HTTPException(409, 'Tên đăng nhập đã được sử dụng.') from exc
    return {'message': 'Đã nhận đăng ký. Tài khoản sẽ dùng được sau khi người kiểm tra duyệt.'}


@router.post('/login')
def login(payload: LoginRequest):
    if os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot').lower() != 'postgres':
        raise HTTPException(503, 'Đăng nhập chỉ khả dụng khi dùng PostgreSQL.')
    user = app_users.find_active_user_by_username(payload.username.strip())
    if user is None or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(401, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return {'access_token': issue_access_token(user), 'token_type': 'Bearer',
            'expires_in': TOKEN_LIFETIME_SECONDS, 'user': public_user(user)}


@router.get('/me')
def me(user: AuthenticatedUser = Depends(require_role(Role.FIELD_STAFF, Role.INSPECTOR))):
    return public_user({'username': user.username, 'display_name': user.display_name, 'role': user.role})


@router.get('/pending')
def pending_registrations(user: AuthenticatedUser = Depends(require_role(Role.INSPECTOR))):
    return {'items': app_users.list_pending_users()}


@router.post('/pending/{user_id}/approve')
def approve_registration(user_id: UUID, user: AuthenticatedUser = Depends(require_role(Role.INSPECTOR))):
    approved = app_users.approve_pending_user(user_id, UUID(user.user_id))
    if approved is None:
        raise HTTPException(404, 'Không tìm thấy đăng ký đang chờ duyệt.')
    return {'user': public_user(approved)}
