# Production database configuration

Cut over on Raksasa at **22:38:07 UTC on 3 November 2026**, with the backup handoff
accepted at **00:47:20 UTC on 4 November**. Production uses **PostgreSQL 18/5433**;
the retained PG16 source is closed to connections. The next ordinary scheduled
application run remains an acceptance gate. Read-only reconciliation at 00:59 UTC
confirmed the current endpoint, healthy indexes/collation and preserved receipts.

| Item | Current production |
| --- | --- |
| Checkout | `/home/pausanias/pausanias` |
| OS/database role | `pausanias` |
| Database | `pausanias` |
| Unix socket / port / major | `/var/run/postgresql` / `5433` / `18` |
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

## Installed PG18 profile and guard

The installed non-secret profile is `/home/pausanias/.config/pausanias/database.conf`,
owned by `pausanias`, mode 0600, in a private directory. Its verified contents are:

```text
DB_HOST=/var/run/postgresql
DB_PORT=5433
DB_NAME=pausanias
DB_USER=pausanias
DB_EXPECTED_SERVER_MAJOR=18
```

The shared resolver resolves each connection field from explicit `--database-url`/
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
No global PGPORT, role, password, HBA or listener change was made for this cutover.

## Readers and external work

`wordspend` retains its existing SELECT on `public.passages` and `public.translations`.
The installed `scripts/import_pausanias.py` supplies an explicit Unix socket,
port 5433, database `pausanias`, role `wordspend` and expected major 18, then applies
any deliberately supplied `PAUSANIAS_DATABASE_URL` fields. It does not use this
project's profile or inherit an unrelated `PGPORT`. Its endpoint is checked and
its source transaction is read-only. The cutover probe passed without running an import.

Wordspend's own database remains **wordspend/5432/PG16**. Its daily pipeline calls
the Pausanias importer only when `IMPORT_PAUSANIAS=1`; the inspected cron does not
enable that flag. No Wordspend writer or schedule was changed.

The existing named `wordspend CONNECT` database right was explicitly approved and
reproduced on the fresh PG18 successor and its two verification copies, as owner
`pausanias`, with no grant option or new schema/table privilege. Exact normalized
source ACL parity was verified. Historical archives omitted database-level ACLs;
their original qualification is retained, with a checksummed metadata companion
and separately audited replay completing the recovery bundle. PUBLIC CONNECT alone
was not treated as equivalent to the source's named-right revocation semantics.

Graphic-book exchange uses the existing AWS profile `pausanias-graphic-book` and
`/home/pausanias/.aws/credentials.pausanias-exchange`; never store credential values
in Git. `graphic_book/cloud_workflow.md` governs claims, conditional S3 writes and
immutable result IDs. The cloud worker uses the exported SQLite corpus, not a live
PostgreSQL connection. Preserve original batch IDs/receipts and pending illustration
results across migration; do not regenerate, resubmit, clear leases or upload an old
local snapshot. MANTO import is a separate operation and is not authorized here.

## Backups, rehearsal and handover gates

Fresh source, preserved-candidate and independent destination archives, full
restores, checksums, metadata companion, grant audits and cutover evidence are under
`/var/backups/postgresql/pausanias-postcron-20261103T191000Z/`.
The final frozen proof compared all 84 tables, 30 sequence states and catalog/schema,
behind the approved source connection fence. The independently verified source
and destination rendered 8,998 files with identical bytes/hashes. Indexes are valid
and the PG18 collation version matches the operating system.

Canonical PG18 `pausanias` is OID 728836519. The previous stale PG18 OID 452938602 is
retained as `pausanias_stale_20261014_preserved_20261103`. Original PG16 `pausanias`
OID 452938602 is retained with `ALLOW_CONNECTIONS=false`; do not reopen it or route
writers there as an automatic rollback. The source and successor are in different
clusters, so their identities include port and system identifier as well as OID.
The original schedule and pipeline lock were restored/released after 220.492 seconds.

Independent post-cutover verification passed at 22:53 UTC. The coordinated backup
refresh completed at 00:08:55 UTC, and the scoped helper/policy installation completed
at 00:44:18 UTC. Final acceptance at 00:47:20 UTC verified both live retirement
mappings, the unchanged Stephanos entry, exclusions, retention and backup schedule.
The resulting encrypted offsite snapshot is
`1128b6299cfdfb309329cb3355f90de030d158d7edb7bd5f4b8c41301d30467c`.
Both successor archives were retrieved and checksum-verified. Four bounded native
sample restores passed; those sample restores omit ownership/ACL/tablespaces and
do not replace Pausanias's separate full 84-table restore and ACL replay proof.

Installed receipt: `backup-policy-installed.json` in the evidence directory above.
Final rollout record:
`/var/backups/postgresql/retirement-validation-pausanias-20261103T231233Z-6284c282/final-pausanias-backup-rollout.json`.
Historical completion records retain their then-pending backup status; later receipts
record the actual completion rather than rewriting those earlier observations.

Next ordinary run: **4 November 18:15 UTC** (5 November 05:15 Sydney). First observe
after **18:20 UTC**, then follow that same run to its natural terminal result. Require
committed changes on canonical PG18, successful publication and local/public output
hash parity, unchanged PG18 routing/PG16 fence and healthy indexes/collation.
The original 100-request and 2-request batch receipts are completed; illustration
results `ffe753e680ee49b88f3f9dbbbd1b44f9` and
`b93bb965e021496ea14b028a8fbd148e` are accepted, each with six file records and one
page reference. Preserve their receipt times and hashes; do not resubmit or reimport
them. New ordinary work or a legitimate active cloud lease must be reconciled by ID,
without overriding claims or replacing snapshots. Do not submit extra paid work to
manufacture acceptance.
After PG18 receives new writes, rollback requires reconciling data, sequence values,
batch receipts and graphic-book import records before changing routes.

## Installed cron output behavior

The database cutover retained the schedule and reporting behavior. A subsequent,
separate reporting change (`ae153fa`, refined by `90a6c19`) sends full numbered log
parts and the final status to Slack, disables daily cron email with `MAILTO=""`, and
runs `cron_slack_watchdog.sh` at `15 9-23 * * *` Sydney time. The monthly MANTO check
keeps its existing email destination. Current cron bytes therefore differ from the
cutover's restored crontab; the daily/monthly times are unchanged. See
[`docs/cron-slack.md`](docs/cron-slack.md). Verify delivery and the dated `.delivered`
marker at ordinary acceptance; no email alone is not proof of success. The first
watchdog check for this run is **4 November 22:15 UTC** (5 November 09:15 Sydney).

`cron_output.py` stores full step output in private per-run logs under
`/home/pausanias/.local/state/pausanias/pipeline/`, with mode 0600 files. Predictor,
network and site producers explicitly mark their routine reports with
`cron_reporting.routine_report()`. The wrapper's existing `--website-stats` opt-in
routes those reports directly to the same private log: model evaluation tables,
Greek coefficient rows and generation summaries need no content-matching filter.
Interactive commands retain their ordinary output. Unknown stdout and warnings
remain visible; exact known completed/empty queue lines are quiet in email.
Unavailable or unsafe routine-log destinations fall back to visible output with a
warning. Zero failure/rejection counters cannot enable a diagnostic latch;
positive failures, rejected results, missing output and failure-limit messages remain
visible. Every stderr line and original nonzero/signal exit status is preserved.
No paid pipeline or test Slack transmission was run to validate this behavior.
