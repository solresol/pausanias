# IMPROVEMENTS.md

*Analysis date: 2026-07-11*

Pausanias is a digital-humanities toolkit over the Greek text of the
*Description of Greece*: corpus import into PostgreSQL (live DB on raksasa),
LLM-based tagging/translation pipelines run nightly via `cronscript.sh` and the
OpenAI Batch API, statistical/network analyses (mythic vs. historical
classification, MANTO place-survival features, translation-length residuals,
stylometry), plus a generated static website and an experimental graphic book.
The project is active and well-governed — `TODO.md` is a genuine live research
agenda, `uv` is already the packaging story, and there is a real test suite —
so the recommendations below are mostly about finishing visible loose ends
before the July paper deadline rather than structural rework.

## Bugs & Fixes

- **Uncommitted graphic-book page 1.12.4.** `git status` shows
  `graphic_book/render_passage_1_12_4.py` and
  `graphic_book/assets/generated/1_12_4/` untracked, while 1.12.3, 1.12.5, and
  1.13.1 are all committed. Either commit 1.12.4 (matching the pattern of
  commits f0a2f1d/5d1743b/f2f631f) or delete it — an untracked page will
  silently miss the nightly `git pull` on raksasa.
- **Batch-ingestion monitoring is still an open gap.** TODO.md flags
  "Monitor daily batch fetch/submission so submitted discourse, people, and
  passage place-state runs do not sit un-ingested," and commit ec2e9be
  records a cron failure diagnosis. Add an explicit check to `cronscript.sh`
  (or a small `batch_health_check.py`) that alerts (email/exit-nonzero) when a
  submitted batch ID has no ingested rows after N hours, instead of relying on
  manual inspection.
- **LLM place links are a known noise source** (commit e5921f3: "LLM links are
  the noise source"). Before any paper claim uses MANTO features, make the
  link-method filter (`fe28131`) the default in `predict_place_survival.py`
  rather than an opt-in flag, so a future run can't accidentally include the
  noisy tier.

## Improvements

- **Consolidate the per-page graphic-book scripts.** There is now one
  `render_passage_X_Y_Z.py` per page. Factor the shared rendering logic into a
  module (alongside `graphic_book_asset_store.py`) and drive it from a data
  table (passage ref → layout/assets), so adding a page is a data change, not
  a new script. This will matter quickly if the book continues past Book 1.
- **`pausanias_db.py` is a good pattern — enforce it.** At 87 lines it is the
  right shared layer; grep for scripts still building their own `psycopg`
  connections or duplicating `--database-url` parsing and migrate them to
  `add_database_argument()`/`connect()`.
- **Retire the legacy sentence-tagging lane deliberately.** TODO.md keeps it
  "only as a background comparison path"; give it an end date or a written
  comparison result, otherwise it burns tokens indefinitely.
- **Ship the paper-facing loose ends first**: the compact interpretation
  write-up, the source-marker spot-check, and the Greta handout are the three
  unchecked items in "Current Paper-Facing Status" and they gate the July
  conversation more than any new feature does.

## Testing

- Coverage is decent for the book/markup/asset code (`tests/` has ~10 files),
  but the highest-risk code — the batch submission/ingestion scripts
  (`sentence_tag_batch.py`, `section_people_batch.py`,
  `passage_place_state_batch.py`) — appears untested. Add tests with a mocked
  OpenAI batch client covering: token-budget planning, resubmission of failed
  batches, and idempotent ingestion (re-fetching a batch must not duplicate
  rows).
- Add a schema smoke test: apply `database/schema.sql` to a scratch Postgres
  (or use `pytest-postgresql`) and assert `initialize_schema()` is idempotent.
  With ~60 `CREATE TABLE IF NOT EXISTS` statements, drift between schema.sql
  and what scripts actually expect is the likely failure mode.

## Documentation

- README.md still shows an SQLite-era tone in places; it says the importer
  reports "imported ... into PostgreSQL" but the Manual Stopwords section is
  the only place `PAUSANIAS_DATABASE_URL` appears. Add a short "Database
  setup" section mirroring CLAUDE.md's excellent connection-resolution notes
  (SSH tunnel to raksasa, env var precedence) so collaborators (Ben, Greta)
  can run read-only analyses.
- `documentation/` contains LaTeX build droppings (`.aux`, `.fdb_latexmk`,
  `.fls`, `.log`, `.nav`, `.out`, `.snm`). Add them to `.gitignore` and remove
  from the tree; keep only the `.tex` source and the `.pdf` if it is a
  deliverable.
- Answer the standing Ben question (Unicode plain-text corpus dump) in
  TODO.md — a one-evening `export_corpus.py` writing passage-ID-tagged UTF-8
  text would close it cheaply and keep the August handoff unblocked.

## Security

- No committed secrets spotted in a quick scan; connection strings use env
  vars / peer auth, which is right. Two hygiene items:
  - Confirm `transcripts/` (private call notes, referenced in TODO.md as
    "private ignored") really is gitignored — it is present in the working
    tree; verify nothing in it has ever been committed.
  - `cronscript.sh` runs `git pull` on raksasa before executing — that means
    anything merged to `main` executes unattended with DB and API-key access.
    Keep that in mind for branch discipline; consider pulling a pinned tag or
    at least logging the pulled SHA per run.

## Housekeeping / Modernization

- Packaging is already correct: `pyproject.toml` + `uv.lock`, no
  `requirements.txt`. No migration needed — keep using `uv add` and
  `uv run script.py`.
- `pausanias.sqlite` (legacy) and `migrate_sqlite_to_postgres.py` are dead
  weight per CLAUDE.md; move the sqlite file out of the repo root (or delete
  it — it's recoverable from git history) and archive the migration script.
- Remove `__pycache__/` from the repo root listing via `.gitignore` if not
  already covered; likewise `tmp/`.
- `notes.txt` at the root duplicates the role of TODO.md/documentation —
  fold anything still live into TODO.md and delete it.

## Quick Wins

1. Commit or discard the dangling 1.12.4 graphic-book page (5 minutes).
2. `.gitignore` + `git rm --cached` the LaTeX build artifacts in
   `documentation/` (5 minutes).
3. Add a batch-ingestion staleness check to `cronscript.sh` (the single
   highest operational-risk gap).
4. Write the corpus dump script for Ben and tick the handoff item.
5. Make the link-method filter default-on in the place-survival model.
