"""HTTP contracts for multivariate monthly EC inference."""
from typing import Annotated, Literal
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from backend.services import multivariate

router = APIRouter(prefix='/multivariate', tags=['Dự báo EC đa biến'])
Month = Annotated[str, Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    station: str = Field(min_length=1, max_length=64)
    target_month: Month
    input_mode: Literal['ARCHIVE', 'MANUAL'] = 'ARCHIVE'
    rainfall_mm: float | None = Field(default=None, ge=0, le=20000, allow_inf_nan=False, strict=True)
    temperature_degC: float | None = Field(default=None, ge=-90, le=65, allow_inf_nan=False, strict=True)
    wind_source_units: float | None = Field(default=None, ge=0, le=150, allow_inf_nan=False, strict=True)


@router.get('/catalog')
def catalog():
    return multivariate.catalog()


@router.get('/inputs')
def inputs(station: Annotated[str, Query(min_length=1, max_length=64)], target_month: Month):
    return multivariate.inputs(station, target_month)


@router.get('/evaluation')
def evaluation(station: Annotated[str, Query(min_length=1, max_length=64)]):
    return multivariate.evaluation(station)


@router.post('/predict')
def predict(payload: ForecastRequest):
    return multivariate.predict(payload.model_dump())
