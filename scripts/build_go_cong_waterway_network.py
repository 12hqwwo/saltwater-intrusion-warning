"""Build and QA a noded Gò Công waterway network, then snap five pilot sites.

Run with QGIS's python-qgis-ltr.bat after download_go_cong_osm_waterways.py.
The source coordinates remain untouched. Snapped points are separate outputs.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
import csv
import json
import math
from pathlib import Path
import unicodedata

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsApplication, QgsCategorizedSymbolRenderer, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsFeature, QgsField, QgsGeometry, QgsMarkerSymbol,
    QgsPalLayerSettings, QgsPointXY, QgsProject, QgsReferencedRectangle,
    QgsRendererCategory, QgsSingleSymbolRenderer, QgsSpatialIndex, QgsSymbol,
    QgsTextBufferSettings, QgsTextFormat, QgsVectorFileWriter, QgsVectorLayer,
    QgsVectorLayerSimpleLabeling, QgsWkbTypes,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_JSON = ROOT / "data" / "raw" / "gis" / "osm" / "go_cong_waterways_20261016.json"
CONTEXT_JSON = ROOT / "data" / "raw" / "gis" / "osm" / "go_cong_pilot5_context_20261016.json"
MONITORING_JSON = ROOT / "data" / "processed" / "gis" / "tiengiang_monitoring" / "monitoring_records.json"
OUT = ROOT / "data" / "processed" / "gis" / "go_cong_network"
COORDINATE_REVIEW_CSV = OUT / "pilot5_coordinate_review.csv"
GPKG = OUT / "go_cong_waterway_network_32648.gpkg"
QGS = OUT / "go_cong_waterway_network_qa.qgs"
SNAP_CSV = OUT / "pilot5_snap_qa_updated.csv"
QA_JSON = OUT / "network_topology_summary.json"

SOURCE_CRS = QgsCoordinateReferenceSystem("EPSG:4326")
METRIC_CRS = QgsCoordinateReferenceSystem("EPSG:32648")
PILOT5 = ("NM29", "NM30", "NM31", "NM32", "NM34")
SNAP_THRESHOLD_M = 100.0
GAP_CHECK_M = 5.0


def norm(text: str) -> str:
    value = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn").lower()


def line_parts(geometry: QgsGeometry) -> list[QgsGeometry]:
    if geometry.isNull() or geometry.isEmpty():
        return []
    if QgsWkbTypes.geometryType(geometry.wkbType()) != QgsWkbTypes.LineGeometry:
        return []
    if QgsWkbTypes.isSingleType(geometry.wkbType()):
        return [geometry]
    return [part for part in geometry.asGeometryCollection()
            if QgsWkbTypes.geometryType(part.wkbType()) == QgsWkbTypes.LineGeometry]


def write_layer(layer: QgsVectorLayer, layer_name: str, overwrite_file: bool) -> None:
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteFile if overwrite_file
        else QgsVectorFileWriter.CreateOrOverwriteLayer
    )
    code, message, *_ = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(GPKG), QgsProject.instance().transformContext(), options)
    if code != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"{layer_name}: {message}")


def make_layer(uri: str, name: str, fields: list[tuple[str, QVariant.Type]]) -> QgsVectorLayer:
    layer = QgsVectorLayer(uri, name, "memory")
    layer.dataProvider().addAttributes([QgsField(field, kind) for field, kind in fields])
    layer.updateFields()
    return layer


def key(point: QgsPointXY) -> tuple[int, int]:
    return round(point.x() * 100), round(point.y() * 100)


def make_raw_layer(payload: dict, transform: QgsCoordinateTransform) -> tuple[QgsVectorLayer, list[QgsGeometry]]:
    fields = [
        ("osm_id", QVariant.LongLong), ("waterway", QVariant.String),
        ("name", QVariant.String), ("name_vi", QVariant.String),
        ("tunnel", QVariant.String), ("covered", QVariant.String),
        ("source", QVariant.String), ("snapshot", QVariant.String),
    ]
    layer = make_layer("LineString?crs=EPSG:32648", "OSM waterways raw", fields)
    provider = layer.dataProvider()
    features: list[QgsFeature] = []
    geometries: list[QgsGeometry] = []
    snapshot = payload["tlcn_extract"]["downloaded_at_utc"]
    for element in payload["elements"]:
        if element.get("type") != "way" or len(element.get("geometry", [])) < 2:
            continue
        points = [QgsPointXY(item["lon"], item["lat"]) for item in element["geometry"]]
        geometry = QgsGeometry.fromPolylineXY(points)
        geometry.transform(transform)
        if geometry.isNull() or geometry.isEmpty() or geometry.length() <= 0:
            continue
        tags = element.get("tags", {})
        feature = QgsFeature(layer.fields())
        feature.setGeometry(geometry)
        feature.setAttributes([
            element["id"], tags.get("waterway", ""), tags.get("name", ""),
            tags.get("name:vi", ""), tags.get("tunnel", ""), tags.get("covered", ""),
            "OpenStreetMap", snapshot,
        ])
        features.append(feature)
        geometries.append(geometry)
    provider.addFeatures(features)
    layer.updateExtents()
    return layer, geometries


def make_bridge_layer(payload: dict, transform: QgsCoordinateTransform) -> QgsVectorLayer:
    fields = [("osm_id", QVariant.LongLong), ("name", QVariant.String),
              ("bridge_name", QVariant.String), ("highway", QVariant.String),
              ("source", QVariant.String)]
    layer = make_layer("LineString?crs=EPSG:32648", "OSM bridges near pilot 5", fields)
    features = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        points = element.get("geometry", [])
        if element.get("type") != "way" or "bridge" not in tags or len(points) < 2:
            continue
        geometry = QgsGeometry.fromPolylineXY([QgsPointXY(p["lon"], p["lat"]) for p in points])
        geometry.transform(transform)
        feature = QgsFeature(layer.fields())
        feature.setGeometry(geometry)
        feature.setAttributes([element["id"], tags.get("name", ""),
                               tags.get("bridge:name", ""), tags.get("highway", ""),
                               "OpenStreetMap context query"])
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    return layer


def build_noded_edges(geometries: list[QgsGeometry],
                      source_label: str = "OSM unary-union noded") -> tuple[QgsVectorLayer, dict]:
    # GEOS unary union nodes every true line intersection and removes exact overlaps.
    noded = QgsGeometry.unaryUnion(geometries)
    raw_segments: list[tuple[QgsPointXY, QgsPointXY, float]] = []
    duplicate_keys: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    duplicates_removed = 0
    zero_length_removed = 0
    for part in line_parts(noded):
        polyline = part.asPolyline()
        for start, end in zip(polyline, polyline[1:]):
            length = math.hypot(end.x() - start.x(), end.y() - start.y())
            if length <= 0.01:
                zero_length_removed += 1
                continue
            a, b = key(start), key(end)
            edge_key = tuple(sorted((a, b)))
            if edge_key in duplicate_keys:
                duplicates_removed += 1
                continue
            duplicate_keys.add(edge_key)
            raw_segments.append((QgsPointXY(start), QgsPointXY(end), length))

    adjacency: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    edge_nodes = []
    for start, end, _ in raw_segments:
        a, b = key(start), key(end)
        adjacency[a].add(b)
        adjacency[b].add(a)
        edge_nodes.append((a, b))

    node_component: dict[tuple[int, int], int] = {}
    component_node_counts: Counter[int] = Counter()
    component = 0
    for start in adjacency:
        if start in node_component:
            continue
        component += 1
        queue = deque([start])
        node_component[start] = component
        while queue:
            current = queue.popleft()
            component_node_counts[component] += 1
            for neighbor in adjacency[current]:
                if neighbor not in node_component:
                    node_component[neighbor] = component
                    queue.append(neighbor)

    fields = [("edge_id", QVariant.Int), ("component", QVariant.Int),
              ("length_m", QVariant.Double), ("source", QVariant.String)]
    layer = make_layer("LineString?crs=EPSG:32648", "Noded waterway network", fields)
    features = []
    component_lengths: Counter[int] = Counter()
    component_edges: Counter[int] = Counter()
    for edge_id, ((start, end, length), (a, _)) in enumerate(zip(raw_segments, edge_nodes), 1):
        comp = node_component[a]
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPolylineXY([start, end]))
        feature.setAttributes([edge_id, comp, length, source_label])
        features.append(feature)
        component_lengths[comp] += length
        component_edges[comp] += 1
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    degree_counts = Counter(len(neighbors) for neighbors in adjacency.values())
    summary = {
        "edge_count": len(raw_segments), "node_count": len(adjacency),
        "component_count": component,
        "duplicate_edges_removed": duplicates_removed,
        "zero_length_edges_removed": zero_length_removed,
        "node_degree_counts": dict(sorted(degree_counts.items())),
        "components": [
            {"component": comp, "nodes": component_node_counts[comp],
             "edges": component_edges[comp], "length_km": round(component_lengths[comp] / 1000, 3)}
            for comp in sorted(component_node_counts,
                               key=lambda item: component_lengths[item], reverse=True)
        ],
    }
    return layer, summary


def find_gap_candidates(raw_layer: QgsVectorLayer) -> tuple[QgsVectorLayer, QgsVectorLayer, list[QgsGeometry]]:
    fields = [("way_a", QVariant.LongLong), ("way_b", QVariant.LongLong),
              ("gap_m", QVariant.Double), ("qa", QVariant.String)]
    output = make_layer("Point?crs=EPSG:32648", "Near-miss endpoints under 5 m", fields)
    connector_fields = [("way_a", QVariant.LongLong), ("way_b", QVariant.LongLong),
                        ("gap_m", QVariant.Double), ("action", QVariant.String)]
    connectors = make_layer("LineString?crs=EPSG:32648", "Topology connectors under 5 m", connector_fields)
    index = QgsSpatialIndex(raw_layer.getFeatures())
    raw_features = {feature.id(): feature for feature in raw_layer.getFeatures()}
    seen: set[tuple[int, int, int, int]] = set()
    results, connector_features, connector_geometries = [], [], []
    for feature in raw_features.values():
        for part in line_parts(feature.geometry()):
            line = part.asPolyline()
            for endpoint in (line[0], line[-1]):
                point_geometry = QgsGeometry.fromPointXY(endpoint)
                best = None
                for candidate_id in index.nearestNeighbor(endpoint, 8):
                    if candidate_id == feature.id():
                        continue
                    candidate = raw_features[candidate_id]
                    distance = candidate.geometry().distance(point_geometry)
                    if 0.05 < distance <= GAP_CHECK_M and (best is None or distance < best[0]):
                        best = (distance, candidate)
                if best is None:
                    continue
                distance, candidate = best
                target = candidate.geometry().nearestPoint(point_geometry).asPoint()
                pair = tuple(sorted((int(feature["osm_id"]), int(candidate["osm_id"]))))
                connector_key = tuple(sorted((key(endpoint), key(target))))
                if connector_key in seen:
                    continue
                seen.add(connector_key)
                result = QgsFeature(output.fields())
                result.setGeometry(point_geometry)
                result.setAttributes([pair[0], pair[1], distance, "AUTO_CONNECT_LT5M"])
                results.append(result)
                connector_geometry = QgsGeometry.fromPolylineXY([endpoint, QgsPointXY(target)])
                connector = QgsFeature(connectors.fields())
                connector.setGeometry(connector_geometry)
                connector.setAttributes([pair[0], pair[1], distance, "AUTO_CONNECT_LT5M"])
                connector_features.append(connector)
                connector_geometries.append(connector_geometry)
    output.dataProvider().addFeatures(results)
    connectors.dataProvider().addFeatures(connector_features)
    output.updateExtents()
    connectors.updateExtents()
    return output, connectors, connector_geometries


def snap_pilot5(monitoring: dict, coordinate_review: dict, edge_layer: QgsVectorLayer, raw_layer: QgsVectorLayer,
                bridge_layer: QgsVectorLayer, transform: QgsCoordinateTransform
                ) -> tuple[QgsVectorLayer, QgsVectorLayer, QgsVectorLayer, QgsVectorLayer, list[dict]]:
    fields = [
        ("site_code", QVariant.String), ("site_name", QVariant.String),
        ("pdf_name", QVariant.String),
        ("pdf_lon", QVariant.Double), ("pdf_lat", QVariant.Double),
        ("input_lon", QVariant.Double), ("input_lat", QVariant.Double),
        ("coord_status", QVariant.String), ("evidence", QVariant.String),
        ("route_evidence", QVariant.String), ("evidence_image", QVariant.String),
        ("coord_shift_m", QVariant.Double),
        ("snap_m", QVariant.Double), ("threshold_m", QVariant.Double),
        ("snap_status", QVariant.String), ("route_check", QVariant.String),
        ("near_name", QVariant.String), ("waterway", QVariant.String),
        ("osm_id", QVariant.LongLong), ("edge_id", QVariant.Int),
        ("component", QVariant.Int), ("bridge_m", QVariant.Double),
        ("bridge_name", QVariant.String), ("bridge_id", QVariant.LongLong),
        ("qa_note", QVariant.String),
    ]
    original_layer = make_layer("Point?crs=EPSG:32648", "Pilot 5 PDF coordinates", fields)
    reviewed_layer = make_layer("Point?crs=EPSG:32648", "Pilot 5 reviewed coordinates", fields)
    candidate_layer = make_layer("Point?crs=EPSG:32648", "Pilot 5 snap candidates", fields)
    accepted_layer = make_layer("Point?crs=EPSG:32648", "Pilot 5 accepted snaps", fields)
    edge_features = {feature.id(): feature for feature in edge_layer.getFeatures()}
    raw_features = {feature.id(): feature for feature in raw_layer.getFeatures()}
    bridge_features = {feature.id(): feature for feature in bridge_layer.getFeatures()}
    edge_index = QgsSpatialIndex(edge_layer.getFeatures())
    raw_index = QgsSpatialIndex(raw_layer.getFeatures())
    bridge_index = QgsSpatialIndex(bridge_layer.getFeatures())
    locations = {row["site_code"]: row for row in monitoring["locations"]}
    reports = []
    original_features, reviewed_features, candidate_features, accepted_features = [], [], [], []
    for code in PILOT5:
        row = locations[code]
        review = coordinate_review[code]
        pdf_geometry = QgsGeometry.fromPointXY(QgsPointXY(row["longitude_deg"], row["latitude_deg"]))
        pdf_geometry.transform(transform)
        input_lat = float(review["review_lat"]) if review["review_lat"] else None
        input_lon = float(review["review_lon"]) if review["review_lon"] else None
        working_name = review["working_name"] or row["site_name"]
        base_attributes = [
            code, working_name, row["site_name"], row["longitude_deg"], row["latitude_deg"],
            input_lon, input_lat, review["coordinate_status"], review["evidence_note"],
            review["route_evidence"], review["evidence_image"],
        ]
        if input_lon is None or input_lat is None:
            attributes = base_attributes + [None] + [
                None, SNAP_THRESHOLD_M, "REVIEW_LOCATION", "NO_REVIEWED_COORDINATE",
                None, None, None, None, None, None, None, None,
                "Tọa độ PDF được báo là nằm trên đất liền; chưa có vị trí thay thế để snap.",
            ]
            original_feature = QgsFeature(original_layer.fields())
            original_feature.setGeometry(pdf_geometry)
            original_feature.setAttributes(attributes)
            original_features.append(original_feature)
            reports.append(dict(zip([field.name() for field in original_layer.fields()], attributes)))
            continue
        input_geometry = QgsGeometry.fromPointXY(QgsPointXY(input_lon, input_lat))
        input_geometry.transform(transform)
        input_metric = input_geometry.asPoint()
        base_attributes.append(pdf_geometry.distance(input_geometry))
        nearest_edge_id = None
        nearest_point = None
        snap_distance = math.inf
        for feature_id in edge_index.nearestNeighbor(input_metric, 12):
            edge = edge_features[feature_id]
            candidate = edge.geometry().nearestPoint(input_geometry)
            distance = candidate.distance(input_geometry)
            if distance < snap_distance:
                nearest_edge_id = feature_id
                nearest_point = candidate
                snap_distance = distance
        if nearest_edge_id is None or nearest_point is None:
            raise RuntimeError(f"No network edge found for {code}")
        edge = edge_features[nearest_edge_id]

        nearest_raw = None
        raw_distance = math.inf
        for feature_id in raw_index.nearestNeighbor(input_metric, 12):
            raw = raw_features[feature_id]
            distance = raw.geometry().distance(input_geometry)
            if distance < raw_distance:
                nearest_raw, raw_distance = raw, distance
        near_name = nearest_raw["name"] if nearest_raw else ""
        waterway = nearest_raw["waterway"] if nearest_raw else ""
        osm_id = int(nearest_raw["osm_id"]) if nearest_raw else None
        nearest_bridge = None
        bridge_distance = math.inf
        for feature_id in bridge_index.nearestNeighbor(input_metric, 12):
            bridge = bridge_features[feature_id]
            distance = bridge.geometry().distance(input_geometry)
            if distance < bridge_distance:
                nearest_bridge, bridge_distance = bridge, distance
        bridge_name = ""
        bridge_id = None
        if nearest_bridge:
            bridge_name = nearest_bridge["bridge_name"] or nearest_bridge["name"] or ""
            bridge_id = int(nearest_bridge["osm_id"])
        expected_words = [word for word in norm(working_name).replace("–", " ").split()
                          if len(word) >= 4 and word not in {"huyen", "thi", "cong", "dong", "cau"}]
        name_match = bool(near_name) and any(word in norm(near_name) for word in expected_words)
        bridge_match = bool(bridge_name) and norm(bridge_name) in norm(working_name) and bridge_distance <= 100
        visual_match = (
            review["route_evidence"] == "USER_VISUAL_WATERWAY_MATCH"
            and bool(review["evidence_image"])
            and snap_distance <= 25.0
            and waterway in {"river", "canal", "stream"}
        )
        route_ok = name_match or bridge_match or visual_match
        route_check = ("OSM_WATERWAY_NAME_MATCH" if name_match else
                       "OSM_BRIDGE_NAME_MATCH" if bridge_match else
                       "USER_IMAGE_AND_NEAR_OSM_WATERWAY" if visual_match else
                       "UNNAMED_OSM_WATERWAY" if not near_name else
                       "OSM_NAME_DIFFERS_REVIEW")
        distance_ok = snap_distance <= SNAP_THRESHOLD_M
        status = "ACCEPTED" if distance_ok and route_ok else (
            "REVIEW_ROUTE" if distance_ok else "REJECTED_TOO_FAR")
        note = ("Đạt ngưỡng khoảng cách và đối chiếu được tuyến/cầu từ OSM hoặc ảnh người dùng."
                if status == "ACCEPTED" else (
                    "Đạt ngưỡng khoảng cách nhưng chưa đủ bằng chứng đúng tuyến."
                    if status == "REVIEW_ROUTE" else
                    "Khoảng snap vượt ngưỡng; không dùng trong phân tích."))
        attributes = base_attributes + [
            snap_distance, SNAP_THRESHOLD_M, status, route_check, near_name,
            waterway, osm_id, int(edge["edge_id"]), int(edge["component"]),
            bridge_distance, bridge_name, bridge_id, note,
        ]
        original_feature = QgsFeature(original_layer.fields())
        original_feature.setGeometry(pdf_geometry)
        original_feature.setAttributes(attributes)
        original_features.append(original_feature)
        reviewed_feature = QgsFeature(reviewed_layer.fields())
        reviewed_feature.setGeometry(input_geometry)
        reviewed_feature.setAttributes(attributes)
        reviewed_features.append(reviewed_feature)
        candidate_feature = QgsFeature(candidate_layer.fields())
        candidate_feature.setGeometry(nearest_point)
        candidate_feature.setAttributes(attributes)
        candidate_features.append(candidate_feature)
        if status == "ACCEPTED":
            accepted_feature = QgsFeature(accepted_layer.fields())
            accepted_feature.setGeometry(nearest_point)
            accepted_feature.setAttributes(attributes)
            accepted_features.append(accepted_feature)
        reports.append(dict(zip([field.name() for field in original_layer.fields()], attributes)))
    original_layer.dataProvider().addFeatures(original_features)
    reviewed_layer.dataProvider().addFeatures(reviewed_features)
    candidate_layer.dataProvider().addFeatures(candidate_features)
    accepted_layer.dataProvider().addFeatures(accepted_features)
    original_layer.updateExtents()
    reviewed_layer.updateExtents()
    candidate_layer.updateExtents()
    accepted_layer.updateExtents()
    return original_layer, reviewed_layer, candidate_layer, accepted_layer, reports


def line_symbol(color: str, width: float) -> QgsSymbol:
    symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.LineGeometry)
    symbol.setColor(QColor(color))
    symbol.symbolLayer(0).setWidth(width)
    return symbol


def label_sites(layer: QgsVectorLayer) -> None:
    settings = QgsPalLayerSettings()
    settings.fieldName = "site_code"
    text = QgsTextFormat()
    text.setSize(9)
    text.setColor(QColor("#182434"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1)
    buffer.setColor(QColor("#ffffff"))
    text.setBuffer(buffer)
    settings.setFormat(text)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.loads(RAW_JSON.read_text(encoding="utf-8"))
    context_payload = json.loads(CONTEXT_JSON.read_text(encoding="utf-8"))
    monitoring = json.loads(MONITORING_JSON.read_text(encoding="utf-8"))
    with COORDINATE_REVIEW_CSV.open(newline="", encoding="utf-8-sig") as handle:
        coordinate_rows = list(csv.DictReader(handle))
    if any(None in row or not row["site_code"] for row in coordinate_rows):
        raise ValueError("Malformed coordinate review CSV")
    coordinate_review = {row["site_code"]: row for row in coordinate_rows}
    if len(coordinate_rows) != len(PILOT5) or set(coordinate_review) != set(PILOT5):
        raise ValueError("Coordinate review must have exactly one row per pilot site")
    for row in coordinate_rows:
        if row["evidence_image"] and not (ROOT / "data" / "raw" / "gis" / "user_review_20261017" / row["evidence_image"]).is_file():
            raise ValueError(f"Missing image evidence for {row['site_code']}")
    transform = QgsCoordinateTransform(SOURCE_CRS, METRIC_CRS, QgsProject.instance())

    raw_layer, raw_geometries = make_raw_layer(payload, transform)
    bridge_layer = make_bridge_layer(context_payload, transform)
    gap_layer, connector_layer, connector_geometries = find_gap_candidates(raw_layer)
    edge_layer, topology = build_noded_edges(raw_geometries + connector_geometries)
    topology["near_miss_endpoints_under_5m"] = gap_layer.featureCount()
    topology["topology_connectors_added"] = connector_layer.featureCount()
    topology["source_way_count"] = raw_layer.featureCount()
    topology["crs"] = "EPSG:32648"
    topology["noding_method"] = "GEOS unary union; every consecutive vertex exported as an edge"
    topology["gap_check_m"] = GAP_CHECK_M
    topology["source_snapshot_utc"] = payload["tlcn_extract"]["downloaded_at_utc"]
    topology["attribution"] = payload["tlcn_extract"]["attribution"]

    original_layer, reviewed_layer, candidate_layer, accepted_layer, snap_reports = snap_pilot5(
        monitoring, coordinate_review, edge_layer, raw_layer, bridge_layer, transform)
    topology["pilot5_snap"] = snap_reports
    topology["accepted_snap_count"] = sum(row["snap_status"] == "ACCEPTED" for row in snap_reports)
    topology["pilot_candidate_components"] = sorted({row["component"] for row in snap_reports if row["component"] is not None})
    topology["all_pilot_candidates_same_component"] = len(topology["pilot_candidate_components"]) == 1
    topology["topology_interpretation"] = (
        "The final edge layer is noded at every intersection, contains no duplicate or zero-length edge, "
        "and includes explicit provisional automatic connectors for source endpoints separated by <=5 m. "
        "Disconnected components can be genuine isolated waterways or unmapped links and remain separate."
    )

    write_layer(raw_layer, "waterways_osm_raw", True)
    write_layer(edge_layer, "network_edges_noded", False)
    write_layer(gap_layer, "topology_gap_candidates", False)
    write_layer(connector_layer, "topology_connectors_lt5m", False)
    write_layer(bridge_layer, "osm_bridges_context", False)
    write_layer(original_layer, "pilot5_original", False)
    write_layer(reviewed_layer, "pilot5_reviewed_coordinates", False)
    write_layer(candidate_layer, "pilot5_snap_candidates", False)
    write_layer(accepted_layer, "pilot5_snapped_accepted", False)

    with SNAP_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=snap_reports[0].keys())
        writer.writeheader()
        writer.writerows(snap_reports)
    QA_JSON.write_text(json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8")

    project = QgsProject.instance()
    project.setCrs(METRIC_CRS)
    raw_map = QgsVectorLayer(f"{GPKG}|layername=waterways_osm_raw", "Tim sông–kênh OSM gốc", "ogr")
    edge_map = QgsVectorLayer(f"{GPKG}|layername=network_edges_noded", "Mạng đã node hóa", "ogr")
    gap_map = QgsVectorLayer(f"{GPKG}|layername=topology_gap_candidates", "Ứng viên khe hở <5 m", "ogr")
    connector_map = QgsVectorLayer(f"{GPKG}|layername=topology_connectors_lt5m", "Đoạn nối topology <5 m", "ogr")
    bridge_map = QgsVectorLayer(f"{GPKG}|layername=osm_bridges_context", "Cầu OSM quanh 5 điểm", "ogr")
    original_map = QgsVectorLayer(f"{GPKG}|layername=pilot5_original", "5 tọa độ PDF gốc", "ogr")
    reviewed_map = QgsVectorLayer(f"{GPKG}|layername=pilot5_reviewed_coordinates", "5 tọa độ đối chiếu", "ogr")
    candidate_map = QgsVectorLayer(f"{GPKG}|layername=pilot5_snap_candidates", "5 vị trí snap ứng viên", "ogr")
    accepted_map = QgsVectorLayer(f"{GPKG}|layername=pilot5_snapped_accepted", "Điểm snap đã nhận", "ogr")
    for layer in (raw_map, edge_map, gap_map, connector_map, bridge_map, original_map, reviewed_map, candidate_map, accepted_map):
        if not layer.isValid():
            raise RuntimeError(f"Invalid output layer: {layer.name()}")
    raw_map.setRenderer(QgsCategorizedSymbolRenderer("waterway", [
        QgsRendererCategory("river", line_symbol("#2166ac", 0.8), "Sông"),
        QgsRendererCategory("canal", line_symbol("#4393c3", 0.55), "Kênh"),
        QgsRendererCategory("stream", line_symbol("#92c5de", 0.35), "Rạch/suối"),
        QgsRendererCategory("drain", line_symbol("#b8e0d2", 0.25), "Thoát nước"),
        QgsRendererCategory("ditch", line_symbol("#d9f0d3", 0.25), "Mương"),
    ]))
    edge_map.setRenderer(QgsSingleSymbolRenderer(line_symbol("#474f5b", 0.25)))
    gap_map.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        "name": "x", "color": "#ff7f00", "size": "3.5"})))
    connector_map.setRenderer(QgsSingleSymbolRenderer(line_symbol("#ff7f00", 1.1)))
    bridge_map.setRenderer(QgsSingleSymbolRenderer(line_symbol("#8e44ad", 0.7)))
    original_map.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        "name": "circle", "color": "#d73027", "outline_color": "#ffffff", "size": "4"})))
    reviewed_map.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        "name": "circle", "color": "#2b83ba", "outline_color": "#ffffff", "size": "4"})))
    candidate_map.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        "name": "diamond", "color": "#fdae61", "outline_color": "#7f3b08", "size": "4.5"})))
    accepted_map.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        "name": "diamond", "color": "#1a9850", "outline_color": "#ffffff", "size": "4.5"})))
    label_sites(original_map)
    label_sites(reviewed_map)
    label_sites(candidate_map)
    label_sites(accepted_map)
    for layer in (raw_map, edge_map, gap_map, connector_map, bridge_map, original_map, reviewed_map, candidate_map, accepted_map):
        project.addMapLayer(layer)
    project.layerTreeRoot().findLayer(edge_map.id()).setItemVisibilityChecked(False)
    project.layerTreeRoot().findLayer(gap_map.id()).setItemVisibilityChecked(True)
    project.layerTreeRoot().findLayer(raw_map.id()).setItemVisibilityChecked(True)
    project.layerTreeRoot().findLayer(original_map.id()).setItemVisibilityChecked(False)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(original_map.extent(), METRIC_CRS))
    if not project.write(str(QGS)):
        raise RuntimeError(project.error())
    QGS.with_name(QGS.name + "~").unlink(missing_ok=True)
    print(json.dumps({
        "source_ways": raw_layer.featureCount(), "network_edges": edge_layer.featureCount(),
        "components": topology["component_count"], "gap_candidates": gap_layer.featureCount(),
        "connectors_added": connector_layer.featureCount(),
        "snap_distances_m": {row["site_code"]: round(row["snap_m"], 2) if row["snap_m"] is not None else None for row in snap_reports},
        "accepted": topology["accepted_snap_count"], "gpkg": str(GPKG), "project": str(QGS),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
