"""Chạy từ gốc repo: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000."""

import logging
import os
from datetime import date
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.database import DatasetNotFound, Repository, SiteNotFound
from backend.schemas import (
    DatasetCollection, ECHistory, Health, HistoryFilters, ObservationKind,
    QualityFlag, StationCollection, StationFeature, StationProperties,
)

logger = logging.getLogger("webgis.api")
app = FastAPI(
    title="WebGIS Đồng Tháp — API dữ liệu lịch sử",
    version="0.1.0",
    description=(
        "Đọc trạm và EC từ PostgreSQL/PostGIS. Đơn vị mS/m; giữ cờ chất lượng nguồn. "
        "Chọn rõ snapshot bằng dataset_code khi đọc lịch sử."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in os.getenv(
            "WEBGIS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


def get_repository() -> Repository:
    # No connection here: invalid requests can return 422 while PostgreSQL is offline.
    return Repository()


Repo = Annotated[Repository, Depends(get_repository)]
SiteCode = Annotated[str, Path(min_length=1, max_length=64)]


@app.exception_handler(SiteNotFound)
async def site_not_found(request: Request, exc: SiteNotFound):
    return JSONResponse(status_code=404, content={"detail": {
        "code": "SITE_NOT_FOUND", "message": "Không tìm thấy trạm trong dữ liệu thật."
    }})


@app.exception_handler(DatasetNotFound)
async def dataset_not_found(request: Request, exc: DatasetNotFound):
    return JSONResponse(status_code=404, content={"detail": {
        "code": "DATASET_NOT_FOUND",
        "message": "Bộ dữ liệu không có quan trắc EC của trạm này; xem endpoint datasets."
    }})


@app.exception_handler(psycopg.Error)
async def database_error(request: Request, exc: psycopg.Error):
    # Do not send SQL, passwords or raw connection errors to the browser/log.
    logger.error("Database error: %s; SQLSTATE=%s", type(exc).__name__, exc.sqlstate or "unknown")
    if exc.sqlstate in {"42P01", "42703", "42883"}:
        code, message = "DB_SCHEMA_MISMATCH", "Schema hoặc PostGIS chưa khớp với API."
    elif exc.sqlstate == "42501":
        code, message = "DB_PERMISSION_DENIED", "Tài khoản PostgreSQL thiếu quyền đọc dữ liệu."
    else:
        code, message = "DATABASE_ERROR", "Không đọc được PostgreSQL; kiểm tra kết nối và tài khoản."
    return JSONResponse(status_code=503, content={"detail": {"code": code, "message": message}})


@app.get("/api/v1/health", response_model=Health, tags=["Kiểm tra"])
def health(repo: Repo):
    """Kiểm tra kết nối thật và chế độ transaction chỉ đọc."""
    return repo.health()


@app.get("/api/v1/stations", response_model=StationCollection, tags=["Trạm"])
def stations(repo: Repo):
    """GeoJSON: tọa độ [kinh độ, vĩ độ]; trạm thiếu vị trí có geometry=null."""
    features = [
        StationFeature(
            id=row["site_code"], geometry=row["geometry"],
            properties=StationProperties(**row),
        )
        for row in repo.stations()
    ]
    return StationCollection(features=features, count=len(features))


@app.get("/api/v1/stations/{site_code}/datasets", response_model=DatasetCollection, tags=["EC"])
def datasets(site_code: SiteCode, repo: Repo):
    """Liệt kê các snapshot EC của một trạm để người gọi chọn dataset_code."""
    return DatasetCollection(site_code=site_code, items=repo.datasets(site_code))


@app.get("/api/v1/stations/{site_code}/observations", response_model=ECHistory, tags=["EC"])
def observations(
    site_code: SiteCode,
    repo: Repo,
    dataset_code: Annotated[str, Query(min_length=1, max_length=96)],
    date_from: Annotated[date | None, Query(description="Ngày bắt đầu theo giờ Việt Nam, YYYY-MM-DD.")] = None,
    date_to: Annotated[date | None, Query(description="Ngày kết thúc, tính cả ngày theo giờ Việt Nam.")] = None,
    quality_flag: QualityFlag | None = None,
    observed_or_estimated: ObservationKind | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
):
    """EC gốc theo một snapshot. Mặc định giữ tất cả cờ, gồm UNVERIFIED và INVALID."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from phải nhỏ hơn hoặc bằng date_to.")
    if date_to == date.max:
        raise HTTPException(status_code=422, detail="date_to phải trước ngày 9999-12-31.")
    result = repo.history(
        site_code=site_code, dataset_code=dataset_code,
        date_from=date_from, date_to=date_to, quality_flag=quality_flag,
        observed_or_estimated=observed_or_estimated, limit=limit, offset=offset,
    )
    return ECHistory(
        site_code=site_code,
        dataset=result["dataset"],
        filters=HistoryFilters(
            date_from=date_from, date_to=date_to,
            quality_flag=quality_flag, observed_or_estimated=observed_or_estimated,
        ),
        total=result["total"], limit=limit, offset=offset,
        has_more=offset + len(result["items"]) < result["total"],
        items=result["items"],
    )
