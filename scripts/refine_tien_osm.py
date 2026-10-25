"""Build a local, attributed Tien corridor from cached real OSM river ways.

Use --refresh to download OSM again. Overpass is tried first; the official OSM
API supplies the same waterway ways when Overpass is unavailable. No live map
requests or network dependencies are added to the web application.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/biengioi/tien_osm_waterways_source.json'
CORRIDOR = ROOT / 'data/biengioi/tien_river_corridor.geojson'
# These five OSM ways form a node-connected main Tien/My Tho/Cua Tieu path.
WAYS = [857503172, 447717911, 1154885448, 51199789, 541622343]
STATION_BANKS = {'MRC_VN_019803': [105.233, 10.8], 'MRC_VN_019805': [106.36, 10.35]}


def request(url, data=None):
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'SaltwaterWebGIS-GeometryRefinement/1.0',
    })
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read()


def xml_ways(raw):
    root = ET.fromstring(raw)
    nodes = {int(n.attrib['id']): {'lon': float(n.attrib['lon']), 'lat': float(n.attrib['lat'])}
             for n in root.findall('node')}
    ways = []
    for way in root.findall('way'):
        tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
        if tags.get('waterway') != 'river':
            continue
        ids = [int(n.attrib['ref']) for n in way.findall('nd')]
        geometry = [nodes[i] for i in ids]
        if any(105.15 <= p['lon'] <= 106.85 and 10.1 <= p['lat'] <= 10.95 for p in geometry):
            ways.append(dict(type='way', id=int(way.attrib['id']), nodes=ids, tags=tags, geometry=geometry))
    return ways


def fetch_source():
    query = '[out:json][timeout:25];way["waterway"="river"]["name"~"Tiền|Tien|Mekong|Mỹ Tho|Cửa Tiểu",i](10.20,105.20,10.85,106.78);out body geom;'
    overpass = 'https://overpass-api.de/api/interpreter'
    try:
        data = json.loads(request(overpass, urllib.parse.urlencode({'data': query}).encode()))
        if set(WAYS) <= {item['id'] for item in data.get('elements', [])}:
            return dict(source_url=overpass, query=query, elements=data['elements'])
    except (OSError, ValueError):
        print('Overpass unavailable/incomplete; fetching official OSM waterway data.')
    urls = [
        'https://api.openstreetmap.org/api/0.6/relation/215354/full',
        'https://api.openstreetmap.org/api/0.6/map?bbox=106.125,10.27,106.15,10.295',
        'https://api.openstreetmap.org/api/0.6/map?bbox=106.433,10.299,106.453,10.319',
    ]
    ways = {}
    for url in urls:
        ways.update({way['id']: way for way in xml_ways(request(url))})
    return dict(source_url=urls[0], additional_source_urls=urls[1:], elements=list(ways.values()))


def xy(point):
    return [point[0] * 111195 * math.cos(math.radians(10.5)), point[1] * 111195]


def distance(a, b):
    return math.dist(xy(a), xy(b))


def point_segment_distance(point, a, b):
    p, a, b = map(xy, (point, a, b))
    delta = [b[k] - a[k] for k in range(2)]
    length = sum(v * v for v in delta)
    t = max(0, min(1, sum((p[k] - a[k]) * delta[k] for k in range(2)) / length)) if length else 0
    return math.dist(p, [a[k] + t * delta[k] for k in range(2)])


def simplify(points, tolerance):
    if len(points) <= 2:
        return points
    index = max(range(1, len(points) - 1), key=lambda i: point_segment_distance(points[i], points[0], points[-1]))
    if point_segment_distance(points[index], points[0], points[-1]) <= tolerance:
        return [points[0], points[-1]]
    return simplify(points[:index + 1], tolerance)[:-1] + simplify(points[index:], tolerance)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    source = fetch_source() if args.refresh or not SOURCE.exists() else json.loads(SOURCE.read_text(encoding='utf-8'))
    source.setdefault('retrieved_at', datetime.now(timezone.utc).isoformat())
    source['copyright'] = 'OpenStreetMap contributors; ODbL 1.0; https://www.openstreetmap.org/copyright'
    indexed = {way['id']: way for way in source['elements']}
    source['elements'] = [indexed[wid] for wid in WAYS]
    points, previous_node = [], None
    for way in source['elements']:
        assert previous_node is None or previous_node == way['nodes'][0], 'OSM ways must share an actual node.'
        coords = [[p['lon'], p['lat']] for p in way['geometry']]
        assert not points or points[-1] == coords[0], 'Disconnected OSM geometry.'
        points.extend(coords[bool(points):])
        previous_node = way['nodes'][-1]
    def project_station(bank):
        # Orthogonal foot in a local metric equirectangular plane, not lon/lat degrees.
        scale_x, scale_y = 111195 * math.cos(math.radians(bank[1])), 111195
        best = None
        for i, (a, b) in enumerate(zip(points, points[1:])):
            ax, ay = (a[0] - bank[0]) * scale_x, (a[1] - bank[1]) * scale_y
            dx, dy = (b[0] - a[0]) * scale_x, (b[1] - a[1]) * scale_y
            t = max(0, min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
            offset = math.hypot(ax + t * dx, ay + t * dy)
            point = [round(a[k] + t * (b[k] - a[k]), 8) for k in range(2)]
            if best is None or offset < best[0]:
                best = offset, i, point, a, b
        offset, index, point, a, b = best
        return index, dict(bank_coordinate=bank, projected_coordinate=point,
                           projection_method='ORTHOGONAL_NEAREST_OSM_SEGMENT_LOCAL_METRIC',
                           source_segment=[a, b], distance_to_axis_m=round(offset, 3))
    (start, upstream_anchor), (middle, downstream_anchor) = [project_station(bank) for bank in STATION_BANKS.values()]
    assert start < middle < len(points) - 1
    anchors = [upstream_anchor['projected_coordinate'], downstream_anchor['projected_coordinate'], points[-1]]
    upstream = [anchors[0]] + points[start + 1:middle + 1] + [anchors[1]]
    downstream = [anchors[1]] + points[middle + 1:]
    # A projection landing exactly on an OSM node must not duplicate that vertex.
    upstream = [p for i, p in enumerate(upstream) if i == 0 or p != upstream[i - 1]]
    downstream = [p for i, p in enumerate(downstream) if i == 0 or p != downstream[i - 1]]
    low, high = 0.0, 1000.0
    for _ in range(35):
        tolerance = (low + high) / 2
        count = len(simplify(upstream, tolerance)) + len(simplify(downstream, tolerance)) - 1
        if count > 175:
            low = tolerance
        else:
            high = tolerance
    coords = simplify(upstream, high)[:-1] + simplify(downstream, high)
    assert 120 <= len(coords) <= 180
    assert coords[0] == anchors[0] and coords[-1] == anchors[-1] and anchors[1] in coords
    assert all(a != b for a, b in zip(coords, coords[1:]))
    source_bytes = (json.dumps(source, ensure_ascii=True, indent=2) + '\n').encode()
    data = json.loads(CORRIDOR.read_text(encoding='utf-8'))
    main = next(f for f in data['features'] if f['properties']['id'] == 'TIEN_MAIN')
    main['geometry']['coordinates'] = coords
    provenance = dict(source='OPENSTREETMAP_WATERWAY_WAYS', source_file=str(SOURCE.relative_to(ROOT)).replace('\\', '/'),
                      source_sha256=hashlib.sha256(source_bytes).hexdigest(), osm_way_ids=WAYS,
                      license='ODbL-1.0', attribution='OpenStreetMap contributors',
                      vertex_count=len(coords), simplification_tolerance_m=round(high, 3),
                      station_axis_anchors=dict(zip(STATION_BANKS, [upstream_anchor, downstream_anchor])),
                      estuary_osm_endpoint=anchors[-1],
                      anchor_note='Station bank pins remain unchanged; simulation chainages 0/125 use orthogonal projections onto OSM. Chainage 175 ends at the actual OSM Cua Tieu mouth, with no artificial extension.')
    main['properties'].update(geometry_status='OSM_DERIVED_PROJECTED_STATION_ANCHORS',
                              geometry_note='Real OSM Tien/My Tho/Cua Tieu ways, simplified locally; station axis anchors are orthogonally projected onto source segments and the mouth is the actual OSM endpoint.',
                              geometry_provenance=provenance)
    data['metadata']['main_axis_provenance'] = provenance
    for feature in data['features']:
        props = feature['properties']
        if 'gate_code' not in props:
            continue
        path, gate = feature['geometry']['coordinates'], props['gate_coordinate']
        old_gate = path[2][:]
        index = min(range(len(coords)), key=lambda i: distance(coords[i], gate))
        props['connection_main_index'] = index
        props['connection_coordinate'] = coords[index][:]
        path[0] = coords[index][:]
        path[1] = [round((path[0][k] + gate[k]) / 2, 9) for k in range(2)]
        assert props['gate_path_index'] == 2 and path[2] == gate == old_gate
    SOURCE.write_bytes(source_bytes)
    CORRIDOR.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(osm_ways=WAYS, vertices=len(coords), simplification_tolerance_m=round(high, 3),
                          projected_station_anchors=anchors[:2], estuary=anchors[-1], canal_connections=10)))


if __name__ == '__main__':
    main()
