-- Chi doc: doi chieu database truoc khi xay API tram va lich su EC.
-- Chay trong pgAdmin/DBeaver, database dongthap_gis da co schema v1 + v2.
BEGIN READ ONLY;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '3s';

-- W01: Database va thoi diem lay ket qua.
SELECT current_database() AS database_name,
       current_timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh' AS checked_at_local,
       current_setting('TimeZone') AS session_timezone;

-- W02: Tram EC, ke ca tram chua co quan trac. So dong gom tat ca snapshot.
WITH observation_summary AS (
    SELECT site_id, count(*) AS observation_rows_all_snapshots,
           count(DISTINCT dataset_id) AS dataset_count,
           min(observed_at) AS first_observed_at, max(observed_at) AS last_observed_at,
           count(*) FILTER (WHERE quality_flag = 'UNVERIFIED') AS unverified_rows,
           count(*) FILTER (WHERE quality_flag = 'VALIDATED') AS validated_rows
    FROM public.conductivity_observation GROUP BY site_id
)
SELECT s.site_id, s.site_code, s.external_site_code, s.site_name,
       s.location_status, s.location_reference,
       ST_X(s.geom) AS longitude, ST_Y(s.geom) AS latitude,
       ST_SRID(s.geom) AS srid, ST_IsValid(s.geom) AS geometry_valid,
       src.source_code,
       coalesce(o.observation_rows_all_snapshots, 0) AS observation_rows_all_snapshots,
       coalesce(o.dataset_count, 0) AS dataset_count,
       o.first_observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS first_observation_local,
       o.last_observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS last_observation_local,
       coalesce(o.unverified_rows, 0) AS unverified_rows,
       coalesce(o.validated_rows, 0) AS validated_rows
FROM public.measurement_site s
JOIN public.data_source src ON src.source_id = s.source_id
LEFT JOIN observation_summary o ON o.site_id = s.site_id
WHERE NOT s.is_demo ORDER BY s.site_code;

-- W03: Snapshot de API co the loc ro bo du lieu, tranh gop trung phien ban.
SELECT d.dataset_id, d.dataset_code, d.sha256, d.source_filename,
       s.site_code, count(*) AS observation_count,
       min(o.observed_at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS first_observation_local,
       max(o.observed_at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS last_observation_local
FROM public.conductivity_observation o
JOIN public.source_dataset d ON d.dataset_id = o.dataset_id
JOIN public.measurement_site s ON s.site_id = o.site_id
WHERE NOT s.is_demo AND NOT d.is_demo
GROUP BY d.dataset_id, d.dataset_code, d.sha256, d.source_filename, s.site_code
ORDER BY s.site_code, d.dataset_code;

-- W04: Ranh gioi da nap, kem phien ban va nguon.
SELECT b.boundary_id, b.boundary_code, b.boundary_name, b.admin_level,
       b.valid_from, b.valid_to, src.source_code, src.reference,
       ST_SRID(b.geom) AS srid, ST_IsValid(b.geom) AS geometry_valid,
       ST_IsEmpty(b.geom) AS geometry_empty
FROM public.admin_boundary b
JOIN public.data_source src ON src.source_id = b.source_id
WHERE NOT b.is_demo ORDER BY b.boundary_code, b.valid_from;

-- W05: COUNT(*) chinh xac; 0 chi mo ta database nay tai thoi diem chay.
SELECT count(*) AS real_gate_rows,
       count(*) FILTER (WHERE geom IS NOT NULL) AS rows_with_geometry,
       count(*) FILTER (WHERE geom IS NULL) AS missing_geometry,
       count(*) FILTER (WHERE geom IS NOT NULL AND
           (ST_IsEmpty(geom) OR NOT ST_IsValid(geom))) AS bad_geometry,
       count(*) FILTER (WHERE geom IS NOT NULL AND ST_SRID(geom) <> 4326) AS wrong_srid
FROM public.irrigation_gate WHERE NOT is_demo;

COMMIT;
