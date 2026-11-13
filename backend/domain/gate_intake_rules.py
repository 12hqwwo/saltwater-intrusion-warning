"""Server evaluation of the configured gate intake screening rule."""
import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone


DEFAULT_PROFILE = dict(
    ruleId='MYTHO_TIEN_RIVER_INTAKE_SCREENING', ruleVersion='TECH_SCREENING_RULE_V1.0',
    ruleName='Kiểm tra kỹ thuật điều kiện xem xét lấy nước sông Tiền',
    ruleNatureNotice='Quy tắc kỹ thuật cấu hình để kiểm tra nhất quán trên WebGIS (không thay thế quy trình vận hành pháp lý của đơn vị quản lý công trình)',
    maxExteriorEcMsM=156.25, maxInteriorEcMsM=125, minPositiveHeadDiffM=0.05,
    requireSameDatum=True, requireMechanicalReady=True,
    maxSampleAgeHoursNormal=6, maxSampleAgeHoursHighVigilance=2, p90ReferenceEcMsM=60.42,
)
STATUS_TITLES = dict(ELIGIBLE_FOR_REVIEW='Đề nghị xem xét lấy nước',
    NOT_SUITABLE='Chưa phù hợp để lấy nước',
    INSUFFICIENT_OR_EXPIRED_DATA='Cần bổ sung hoặc đo lại')
NUMBER = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$', re.I)
STAMP = re.compile(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:\d{2})$')


def _text(value):
    return value.strip() if isinstance(value, str) else ''


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    if isinstance(value, str) and not NUMBER.fullmatch(value.strip()):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, OverflowError):
        return None


def _nonnegative(value):
    number = _number(value)
    return number if number is not None and number >= 0 else None


def _timestamp(value):
    if not isinstance(value, str):
        return None
    match = STAMP.fullmatch(value)
    if not match:
        return None
    zone = match.group(8)
    if zone != 'Z':
        hour, minute = map(int, zone[1:].split(':'))
        if hour > 14 or minute > 59 or (hour == 14 and minute):
            return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError:
        return None


def _iso(value):
    return value.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _profile(value):
    profile = dict(DEFAULT_PROFILE if value is None else value)
    for key in ('ruleId', 'ruleVersion', 'ruleName', 'ruleNatureNotice'):
        if not _text(profile.get(key)):
            raise ValueError(f'RuleProfile thiếu {key}.')
    for key in ('maxExteriorEcMsM', 'maxInteriorEcMsM', 'minPositiveHeadDiffM',
                'maxSampleAgeHoursNormal', 'maxSampleAgeHoursHighVigilance', 'p90ReferenceEcMsM'):
        number = profile.get(key)
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
            raise ValueError(f'Ngưỡng {key} phải là số hữu hạn không âm.')
    if (profile['minPositiveHeadDiffM'] <= 0 or profile['maxSampleAgeHoursNormal'] <= 0 or
        profile['maxSampleAgeHoursHighVigilance'] <= 0 or
        profile['maxSampleAgeHoursHighVigilance'] > profile['maxSampleAgeHoursNormal']):
        raise ValueError('Chênh mực nước và thời hạn mẫu phải dương; thời hạn cảnh giác cao không được dài hơn bình thường.')
    if profile.get('requireSameDatum') is not True or not isinstance(profile.get('requireMechanicalReady'), bool):
        raise ValueError('RuleProfile không hợp lệ.')
    return profile


