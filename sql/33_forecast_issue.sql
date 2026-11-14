-- Immutable monthly issue ledger. Apply with scripts/apply_dss_migration.py.
DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for forecast issue ledger: %', current_database();
    END IF;
END $$;

CREATE TABLE dss_reference.forecast_slot (
    slot_id uuid PRIMARY KEY,
    station_key varchar(16) NOT NULL CHECK (station_key IN ('MYTHO','MYTHUAN','TANCHAU')),
    target_month date NOT NULL CHECK (isfinite(target_month) AND extract(day FROM target_month)=1),
    schedule_code text NOT NULL CHECK (schedule_code='MONTHLY_D06_PREV'),
    scheduled_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(station_key,target_month,schedule_code),
    CHECK (scheduled_at=make_timestamptz(
        extract(year FROM target_month - interval '1 month')::int,
        extract(month FROM target_month - interval '1 month')::int,
        6,9,0,0,'Asia/Ho_Chi_Minh'))
);

CREATE TABLE dss_reference.forecast_slot_event (
    event_id uuid PRIMARY KEY,
    slot_id uuid NOT NULL REFERENCES dss_reference.forecast_slot(slot_id),
    event_type text NOT NULL CHECK (event_type='MISSED'),
    reason_code text NOT NULL CHECK (reason_code IN ('MISSING_INPUT','JOB_NOT_RUN','RUN_FAILED')),
    detected_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(slot_id,event_type)
);

