"""Read-only HTTP adapter for the Pilot Gò Công spatial repository."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.pilot_spatial_repository import PilotArtifactUnavailable, repository


ROOT = Path(__file__).resolve().parents[1]
WEBGIS = ROOT / "webgis/pilot_spatial.html"
DATA_SERVICE = ROOT / "webgis/pilot_spatial_data_service.js"
router = APIRouter(prefix="/pilot/spatial", tags=["Spatial pilot"])


def from_repository(method):
    """Translate repository failures into a stable read-only API response."""
    try:
        return method()
    except PilotArtifactUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/sites")
def sites():
    return from_repository(repository.sites)


@router.get("/routes")
def routes():
    return from_repository(repository.routes)


@router.get("/crossings")
def crossings():
    return from_repository(repository.crossings)


@router.get("/coordinate-candidates")
def coordinate_candidates():
    return from_repository(repository.coordinate_candidates)


@router.get("/metrics")
def metrics():
    return from_repository(repository.metrics)


@router.get("/predictions")
def predictions():
    return from_repository(repository.predictions)


@router.get("/waterways")
def waterways():
    return from_repository(repository.waterways)


@router.get("/data-service.js", include_in_schema=False)
def data_service():
    if not DATA_SERVICE.is_file():
        raise HTTPException(status_code=503, detail="WebGIS data service unavailable")
    return FileResponse(DATA_SERVICE, media_type="text/javascript; charset=utf-8")


@router.get("/map", include_in_schema=False)
def map_page():
    if not WEBGIS.is_file():
        raise HTTPException(status_code=503, detail="WebGIS page unavailable")
    return FileResponse(WEBGIS, media_type="text/html; charset=utf-8")
