# AGENTS.md

Follow the project guidance in `CLAUDE.md`.

## PostgreSQL JSON policy

Greg dislikes using PostgreSQL `JSON` or `JSONB` as an application-data escape
hatch. Do not add new JSON/JSONB columns, JSONB staging CTEs, or
`jsonb_to_recordset` write paths unless Greg explicitly approves that design.

Prefer normal relational tables with typed columns, foreign keys, and indexes.
For variable key/value data, use child tables or a typed raw-text column plus
explicit parsing/validation in Python. If you inherit an existing JSON/JSONB
path, prefer reducing it while you are nearby instead of copying the pattern.
