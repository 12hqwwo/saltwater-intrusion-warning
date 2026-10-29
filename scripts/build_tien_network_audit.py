"""Build a provisional Tien centerline and station projection from saved OSM ways."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/biengioi/tien_osm_waterways_source.json"
INVENTORY = ROOT / "data/external/tien_multisite_20261029_verified/inventory.json"
OUT = ROOT / "outputs/tien_network_20261029"
SITES = ["019803", "019804", "019805", "019827", "985203"]
LAT0 = 10.5
KM_LAT = 111.195
KM_LON = 111.195 * math.cos(math.radians(LAT0))


def xy(point):
    return point["lon"] * KM_LON, point["lat"] * KM_LAT


def distance(a, b):
    ax, ay = xy(a)
    bx, by = xy(b)
    return math.hypot(bx-ax, by-ay)


def project(point, a, b):
    px, py = xy(point)
    ax, ay = xy(a)
    bx, by = xy(b)
    vx, vy = bx-ax, by-ay
    fraction = max(0.0, min(1.0, ((px-ax)*vx+(py-ay)*vy)/(vx*vx+vy*vy)))
    return math.hypot(px-(ax+fraction*vx), py-(ay+fraction*vy)), fraction


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    ways = source["elements"]
    if len(ways) != 5:
        raise ValueError("Review changed OSM path")
    gaps = [distance(a["geometry"][-1], b["geometry"][0]) for a,b in zip(ways,ways[1:])]
    if max(gaps) > .01:
        raise ValueError("OSM ways not connected within 10 m")
    features = []
    segments = []
    chainage = 0.0
    for way in ways:
        points = way["geometry"]
        features.append(dict(type="Feature", properties=dict(osm_way_id=way["id"],
            name=way.get("tags",{}).get("name"), direction_verified=False),
            geometry=dict(type="LineString", coordinates=[[p["lon"],p["lat"]] for p in points])))
        for a,b in zip(points,points[1:]):
            length = distance(a,b)
            segments.append((a,b,chainage,length,way["id"]))
            chainage += length
    sites = []
    for code in SITES:
        matches = [x for x in inventory if x.get("stationCode") == code and
                   x.get("latitude") is not None and x.get("longitude") is not None]
        if not matches:
            raise ValueError("Missing station coordinate " + code)
        station = matches[0]
        point = dict(lon=station["longitude"], lat=station["latitude"])
        candidates = [(d, start+fraction*length, way_id) for a,b,start,length,way_id in segments
                      for d,fraction in [project(point,a,b)]]
        d, along, way_id = min(candidates)
        sites.append(dict(station_code=code, station_name=station["stationName"],
            latitude=point["lat"], longitude=point["lon"],
            projected_chainage_km=round(along,3), distance_to_centerline_km=round(d,3),
            nearest_osm_way_id=way_id, status="PROVISIONAL_GEOMETRY_ONLY"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "centerline.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=features),
        ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "station_chainage.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=sites[0].keys())
        writer.writeheader(); writer.writerows(sites)
    (OUT / "topology_audit.json").write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        inventory_sha256=hashlib.sha256(INVENTORY.read_bytes()).hexdigest(),
        way_count=len(ways), consecutive_endpoint_gaps_km=gaps,
        path_length_km=chainage, station_count=len(sites),
        limitations=["Only five OSM ways and one Cua Tieu route; distributary and canal branches missing",
                     "OSM geometry order is not verified flow direction",
                     "Nearest line projection is not station hydraulic connectivity",
                     "No bathymetry, cross sections, gates, rating curves or travel time"]), indent=2), encoding="utf-8")
    print("path_km",round(chainage,1),"gaps_km",gaps)
    for row in sites: print(row)


if __name__ == "__main__":
    main()
