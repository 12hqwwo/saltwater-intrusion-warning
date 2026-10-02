# 01. Data Audit

Audit date: 2026-10-03. Scope: repository files, SQL definitions, ETL, CSV/XLSX/NetCDF/GeoJSON, and the two MRC licence/receipt PDFs. The live PostgreSQL/PostGIS instance was not queried because no database connection was available; database conclusions below are therefore schema-contract checks, not proof of a deployed migration.

`null_count` below counts the primary measurement/location field, not every optional metadata cell.

| dataset | time_range | frequency | row_count | null_count | source | unit | status |
|---|---|---:|---:|---:|---|---|---|
| EC Tân Châu raw | 1985-05-15 to 2023-12-15 | monthly | 464 | 0 | MRC WRUP VN_019803; snapshot 2026-08-31 | mS/m | Source grade `Unverified data`; raw preserved |
| EC Mỹ Tho raw | 1985-06-26 to 2023-12-15 | monthly | 463 | 0 | MRC WRUP VN_019805; snapshot 2026-08-31 | mS/m | Source grade `Unverified data`; raw preserved |
| EC QA/clean | 1985-05-15 to 2023-12-15 | monthly | 927 | 0 original / 0 clean | Derived from the two MRC snapshots | mS/m | 810 VERIFIED; 117 SUSPECT; 0 REJECTED; 0 MISSING |
| Open-Meteo canonical daily | 1985-01-01 to 2026-08-31 | daily | 30,436 | 0 | Open-Meteo ERA5-Land | mixed | 15,218 rows per location; no duplicate station/date keys |
| DAHITI Tân Châu raw | 2002-06-13 to 2016-05-07 | irregular | 108 | 0 water level | DAHITI id 627; snapshot 2026-09-12 20:14 | m | Optional; 108 observed months; no fill |
| DAHITI Mỹ Tho raw | 2008-07-17 to 2026-08-06 | irregular | 621 | 0 water level | DAHITI id 3316; snapshot 2026-09-12 20:14 | m | Optional; 218 observed months; no fill |
| GloFAS Tân Châu raw grid | 1985-01-02 to 2024-01-01 | daily | 14,244 timestamps in 117 NetCDF files | 0 at selected nearest cell | Copernicus GloFAS ERA5 v4 | m³/s | 469 feature months; grid cell marked SUSPECT until upstream area is verified |
| GloFAS Mỹ Tho daily | 1985-01-01 to 2026-08-31 | daily | 15,218 | 15,218 | Copernicus GloFAS requested source | m³/s | MISSING: no validated main-river cell; Tân Châu was not copied |
| GloFAS Mỹ Tho monthly | 1985-01 to 2026-08 | monthly | 500 | 500 | Copernicus GloFAS requested source | m³/s | MISSING for the same reason |
| UHSLC Vũng Tàu | 1985-11-29 to 2026-07-31 | daily maximum | 14,855 | 0 | UHSLC station 142 | m | Auxiliary observed coastal series; not used as FES2022b replacement |
| FES2022b tide boundary | not available | required hourly | 0 | all | FES2022b + PyFES | m | BLOCKED: model files, three verified offshore points, and datum metadata are absent |
| Gate master | static snapshot 2026-10-02 | static | 3,569 | 3,547 primary coordinates | Compiled gate master with row-level sources | EPSG:4326 | 12 OFFICIAL; 10 VERIFIED_MAP_PIN; 2 CANDIDATE; 3,545 UNKNOWN; 22 WebGIS-ready |
| Monthly feature v2 | 1985-01 to 2026-08 | monthly | 1,000 | EC 190; discharge 531; tide 1,000; DAHITI 674 | QA-controlled joins | mixed | Grain valid: 500 months × 2 locations; no duplicate key |
| Model comparison | test window 2022-01 to 2023-12 | monthly | 6 | 0 metric cells | Seasonal Naive / SARIMA / Random Forest | mS/m | All three ran; common evaluation months used per station |

