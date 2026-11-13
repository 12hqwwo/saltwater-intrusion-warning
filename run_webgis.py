"""Serve the WebGIS application and API from one local process."""
import argparse
import ipaddress
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_local_env():
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep or not key.strip().replace('_', '').isalnum():
                raise ValueError('Invalid .env entry; use KEY=value, no shell expressions.')
            os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def port_number(value):
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError('Port must be between 1 and 65535.')
    return port


def bind_host(value):
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Host must be an IPv4 or IPv6 address.') from exc


def validate_lan_host(host):
    address = ipaddress.ip_address(host)
    if address.is_loopback:
        return
    allowed = [item.strip() for item in os.getenv('WEBGIS_ALLOWED_HOSTS', '').split(',') if item.strip()]
    external = [item for item in allowed if item not in {'localhost', '127.0.0.1', '[::1]', 'testserver'}]
    if not os.getenv('WEBGIS_WRITE_API_KEY') or not external or '*' in allowed:
        raise ValueError('LAN binding requires a write API key and explicit WEBGIS_ALLOWED_HOSTS.')
    if not address.is_unspecified and host not in allowed and f'[{host}]' not in allowed:
        raise ValueError('Bind host must appear in WEBGIS_ALLOWED_HOSTS.')


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['snapshot', 'postgres'], default=os.getenv('WEBGIS_RESEARCH_MODE', 'postgres'))
    parser.add_argument('--host', type=bind_host, default='127.0.0.1')
    parser.add_argument('--port', type=port_number, default=8000)
    parser.add_argument('--api-only', action='store_true', help='Run without the built frontend.')
    args = parser.parse_args()
    try:
        validate_lan_host(args.host)
    except ValueError as exc:
        parser.error(str(exc))
    os.environ['WEBGIS_RESEARCH_MODE'] = args.mode
    from backend.security import enabled
    if not enabled():
        parser.error('Security must be enabled. Run scripts/setup_security.py --apply first.')
    if args.mode == 'postgres':
        from backend.database import read_connection
        with read_connection() as conn:
            conn.execute('SELECT 1')
    from backend.main import app
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import RedirectResponse
    frontend = ROOT / 'frontend' / 'dist'
    if not args.api_only:
        if not (frontend / 'workspace.html').is_file():
            parser.error('Frontend build missing. Run npm.cmd --prefix frontend run build, or use --api-only.')

        @app.get('/')
        def start():
            return RedirectResponse('/workspace.html')

        app.mount('/', StaticFiles(directory=frontend, html=True), name='webgis')
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, timeout_keep_alive=5)

if __name__ == '__main__':
    main()
