"""Download an auditable OpenStreetMap waterway extract for the Gò Công pilot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "gis" / "osm" / "go_cong_waterways_20261016.json"
DEFAULT_CONTEXT_OUTPUT = ROOT / "data" / "raw" / "gis" / "osm" / "go_cong_pilot5_context_20261016.json"
BBOX = (10.18, 106.42, 10.50, 106.82)  # south, west, north, east
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_FALLBACK_URL = "https://overpass.kumi.systems/api/interpreter"
PILOT5 = {
    "NM29": (10.26913888888889, 106.63777777777777),
    "NM30": (10.351166666666666, 106.6705),
    "NM31": (10.320555555555556, 106.70988888888888),
    "NM32": (10.40461111111111, 106.75544444444445),
    "NM34": (10.246972222222222, 106.69666666666667),
}


def fetch(query: str) -> dict:
    last_error = None
    for endpoint in (OVERPASS_URL, OVERPASS_FALLBACK_URL):
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
            headers={"User-Agent": "TLCN-GoCong-waterway-research/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                return json.load(response)
        except Exception as error:  # The public mirrors occasionally return 429/502.
            last_error = error
    raise last_error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--context-output", type=Path, default=DEFAULT_CONTEXT_OUTPUT)
    args = parser.parse_args()
    south, west, north, east = BBOX
    query = f'''[out:json][timeout:180];
way["waterway"~"^(river|canal|stream|drain|ditch|tidal_channel)$"]({south},{west},{north},{east});
out tags geom;'''
    payload = fetch(query)
    payload["tlcn_extract"] = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "overpass_url": OVERPASS_URL,
        "query": query,
        "bbox_wgs84": {"south": south, "west": west, "north": north, "east": east},
        "attribution": "© OpenStreetMap contributors; ODbL 1.0",
        "copyright_url": "https://www.openstreetmap.org/copyright",
        "purpose": "Working centerline network for the Gò Công EC pilot; not field-surveyed hydrography.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    context_parts = []
    for latitude, longitude in PILOT5.values():
        context_parts.extend([
            f'way(around:1000,{latitude},{longitude})["bridge"];',
            f'node(around:1000,{latitude},{longitude})["waterway"="sluice_gate"];',
            f'way(around:1000,{latitude},{longitude})["natural"="water"];',
        ])
    context_query = "[out:json][timeout:180];(" + "".join(context_parts) + ");out tags center geom;"
    context = fetch(context_query)
    context["tlcn_extract"] = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "overpass_url": OVERPASS_URL,
        "query": context_query,
        "pilot5": PILOT5,
        "attribution": "© OpenStreetMap contributors; ODbL 1.0",
    }
    args.context_output.parent.mkdir(parents=True, exist_ok=True)
    args.context_output.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")
    ways = [element for element in payload.get("elements", []) if element.get("type") == "way"]
    print(json.dumps({"output": str(args.output), "ways": len(ways),
                      "context_output": str(args.context_output),
                      "context_elements": len(context.get("elements", [])),
                      "downloaded_at_utc": payload["tlcn_extract"]["downloaded_at_utc"]}))


if __name__ == "__main__":
    main()
