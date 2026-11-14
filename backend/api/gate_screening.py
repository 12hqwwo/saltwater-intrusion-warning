"""Stateless, read-only-in-effect gate screening endpoint."""
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.domain.gate_intake_rules import evaluate

router = APIRouter(tags=['Gate screening'])


class ScreeningRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    measurement: dict[str, Any]
    profile: dict[str, Any] | None = None
    forecast_context: dict[str, Any] | None = None
    now_iso: str = Field(max_length=40)


@router.post('/gate-screening/evaluate')
async def gate_screening(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, 'Phiếu kiểm tra vượt giới hạn 64 KiB.')
    try:
        payload = ScreeningRequest.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, 'Phiếu kiểm tra không đúng cấu trúc.') from exc
    try:
        return evaluate(payload.measurement, payload.profile, payload.forecast_context, payload.now_iso)
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(422, str(exc)) from exc
