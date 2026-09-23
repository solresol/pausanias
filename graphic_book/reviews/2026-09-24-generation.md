# Graphic-book generation — 2026-09-24

## New page

- New passage: `1.23.10`, the earliest translated passage without a canonical image in numeric SQLite passage order.
- Final image: `graphic_book/images/1/23/10.png`.
- Approved quality references: `1.1.4` and `1.1.5`.
- Six preceding pages compared: `1.23.4`–`1.23.9`.
- Selected composition: one tall central civic portrait with opposed prose blocks, Paiania and Athenian naval-command orientation, and no tall translation sidebar, map or filler inset.
- Full-size, seven-page thumbnail, semantic-fit, orientation, historical-care, content-suitability and variety reviews: PASS. An initial pseudo-writing failure on the tablets was removed in a targeted art correction before acceptance.
- Deterministic text fit: PASS for nine blocks with 12px padding; complete SQLite translation in original order at 34px and 32px; minimum auxiliary type 27px.
- Local HTML/PDF build: PASS, 145 illustrated passages and 146 PDF pages; reader `145 of 145`; PDF page 146 visually inspected.
- Combined backup push/verify: PASS; 406 component assets verified; raksasa and S3 finished pages and S3 component assets agree.
- Finished-page SHA-256, independently matched locally, on raksasa and from S3: `caccb874fa5f4a6a6190e101c90a8b15a29bb119ac9c81719f727e12010fc79a`.
- Corrected component SHA-256, independently matched locally and from S3: `f5ed5004005420ba10402a74c11cee2f1489a94f91f58e3928ca80169fcd4c02`.
- New-page source commit: `543d96588f8253055a08a9e35ae7f1940405ce71`, pushed to `origin/main`.

## Occasional replacement decision

- Random procedure: one draw from `random.SystemRandom().random()` after the new-page build, backup verification and source push succeeded.
- Recorded draw: `0.41051073388116843`.
- Trigger threshold: `< 0.20`.
- Outcome: `skipped` because the draw was not below the threshold.
- No older passage was selected, generated, archived, promoted or modified.
