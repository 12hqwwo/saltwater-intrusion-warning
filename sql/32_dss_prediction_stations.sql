-- Add My Thuan to the saved-prediction station/site contract; no row rewrites.
DO $$
BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Refusing DSS migration outside dongthap_gis';
    END IF;
END $$;

ALTER TABLE dss_reference.multivariate_prediction_log
    DROP CONSTRAINT multivariate_prediction_log_station_key_check,
    DROP CONSTRAINT multivariate_prediction_log_check1,
    ADD CONSTRAINT prediction_station_key_check
        CHECK (station_key IN ('MyTho', 'TanChau', 'MyThuan')),
    ADD CONSTRAINT prediction_station_site_check
        CHECK ((station_key = 'MyTho' AND site_code = 'MRC_VN_019805')
            OR (station_key = 'TanChau' AND site_code = 'MRC_VN_019803')
            OR (station_key = 'MyThuan' AND site_code = 'MRC_VN_019804'));
