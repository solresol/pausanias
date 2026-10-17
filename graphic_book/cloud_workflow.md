# Graphic-book SQLite exchange

The full PostgreSQL corpus and illustration catalogue are exported into
`s3://pausanias-graphic-book-assets-849621205733/workflow/corpus.sqlite`.
The local working file is `graphic_book/workflow/corpus.sqlite` (ignored by Git).
The root `pausanias.sqlite` is a legacy file and must never be used.

The daily image automation runs at noon Australia/Sydney. Raksasa's website
cron runs at 05:15 Australia/Sydney. It imports completed results and refreshes
the export immediately before building the site. The automation can run on a
local or managed cloud computer with Python 3.11+, `uv`, AWS credentials, and
S3/GitHub/image-generation access. Linux renderers need DejaVu or Liberation
serif fonts. Explicit font overrides are documented in `graphic_book_fonts.py`.

## Ownership and persistence

`graphic_book_exchange.py` uses the AWS SDK and **conditional PutObject**:
`If-None-Match: *` for bootstrap and `If-Match` against the downloaded ETag for
every later write. An `active_worker` row identifies the owner and expiring
lease. Only a successful claim authorizes work. Two readers of the same idle
database cannot both claim it. A failed precondition ends the session; never
retry its stale database with a new ETag.

Claims last six hours for image generation and one hour for raksasa. Renew
before expiry for longer work. An expired claim can be taken over conditionally;
the old worker cannot publish over its successor. `metadata.generation` changes
on every update. SQLite handles are closed before single-file uploads; WAL
sidecar files are not part of the exchange.

Results and their files use immutable `workflow/results/<result-id>/` keys.
They become visible through a successful conditional database update. A rejected
upload can leave unreferenced files, which are safe to retain for recovery.
New pages and replacements are checkpointed separately. Failure of an optional
replacement must preserve the checkpointed new page.

The database contains `passages`, `translations`, `illustrations`, `runs`,
`active_worker`, `results`, and `result_files`, with typed columns and checksums.
Corpus edits always originate in PostgreSQL. Raksasa imports only result records
and their file metadata; it never copies SQLite translations back to PostgreSQL.
`graphic_book_results`, `graphic_book_result_files`, and `graphic_book_pages`
record accepted/rejected results and the current page catalogue in PostgreSQL.
Result IDs make imports idempotent. Source-text changes and changed originals
reject obsolete candidates while retaining the previous accepted page.

## Daily generation

Follow all art, text-fit, composition, semantic, suitability, and review gates in
`graphic_book/README.md`. This document replaces that file's older direct
SSH/combined-backup instructions for exchange-based runs.

1. Claim the latest export:

   ```sh
   uv run graphic_book_exchange.py begin
   uv run graphic_book_exchange.py hydrate
   uv run graphic_book_exchange.py next
   ```

   If `begin` reports an active worker, **stop immediately**. Its exit status is
   3. No art generation, source commits, or old backup commands are authorized
   by an unsuccessful claim. A successful command prints the run ID and next
   passage in numeric order. Inspect the exported translation with
   `graphic_book_corpus.load_translation(passage_id)`, preserving its exact text.
   `hydrate` verifies all accepted pages needed for references and PDF checks,
   and retrieves component/archived images recorded by exchange results.
   Source renderers/plans are available from Git; historical component art can
   be retrieved with `./sync_graphic_book_assets.sh pull` when needed.

2. Plan, generate, render, and review the new page. New renderers must use
   `graphic_book_corpus.load_translation()` or `snapshot_path()`, with no
   PostgreSQL connection and no legacy SQLite fallback. Source/component paths
   must be relative to the repository, and fonts must use `graphic_book_fonts`.
   Validate the whole local HTML/PDF with:

   ```sh
   uv run build_graphic_book.py --image-dir graphic_book/images --output-dir pausanias_site/graphic-book
   ```

3. Commit and push the scoped renderer, prompts, plan, and review text. Keep all
   binary images, the workflow database/session, generated site, and unrelated
   dirty files out of Git. Record the full commit SHA. Then checkpoint the result:

   ```sh
   uv run graphic_book_exchange.py record-result --passage 1.26.8 \
     --image graphic_book/images/1/26/8.png --source-commit <full-commit-sha> \
     --file graphic_book/render_passage_1_26_8.py \
     --file graphic_book/assets/generated/1_26_8/page_plan.md \
     --file graphic_book/assets/generated/1_26_8/main.prompt.txt \
     --file graphic_book/assets/generated/1_26_8/main.png
   ```

   Replace the example paths with the actual passage and pass `--file` for
   **every** new source, prompt, review, and component image. The command reads
   the uploaded objects back and verifies their hashes before checkpointing.
   It accepts exactly one new page and at most one replacement per run. A new
   page must be the earliest translated passage absent from the catalogue.

4. Run `uv run graphic_book_exchange.py replacement-decision` once the new page
   is checkpointed. Repeated calls reuse the same random draw. Follow the
   existing 20% replacement procedure. Persist a selected target using
   `replacement-decision --passage <id> --outcome pending`; it cannot be changed
   later in the run. Record skipped/no-candidate/rejected outcomes with
   `--outcome`. Inspect the original PNG and neighbouring pages, preserve old
   component art and source, and complete all replacement review gates before
   checkpointing it with `record-result --kind replacement --original-sha256
   <catalogued-original-hash> ...`. The command independently retrieves and
   archives the original PNG under the immutable result directory, verifies it,
   and adds its checksum/path to `result_files`. Raksasa independently checks
   the original checksum again before accepting a replacement.

5. Run `uv run graphic_book_exchange.py finish --notes '<outcome>'` to publish
   the finished state with an empty active-worker table. If a later step fails,
   use `abort --notes '<failure>'` to release your claim while preserving already
   checkpointed results. Never upload the database using another tool. After
   expiry or a conditional-write failure, stop; do not clear another worker's
   claim. For long runs use `uv run graphic_book_exchange.py renew` well before
   the six-hour lease expires.

Report the passage, checks, source commit/push, result ID, S3 verification,
replacement draw/outcome, and claim-release result. Raksasa import and website
publication happen on the next overnight run; do not report them as completed
from a daytime upload.

## Raksasa

The service user uses the dedicated `pausanias-graphic-book` AWS profile in
`~/.aws/credentials.pausanias-exchange`. Cron
calls `sync` after translation/tagging work and before the website build. To
perform the same bounded exchange operation manually:

```sh
AWS_PROFILE=pausanias-graphic-book \
  AWS_SHARED_CREDENTIALS_FILE=/home/pausanias/.aws/credentials.pausanias-exchange \
  uv run graphic_book_exchange.py sync \
  --image-dir /home/pausanias/pausanias-graphic-book/images
```

An active cloud worker skips exchange work and leaves existing accepted pages
available for the normal build. Other failures fail the cron run and appear in
cron mail. Accepted page metadata commits to PostgreSQL before materialization;
a failed download is safely retried from PostgreSQL's current page catalogue.
The existing S3 `images/` mirror is maintained for compatibility. Initial seeding
registers existing pages with unknown text provenance rather than falsely
attributing them to a current translation.

Inspect remote state without overwriting an active local checkout:

```sh
uv run graphic_book_exchange.py status
```

For isolated tests use `--s3-uri s3://<bucket>/<test-prefix>` and a separate
`--snapshot` path before the subcommand. Both snapshot and artifact keys then
stay within that prefix. No DynamoDB table is required.
