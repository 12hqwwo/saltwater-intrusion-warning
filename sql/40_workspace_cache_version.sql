-- Transactional version marker for the PostgreSQL workspace cache.
DO $$ BEGIN
    IF current_database() <> 'dongthap_gis' THEN
        RAISE EXCEPTION 'Wrong database for workspace cache version: %', current_database();
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.workspace_cache_version (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    version bigint NOT NULL DEFAULT 1,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO public.workspace_cache_version(singleton) VALUES (true)
ON CONFLICT (singleton) DO NOTHING;
GRANT SELECT ON public.workspace_cache_version TO webgis_reader;

CREATE OR REPLACE FUNCTION public.bump_workspace_cache_version()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public AS $$
BEGIN
    UPDATE public.workspace_cache_version
       SET version = version + 1, updated_at = clock_timestamp()
     WHERE singleton = true;
    RETURN NULL;
END;
$$;

-- Statement triggers keep an ETL batch to one version change per statement.
-- The update rolls back with the import if any step fails.
CREATE TRIGGER workspace_dataset_changed
AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.source_dataset
FOR EACH STATEMENT EXECUTE FUNCTION public.bump_workspace_cache_version();
CREATE TRIGGER workspace_observation_changed
AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.conductivity_observation
FOR EACH STATEMENT EXECUTE FUNCTION public.bump_workspace_cache_version();
CREATE TRIGGER workspace_site_changed
AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.measurement_site
FOR EACH STATEMENT EXECUTE FUNCTION public.bump_workspace_cache_version();
CREATE TRIGGER workspace_source_changed
AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON public.data_source
FOR EACH STATEMENT EXECUTE FUNCTION public.bump_workspace_cache_version();
