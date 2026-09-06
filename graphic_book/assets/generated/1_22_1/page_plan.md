# Page plan: 1.22.1

Earliest numeric passage with a nonempty local SQLite translation and no canonical PNG, verified 2026-09-07.

- Key places and objects: Athens, ascent toward the Acropolis past the sanctuary of Asclepius, temple of Themis, tomb of Hippolytus before it; another Hippolytus tomb at Troezen.
- Main visual: rich painterly reconstruction of the south Acropolis slope. A path passes a lower sanctuary terrace and ascends toward a small temple with a modest tomb in its forecourt. Acropolis walls above establish orientation. Architecture and precise arrangement are illustrative, not an archaeological plan.
- Insets: fully clothed Phaedra confides in her elderly nurse in a classical domestic interior; separate Troezen tomb tradition in an Argolid landscape, explicitly illustrative. No depiction of the fatal curse or invented account from the next passage.
- Orientation: local Athens / south slope note and main callouts; Troezen identified in the northeastern Peloponnese across the Saronic Gulf.
- Approved style references inspected: graphic_book/images/1/1/4.png and 1/1/5.png. Continuity layout: render_passage_1_21_7.py.
- Production: generated text-free raster art; deterministic local text and callout composition on 1402x1122 parchment. Measure actual text bounds with 12 px padding; fail before save on overflow. Preserve the full SQLite translation.
- Review: full-size PNG inspection for art quality, exact text, border clearance, appropriate leaders, orientation, and fully clothed figures before canonical filing. Build HTML/PDF, inspect final PDF page, combined backup push and verify before scoped source commit and push.

## Acceptance review

- Full-size 1402x1122 candidate PNG inspected before canonical rendering; accepted. Rich masonry, layered landscape and expressive scenic insets meet the approved visual standard. Insets retain their full height to avoid cropping the figures.
- Three leaders verified against the sanctuary colonnade, Themis temple doorway and Hippolytus tomb masonry. Athens south-slope orientation is explicit; Troezen tradition is distinguished from the Athenian tomb. Reconstructed architecture and conversation are labelled as illustrative.
- 14 deterministic actual-bounding-box checks passed with 12 px padding. Complete English translation matches SQLite; translation font 18 px; minimum auxiliary font 15 px. No crowding or clipped text observed.
- Local HTML/PDF build passed: 128 illustrated passages, 129 PDF pages. Reader identifies 1.22.1 as 128 of 128. Rasterized PDF page 129 visually inspected and accepted.
- Component generation: built-in imagegen, main ascent and paired tradition insets. Prompts retained alongside this plan; component rasters backed up outside Git.
