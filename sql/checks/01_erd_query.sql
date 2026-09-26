-- =============================================================================
-- ERD Query: Hiển thị toàn bộ schema dongthap_gis (bảng, cột, FK)
-- Chạy trong pgAdmin Query Tool của database dongthap_gis
-- Để xem ERD đồ họa: Tools → ERD Tool (pgAdmin 7+)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- A. Danh sách tất cả bảng trong schema public
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    c.relname                                   AS table_name,
    pg_catalog.obj_description(c.oid, 'pg_class') AS description,
    pg_catalog.pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    (SELECT reltuples::bigint FROM pg_class WHERE oid = c.oid) AS approx_rows
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY c.relname;

-- ─────────────────────────────────────────────────────────────────────────────
-- B. Chi tiết cột từng bảng (tên, kiểu, nullable, default, comment)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    n.nspname                           AS schema_name,
    c.relname                           AS table_name,
    a.attnum                            AS col_order,
    a.attname                           AS column_name,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
    CASE WHEN a.attnotnull THEN 'NOT NULL' ELSE 'nullable' END AS nullable,
    pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS default_value,
    pg_catalog.col_description(c.oid, a.attnum)  AS col_comment
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n    ON n.oid = c.relnamespace
JOIN pg_catalog.pg_attribute a    ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY c.relname, a.attnum;

-- ─────────────────────────────────────────────────────────────────────────────
-- C. Tất cả Primary Key và Unique constraints
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    n.nspname                  AS schema_name,
    t.relname                  AS table_name,
    i.relname                  AS index_name,
    CASE ix.indisprimary WHEN true THEN 'PRIMARY KEY' ELSE 'UNIQUE' END AS constraint_type,
    array_agg(a.attname ORDER BY a.attnum) AS columns
FROM pg_catalog.pg_class t
JOIN pg_catalog.pg_namespace n  ON n.oid = t.relnamespace
JOIN pg_catalog.pg_index ix     ON ix.indrelid = t.oid AND (ix.indisprimary OR ix.indisunique)
JOIN pg_catalog.pg_class i      ON i.oid = ix.indexrelid
JOIN pg_catalog.pg_attribute a  ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
WHERE n.nspname = 'public'
  AND t.relkind = 'r'
GROUP BY n.nspname, t.relname, i.relname, ix.indisprimary
ORDER BY t.relname, constraint_type;

-- ─────────────────────────────────────────────────────────────────────────────
-- D. Tất cả Foreign Key (quan hệ giữa các bảng) – đây là backbone ERD
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    tc.table_name                      AS source_table,
    kcu.column_name                    AS source_column,
    ccu.table_name                     AS target_table,
    ccu.column_name                    AS target_column,
    tc.constraint_name                 AS fk_name,
    rc.update_rule,
    rc.delete_rule
FROM information_schema.table_constraints       AS tc
JOIN information_schema.key_column_usage        AS kcu
     ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema   = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
     ON ccu.constraint_name = tc.constraint_name
     AND ccu.table_schema   = tc.table_schema
JOIN information_schema.referential_constraints AS rc
     ON rc.constraint_name = tc.constraint_name
     AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema    = 'public'
ORDER BY source_table, fk_name;

-- ─────────────────────────────────────────────────────────────────────────────
-- E. Geometry columns (PostGIS)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    f_table_name    AS table_name,
    f_geometry_column AS geom_column,
    type            AS geometry_type,
    srid,
    coord_dimension
FROM geometry_columns
WHERE f_table_schema = 'public'
ORDER BY f_table_name;

-- ─────────────────────────────────────────────────────────────────────────────
-- F. Số hàng thực tế từng bảng
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    'data_source'              AS table_name, COUNT(*) AS row_count FROM public.data_source
UNION ALL SELECT 'admin_boundary',            COUNT(*) FROM public.admin_boundary
UNION ALL SELECT 'salinity_station',          COUNT(*) FROM public.salinity_station
UNION ALL SELECT 'irrigation_gate',           COUNT(*) FROM public.irrigation_gate
UNION ALL SELECT 'salinity_observation',      COUNT(*) FROM public.salinity_observation
UNION ALL SELECT 'water_level_observation',   COUNT(*) FROM public.water_level_observation
-- Extended real-data tables (if migration 10 was run)
UNION ALL SELECT 'analysis_area',             COUNT(*) FROM public.analysis_area             WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='analysis_area' AND table_schema='public')
UNION ALL SELECT 'measurement_site',          COUNT(*) FROM public.measurement_site          WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='measurement_site' AND table_schema='public')
UNION ALL SELECT 'source_dataset',            COUNT(*) FROM public.source_dataset            WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='source_dataset' AND table_schema='public')
UNION ALL SELECT 'conductivity_observation',  COUNT(*) FROM public.conductivity_observation  WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='conductivity_observation' AND table_schema='public')
UNION ALL SELECT 'monthly_feature',           COUNT(*) FROM public.monthly_feature           WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='monthly_feature' AND table_schema='public')
ORDER BY table_name;
