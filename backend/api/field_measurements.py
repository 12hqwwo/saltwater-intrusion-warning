"""Staff-only EC field submissions and independent review key."""
import hmac
import os
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.api.dss_storage import same_origin_write
from backend.security import actor
from backend.services import field_measurements as service

router = APIRouter(prefix='/field-measurements', tags=['Phiếu EC thực địa'])


def _key(request: Request, name: str):
    expected = os.getenv(name, '')
    if not expected:
        raise HTTPException(503, f'{name} chưa được cấu hình cho cán bộ nội bộ.')
    if not hmac.compare_digest(request.headers.get('x-api-key', '').encode(), expected.encode()):
        raise HTTPException(401, 'API key không hợp lệ hoặc còn thiếu.')


def require_submit_key(request: Request):
    _key(request, 'WEBGIS_WRITE_API_KEY')


def require_review_key(request: Request):
    _key(request, 'WEBGIS_REVIEW_API_KEY')


class FieldRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ec: float = Field(allow_inf_nan=False)
    unit: Literal['µS/cm', 'dS/m', 'mS/cm', 'mS/m']
    observed_at: str = Field(min_length=20, max_length=40)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    position_kind: Literal['RIVER', 'FIELD']
    device: str = Field(min_length=1, max_length=120)
    submitted_by: str = Field(min_length=1, max_length=120)
    ec_basis: Literal['EC25', 'RAW', 'UNKNOWN'] = 'UNKNOWN'
    calibrated_at: str | None = None
    calibration_reference: str | None = Field(default=None, max_length=120)
    water_temp_degC: float | None = Field(default=None, allow_inf_nan=False)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['APPROVED', 'REJECTED']
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default='', max_length=2000)


@router.post('', status_code=201, dependencies=[Depends(same_origin_write), Depends(require_submit_key)])
async def submit(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 16384:
            raise HTTPException(413, 'Phiếu số đo vượt giới hạn 16 KiB.')
    try:
        payload = FieldRequest.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, 'Phiếu số đo không đúng cấu trúc.') from exc
    return service.submit(payload.model_dump())


@router.get('')
def measurements(request: Request, status: Literal['PENDING', 'APPROVED', 'REJECTED'] | None = None,
                 bbox: Annotated[str | None, Query(max_length=100)] = None):
    if status != 'APPROVED':
        require_review_key(request)
    return service.list_measurements(status, bbox)


@router.post('/{measurement_id}/review', dependencies=[Depends(same_origin_write), Depends(require_review_key)])
def review(measurement_id: UUID, payload: ReviewRequest):
    token = actor.set('REVIEW_KEY_CLIENT')
    try:
        return service.review(measurement_id, payload.decision, payload.reviewer, payload.note)
    finally:
        actor.reset(token)
