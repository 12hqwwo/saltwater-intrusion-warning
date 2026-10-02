# Data-contract rules

## Electrical Conductivity is the target

Canonical target:
- field: `conductivity_ms_per_m` in PostgreSQL
- file field: `conductivity_mS_per_m`
- unit: `mS/m`

Do not create:
- `salinity_lag_1`
- `/salinity/history`
- `SalinityRecord`
- fixed `EC * 0.64` conversions in the active pipeline

Use:
- `ec_lag_1`
- `/ec/history`
- `ConductivityRecord`

## Temporal resolution

MRC target observations are mostly monthly.
Therefore:
- model evaluation must remain monthly for Release 1;
- do not evaluate daily 3–10 day EC forecasts from upsampled monthly labels;
- `data/processed/ml_features_dataset.csv` must be treated as legacy/prototype until its
  daily target-generation provenance is proven.

## Provenance

Every imported dataset should preserve:
- original filename
- source
- source row count
- SHA-256
- unit
- temporal resolution
- spatial reference / site
- import timestamp
- transformation notes

## MRC threshold reference

For the Academic MVP at Mỹ Tho:
- NORMAL `< 150 mS/m`
- WATCH `150 <= EC < 620 mS/m`
- SEVERE `>= 620 mS/m`

These are reference thresholds for risk visualization, not automatic gate-operation rules.

## DAHITI

DAHITI is irregular satellite-altimetry water level.
Do not:
- describe it as tide;
- use it to select intra-day gate opening windows;
- invent missing vertical datum.

## GloFAS

The existing bbox mean is technical debt.
Before model use:
- locate nearest valid river grid / mapped reach to Tân Châu;
- store selected grid coordinate;
- store extraction method;
- verify variable and units;
- preserve missing periods instead of fabricating discharge.

## Leakage

Features for predicting month `t` may only use information available at or before the
forecast issue time. Never use future monthly values while constructing lags, rolling
features, normalization, imputation, or train/test preprocessing.
