---
name: code-review
description: Review TLCN code changes against project architecture, EC data contracts, GIS safety and reproducibility.
---

Read changed files plus relevant rules before reviewing.

Check, in order:
1. scientific/data correctness;
2. temporal leakage;
3. EC terminology and units;
4. PostGIS/database safety;
5. reproducibility/provenance;
6. tests;
7. maintainability.

Use `references/checklist.md`.
If useful, run `scripts/check_project.py`.
Do not approve a change only because it executes successfully.
