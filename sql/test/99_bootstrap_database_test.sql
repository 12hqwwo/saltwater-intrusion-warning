-- ONLY for a NEW EMPTY test database dongthap_gis_etl_test.
-- Based on the two supplied DDL scripts; same tables and constraints.
-- Existing object guards are retained. Never run on the main database.
BEGIN;
SET LOCAL client_encoding='UTF8';
-- Schema v1. Chay MOT LAN trong database dongthap_gis_etl_test, sau 00_preflight.sql.
-- Toan bo trong mot transaction. Khong xoa/sua bang da co.

SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL search_path = public, pg_catalog;

DO $$
BEGIN
  IF current_database() <> 'dongthap_gis_etl_test' THEN
    RAISE EXCEPTION 'Hay mo Query Tool cua database dongthap_gis_etl_test. Dang o: %', current_database();
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname IN
      ('data_source','admin_boundary','salinity_station','irrigation_gate',
       'salinity_observation','water_level_observation',
       'v_station_latest','v_station_training')
  ) THEN
    RAISE EXCEPTION 'Da co doi tuong trung ten. Khong chay lai schema va khong DROP; doi chieu schema hien tai.';
  END IF;
END $$;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_extension e JOIN pg_namespace n ON e.extnamespace=n.oid
    WHERE e.extname='postgis' AND n.nspname='public'
  ) THEN
    RAISE EXCEPTION 'PostGIS dang o schema khac public; can doi chieu cau hinh truoc khi chay bo nay.';
  END IF;
END $$;

CREATE TABLE public.data_source (
  source_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_code varchar(64) NOT NULL UNIQUE CHECK (source_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
  source_name text NOT NULL CHECK (btrim(source_name) <> ''),
  source_type varchar(16) NOT NULL CHECK (source_type IN ('OFFICIAL','RESEARCH','MANUAL','SYNTHETIC')),
  reference text NOT NULL CHECK (btrim(reference) <> ''),
  is_demo boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, is_demo),
  CHECK (is_demo = (source_type = 'SYNTHETIC'))
);

CREATE TABLE public.admin_boundary (
  boundary_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  boundary_code varchar(64) NOT NULL CHECK (btrim(boundary_code) <> ''),
  boundary_name text NOT NULL CHECK (btrim(boundary_name) <> ''),
  admin_level varchar(16) NOT NULL CHECK (admin_level IN ('PROVINCE','COMMUNE','STUDY_AREA')),
  valid_from date NOT NULL,
  valid_to date,
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL,
  geom geometry(MultiPolygon,4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo),
  UNIQUE (boundary_code,valid_from,is_demo),
  CHECK (isfinite(valid_from) AND (valid_to IS NULL OR (isfinite(valid_to) AND valid_to >= valid_from))),
  CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom)),
  CHECK (ST_XMin(Box3D(geom)) >= -180 AND ST_XMax(Box3D(geom)) <= 180
     AND ST_YMin(Box3D(geom)) >= -90 AND ST_YMax(Box3D(geom)) <= 90)
);

CREATE TABLE public.salinity_station (
  station_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  station_code varchar(64) NOT NULL UNIQUE CHECK (station_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
  station_name text NOT NULL CHECK (btrim(station_name) <> ''),
  waterway_name text,
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  geom geometry(Point,4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (station_id,is_demo),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo),
  CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom)),
  CHECK (ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90)
);

CREATE TABLE public.irrigation_gate (
  gate_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  gate_code varchar(64) NOT NULL UNIQUE CHECK (gate_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
  gate_name text NOT NULL CHECK (btrim(gate_name) <> ''),
  waterway_name text,
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  geom geometry(Point,4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (gate_id,is_demo),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo),
  CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom)),
  CHECK (ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90)
);

CREATE TABLE public.salinity_observation (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  station_id bigint NOT NULL,
  observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
  salinity_ppt double precision NOT NULL
    CHECK (salinity_ppt >= 0 AND salinity_ppt < 'Infinity'::double precision),
  quality_flag varchar(16) NOT NULL DEFAULT 'UNVERIFIED'
    CHECK (quality_flag IN ('UNVERIFIED','VALIDATED','SUSPECT','INVALID')),
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (station_id,observed_at),
  FOREIGN KEY (station_id,is_demo) REFERENCES public.salinity_station(station_id,is_demo),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo)
);

