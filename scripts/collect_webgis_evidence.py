"""Capture actual API responses from the running local WebGIS for the report."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError, URLError


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--include-database', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1] / 'runs/webgis_evidence' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root.mkdir(parents=True, exist_ok=False)
    records = []
    def fetch(endpoint, name):
        try:
            with urlopen(args.url.rstrip('/') + endpoint, timeout=20) as response:
                content, status = response.read(), response.status
        except HTTPError as exc:
            content, status = exc.read(), exc.code
        except (URLError, TimeoutError, OSError) as exc:
            # Preserve a failed check as evidence, including when server is down.
            content = json.dumps({'status':'CONNECTION_FAILED','error_type':type(exc).__name__}).encode('utf-8')
            status = None
        (root / name).write_bytes(content)
        records.append(dict(endpoint=endpoint, file=name, http_status=status))
        return json.loads(content) if name.endswith('.json') and status == 200 else None
    fetch('/api/v1/app-health', 'app_health.json')
    summary = fetch('/api/v1/research/summary', 'research_summary.json')
    fetch('/api/v1/research/stations', 'stations.geojson')
    fetch('/api/v1/research/gates', 'gate_catalog.json')
    fetch('/api/v1/research/intake', 'intake_summary.json')
    fetch('/api/v1/research/intake/coverage', 'intake_coverage.json')
    fetch('/api/v1/research/intake/measurement-points', 'intake_points.json')
    fetch('/api/v1/research/intake/observations?point=ST_SOAIRAP_RACHBANG%3A%3AINTERIOR_0M', 'intake_rachbang_0m.json')
    if summary:
        for ex in summary['experiments']:
            eid = ex['experiment_id']
            fetch('/api/v1/research/experiments/' + eid, eid + '.json')
            for file in ['metrics.csv', 'predictions.csv', 'run_manifest.json', 'split_manifest.csv']:
                fetch('/api/v1/research/artifacts/' + eid + '/' + file, eid + '_' + file)
    if args.include_database:
        fetch('/api/v1/health', 'database_health.json')
        fetch('/api/v1/stations', 'database_stations.geojson')
        fetch('/api/v1/research/database-gates', 'database_gates.json')
    (root / 'capture_manifest.json').write_text(json.dumps(dict(captured_at=datetime.now(timezone.utc).isoformat(), records=records), ensure_ascii=False, indent=2), encoding='utf-8')
    print(root)
    print('HTTP failures:', sum(r['http_status'] != 200 for r in records))
    return 1 if any(r['http_status'] != 200 for r in records) else 0


if __name__ == '__main__':
    raise SystemExit(main())
