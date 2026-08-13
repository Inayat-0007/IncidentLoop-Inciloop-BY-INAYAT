---
name: add-migration
description: Change local SQLite/JSON memory schema. Use when editing DATA_MODEL or memory/store.py.
---

# Add memory schema change

1. Update `docs/DATA_MODEL.md`.
2. Change `backend/memory/store.py` `CREATE TABLE IF NOT EXISTS` (expand/contract; do not drop user data in place).
3. Do not add Postgres/Prisma without an ADR.
