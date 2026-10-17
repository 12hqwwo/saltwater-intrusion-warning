"""Truy vấn tham số hóa trên schema v1/v2; mỗi lời gọi dùng transaction chỉ đọc."""

import os
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta

import psycopg
from psycopg.rows import dict_row

from backend.schemas import LOCAL_TZ


class SiteNotFound(Exception):
    """Không có trạm thật mang mã được yêu cầu."""


class DatasetNotFound(Exception):
    """Snapshot không có quan trắc EC của trạm được yêu cầu."""


@contextmanager
def read_connection():
    # Password/passfile/SSL settings use libpq's standard PG* environment.
    # Never interpolate credentials into SQL or log connection strings.
    with psycopg.connect(
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "dongthap_gis"),
        user=os.getenv("PGUSER", "postgres"),
        connect_timeout=5,
        application_name="webgis_read_api",
        options="-c statement_timeout=10000 -c lock_timeout=3000 -c timezone=Asia/Ho_Chi_Minh",
        row_factory=dict_row,
    ) as conn:
        conn.read_only = True
        # Count and page must see the same snapshot within one request.
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        yield conn


STATIONS_SQL = """
SELECT s.site_code, s.site_name, s.external_site_code,
       s.location_status, s.location_reference,
       src.source_code, src.source_name, src.reference AS source_reference,
       public.ST_AsGeoJSON(s.geom, 15)::jsonb AS geometry
FROM public.measurement_site s
JOIN public.data_source src ON src.source_id = s.source_id
WHERE s.is_demo = false AND src.is_demo = false
ORDER BY s.site_code
"""

SITE_SQL = """
SELECT s.site_id
FROM public.measurement_site s
JOIN public.data_source src ON src.source_id = s.source_id
WHERE s.site_code = %s AND s.is_demo = false AND src.is_demo = false
"""

# Only fixed SQL fragments are composed; client values are bound separately.
DATASETS_SELECT = """
SELECT d.dataset_id, d.dataset_code, d.sha256, d.source_filename,
       d.imported_at, src.source_code,
       count(*) AS observation_count,
       min(o.observed_at) AS first_observation,
       max(o.observed_at) AS last_observation,
       count(*) FILTER (WHERE o.observed_or_estimated = 'O') AS observed_rows,
       count(*) FILTER (WHERE o.observed_or_estimated = 'E') AS estimated_rows,
       count(*) FILTER (WHERE o.quality_flag = 'UNVERIFIED') AS unverified_rows,
       count(*) FILTER (WHERE o.quality_flag = 'VALIDATED') AS validated_rows,
       count(*) FILTER (WHERE o.quality_flag = 'SUSPECT') AS suspect_rows,
       count(*) FILTER (WHERE o.quality_flag = 'INVALID') AS invalid_rows
FROM public.conductivity_observation o
JOIN public.source_dataset d ON d.dataset_id = o.dataset_id
JOIN public.data_source src ON src.source_id = d.source_id
WHERE o.site_id = %s AND d.dataset_kind = 'RAW_EC'
  AND d.is_demo = false AND src.is_demo = false
"""

DATASETS_GROUP = """
GROUP BY d.dataset_id, d.dataset_code, d.sha256, d.source_filename,
         d.imported_at, src.source_code
ORDER BY d.imported_at DESC, d.dataset_code
"""


def history_predicate(
    site_id: int,
    dataset_id: int,
    date_from: date | None,
    date_to: date | None,
    quality_flag: str | None,
    observed_or_estimated: str | None,
):
    clauses = ["o.site_id = %s", "o.dataset_id = %s"]
    params = [site_id, dataset_id]
    if date_from is not None:
        clauses.append("o.observed_at >= %s")
        params.append(datetime.combine(date_from, time.min, tzinfo=LOCAL_TZ))
    if date_to is not None:
        # date_to is inclusive for the whole local day; upper bound is exclusive.
        clauses.append("o.observed_at < %s")
        params.append(datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=LOCAL_TZ))
    if quality_flag is not None:
        clauses.append("o.quality_flag = %s")
        params.append(quality_flag)
    if observed_or_estimated is not None:
        clauses.append("o.observed_or_estimated = %s")
        params.append(observed_or_estimated)
    return " AND ".join(clauses), params


class Repository:
    @staticmethod
    def _site_id(conn, site_code: str) -> int:
        row = conn.execute(SITE_SQL, (site_code,)).fetchone()
        if row is None:
            raise SiteNotFound
        return row["site_id"]

    def health(self) -> dict:
        with read_connection() as conn:
            return conn.execute("""
                SELECT current_database() AS database_name,
                       current_setting('transaction_read_only') = 'on'
                           AS transaction_read_only
            """).fetchone()

    def stations(self) -> list[dict]:
        with read_connection() as conn:
            return conn.execute(STATIONS_SQL).fetchall()

    def datasets(self, site_code: str) -> list[dict]:
        with read_connection() as conn:
            site_id = self._site_id(conn, site_code)
            return conn.execute(DATASETS_SELECT + DATASETS_GROUP, (site_id,)).fetchall()

    def history(
        self,
        site_code: str,
        dataset_code: str,
        date_from: date | None,
        date_to: date | None,
        quality_flag: str | None,
        observed_or_estimated: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        with read_connection() as conn:
            site_id = self._site_id(conn, site_code)
            dataset = conn.execute(
                DATASETS_SELECT + " AND d.dataset_code = %s " + DATASETS_GROUP,
                (site_id, dataset_code),
            ).fetchone()
            if dataset is None:
                raise DatasetNotFound
            where, params = history_predicate(
                site_id, dataset["dataset_id"], date_from, date_to,
                quality_flag, observed_or_estimated,
            )
            total = conn.execute(
                "SELECT count(*) AS total FROM public.conductivity_observation o WHERE " + where,
                params,
            ).fetchone()["total"]
            items = conn.execute(
                """
                SELECT o.ec_observation_id, o.source_row, o.observed_at,
                       o.conductivity_ms_per_m, o.unit, o.observed_or_estimated,
                       o.quality_flag, o.approval_level, o.grade, o.source_label
                FROM public.conductivity_observation o WHERE
                """ + where + " ORDER BY o.observed_at, o.ec_observation_id LIMIT %s OFFSET %s",
                params + [limit, offset],
            ).fetchall()
            return {"dataset": dataset, "total": total, "items": items}
