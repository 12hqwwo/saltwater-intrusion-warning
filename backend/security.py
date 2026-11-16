import os
from contextvars import ContextVar
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

actor = ContextVar('webgis_actor', default='LOCAL_APPLICATION')
REFERRER_POLICY_ORIGIN_ONLY_CROSS_SITE = 'strict-origin-when-cross-origin'


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
        if not enabled():
            return await call_next(request)
        try:
            if request.url.path.startswith('/api/') and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
                same_origin(request)
            marker = actor.set('LOCAL_APPLICATION')
            try:
                response = await call_next(request)
            finally:
                actor.reset(marker)
        except HTTPException as exc:
            response = JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = REFERRER_POLICY_ORIGIN_ONLY_CROSS_SITE
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
