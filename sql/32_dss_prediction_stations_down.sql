-- Valid only while no MyThuan prediction rows exist. Run through rollback script.
DO $$
BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Refusing DSS rollback outside dongthap_gis';
    END IF;
    IF EXISTS (
        SELECT 1 FROM dss_reference.multivariate_prediction_log
        WHERE station_key = 'MyThuan'
    ) THEN
        RAISE EXCEPTION 'Cannot roll back station constraints while MyThuan rows exist';
    END IF;
END $$;

ALTER TABLE dss_reference.multivariate_prediction_log
    DROP CONSTRAINT prediction_station_key_check,
    DROP CONSTRAINT prediction_station_site_check,
    ADD CONSTRAINT multivariate_prediction_log_station_key_check
        CHECK (station_key IN ('MyTho', 'TanChau')),
    ADD CONSTRAINT multivariate_prediction_log_check1
        CHECK ((station_key = 'MyTho' AND site_code = 'MRC_VN_019805')
            OR (station_key = 'TanChau' AND site_code = 'MRC_VN_019803'));
