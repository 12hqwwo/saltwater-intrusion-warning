# External data layout

- `sources/` contains one canonical copy of each reusable source dataset and
  its normalized tables.
- `download_runs/` contains run-specific responses and provenance manifests.
  A run manifest may reference a canonical file through `canonical_path`;
  that file is intentionally not copied into every run directory.

`scripts/fetch_public_research_data.py` verifies pinned SHA-256 values before
reusing canonical Son Doc and Tan Chau files. Optional ERA5 responses remain in
the corresponding download-run directory because they are specific to that
request.
