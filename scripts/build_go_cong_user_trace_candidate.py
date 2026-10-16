"""Add user-drawn KML waterways as a provisional Gò Công network overlay.

The baseline OSM GeoPackage and project are left intact. This output is for
spatial review; KML–OSM crossings and open-water endpoints need hydrologic QA.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsFeature, QgsField, QgsGeometry, QgsMarkerSymbol, QgsPointXY, QgsProject,
    QgsSingleSymbolRenderer, QgsSpatialIndex, QgsSymbol, QgsVectorFileWriter,
    QgsVectorLayer, QgsWkbTypes,
)

from build_go_cong_waterway_network import build_noded_edges


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/gis/go_cong_network"
SOURCE_KML = ROOT / "data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml"
BASE_GPKG = OUT / "go_cong_waterway_network_32648.gpkg"
BASE_PROJECT = OUT / "go_cong_waterway_network_qa.qgs"
GPKG = OUT / "go_cong_user_trace_candidate_32648.gpkg"
QGS = OUT / "go_cong_user_trace_candidate_qa.qgs"
CSV = OUT / "pilot5_user_trace_snap_qa.csv"
JSON = OUT / "user_trace_topology_qa.json"


def memory_layer(uri: str, name: str, fields: list[tuple[str, QVariant.Type]]) -> QgsVectorLayer:
    layer = QgsVectorLayer(uri, name, "memory")
    layer.dataProvider().addAttributes([QgsField(field, kind) for field, kind in fields])
    layer.updateFields()
    return layer


def write_layer(layer: QgsVectorLayer, name: str, first: bool = False) -> None:
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = name
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = (QgsVectorFileWriter.CreateOrOverwriteFile if first
                                    else QgsVectorFileWriter.CreateOrOverwriteLayer)
    result, message, *_ = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(GPKG), QgsProject.instance().transformContext(), options)
    if result != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"{name}: {message}")


def line_symbol(color: str, width: float) -> QgsSymbol:
    symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.LineGeometry)
    symbol.setColor(QColor(color))
    symbol.symbolLayer(0).setWidth(width)
    return symbol


def closest_way(geometry: QgsGeometry, features: list[QgsFeature]) -> dict:
    feature = min(features, key=lambda row: row.geometry().distance(geometry))
    return {
        "osm_id": int(feature["osm_id"]),
        "name": feature["name"],
        "waterway": feature["waterway"],
        "distance_m": round(feature.geometry().distance(geometry), 2),
    }


def kml_lines(transform: QgsCoordinateTransform) -> list[dict]:
    root = ET.parse(SOURCE_KML).getroot()
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    traces = []
    for placemark in root.findall(".//k:Placemark", ns):
        coordinate_text = placemark.findtext(".//k:LineString/k:coordinates", default="", namespaces=ns)
        if not coordinate_text.strip():
            continue
        name = placemark.findtext("k:name", default="", namespaces=ns)
        site_code = "NM29" if "NM29" in name else "NM31" if "Tân Hòa" in name else None
        if site_code is None:
            raise ValueError(f"Unrecognized KML trace: {name}")
        points = [QgsPointXY(*map(float, token.split(",")[:2])) for token in coordinate_text.split()]
        if len(points) < 2:
            raise ValueError(f"Short KML trace: {name}")
        geometry = QgsGeometry.fromPolylineXY(points)
        geometry.transform(transform)
        traces.append({"trace_id": len(traces) + 1, "site_code": site_code,
                       "name": name, "geometry": geometry, "vertices": len(points)})
    if len(traces) != 4 or [trace["site_code"] for trace in traces] != ["NM29", "NM31", "NM31", "NM31"]:
        raise ValueError("Expected one NM29 line and three NM31 lines in the supplied KML")
    return traces


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    project = QgsProject.instance()
    if not project.read(str(BASE_PROJECT)):
        raise RuntimeError("Could not read the baseline QGIS project")
    metric_crs = QgsCoordinateReferenceSystem("EPSG:32648")
    transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), metric_crs, project)
    raw_layer = QgsVectorLayer(f"{BASE_GPKG}|layername=waterways_osm_raw", "OSM", "ogr")
    connectors_layer = QgsVectorLayer(f"{BASE_GPKG}|layername=topology_connectors_lt5m", "OSM connectors", "ogr")
    site_layer = QgsVectorLayer(f"{BASE_GPKG}|layername=pilot5_reviewed_coordinates", "Pilot sites", "ogr")
    if not all(layer.isValid() for layer in (raw_layer, connectors_layer, site_layer)):
        raise RuntimeError("Missing baseline GeoPackage layer")
    raw_features = list(raw_layer.getFeatures())
    traces = kml_lines(transform)

    trace_fields = [("trace_id", QVariant.Int), ("site_code", QVariant.String),
                    ("trace_name", QVariant.String), ("length_m", QVariant.Double),
                    ("vertices", QVariant.Int), ("qa_status", QVariant.String),
                    ("source", QVariant.String)]
    trace_layer = memory_layer("LineString?crs=EPSG:32648", "User KML traces", trace_fields)
    for trace in traces:
        feature = QgsFeature(trace_layer.fields())
        feature.setGeometry(trace["geometry"])
        feature.setAttributes([trace["trace_id"], trace["site_code"], trace["name"],
                               trace["geometry"].length(), trace["vertices"],
                               "USER_APPROVED_PILOT_GEOMETRY",
                               SOURCE_KML.name])
        trace_layer.dataProvider().addFeatures([feature])
    trace_layer.updateExtents()

    # Retain each small gap as an explicit, inspectable assumption.
    gap_layer = memory_layer("LineString?crs=EPSG:32648", "KML trace connector", [
        ("site_code", QVariant.String), ("from_trace", QVariant.Int),
        ("to_trace", QVariant.Int), ("gap_m", QVariant.Double),
        ("qa_status", QVariant.String)])
    gap_geometries = []
    gap_reports = []
    for before, after in zip(traces[1:-1], traces[2:]):
        end = before["geometry"].asPolyline()[-1]
        start = after["geometry"].asPolyline()[0]
        gap_m = QgsGeometry.fromPointXY(end).distance(QgsGeometry.fromPointXY(start))
        if not 0 < gap_m <= 5:
            raise ValueError(f"Unexpected gap between Tân Hòa KML traces {before['trace_id']} and {after['trace_id']}: {gap_m:.2f} m")
        gap_geometry = QgsGeometry.fromPolylineXY([QgsPointXY(end), QgsPointXY(start)])
        gap_feature = QgsFeature(gap_layer.fields())
        gap_feature.setGeometry(gap_geometry)
        gap_feature.setAttributes(["NM31", before["trace_id"], after["trace_id"],
                                   gap_m, "USER_APPROVED_PILOT_CONNECTOR"])
        gap_layer.dataProvider().addFeatures([gap_feature])
        gap_geometries.append(gap_geometry)
        gap_reports.append({"from_trace": before["trace_id"], "to_trace": after["trace_id"],
                            "gap_m": round(gap_m, 2)})
    gap_layer.updateExtents()

    augmented_inputs = ([feature.geometry() for feature in raw_features]
                        + [feature.geometry() for feature in connectors_layer.getFeatures()]
                        + [trace["geometry"] for trace in traces] + gap_geometries)
    edge_layer, topology = build_noded_edges(augmented_inputs, "OSM + user KML candidate")
    edge_features = {feature.id(): feature for feature in edge_layer.getFeatures()}
    edge_index = QgsSpatialIndex(edge_layer.getFeatures())
    with (OUT / "pilot5_snap_qa_updated.csv").open(newline="", encoding="utf-8-sig") as handle:
        baseline = {row["site_code"]: row for row in csv.DictReader(handle)}

    snap_fields = [("site_code", QVariant.String), ("site_name", QVariant.String),
                   ("osm_snap_m", QVariant.Double), ("kml_snap_m", QVariant.Double),
                   ("aug_snap_m", QVariant.Double), ("source_near", QVariant.String),
                   ("trace_id", QVariant.Int), ("component", QVariant.Int),
                   ("snap_status", QVariant.String), ("qa_note", QVariant.String)]
    candidate_layer = memory_layer("Point?crs=EPSG:32648", "Augmented snap candidates", snap_fields)
    approved_layer = memory_layer("Point?crs=EPSG:32648", "User-approved KML snaps", snap_fields)
    reports = []
    for site in site_layer.getFeatures():
        code = site["site_code"]
        original = site.geometry()
        point = original.asPoint()
        edge = min((edge_features[fid] for fid in edge_index.nearestNeighbor(point, 16)),
                   key=lambda feature: feature.geometry().distance(original))
        nearest_point = edge.geometry().nearestPoint(original)
        aug_distance = original.distance(nearest_point)
        trace = min(traces, key=lambda item: item["geometry"].distance(original))
        trace_distance = trace["geometry"].distance(original)
        osm_distance = float(baseline[code]["snap_m"])
        source_near = "USER_KML" if trace_distance + 0.01 < osm_distance else "OSM"
        if code in {"NM29", "NM31"} and trace["site_code"] == code and aug_distance <= 100 and source_near == "USER_KML":
            status = "USER_APPROVED_FOR_PILOT"
            note = "Người dùng chốt mạng làm việc; chưa có kiểm định thủy lực độc lập tại nút giao/cống."
        elif baseline[code]["snap_status"] == "ACCEPTED":
            status = "BASELINE_ACCEPTED"
            note = "Điểm đã nhận trên mạng OSM nền; giữ nguyên đánh giá trước."
        else:
            status = "REVIEW"
            note = "Chưa đủ căn cứ nhận snap trên mạng ứng viên."
        attributes = [code, site["site_name"], osm_distance, trace_distance, aug_distance,
                      source_near, trace["trace_id"] if source_near == "USER_KML" else None,
                      int(edge["component"]), status, note]
        feature = QgsFeature(candidate_layer.fields())
        feature.setGeometry(nearest_point)
        feature.setAttributes(attributes)
        candidate_layer.dataProvider().addFeatures([feature])
        if status == "USER_APPROVED_FOR_PILOT":
            approved = QgsFeature(approved_layer.fields())
            approved.setGeometry(nearest_point)
            approved.setAttributes(attributes)
            approved_layer.dataProvider().addFeatures([approved])
        reports.append(dict(zip([field.name() for field in candidate_layer.fields()], attributes)))
    candidate_layer.updateExtents()
    approved_layer.updateExtents()

    endpoint_qa = []
    for trace in traces:
        polyline = trace["geometry"].asPolyline()
        crossings = [int(way["osm_id"]) for way in raw_features
                     if trace["geometry"].intersects(way.geometry())]
        endpoint_qa.append({
            "trace_id": trace["trace_id"], "site_code": trace["site_code"],
            "name": trace["name"], "length_km": round(trace["geometry"].length() / 1000, 3),
            "vertices": trace["vertices"], "osm_crossing_count": len(crossings),
            "osm_crossing_ids": crossings,
            "start_nearest_osm": closest_way(QgsGeometry.fromPointXY(polyline[0]), raw_features),
            "end_nearest_osm": closest_way(QgsGeometry.fromPointXY(polyline[-1]), raw_features),
        })
    topology.update({
        "status": "USER_APPROVED_PILOT_NETWORK",
        "geometry_review": "User finalized this working network on 2026-10-17; no independent hydraulic validation of crossings, barriers, or sluice operation",
        "source_kml": str(SOURCE_KML),
        "trace_count": len(traces), "trace_length_km": round(sum(t["geometry"].length() for t in traces) / 1000, 3),
        "tan_hoa_trace_gaps": gap_reports,
        "trace_endpoint_qa": endpoint_qa,
        "pilot5_snap": reports,
        "warning": "KML crossings are noded geometrically, but water connectivity and barriers are not yet field-verified.",
    })

    write_layer(trace_layer, "user_traced_waterways", True)
    write_layer(gap_layer, "tan_hoa_trace_connector", False)
    write_layer(edge_layer, "augmented_network_edges_candidate", False)
    write_layer(candidate_layer, "pilot5_augmented_snap_candidates", False)
    write_layer(approved_layer, "pilot5_user_trace_snap_approved", False)
    with CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=reports[0].keys())
        writer.writeheader()
        writer.writerows(reports)
    JSON.write_text(json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8")

    display = [
        ("user_traced_waterways", "Tim nước KML do người dùng vẽ", line_symbol("#8e44ad", 0.9), True),
        ("tan_hoa_trace_connector", "Khe nối KML Tân Hòa dưới 5 m", line_symbol("#e67e22", 1.1), True),
        ("augmented_network_edges_candidate", "Mạng OSM + KML ứng viên", line_symbol("#e67e22", 0.25), False),
    ]
    for layer_name, title, symbol, visible in display:
        layer = QgsVectorLayer(f"{GPKG}|layername={layer_name}", title, "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Invalid output layer: {layer_name}")
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        project.addMapLayer(layer)
        project.layerTreeRoot().findLayer(layer.id()).setItemVisibilityChecked(visible)
    for layer_name, title, color, visible in [
        ("pilot5_augmented_snap_candidates", "5 điểm snap OSM + KML", "#f1c40f", False),
        ("pilot5_user_trace_snap_approved", "NM29 NM31 snap KML đã chốt", "#9b59b6", True),
    ]:
        layer = QgsVectorLayer(f"{GPKG}|layername={layer_name}", title, "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Invalid output layer: {layer_name}")
        layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
            "name": "diamond", "color": color, "outline_color": "#ffffff", "size": "5"})))
        project.addMapLayer(layer)
        project.layerTreeRoot().findLayer(layer.id()).setItemVisibilityChecked(visible)
    if not project.write(str(QGS)):
        raise RuntimeError(project.error())
    project.clear()
    if not project.read(str(QGS)):
        raise RuntimeError("Could not reopen the KML review project")
    invalid = [layer.name() for layer in project.mapLayers().values() if not layer.isValid()]
    if invalid:
        raise RuntimeError(f"Invalid layers after reopening QGIS project: {invalid}")
    print(json.dumps({"trace_count": len(traces), "trace_km": topology["trace_length_km"],
                      "augmented_edges": topology["edge_count"], "components": topology["component_count"],
                      "tan_hoa_gaps_m": [gap["gap_m"] for gap in gap_reports],
                      "snap_m": {row["site_code"]: round(row["aug_snap_m"], 2) for row in reports},
                      "user_approved": [row["site_code"] for row in reports if row["snap_status"] == "USER_APPROVED_FOR_PILOT"],
                      "gpkg": str(GPKG), "project": str(QGS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
