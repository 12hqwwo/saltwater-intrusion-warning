"""Read-only geometry audit of the user-drawn waterway KML against OSM."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer,
)


ROOT = Path(__file__).resolve().parents[1]
KML = ROOT / "data/raw/gis/user_review_20261017/ban_do_nhanh_song_v2.kml"
GPKG = ROOT / "data/processed/gis/go_cong_network/go_cong_waterway_network_32648.gpkg"
COORDS = ROOT / "data/processed/gis/go_cong_network/pilot5_coordinate_review.csv"


def nearest_osm(geometry: QgsGeometry, osm: list) -> dict:
    way = min(osm, key=lambda feature: feature.geometry().distance(geometry))
    return {
        "osm_id": int(way["osm_id"]),
        "name": way["name"],
        "waterway": way["waterway"],
        "distance_m": round(way.geometry().distance(geometry), 2),
    }


def main() -> None:
    app = QgsApplication([], False)
    app.initQgis()
    raw_layer = QgsVectorLayer(f"{GPKG}|layername=waterways_osm_raw", "OSM", "ogr")
    if not raw_layer.isValid():
        raise RuntimeError("Missing OSM raw layer")
    osm = list(raw_layer.getFeatures())
    source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    target_crs = QgsCoordinateReferenceSystem("EPSG:32648")
    transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
    with COORDS.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    sites = {}
    for row in rows:
        geometry = QgsGeometry.fromPointXY(QgsPointXY(float(row["review_lon"]), float(row["review_lat"])))
        geometry.transform(transform)
        sites[row["site_code"]] = geometry
    root = ET.parse(KML).getroot()
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    lines = []
    for placemark in root.findall(".//k:Placemark", ns):
        name = placemark.findtext("k:name", default="", namespaces=ns)
        coordinates = placemark.findtext(".//k:LineString/k:coordinates", default="", namespaces=ns)
        if not coordinates.strip():
            continue
        points = [QgsPointXY(*map(float, item.split(",")[:2])) for item in coordinates.split()]
        geom = QgsGeometry.fromPolylineXY(points)
        geom.transform(transform)
        line = geom.asPolyline()
        start, end = (QgsGeometry.fromPointXY(QgsPointXY(point)) for point in (line[0], line[-1]))
        crossings = [int(way["osm_id"]) for way in osm if geom.intersects(way.geometry())]
        lines.append({
            "name": name,
            "geometry": geom,
            "length_km": round(geom.length() / 1000, 3),
            "vertices": len(points),
            "start_lonlat": [points[0].x(), points[0].y()],
            "end_lonlat": [points[-1].x(), points[-1].y()],
            "start_nearest_osm": nearest_osm(start, osm),
            "end_nearest_osm": nearest_osm(end, osm),
            "site_distances_m": {code: round(geom.distance(site), 2) for code, site in sites.items()},
            "osm_intersected_count": len(crossings),
            "osm_intersected_ids_first20": crossings[:20],
        })
    for left in range(len(lines)):
        lines[left]["other_kml_distances_m"] = {
            str(right + 1): round(lines[left]["geometry"].distance(lines[right]["geometry"]), 2)
            for right in range(len(lines)) if right != left
        }
    for line in lines:
        del line["geometry"]
    print(json.dumps(lines, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
