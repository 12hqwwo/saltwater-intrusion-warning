# GIS and PostGIS rules

## CRS

Project GIS default: EPSG:4326 / WGS84 unless the source states otherwise.

Always preserve source CRS metadata and transform explicitly when needed.

## Stations

Grounded KML coordinates:
- Tân Châu: 105.2480164 E, 10.80062008 N
- Mỹ Tho: 106.3529997 E, 10.35912163 N

A station and an irrigation gate are different physical objects. Never reuse station
coordinates as gate coordinates.

## Administrative boundaries

Current migration target:
- 1 Đồng Tháp province boundary
- 102 commune/ward boundaries
- effective date: 2025-07-01
- geometry: valid `MultiPolygon`, SRID 4326

`sql/03_admin_boundary_dong_thap.py` must run in preview mode first. `--commit` is a
separate explicit step.

## Irrigation gates

`data/raw/gate/sluice_gates_dong_thap_new.csv` has 15 inventory rows.
`data/raw/gate/sluice_gates_dong_thap_new.geojson` has 12 spatial features.

Three pending gates have no trusted coordinate. Do not use a project centroid as a fake
geometry. Fix the schema or keep pending records outside the spatial table until location
can be represented honestly.

Current `sql/02_irrigation_gate_dong_thap.sql` contains a known placeholder-centroid
approach and must not be treated as final.

## Geometry checks

For imported GIS layers verify:
- `ST_IsValid(geom)`
- `ST_IsEmpty(geom) = false`
- expected `ST_SRID`
- expected geometry type
- feature count
- spatial sanity in QGIS
