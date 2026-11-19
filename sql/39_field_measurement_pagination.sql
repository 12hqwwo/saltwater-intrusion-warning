-- Keyset pagination for the public map, review queue and "my measurements" list.
DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for field measurement pagination: %', current_database();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS field_measurement_submitted_page_idx
    ON dss_reference.field_measurement (submitted_at DESC, measurement_id DESC);

CREATE INDEX IF NOT EXISTS field_measurement_owner_page_idx
    ON dss_reference.field_measurement (submitted_by, submitted_at DESC, measurement_id DESC);
