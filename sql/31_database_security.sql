-- Installed atomically by setup_security.py, using the deployment administrator.
CREATE TABLE webgis_security.audit_log (
    audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    database_actor text NOT NULL,
    application_actor text NOT NULL,
    table_name text NOT NULL,
    action text NOT NULL CHECK (action = 'INSERT'),
    record_id text NOT NULL
);
CREATE FUNCTION webgis_security.audit_dss_insert() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    INSERT INTO webgis_security.audit_log(database_actor,application_actor,table_name,action,record_id)
    VALUES (session_user,coalesce(nullif(current_setting('webgis.actor',true),''),'SYSTEM'),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,TG_OP,
        coalesce(to_jsonb(NEW)->>'draft_id',to_jsonb(NEW)->>'prediction_id'));
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION webgis_security.audit_dss_insert() FROM PUBLIC;
CREATE TRIGGER audit_gate_draft AFTER INSERT ON dss_reference.gate_simulation_drafts
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();
CREATE TRIGGER audit_prediction AFTER INSERT ON dss_reference.multivariate_prediction_log
FOR EACH ROW EXECUTE FUNCTION webgis_security.audit_dss_insert();
COMMENT ON TABLE webgis_security.audit_log IS
 'DSS append audit: user identities and record identifiers only; no passwords or measurement payloads. Application roles cannot change this table.';
