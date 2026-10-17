-- CHI DOC. Chay tung khoi A01...A12 trong Query Tool, luu CSV theo ma khoi.
-- Chay A01/A02 truoc. Neu PostGIS/bang thieu, dung cac khoi phu thuoc.
-- Khong chay lai script CREATE schema tren DB da co.

-- A01: Ket noi va extension. Khong yeu cau PostGIS de chay cau nay.
SELECT current_database() AS database_name,
       current_setting('server_version') AS postgres_version,
       current_setting('TimeZone') AS session_timezone,
       e.extversion AS postgis_version, n.nspname AS postgis_schema
FROM (VALUES (1)) AS seed(x)
LEFT JOIN pg_extension e ON e.extname='postgis'
LEFT JOIN pg_namespace n ON n.oid=e.extnamespace;

-- A02: 11 bang nen va 2 bang theo ke hoach can kiem tra, khong ket luan da co.
WITH expected(table_name, requirement) AS (VALUES
 ('data_source','BASE'),('admin_boundary','BASE'),('salinity_station','BASE'),
 ('irrigation_gate','BASE'),('salinity_observation','BASE'),
 ('water_level_observation','BASE'),('analysis_area','BASE'),
 ('source_dataset','BASE'),('measurement_site','BASE'),
 ('conductivity_observation','BASE'),('monthly_feature','BASE'),
 ('forecast_result','CHECK_PLAN'),('gate_recommendation','CHECK_PLAN'))
SELECT table_name, requirement,
       to_regclass('public.' || table_name) IS NOT NULL AS exists_in_public
FROM expected ORDER BY requirement, table_name;

-- A03: Ten cot va kieu du lieu thuc te; luu de doi chieu migration/ETL.
SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name IN
 ('data_source','admin_boundary','salinity_station','irrigation_gate',
  'salinity_observation','water_level_observation','analysis_area','source_dataset',
  'measurement_site','conductivity_observation','monthly_feature',
  'forecast_result','gate_recommendation')
ORDER BY table_name,ordinal_position;

-- A04: PK/FK/UNIQUE/CHECK. convalidated=false can duoc giai thich truoc nghiem thu.
SELECT c.conrelid::regclass::text AS table_name,c.conname,c.contype,
       c.convalidated,pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace
WHERE n.nspname='public' AND c.conrelid<>0 AND c.contype IN ('p','f','u','c')
ORDER BY table_name,c.conname;

-- A05: Index thoi gian va GiST hinh hoc.
SELECT tablename,indexname,indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename IN
 ('admin_boundary','irrigation_gate','measurement_site','salinity_station',
  'conductivity_observation','monthly_feature','salinity_observation','water_level_observation')
ORDER BY tablename,indexname;

-- A06: Snapshot, SHA va so dong da luu; khong cong nhieu snapshot thanh so do moi.
SELECT d.dataset_id,d.dataset_code,s.source_code,d.dataset_kind,
       d.source_filename,d.sha256,d.source_row_count,
       CASE WHEN d.dataset_kind='RAW_EC' THEN
         (SELECT count(*) FROM public.conductivity_observation o WHERE o.dataset_id=d.dataset_id)
       WHEN d.dataset_kind='MONTHLY_FEATURES' THEN
         (SELECT count(*) FROM public.monthly_feature m WHERE m.dataset_id=d.dataset_id)
       END AS stored_rows,d.imported_at
FROM public.source_dataset d JOIN public.data_source s USING(source_id)
ORDER BY d.dataset_id;

