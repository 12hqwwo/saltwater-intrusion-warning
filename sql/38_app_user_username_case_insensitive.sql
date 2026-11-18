DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for application users: %', current_database();
    END IF;
    IF EXISTS (
        SELECT 1 FROM webgis_security.app_user
        GROUP BY lower(username) HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Case-insensitive duplicate usernames exist in webgis_security.app_user.'
            USING HINT = 'Inspect SELECT lower(username), array_agg(username) FROM webgis_security.app_user GROUP BY lower(username) HAVING count(*) > 1;';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS app_user_username_lower_key ON webgis_security.app_user (lower(username));
