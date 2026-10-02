---
name: postgis-migration
description: Design and review safe PostgreSQL/PostGIS migrations for boundaries, stations and gates.
---

Every migration should:
- guard the database name;
- verify required tables/extensions;
- preserve source provenance;
- validate geometry and SRID;
- be idempotent or explicitly detect duplicates;
- provide preview/verification queries;
- default to rollback for risky data loads;
- require explicit commit.

Never fabricate geometry to satisfy a NOT NULL column.
