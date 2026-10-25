"""Optional API key and browser request boundaries; DB roles enforce data privileges."""
import hmac
import os
from contextvars import ContextVar
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

actor = ContextVar('webgis_actor', default='LOCAL_APPLICATION')
WRITE_PATHS = {'/api/v1/workspace/gate-drafts', '/api/v1/workspace/multivariate/history'}


def enabled():
    return os.getenv('WEBGIS_SECURITY_ENABLED', 'true').lower() == 'true'


def same_origin(request):
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/')} | {
        item.strip() for item in os.getenv('WEBGIS_CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173').split(',') if item.strip()}
    if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin not in allowed):
        raise HTTPException(403, 'Nguồn yêu cầu không được phép.')


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not enabled():  # Only offline, isolated regression fixtures opt out.
            return await call_next(request)
        try:
            writing = request.method == 'POST' and request.url.path.rstrip('/') in WRITE_PATHS
            if request.url.path.startswith('/api/') and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
                same_origin(request)
            key = os.getenv('WEBGIS_WRITE_API_KEY', '')
            if writing and key and not hmac.compare_digest(request.headers.get('x-api-key', '').encode(), key.encode()):
                raise HTTPException(401, 'API key ghi dữ liệu không hợp lệ hoặc còn thiếu.')
            marker = actor.set('API_KEY_CLIENT' if writing and key else 'LOCAL_APPLICATION')
            try:
                response = await call_next(request)
            finally:
                actor.reset(marker)
        except HTTPException as exc:
            response = JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # External map tiles require a Referer; send only the origin cross-site,
        # never the page path/query, and send nothing on an HTTPS downgrade.
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
