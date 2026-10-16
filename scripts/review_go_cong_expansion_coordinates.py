"""Keep printed and proposed NM26/NM28/NM33 coordinates separately for QA."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsGeometry, QgsPointXY, QgsProject, QgsSpatialIndex, QgsVectorLayer)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/gis/tiengiang_monitoring/pilot_go_cong_8.csv"
HYPOTHESES = ROOT / "data/processed/gis/tiengiang_monitoring/coordinate_hypotheses_5.csv"
NET = ROOT / "data/processed/gis/go_cong_network/go_cong_user_trace_candidate_32648.gpkg"
OSM = ROOT / "data/processed/gis/go_cong_network/go_cong_waterway_network_32648.gpkg"
OUT = ROOT / "data/processed/gis/go_cong_network/pilot8_expansion_screen"
CODES = ("NM28", "NM33", "NM26")


def load(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main():
    app = QgsApplication([], False)
    app.initQgis()
    edges = QgsVectorLayer(f"{NET}|layername=augmented_network_edges_candidate", "network", "ogr")
    osm = QgsVectorLayer(f"{OSM}|layername=waterways_osm_raw", "osm", "ogr")
    if not edges.isValid() or not osm.isValid():
        raise RuntimeError("Missing reviewed graph or raw OSM layer")
    edge_features = {f.id(): f for f in edges.getFeatures()}
    osm_features = {f.id(): f for f in osm.getFeatures()}
    edge_index = QgsSpatialIndex(edges.getFeatures())
    osm_index = QgsSpatialIndex(osm.getFeatures())
    transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"),
                                       QgsCoordinateReferenceSystem("EPSG:32648"),
                                       QgsProject.instance().transformContext())
    source = {row["site_code"]: row for row in load(SOURCE)}
    candidates = {row["site_code"]: row for row in load(HYPOTHESES)}
    rows, geo = [], []
    for code in CODES:
        entry = source[code]
        options = [("PDF_PRINTED", float(entry["longitude_deg"]), float(entry["latitude_deg"]),
                    f"PDF p.{entry['coordinate_pdf_page']}; printed DMS {entry['longitude_dms_raw']} {entry['latitude_dms_raw']}")]
        if code in candidates:
            hypothesis = candidates[code]
            options.append(("HYPOTHESIS_ROW_SWAP", float(hypothesis["candidate_longitude_deg"]),
                            float(hypothesis["candidate_latitude_deg"]), hypothesis["candidate_reason"]))
        for option, lon, lat, evidence in options:
            metric = QgsGeometry.fromPointXY(QgsPointXY(lon, lat))
            metric.transform(transform)
            nearest_edge = min((edge_features[fid] for fid in edge_index.nearestNeighbor(metric.asPoint(), 32)),
                               key=lambda feature: feature.geometry().distance(metric))
            nearest_osm = min((osm_features[fid] for fid in osm_index.nearestNeighbor(metric.asPoint(), 32)),
                              key=lambda feature: feature.geometry().distance(metric))
            row = {"site_code": code, "site_name_pdf": entry["site_name"],
                   "coordinate_version": option, "latitude_deg": lat, "longitude_deg": lon,
                   "pdf_latitude_deg": float(entry["latitude_deg"]),
                   "pdf_longitude_deg": float(entry["longitude_deg"]),
                   "pdf_latitude_dms": entry["latitude_dms_raw"],
                   "pdf_longitude_dms": entry["longitude_dms_raw"],
                   "nearest_network_m": round(nearest_edge.geometry().distance(metric), 2),
                   "nearest_component": int(nearest_edge["component"]),
                   "nearest_osm_waterway_m": round(nearest_osm.geometry().distance(metric), 2),
                   "nearest_osm_way_id": int(nearest_osm["osm_id"]),
                   "nearest_osm_type": nearest_osm["waterway"] or "",
                   "nearest_osm_name": nearest_osm["name"] or nearest_osm["name_vi"] or "",
                   "coordinate_evidence": evidence,
                   "position_verified": False, "waterbody_verified": False,
                   "sluice_side_verified": False if code == "NM33" else "NOT_APPLICABLE",
                   "pilot_admission": "HOLD"}
            rows.append(row)
            geo.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": row})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "pilot8_coordinate_review_v2.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "pilot8_coordinate_review_v2.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": geo}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (OUT / "coordinate_review_manifest.json").write_text(json.dumps({
        "printed_coordinates_preserved": True,
        "nm28_hypothesis": "Possible NM27/NM28 row swap from PDF appendix; unverified",
        "nm33": "No alternate coordinate; sample location and sluice side unverified",
        "nm26": "No inferred longitude correction; printed 106°04′7.7″ preserved",
        "admission_rule": "No site enters pilot v2 based only on shortest geometric snap distance",
        "nearest_osm_name_interpretation": "Search aid only; nearest way is not verified sample waterbody",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
