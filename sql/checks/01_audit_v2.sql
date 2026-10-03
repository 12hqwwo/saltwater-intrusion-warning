-- Bổ sung audit schema theo yêu cầu:
-- 1. Số dòng các bảng nghiệp vụ
SELECT relname AS table_name, n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY relname;

-- 2. Ngày quan trắc đầu/cuối, phân bố cờ chất lượng, tỷ lệ O/E
SELECT d.dataset_code, s.site_code, count(*) AS observation_count,
       min(o.observed_at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS first_observation_local,
       max(o.observed_at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS last_observation_local,
       count(*) FILTER(WHERE o.quality_flag='UNVERIFIED') AS unverified_rows,
       count(*) FILTER(WHERE o.quality_flag='VALIDATED') AS validated_rows,
       count(*) FILTER(WHERE o.observed_or_estimated='O') AS observed_rows,
       count(*) FILTER(WHERE o.observed_or_estimated='E') AS estimated_rows
FROM public.conductivity_observation o
JOIN public.source_dataset d USING(dataset_id)
JOIN public.measurement_site s USING(site_id)
GROUP BY d.dataset_code, s.site_code
ORDER BY d.dataset_code, s.site_code;

-- 3. Tọa độ thiếu, SRID, hình học không hợp lệ và nguồn vị trí của bảng cống
SELECT 'irrigation_gate' AS table_name, count(*) AS total_rows, count(geom) AS rows_with_geometry,
       count(*) FILTER(WHERE geom IS NOT NULL AND (ST_IsEmpty(geom) OR NOT ST_IsValid(geom))) AS bad_geometry,
       count(*) FILTER(WHERE geom IS NOT NULL AND ST_SRID(geom)<>4326) AS wrong_srid,
       count(*) FILTER(WHERE geom IS NULL) AS missing_geometry
FROM public.irrigation_gate WHERE NOT is_demo;
