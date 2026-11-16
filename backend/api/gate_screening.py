from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.domain.gate_intake_rules import evaluate
from backend.domain.gate_intake_rules import DEFAULT_PROFILE
from backend.auth.current_user import read_optional_user
from fastapi import Depends

router = APIRouter(tags=['Gate screening'])


class ScreeningRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    measurement: dict[str, Any]
    profile: dict[str, Any] | None = None
    forecast_context: dict[str, Any] | None = None
    now_iso: str = Field(max_length=40)


@router.post('/gate-screening/evaluate')
async def gate_screening(request: Request, user=Depends(read_optional_user)):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, 'Phiếu kiểm tra vượt giới hạn 64 KiB.')
    try:
        payload = ScreeningRequest.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, 'Phiếu kiểm tra không đúng cấu trúc.') from exc
    if user is None and payload.profile is not None and payload.profile != DEFAULT_PROFILE:
        raise HTTPException(403, 'Khách chỉ được dùng ngưỡng mặc định.')
    try:
        result = evaluate(payload.measurement, payload.profile, payload.forecast_context, payload.now_iso)
        reasons = {
            'ELIGIBLE_FOR_REVIEW': 'Các điều kiện kiểm tra đạt; người vận hành cần xem xét trước khi thao tác.',
            'NOT_SUITABLE': 'Điều kiện đo hiện tại chưa phù hợp để xem xét lấy nước.',
            'INSUFFICIENT_OR_EXPIRED_DATA': 'Cần bổ sung hoặc đo lại dữ liệu hiện trường.',
        }
        result['summaryReason'] = reasons[result['status']]
        return result if user else {key: result[key] for key in ('status', 'statusTitle', 'summaryReason')}
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(422, str(exc)) from exc
