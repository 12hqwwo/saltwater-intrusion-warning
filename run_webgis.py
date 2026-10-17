"""Windows: python run_webgis.py --mode snapshot (serves built frontend too)."""
import argparse
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

def main():
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['snapshot', 'postgres'], default=os.getenv('WEBGIS_RESEARCH_MODE', 'snapshot'))
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    os.environ['WEBGIS_RESEARCH_MODE'] = args.mode
    from backend.main import app
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import RedirectResponse
    if (ROOT/'frontend/dist/research.html').is_file():
        @app.get('/')
        def start():
            return RedirectResponse('/research.html')
        app.mount('/', StaticFiles(directory=ROOT/'frontend/dist', html=True), name='webgis')
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port)

if __name__ == '__main__':
    main()
