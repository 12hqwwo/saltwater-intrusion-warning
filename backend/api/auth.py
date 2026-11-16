from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.auth.access_tokens import TOKEN_LIFETIME_SECONDS, issue_access_token
from backend.auth.current_user import AuthenticatedUser, require_role
from backend.auth.password_hashing import verify_password
from backend.auth.roles import Role
from backend.repositories import app_users


router = APIRouter(prefix='/auth', tags=['Đăng nhập'])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


def public_user(user):
    return {'username': user['username'], 'display_name': user['display_name'], 'role': user['role']}


@router.post('/login')
def login(payload: LoginRequest):
    user = app_users.find_active_user_by_username(payload.username.strip())
    if user is None or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(401, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return {'access_token': issue_access_token(user), 'token_type': 'Bearer',
            'expires_in': TOKEN_LIFETIME_SECONDS, 'user': public_user(user)}


@router.get('/me')
def me(user: AuthenticatedUser = Depends(require_role(Role.FIELD_STAFF, Role.INSPECTOR))):
    return public_user({'username': user.username, 'display_name': user.display_name, 'role': user.role})