def evaluate(measurement: dict, profile: dict | None = None,
             forecast_context: dict | None = None, now_iso: str | None = None) -> dict:
    now = _timestamp(now_iso)
    if now is None:
        raise ValueError('Thời điểm đánh giá phải là ISO hợp lệ có múi giờ.')
    input_data = measurement or {}
    rule = _profile(profile)
    context = forecast_context or {}
    station = _nonnegative(context.get('mythoEc'))
    explicit = _nonnegative(context.get('projectedGateEc'))
    projected = explicit if explicit is not None else station
    p90 = _nonnegative(context.get('p90Threshold'))
    if p90 is None:
        p90 = rule['p90ReferenceEcMsM']
    high_station = station is not None and station >= p90
    gate_threshold = .8 * rule['maxExteriorEcMsM']
    high_gate = projected is not None and projected >= gate_threshold
    high_context = context.get('isHighVigilance') is True
    high = high_station or high_gate or high_context
    max_age = rule['maxSampleAgeHoursHighVigilance'] if high else rule['maxSampleAgeHoursNormal']
    checks = []

    def add(identifier, status, observed, threshold):
        checks.append(dict(id=identifier, status=status, observedValue=observed, thresholdValue=threshold))

    measured = _timestamp(input_data.get('measuredAtIso'))
    sample_age = None
    expires = None
    if measured is None or measured > now:
        add('SAMPLE_FRESHNESS', 'MISSING_OR_EXPIRED', input_data.get('measuredAtIso'), max_age)
    else:
        sample_age = (now - measured).total_seconds() / 3600
        expires = measured + timedelta(hours=max_age)
        add('SAMPLE_FRESHNESS', 'PASSED' if sample_age <= max_age else 'MISSING_OR_EXPIRED', sample_age, max_age)
    for identifier, field, threshold in (
        ('EXTERIOR_EC', 'exteriorEcMsM', rule['maxExteriorEcMsM']),
        ('INTERIOR_EC', 'interiorEcMsM', rule['maxInteriorEcMsM'])):
        value = _nonnegative(input_data.get(field))
        status = 'MISSING_OR_EXPIRED' if value is None else 'PASSED' if value <= threshold else 'FAILED'
        add(identifier, status, value, threshold)
    same_datum = input_data.get('sameElevationDatum') is True
    add('ELEVATION_DATUM', 'PASSED' if same_datum else 'MISSING_OR_EXPIRED', same_datum, True)
    exterior = _number(input_data.get('exteriorStageM'))
    interior = _number(input_data.get('interiorStageM'))
    head = exterior - interior if same_datum and exterior is not None and interior is not None else None
    head_available = head is not None and math.isfinite(head)
    tolerance = min(1e-10, rule['minPositiveHeadDiffM'] * 1e-10,
                    4 * 2.220446049250313e-16 * max(1, abs(exterior or 0), abs(interior or 0)))
    head_passed = head_available and head > 0 and head + tolerance >= rule['minPositiveHeadDiffM']
    add('HYDRAULIC_HEAD_DIFF', 'MISSING_OR_EXPIRED' if not head_available else 'PASSED' if head_passed else 'FAILED',
        head if head_available else None, rule['minPositiveHeadDiffM'])
    mechanical = _text(input_data.get('mechanicalStatus'))
    known = mechanical in ('READY', 'NOT_READY', 'MAINTENANCE', 'FAULT', 'BLOCKED', 'OUT_OF_SERVICE')
    mechanical_passed = known and (not rule['requireMechanicalReady'] or mechanical == 'READY')
    add('MECHANICAL_READINESS', 'MISSING_OR_EXPIRED' if not known else 'PASSED' if mechanical_passed else 'FAILED',
        mechanical or None, 'READY' if rule['requireMechanicalReady'] else 'Đã khai báo tình trạng')
    measured_by = _text(input_data.get('measuredBy'))
    add('MEASUREMENT_PROVENANCE', 'PASSED' if measured_by else 'MISSING_OR_EXPIRED', measured_by or None, 'Có người đo / nguồn số đo')
    if input_data.get('dataKind') == 'SIMULATION' or input_data.get('gateObservation') is False:
        add('FIELD_MEASUREMENT', 'MISSING_OR_EXPIRED', 'SIMULATION', 'FIELD_MEASUREMENT')
    statuses = {item['status'] for item in checks}
    status = ('INSUFFICIENT_OR_EXPIRED_DATA' if 'MISSING_OR_EXPIRED' in statuses else
              'NOT_SUITABLE' if 'FAILED' in statuses else 'ELIGIBLE_FOR_REVIEW')
    return dict(status=status, statusTitle=STATUS_TITLES[status], checks=checks,
                criteriaChecks=checks, policy_version=rule['ruleVersion'], ruleProfile=rule,
                rule_profile_hash=_hash(rule), input_hash=_hash(dict(measurement=input_data,
                    forecast_context=context, now_iso=now_iso)),
                evaluatedAtIso=_iso(now), validUntilIso=_iso(expires) if status == 'ELIGIBLE_FOR_REVIEW' else None,
                sampleExpiresAtIso=_iso(expires) if expires else None, sampleAgeHours=sample_age,
                headDiffM=head if head_available else None,
                effectiveMaxSampleAgeHours=max_age, requiresOperatorReview=True, actuatorCommand=None)
