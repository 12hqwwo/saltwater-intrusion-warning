"""Validate storage requests independently from operational decision claims."""
import json
import math
from functools import wraps
import psycopg
from backend.repositories import dss_storage as store
from backend.services import multivariate
from backend.services.workspace import WorkspaceError
from backend.domain.gates import stamp


def storage_errors(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except store.StorageDisabled as exc:
            raise WorkspaceError(503, 'DSS_WRITES_DISABLED: Chưa bật lưu PostgreSQL; bản nháp cục bộ và dự báo vẫn dùng được.') from exc
        except psycopg.Error as exc:
            if exc.sqlstate in {'42P01', '42703', '3F000'}:
                message = 'DSS_SCHEMA_MISSING: Chưa cài migration lưu trữ DSS hoặc schema chưa khớp.'
            elif exc.sqlstate == '42501':
                message = 'DSS_PERMISSION_DENIED: Tài khoản thiếu quyền lưu trữ DSS.'
            else:
                message = 'DSS_DATABASE_UNAVAILABLE: Không truy cập được kho DSS; kiểm tra kết nối.'
            raise WorkspaceError(503, message) from exc
    return guarded


@storage_errors
def presets():
    return dict(items=store.threshold_presets(), source='POSTGRESQL_DSS', is_operational_rule=False)


@storage_errors
def save_prediction(payload):
    store.require_writes()
    # Recompute from the validated request, not a client-supplied rounded result.
    return store.save_prediction(multivariate.predict(payload))


@storage_errors
def predictions(station, target_month, limit, offset):
    if station is not None:
        try:
            station = multivariate.models.STATIONS[multivariate.models.normalize_station(station)][0]
        except ValueError as exc:
            raise WorkspaceError(422, 'Mã trạm lịch sử dự báo không hợp lệ.') from exc
    if target_month is not None:
        multivariate._target(target_month)
    return store.predictions(station, target_month, limit, offset)


@storage_errors
def prediction(prediction_id):
    result = store.prediction(prediction_id)
    if result is None:
        raise WorkspaceError(404, 'Không tìm thấy dự báo đã lưu.')
    return result


def validate_draft(gate_code, data, policy):
    def walk(value, depth=0):
        if depth > 12:
            raise ValueError('Dossier nesting exceeds limit.')
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Dossier numbers must be finite.')
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'gate_code' and child not in (None, gate_code):
                    raise ValueError('Nested gate code mismatch.')
                walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                walk(child, depth + 1)
    def numeric(value, nonnegative=False):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or (nonnegative and value < 0)):
            raise ValueError('Invalid numeric dossier field.')
    try:
        if len(json.dumps([data, policy], allow_nan=False).encode('utf-8')) > 240000:
            raise ValueError('Dossier exceeds size limit.')
        walk(data); walk(policy)
        for obj in (data, policy):
            if obj.get('gate_code') != gate_code or type(obj.get('schema_version')) is not int or obj['schema_version'] != 1:
                raise ValueError('Gate/schema mismatch.')
        if data.get('mode') not in (None, 'INTAKE', 'DRAIN'):
            raise ValueError('Invalid operation mode.')
        if data.get('evaluation_mode') not in (None, 'SIMULATION'):
            raise ValueError('Drafts only support simulation.')
        for key in ('issue_time', 'last_changed_at'):
            if data.get(key) is not None:
                stamp(data[key])
        for key in ('allow_drainage_with_saline_outside',):
            if policy.get(key) is not None and not isinstance(policy[key], bool):
                raise ValueError('Policy boolean must be true/false.')
        observations = data.get('observations', {})
        if not isinstance(observations, dict) or set(observations) - {'outside_level', 'inside_level', 'outside_quality', 'inside_quality'}:
            raise ValueError('Invalid observation fields.')
        for key, row in observations.items():
            if not isinstance(row, dict):
                raise ValueError('Observation must be an object.')
            numeric(row.get('value'), 'quality' in key)
            if 'quality' in key and (row.get('unit') not in (None, 'mS/m') or row.get('parameter') not in (None, 'EC')
                    or row.get('ec_basis') not in (None, 'UNKNOWN', 'EC25', 'RAW')):
                raise ValueError('EC observation unit/basis mismatch.')
            for key in ('observed_at', 'available_at'):
                if row.get(key) is not None:
                    stamp(row[key])
        for name in ('levels', 'quality_thresholds'):
            group = policy.get(name, {})
            if not isinstance(group, dict):
                raise ValueError('Policy group must be an object.')
            for key, value in group.items():
                numeric(value, name == 'quality_thresholds' or key in ('min_head_m', 'max_abs_head_m'))
        parameter = policy.get('parameter', {})
        if not isinstance(parameter, dict) or parameter.get('ec_basis') not in (None, 'UNKNOWN', 'EC25', 'RAW'):
            raise ValueError('Invalid EC basis.')
        if parameter.get('unit') not in (None, 'mS/m') or parameter.get('name') not in (None, 'EC'):
            raise ValueError('Draft parameter must be EC in mS/m.')
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise WorkspaceError(422, 'Hồ sơ nháp không hợp lệ: ' + str(exc)) from exc


@storage_errors
def save_draft(gate_code, data, policy):
    validate_draft(gate_code, data, policy)
    return store.save_draft(gate_code, data, policy)


@storage_errors
def drafts(gate_code, limit, offset):
    return store.drafts(gate_code, limit, offset)