-- A07: Coverage EC goc theo snapshot/tram. Thoi gian xuat theo UTC+7.
SELECT d.dataset_code,s.site_code,count(*) AS observation_count,
       min(o.observed_at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS first_observation_local,
       max(o.observed_at) AT TIME ZONE 'Asia/Ho_Chi_Minh' AS last_observation_local,
       count(*) FILTER(WHERE o.quality_flag='UNVERIFIED') AS unverified_rows,
       count(*) FILTER(WHERE o.quality_flag='INVALID') AS invalid_rows
FROM public.conductivity_observation o
JOIN public.source_dataset d USING(dataset_id)
JOIN public.measurement_site s USING(site_id)
GROUP BY d.dataset_code,s.site_code ORDER BY d.dataset_code,s.site_code;

-- A08: Lich thang khac voi thang thuc su co gia tri EC.
SELECT d.dataset_code,a.area_code,count(*) AS calendar_rows,
       min(m.month_start) AS first_calendar_month,max(m.month_start) AS last_calendar_month,
       count(m.conductivity_ms_per_m) AS ec_months,
       max(m.month_start) FILTER(WHERE m.conductivity_ms_per_m IS NOT NULL) AS last_month_with_ec,
       count(m.water_level_m) AS water_level_months,
       count(m.glofas_discharge_m3s) AS discharge_months
FROM public.monthly_feature m JOIN public.source_dataset d USING(dataset_id)
JOIN public.analysis_area a USING(area_id)
GROUP BY d.dataset_code,a.area_code ORDER BY d.dataset_code,a.area_code;

-- A09: Chi chay khi PostGIS da duoc cai o public, va measurement_site ton tai.
SELECT s.site_id,s.site_code,s.external_site_code,s.site_name,a.area_code,
       s.location_status,ST_X(s.geom) AS longitude,ST_Y(s.geom) AS latitude,
       ST_SRID(s.geom) AS srid,s.location_reference
FROM public.measurement_site s LEFT JOIN public.analysis_area a USING(area_id)
ORDER BY s.site_code;

-- A10: Dem doi tuong khong gian thuc; khong lay so luong tu CSV truoc de suy ra.
SELECT 'measurement_site' AS table_name,count(*) AS total_rows,count(geom) AS rows_with_geometry,
       count(*) FILTER(WHERE geom IS NOT NULL AND (ST_IsEmpty(geom) OR NOT ST_IsValid(geom))) AS bad_geometry,
       count(*) FILTER(WHERE geom IS NOT NULL AND ST_SRID(geom)<>4326) AS wrong_srid
FROM public.measurement_site WHERE NOT is_demo
UNION ALL
SELECT 'admin_boundary',count(*),count(geom),
       count(*) FILTER(WHERE geom IS NOT NULL AND (ST_IsEmpty(geom) OR NOT ST_IsValid(geom))),
       count(*) FILTER(WHERE geom IS NOT NULL AND ST_SRID(geom)<>4326)
FROM public.admin_boundary WHERE NOT is_demo
UNION ALL
SELECT 'irrigation_gate',count(*),count(geom),
       count(*) FILTER(WHERE geom IS NOT NULL AND (ST_IsEmpty(geom) OR NOT ST_IsValid(geom))),
       count(*) FILTER(WHERE geom IS NOT NULL AND ST_SRID(geom)<>4326)
FROM public.irrigation_gate WHERE NOT is_demo;

-- A11: Danh sach ranh gioi de chon boundary_id va phien ban ro rang.
SELECT b.boundary_id,b.boundary_code,b.boundary_name,b.admin_level,
       b.valid_from,b.valid_to,s.source_code,s.reference,
       ST_GeometryType(b.geom) AS geometry_type,ST_SRID(b.geom) AS srid,
       ST_IsValid(b.geom) AS valid_geometry
FROM public.admin_boundary b JOIN public.data_source s USING(source_id)
WHERE NOT b.is_demo ORDER BY b.boundary_code,b.valid_from;

-- A12: Danh muc cong va nguon toa do hien co.
SELECT g.gate_id,g.gate_code,g.gate_name,g.waterway_name,g.is_active,
       ST_X(g.geom) AS longitude,ST_Y(g.geom) AS latitude,ST_SRID(g.geom) AS srid,
       s.source_code,s.reference
FROM public.irrigation_gate g JOIN public.data_source s USING(source_id)
WHERE NOT g.is_demo ORDER BY g.gate_code;