CREATE TABLE public.water_level_observation (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  station_id bigint NOT NULL,
  observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
  water_level_m double precision NOT NULL
    CHECK (water_level_m > '-Infinity'::double precision AND water_level_m < 'Infinity'::double precision),
  vertical_datum text NOT NULL CHECK (btrim(vertical_datum) <> ''),
  quality_flag varchar(16) NOT NULL DEFAULT 'UNVERIFIED'
    CHECK (quality_flag IN ('UNVERIFIED','VALIDATED','SUSPECT','INVALID')),
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (station_id,observed_at),
  FOREIGN KEY (station_id,is_demo) REFERENCES public.salinity_station(station_id,is_demo),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo)
);

CREATE INDEX idx_boundary_geom ON public.admin_boundary USING gist(geom);
CREATE INDEX idx_station_geom ON public.salinity_station USING gist(geom);
CREATE INDEX idx_gate_geom ON public.irrigation_gate USING gist(geom);
CREATE INDEX idx_boundary_source ON public.admin_boundary(source_id);
CREATE INDEX idx_station_source ON public.salinity_station(source_id);
CREATE INDEX idx_gate_source ON public.irrigation_gate(source_id);
CREATE INDEX idx_salinity_source ON public.salinity_observation(source_id);
CREATE INDEX idx_water_source ON public.water_level_observation(source_id);
CREATE INDEX idx_salinity_time ON public.salinity_observation(observed_at);
CREATE INDEX idx_water_time ON public.water_level_observation(observed_at);

-- Giu tat ca tram, ke ca tram chua co so do. Khong che mat quality_flag.
CREATE VIEW public.v_station_latest AS
SELECT s.station_id,s.station_code,s.station_name,s.waterway_name,s.is_demo,s.is_active,
       s.geom,o.observed_at,o.salinity_ppt,o.quality_flag,o.source_id AS observation_source_id
FROM public.salinity_station s
LEFT JOIN LATERAL (
  SELECT x.observed_at,x.salinity_ppt,x.quality_flag,x.source_id
  FROM public.salinity_observation x
  WHERE x.station_id=s.station_id AND x.quality_flag <> 'INVALID'
  ORDER BY x.observed_at DESC LIMIT 1
) o ON true;

-- Du lieu huan luyen mac dinh: chi so do thuc te da duoc xac minh.
CREATE VIEW public.v_station_training AS
SELECT o.observation_id,o.station_id,s.station_code,o.observed_at,o.salinity_ppt,o.source_id
FROM public.salinity_observation o
JOIN public.salinity_station s ON s.station_id=o.station_id
WHERE o.is_demo=false AND o.quality_flag='VALIDATED';

COMMENT ON TABLE public.data_source IS 'Nguon va phan loai du lieu. SYNTHETIC bat buoc is_demo=true.';
COMMENT ON TABLE public.admin_boundary IS 'Ranh gioi co phien ban theo valid_from; chi nap khi co nguon va CRS xac minh.';
COMMENT ON TABLE public.salinity_station IS 'Danh muc tram. Moi tram nhieu so do; khong luu gia tri man hien tai tai day.';
COMMENT ON TABLE public.irrigation_gate IS 'Danh muc cong; khong luu khuyen nghi nhu trang thai van hanh thuc te.';
COMMENT ON COLUMN public.salinity_observation.salinity_ppt IS 'Do man theo phan nghin khoi luong (g/kg); khong nap truc tiep EC hoac PSU khi chua chuan hoa co can cu.';
COMMENT ON COLUMN public.water_level_observation.vertical_datum IS 'Moc cao do do nguon du lieu cong bo; bat buoc de dien giai water_level_m.';
COMMENT ON VIEW public.v_station_training IS 'Chi du lieu thuc VALIDATED; demo se cho 0 dong la dung.';

-- Migration bo sung v2. Chay MOT LAN trong dongthap_gis_etl_test, sau schema nen v1.
-- Giu nguyen tat ca bang v1. Khong DROP/ALTER/TRUNCATE du lieu hien co.

SET LOCAL search_path=public,pg_catalog;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
DO $$ BEGIN
  IF current_database()<>'dongthap_gis_etl_test' THEN
    RAISE EXCEPTION 'Can mo Query Tool cua database dongthap_gis_etl_test';
  END IF;
  IF to_regclass('public.data_source') IS NULL THEN
    RAISE EXCEPTION 'Can schema v1 truoc. Neu DB moi, chay 01_core_schema_if_new.sql';
  END IF;
END $$;

