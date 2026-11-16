from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from backend.auth.access_tokens import decode_access_token
from backend.auth.roles import Role
from backend.repositories import app_users
from backend.security import actor


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    username: str
    display_name: str
    role: Role


def read_optional_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(401, 'Cần phiên đăng nhập Bearer hợp lệ.')
    claims = decode_access_token(token)
    try:
        UUID(claims['sub'])
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(401, 'Phiên đăng nhập không hợp lệ.') from exc
    user = app_users.find_active_user_by_id(claims['sub'])
    if user is None or user.get('is_active') is False or user['username'] != claims['username'] or user['role'] != claims['role']:
        raise HTTPException(401, 'Tài khoản không còn hiệu lực.')
    identity = AuthenticatedUser(str(user['user_id']), user['username'], user['display_name'], Role(user['role']))
    actor.set(f'USER:{identity.username}')
    return identity


def require_role(*roles: Role) -> Callable:
    def check(user: AuthenticatedUser | None = Depends(read_optional_user)) -> AuthenticatedUser:
        if user is None:
            raise HTTPException(401, 'Cần đăng nhập để thực hiện thao tác này.')
        if user.role not in roles:
            raise HTTPException(403, 'Tài khoản không có quyền thực hiện thao tác này.')
        return user
    return check
