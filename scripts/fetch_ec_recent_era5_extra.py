"""Fetch September 2026 ERA5 extra features at the existing My Tho grid point."""
from __future__ import annotations

import hashlib
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/ec_hydrology_current_20261029"
URL = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(dict(
    latitude=10.36, longitude=106.36, start_date="2026-09-01", end_date="2026-09-30",
    daily="soil_moisture_0_to_100cm_mean,wind_speed_10m_mean,wind_direction_10m_dominant",
    models="era5", timezone="Asia/Ho_Chi_Minh", wind_speed_unit="ms"))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(Request(URL, headers={"User-Agent": "TLCN-EC-hydrology/1.0"}),
                 timeout=90, context=context) as response:
        if response.url.split("/")[2] != "archive-api.open-meteo.com":
            raise ValueError("Unexpected redirect")
        blob = response.read(1_000_001)
    if len(blob) > 1_000_000:
        raise ValueError("ERA5 response too large")
    payload = json.loads(blob)
    if payload.get("error") or len(payload.get("daily", {}).get("time", [])) != 30:
        raise ValueError("Incomplete ERA5 September 2026")
    if payload["daily_units"].get("wind_speed_10m_mean") != "m/s":
        raise ValueError("Wind unit changed")
    (OUT / "era5_extra_MyTho_2026-09.json").write_bytes(blob)
    (OUT / "manifest.json").write_text(json.dumps(dict(source_url=URL,
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        sha256=hashlib.sha256(blob).hexdigest(), daily_rows=30,
        note="ERA5 reanalysis product, not a historical issue-time forecast vintage"),
        indent=2), encoding="utf-8")
    print("downloaded", len(blob), "bytes")


if __name__ == "__main__":
    main()