## EC QA results

| station | VERIFIED | SUSPECT | REJECTED | MISSING |
|---|---:|---:|---:|---:|
| Tân Châu | 445 | 19 | 0 | 0 |
| Mỹ Tho | 365 | 98 | 0 | 0 |

No raw value was overwritten. Statistical extremes and abrupt changes are retained as `SUSPECT`; they are excluded from training by default. The former implementation incorrectly loaded the Tân Châu file for both stations because square brackets in a glob pattern were interpreted as a character class. It produced 928 QA rows, mislabeled 464 Tân Châu rows as Mỹ Tho, and made the two EC feature series identical. The corrected output has the expected 927 source rows and distinct station series.

The value 841 mS/m at Mỹ Tho is not automatically converted or rejected. The source explicitly labels the unit mS/m; without calibration metadata, a unit conversion would be invented. It is retained as `SUSPECT` with outlier/jump reasons.

## Review of the 11-table database contract

The 11 names come from `sql/checks/01_erd_query.sql`. The live existence, row counts, constraints, and deployed versions remain unverified.

| table | decision | required action |
|---|---|---|
| `data_source` | keep | Ensure source URL/licence and current snapshot/version are recorded. |
| `admin_boundary` | keep | No change needed for this pipeline. |
| `salinity_station` | keep as legacy compatibility | Prefer `measurement_site` for new EC/hydrology locations; do not delete without an application migration. |
| `irrigation_gate` | keep | Keep gate identity here; store alternative/candidate coordinates in `gate_coordinate_source`. |
| `salinity_observation` | keep as legacy | Do not load conductivity into a salinity field without a validated conversion. |
| `water_level_observation` | keep | Use for observed water levels; do not overload it with model tide/discharge products. |
| `analysis_area` | keep | No change needed. |
| `measurement_site` | keep | Reuse as the core location catalogue where applicable. |
| `source_dataset` | keep and strengthen metadata | Require immutable snapshot/version and licence/provenance. |
| `conductivity_observation` | modify | Preserve original value and attach QA flag/reason; only VERIFIED observations train models. |
| `monthly_feature` | rebuild | Enforce unique `(location_id, year_month)`, QA-controlled target eligibility, and future-only rows after 2023-12. |

The repository also contains `backend/schema.sql`, a separate four-table legacy prototype (`Station`, `WaterLevel`, `Salinity`, `Weather`). It is not equivalent to the 11-table contract and must not be treated as proof of the production schema.

## Required migration review

`sql/migrations/11_schema_migration.sql` now defines the six requested tables: `tide_point`, `tide_prediction`, `hydro_point`, `discharge_observation`, `data_quality_flag`, and `gate_coordinate_source`. It includes PostGIS geometry, snapshot/version/source fields, QA foreign keys, and a constraint preventing CANDIDATE/UNKNOWN gate coordinates from becoming primary. The migration has been syntax-reviewed only; it has not been applied to PostgreSQL.

## Major defects found in the previous outputs

1. Both EC station outputs came from VN_019803.
2. The same Tân Châu GloFAS monthly series was joined to both locations.
3. Open-Meteo values were aggregated from duplicate copies, multiplying rainfall.
4. UHSLC Vũng Tàu was presented as a replacement for the required FES2022b boundary product.
5. SARIMA failed and still appeared in the comparison table with zero test rows.
6. Random Forest scores for the two stations were based on duplicated EC targets.
7. Gate QA covered only 15 rows although the master workbook contains 3,569 records.
8. The migration created six different tables from the six named in the requirement.
9. Audit reports overstated EC row counts by one and claimed an unproven unit error.
10. MRC licensing requires non-commercial use, acknowledgement, and prior permission before redistributing supplied/derived data to third parties.

## Spatial and gate-operation guardrails

No official IDW raster is generated from two EC stations. Synthetic demo locations remain archived and are not used by the v2 feature/model pipeline. No model output directly controls a gate; the repository's rule/approval work remains separate from forecast generation.
