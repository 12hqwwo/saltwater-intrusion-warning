-- Applied in one transaction by scripts/apply_dss_storage.py. No public table writes.
-- Existing incompatible DSS tables cause an error instead of being overwritten.
CREATE SCHEMA IF NOT EXISTS dss_reference;

CREATE TABLE dss_reference.ec_threshold_presets (
    preset_code varchar(64) PRIMARY KEY CHECK (preset_code ~ '^[A-Z0-9_-]+$'),
    usage_purpose text NOT NULL CHECK (btrim(usage_purpose) <> ''),
    threshold_ms_m double precision NOT NULL CHECK (threshold_ms_m > 0 AND threshold_ms_m < 'Infinity'::float8),
    ec_basis varchar(16) NOT NULL CHECK (ec_basis IN ('UNKNOWN','RAW','EC25')),
    allow_intake_below_ms_m double precision,
    stop_intake_from_ms_m double precision,
    source_note text NOT NULL CHECK (btrim(source_note) <> ''),
    evidence_status varchar(32) NOT NULL CHECK (evidence_status IN ('USER_SCENARIO_UNVERIFIED','SOURCE_REVIEW_REQUIRED')),
    is_operational_rule boolean NOT NULL DEFAULT false CHECK (NOT is_operational_rule),
    CHECK ((allow_intake_below_ms_m IS NULL AND stop_intake_from_ms_m IS NULL)
        OR (allow_intake_below_ms_m IS NOT NULL AND stop_intake_from_ms_m IS NOT NULL
            AND allow_intake_below_ms_m > 0 AND stop_intake_from_ms_m > allow_intake_below_ms_m
            AND stop_intake_from_ms_m < 'Infinity'::float8))
);

-- Illustrative user-supplied comparison scenarios, not crop/safety standards.
INSERT INTO dss_reference.ec_threshold_presets
    (preset_code,usage_purpose,threshold_ms_m,ec_basis,allow_intake_below_ms_m,stop_intake_from_ms_m,source_note,evidence_status)
VALUES
    ('SCENARIO_EC50','Đối chiếu EC 50 mS/m',50,'UNKNOWN',50,80,
     'Giá trị minh họa do người dùng cung cấp, chưa xác nhận ngưỡng cây trồng/cấp nước. Không phải quy trình vận hành.', 'USER_SCENARIO_UNVERIFIED'),
    ('SCENARIO_EC100','Đối chiếu EC 100 mS/m',100,'UNKNOWN',100,150,
     'Giá trị minh họa do người dùng cung cấp, chưa xác nhận ngưỡng cây trồng/cấp nước. Không phải quy trình vận hành.', 'USER_SCENARIO_UNVERIFIED'),
    ('SCENARIO_EC150','Đối chiếu EC 150 mS/m',150,'UNKNOWN',120,200,
     'Giá trị minh họa do người dùng cung cấp, chưa xác nhận ngưỡng cây trồng/cấp nước. Không phải quy trình vận hành.', 'USER_SCENARIO_UNVERIFIED');

CREATE TABLE dss_reference.multivariate_prediction_log (
    prediction_id uuid PRIMARY KEY,
    station_key varchar(16) NOT NULL CHECK (station_key IN ('MyTho','TanChau')),
    site_code varchar(64) NOT NULL,
    target_month date NOT NULL CHECK (isfinite(target_month) AND extract(day FROM target_month)=1),
    input_month date NOT NULL CHECK (isfinite(input_month) AND extract(day FROM input_month)=1),
    input_mode varchar(16) NOT NULL CHECK (input_mode IN ('ARCHIVE','MANUAL')),
    model_version varchar(64) NOT NULL CHECK (btrim(model_version) <> ''),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
    saved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (input_month = (target_month - interval '2 months')::date),
    CHECK ((station_key='MyTho' AND site_code='MRC_VN_019805') OR (station_key='TanChau' AND site_code='MRC_VN_019803')),
    CHECK (payload ?& ARRAY['prediction_id','station','site_code','target_month','input_month','input_mode',
        'model_version','predicted_ec_mS_m','unit','feature_values','input_provenance','issued_at',
        'deployment_ready','gate_decision_eligible']),
    CHECK ((payload->>'prediction_id')::uuid=prediction_id AND payload->>'station'=station_key
        AND payload->>'site_code'=site_code AND payload->>'input_mode'=input_mode
        AND payload->>'model_version'=model_version),
    CHECK (payload->>'target_month'=to_char(target_month,'YYYY-MM')
        AND payload->>'input_month'=to_char(input_month,'YYYY-MM')),
    CHECK (payload->>'unit'='mS/m' AND payload->'deployment_ready'='false'::jsonb
        AND payload->'gate_decision_eligible'='false'::jsonb),
    CHECK (jsonb_typeof(payload->'predicted_ec_mS_m')='number'
        AND (payload->>'predicted_ec_mS_m')::float8 >= 0
        AND (payload->>'predicted_ec_mS_m')::float8 < 'Infinity'::float8)
);
CREATE INDEX idx_dss_prediction_station_month ON dss_reference.multivariate_prediction_log
    (station_key,target_month,saved_at DESC,prediction_id DESC);
CREATE INDEX idx_dss_prediction_saved ON dss_reference.multivariate_prediction_log (saved_at DESC,prediction_id DESC);

CREATE TABLE dss_reference.gate_simulation_drafts (
    draft_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gate_code varchar(64) NOT NULL CHECK (gate_code ~ '^[A-Za-z0-9_-]+$'),
    input_payload jsonb NOT NULL CHECK (jsonb_typeof(input_payload)='object'),
    policy_payload jsonb NOT NULL CHECK (jsonb_typeof(policy_payload)='object'),
    status varchar(32) NOT NULL DEFAULT 'DRAFT_UNVERIFIED' CHECK (status='DRAFT_UNVERIFIED'),
    declarations_verified_by_server boolean NOT NULL DEFAULT false CHECK (NOT declarations_verified_by_server),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (input_payload ?& ARRAY['gate_code','schema_version'] AND policy_payload ?& ARRAY['gate_code','schema_version']),
    CHECK (input_payload->>'gate_code'=gate_code AND policy_payload->>'gate_code'=gate_code),
    CHECK (input_payload->'schema_version'='1'::jsonb AND policy_payload->'schema_version'='1'::jsonb),
    CHECK (octet_length(input_payload::text)+octet_length(policy_payload::text) <= 262144)
);
CREATE INDEX idx_dss_draft_gate_created ON dss_reference.gate_simulation_drafts
    (gate_code,created_at DESC,draft_id DESC);

COMMENT ON TABLE dss_reference.multivariate_prediction_log IS 'Append-only API prediction history; full server-generated JSON preserves unrounded features and provenance. No observation-table writes.';
COMMENT ON TABLE dss_reference.gate_simulation_drafts IS 'Append-only unverified user declarations, not approved procedures or actuator commands.';
