"""Frozen monthly EC issue and one-label scoring rules."""
import hashlib
import json
import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

SCHEDULE_CODE = 'MONTHLY_D06_PREV'
LABEL_PROTOCOL_VERSION = 'MONTHLY_EC_LABEL_V1_20261114'
LOCAL_TZ = ZoneInfo('Asia/Ho_Chi_Minh')
STATIONS = ('MYTHO', 'MYTHUAN', 'TANCHAU')
LEDGER_START_LOCAL = date(2026, 11, 14)


def _shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def schedule(target_month: str) -> datetime:
    target = date.fromisoformat(target_month + '-01')
    previous = _shift_month(target, -1)
    return datetime(previous.year, previous.month, 6, 9, tzinfo=LOCAL_TZ)


def build_issue(prediction: dict, issued_at: datetime) -> dict:
    if issued_at.tzinfo is None:
        raise ValueError('issued_at needs a timezone')
    target = date.fromisoformat(prediction['target_month'] + '-01')
    input_month = _shift_month(target, -2).strftime('%Y-%m')
    if prediction.get('input_month') != input_month or prediction.get('input_mode') != 'ARCHIVE':
        raise ValueError('The blind issue requires complete archived t-2 inputs')
    model_sha = prediction.get('model_provenance', {}).get('model_sha256')
    if not isinstance(model_sha, str) or len(model_sha) != 64:
        raise ValueError('Missing pinned model hash')
    ec = prediction.get('predicted_ec_mS_m')
    if isinstance(ec, bool) or not isinstance(ec, (int, float)) or not math.isfinite(ec) or ec < 0:
        raise ValueError('Invalid forecast EC')
    provenance = dict(weather=prediction.get('input_provenance'),
                      hydrology=prediction.get('hydrology_provenance'))
    data_version = hashlib.sha256(json.dumps(provenance, sort_keys=True, ensure_ascii=False,
                                             separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
    return dict(station_key=str(prediction['station']).upper(), target_month=prediction['target_month'],
                input_month=input_month, model_version=prediction['model_version'],
                model_sha256=model_sha, data_version=data_version,
                predicted_ec_mS_m=float(ec), payload=prediction,
                issued_at=issued_at.isoformat())


def score(issue: dict, observation: dict) -> dict | None:
    source = observation.get('obs_source')
    if source not in ('MRC', 'FIELD_APPROVED'):
        return None
    if observation.get('equivalent_monthly_label') is not True:
        return None
    if observation.get('label_protocol_version') != LABEL_PROTOCOL_VERSION:
        return None
    try:
        observed_at = datetime.fromisoformat(observation['observed_at'].replace('Z', '+00:00'))
        if observed_at.tzinfo is None or observed_at.astimezone(LOCAL_TZ).strftime('%Y-%m') != issue['target_month']:
            return None
        value = float(observation['observed_ec_mS_m'])
        predicted = float(issue['predicted_ec_mS_m'])
        if not math.isfinite(value) or value < 0 or not math.isfinite(predicted) or predicted < 0:
            return None
        ref = observation['observation_ref']
        if not isinstance(ref, str) or not ref.strip():
            return None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    return dict(label_protocol_version=LABEL_PROTOCOL_VERSION, observation_ref=ref,
                obs_source=source, observed_ec_mS_m=value,
                abs_error_mS_m=abs(value - predicted))
