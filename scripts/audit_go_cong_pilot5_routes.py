"""Export inspectable pilot-5 shortest paths and KML/OSM crossings to GeoJSON."""

from __future__ import annotations

from collections import defaultdict
import csv
import heapq
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsProject,
                       QgsCoordinateTransform, QgsGeometry, QgsPointXY,
                       QgsMarkerSymbol, QgsSingleSymbolRenderer, QgsSpatialIndex,
                       QgsSymbol, QgsVectorLayer, QgsWkbTypes)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/gis/go_cong_network/pilot5_route_audit"
NETWORK = ROOT / "data/processed/gis/go_cong_network/go_cong_user_trace_candidate_32648.gpkg"
BASE = ROOT / "data/processed/gis/go_cong_network/go_cong_waterway_network_32648.gpkg"
KML = ROOT / "data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml"
GATES = ROOT / "data/raw/gis/gates/sluice_gates_dong_thap_new.csv"
CODES = ("NM29", "NM30", "NM31", "NM32", "NM34")


def node(point: QgsPointXY) -> tuple[int, int]:
    return round(point.x() * 100), round(point.y() * 100)


def add(graph: dict, a: tuple, b: tuple, weight: float, edge_id: int) -> None:
    graph[a].append((b, weight, edge_id))
    graph[b].append((a, weight, edge_id))


def shortest(graph: dict, start: tuple, goal: tuple) -> tuple[float, list[tuple]]:
    best = {start: 0.0}
    previous = {}
    queue = [(0.0, start)]
    while queue:
        distance, here = heapq.heappop(queue)
        if distance > best[here]:
            continue
        if here == goal:
            break
        for there, weight, edge_id in graph[here]:
            trial = distance + weight
            if trial < best.get(there, math.inf):
                best[there] = trial
                previous[there] = (here, edge_id, weight)
                heapq.heappush(queue, (trial, there))
    if goal not in best:
        return math.inf, []
    segments = []
    here = goal
    while here != start:
        before, edge_id, weight = previous[here]
        segments.append((before, here, edge_id, weight))
        here = before
    segments.reverse()
    return best[goal], segments


def geojson_feature(geometry: QgsGeometry, props: dict, to_wgs: QgsCoordinateTransform) -> dict:
    converted = QgsGeometry(geometry)
    converted.transform(to_wgs)
    return {"type": "Feature", "geometry": json.loads(converted.asJson()), "properties": props}


