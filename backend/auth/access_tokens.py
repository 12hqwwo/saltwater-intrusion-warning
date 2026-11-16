import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException


TOKEN_LIFETIME_SECONDS = 8 * 60 * 60


def signing_key() -> str:
    key = os.getenv('WEBGIS_AUTH_SECRET', '')
    if len(key) < 32:
        raise HTTPException(503, 'Chưa cấu hình khóa ký phiên đăng nhập.')
    return key


def issue_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        'sub': str(user['user_id']), 'username': user['username'], 'role': user['role'],
        'iat': now, 'exp': now + timedelta(seconds=TOKEN_LIFETIME_SECONDS),
    }, signing_key(), algorithm='HS256')


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, signing_key(), algorithms=['HS256'], options={'require': ['sub', 'username', 'role', 'iat', 'exp']})
        if claims['role'] not in ('FIELD_STAFF', 'INSPECTOR'):
            raise ValueError('Invalid role')
        return claims
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(401, 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn.') from exc
