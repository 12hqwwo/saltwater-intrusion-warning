"""Download public candidate inputs into an isolated EC research snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/external/ec_feature_research_20261019"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "download_manifest.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    previous_files = {r["filename"]: r for r in previous.get("files", [])}
    # Match the existing meteorological extraction coordinates, not a new map pin.
    import csv
    with (ROOT / "data/raw/meteorology/openmeteo/openmeteo_all_stations_daily.csv").open(encoding="utf-8-sig") as stream:
        locations = {r["station"]: (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(stream)}
    jobs = [("noaa_nino34_anomaly.txt", "https://psl.noaa.gov/data/correlation/nina34.anom.data", "NOAA monthly Nino3.4 anomaly; retain source footer/version")]
    for station, (lat, lon) in sorted(locations.items()):
        query = dict(latitude=lat, longitude=lon, start_date="1985-01-01", end_date="2026-08-31",
                     daily="soil_moisture_0_to_100cm_mean,wind_speed_10m_mean,wind_direction_10m_dominant",
                     models="era5", timezone="Asia/Ho_Chi_Minh", wind_speed_unit="ms")
        jobs.append((f"era5_extra_{station}.json", "https://archive-api.open-meteo.com/v1/archive?" + urlencode(query),
                     "ERA5 reanalysis; grid proxy; delayed availability; not a forecast vintage"))
        query = dict(latitude=lat, longitude=lon, start_date="2021-01-01", end_date="2021-12-31",
                     daily="river_discharge")
        jobs.append((f"glofas_preview_{station}_2021.json", "https://flood-api.open-meteo.com/v1/flood?" + urlencode(query),
                     "API default model (version not echoed); spatial QA preview only, excluded from model comparisons"))
    records = []
    failed = False
    for filename, url, note in jobs:
        path = args.output / filename
        record = dict(filename=filename, url=url, note=note, accessed_at=datetime.now(timezone.utc).isoformat())
        try:
            if path.exists():
                content = path.read_bytes()
                record.update(previous_files.get(filename, {}))
                record["status"] = "CACHED"
            else:
                request = Request(url, headers={"User-Agent": "EC-feature-research/1.0"})
                with urlopen(request, timeout=90) as response:
                    content = response.read()
                    record["content_type"] = response.headers.get("Content-Type")
                if filename.endswith(".json"):
                    payload = json.loads(content)
                    if payload.get("error") or "daily" not in payload:
                        raise ValueError(f"API returned no daily series: {str(payload)[:250]}")
                path.write_bytes(content)
                record["status"] = "DOWNLOADED"
            record.update(sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
            if filename.endswith(".json"):
                payload = json.loads(content)
                record.update(returned_latitude=payload.get("latitude"), returned_longitude=payload.get("longitude"),
                              daily_units=payload.get("daily_units"), rows=len(payload["daily"]["time"]))
        except Exception as exc:
            failed = True
            record.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
            if isinstance(exc, HTTPError):
                record["response_error"] = exc.read(2048).decode("utf-8", errors="replace")
        records.append(record)
        manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), files=records)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{filename}: {record['status']} {record.get('error', '')} {record.get('response_error', '')}", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
