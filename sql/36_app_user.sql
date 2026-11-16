DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for application users: %', current_database();
    END IF;
END $$;

CREATE TABLE webgis_security.app_user (
    user_id uuid PRIMARY KEY,
    username varchar(64) NOT NULL UNIQUE CHECK (username ~ '^[A-Za-z0-9._-]+$'),
    display_name varchar(120) NOT NULL CHECK (btrim(display_name) <> ''),
    password_hash text NOT NULL CHECK (password_hash ~ '^scrypt\$16384\$8\$1\$'),
    role text NOT NULL CHECK (role IN ('FIELD_STAFF','INSPECTOR')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

REVOKE ALL ON webgis_security.app_user FROM PUBLIC, webgis_reader;
GRANT USAGE ON SCHEMA webgis_security TO webgis_writer;
GRANT SELECT ON webgis_security.app_user TO webgis_writer;

CREATE FUNCTION webgis_security.prevent_self_field_review() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM dss_reference.field_measurement
               WHERE measurement_id=NEW.measurement_id AND submitted_by=NEW.reviewer) THEN
        RAISE EXCEPTION 'Reviewer cannot approve own field measurement' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER prevent_self_field_review BEFORE INSERT ON dss_reference.field_measurement_review
FOR EACH ROW EXECUTE FUNCTION webgis_security.prevent_self_field_review();
