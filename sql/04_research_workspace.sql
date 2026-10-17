-- Additive research schema. Does not alter the existing 11 business tables.
-- Run transactionally through scripts/import_research_workspace.py --apply.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS webgis_research;

CREATE TABLE IF NOT EXISTS webgis_research.snapshot (
  snapshot_id text PRIMARY KEY CHECK (snapshot_id ~ '^[0-9a-f]{64}$'),
  imported_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL CHECK (jsonb_typeof(metadata) = 'object')
);
CREATE TABLE IF NOT EXISTS webgis_research.source (
  snapshot_id text NOT NULL REFERENCES webgis_research.snapshot,
  source_id text NOT NULL,
  metadata jsonb NOT NULL,
  PRIMARY KEY (snapshot_id, source_id)
);
CREATE TABLE IF NOT EXISTS webgis_research.site (
  snapshot_id text NOT NULL REFERENCES webgis_research.snapshot,
  site_code text NOT NULL,
  site_name text NOT NULL,
  geom geometry(Point,4326),
  metadata jsonb NOT NULL,
  PRIMARY KEY (snapshot_id, site_code),
  CHECK (geom IS NULL OR (NOT ST_IsEmpty(geom) AND ST_IsValid(geom) AND
    ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90))
);
CREATE TABLE IF NOT EXISTS webgis_research.ec_observation (
  snapshot_id text NOT NULL,
  site_code text NOT NULL,
  observed_date date NOT NULL,
  observed_at timestamptz,
  time_precision text NOT NULL CHECK (time_precision IN ('DATE_ONLY','SOURCE_TIMESTAMP')),
  ec_ms_m double precision NOT NULL CHECK (ec_ms_m >= 0 AND ec_ms_m < 'Infinity'::float8),
  quality_flag text NOT NULL,
  source_id text NOT NULL,
  metadata jsonb NOT NULL,
  PRIMARY KEY (snapshot_id, site_code, observed_date),
  FOREIGN KEY (snapshot_id,site_code) REFERENCES webgis_research.site,
  FOREIGN KEY (snapshot_id,source_id) REFERENCES webgis_research.source,
  CHECK ((time_precision='DATE_ONLY' AND observed_at IS NULL) OR
         (time_precision='SOURCE_TIMESTAMP' AND observed_at IS NOT NULL AND isfinite(observed_at)
          AND (observed_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date=observed_date))
);
CREATE TABLE IF NOT EXISTS webgis_research.gate_catalog (
  snapshot_id text NOT NULL REFERENCES webgis_research.snapshot,
  gate_code text NOT NULL,
  gate_name text NOT NULL,
  source_id text NOT NULL,
  geom geometry(Point,4326),
  metadata jsonb NOT NULL,
  PRIMARY KEY (snapshot_id,gate_code),
  FOREIGN KEY (snapshot_id,source_id) REFERENCES webgis_research.source
);
CREATE TABLE IF NOT EXISTS webgis_research.experiment (
  snapshot_id text NOT NULL,
  experiment_id text NOT NULL,
  site_code text NOT NULL,
  metadata jsonb NOT NULL,
  PRIMARY KEY (snapshot_id,experiment_id),
  FOREIGN KEY (snapshot_id,site_code) REFERENCES webgis_research.site
);
CREATE INDEX IF NOT EXISTS research_site_geom ON webgis_research.site USING gist(geom);
CREATE INDEX IF NOT EXISTS research_gate_geom ON webgis_research.gate_catalog USING gist(geom);
COMMENT ON SCHEMA webgis_research IS 'Versioned research snapshots; no automatic promotion to VALIDATED and no actuator commands.';
COMMENT ON COLUMN webgis_research.site.geom IS 'NULL when CRS is unknown; original coordinates remain in metadata.';
