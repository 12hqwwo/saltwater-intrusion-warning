-- Migration 20: Alert threshold profiles, gate rule profiles, data freshness policy.
-- Chay sau 10_extend_realdata_schema.sql.
-- Khong DROP/ALTER bang cu.
BEGIN;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';

DO $$ BEGIN
  IF current_database() <> 'dongthap_gis' THEN
    RAISE EXCEPTION 'Mo Query Tool cua database dongthap_gis. Dang o: %', current_database();
  END IF;
  IF to_regclass('public.conductivity_observation') IS NULL THEN
    RAISE EXCEPTION 'Can 10_extend_realdata_schema.sql truoc.';
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────
-- 1. ALERT THRESHOLD PROFILE
--    Dung cho dashboard / risk classification.
--    KHONG dung de quyet dinh mo/dong cong.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE public.alert_threshold_profile (
  threshold_profile_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  profile_code           VARCHAR(80)  NOT NULL UNIQUE
                           CHECK (btrim(profile_code) <> ''),
  profile_name           VARCHAR(200) NOT NULL
                           CHECK (btrim(profile_name) <> ''),
  -- FK sang measurement_site (thay the salinity_station cu)
  site_id                BIGINT REFERENCES public.measurement_site(site_id),
  -- Nguong canh bao (mS/m)
  watch_min_ec_ms_per_m  DOUBLE PRECISION NOT NULL
                           CHECK (watch_min_ec_ms_per_m > 0),
  severe_min_ec_ms_per_m DOUBLE PRECISION NOT NULL
                           CHECK (severe_min_ec_ms_per_m > 0),
  -- Metadata nguon
  source_title           TEXT NOT NULL CHECK (btrim(source_title) <> ''),
  source_reference       TEXT,
  -- NULL khi chua xac dinh ngay nghiep vu chinh xac
  effective_from         TIMESTAMPTZ,
  effective_to           TIMESTAMPTZ,
  is_active              BOOLEAN NOT NULL DEFAULT TRUE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (watch_min_ec_ms_per_m < severe_min_ec_ms_per_m),
  CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from)
);

COMMENT ON TABLE  public.alert_threshold_profile IS 'Nguong tham chieu MRC phan loai trang thai EC (NORMAL/WATCH/SEVERE). KHONG la quy tac van hanh.';

-- Seed: nguong MRC tham chieu tai My Tho
-- Lay site_id tu measurement_site (MRC_VN_019805 = My Tho)
INSERT INTO public.alert_threshold_profile
  (profile_code, profile_name, site_id,
   watch_min_ec_ms_per_m, severe_min_ec_ms_per_m,
   source_title, source_reference, effective_from)
SELECT
  'MRC_MYTHO_REF_2023',
  'MRC Reference Thresholds – Mỹ Tho',
  site_id,
  150.0,
  620.0,
  'MRC State of the Basin Report 2023',
  'https://www.mrcmekong.org/publication/',
  NULL
FROM public.measurement_site
WHERE site_code = 'MRC_VN_019805';


-- ─────────────────────────────────────────────────────────────
-- 2. GATE RULE PROFILE
--    Quy tac van hanh cong cu the.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE public.gate_rule_profile (
  gate_rule_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  -- Sua: sluice_gate -> irrigation_gate (khop schema hien tai)
  gate_id                  BIGINT NOT NULL REFERENCES public.irrigation_gate(gate_id),
  max_ec_for_intake        DOUBLE PRECISION NOT NULL CHECK (max_ec_for_intake > 0),
  min_safe_duration_min    INTEGER NOT NULL CHECK (min_safe_duration_min > 0),
  tide_condition           VARCHAR(100),
  water_level_condition    VARCHAR(200),
  valid_from               TIMESTAMPTZ,
  valid_to                 TIMESTAMPTZ,
  approved_by              VARCHAR(100) NOT NULL CHECK (btrim(approved_by) <> ''),
  rule_source              TEXT,
  is_active                BOOLEAN NOT NULL DEFAULT TRUE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from)
);

-- Gate rule required inputs relation (giao tiep cho Decision Engine)
CREATE TABLE public.gate_rule_required_input (
  gate_rule_id             BIGINT NOT NULL REFERENCES public.gate_rule_profile(gate_rule_id),
  input_type               VARCHAR(50) NOT NULL, -- e.g. 'EC', 'TIDE', 'WATER_LEVEL'
  required                 BOOLEAN NOT NULL DEFAULT TRUE,
  max_age_minutes          INTEGER NOT NULL CHECK (max_age_minutes > 0),
  PRIMARY KEY (gate_rule_id, input_type)
);

COMMENT ON TABLE public.gate_rule_profile IS 'Quy tac van hanh cong (luong rieng so voi alert_threshold_profile).';
COMMENT ON TABLE public.gate_rule_required_input IS 'Inputs can thiet va muc do tuoi (freshness) ap dung cho rule do, thay cho viec check freshness global.';

-- ─────────────────────────────────────────────────────────────
-- 3. DATA FRESHNESS POLICY
-- ─────────────────────────────────────────────────────────────
CREATE TABLE public.data_freshness_policy (
  source_id                BIGINT PRIMARY KEY REFERENCES public.data_source(source_id),
  dataset_kind             VARCHAR(24) NOT NULL DEFAULT 'HISTORICAL', -- HISTORICAL / OPERATIONAL
  expected_cadence_min     INTEGER, -- nullable cho HISTORICAL
  warning_after_min        INTEGER, 
  stale_after_min          INTEGER,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  public.data_freshness_policy IS 'Data cadence theo tung source va product type (historical/operational).';

-- ─────────────────────────────────────────────────────────────
-- 4. SYSTEM CAPABILITIES LOG (ghi lai trang thai khai bao)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE public.system_capability_snapshot (
  snapshot_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  snapshotted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  system_mode      VARCHAR(30) NOT NULL DEFAULT 'RESEARCH',
  capabilities     JSONB NOT NULL CHECK (jsonb_typeof(capabilities) = 'object'),
  created_by       VARCHAR(100) NOT NULL DEFAULT 'system'
);

COMMENT ON TABLE public.system_capability_snapshot IS 'Lich su trang thai capabilities. Sau nay Capability Service tu dong generate, con bang nay luu audit trail.';

-- Seed: ban ghi dau tien
INSERT INTO public.system_capability_snapshot (system_mode, capabilities, created_by)
VALUES (
  'RESEARCH',
  '{
    "historical_ec":                   {"enabled": true},
    "monthly_lag_analysis":            {"enabled": true},
    "forecast_3_10d":                  {"enabled": false, "reason_code": "TARGET_RESOLUTION_INSUFFICIENT"},
    "tide_forecast":                   {"enabled": false, "reason_code": "SOURCE_NOT_INTEGRATED"},
    "gate_recommendation_operational": {"enabled": false, "reason_code": "MISSING_OPERATIONAL_INPUTS"},
    "safe_water_window_public":        {"enabled": false, "reason_code": "NO_APPROVED_OPERATION_PLAN"}
  }'::jsonb,
  'system_init'
);

CREATE INDEX idx_capabilities_time ON public.system_capability_snapshot(snapshotted_at DESC);

COMMIT;
