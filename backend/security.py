import hmac
import os
import time
from contextvars import ContextVar
from threading import Lock
import psycopg
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

actor = ContextVar('webgis_actor', default='LOCAL_APPLICATION')
REFERRER_POLICY_ORIGIN_ONLY_CROSS_SITE = 'strict-origin-when-cross-origin'

RATE_LIMITED_PATHS = {'/api/v1/auth/login', '/api/v1/auth/register'}
_rate_limit_lock = Lock()
_rate_limit_state: dict[tuple[str, ...], tuple[float, int]] = {}
_RATE_LIMIT_WINDOW_SECONDS = max(1, int(os.getenv('WEBGIS_AUTH_RATE_LIMIT_WINDOW_SECONDS', '60')))
_RATE_LIMIT_MAX_ATTEMPTS = max(1, int(os.getenv('WEBGIS_AUTH_RATE_LIMIT_MAX_ATTEMPTS', '10')))
_RATE_LIMIT_USERNAME_MAX_ATTEMPTS = max(1, int(os.getenv('WEBGIS_AUTH_USERNAME_RATE_LIMIT_MAX_ATTEMPTS', '5')))
_RATE_LIMIT_MAX_KEYS = 10_000
WRITE_PATHS = {'/api/v1/workspace/gate-drafts', '/api/v1/workspace/multivariate/history',
               '/api/v1/research/gate-drafts', '/api/v1/research/multivariate/history',
               '/api/v1/multivariate/history', '/api/v1/forecast-issues',
               '/api/v1/field-measurements'}


def enabled():
    return os.getenv('WEBGIS_SECURITY_ENABLED', 'true').lower() == 'true'


def reset_rate_limits():
    with _rate_limit_lock:
        _rate_limit_state.clear()


def _enforce_rate_limit(key, max_attempts):
    now = time.monotonic()
    with _rate_limit_lock:
        if len(_rate_limit_state) >= _RATE_LIMIT_MAX_KEYS and key not in _rate_limit_state:
            expired = [item for item, (started, _) in _rate_limit_state.items()
                       if now - started >= _RATE_LIMIT_WINDOW_SECONDS]
            for item in expired:
                del _rate_limit_state[item]
            if len(_rate_limit_state) >= _RATE_LIMIT_MAX_KEYS:
                oldest = min(_rate_limit_state, key=lambda item: _rate_limit_state[item][0])
                del _rate_limit_state[oldest]
        window_start, count = _rate_limit_state.get(key, (now, 0))
        if now - window_start >= _RATE_LIMIT_WINDOW_SECONDS:
            window_start, count = now, 0
        count += 1
        _rate_limit_state[key] = (window_start, count)
    if count > max_attempts:
        retry_after = max(1, int(_RATE_LIMIT_WINDOW_SECONDS - (now - window_start)))
        raise HTTPException(429, 'Quá nhiều yêu cầu, thử lại sau.', headers={'Retry-After': str(retry_after)})


def enforce_login_username_rate_limit(client_ip: str, username: str):
    _enforce_rate_limit(('login-user', client_ip, username.strip().lower()), _RATE_LIMIT_USERNAME_MAX_ATTEMPTS)


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
                _enforce_rate_limit(('ip', client_ip, request.url.path), _RATE_LIMIT_MAX_ATTEMPTS)
            application_actor = 'LOCAL_APPLICATION'
            authorization = request.headers.get('authorization', '')
            if authorization.lower().startswith('bearer '):
                from backend.auth.access_tokens import decode_access_token
                from backend.repositories import app_users
                try:
                    claims = decode_access_token(authorization[7:])
                    user = await run_in_threadpool(app_users.find_active_user_by_id, claims['sub'])
                    if user is not None and user.get('is_active') is not False \
                            and user['username'] == claims['username'] and user['role'] == claims['role']:
                        application_actor = f"USER:{claims['username']}"
                except (HTTPException, psycopg.Error):
                    pass
            writing = request.method == 'POST' and request.url.path.rstrip('/') in WRITE_PATHS
            key = os.getenv('WEBGIS_WRITE_API_KEY', '')
            if writing and key and application_actor == 'LOCAL_APPLICATION':
                if not hmac.compare_digest(request.headers.get('x-api-key', '').encode(), key.encode()):
                    raise HTTPException(401, 'API key ghi dữ liệu không hợp lệ hoặc còn thiếu.')
                application_actor = 'API_KEY_CLIENT'
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
