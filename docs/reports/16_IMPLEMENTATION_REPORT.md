# 16. Implementation Report

Report date: 2026-10-03.

## 1. Đã làm gì

- Audited all repository source/data formats, including CSV, XLSX, NetCDF, GeoJSON, notebooks, SQL, and MRC licence PDFs.
- Reorganized raw, staging, processed, feature, model, pipeline, migration, and report files without changing raw file contents.
- Corrected station-safe EC loading and rebuilt QA outputs.
- Kept Mỹ Tho GloFAS explicitly NULL because no valid cell/upstream area is available.
- Rebuilt gate QA from the 3,569-row master workbook.
- Rebuilt monthly features without duplicated meteorology, without Tân Châu-to-Mỹ Tho discharge copying, and without UHSLC-as-FES substitution.
- Re-ran Seasonal Naive, SARIMA, and Random Forest on a time-based split and common evaluation months.
- Replaced the incorrect migration with the six requested schema objects.

## 2. Dataset trước/sau

| item | before | after |
|---|---:|---:|
| EC QA rows | 928 | 927 = 464 Tân Châu + 463 Mỹ Tho |
| Distinct EC station series | 1 mislabeled series duplicated | 2 source-validated series |
| Gate QA rows | 15 | 3,569 |
| WebGIS-ready gates | 12 | 22 |
| Monthly feature rows | 1,000 | 1,000 |
| Mỹ Tho months incorrectly carrying Tân Châu discharge | 469 | 0 |
| Tide months incorrectly carrying UHSLC proxy | 489 per location | 0; FES fields remain NULL |
| Model rows | 6, including two failed SARIMA rows | 6 successful runs |

## 3. Những lỗi tìm thấy

- Glob parsing selected VN_019803 for both EC stations.
- GloFAS Tân Châu was merged into Mỹ Tho.
- Five overlapping Open-Meteo files were concatenated before aggregation.
- UHSLC daily maxima were mislabeled as a FES tide boundary feature.
- SARIMA failed due to a pandas/statsmodels return-type mismatch.
- Parallel Random Forest workers were not reliable in the Windows sandbox.
- Candidate/unknown gate coverage and the 3,569-row master were omitted from QA.
- Migration table names did not match the requirement.
- The original audit/report claimed completion despite missing 04-06 outputs and failed SARIMA.

## 4. Những gì đã sửa

- Exact station-code validation now prevents cross-station EC loading.
- Raw values remain unchanged; QA flags/reasons are separate derived columns.
- Only VERIFIED EC becomes `ec_target`; SUSPECT records stay in the QA/clean file but do not train by default.
- The canonical all-stations Open-Meteo file is aggregated once.
- GloFAS is location-specific: Tân Châu is present with `SUSPECT` cell provenance; Mỹ Tho is NULL/MISSING.
- Tide features accept only FES2022-labelled input.
- DAHITI uses observed months only and exposes `dahiti_available`.
- Candidate gate coordinates stay in candidate columns and never become primary/WebGIS-ready.
- Model comparison uses identical evaluated months for all successful models at each station.

## 5. Những gì vẫn NULL và lý do

- All FES tide feature columns are NULL because FES2022b model files, datum, and verified offshore points are absent.
- All Mỹ Tho GloFAS values are NULL because no main-river grid cell with a verified upstream area is available.
- DAHITI is NULL outside true observation months; no zero-fill or long-gap forward-fill is used.
- EC is NULL in feature rows for SUSPECT records and for months without a source observation.

## 6. Kết quả QA EC

| station | VERIFIED | SUSPECT | REJECTED | MISSING |
|---|---:|---:|---:|---:|
| Tân Châu | 445 | 19 | 0 | 0 |
| Mỹ Tho | 365 | 98 | 0 | 0 |

Mỹ Tho's high values, including 841 mS/m, are retained as SUSPECT. No unsupported unit conversion was applied.

## 7. Tide point đã chọn

None. Selecting `TIDE_CUA_TIEU`, `TIDE_CUA_DAI`, and `TIDE_MIDDLE` without shoreline/bathymetry validation and FES datum/model metadata would create false provenance. Therefore `04_tide_points.geojson`, `05_tide_hourly.csv`, and `06_tide_monthly.csv` are intentionally not fabricated.

## 8. GloFAS cell Mỹ Tho đã chọn

None. The available Tân Châu grid covers approximately 10.725-10.875°N and 105.125-105.275°E, which does not cover Mỹ Tho. The Mỹ Tho daily/monthly outputs remain MISSING with grid coordinates and upstream area NULL.

## 9. Schema mới

The reviewed migration defines:

1. `data_quality_flag`
2. `tide_point`
3. `tide_prediction`
4. `hydro_point`
5. `discharge_observation`
6. `gate_coordinate_source`

It has not been executed against the live database. Operation tables were not added because the data conditions for steps 11-12 are not met by this run.

## 10. Kết quả baseline/SARIMA/Random Forest

| station | model | n_test | MAE | RMSE | accepted vs baseline |
|---|---|---:|---:|---:|---|
| Tân Châu | Seasonal Naive | 23 | 2.3117 | 3.1515 | baseline |
| Tân Châu | SARIMA | 23 | 1.8111 | 2.1748 | yes |
| Tân Châu | Random Forest | 23 | 1.8488 | 2.4616 | yes |
| Mỹ Tho | Seasonal Naive | 17 | 4.2759 | 5.6285 | baseline |
| Mỹ Tho | SARIMA | 17 | 3.2989 | 4.3584 | yes |
| Mỹ Tho | Random Forest | 17 | 3.4725 | 4.8042 | yes |

These are experimental station-level results. There is no official spatial raster, no gate-control output, and no universal exceedance metric because thresholds are gate/use-specific and require a validated EC-to-salinity decision rule.

## 11. Việc còn lại

1. Obtain licensed FES2022b model files, verify three offshore points and datum, then generate 04-06.
2. Download a Mỹ Tho GloFAS extent and validate main-channel position plus upstream area before generating non-NULL 07-08.
3. Confirm the Tân Châu GloFAS cell/upstream area; it is currently marked SUSPECT and excluded from model eligibility logic.
4. Connect to PostgreSQL/PostGIS, run the 11-table audit query, review FK types, and apply the migration in a transaction.
5. Obtain an independent EC review/calibration protocol before promoting SUSPECT observations.
6. Add more observed EC/salinity stations before any official river-network spatial interpolation.
7. Keep recommendations behind explicit rule evaluation and human approval.
