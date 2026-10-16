"""Screen NM26/NM28/NM33 against the pilot graph without admitting them."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsGeometry, QgsPointXY,
                       QgsProject, QgsSpatialIndex, QgsVectorLayer)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/gis/tiengiang_monitoring/pilot_go_cong_8.csv"
NETWORK = ROOT / "data/processed/gis/go_cong_network/go_cong_user_trace_candidate_32648.gpkg"
OUT = ROOT / "data/processed/gis/go_cong_network/pilot8_expansion_screen"
CODES = ("NM26", "NM28", "NM33")


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    layer = QgsVectorLayer(f"{NETWORK}|layername=augmented_network_edges_candidate", "edges", "ogr")
    if not layer.isValid():
        raise RuntimeError("Missing augmented network")
    features = {feature.id(): feature for feature in layer.getFeatures()}
    index = QgsSpatialIndex(layer.getFeatures())
    transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"),
                                       QgsCoordinateReferenceSystem("EPSG:32648"),
                                       QgsProject.instance().transformContext())
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        source = {row["site_code"]: row for row in csv.DictReader(handle) if row["site_code"] in CODES}
    if set(source) != set(CODES):
        raise RuntimeError("Missing one of NM26/NM28/NM33")
    rows, geojson = [], []
    for code in CODES:
        record = source[code]
        lon, lat = float(record["longitude_deg"]), float(record["latitude_deg"])
        point = QgsGeometry.fromPointXY(QgsPointXY(lon, lat))
        point.transform(transform)
        edge = min((features[fid] for fid in index.nearestNeighbor(point.asPoint(), 32)),
                   key=lambda item: item.geometry().distance(point))
        distance = edge.geometry().distance(point)
        row = {"site_code": code, "site_name_pdf": record["site_name"],
               "pdf_lat": lat, "pdf_lon": lon,
               "nearest_network_m": round(distance, 2),
               "nearest_edge_id": int(edge["edge_id"]),
               "nearest_component": int(edge["component"]),
               "distance_under_100m": distance <= 100,
               "coordinate_status": record["coordinate_status"],
               "decision": "HOLD_COORDINATE_QA",
               "reason": record["coordinate_note"]}
        rows.append(row)
        geojson.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": row})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "pilot8_expansion_coordinate_screen.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "pilot8_expansion_coordinate_screen.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": geojson}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
