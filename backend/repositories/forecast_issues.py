"""Append-only PostgreSQL access for scheduled EC forecast issues."""
from uuid import uuid4

from psycopg.types.json import Jsonb

from backend.database import read_connection
from backend.repositories.dss_storage import write_connection
from backend.domain.forecast_issue import LABEL_PROTOCOL_VERSION, _shift_month


def insert_slot(conn, station, target_month, schedule_code, scheduled_at):
    row = conn.execute('''INSERT INTO dss_reference.forecast_slot
        (slot_id,station_key,target_month,schedule_code,scheduled_at)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (station_key,target_month,schedule_code) DO NOTHING
        RETURNING *''', (uuid4(), station, target_month, schedule_code, scheduled_at)).fetchone()
    return row or conn.execute('''SELECT * FROM dss_reference.forecast_slot
        WHERE station_key=%s AND target_month=%s AND schedule_code=%s''',
        (station, target_month, schedule_code)).fetchone()


def insert_missed(conn, slot_id, reason_code):
    return conn.execute('''INSERT INTO dss_reference.forecast_slot_event
        (event_id,slot_id,event_type,reason_code) VALUES (%s,%s,'MISSED',%s)
        ON CONFLICT (slot_id,event_type) DO NOTHING RETURNING *''',
        (uuid4(), slot_id, reason_code)).fetchone()


def existing_issue(conn, slot_id):
    return conn.execute('SELECT * FROM dss_reference.forecast_issue WHERE slot_id=%s', (slot_id,)).fetchone()


def insert_issue(conn, slot_id, issue):
    return conn.execute('''INSERT INTO dss_reference.forecast_issue
        (issue_id,slot_id,input_month,model_version,model_sha256,data_version,
         predicted_ec_mS_m,payload,issue_status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'LATE') RETURNING *''',
        (uuid4(), slot_id, issue['input_month'] + '-01', issue['model_version'],
         issue['model_sha256'], issue['data_version'], issue['predicted_ec_mS_m'],
         Jsonb(issue['payload']))).fetchone()


def list_slots(station=None, date_from=None, date_to=None, limit=200):
    with read_connection() as conn:
        return conn.execute('''SELECT s.*, e.event_id,e.event_type,e.reason_code,e.detected_at,
            i.issue_id,i.input_month,i.model_version,i.model_sha256,i.data_version,
            i.predicted_ec_mS_m,i.issue_status,i.issued_at,
            sc.score_id,sc.label_protocol_version,sc.observation_ref,sc.obs_source,
            sc.observed_ec_mS_m,sc.abs_error_mS_m,sc.scored_at
            FROM dss_reference.forecast_slot s
            LEFT JOIN dss_reference.forecast_slot_event e ON e.slot_id=s.slot_id
            LEFT JOIN dss_reference.forecast_issue i ON i.slot_id=s.slot_id
            LEFT JOIN dss_reference.forecast_score sc ON sc.issue_id=i.issue_id
                AND sc.label_protocol_version='MONTHLY_EC_LABEL_V1_20261114'
            WHERE (%s::text IS NULL OR s.station_key=%s)
              AND (%s::date IS NULL OR s.target_month >= %s)
              AND (%s::date IS NULL OR s.target_month <= %s)
            ORDER BY s.target_month DESC,s.station_key LIMIT %s''',
            (station, station, date_from, date_from, date_to, date_to, limit)).fetchall()


def insert_score(issue_id, score):
    with write_connection() as conn:
        return conn.execute('''INSERT INTO dss_reference.forecast_score
            (issue_id,label_protocol_version,observation_ref,obs_source,
             observed_ec_mS_m,abs_error_mS_m)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING *''',
            (issue_id, score['label_protocol_version'], score['observation_ref'],
             score['obs_source'], score['observed_ec_mS_m'], score['abs_error_mS_m'])).fetchone()


SITE_CODES = {'MYTHO': 'MRC_VN_019805', 'MYTHUAN': 'MRC_VN_019804',
              'TANCHAU': 'MRC_VN_019803'}


def candidate_mrc_label(station, target_month):
    """Select one MRC label by preregistered source and day ordering, never by error."""
    if station not in SITE_CODES:
        raise ValueError('Unsupported station')
    end = _shift_month(target_month, 1)
    with read_connection() as conn:
        row = conn.execute('''SELECT d.dataset_code,o.ec_observation_id,o.observed_at,
                o.conductivity_ms_per_m
            FROM public.conductivity_observation o
            JOIN public.source_dataset d ON d.dataset_id=o.dataset_id
            JOIN public.data_source src ON src.source_id=d.source_id
            JOIN public.measurement_site s ON s.site_id=o.site_id
            WHERE s.site_code=%s AND d.dataset_kind='RAW_EC'
              AND d.dataset_code LIKE 'MRC_%%' AND NOT d.is_demo AND NOT src.is_demo
              AND o.observed_or_estimated='O' AND o.quality_flag<>'INVALID'
              AND o.unit='mS/m' AND o.conductivity_ms_per_m>=0
              AND o.observed_at >= %s AND o.observed_at < %s
            ORDER BY d.imported_at,d.dataset_code,
                abs(extract(day FROM o.observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh')-15),
                o.observed_at,o.ec_observation_id LIMIT 1''',
            (SITE_CODES[station], target_month, end)).fetchone()
    if row is None:
        return None
    return dict(obs_source='MRC', equivalent_monthly_label=True,
                label_protocol_version=LABEL_PROTOCOL_VERSION,
                observation_ref=f"{row['dataset_code']}:{row['ec_observation_id']}",
                observed_at=row['observed_at'].isoformat(),
                observed_ec_mS_m=row['conductivity_ms_per_m'])