CREATE TABLE public.analysis_area (
  area_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  area_code varchar(32) NOT NULL UNIQUE,
  area_name text NOT NULL CHECK (btrim(area_name)<>''),
  scope_note text NOT NULL CHECK (btrim(scope_note)<>'')
);

CREATE TABLE public.source_dataset (
  dataset_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  dataset_code varchar(96) NOT NULL UNIQUE,
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL DEFAULT false CHECK (is_demo=false),
  dataset_kind varchar(24) NOT NULL CHECK (dataset_kind IN ('RAW_EC','MONTHLY_FEATURES')),
  data_product_kind varchar(24) NOT NULL CHECK (data_product_kind IN ('IN_SITU_OBSERVATION','MIXED_DERIVED')),
  source_filename text NOT NULL CHECK (btrim(source_filename)<>''),
  sha256 char(64) NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  source_row_count integer NOT NULL CHECK (source_row_count>=0),
  metadata jsonb NOT NULL CHECK (jsonb_typeof(metadata)='object'),
  imported_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (dataset_id,dataset_kind),
  UNIQUE (dataset_id,source_id,dataset_kind),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo),
  CHECK ((dataset_kind='RAW_EC' AND data_product_kind='IN_SITU_OBSERVATION') OR
         (dataset_kind='MONTHLY_FEATURES' AND data_product_kind='MIXED_DERIVED'))
);

CREATE TABLE public.measurement_site (
  site_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  site_code varchar(64) NOT NULL UNIQUE,
  source_id bigint NOT NULL,
  is_demo boolean NOT NULL DEFAULT false CHECK (is_demo=false),
  country_code char(2) NOT NULL,
  external_site_code varchar(64) NOT NULL,
  site_name text NOT NULL CHECK (btrim(site_name)<>''),
  area_id bigint REFERENCES public.analysis_area(area_id),
  geom geometry(Point,4326),
  location_status varchar(16) NOT NULL DEFAULT 'UNKNOWN'
    CHECK (location_status IN ('UNKNOWN','REPORTED','VERIFIED')),
  location_reference text,
  UNIQUE (source_id,country_code,external_site_code),
  UNIQUE (site_id,source_id),
  FOREIGN KEY (source_id,is_demo) REFERENCES public.data_source(source_id,is_demo),
  CHECK ((geom IS NULL AND location_status='UNKNOWN') OR
         (geom IS NOT NULL AND location_status IN ('REPORTED','VERIFIED')
          AND location_reference IS NOT NULL AND btrim(location_reference)<>''
          AND NOT ST_IsEmpty(geom) AND ST_IsValid(geom)
          AND ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90))
);

CREATE TABLE public.conductivity_observation (
  ec_observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  dataset_id bigint NOT NULL,
  dataset_kind varchar(24) NOT NULL DEFAULT 'RAW_EC' CHECK (dataset_kind='RAW_EC'),
  source_id bigint NOT NULL,
  site_id bigint NOT NULL,
  source_row integer NOT NULL CHECK (source_row>=2),
  observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
  conductivity_ms_per_m double precision NOT NULL
    CHECK (conductivity_ms_per_m>=0 AND conductivity_ms_per_m<'Infinity'::double precision),
  unit varchar(8) NOT NULL DEFAULT 'mS/m' CHECK (unit='mS/m'),
  source_label text NOT NULL,
  observed_or_estimated char(1) NOT NULL CHECK (observed_or_estimated IN ('O','E')),
  approval_level text NOT NULL,
  grade text NOT NULL,
  quality_flag varchar(16) NOT NULL DEFAULT 'UNVERIFIED'
    CHECK (quality_flag IN ('UNVERIFIED','VALIDATED','SUSPECT','INVALID')),
  UNIQUE (dataset_id,site_id,observed_at),
  UNIQUE (dataset_id,source_row),
  FOREIGN KEY (dataset_id,source_id,dataset_kind)
    REFERENCES public.source_dataset(dataset_id,source_id,dataset_kind),
  FOREIGN KEY (site_id,source_id) REFERENCES public.measurement_site(site_id,source_id)
);

