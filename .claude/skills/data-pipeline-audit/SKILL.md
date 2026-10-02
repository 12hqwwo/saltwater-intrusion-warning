---
name: data-pipeline-audit
description: Audit raw→interim→processed→PostgreSQL→model flow for units, leakage, missingness and provenance.
---

Start from source files, not from model output.

Required checks:
- row counts and date ranges;
- units;
- station/site identity;
- missingness;
- temporal aggregation;
- source hashes;
- duplicate handling;
- EC naming;
- GloFAS spatial extraction;
- DAHITI interpretation;
- monthly target resolution.

Do not silently impute missing values.
