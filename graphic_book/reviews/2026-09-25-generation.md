# Pausanias graphic-book generation — 2026-09-25

- New passage: `1.24.1`, earliest translated passage without an accepted image in numeric SQLite order.
- New image: `graphic_book/images/1/24/1.png`; SHA-256 `8698aafc0ca7b2e018f80a62305dc63c083f28d1c0668214f96a5f2a55962c5e`.
- Approved quality anchors: `1.1.4`, `1.1.5`. Six actual preceding pages compared: `1.23.5`–`1.23.10`.
- Composition: continuous oblique sculptural-gallery panorama above two measured reading fields. The broad-image/lower-band family occurs twice in candidate plus five predecessors; neither immediate predecessor shares it. No tall left translation sidebar.
- Text: full verbatim SQLite English passage in order; eight deterministic fitted text blocks with 12px padding, passage at 36px, auxiliary minimum 27px. Full-size PNG and seven-page thumbnail comparison passed art quality, historical orientation, semantic fit, suitability, and variety review. Initial component was corrected to remove a modern-looking skyline.
- Local build: PASS; 146 illustrated passages, reader `146 of 146`, 147-page PDF; PDF page 147 visually reviewed. Full `create_website.py` not run.
- Combined backup push and verify: PASS, 408 component assets. Finished page local, raksasa and independently downloaded S3 hashes match. Selected component local and downloaded S3 hashes match (`87a5847556e9ec0e9a6c3e67db21a04768bc95c7af60e80563e407904636a539`).
- New-page source commit: `e0af4b8`, pushed to `origin/main` successfully. Only renderer, prompts, plan and asset manifest staged; ignored binaries, SQLite, generated site and unrelated dirty README were excluded.

## Occasional replacement decision

- One Python `random.SystemRandom().random()` draw: `0.7228248089904347`.
- Threshold: `< 0.20`.
- Outcome: **skipped**. No older passage selected or modified. Reuse this exact draw on any retry of this daily run.
