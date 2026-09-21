# Graphic-book generation — 2026-09-22

## New page

- New passage: `1.23.8`, the earliest translated passage without a canonical image in numeric SQLite passage order.
- Final image: `graphic_book/images/1/23/8.png`.
- Approved quality references: `1.1.4` and `1.1.5`.
- Six preceding pages compared: `1.23.2`–`1.23.7`.
- Selected composition: one close, low-angle bronze-horse panorama above two measured reading columns; no tall sidebar or filler inset.
- Full-size, seven-page thumbnail, semantic-fit, orientation, content-suitability and variety reviews: PASS.
- Deterministic text fit: PASS for eight blocks with 12px padding; complete SQLite translation in original order at 33px; minimum auxiliary type 28px.
- Local HTML/PDF build: PASS, 143 illustrated passages and 144 PDF pages; reader `143 of 143`; PDF page 144 visually inspected.
- Combined backup push/verify: PASS; 402 component assets verified; raksasa and S3 finished pages and S3 component assets agree.
- Finished-page SHA-256, independently matched locally, on raksasa and from S3: `7dab0b54dffeb0f32baaae484b34ca2f8284f757577763f33df58ce7c73975ac`.
- New-page source commit: `6a3fd8d1e58dd65189a7f1d21ff5355ab4faf173`, pushed to `origin/main`.

## Occasional replacement decision

- Random procedure: one draw from `random.SystemRandom().random()` after the new-page build, backup verification and source push succeeded.
- Recorded draw: `0.4382892922203515`.
- Trigger threshold: `< 0.20`.
- Outcome: `skipped` because the draw was not below the threshold.
- No older passage was selected, generated, archived, promoted or modified.
