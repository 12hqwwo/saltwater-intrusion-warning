"""Restricted DSS field submissions and append-only reviews."""
from uuid import uuid4
from datetime import timedelta, time
import hashlib
import statistics

from psycopg.types.json import Jsonb

from backend.database import read_connection
from backend.repositories.dss_storage import write_connection
from backend.domain.forecast_issue import LABEL_PROTOCOL_VERSION, LOCAL_TZ, _shift_month


def insert_measurement(value, raw):
    with write_connection() as conn:
        return conn.execute('''INSERT INTO dss_reference.field_measurement
            (measurement_id,geom,ec_mS_m,unit_original,ec_basis,calibrated_at,
             water_temp_degC,observed_at,position_kind,device,submitted_by,flags,raw_payload)
            VALUES (%s,ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING measurement_id,submitted_at''',
            (uuid4(), value['longitude'], value['latitude'], value['ec_mS_m'],
             value['unit_original'], value['ec_basis'], value['calibrated_at'],
             value['water_temp_degC'], value['observed_at'], value['position_kind'],
             value['device'], value['submitted_by'], value['flags'], Jsonb(raw))).fetchone()


def list_measurements(status, bbox, limit=200):
    with read_connection() as conn:
        return conn.execute('''SELECT measurement_id,ST_X(geom) AS longitude,ST_Y(geom) AS latitude,
            ec_mS_m,unit_original,ec_basis,calibrated_at,water_temp_degC,
            observed_at,position_kind,device,submitted_by,flags,submitted_at,
            status,review_id,reviewer,review_note,reviewed_at
            FROM dss_reference.v_field_measurement_status
            WHERE (%s::text IS NULL OR status=%s)
              AND (%s::float8 IS NULL OR ST_Intersects(geom,ST_MakeEnvelope(%s,%s,%s,%s,4326)))
            ORDER BY submitted_at DESC,measurement_id DESC LIMIT %s''',
            (status, status, bbox[0] if bbox else None,
             *(bbox or (None, None, None, None)), limit)).fetchall()


def insert_review(measurement_id, decision, reviewer, note):
    with write_connection() as conn:
        exists = conn.execute('SELECT 1 FROM dss_reference.field_measurement WHERE measurement_id=%s',
                              (measurement_id,)).fetchone()
        if exists is None:
            return None
        return conn.execute('''INSERT INTO dss_reference.field_measurement_review
            (measurement_id,decision,reviewer,note)
            VALUES (%s,%s,%s,%s) RETURNING review_id,measurement_id,decision,reviewer,reviewed_at''',
            (measurement_id, decision, reviewer, note)).fetchone()


LABEL_SITES = {'MYTHO': 'MRC_VN_019805', 'MYTHUAN': 'MRC_VN_019804',
               'TANCHAU': 'MRC_VN_019803'}


def historical_month_median(longitude, latitude, observed_at):
    """Reference median for a review flag, using the nearest of the three MRC stations."""
    with read_connection() as conn:
        row = conn.execute('''WITH nearest AS (
                SELECT site_id FROM public.measurement_site
                WHERE site_code=ANY(%s) AND geom IS NOT NULL
                ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography
                LIMIT 1
            )
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY o.conductivity_ms_per_m) AS median_ec
            FROM public.conductivity_observation o
            JOIN nearest n ON n.site_id=o.site_id
            JOIN public.source_dataset d ON d.dataset_id=o.dataset_id
            WHERE d.dataset_kind='RAW_EC' AND d.dataset_code LIKE 'MRC_%%' AND NOT d.is_demo
              AND o.observed_or_estimated='O' AND o.quality_flag<>'INVALID'
              AND o.unit='mS/m' AND o.conductivity_ms_per_m>=0
              AND extract(month FROM o.observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh')=%s''',
            (list(LABEL_SITES.values()), longitude, latitude,
             observed_at.astimezone(LOCAL_TZ).month)).fetchone()
    return row['median_ec'] if row else None


def field_label_from_rows(rows, target_month):
    """Apply the 14 Nov preregistered temporal, calibration and agreement criteria."""
    selected = []
    for row in rows:
        observed = row['observed_at'].astimezone(LOCAL_TZ)
        calibrated = row['calibrated_at']
        if (observed.date().replace(day=1) != target_month or not 13 <= observed.day <= 17
                or not time(9) <= observed.time() < time(16)
                or calibrated is None or not 0 <= (observed.date() - calibrated).days <= 30
                or not row.get('calibration_reference')
                or row['ec_basis'] != 'EC25' or row['position_kind'] != 'RIVER'):
            continue
        selected.append(row)
    selected.sort(key=lambda row: (row['observed_at'], str(row['measurement_id'])))
    if len(selected) < 2 or not any(
        (later['observed_at'] - earlier['observed_at']) >= timedelta(minutes=30)
        for i, earlier in enumerate(selected) for later in selected[i + 1:]):
        return None
    values = [row['ec_mS_m'] for row in selected]
    median = statistics.median(values)
    if (median == 0 and max(values) != 0) or (median > 0 and (max(values) - min(values)) / median > .20):
        return None
    ids = sorted(str(row['measurement_id']) for row in selected)
    reference = hashlib.sha256((LABEL_PROTOCOL_VERSION + ':' + ','.join(ids)).encode('utf-8')).hexdigest()
    return dict(obs_source='FIELD_APPROVED', equivalent_monthly_label=True,
                label_protocol_version=LABEL_PROTOCOL_VERSION,
                observation_ref='FIELD_SET:' + reference,
                observed_at=selected[0]['observed_at'].isoformat(), observed_ec_mS_m=median)


def candidate_field_label(station, target_month):
    if station not in LABEL_SITES:
        raise ValueError('Unsupported station')
    end = _shift_month(target_month, 1)
    with read_connection() as conn:
        rows = conn.execute('''SELECT m.measurement_id,m.observed_at,m.ec_mS_m,
                m.ec_basis,m.position_kind,m.calibrated_at,
                m.raw_payload->>'calibration_reference' AS calibration_reference
            FROM dss_reference.v_field_measurement_status m
            JOIN public.measurement_site s ON s.site_code=%s AND s.geom IS NOT NULL
            WHERE m.status='APPROVED' AND m.observed_at >= %s AND m.observed_at < %s
              AND ST_DWithin(m.geom::geography,s.geom::geography,2000)
            ORDER BY m.observed_at,m.measurement_id''',
            (LABEL_SITES[station], target_month, end)).fetchall()
    return field_label_from_rows(rows, target_month)
