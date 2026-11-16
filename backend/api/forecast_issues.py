from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.services import forecast_issues
from backend.auth.current_user import require_role
from backend.auth.roles import Role
from backend.api.dss_storage import same_origin_write

router = APIRouter(prefix='/forecast-issues', tags=['Sổ phát hành dự báo'])
Month = Annotated[str, Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]


class IssueRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target_month: Month
    schedule_code: Literal['MONTHLY_D06_PREV'] = 'MONTHLY_D06_PREV'


@router.post('', status_code=201, dependencies=[Depends(same_origin_write), Depends(require_role(Role.INSPECTOR))])
def issue(payload: IssueRequest):
    return forecast_issues.issue_month(payload.target_month, payload.schedule_code)


@router.get('')
def history(station: str | None = None,
            date_from: Annotated[str | None, Query(alias='from')] = None,
            date_to: Annotated[str | None, Query(alias='to')] = None,
            with_scores: bool = True):
    return forecast_issues.list_issues(station, date_from, date_to, with_scores)
