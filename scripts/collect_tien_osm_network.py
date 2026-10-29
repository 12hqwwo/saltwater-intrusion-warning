"""Fetch named river/canal OSM ways in the Tien corridor as provisional topology."""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/tien_osm_network_20261029"
ENDPOINT = "https://overpass.private.coffee/api/interpreter"
BBOX = "10.18,105.19,10.87,106.78"  # south,west,north,east; Tien corridor and estuary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", action="store_true")
    args = parser.parse_args()
    query = (f'[out:json][timeout:120];(way["waterway"="river"]({BBOX});'
             f'way["waterway"="canal"]["name"]({BBOX}););'
             + ("out count;" if args.count else "out geom;"))
    url = ENDPOINT + "?" + urlencode({"data": query})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(Request(url, headers={"User-Agent": "TLCN-academic-river-topology/1.0"}),
                 timeout=160, context=context) as response:
        if response.url.split("/")[2] != "overpass.private.coffee":
            raise ValueError("Unexpected redirect")
        blob = response.read(30_000_001)
    if len(blob) > 30_000_000:
        raise ValueError("Overpass result too large; refine bounding box")
    payload = json.loads(blob)
    if args.count:
        print(payload["elements"])
        return
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "overpass_raw.json").write_bytes(blob)
    ways = [x for x in payload["elements"] if x.get("type") == "way" and len(x.get("geometry", [])) >= 2]
    features = [dict(type="Feature", id=str(x["id"]),
                     properties=dict(osm_id=x["id"], waterway=x["tags"].get("waterway"),
                                     name=x["tags"].get("name"), direction_verified=False),
                     geometry=dict(type="LineString", coordinates=[[p["lon"],p["lat"]]
                                                            for p in x["geometry"]])) for x in ways]
    (OUT / "waterways.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=features),
                                                      ensure_ascii=False), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps(dict(source=ENDPOINT, query=query,
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        raw_sha256=hashlib.sha256(blob).hexdigest(), way_count=len(ways),
        river_count=sum(x["tags"].get("waterway") == "river" for x in ways),
        named_canal_count=sum(x["tags"].get("waterway") == "canal" for x in ways),
        license="OpenStreetMap ODbL; attribution required",
        warning="Unverified flow direction, connectivity, completeness, gates and hydraulic cross sections"),
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ways={len(ways)} bytes={len(blob)}")


if __name__ == "__main__":
    main()
