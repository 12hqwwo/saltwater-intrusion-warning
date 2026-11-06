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
def evaluation(station: Annotated[str, Query(min_length=1, max_length=64)],
               protocol: Literal['HISTORICAL', 'FROZEN_EC_WEATHER_ONLY_V1'] = 'HISTORICAL',
               experiment: Literal['gap_2019_2021', 'gap_2021_2023', 'gap_2022_2023'] | None = None,
               ec_delay_days: Literal['5', '35'] = '5'):
    return multivariate.evaluation(station, protocol, experiment, int(ec_delay_days))


@router.post('/predict')
def predict(payload: ForecastRequest):
    return multivariate.predict(payload.model_dump())
