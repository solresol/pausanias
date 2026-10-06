# Pausanias graphic-book generation — 2026-10-07

new_passage: 1.25.5
random_draw: 0.1851302732756891
replacement_threshold: 0.20
replacement_status: accepted
replacement_passage: 1.20.2
replacement_original_sha256: e7cfb57f99126ef8fe84edfc7829b38abcf631dc89daca6a7c5a6ba42bd3ff49
replacement_run: 20261006T171310Z
replacement_selection: First visually qualifying PNG in SystemRandom shuffled eligible list; it has a tall left translation panel, large right art and two lower insets.

## New page 1.25.5

- Final image: `graphic_book/images/1/25/5.png`, SHA-256 `1283e738a88deab861f09ac0b4892d647c9d8ad991debf592a96576562475abd`.
- Approved craft anchors: 1.1.4 and 1.1.5. Actual preceding pages: 1.24.7, 1.24.8, 1.25.1, 1.25.2, 1.25.3, 1.25.4. Selected diagonal sea-return/harbor diptych with opposed reading fields. Full-size and seven-page thumbnail checks passed; unlike both immediate predecessors, no left sidebar, and absent from candidate-plus-five context. Harbor architecture and soldiers were corrected before acceptance; historical orientation, semantic fit, art quality, content suitability and legibility passed.
- Complete SQLite translation in source order; nine measured blocks, 12px padding, 37px and 42px body type, no overflow. Bounded build passed: 158 illustrated passages, reader 158 of 158, 159-page PDF; last PDF page visually inspected.
- Combined backup push/verify passed: 435 component assets at new-page stage; local assets, S3 manifest/pages and raksasa pages agreed. Independent local/raksasa/downloaded-S3 page hash matched the value above. Accepted harbor component hash `1d1b379348a86e1c5e7afe3a5c6676c648e264be4769d5d4daee3f94f179271b` matched local/downloaded-S3. Source-only commit `cc3731b` pushed to `origin/main`.

## Optional replacement 1.20.2

- Single draw above was below 0.20. Eligible accepted IDs were numerically listed, excluding six latest, anchors 1.1.4/1.1.5 and six previously marked replacements, then shuffled once with `random.SystemRandom().shuffle()`. First inspected candidate 1.20.2 visibly qualified. No second target was selected.
- Original canonical image `graphic_book/images/1/20/2.png`, SHA-256 `e7cfb57f99126ef8fe84edfc7829b38abcf631dc89daca6a7c5a6ba42bd3ff49`, used tall left translation, large right temple art and two lower insets. The prior source renderer and plan were copied to `graphic_book/assets/generated/1_20_2/revisions/20261006T171310Z/` before editing; old component art remains.
- Selected one expansive workshop tableau over two prose fields. Three alternatives, six predecessors and two successors are documented in the replacement page plan. Final candidate `graphic_book/output/replacements/1_20_2/20261006T171310Z/candidate.png`, SHA-256 `2d74d5f6e072a0d36869c05890403238518edcd88d13241b3daaa94c5d57ba59`. Its initial component and initial candidate are retained. Sculptural figures were corrected to a clothed boy Satyr with cup and youthful clothed Eros. Eight measured blocks at 34px body with 12px padding preserve the complete 604-character SQLite prose. Full-size and target-context thumbnail review passed; the page is visibly stronger and breaks the repetitive layout. Temporary substituted-image HTML/PDF build passed with 158 illustrations and 159 pages; reader 115 of 158 and PDF page 116 visually inspected.
- Archived original: `graphic_book/assets/generated/1_20_2/revisions/20261006T171310Z/previous-page.png`; S3 key `s3://pausanias-graphic-book-assets-849621205733/assets/generated/1_20_2/revisions/20261006T171310Z/previous-page.png`. Copied local and downloaded S3 archive hashes both equaled the original hash. Asset push/verify passed before promotion. Canonical original hash was rechecked before atomic replacement.
- After promotion, the normal bounded HTML/PDF build passed: 158 illustrations, 159 PDF pages. Combined backup push/verify passed with 438 component assets; local/S3 manifest, S3 finished pages and raksasa pages agree. Independent local/raksasa/downloaded-S3 replacement page hashes equal the candidate hash above. Accepted revision component local/downloaded-S3 hash `53f9cd4ce8412baab5d03f3de3e0a5de7f4eadd3beb70ece3eb1ef96159504bf`. Replacement source commit/push recorded below.
