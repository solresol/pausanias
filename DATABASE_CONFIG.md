# Production database configuration

Observed on Raksasa on 2 November 2026. **Production remains PostgreSQL16/5432.**
This preparation branch stages PG18 routing and quieter cron output; it does not
claim a production cutover, writer pause, cloud-result import or publication.

| Item | Current production |
| --- | --- |
| Checkout | `/home/pausanias/pausanias` |
| OS/database role | `pausanias` |
| Database | `pausanias` |
| Unix socket / port / major | `/var/run/postgresql` / `5432` / `16` |
| Shared Python resolver | `pausanias_db.py`: `get_database_url()` and `connect()` |
| Cron | `crontab -u pausanias -l`: daily `15 5 * * *` Australia/Sydney |
| Daily wrapper | `/home/pausanias/pausanias/cronscript.sh` and its four daily sub-wrappers |
| Monthly reader | `27 6 1 * *`, `manto_release_check.py --database-url "dbname=pausanias" --fail-on-newer` |
| Authentication | Existing same-host peer; no password needed by the cron role |
| `.pgpass` / `.pg_service.conf` | Absent under `/home/pausanias` at inspection; unused by this peer route |

The installed wrapper exports `PAUSANIAS_DATABASE_URL`, default `dbname=pausanias`.
No endpoint overrides were found in its cron, service-account nonlogin environment,
`.profile`, `.bashrc` or `/etc/environment` during the scoped audit. Explicit manual
DSNs remain caller-controlled; old documentation mentions user `gregb`, which is
not the observed production cron identity.

## Prepared PG18 profile and guard

The planned non-secret profile is `/home/pausanias/.config/pausanias/database.conf`,
owned by `pausanias`, mode600, in a private directory. **It is not installed yet.**
Its proposed contents are:

```text
DB_HOST=/var/run/postgresql
DB_PORT=5433
DB_NAME=pausanias
DB_USER=pausanias
DB_EXPECTED_SERVER_MAJOR=18
```

This branch resolves each connection field from explicit `--database-url`/
`PAUSANIAS_DATABASE_URL`/`DATABASE_URL` DSN fields, then corresponding `PG*`
environment fields, then the profile, then the legacy database-name default.
Thus a name-only daily-wrapper DSN inherits the profile's explicit socket/port/user.
`PAUSANIAS_DATABASE_CONFIG` can select a different profile; a missing explicitly
selected file fails closed. Unknown keys, including password entries, are rejected.
`PAUSANIAS_DATABASE_EXPECTED_MAJOR` supplies a deliberate major-version override
for isolated/admin checks. With a major configured, `connect()` verifies actual
database, role, socket, port and version before returning the connection for SQL.

Run production writers as the service account so they use its profile. Other users'
home directories and explicit DSNs are separate configuration contexts. The helper
`database_endpoint.py` prints only resolved connection identity, never credentials.
No global PGPORT, role, password, HBA or listener change is part of this preparation.

## Readers and external work

`wordspend` has SELECT on `public.passages` and `public.translations`, with no writes.
Its installed `scripts/import_pausanias.py` uses `PAUSANIAS_DATABASE_URL`, falling
back independently to `dbname=pausanias`; it does not use this project's profile.
Its daily pipeline calls that importer only when `IMPORT_PAUSANIAS=1`; the inspected
`35 4 * * *` Wordspend cron does not explicitly enable the flag. Coordinate this
manual/conditional reader before closing the old source. Do not move Wordspend's
own database as part of a Pausanias reader change.

The source explicitly records `wordspend CONNECT`, while the new isolated restore
has the default database ACL. Current effective CONNECT is equal through PUBLIC;
the named schema USAGE and both SELECT grants restored exactly. Wordspend is neither
owner nor superuser and has no inherited roles. Normal peer/zero-row SELECT probes
work on both versions without a new grant. The raw ACL difference is retained:
revoking PUBLIC CONNECT later would leave the source's direct Wordspend entitlement
intact, while the omitted-entry copy would lose connectivity. Preserving that future
revocation behavior needs the named entry; no grant was added by this preparation.

Graphic-book exchange uses the existing AWS profile `pausanias-graphic-book` and
`/home/pausanias/.aws/credentials.pausanias-exchange`; never store credential values
in Git. `graphic_book/cloud_workflow.md` governs claims, conditional S3 writes and
immutable result IDs. The cloud worker uses the exported SQLite corpus, not a live
PostgreSQL connection. Preserve original batch IDs/receipts and pending illustration
results across migration; do not regenerate, resubmit, clear leases or upload an old
local snapshot. MANTO import is a separate operation and is not authorized here.

## Backups, rehearsal and handover gates

Source and stale-candidate archives, checksums and isolated restore evidence are
under `/var/backups/postgresql/project-rehearsals-20261102T043400Z/`. The source
restore has84tables/30sequences; the stale candidate has81tables/30sequences and
lacks the three graphic-book exchange tables. Both original databases are intact.
Database-level ACL differences remain recorded separately from successful content,
schema, object-owner/ACL, sequence and application-reader comparisons.

Before production cutover: resolve that ACL decision; coordinate all writers; prove
a fresh final consistent copy; validate endpoints and generated outputs; preserve
the original PG16 database and stale PG18 candidate; verify a destination backup;
then observe an ordinary scheduled run. The staged wrapper's single-instance flock
provides a coordination point but does not fence independent database clients.
Permanent legacy closure needs scoped approval and a source/successor backup
retirement mapping; the installed retirement validator accepts at most one entry and
hardcodes canonical Stephanos. Pausanias therefore needs a reviewed bounded helper
extension preserving Stephanos as well as its own exact source/successor mapping.
After PG18 receives new writes, rollback requires reconciling data, sequence values,
batch receipts and graphic-book import records before changing routes.

## Prepared cron output behavior

The staged wrapper retains the schedule and existing Slack/failure reporting.
`cron_output.py` stores full step stdout/stderr in private per-run logs under
`/home/pausanias/.local/state/pausanias/pipeline/`, with mode600 files. Recognized
website notices/statistics stay in those logs; exact known completed/empty queue
lines are quiet in email. Unrecognized stdout remains visible even in website-
statistics mode. Zero failure/rejection counters cannot enable a diagnostic latch;
positive failures, rejected results, missing output and failure-limit messages remain
visible. Every stderr line and original nonzero/signal exit status is preserved.
No paid pipeline or test Slack transmission was run to validate this behavior.