def save_geojson(path: Path, features: list[dict]) -> None:
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    to_metric = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"),
                                       QgsCoordinateReferenceSystem("EPSG:32648"),
                                       QgsProject.instance().transformContext())
    to_wgs = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:32648"),
                                    QgsCoordinateReferenceSystem("EPSG:4326"),
                                    QgsProject.instance().transformContext())
    edges = QgsVectorLayer(f"{NETWORK}|layername=augmented_network_edges_candidate", "edges", "ogr")
    snaps = QgsVectorLayer(f"{NETWORK}|layername=pilot5_augmented_snap_candidates", "snaps", "ogr")
    original = QgsVectorLayer(f"{BASE}|layername=pilot5_reviewed_coordinates", "original", "ogr")
    osm = QgsVectorLayer(f"{BASE}|layername=waterways_osm_raw", "osm", "ogr")
    if not all(layer.isValid() for layer in (edges, snaps, original, osm)):
        raise RuntimeError("Missing input GeoPackage layer")
    edge_map = {feature.id(): feature for feature in edges.getFeatures()}
    edge_index = QgsSpatialIndex(edges.getFeatures())
    graph = defaultdict(list)
    coordinates = {}
    for edge in edge_map.values():
        a, b = edge.geometry().asPolyline()
        ka, kb = node(a), node(b)
        coordinates[ka], coordinates[kb] = QgsPointXY(a), QgsPointXY(b)
        add(graph, ka, kb, edge.geometry().length(), edge.id())
    by_edge = defaultdict(list)
    snap_info = {}
    for feature in snaps.getFeatures():
        code = feature["site_code"]
        point = feature.geometry()
        nearby = [edge_map[fid] for fid in edge_index.nearestNeighbor(point.asPoint(), 32)]
        edge = min(nearby, key=lambda item: item.geometry().distance(point))
        if edge.geometry().distance(point) > 0.02:
            raise RuntimeError(f"Snap {code} is not on a noded edge")
        along = edge.geometry().lineLocatePoint(point)
        a, b = edge.geometry().asPolyline()
        station = ("site", code)
        coordinates[station] = QgsPointXY(point.asPoint())
        add(graph, station, node(a), along, edge.id())
        add(graph, station, node(b), edge.geometry().length() - along, edge.id())
        by_edge[edge.id()].append((along, station))
        snap_info[code] = float(feature["aug_snap_m"])
    for edge_id, stations in by_edge.items():
        ordered = sorted(stations)
        for (distance_a, station_a), (distance_b, station_b) in zip(ordered, ordered[1:]):
            add(graph, station_a, station_b, distance_b - distance_a, edge_id)
    site_geom = {feature["site_code"]: feature.geometry() for feature in original.getFeatures()}

    root = ET.parse(KML).getroot()
    namespace = {"k": "http://www.opengis.net/kml/2.2"}
    traces = []
    for placemark in root.findall(".//k:Placemark", namespace):
        raw = placemark.findtext(".//k:LineString/k:coordinates", default="", namespaces=namespace)
        if not raw.strip():
            continue
        geom = QgsGeometry.fromPolylineXY([QgsPointXY(*map(float, item.split(",")[:2])) for item in raw.split()])
        geom.transform(to_metric)
        traces.append(geom)
    if len(traces) != 4:
        raise RuntimeError("Expected four approved KML lines")

    routes, route_rows, route_geom = [], [], {}
    for i, a in enumerate(CODES):
        for b in CODES[i + 1:]:
            length, segments = shortest(graph, ("site", a), ("site", b))
            if not segments:
                raise RuntimeError(f"No route {a} to {b}")
            points = [coordinates[segments[0][0]]] + [coordinates[segment[1]] for segment in segments]
            geometry = QgsGeometry.fromPolylineXY(points)
            direct = site_geom[a].distance(site_geom[b])
            kml_length = 0.0
            kml_edge_ids = set()
            for left, right, edge_id, weight in segments:
                segment = QgsGeometry.fromPolylineXY([coordinates[left], coordinates[right]])
                midpoint = segment.interpolate(segment.length() / 2)
                if any(trace.distance(midpoint) < 0.05 for trace in traces):
                    kml_length += weight
                    kml_edge_ids.add(edge_id)
            props = {"site_a": a, "site_b": b, "river_m": round(length, 3),
                     "euclidean_m": round(direct, 3),
                     "detour_ratio": round(length / direct, 4),
                     "route_segments": len(segments), "kml_on_route_m": round(kml_length, 3),
                     "kml_pct": round(100 * kml_length / length, 2),
                     "kml_edge_count": len(kml_edge_ids),
                     "snap_a_m": round(snap_info[a], 3), "snap_b_m": round(snap_info[b], 3)}
            route_rows.append(props)
            routes.append(geojson_feature(geometry, props, to_wgs))
            route_geom[a, b] = geometry

    crossing_rows, crossing_features = [], []
    for trace_id, trace in enumerate(traces, 1):
        for way in osm.getFeatures():
            if not trace.intersects(way.geometry()):
                continue
            intersection = trace.intersection(way.geometry())
            point = intersection if intersection.type() == 0 else intersection.centroid()
            if point.isEmpty():
                continue
            focus_distance = route_geom["NM29", "NM34"].distance(point)
            props = {"trace_id": trace_id, "osm_id": int(way["osm_id"]),
                     "osm_name": way["name"] or "", "waterway": way["waterway"],
                     "nm29_nm34_route_distance_m": round(focus_distance, 2),
                     "on_nm29_nm34_route_5m": focus_distance <= 5,
                     "connection_status": "USER_APPROVED_GRAPH_UNVERIFIED_HYDRAULICS"}
            crossing_rows.append(props)
            crossing_features.append(geojson_feature(point, props, to_wgs))

    gate_rows = []
    with GATES.open(newline="", encoding="utf-8-sig") as handle:
        for gate in csv.DictReader(handle):
            if not gate["latitude"] or not gate["longitude"]:
                continue
            point = QgsGeometry.fromPointXY(QgsPointXY(float(gate["longitude"]), float(gate["latitude"])))
            point.transform(to_metric)
            for (a, b), geometry in route_geom.items():
                distance = geometry.distance(point)
                if distance <= 100:
                    gate_rows.append({"site_a": a, "site_b": b,
                                      "gate_id": gate["gate_id"], "gate_name": gate["gate_name"],
                                      "coordinate_status": gate["coordinate_status"],
                                      "distance_to_route_m": round(distance, 2),
                                      "interpretation": "PROXIMITY_ONLY_NOT_CONFIRMED_ROUTE_THROUGH_GATE"})

    OUT.mkdir(parents=True, exist_ok=True)
    save_geojson(OUT / "pilot5_shortest_routes.geojson", routes)
    save_csv(OUT / "pilot5_shortest_routes.csv", route_rows)
    save_geojson(OUT / "kml_osm_crossings.geojson", crossing_features)
    save_csv(OUT / "kml_osm_crossings.csv", crossing_rows)
    if gate_rows:
        save_csv(OUT / "gate_proximity_to_routes.csv", gate_rows)
    (OUT / "manifest.json").write_text(json.dumps({
        "network": str(NETWORK), "source_kml": str(KML),
        "crs_distance": "EPSG:32648", "route_count": len(routes),
        "crossing_count": len(crossing_rows), "gate_proximity_count": len(gate_rows),
        "crossing_interpretation": "Geometric line intersections noded in the approved pilot graph; no independent hydraulic verification",
        "gate_interpretation": "Near a catalogued gate is not proof that a shortest path crosses an open gate",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    project = QgsProject.instance()
    source_project = ROOT / "data/processed/gis/go_cong_network/go_cong_user_trace_candidate_qa.qgs"
    output_project = OUT / "go_cong_pilot5_route_audit.qgs"
    if not project.read(str(source_project)):
        raise RuntimeError("Could not read the approved network project")
    for name, title, color, visible, subset in (
        ("pilot5_shortest_routes.geojson", "10 đường ngắn nhất", "#f39c12", False, None),
        ("pilot5_shortest_routes.geojson", "NM29–NM34: đường vòng", "#c0392b", True,
         '"site_a" = \'NM29\' AND "site_b" = \'NM34\''),
        ("kml_osm_crossings.geojson", "15 giao KML–OSM cần xem", "#e74c3c", True, None),
    ):
        layer = QgsVectorLayer(str(OUT / name), title, "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Invalid route audit layer: {name}")
        if subset:
            layer.setSubsetString(subset)
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.LineGeometry)
            symbol.setColor(QColor(color))
            symbol.symbolLayer(0).setWidth(1.2 if subset else 0.6)
        else:
            symbol = QgsMarkerSymbol.createSimple({"name": "circle", "color": color,
                                                    "outline_color": "#ffffff", "size": "3"})
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        project.addMapLayer(layer)
        project.layerTreeRoot().findLayer(layer.id()).setItemVisibilityChecked(visible)
    if not project.write(str(output_project)):
        raise RuntimeError(project.error())
    project.clear()
    if not project.read(str(output_project)) or any(not layer.isValid() for layer in project.mapLayers().values()):
        raise RuntimeError("Route audit QGIS project failed reopening")
    print(json.dumps({"routes": len(routes), "crossings": len(crossing_rows),
                      "near_gate_routes": len(gate_rows),
                      "nm29_nm34": next(row for row in route_rows if row["site_a"] == "NM29" and row["site_b"] == "NM34"),
                      "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
