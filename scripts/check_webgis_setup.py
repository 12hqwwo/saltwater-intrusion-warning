"""Windows setup diagnosis. Does not disclose passwords or modify PostgreSQL."""
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from run_webgis import load_local_env
    load_local_env()
    checks=[]
    def add(name,status,detail):
        checks.append(dict(name=name,status=status,detail=detail))
    add('local_env','PRESENT' if (ROOT/'.env').exists() else 'ABSENT',
        'PG* environment or PGPASSFILE may be used without .env. No secret values are reported.')
    for package in ['fastapi','starlette','uvicorn','psycopg','pandas','openpyxl']:
        try:
            add(package,'OK',importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            add(package,'MISSING','Install requirements-prototype.txt in this Python environment.')
    add('frontend_build','OK' if (ROOT/'frontend/dist/workspace.html').exists() else 'MISSING',
        'Run npm.cmd --prefix frontend run build after frontend changes.')
    try:
        from backend.research import validate_bundle
        import hashlib
        path=ROOT/'data/research/workspace.json'
        raw=path.read_bytes()
        manifest=json.loads(path.with_name('workspace_manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest()!=manifest['sha256']:
            raise ValueError('Checksum mismatch')
        data=validate_bundle(json.loads(raw))
        add('research_snapshot','OK',dict(observations=len(data['observations']),stations=len(data['stations'])))
    except Exception as exc:
        add('research_snapshot','FAILED',type(exc).__name__)
    try:
        from backend.database import read_connection
        with read_connection() as connection:
            row=connection.execute("SELECT current_database() AS database, EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis') AS postgis, to_regclass('webgis_research.snapshot') IS NOT NULL AS research_schema").fetchone()
            add('postgres','OK',dict(postgis=row['postgis'],research_schema=row['research_schema']))
    except Exception as exc:
        # Classify known errors, never copy raw connection strings into logs.
        detail='CONNECTION_OR_PERMISSION_ERROR'
        if 'no password supplied' in str(exc): detail='PASSWORD_NOT_CONFIGURED'
        elif 'password authentication failed' in str(exc): detail='AUTHENTICATION_FAILED'
        elif 'does not exist' in str(exc): detail='DATABASE_NOT_FOUND'
        add('postgres','FAILED',detail)
    report=dict(checked_at=datetime.now(timezone.utc).isoformat(),python=sys.version.split()[0],checks=checks)
    path=ROOT/'runs/setup_checks'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 1 if any(c['status'] in ('FAILED','MISSING') for c in checks) else 0


if __name__=='__main__':
    raise SystemExit(main())