CREATE TABLE dss_reference.forecast_issue (
    issue_id uuid PRIMARY KEY,
    slot_id uuid NOT NULL UNIQUE REFERENCES dss_reference.forecast_slot(slot_id),
    input_month date NOT NULL CHECK (isfinite(input_month) AND extract(day FROM input_month)=1),
    model_version text NOT NULL CHECK (btrim(model_version)<>''),
    model_sha256 char(64) NOT NULL CHECK (model_sha256 ~ '^[0-9a-f]{64}$'),
    data_version char(64) NOT NULL CHECK (data_version ~ '^[0-9a-f]{64}$'),
    predicted_ec_mS_m float8 NOT NULL CHECK (predicted_ec_mS_m>=0 AND predicted_ec_mS_m<'Infinity'::float8),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object' AND octet_length(payload::text)<=262144),
    issue_status text NOT NULL CHECK (issue_status IN ('ON_TIME','LATE')),
    issued_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE dss_reference.forecast_score (
    score_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    issue_id uuid NOT NULL REFERENCES dss_reference.forecast_issue(issue_id),
    label_protocol_version text NOT NULL CHECK (btrim(label_protocol_version)<>''),
    observation_ref text NOT NULL CHECK (btrim(observation_ref)<>''),
    obs_source text NOT NULL CHECK (obs_source IN ('MRC','FIELD_APPROVED')),
    observed_ec_mS_m float8 NOT NULL CHECK (observed_ec_mS_m>=0 AND observed_ec_mS_m<'Infinity'::float8),
    abs_error_mS_m float8 NOT NULL CHECK (abs_error_mS_m>=0 AND abs_error_mS_m<'Infinity'::float8),
    scored_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(issue_id,label_protocol_version)
);

CREATE FUNCTION dss_reference.guard_forecast_issue() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE scheduled timestamptz; target date; has_missed boolean;
BEGIN
    SELECT scheduled_at,target_month INTO scheduled,target
    FROM dss_reference.forecast_slot WHERE slot_id=NEW.slot_id FOR SHARE;
    IF target IS NULL OR NEW.input_month<>(target - interval '2 months')::date THEN
        RAISE EXCEPTION 'Issue input month does not match slot' USING ERRCODE='23514';
    END IF;
    NEW.issued_at:=clock_timestamp();
    IF NEW.issued_at<scheduled THEN
        RAISE EXCEPTION 'Cannot issue before scheduled time' USING ERRCODE='23514';
    END IF;
    SELECT EXISTS(SELECT 1 FROM dss_reference.forecast_slot_event
        WHERE slot_id=NEW.slot_id AND event_type='MISSED') INTO has_missed;
    NEW.issue_status:=CASE WHEN has_missed OR NEW.issued_at>=scheduled+interval '1 hour'
        THEN 'LATE' ELSE 'ON_TIME' END;
    RETURN NEW;
END $$;
CREATE TRIGGER forecast_issue_guard BEFORE INSERT ON dss_reference.forecast_issue
FOR EACH ROW EXECUTE FUNCTION dss_reference.guard_forecast_issue();

CREATE FUNCTION dss_reference.stamp_forecast_event() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    NEW.detected_at:=clock_timestamp();
    RETURN NEW;
END $$;
CREATE TRIGGER forecast_event_stamp BEFORE INSERT ON dss_reference.forecast_slot_event
FOR EACH ROW EXECUTE FUNCTION dss_reference.stamp_forecast_event();

CREATE FUNCTION dss_reference.guard_forecast_score() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE prediction float8;
BEGIN
    SELECT predicted_ec_mS_m INTO prediction FROM dss_reference.forecast_issue WHERE issue_id=NEW.issue_id;
    IF prediction IS NULL OR abs(NEW.abs_error_mS_m-abs(NEW.observed_ec_mS_m-prediction))>1e-8 THEN
        RAISE EXCEPTION 'Forecast score does not match immutable issue' USING ERRCODE='23514';
    END IF;
    NEW.scored_at:=clock_timestamp();
    RETURN NEW;
END $$;
CREATE TRIGGER forecast_score_guard BEFORE INSERT ON dss_reference.forecast_score
FOR EACH ROW EXECUTE FUNCTION dss_reference.guard_forecast_score();

CREATE FUNCTION dss_reference.reject_forecast_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'Forecast ledger is append-only' USING ERRCODE='42501';
END $$;
CREATE TRIGGER forecast_slot_immutable BEFORE UPDATE OR DELETE ON dss_reference.forecast_slot FOR EACH ROW EXECUTE FUNCTION dss_reference.reject_forecast_mutation();
CREATE TRIGGER forecast_event_immutable BEFORE UPDATE OR DELETE ON dss_reference.forecast_slot_event FOR EACH ROW EXECUTE FUNCTION dss_reference.reject_forecast_mutation();
CREATE TRIGGER forecast_issue_immutable BEFORE UPDATE OR DELETE ON dss_reference.forecast_issue FOR EACH ROW EXECUTE FUNCTION dss_reference.reject_forecast_mutation();
CREATE TRIGGER forecast_score_immutable BEFORE UPDATE OR DELETE ON dss_reference.forecast_score FOR EACH ROW EXECUTE FUNCTION dss_reference.reject_forecast_mutation();

CREATE INDEX forecast_slot_month_idx ON dss_reference.forecast_slot(target_month,station_key);
CREATE INDEX forecast_score_issue_idx ON dss_reference.forecast_score(issue_id);

COMMENT ON TABLE dss_reference.forecast_slot IS 'One immutable slot per station, target month and schedule. Schedule MONTHLY_D06_PREV: 09:00 on day 06 of previous month, Asia/Ho_Chi_Minh.';
COMMENT ON TABLE dss_reference.forecast_slot_event IS 'Append-only missed slot evidence. detected_at is always the real database insertion time.';
COMMENT ON TABLE dss_reference.forecast_issue IS 'Immutable blind issue; at most one per slot. On-time window is 09:00–10:00 local on schedule day; any earlier missed event forces LATE.';
COMMENT ON TABLE dss_reference.forecast_score IS 'One score per issue and preregistered label protocol version; ON_TIME and LATE are reported separately.';

CREATE OR REPLACE FUNCTION webgis_security.audit_dss_insert() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    INSERT INTO webgis_security.audit_log(database_actor,application_actor,table_name,action,record_id)
    VALUES (session_user,coalesce(nullif(current_setting('webgis.actor',true),''),'SYSTEM'),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,TG_OP,
        coalesce(to_jsonb(NEW)->>'draft_id',to_jsonb(NEW)->>'prediction_id',
                 to_jsonb(NEW)->>'event_id',to_jsonb(NEW)->>'score_id',
                 to_jsonb(NEW)->>'issue_id',to_jsonb(NEW)->>'slot_id'));
    RETURN NEW;
END;
$$;
CREATE TRIGGER audit_forecast_slot AFTER INSERT ON dss_reference.forecast_slot
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();
CREATE TRIGGER audit_forecast_event AFTER INSERT ON dss_reference.forecast_slot_event
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();
CREATE TRIGGER audit_forecast_issue AFTER INSERT ON dss_reference.forecast_issue
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();
CREATE TRIGGER audit_forecast_score AFTER INSERT ON dss_reference.forecast_score
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();

GRANT SELECT ON dss_reference.forecast_slot,dss_reference.forecast_slot_event,
    dss_reference.forecast_issue,dss_reference.forecast_score TO webgis_reader;
GRANT SELECT,INSERT ON dss_reference.forecast_slot,dss_reference.forecast_slot_event,
    dss_reference.forecast_issue,dss_reference.forecast_score TO webgis_writer;
GRANT USAGE ON SEQUENCE dss_reference.forecast_score_score_id_seq TO webgis_writer;
