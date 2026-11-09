# MANTO v3 import and preview verification

Final verification: 9 November 2026, 11:55 UTC. The import is complete in an
isolated database schema. It is **not activated as the public site's default**.
The March and August production releases remain intact. The public default
selection remains the August release.

## Pinned source

- [MANTO data release, Zenodo record 23079055](https://zenodo.org/records/23079055).
- Version-specific DOI: [10.5281/zenodo.23079055](https://doi.org/10.5281/zenodo.23079055).
- Publication date: 1 October 2026. Zenodo still listed this as the latest record
  of concept 19446254 when checked again after the import.
- Archive: `publication-2616-20261001075526.zip`, exactly **517,649,184 bytes**.
- Published MD5: `f0cfc21122e9a700699c4a2a73533133`, verified against the download.
- Additional local SHA-256:
  `ee1739b3d4707b923fbbd2f9999aa096c0a16365f15413c3144f0395f8f309fa`.
- Licence: **CC BY-NC 4.0**. Credit the release creators: Greta Hawes, Ewan Shanks
  Coopey and R. Scott Smith. Retain attribution and identify derived work;
  commercial reuse requires a separate rights review.
- The public page calls this v3; the API's optional version field is empty.
  Reproducibility therefore uses the immutable record ID, DOI and checksums.

The complete source archive is retained locally. The existing relational
importer stores an index and selected fields, not every source cell verbatim.
The archive remains the authoritative copy for recovering full records.

## What was imported

These are actual database row counts, not attempted-upsert counters:

| Representation | Rows |
| --- | ---: |
| Release metadata | 1 |
| Raw-record index | 1,749,288 |
| Indexed entities, all kinds | 54,105 |
| Canonical entity details | 9,443 |
| Canonical tie details | 34,373 |
| Flattened indexed edges | 1,644,591 |
| Provisional Information-field status labels | 932 |

The raw index reconciles to **1,695,182 CSV rows plus 54,106 JSON records**.
All 22 JSON object exports match the independently counted rows of their
corresponding object CSVs. The remaining JSON record is publication metadata.
All per-file CSV counts match the archive. All seven staging foreign keys are
present and validated, and all staged rows belong to the pinned release.

The geographic prefix identifies **2,452 geographic entities**, not 2,452 cities.
The current importer's source flags divide its edges as follows:

| Existing filter result | Edges |
| --- | ---: |
| Provisionally pre-Pausanias | 250,037 |
| Pausanias source, excluded | 581,768 |
| Later or otherwise not pre-Pausanias | 371,950 |
| Source date unknown | 440,836 |

These flags retain the existing 180 CE cutoff and heuristic source-date parser.
They do not establish independent earlier witnesses. Edge counts are expanded
export representations, not counts of distinct stories, traditions or sources.

The provisional Information-field labels remain 873 `survives`, 9
`does_not_survive`, and 50 `exclude`. They are not adjudicated ground truth.

## Safety and reproducibility checks

1. Pinned the source record, licence, archive size and checksum before import;
   checked every ZIP member's CRC, paths, CSV row widths and required columns.
   The archive contains 336 entries and about 11.32 GB of uncompressed data.
2. Created a completed PG18 custom-format backup of the seven existing MANTO
   tables before staging. Its table-of-contents and checksum were checked.
   This was not a full restore rehearsal or a change to the backup policy.
3. Used `manto_stage_import.py`, with a guard for the documented PG18 endpoint,
   a new schema, the existing import lock, copied table constraints and explicit
   staging-only search path. The helper has no public-table promotion path.
4. Reconciled actual table and per-file counts after completion. The per-release
   row counts of all seven existing public MANTO tables are unchanged. This is
   a row-count comparison, not a claim of a byte-for-byte content hash.
5. Did not create credentials, roles, grants, DNS records, scheduled jobs,
   Slack channels or a live deployment. The existing source checkout with
   unrelated changes was not modified.

The import ran using the parser and staging changes at commit `7d0307b`.
The detailed local audit, source metadata, archive, backup and checksums are
retained with the job. The importer writes its start time in `imported_at`;
the verification time above records when completion was checked.

### Export-format issue caught before database writes

Fifteen source CSVs repeat a `Name` header. In four of them, 258 rows contain
different display and raw names under those repeated headers. The old parser
silently kept only the last value. It now retains the first display value and
preserves later values under collision-free duplicate keys in the parsed record.
Conflicting duplicate identifier fields still fail preflight.

This prevents silent overwriting during parsing. It does not turn the existing
database summaries into a lossless copy; the source archive is still needed.
Comparisons with older imports must distinguish parser changes from upstream
release changes.

## Refreshed local atlas

The preview was rebuilt using read-only queries against the completed v3 stage
and existing Pausanias evidence tables. It contains:

- 2,452 geographic entities, including 1,498 with representative coordinates.
- 866 entities with at least one selected identity-related figure association.
- 81,342 geographic pairs within 100 km, with 25/50/100 km exploration controls.
- 1,954 existing automated passage-level claims, with Greek context,
  machine-assisted project translations and links to the source passages.
- The earlier corrected model comparison and a GNN evaluation plan, not a new
  trained classifier.

The new release has no reviewed name-to-place links yet. Older release links
were deliberately not relabelled as v3 links. All passage-to-MANTO matches in
this preview therefore remain unresolved. Missing matches do not mean absent
or abandoned settlements.

Validation: **63 focused tests passed**. Headless Chrome checked all five views
at desktop and mobile widths, release notices, selections, filters, pagination,
empty results and refresh restoration. No page errors or page-level horizontal
overflow were found. Screenshots were visually reviewed. A sample Pausanias
source link was confirmed to return HTTP 200. JavaScript syntax and Git
whitespace checks passed.

### A concrete outcome-label audit example

The existing Pausanias extractor labels the ancient enclosure described in
10.4.2 as `extant_uninhabited`, while its own rationale says that **no habitation
claim is made**. The preceding [Panopeus passage, 10.4.1](https://pausanias.symmachus.org/translation/10/4/1.html),
explicitly describes residents despite the lack of expected civic buildings.

This is a project extraction/label issue, not a defect attributed to MANTO.
The example supports separating buildings, civic status and habitation, and
reviewing passage context before assigning a settlement outcome. Production
labels were left unchanged; neither automated confidence nor a ruin phrase is
sufficient for the survival training set.

## Next steps

1. Resolve settlement identities and review direct witnesses, source dates and
   endpoint habitation under the [study plan](manto_local_culture_survival_plan_2026-11-09.md).
2. Build release-specific links and validated features without copying old
   candidate labels into new ground truth. Keep source assertions and uncertainty
   separate from the flattened exploratory graph.
3. Decide the production activation path explicitly. Existing pages select the
   newest imported public release, so promoting the raw stage alone would switch
   them before release-specific links, features and models are ready.
4. Provision the separately approved website access and deployment path only
   after its exact target, licence compliance, access scope and TLS are verified.

For future importer performance, compute shared record facts once, reuse header
extraction plans, release whole-file JSON buffers promptly, and bound batches by
bytes as well as row count. Test output equivalence before adopting these
optimizations. Do not alter source-date rules or truncation limits merely to
make a run faster.
