-- Chay trong Query Tool cua database dongthap_gis. Chi doc, khong thay doi DB.
SELECT current_database() AS database_name, current_user AS connected_user,
       current_setting('server_version') AS postgres_version,
       current_setting('TimeZone') AS session_timezone;

SELECT name, default_version, installed_version
FROM pg_available_extensions WHERE name = 'postgis';

-- Neu co ten bang trung voi bo nay: dung lai va doi chieu, khong DROP bang.
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('data_source','admin_boundary','salinity_station',
    'irrigation_gate','salinity_observation','water_level_observation',
    'forecast_run','salinity_forecast','salinity_threshold',
    'gate_recommendation','gate_operation_plan','gate_operation_item')
ORDER BY table_name;
