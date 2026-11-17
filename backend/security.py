import os
import time
from contextvars import ContextVar
from threading import Lock
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

actor = ContextVar('webgis_actor', default='LOCAL_APPLICATION')
REFERRER_POLICY_ORIGIN_ONLY_CROSS_SITE = 'strict-origin-when-cross-origin'

RATE_LIMITED_PATHS = {'/api/v1/auth/login', '/api/v1/auth/register'}
_rate_limit_lock = Lock()
_rate_limit_state: dict[tuple[str, str], tuple[float, int]] = {}


def enabled():
    return os.getenv('WEBGIS_SECURITY_ENABLED', 'true').lower() == 'true'


def reset_rate_limits():
    with _rate_limit_lock:
        _rate_limit_state.clear()


def _enforce_rate_limit(client_ip, path):
    window_seconds = int(os.getenv('WEBGIS_AUTH_RATE_LIMIT_WINDOW_SECONDS', '60'))
    max_attempts = int(os.getenv('WEBGIS_AUTH_RATE_LIMIT_MAX_ATTEMPTS', '10'))
    key = (client_ip, path)
    now = time.monotonic()
    with _rate_limit_lock:
        window_start, count = _rate_limit_state.get(key, (now, 0))
        if now - window_start >= window_seconds:
            window_start, count = now, 0
        count += 1
        _rate_limit_state[key] = (window_start, count)
    if count > max_attempts:
        retry_after = max(1, int(window_seconds - (now - window_start)))
        raise HTTPException(429, 'Quá nhiều yêu cầu, thử lại sau.', headers={'Retry-After': str(retry_after)})


def same_origin(request):
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/')} | {
        item.strip() for item in os.getenv('WEBGIS_CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173').split(',') if item.strip()}
    if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin not in allowed):
        raise HTTPException(403, 'Nguồn yêu cầu không được phép.')


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not enabled():
            return await call_next(request)
        try:
            if request.url.path.startswith('/api/') and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
                same_origin(request)
            if request.method == 'POST' and request.url.path in RATE_LIMITED_PATHS:
                client_ip = request.client.host if request.client else 'unknown'
                _enforce_rate_limit(client_ip, request.url.path)
            application_actor = 'LOCAL_APPLICATION'
            authorization = request.headers.get('authorization', '')
            if authorization.lower().startswith('bearer '):
                from backend.auth.access_tokens import decode_access_token
                from backend.repositories import app_users
                try:
                    claims = decode_access_token(authorization[7:])
                    user = app_users.find_active_user_by_id(claims['sub'])
                    if user is not None and user.get('is_active') is not False \
                            and user['username'] == claims['username'] and user['role'] == claims['role']:
                        application_actor = f"USER:{claims['username']}"
                except HTTPException:
                    pass
            marker = actor.set(application_actor)
            try:
                response = await call_next(request)
            finally:
                actor.reset(marker)
        except HTTPException as exc:
            response = JSONResponse({'detail': exc.detail}, status_code=exc.status_code, headers=exc.headers)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = REFERRER_POLICY_ORIGIN_ONLY_CROSS_SITE
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
