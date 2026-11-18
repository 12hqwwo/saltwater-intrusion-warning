from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.api.dss_storage import same_origin_write
from backend.auth.current_user import AuthenticatedUser, read_optional_user, require_role
from backend.auth.roles import Role
from backend.services import field_measurements as service

router = APIRouter(prefix='/field-measurements', tags=['Phiếu EC thực địa'])


class FieldRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ec: float = Field(allow_inf_nan=False)
    unit: Literal['µS/cm', 'dS/m', 'mS/cm', 'mS/m']
    observed_at: str = Field(min_length=20, max_length=40)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    position_kind: Literal['RIVER', 'FIELD']
    device: str = Field(min_length=1, max_length=120)
    ec_basis: Literal['EC25', 'RAW', 'UNKNOWN'] = 'UNKNOWN'
    calibrated_at: str | None = None
    calibration_reference: str | None = Field(default=None, max_length=120)
    water_temp_degC: float | None = Field(default=None, allow_inf_nan=False)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['APPROVED', 'REJECTED']
    note: str = Field(default='', max_length=2000)


@router.post('', status_code=201, dependencies=[Depends(same_origin_write)])
async def submit(request: Request, user: AuthenticatedUser = Depends(require_role(Role.FIELD_STAFF))):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 16384:
            raise HTTPException(413, 'Phiếu số đo vượt giới hạn 16 KiB.')
    try:
        payload = FieldRequest.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, 'Phiếu số đo không đúng cấu trúc.') from exc
    return await run_in_threadpool(service.submit, payload.model_dump() | {'submitted_by': user.username})


@router.get('/mine')
def mine(user: AuthenticatedUser = Depends(require_role(Role.FIELD_STAFF))):
    return service.list_measurements(submitted_by=user.username)


@router.get('')
def measurements(request: Request, status: Literal['PENDING', 'APPROVED', 'REJECTED'] | None = None,
                 bbox: Annotated[str | None, Query(max_length=100)] = None,
                 user: AuthenticatedUser | None = Depends(read_optional_user)):
    if status != 'APPROVED':
        if user is None:
            raise HTTPException(401, 'Cần đăng nhập để xem phiếu chưa duyệt.')
        if user.role != Role.INSPECTOR:
            raise HTTPException(403, 'Chỉ cán bộ kiểm tra được xem hàng chờ duyệt.')
    return service.list_measurements(status, bbox)


@router.post('/{measurement_id}/review', dependencies=[Depends(same_origin_write)])
def review(measurement_id: UUID, payload: ReviewRequest,
           user: AuthenticatedUser = Depends(require_role(Role.INSPECTOR))):
    return service.review(measurement_id, payload.decision, user.username, payload.note)
