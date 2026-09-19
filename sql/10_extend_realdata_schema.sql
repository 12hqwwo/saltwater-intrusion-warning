-- Migration bo sung v2. Chay MOT LAN trong dongthap_gis, sau schema nen v1.
-- Giu nguyen tat ca bang v1. Khong DROP/ALTER/TRUNCATE du lieu hien co.
BEGIN;
SET LOCAL search_path=public,pg_catalog;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
DO $$ BEGIN
  IF current_database()<>'dongthap_gis' THEN
    RAISE EXCEPTION 'Can mo Query Tool cua database dongthap_gis';
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