CREATE TABLE public.monthly_feature (
  dataset_id bigint NOT NULL,
  dataset_kind varchar(24) NOT NULL DEFAULT 'MONTHLY_FEATURES' CHECK (dataset_kind='MONTHLY_FEATURES'),
  area_id bigint NOT NULL REFERENCES public.analysis_area(area_id),
  month_start date NOT NULL CHECK (isfinite(month_start) AND extract(day FROM month_start)=1),
  source_row integer NOT NULL CHECK (source_row>=2),
  conductivity_ms_per_m double precision CHECK (conductivity_ms_per_m>=0 AND conductivity_ms_per_m<'Infinity'::double precision),
  precipitation_sum double precision CHECK (precipitation_sum>=0 AND precipitation_sum<'Infinity'::double precision),
  temperature_mean double precision CHECK (temperature_mean>'-Infinity'::double precision AND temperature_mean<'Infinity'::double precision),
  temperature_max double precision CHECK (temperature_max>'-Infinity'::double precision AND temperature_max<'Infinity'::double precision),
  temperature_min double precision CHECK (temperature_min>'-Infinity'::double precision AND temperature_min<'Infinity'::double precision),
  evapotranspiration_sum double precision CHECK (evapotranspiration_sum>=0 AND evapotranspiration_sum<'Infinity'::double precision),
  windspeed_mean double precision CHECK (windspeed_mean>=0 AND windspeed_mean<'Infinity'::double precision),
  humidity_mean double precision CHECK (humidity_mean BETWEEN 0 AND 100),
  shortwave_rad_sum double precision CHECK (shortwave_rad_sum>=0 AND shortwave_rad_sum<'Infinity'::double precision),
  water_level_m double precision CHECK (water_level_m>'-Infinity'::double precision AND water_level_m<'Infinity'::double precision),
  glofas_discharge_m3s double precision CHECK (glofas_discharge_m3s>=0 AND glofas_discharge_m3s<'Infinity'::double precision),
  PRIMARY KEY (dataset_id,area_id,month_start),
  UNIQUE (dataset_id,source_row),
  FOREIGN KEY (dataset_id,dataset_kind) REFERENCES public.source_dataset(dataset_id,dataset_kind),
  CHECK (temperature_min<=temperature_mean AND temperature_mean<=temperature_max)
);

CREATE INDEX idx_measurement_site_geom ON public.measurement_site USING gist(geom);
CREATE INDEX idx_measurement_site_area ON public.measurement_site(area_id);
CREATE INDEX idx_ec_site_time ON public.conductivity_observation(site_id,observed_at);
CREATE INDEX idx_ec_source ON public.conductivity_observation(source_id);
CREATE INDEX idx_dataset_source ON public.source_dataset(source_id);
CREATE INDEX idx_monthly_area_time ON public.monthly_feature(area_id,month_start);

CREATE VIEW public.v_monthly_coverage AS
SELECT d.dataset_code,a.area_code,count(*) AS calendar_rows,
       min(m.month_start) AS first_month,max(m.month_start) AS last_month,
       count(m.conductivity_ms_per_m) AS ec_months,
       count(m.water_level_m) AS water_level_months,
       count(m.glofas_discharge_m3s) AS discharge_months
FROM public.monthly_feature m
JOIN public.source_dataset d USING(dataset_id)
JOIN public.analysis_area a USING(area_id)
GROUP BY d.dataset_code,a.area_code;

COMMENT ON TABLE public.analysis_area IS 'Nhom phan tich TanChau/MyTho trong pipeline; KHONG phai cam ket moi nguon cung mot toa do tram.';
COMMENT ON TABLE public.source_dataset IS 'Snapshot bat bien theo SHA-256. Du lieu that chua xac minh van is_demo=false; trang thai chat luong doc lap.';
COMMENT ON TABLE public.measurement_site IS 'Doi tuong do vat ly theo nguon. NULL geom khi file goc chua cung cap toa do duoc xac minh.';
COMMENT ON TABLE public.conductivity_observation IS 'EC goc mS/m. Giu timezone, O/E, approval va grade. Khong quy doi sang salinity_ppt.';
COMMENT ON TABLE public.monthly_feature IS 'Ban sao co cau truc cua master_timeseries; khong phai quan trac tuc thoi hoac nguon van hanh. Phai chon dataset ro rang khi truy van.';
COMMENT ON COLUMN public.monthly_feature.windspeed_mean IS 'Giu ten cot legacy; code goc tinh mean cua daily maximum. Don vi chua xac minh tu metadata Open-Meteo.';
COMMENT ON COLUMN public.monthly_feature.water_level_m IS 'So tong hop DAHITI theo nhan khu vuc; chua gan cho toa do tram MRC va chua biet moc cao do.';
COMMENT ON COLUMN public.monthly_feature.glofas_discharge_m3s IS 'Snapshot legacy da lay trung binh khong gian. Can kiem tra luoi goc truoc khi coi la luu luong tai tram.';

COMMIT;

