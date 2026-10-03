---
name: security-audit
description: Audit secrets, database commands, generated SQL and external-data handling in the TLCN project.
---

Check:
- `.env` and API keys;
- debug logging of secret fragments;
- SQL literal safety;
- dangerous DB targeting;
- destructive git/shell commands;
- downloaded external files and provenance;
- path traversal / arbitrary file writes;
- frontend exposure of credentials.

Report findings by severity and cite exact file/line locations.
