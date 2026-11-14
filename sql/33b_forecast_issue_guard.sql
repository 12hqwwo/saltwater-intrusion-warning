-- Correct the issue trigger to read immutable slots without requiring UPDATE privilege.
DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for forecast issue guard: %', current_database();
    END IF;
END $$;

CREATE OR REPLACE FUNCTION dss_reference.guard_forecast_issue() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE scheduled timestamptz; target date; has_missed boolean;
BEGIN
    SELECT scheduled_at,target_month INTO scheduled,target
    FROM dss_reference.forecast_slot WHERE slot_id=NEW.slot_id;
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
