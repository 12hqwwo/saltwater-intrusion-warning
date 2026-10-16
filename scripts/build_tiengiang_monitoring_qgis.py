"""Build a GeoPackage and QGIS project from the checked PDF transcription.

Run with QGIS's python-qgis-ltr.bat, after extract_tiengiang_monitoring.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsApplication, QgsCategorizedSymbolRenderer, QgsCoordinateReferenceSystem,
    QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject,
    QgsMarkerSymbol, QgsPalLayerSettings, QgsRendererCategory, QgsReferencedRectangle,
    QgsSingleSymbolRenderer, QgsSymbol, QgsTextBufferSettings, QgsTextFormat,
    QgsVectorFileWriter, QgsVectorLayer, QgsVectorLayerSimpleLabeling, QgsWkbTypes,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "gis" / "tiengiang_monitoring"
GPKG = OUT / "tiengiang_ec_34_qa4.gpkg"
QGS = OUT / "go_cong_ec_pilot_qa4.qgs"

FIELDS = [
    ("site_code", QVariant.String), ("site_name", QVariant.String),
    ("lon_dms", QVariant.String), ("lat_dms", QVariant.String),
    ("longitude", QVariant.Double), ("latitude", QVariant.Double),
    ("coord_qa", QVariant.String), ("coord_note", QVariant.String),
    ("pilot", QVariant.Int), ("source_page", QVariant.String),
    ("ec_page", QVariant.Int),
    ("ec_I_mSm", QVariant.Double), ("ec_II_mSm", QVariant.Double),
    ("ec_III_mSm", QVariant.Double), ("ec_IV_mSm", QVariant.Double),
]


def memory_layer(name: str, rows: list[dict]) -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:4326", name, "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField(name, kind) for name, kind in FIELDS])
    layer.updateFields()
    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        if row["longitude_deg"] is not None and row["latitude_deg"] is not None:
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row["longitude_deg"], row["latitude_deg"])))
        feature.setAttributes([
            row["site_code"], row["site_name"], row["longitude_dms_raw"],
            row["latitude_dms_raw"], row["longitude_deg"], row["latitude_deg"],
            row["coordinate_status"], row["coordinate_note"], int(row["pilot_go_cong"]),
            row["coordinate_pdf_page"], row["ec_pdf_page"],
            row["ec_I_ms_m"], row["ec_II_ms_m"], row["ec_III_ms_m"], row["ec_IV_ms_m"],
        ])
        features.append(feature)
    provider.addFeatures(features)
    layer.updateExtents()
    return layer


def write_layer(layer: QgsVectorLayer, name: str, overwrite_file: bool) -> None:
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = name
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteFile if overwrite_file
        else QgsVectorFileWriter.CreateOrOverwriteLayer
    )
    code, message, *_ = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(GPKG), QgsProject.instance().transformContext(), options)
    if code != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"GeoPackage {name}: {message}")


def candidate_layer(rows: list[dict]) -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:4326", "Giả thuyết tọa độ — chưa xác minh", "memory")
    provider = layer.dataProvider()
    fields = [
        ("site_code", QVariant.String), ("site_name", QVariant.String),
        ("source_lon", QVariant.String), ("source_lat", QVariant.String),
        ("candidate_lon", QVariant.String), ("candidate_lat", QVariant.String),
        ("method", QVariant.String), ("qa_status", QVariant.String),
        ("reason", QVariant.String), ("table_page", QVariant.String),
        ("map_page", QVariant.Int),
    ]
    provider.addAttributes([QgsField(name, kind) for name, kind in fields])
    layer.updateFields()
    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(
            row["candidate_longitude_deg"], row["candidate_latitude_deg"])))
        feature.setAttributes([
            row["site_code"], row["site_name"],
            row["source_longitude_dms_raw"], row["source_latitude_dms_raw"],
            row["candidate_longitude_dms"], row["candidate_latitude_dms"],
            row["candidate_method"], row["candidate_status"],
            row["candidate_reason"], row["source_coordinate_pdf_page"],
            row["comparison_map_pdf_page"],
        ])
        features.append(feature)
    provider.addFeatures(features)
    layer.updateExtents()
    return layer


def symbol(color: str, size: float) -> QgsSymbol:
    s = QgsSymbol.defaultSymbol(QgsWkbTypes.PointGeometry)
    s.setColor(QColor(color))
    s.symbolLayer(0).setSize(size)
    return s


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    payload = json.loads((OUT / "monitoring_records.json").read_text(encoding="utf-8"))
    rows = payload["locations"]
    pilots = [row for row in rows if row["pilot_go_cong"]]
    candidates = payload["coordinate_candidates"]
    assert len(rows) == 34 and len(pilots) == 8 and len(candidates) == 5
    all_memory = memory_layer("34 điểm NM1–NM34", rows)
    pilot_memory = memory_layer("Pilot Gò Công: NM26, NM28–NM34", pilots)
    candidate_memory = candidate_layer(candidates)
    write_layer(all_memory, "sites_34", True)
    write_layer(pilot_memory, "pilot_go_cong_8", False)
    write_layer(candidate_memory, "coordinate_hypotheses_5", False)

    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    all_layer = QgsVectorLayer(f"{GPKG}|layername=sites_34", "34 điểm quan trắc (PDF)", "ogr")
    pilot_layer = QgsVectorLayer(f"{GPKG}|layername=pilot_go_cong_8", "Pilot Gò Công — 8 điểm", "ogr")
    candidate_map_layer = QgsVectorLayer(
        f"{GPKG}|layername=coordinate_hypotheses_5",
        "Giả thuyết vị trí (5 điểm, chưa xác minh)", "ogr")
    if not all_layer.isValid() or not pilot_layer.isValid() or not candidate_map_layer.isValid():
        raise RuntimeError("Could not reload GeoPackage layers")
    all_layer.setRenderer(QgsSingleSymbolRenderer(symbol("#a7adb8", 2.2)))
    pilot_layer.setRenderer(QgsCategorizedSymbolRenderer("coord_qa", [
        QgsRendererCategory("DMS_TRANSCRIBED", symbol("#1776bf", 3.6), "Tọa độ từ PDF"),
        QgsRendererCategory("REVIEW_POSITION", symbol("#d43f35", 4.4), "Cần xác minh vị trí"),
    ]))
    labels = QgsPalLayerSettings()
    labels.fieldName = "site_code"
    label_format = QgsTextFormat()
    label_format.setSize(9)
    label_format.setColor(QColor("#233044"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1)
    buffer.setColor(QColor("#ffffff"))
    label_format.setBuffer(buffer)
    labels.setFormat(label_format)
    pilot_layer.setLabeling(QgsVectorLayerSimpleLabeling(labels))
    pilot_layer.setLabelsEnabled(True)
    candidate_map_layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({
        "name": "diamond", "color": "#ffb020", "outline_color": "#7c4a03", "size": "4.5",
    })))
    candidate_labels = QgsPalLayerSettings()
    candidate_labels.fieldName = '"site_code" || \' ?\''
    candidate_labels.isExpression = True
    candidate_labels.setFormat(label_format)
    candidate_map_layer.setLabeling(QgsVectorLayerSimpleLabeling(candidate_labels))
    candidate_map_layer.setLabelsEnabled(True)
    all_layer.setDisplayExpression('"site_code" || \' — \' || "site_name"')
    pilot_layer.setDisplayExpression('"site_code" || \' — \' || "site_name"')
    project.addMapLayer(all_layer)
    project.addMapLayer(pilot_layer)
    project.addMapLayer(candidate_map_layer)
    project.layerTreeRoot().findLayer(all_layer.id()).setItemVisibilityChecked(False)
    project.layerTreeRoot().findLayer(pilot_layer.id()).setItemVisibilityChecked(True)
    project.layerTreeRoot().findLayer(candidate_map_layer.id()).setItemVisibilityChecked(True)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(pilot_layer.extent(), pilot_layer.crs()))
    if not project.write(str(QGS)):
        raise RuntimeError(f"Could not save QGIS project: {project.error()}")
    QGS.with_name(QGS.name + "~").unlink(missing_ok=True)
    print(f"Saved {GPKG} and {QGS}; layers: {all_layer.featureCount()}, {pilot_layer.featureCount()}, {candidate_map_layer.featureCount()}")


if __name__ == "__main__":
    main()
