# Graphic-book generation — 2026-10-15

## New page

- Passage: **1.26.5**, earliest translated SQLite passage without a canonical image at run start.
- Accepted image: `graphic_book/images/1/26/5.png`; SHA-256 `df4bf5ba47dacd50613e08ca879f89c7444d4126ce1e29f69f69afa4673f9e68`.
- Craft anchors inspected: actual PNGs 1.1.4 and 1.1.5. Six preceding actual PNGs and plans reviewed: 1.25.7, 1.25.8, 1.26.1, 1.26.2, 1.26.3, 1.26.4.
- Selected composition: one wide interpretive Erechtheion interior between two upper and two lower translation fields. First art's misleading near-sea background was edited to show inland Athens/Attica. Full-size PNG and seven-page thumbnail comparison passed art quality, orientation, semantic fit, historical restraint, suitability, no sidebar, and composition variety. No callouts or scenic insets.
- Deterministic text fit passed: complete exact 939-character SQLite translation in original order, four measured 38px translation fields; eight total blocks, each with 12px padding. Caption at 23px; no clipping or border contact.
- Local build passed: 166 illustrated passages, 167-page PDF; final PDF page 167 reviewed visually. Full `create_website.py` was not run.
- Combined backup push and verify passed for 458 component assets. The finished page hash matched local, `pausanias@raksasa` and downloaded S3. The accepted component hash `c6b58b6bb0cde2cf59436ec58722092ff8ee99a187cae57eab3012ff2d4593ba` matched local and downloaded S3; manifest row was included.
- Tracked source commit: `7e70961`, pushed to `origin/main`. Ignored binary images, SQLite, generated site and unrelated dirty 1.20.4/README work were excluded.

## Occasional replacement decision

- Single `random.SystemRandom().random()` draw: **0.44841863707240537**.
- Threshold: value below 0.20 triggers. **Skipped**; no older passage was selected, changed, archived or backed up in this run.
- Reuse this draw on a retry of the same daily run; do not draw again.

Run time: 2026-10-14T17:06:46Z (2026-10-15 Australia/Sydney).
