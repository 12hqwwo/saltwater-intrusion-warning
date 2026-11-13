"""Validate staff field EC and keep review status separate from source observations."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.domain.field_measurement import normalize
from backend.repositories import field_measurements as repo
from backend.services.dss_storage import storage_errors
from backend.services.workspace import WorkspaceError


@storage_errors
def submit(raw):
    if len(json.dumps(raw, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 16000:
        raise WorkspaceError(413, 'Phiếu số đo vượt giới hạn 16 KiB.')
    try:
        normalized = normalize(raw, datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')))
    except ValueError as exc:
        raise WorkspaceError(422, str(exc)) from exc
    median = repo.historical_month_median(
        normalized['longitude'], normalized['latitude'], normalized['observed_at'])
    if median is not None and normalized['ec_mS_m'] > 3 * median:
        normalized['flags'].append('REVIEW_HIGH')
    saved = repo.insert_measurement(normalized, raw)
    return dict(measurement_id=saved['measurement_id'], status='PENDING',
                submitted_at=saved['submitted_at'], ec_mS_m=normalized['ec_mS_m'],
                unit_original=normalized['unit_original'], flags=normalized['flags'])


@storage_errors
def list_measurements(status=None, bbox=None):
    if status not in (None, 'PENDING', 'APPROVED', 'REJECTED'):
        raise WorkspaceError(422, 'Trạng thái duyệt không hợp lệ.')
    parsed = None
    if bbox is not None:
        try:
            parsed = tuple(float(value) for value in bbox.split(','))
            if (len(parsed) != 4 or not -180 <= parsed[0] < parsed[2] <= 180
                    or not -90 <= parsed[1] < parsed[3] <= 90):
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise WorkspaceError(422, 'bbox phải là minLon,minLat,maxLon,maxLat hợp lệ.') from exc
    return dict(items=repo.list_measurements(status, parsed), status=status)


@storage_errors
def review(measurement_id, decision, reviewer, note):
    if decision not in ('APPROVED', 'REJECTED') or not isinstance(reviewer, str) or not reviewer.strip():
        raise WorkspaceError(422, 'Quyết định và người duyệt không hợp lệ.')
    saved = repo.insert_review(measurement_id, decision, reviewer.strip(), note)
    if saved is None:
        raise WorkspaceError(404, 'Không tìm thấy phiếu thực địa.')
    return saved
