# Graphic-book generation — 2026-09-23

## New page

- New passage: `1.23.9`, the earliest translated passage without a canonical image in numeric SQLite passage order.
- Final image: `graphic_book/images/1/23/9.png`.
- Approved quality references: `1.1.4` and `1.1.5`.
- Six preceding pages compared: `1.23.3`–`1.23.8`.
- Selected composition: staggered prose/statue then tomb-road/prose rows, with separate Acropolis and Melitid-gate orientation; no tall sidebar, map or filler inset.
- Full-size, seven-page thumbnail, semantic-fit, orientation, historical-care and variety reviews: PASS.
- Deterministic text fit: PASS for ten blocks with 12px padding; complete SQLite translation in original order at 34px; minimum auxiliary type 25px.
- Local HTML/PDF build: PASS, 144 illustrated passages and 145 PDF pages; reader `144 of 144`; PDF page 145 visually inspected.
- Combined backup push/verify: PASS; 404 component assets verified; raksasa and S3 finished pages and S3 component assets agree.
- Finished-page SHA-256, independently matched locally, on raksasa and from S3: `03a27b7ac11241185d63dab8de2b075cde344c2ebc83fd11032f125eac54c9d3`.
- Component SHA-256 values independently matched locally and from S3: Epicharinos `9e5a4fa9a2221375cf6ee6942f8a68ac72db1842c065d40e140c653a0bbfb664`; Melitid gate `5b63c4dfe5cdf550a3a2dab62233a2969a88b769b79a090628961fa6a3e3f857`.
- New-page source commit: `3b6b0fc0ad6028878901cd85aa9c8f02b62a2d17`, pushed to `origin/main`.

## Occasional replacement decision

- Random procedure: one draw from `random.SystemRandom().random()` after the new-page build, backup verification and source push succeeded.
- Recorded draw: `0.23922619781785315`.
- Trigger threshold: `< 0.20`.
- Outcome: `skipped` because the draw was not below the threshold.
- No older passage was selected, generated, archived, promoted or modified.
