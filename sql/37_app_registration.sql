DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for application registration: %', current_database();
    END IF;
END $$;

ALTER TABLE webgis_security.app_user
    ADD COLUMN registration_requested_at timestamptz,
    ADD COLUMN approved_by uuid REFERENCES webgis_security.app_user(user_id),
    ADD COLUMN approved_at timestamptz;

GRANT INSERT (user_id,username,display_name,password_hash,role,is_active,registration_requested_at)
    ON webgis_security.app_user TO webgis_writer;
GRANT UPDATE (is_active,approved_by,approved_at)
    ON webgis_security.app_user TO webgis_writer;
