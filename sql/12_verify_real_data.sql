-- Read-only checks for the two supplied snapshots. Execute after file 11.
-- Expected: raw EC=464, monthly=1000; comparison=464 pairs, 0 mismatches.

SELECT current_database() AS database_name;

SELECT d.dataset_code,d.dataset_kind,d.source_row_count,d.is_demo,d.sha256,
       d.metadata
FROM public.source_dataset d
WHERE d.sha256 IN (
 'bd4cf100cb4782e37b355d94f15911c1bab2c4a9d4ad69d2fa2c3b4c5d590ba7',
 'f9b2de085a265a13e21779aa7c95b8d0caaed9335ae61d820475f54e519eac71')
ORDER BY d.dataset_kind;

SELECT d.dataset_code,count(*) AS raw_rows,
       min(o.observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh') AS first_local_time,
       max(o.observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh') AS last_local_time,
       min(o.conductivity_ms_per_m) AS min_ec_ms_per_m,
       max(o.conductivity_ms_per_m) AS max_ec_ms_per_m
FROM public.conductivity_observation o
JOIN public.source_dataset d USING(dataset_id)
WHERE d.sha256='bd4cf100cb4782e37b355d94f15911c1bab2c4a9d4ad69d2fa2c3b4c5d590ba7'
GROUP BY d.dataset_code;

SELECT * FROM public.v_monthly_coverage
WHERE dataset_code='MASTER_f9b2de085a265a13'
ORDER BY area_code;

SELECT o.unit,o.observed_or_estimated,o.approval_level,o.grade,o.quality_flag,
       count(*) AS rows
FROM public.conductivity_observation o
JOIN public.source_dataset d USING(dataset_id)
WHERE d.sha256='bd4cf100cb4782e37b355d94f15911c1bab2c4a9d4ad69d2fa2c3b4c5d590ba7'
GROUP BY o.unit,o.observed_or_estimated,o.approval_level,o.grade,o.quality_flag;

SELECT m.site_code,m.external_site_code,m.location_status,
       ST_AsText(m.geom) AS geometry,m.location_reference
FROM public.measurement_site m WHERE m.site_code='MRC_VN_019803';
-- Initially: 019803, UNKNOWN, geometry=NULL. Update only with source coordinates.

WITH raw_months AS (
 SELECT date_trunc('month',o.observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS month_start,
        avg(o.conductivity_ms_per_m) AS raw_ec,count(*) AS sample_count
 FROM public.conductivity_observation o
 JOIN public.source_dataset d USING(dataset_id)
 WHERE d.sha256='bd4cf100cb4782e37b355d94f15911c1bab2c4a9d4ad69d2fa2c3b4c5d590ba7'
 GROUP BY 1
), master_months AS (
 SELECT m.month_start,m.conductivity_ms_per_m AS master_ec
 FROM public.monthly_feature m
 JOIN public.source_dataset d USING(dataset_id)
 JOIN public.analysis_area a USING(area_id)
 WHERE d.sha256='f9b2de085a265a13e21779aa7c95b8d0caaed9335ae61d820475f54e519eac71'
   AND a.area_code='TANCHAU' AND m.conductivity_ms_per_m IS NOT NULL
)
SELECT count(*) FILTER(WHERE r.raw_ec IS NOT NULL AND m.master_ec IS NOT NULL) AS paired_months,
       count(*) FILTER(WHERE r.raw_ec IS NULL OR m.master_ec IS NULL) AS unpaired_months,
       count(*) FILTER(WHERE abs(r.raw_ec-m.master_ec)>1e-10) AS mismatched_months,
       max(abs(r.raw_ec-m.master_ec)) AS largest_difference,
       min(r.sample_count) AS min_samples_per_month,
       max(r.sample_count) AS max_samples_per_month
FROM raw_months r FULL JOIN master_months m USING(month_start);

-- In pgAdmin, run this last query separately if you need its complete result.
-- Each source snapshot must be selected explicitly; never pool their duplicates.
SELECT a.area_code,m.month_start,m.conductivity_ms_per_m,m.water_level_m,m.glofas_discharge_m3s
FROM public.monthly_feature m
JOIN public.analysis_area a USING(area_id)
JOIN public.source_dataset d USING(dataset_id)
WHERE d.sha256='f9b2de085a265a13e21779aa7c95b8d0caaed9335ae61d820475f54e519eac71'
ORDER BY a.area_code,m.month_start;
