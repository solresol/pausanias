# Pausanias daily graphic image — 2026-10-04 (Australia/Sydney)

## New page: 1.25.2

- Earliest numeric translated passage without an image in local `pausanias.sqlite`: **1.25.2**.
- Canonical image: `graphic_book/images/1/25/2.png`; SHA-256 `a79868b73062de073748f226ccfc00a31c9e2892cbc4ce0aee640fe9a0dc4817`.
- Approved visual craft references inspected: 1.1.4 and 1.1.5. Actual six predecessor PNGs and plans compared: 1.24.4, 1.24.5, 1.24.6, 1.24.7, 1.24.8 and 1.25.1.
- Chosen composition: two unequal upper reading fields over a full-width lower sculpture-terrace scene. This repeats neither of the two immediate predecessors; it occurs once in the candidate-plus-five window. No tall left translation sidebar. Low oblique viewpoint, verdigris/charcoal/limestone palette and late-morning side light change viewpoint, palette, lighting and subject balance from 1.25.1. Variety PASS.
- The first art component was rejected for a modern-looking distant city and second hilltop landmark; a targeted revision corrected the background. Final art, historical/semantic fit, geographic orientation, content suitability, text clearance and coffee-table visual quality inspected full size and in `tmp/1_25_2_comparison.png`: PASS. Both component versions retained in the ignored S3-backed asset cache.
- Eight deterministically measured text blocks, 12px padding, glyph-bounds checks: PASS. Complete verbatim SQLite English passage in source order: PASS. Body at 39 and 37px, auxiliary at 22px or above. Full-size final PNG and final PDF page inspected.
- Bounded `uv run build_graphic_book.py --image-dir graphic_book/images --output-dir pausanias_site/graphic-book`: PASS; 155 illustrated passages, reader 155 of 155, 156-page PDF. Full website generator was not run.
- `./sync_graphic_book_backups.sh push` and `verify`: PASS; 428 component assets in manifest. Local, raksasa and independently downloaded S3 finished-page hashes all match `a79868b73062de073748f226ccfc00a31c9e2892cbc4ce0aee640fe9a0dc4817`. Accepted component local/downloaded-S3 hashes match `002a421af66d5ee5de24b78a547438aff5eb2545d5449f7905351691d7056110`.
- Relevant tracked source artifacts and asset manifest committed as `ad843d7` and pushed to `origin/main`. Ignored final image, component PNGs, SQLite, generated site and unrelated dirty README were excluded.

## Optional replacement decision

- One Python `random.SystemRandom().random()` draw after the completed new-page workflow: **0.23502329323369398**.
- Threshold: strictly below 0.20. Outcome: **skipped**; no older passage selected or modified. Reuse this draw on any retry of the 2026-10-04 run.
