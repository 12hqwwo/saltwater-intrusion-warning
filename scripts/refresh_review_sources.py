"""Retrieve original sources without replacing originals; retain each failure."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.fetch_public_research_data import download, write_json

ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / 'data/external' / datetime.now(timezone.utc).strftime('source_review_%Y%m%dT%H%M%SZ')
    out.mkdir(exist_ok=False)
    raw = ROOT / 'data/external/ec_recovery_20261011'
    manifest = json.loads((raw / 'ec_recovery_manifest.json').read_text(encoding='utf-8'))
    jobs = [(s['url'], out / s['file'], s['sha256']) for s in manifest['sources']]
    jobs += [('https://thuyloitiengiang.vn/en/web/thuyloitiengiang/chi-tiet-tin-tuc?id=522066', out/'tiengiang_20261013.html', None),
             ('https://vienthuysan2.org.vn/', out/'ria2_index.html', None),
             ('https://www.siwrr.org.vn/docs/2023/files/20251124-Ban-tin-mua-kho-2025-2026-DB-HTVH-CL-CB-24-11-2025.pdf',out/'siwrr_forecast.pdf',None)]
    def fetch(job):
        url, path, sha = job
        try:
            result = download(url, path, sha)
            if sha and not (raw/path.name).exists():
                (raw/path.name).write_bytes(path.read_bytes())
            return dict(result, classification='SOURCE_DOCUMENT_NOT_AUTOMATICALLY_OBSERVATIONS')
        except Exception as exc:
            return dict(url=url, attempted_at=datetime.now(timezone.utc).isoformat(), status='BLOCKED', error_type=type(exc).__name__, error=str(exc))
    result = list(ThreadPoolExecutor(max_workers=4).map(fetch, jobs))
    write_json(out/'manifest.json', result)
    print(json.dumps(dict(output=str(out), downloads=sum('sha256' in r for r in result), failures=sum('error' in r for r in result))))

if __name__ == '__main__':
    main()
