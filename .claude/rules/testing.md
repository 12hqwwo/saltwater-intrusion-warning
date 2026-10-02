# Testing rules

## Python ETL

Primary offline test command:

```powershell
python -m unittest discover -s etl/tests -v
```

The current snapshot has a fixture-path mismatch:
`etl/tests/test_validation.py` expects:
- `mrc_mytho.csv`
- `mrc_tanchau.csv`
- `master_timeseries.csv`

while the repo stores differently named MRC raw files and the master under
`data/processed/`.

Do not mark ETL logic broken solely from `FileNotFoundError`; first repair the test fixture
contract or point `WEBGIS_TEST_DATA_DIR` to a controlled fixture directory with those
names.

## Database changes

Never use the main database for destructive tests.

For schema/ETL tests:
- use `dongthap_gis_etl_test`;
- use transactions;
- test idempotence;
- intentionally test rollback;
- verify counts and hashes.

For `dongthap_gis`:
- backup before material data changes;
- preview first;
- verify;
- then commit.

## Model evaluation

Use chronological validation, never random shuffle for the primary time-series result.

Minimum comparison:
- naive persistence baseline
- Random Forest
- SARIMAX

Report at least:
- MAE
- RMSE
- train/test periods
- sample count
- feature set
- missing-data policy

Prefer rolling-origin / time-series split once the first baseline works.

## Regression tests to add

Before Release 1 freeze, add tests for:
- EC unit remains `mS/m`;
- no fixed EC-to-salinity conversion in active pipeline;
- no daily target is synthesized from monthly EC;
- GloFAS extractor selects a recorded point/reach, not bbox mean;
- pending gates do not receive fake coordinates.
