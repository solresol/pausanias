# Pausanias 1.26.7 page plan

Run: 2026-10-17 Australia/Sydney. Source: local `pausanias.sqlite` `translations.english_translation`. Approved craft anchors inspected as actual PNGs: 1.1.4 and 1.1.5; their finish and typography guide this page, not their panel geometry.

| Preceding passage | Actual composition / translation | Scenic panels | Viewpoint | Palette and light |
| --- | --- | ---: | --- | --- |
| 1.25.8 | broad upper hill panorama, four lower prose columns | 1 | high, distant | blue lilac, dawn |
| 1.26.1 | tall left approach scene, three right prose blocks | 1 | low, human-scale | dry earth, terracotta, midday |
| 1.26.2 | central shield object, four surrounding prose fields | 1 | close oblique | bronze, green, cool sidelight |
| 1.26.3 | four upper prose fields, lower Eleusis panorama | 1 | ground-level wide | indigo, olive, clear daylight |
| 1.26.4 | two upper sculpture portraits, paired lower prose fields | 2 | close oblique | verdigris and pale stone, diffuse light |
| 1.26.5 | middle Erechtheion interior band, prose above and below | 1 | low architectural sweep | sea green and blue grey, doorway shaft |
| 1.26.6 | broad upper sanctuary scene, three lower prose columns | 1 | human-height room view | gold, painted wood, subdued morning light |

## Three compositions considered before art

1. **Selected: monumental vertical lamp and bronze palm study on the left, three ordered prose fields on the right.** The palm can visibly reach the ceiling and the lamp can dominate the near foreground. The third field explains Callimachus and stone craft. Art occupies more than half the page; it is a single rich architectural still life, not a column of inset illustrations. At thumbnail scale the left art/right text arrangement differs from both immediate predecessors; 1.26.1 has an earlier related art-left silhouette but falls outside the candidate-plus-five window. No left translation sidebar.
2. Rejected: broad upper sanctuary image over three lower prose columns. This repeats 1.26.6 directly and leaves the palm's height unexpressed.
3. Rejected: central lamp study with text on both sides. This is too close to 1.26.2's object surrounded by prose and reduces the art's printed scale.

## Placement and art direction

Canvas 1800×1600. Header `(28,16)–(1772,129)`. A single vertical raster `(28,150)–(1080,1570)` at about 0.74:1. Translation reading order is top to bottom at right: `(1120,150)–(1772,647)`, `(1120,667)–(1772,1038)`, `(1120,1058)–(1772,1570)`. The first field ends before “Above the lamp”; the second ends before “Callimachus”; the last contains the full remaining sentence. Exact SQLite text and punctuation are preserved by concatenating the source substrings with spaces. Header and all prose are measured with 12px padding and a 30px minimum body font before commissioning art. A short measured caption is reserved within the art's lower margin if it fits, otherwise omitted.

Selected raster: close, eye-level to slightly low view inside a restrained ancient Athenian sanctuary at the Acropolis. The ancient gold lamp burns steadily in the near foreground with a linen wick; a worked bronze palm tree rises from above it toward the ceiling, and subtle smoke is drawn upward. Stone and bronze surfaces have tactile detail. A small partly pierced stone sample can allude to Callimachus's stone craft without depicting an unrecorded event. No cult statue is needed: 1.26.6 already foregrounded that subject. This is an interpretive scene, not a claimed exact reconstruction. No inscriptions, labels, or long text baked into the art. No modern fittings, Roman or medieval details, figures or nudity. Deep teal, weathered bronze and warm flame against cool blue-grey dawn interior; quiet diffuse light with a precise flame highlight. The camera moves closer and lower than 1.26.6, the palette shifts from gold/wood to blue-green/bronze, and the balance shifts from cult image/room to lamp/palm/stone craft, all following this passage's described objects.

Orientation: local heading locates the lamp on the Athenian Acropolis, and the depiction of lamp beneath palm makes the smoke device's vertical relationship clear. No map or scenic inset is needed.

## Render and review

Pre-art and final deterministic fit **PASS**: six measured text blocks, 12px padding, complete exact 646-character SQLite translation in source order, all three prose fields at 40px; ID, heading and orientation also fit. No caption was needed. The first generated raster was rejected because a distant hilltop temple implied a second Acropolis; the edited raster retains the lamp, smoke, bronze palm, pierced stone and material finish but substitutes inland Attic hills through the opening. Both component versions are retained, and the edit instruction is appended to `art_prompt.txt`.

The corrected page was inspected at full 1800×1600 size. The lamp, linen wick, smoke, palm reaching the ceiling and pierced stone all directly support the passage; heading locates the sanctuary on the Athenian Acropolis. No figures, nudity, pseudo-writing, irrelevant callouts, clipping, or border contact. The bronze palm/lamp arrangement is interpretive; it does not claim a surviving exact reconstruction. Art, semantic fit, orientation, historical care, content suitability, hierarchy and typography **PASS** against anchors 1.1.4 and 1.1.5.

Actual PNG comparison at `tmp/1_26_7_comparison.png` covers six predecessors 1.25.8–1.26.6 at thumbnail scale. The tall left art/right prose silhouette differs from both immediate predecessors 1.26.5 and 1.26.6 and occurs once in candidate plus five predecessors. There is no left translation sidebar. Relative to 1.26.6, camera distance/angle, dominant palette, lighting and object/architecture balance all change for passage-specific reasons. Variety **PASS**. The right prose fields intentionally use their measured vertical space, with clear reading order and no inset clutter.

Bounded local build **PASS**: 168 illustrated passages, reader 168 of 168, 169 PDF pages. Final PDF page 169 was rasterized and visually inspected; its image, reading order and text are intact. Combined backup push and verify **PASS** for 461 component assets; local assets, S3 manifest, S3 finished pages and raksasa finished pages match. Independent SHA-256 of the finished page is `e8aa825830770e8c3befd9d75dd717c4ab0af1c46e68ca5c9e634dfc1f0daaea` at local, raksasa and downloaded S3. Accepted component local and downloaded-S3 SHA-256 is `80cb200968fba1c1f5a8eb2e8dd422984143f1bedeef206dbd61be8f3256015b`.

Source commit and push pending.
