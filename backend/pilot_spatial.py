"""Read-only pilot spatial evidence API. No synthetic EC or unverified forecast."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


ROOT = Path(__file__).resolve().parents[1]
GIS = ROOT / "data/processed/gis/go_cong_network"
MONITORING = ROOT / "data/processed/gis/tiengiang_monitoring"
WEBGIS = ROOT / "webgis/pilot_spatial.html"
PILOT = {"NM29", "NM30", "NM31", "NM32", "NM34"}
router = APIRouter(prefix="/pilot/spatial", tags=["Spatial pilot"])


def rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Pilot artifact unavailable: {path.name}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def geojson(path: Path) -> dict:
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Pilot layer unavailable: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/sites")
def sites():
    reviewed = rows(GIS / "pilot5_coordinate_review.csv")
    snap = {row["site_code"]: row for row in rows(GIS / "pilot5_user_trace_snap_qa.csv")}
    values = rows(MONITORING / "ec_campaigns_136.csv")
    ec = {}
    for row in values:
        if row["site_code"] in PILOT:
            ec.setdefault(row["site_code"], {})[row["campaign"]] = float(row["ec_ms_m"])
    features = []
    for row in reviewed:
        code = row["site_code"]
        if code not in PILOT:
            continue
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": [float(row["review_lon"]), float(row["review_lat"])]},
                         "properties": {"site_code": code, "name": row["working_name"],
                                        "coordinate_status": row["coordinate_status"],
                                        "snap_distance_m": round(float(snap[code]["aug_snap_m"]), 2),
                                        "snap_status": snap[code]["snap_status"],
                                        "ec_ms_m_by_campaign": ec.get(code, {}),
                                        "campaign_dates_known": False,
                                        "topology_status": "GRAPH_APPROVED_HYDRAULICS_UNVERIFIED"}})
    if len(features) != 5 or any(len(f["properties"]["ec_ms_m_by_campaign"]) != 4 for f in features):
        raise HTTPException(status_code=503, detail="Pilot-5 source is incomplete")
    return {"type": "FeatureCollection", "features": features}


@router.get("/routes")
def routes():
    return geojson(GIS / "pilot5_route_audit/pilot5_shortest_routes.geojson")


@router.get("/crossings")
def crossings():
    return geojson(GIS / "pilot5_topology_scenarios/crossing_cluster.geojson")


@router.get("/coordinate-candidates")
def coordinate_candidates():
    return geojson(GIS / "pilot8_expansion_screen/pilot8_coordinate_review_v2.geojson")


@router.get("/metrics")
def metrics():
    return {"unit": "mS/m", "validation": "leave-one-location-out per undated campaign I-IV",
            "rows": rows(GIS / "pilot5_topology_scenarios/scenario_metrics.csv")}


@router.get("/predictions")
def predictions():
    return {"unit": "mS/m", "rows": rows(GIS / "pilot5_topology_scenarios/scenario_lolo_predictions.csv")}


@router.get("/map", include_in_schema=False)
def map_page():
    if not WEBGIS.is_file():
        raise HTTPException(status_code=503, detail="WebGIS page unavailable")
    return FileResponse(WEBGIS, media_type="text/html; charset=utf-8")
