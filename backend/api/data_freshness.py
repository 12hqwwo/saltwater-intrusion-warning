"""Read-only source currency report for the operational overview."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from backend.domain.data_freshness import assess
from backend.repositories.hydrology_inputs import _matrix, _signature
from backend.repositories.multivariate_inputs import get_monthly_weather

router = APIRouter(tags=['Data freshness'])


def _weather(station: str, today):
    rows = get_monthly_weather(station)
    if not rows:
        return dict(status='UNAVAILABLE', last_source_month=None,
                    next_target_month_supported=None, days_until_stale=None,
                    retrieved_at=None, availability_basis='No complete verified ERA5 month is available.')
    last = rows[-1]
    return assess(last['input_month'], today, retrieved_at=last.get('retrieved_at'))


def _hydrology(today):
    frame = _matrix(_signature())
    result = {}
    for name, column in (('KRATIE_Q', 'kratie_q_t2'), ('TANCHAU_STAGE', 'tc_stage_t2')):
        valid = frame[frame[column].map(math.isfinite)]
        if valid.empty:
            result[name] = dict(status='UNAVAILABLE', last_source_month=None,
                                next_target_month_supported=None, days_until_stale=None,
                                retrieved_at=None, availability_basis='No complete month with at least 20 daily values.')
        else:
            result[name] = assess(valid.iloc[-1]['weather_month'].strftime('%Y-%m'), today)
            result[name]['availability_basis'] += ' Monthly source requires at least 20 days.'
    return result


def report(today=None):
    today = today or datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
    sources = {f'ERA5_{station.upper()}': _weather(station, today)
               for station in ('MyTho', 'TanChau', 'MyThuan')}
    sources.update(_hydrology(today))
    sources['MRC_EC_MYTHO'] = dict(status='STALE', last_source_month='2023-12',
        last_observation='2023-12-15', next_target_month_supported=None,
        days_until_stale=None, retrieved_at=None,
        availability_basis='Last EC label in the frozen MRC training snapshot; no new observation is inferred.')
    return dict(as_of=today.isoformat(), sources=sources)


@router.get('/data-freshness')
def data_freshness():
    return report()
