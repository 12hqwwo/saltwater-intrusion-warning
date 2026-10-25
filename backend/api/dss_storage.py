"""Optional DSS persistence endpoints; independent from the inference endpoint."""
import json
import os
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from backend.api.multivariate import ForecastRequest, Month
from backend.services import dss_storage

router = APIRouter(tags=['DSS storage'])
GateCode = Annotated[str, Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=1000000)]


def same_origin_write(request: Request):
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/')} | {
        item.strip() for item in os.getenv('WEBGIS_CORS_ORIGINS',
            'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173').split(',')}
    if origin and origin not in allowed:
        raise HTTPException(403, 'DSS write origin is not allowed.')
    if request.headers.get('content-type', '').split(';')[0].lower() != 'application/json':
        raise HTTPException(415, 'DSS writes require application/json.')


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    gate_code: GateCode
    input: dict
    policy: dict


@router.get('/threshold-presets')
def presets():
    return dss_storage.presets()


@router.get('/multivariate/history')
def history(station: Annotated[str | None, Query(max_length=64)] = None,
            target_month: Month | None = None, limit: Limit = 20, offset: Offset = 0):
    return dss_storage.predictions(station, target_month, limit, offset)


@router.get('/multivariate/history/{prediction_id}')
def saved_prediction(prediction_id: UUID):
    return dss_storage.prediction(prediction_id)


@router.post('/multivariate/history', dependencies=[Depends(same_origin_write)])
def save_prediction(payload: ForecastRequest):
    return dss_storage.save_prediction(payload.model_dump())


@router.get('/gate-drafts')
def drafts(gate_code: GateCode, limit: Limit = 20, offset: Offset = 0):
    return dss_storage.drafts(gate_code, limit, offset)


@router.post('/gate-drafts', dependencies=[Depends(same_origin_write)])
async def save_draft(request: Request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 262144:
            raise HTTPException(413, 'Dossier exceeds 256 KiB.')
        chunks.append(chunk)
    try:
        def invalid_constant(value):
            raise ValueError('Non-finite JSON number.')
        payload = DraftRequest.model_validate(json.loads(b''.join(chunks), parse_constant=invalid_constant))
    except (ValueError, TypeError, RecursionError, ValidationError) as exc:
        raise HTTPException(422, 'Expected gate_code, input and policy objects containing finite JSON values.') from exc
    return await run_in_threadpool(dss_storage.save_draft, payload.gate_code, payload.input, payload.policy)
