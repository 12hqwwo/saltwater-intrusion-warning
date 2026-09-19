-- Schema v1. Chay MOT LAN trong database dongthap_gis, sau 00_preflight.sql.
-- Toan bo trong mot transaction. Khong xoa/sua bang da co.
BEGIN;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL search_path = public, pg_catalog;

DO $$
BEGIN
  IF current_database() <> 'dongthap_gis' THEN
    RAISE EXCEPTION 'Hay mo Query Tool cua database dongthap_gis. Dang o: %', current_database();
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
COMMIT;
