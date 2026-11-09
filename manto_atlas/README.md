# MANTO research atlas preview

An independently built static site for the local-culture and settlement-persistence
study. The exporter reads existing tables in a transaction marked READ ONLY; it
never initializes the schema, imports MANTO, retrains models or publishes files.
It uses no LLM/API calls, external JavaScript, fonts, map tiles or analytics.

## Build locally

```sh
uv run build_manto_atlas.py \
  --database-url 'host=/var/run/postgresql port=5433 dbname=pausanias user=gregb' \
  --release-record-id 22239985 \
  --output-dir tmp/manto-atlas-preview
```

Use the correct configured role for the execution account. The example is a
manual read-only run on Raksasa, not a proposed service-account grant. Never fall
back to retired PostgreSQL 16 or the legacy SQLite database. All generated data
stay in the ignored output directory. Open its `index.html` locally, or serve the
whole directory with a local web server. No live publication occurs.

## What is implemented

- Overview with source release, coverage and clear research-stage limitations.
- Geographic neighbours at 25/50/100 km and weighted figure-profile comparisons.
- Selected local-identity relation profiles, binary deduplication and asymmetric
  containment. Empty profiles remain unknown rather than maximally distinctive.
- Schematic geographic map and an experimental higher-level network aggregating
  nearby shared-figure pairs by MANTO name-label suffixes. These are not verified
  settlements or cultural communities.
- Searchable, paginated Pausanias claim register with temporal/status filters,
  Greek context, existing project translations, original passage links and
  explicit unreviewed candidate entity matches.
- Historical corrected model comparison, methods and GNN benchmark plan. No new
  outcome model or GNN is trained by this preview.
- Shareable query parameters, keyboard-operable graph nodes, mobile layout,
  escaped source text, a restrictive content-security policy and build hashes.

The full methodology is
`documentation/manto_local_culture_survival_plan_2026-11-09.md`. This preview is
not a substitute for its source-date, identity and endpoint-adjudication gates.

## Validation recorded 9 November 2026

The subsequent v3 refresh uses the validated isolated October import: 2,452
geographic entities, 1,498 mapped locations, 81,342 nearby pairs and 1,954
existing passage claims. All 63 focused MANTO/model tests and the five-view
desktop/mobile browser checks passed. It does not activate the public release
or carry forward older name-to-place links. See
`documentation/manto_v3_staged_import_2026-11-09.md` for the import receipt,
validation details and current limitations.

The earlier August preview was checked as follows:

- Built from the August release using current PG18 read-only queries: 2,450
  geographic entities, 1,954 passage claims and 77,896 within-100-km pairs.
- 39 focused tests passed across atlas, importer, connectedness, geography,
  survival predictor and website structure tests.
- Headless Chrome checked all five views at 1440px and 390px widths, map/network
  selections, radius changes, evidence search, empty results, pagination,
  status/scope filtering and refresh restoration. No page errors or mobile
  horizontal overflow. Desktop/mobile screenshots were visually reviewed locally.
- JavaScript syntax and Git whitespace checks passed.

## Remaining work before production

- The v3 archive and import integrity checks are complete. Audit chronology,
  settlement-only identities and human outcome labels; the current importer
  uses a provisional 180 CE cutoff.
- Implement direct source citations per narrative assertion; current figure
  scores are snapshot diagnostics, not independently witnessed findings.
- Replace suffix-based aggregation with reviewed regions and uncertainty-aware
  communities. Add travel and terrain alternatives when sourced.
- The current downloadable snapshot repeats passage text and stores pairwise
  comparisons, about 12 MB uncompressed. Deduplicate shared passages, consider
  bounded/lazy data chunks, precompress assets and test production caching before
  routine deployment. Generated snapshots must not be committed to Git.
- Provision and verify the separately authorized service account, least-privilege
  database access, restricted deployment key, Merah vhost, Cloudflare, cron and
  existing-channel Slack reporting. See the deployment proposal. No such changes
  have been made by the preview builder.
