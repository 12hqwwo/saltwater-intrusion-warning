---
name: test-writer
description: Add focused tests for ETL, SQL contracts and monthly ML pipeline without altering raw evidence.
---

Prefer small deterministic fixtures under `tests/fixtures/` or `etl/tests/fixtures/`.
Do not make tests depend on a developer-specific D: path.
Keep DB tests separate from offline validation tests.
For time-series code, test chronology and leakage explicitly.
Never weaken an existing data constraint just to make a test pass.
