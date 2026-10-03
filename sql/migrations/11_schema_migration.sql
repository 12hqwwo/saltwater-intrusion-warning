-- Pipeline extension required by the execution prompt.
-- This migration is idempotent and does not modify raw observations.
-- Review against the live schema before applying; this repository has no DB
-- connection credentials and therefore cannot prove that the migration ran.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.data_quality_flag (
    quality_code       VARCHAR(20) PRIMARY KEY,
    description        TEXT NOT NULL,
    severity           SMALLINT NOT NULL CHECK (severity BETWEEN 0 AND 3),
    allow_training     BOOLEAN NOT NULL
);

INSERT INTO public.data_quality_flag
    (quality_code, description, severity, allow_training)
VALUES
    ('VERIFIED', 'Passed pipeline QA and eligible for training.', 0, TRUE),
    ('SUSPECT',  'Retained for review; excluded from training by default.', 1, FALSE),
    ('MISSING',  'Expected observation is unavailable; numeric value remains NULL.', 2, FALSE),
    ('REJECTED', 'Structurally or physically invalid record; excluded from training.', 3, FALSE)
ON CONFLICT (quality_code) DO UPDATE SET
    description = EXCLUDED.description,
    severity = EXCLUDED.severity,
    allow_training = EXCLUDED.allow_training;

CREATE TABLE IF NOT EXISTS public.tide_point (
    tide_point_id      BIGSERIAL PRIMARY KEY,
    name               TEXT NOT NULL UNIQUE,
    latitude           DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude          DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    geom               geometry(Point, 4326) NOT NULL,
    model_name         TEXT NOT NULL,
    source             TEXT NOT NULL,
    description        TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ST_SRID(geom) = 4326)
);

CREATE INDEX IF NOT EXISTS idx_tide_point_geom
    ON public.tide_point USING GIST (geom);

CREATE TABLE IF NOT EXISTS public.hydro_point (
    point_id           BIGSERIAL PRIMARY KEY,
    name               TEXT NOT NULL UNIQUE,
    point_type         TEXT NOT NULL,
    latitude           DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude          DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    geom               geometry(Point, 4326) NOT NULL,
    source             TEXT NOT NULL,
    grid_lat           DOUBLE PRECISION,
    grid_lon           DOUBLE PRECISION,
    upstream_area      DOUBLE PRECISION CHECK (upstream_area IS NULL OR upstream_area >= 0),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ST_SRID(geom) = 4326)
);

CREATE INDEX IF NOT EXISTS idx_hydro_point_geom
    ON public.hydro_point USING GIST (geom);

CREATE TABLE IF NOT EXISTS public.tide_prediction (
    id                 BIGSERIAL PRIMARY KEY,
    tide_point_id      BIGINT NOT NULL REFERENCES public.tide_point(tide_point_id),
    observed_at        TIMESTAMPTZ NOT NULL,
    water_level_m      DOUBLE PRECISION,
    model_name         TEXT NOT NULL,
    model_version      TEXT NOT NULL,
    datum              TEXT NOT NULL,
    source             TEXT NOT NULL,
    quality_flag       VARCHAR(20) NOT NULL
                           REFERENCES public.data_quality_flag(quality_code),
    snapshot_id        TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tide_point_id, observed_at, model_name, model_version, snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_tide_prediction_point_time
    ON public.tide_prediction (tide_point_id, observed_at);

CREATE TABLE IF NOT EXISTS public.discharge_observation (
    id                 BIGSERIAL PRIMARY KEY,
    point_id           BIGINT NOT NULL REFERENCES public.hydro_point(point_id),
    observed_at        TIMESTAMPTZ NOT NULL,
    discharge_m3s      DOUBLE PRECISION CHECK (discharge_m3s IS NULL OR discharge_m3s >= 0),
    source             TEXT NOT NULL,
    version            TEXT NOT NULL,
    quality_flag       VARCHAR(20) NOT NULL
                           REFERENCES public.data_quality_flag(quality_code),
    snapshot_id        TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (point_id, observed_at, source, version, snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_discharge_observation_point_time
    ON public.discharge_observation (point_id, observed_at);

CREATE TABLE IF NOT EXISTS public.gate_coordinate_source (
    id                 BIGSERIAL PRIMARY KEY,
    gate_id            BIGINT NOT NULL REFERENCES public.irrigation_gate(gate_id),
    latitude           DOUBLE PRECISION CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude          DOUBLE PRECISION CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    source_id          BIGINT REFERENCES public.data_source(source_id),
    coordinate_method  VARCHAR(30) NOT NULL CHECK (
                           coordinate_method IN (
                               'OFFICIAL', 'VERIFIED_MAP_PIN', 'CANDIDATE', 'UNKNOWN'
                           )
                       ),
    confidence         TEXT,
    verified_at        TIMESTAMPTZ,
    is_primary         BOOLEAN NOT NULL DEFAULT FALSE,
    snapshot_id        TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        NOT is_primary
        OR coordinate_method IN ('OFFICIAL', 'VERIFIED_MAP_PIN')
    ),
    CHECK (
        (latitude IS NULL AND longitude IS NULL)
        OR (latitude IS NOT NULL AND longitude IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_gate_coordinate_primary
    ON public.gate_coordinate_source (gate_id)
    WHERE is_primary;

CREATE INDEX IF NOT EXISTS idx_gate_coordinate_method
    ON public.gate_coordinate_source (coordinate_method);

COMMIT;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'tide_point',
      'tide_prediction',
      'hydro_point',
      'discharge_observation',
      'data_quality_flag',
      'gate_coordinate_source'
  )
ORDER BY table_name;
