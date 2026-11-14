"""Normalize submitted field EC without promoting it to MRC observation data."""
import math
from datetime import datetime, timedelta

CONVERSIONS = {'µS/cm': 0.1, 'dS/m': 100.0, 'mS/cm': 100.0, 'mS/m': 1.0}


def normalize(raw: dict, now: datetime, reference_median_mS_m: float | None = None) -> dict:
    if now.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    unit = raw.get('unit')
    if unit not in CONVERSIONS:
        raise ValueError('UNIT_UNKNOWN')
    ec = raw.get('ec')
    if isinstance(ec, bool) or not isinstance(ec, (int, float)) or not math.isfinite(ec):
        raise ValueError('EC_OUT_OF_RANGE')
    converted = ec * CONVERSIONS[unit]
    if not math.isfinite(converted) or converted < 0 or converted > 6000:
        raise ValueError('EC_OUT_OF_RANGE')
    try:
        observed = datetime.fromisoformat(raw['observed_at'].replace('Z', '+00:00'))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError('INVALID_TIMESTAMP') from exc
    if observed.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    if observed > now + timedelta(minutes=10):
        raise ValueError('FUTURE_TIMESTAMP')
    if observed < now - timedelta(days=365):
        raise ValueError('TOO_OLD')
    longitude, latitude = raw.get('longitude'), raw.get('latitude')
    if (any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in (longitude, latitude)) or not -180 <= longitude <= 180 or not -90 <= latitude <= 90):
        raise ValueError('INVALID_COORDINATE')
    if raw.get('position_kind') not in ('RIVER', 'FIELD'):
        raise ValueError('POSITION_KIND_UNKNOWN')
    if not isinstance(raw.get('device'), str) or not raw['device'].strip():
        raise ValueError('DEVICE_REQUIRED')
    if not isinstance(raw.get('submitted_by'), str) or not 1 <= len(raw['submitted_by'].strip()) <= 120:
        raise ValueError('SUBMITTER_REQUIRED')
    basis = raw.get('ec_basis', 'UNKNOWN')
    if basis not in ('EC25', 'RAW', 'UNKNOWN'):
        raise ValueError('EC_BASIS_UNKNOWN')
    temperature = raw.get('water_temp_degC')
    if temperature is not None and (isinstance(temperature, bool) or not isinstance(temperature, (int, float))
                                    or not math.isfinite(temperature) or not -5 <= temperature <= 50):
        raise ValueError('INVALID_TEMPERATURE')
    calibrated = raw.get('calibrated_at')
    calibration_reference = raw.get('calibration_reference')
    if calibration_reference is not None and (not isinstance(calibration_reference, str) or len(calibration_reference) > 120):
        raise ValueError('INVALID_CALIBRATION_REFERENCE')
    if calibrated is not None:
        try:
            calibrated = datetime.fromisoformat(calibrated).date()
        except (ValueError, TypeError) as exc:
            raise ValueError('INVALID_CALIBRATION_DATE') from exc
        if calibrated > observed.date():
            raise ValueError('INVALID_CALIBRATION_DATE')
    flags = []
    if (reference_median_mS_m is not None and math.isfinite(reference_median_mS_m)
            and reference_median_mS_m >= 0 and converted > 3 * reference_median_mS_m):
        flags.append('REVIEW_HIGH')
    if basis != 'EC25':
        flags.append('NO_EC25')
    if calibrated is None or (observed.date() - calibrated).days > 30 or not calibration_reference or not calibration_reference.strip():
        flags.append('CALIBRATION_UNVERIFIED')
    return dict(ec_mS_m=converted, unit_original=unit, flags=flags,
                observed_at=observed, longitude=float(longitude), latitude=float(latitude),
                water_temp_degC=temperature, position_kind=raw['position_kind'],
                device=raw['device'].strip(), submitted_by=raw['submitted_by'].strip(),
                ec_basis=basis, calibrated_at=calibrated,
                calibration_reference=calibration_reference.strip() if calibration_reference else None)
