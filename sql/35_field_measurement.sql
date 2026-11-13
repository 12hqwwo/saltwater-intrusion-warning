-- Reviewed staff-only field EC. Kept separate from MRC observation tables.
DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for field EC: %', current_database();
    END IF;
END $$;

CREATE TABLE dss_reference.field_measurement (
    measurement_id uuid PRIMARY KEY,
    geom geometry(Point,4326) NOT NULL,
    ec_mS_m float8 NOT NULL CHECK (ec_mS_m>=0 AND ec_mS_m<=6000 AND ec_mS_m<'Infinity'::float8),
    unit_original text NOT NULL CHECK (unit_original IN ('µS/cm','dS/m','mS/cm','mS/m')),
    ec_basis text NOT NULL CHECK (ec_basis IN ('EC25','RAW','UNKNOWN')),
    calibrated_at date,
    water_temp_degC float8 CHECK (water_temp_degC BETWEEN -5 AND 50),
    observed_at timestamptz NOT NULL,
    position_kind text NOT NULL CHECK (position_kind IN ('RIVER','FIELD')),
    device text NOT NULL CHECK (btrim(device)<>''),
    submitted_by text NOT NULL CHECK (char_length(btrim(submitted_by)) BETWEEN 1 AND 120),
    flags text[] NOT NULL DEFAULT '{}',
    raw_payload jsonb NOT NULL CHECK (jsonb_typeof(raw_payload)='object' AND octet_length(raw_payload::text)<=16384),
    submitted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90),
    CHECK (calibrated_at IS NULL OR calibrated_at<=observed_at::date)
);
CREATE INDEX field_measurement_geom_gist ON dss_reference.field_measurement USING gist(geom);
CREATE INDEX field_measurement_observed_idx ON dss_reference.field_measurement(observed_at DESC);

CREATE TABLE dss_reference.field_measurement_review (
    review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    measurement_id uuid NOT NULL REFERENCES dss_reference.field_measurement(measurement_id),
    decision text NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
    reviewer text NOT NULL CHECK (btrim(reviewer)<>''),
    note text NOT NULL,
    reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX field_review_latest_idx ON dss_reference.field_measurement_review
    (measurement_id,reviewed_at DESC,review_id DESC);

CREATE VIEW dss_reference.v_field_measurement_status AS
SELECT m.*,coalesce(r.decision,'PENDING') AS status,
       r.review_id,r.reviewer,r.note AS review_note,r.reviewed_at
FROM dss_reference.field_measurement m
LEFT JOIN LATERAL (
    SELECT review_id,decision,reviewer,note,reviewed_at
    FROM dss_reference.field_measurement_review
    WHERE measurement_id=m.measurement_id
    ORDER BY reviewed_at DESC,review_id DESC LIMIT 1
) r ON true;

CREATE FUNCTION dss_reference.stamp_field_event() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF TG_TABLE_NAME='field_measurement' THEN
        NEW.submitted_at:=clock_timestamp();
    ELSE
        NEW.reviewed_at:=clock_timestamp();
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER field_measurement_stamp BEFORE INSERT ON dss_reference.field_measurement
FOR EACH ROW EXECUTE FUNCTION dss_reference.stamp_field_event();
CREATE TRIGGER field_review_stamp BEFORE INSERT ON dss_reference.field_measurement_review
FOR EACH ROW EXECUTE FUNCTION dss_reference.stamp_field_event();

CREATE TRIGGER field_measurement_immutable BEFORE UPDATE OR DELETE ON dss_reference.field_measurement
FOR EACH ROW EXECUTE FUNCTION dss_reference.reject_forecast_mutation();
CREATE TRIGGER field_review_immutable BEFORE UPDATE OR DELETE ON dss_reference.field_measurement_review
FOR EACH ROW EXECUTE FUNCTION dss_reference.reject_forecast_mutation();

CREATE OR REPLACE FUNCTION webgis_security.audit_dss_insert() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    INSERT INTO webgis_security.audit_log(database_actor,application_actor,table_name,action,record_id)
    VALUES (session_user,coalesce(nullif(current_setting('webgis.actor',true),''),'SYSTEM'),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,TG_OP,
        coalesce(to_jsonb(NEW)->>'draft_id',to_jsonb(NEW)->>'prediction_id',
                 to_jsonb(NEW)->>'review_id',to_jsonb(NEW)->>'measurement_id',
                 to_jsonb(NEW)->>'event_id',to_jsonb(NEW)->>'score_id',
                 to_jsonb(NEW)->>'issue_id',to_jsonb(NEW)->>'slot_id'));
    RETURN NEW;
END;
$$;
CREATE TRIGGER audit_field_measurement AFTER INSERT ON dss_reference.field_measurement
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();
CREATE TRIGGER audit_field_review AFTER INSERT ON dss_reference.field_measurement_review
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();

COMMENT ON TABLE dss_reference.field_measurement IS 'Append-only staff submission. Not MRC data and not an operational decision until reviewed.';
COMMENT ON TABLE dss_reference.field_measurement_review IS 'Append-only review history; the latest review controls visibility.';

GRANT SELECT ON dss_reference.field_measurement,dss_reference.field_measurement_review,
    dss_reference.v_field_measurement_status TO webgis_reader;
GRANT SELECT,INSERT ON dss_reference.field_measurement,dss_reference.field_measurement_review TO webgis_writer;
GRANT USAGE ON SEQUENCE dss_reference.field_measurement_review_review_id_seq TO webgis_writer;
