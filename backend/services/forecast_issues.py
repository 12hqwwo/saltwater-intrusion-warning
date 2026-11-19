"""Issue each scheduled forecast once and keep late scores separate."""
from datetime import date, datetime, timedelta

from backend.domain import forecast_issue as rules
from backend.repositories import forecast_issues as repo
from backend.repositories.dss_storage import write_connection
from backend.services import multivariate
from backend.services.dss_storage import storage_errors
from backend.services.workspace import WorkspaceError


@storage_errors
def issue_for_station(station: str, target_month: str, now: datetime | None = None):
    scheduled = rules.schedule(target_month)
    now = now or datetime.now(rules.LOCAL_TZ)
    if now < scheduled:
        raise WorkspaceError(422, 'Chưa đến lịch MONTHLY_D06_PREV của tháng mục tiêu.')
    prediction = None
    failure = None
    try:
        prediction = multivariate.predict(dict(station=station, target_month=target_month, input_mode='ARCHIVE'))
    except WorkspaceError as exc:
        failure = exc
    with write_connection() as conn:
        slot = repo.insert_slot(conn, station, target_month + '-01', rules.SCHEDULE_CODE, scheduled)
        if repo.existing_issue(conn, slot['slot_id']):
            raise WorkspaceError(409, f'Slot {station} {target_month} đã có một bản phát hành.')
        db_now = conn.execute('SELECT clock_timestamp() AS now').fetchone()['now']
        late = db_now >= scheduled + timedelta(hours=1)
        if late:
            repo.insert_missed(conn, slot['slot_id'], 'JOB_NOT_RUN')
        if failure:
            if not late:
                repo.insert_missed(conn, slot['slot_id'], 'MISSING_INPUT' if failure.status_code == 422 else 'RUN_FAILED')
            return dict(station=station, target_month=target_month, slot_id=str(slot['slot_id']),
                        status='MISSED', http_status=failure.status_code, reason=failure.detail)
        try:
            issue = rules.build_issue(prediction, db_now)
        except (ValueError, KeyError, TypeError) as exc:
            if not late:
                repo.insert_missed(conn, slot['slot_id'], 'RUN_FAILED')
            return dict(station=station, target_month=target_month, slot_id=str(slot['slot_id']),
                        status='MISSED', http_status=422, reason=str(exc))
        saved = repo.insert_issue(conn, slot['slot_id'], issue)
        return dict(station=station, target_month=target_month, slot_id=str(slot['slot_id']),
                    issue_id=str(saved['issue_id']), status=saved['issue_status'],
                    predicted_ec_mS_m=saved['predicted_ec_mS_m'], issued_at=saved['issued_at'])


def issue_month(target_month: str, schedule_code: str = rules.SCHEDULE_CODE):
    target = multivariate._target(target_month)
    if schedule_code != rules.SCHEDULE_CODE:
        raise WorkspaceError(422, 'Mã lịch phát hành không hợp lệ.')
    if rules.schedule(target_month).date() < rules.LEDGER_START_LOCAL:
        raise WorkspaceError(422, 'Lịch này có trước ngày mở sổ 14/11/2026; không tạo bản phát hành hồi tố.')
    today = datetime.now(rules.LOCAL_TZ).date().replace(day=1)
    if target <= today:
        raise WorkspaceError(422, 'Không phát hành lùi tháng hiện tại hoặc tháng đã qua.')
    items = []
    for station in rules.STATIONS:
        try:
            items.append(issue_for_station(station, target_month))
        except WorkspaceError as exc:
            if exc.status_code not in (409, 422):
                raise
            items.append(dict(station=station, target_month=target_month,
                              status='ERROR', http_status=exc.status_code, reason=exc.detail))
    if items and all(item.get('http_status') == 409 for item in items):
        raise WorkspaceError(409, 'Cả ba slot của tháng này đã có bản phát hành.')
    return dict(schedule_code=schedule_code, target_month=target_month, items=items)


@storage_errors
def audit_due(target_month: str, now: datetime | None = None):
    """Record JOB_NOT_RUN at the next check, keeping the actual DB detection time."""
    multivariate._target(target_month)
    scheduled = rules.schedule(target_month)
    if scheduled.date() < rules.LEDGER_START_LOCAL:
        raise WorkspaceError(422, 'Không kiểm tra hồi tố lịch trước ngày mở sổ.')
    if (now or datetime.now(rules.LOCAL_TZ)) < scheduled + timedelta(hours=1):
        return dict(target_month=target_month, due=False, items=[])
    items = []
    with write_connection() as conn:
        for station in rules.STATIONS:
            slot = repo.insert_slot(conn, station, target_month + '-01', rules.SCHEDULE_CODE, scheduled)
            issue = repo.existing_issue(conn, slot['slot_id'])
            if issue:
                items.append(dict(station=station, status=issue['issue_status']))
            else:
                inserted = repo.insert_missed(conn, slot['slot_id'], 'JOB_NOT_RUN')
                items.append(dict(station=station, status='MISSED', newly_detected=inserted is not None))
    return dict(target_month=target_month, due=True, items=items)


@storage_errors
def list_issues(station=None, date_from=None, date_to=None, with_scores=True):
    if station:
        try:
            station = multivariate.models.normalize_station(station)
        except ValueError as exc:
            raise WorkspaceError(422, 'Mã trạm không hợp lệ.') from exc
    start = multivariate._target(date_from).isoformat() if date_from else None
    end = multivariate._target(date_to).isoformat() if date_to else None
    if start and end and start > end:
        raise WorkspaceError(422, 'Khoảng tháng không hợp lệ.')
    rows = repo.list_slots(station, start, end)
    scores = repo.score_summary(station, start, end) if with_scores else []
    items = []
    by_source = {source: {'ON_TIME': None, 'LATE': None}
                 for source in ('MRC', 'FIELD_APPROVED')}
    for row in scores:
        by_source[row['obs_source']][row['issue_status']] = row
    for row in rows[:200]:
        slot = {key: row[key] for key in ('slot_id', 'station_key', 'target_month', 'schedule_code', 'scheduled_at')}
        events = ([{key: row[key] for key in ('event_id', 'event_type', 'reason_code', 'detected_at')}]
                  if row['event_id'] else [])
        issue = ({key: row[key] for key in ('issue_id', 'input_month', 'model_version',
                 'model_sha256', 'data_version', 'predicted_ec_mS_m', 'issue_status', 'issued_at')}
                 if row['issue_id'] else None)
        score = ({key: row[key] for key in ('score_id', 'label_protocol_version', 'observation_ref',
                  'obs_source', 'observed_ec_mS_m', 'abs_error_mS_m', 'scored_at')}
                 if with_scores and row['score_id'] else None)
        items.append(dict(slot=slot, events=events, issue=issue, score=score))
    def metrics(groups):
        result = {}
        for status, prefix in (('ON_TIME', 'on_time'), ('LATE', 'late')):
            aggregate = groups[status]
            result[prefix + '_n_scored'] = aggregate['n_scored'] if aggregate else 0
            result[prefix + '_mae_mS_m'] = aggregate['mae_mS_m'] if aggregate else None
        return result

    source_metrics = {source: metrics(groups) for source, groups in by_source.items()}
    # Keep legacy fields MRC-only: older clients must never display a pooled MAE.
    summary = dict(source_metrics['MRC'], primary_obs_source='MRC', by_source=source_metrics)
    return dict(items=items, items_truncated=len(rows) > 200, summary=summary,
                label_protocol_version=rules.LABEL_PROTOCOL_VERSION)
