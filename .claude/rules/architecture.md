# Architecture rules

## Actual architecture first

Always distinguish `implemented` from `target design`.

Implemented / present in this snapshot:
- Python data collection and processing.
- CSV/NetCDF/KML/GeoJSON raw data.
- PostgreSQL 17 + PostGIS migrations.
- ETL loader in `etl/etl_csv.py`.
- Vite/OpenLayers dependency scaffold in `frontend/`.
- SQL checks and database-test bootstrap.

Target design described in the UI/UX document:
- React + Vite + TypeScript + OpenLayers.
- FastAPI modular monolith.
- PostgreSQL/PostGIS.
- ML engine and decision-support layer.

Do not claim target components are already implemented.

## Data layers

Preferred direction:

```text
data/raw
  -> data/interim
  -> data/processed
  -> PostgreSQL/PostGIS
  -> model-ready dataset
  -> model outputs
  -> API
  -> WebGIS
```

Raw data is immutable evidence. Transformations must be reproducible.

## Database ownership

New EC work belongs to:
- `source_dataset`
- `measurement_site`
- `conductivity_observation`
- `monthly_feature`

Legacy salinity tables remain only for migration compatibility unless a specific task
requires them.

## Backend

If backend implementation starts, create a deliberate FastAPI source tree instead of
relying on the existing `.pyc`.

Recommended future structure:

```text
src/backend/
  app/
    main.py
    api/
    db/
    models/
    services/
```

Do not create operational gate-control endpoints until approved data/rules exist.

## Frontend

Current `frontend/package.json` is not evidence of a complete UI.
Before frontend work, decide whether to migrate to the target React/TypeScript stack or
keep the existing Vite/OpenLayers/Bootstrap scaffold. Do not mix both silently.
