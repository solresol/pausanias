# Pausanias 1.26.6 — Athena's ancient image and Callimachus's lamp

Run: 2026-10-16 Australia/Sydney. Source: the complete 634-character English translation in local `pausanias.sqlite`. Craft anchors inspected as actual PNGs: 1.1.4 and 1.1.5; their finish and typography, not their sidebar or ochre furniture, guide this page.

| Preceding passage | Actual composition and translation placement | Scenic panels | Viewpoint | Dominant palette and lighting |
| --- | --- | --- | --- | --- |
| 1.25.8 | One wide upper Athens prospect, four lower prose columns | 1 | elevated distant view | blue violet dawn |
| 1.26.1 | Tall left hill-approach image, three right prose fields | 1 | ground-level human view | earth, olive, midday |
| 1.26.2 | Tall central shield, four corner prose fields | 1 | close object view | green bronze, slate, cool side light |
| 1.26.3 | Four upper prose columns above lower Eleusis scene | 1 | wide ground-level plain | indigo, olive, cool post-rain light |
| 1.26.4 | Paired upper sculpture portraits over paired prose | 2 | close oblique sculptures | verdigris, pale stone, diffuse day |
| 1.26.5 | Wide architectural band between two upper and two lower prose fields | 1 | low oblique interior | sea green, grey, deep blue, shaft of light |

## Three pre-art compositions

1. **Selected: one immersive broad upper sanctuary scene, three ordered lower translation columns.** The ancient cult image and Callimachus's gold lamp can occupy one credible sacred interior rather than becoming unrelated object stickers. Three bottom columns read left to right, with no tall sidebar. This silhouette differs from 1.26.4 and 1.26.5 and appears only once in candidate plus five predecessors.
2. **Rejected: central statue portrait with prose in four corners.** Too close to 1.26.2's central shield composition, and would visually separate the lamp.
3. **Rejected: asymmetric statue/lamp diptych with adjacent prose.** The paired upper objects and lower text would echo 1.26.4 and imply two separate settings.

## Geometry, reading order and art

Canvas 1800×1600. Header `(28,16)–(1772,127)`. Broad art `(28,145)–(1772,1045)` (1.94:1); short orientation caption `(28,1055)–(1772,1102)`. Three translation fields `(28,1120)–(576,1570)`, `(626,1120)–(1174,1570)`, `(1224,1120)–(1772,1570)`. Split at the exact source phrases “But the holiest thing” and “The tradition about it”; joining the fields with spaces must equal the SQLite translation byte-for-byte. Pre-art measured fit at minimum 30px is required. Header and caption are measured too.

Selected art: richly detailed, painterly reconstruction of an ancient Athenian sanctuary on the Acropolis. Wide, human-height three-quarter interior view. The archaic, fully draped wooden cult image of Athena stands within a dignified architectural setting, with Callimachus's small worked-gold lamp prominent on a stone support in the foreground. The lamp is visually distinct from the statue. Historicity is interpretive: no claim to know the exact appearance of the lost image or lamp, no falling-from-heaven event depicted, no invented priestly ritual. Use tactile painted wood, aged limestone, restrained gold and dusty teal shadows; soft cool early-morning light from one side. No text, labels or lettering baked into art. No Classical Parthenon facade, later Roman or medieval objects, modern fittings, nudity, or extra mythic spectacle. The header locates the Acropolis, and the caption distinguishes Pausanias's report from a precise reconstruction.

Relative to 1.26.5, the composition changes from a narrow middle architectural band to a dominant upper illustration with three lower columns. Camera shifts from low architectural sweep to human-height object encounter; the subject balance changes from architecture/water/rock to cult image/lamp; palette moves from sea green and blue shadow to painted wood and gold; light shifts from a dramatic shaft to subdued morning light. These changes follow the passage.

## Review

Pre-art and final deterministic text fit **PASS**: seven measured blocks, 12px padding, 38–39px translation, exact 634-character SQLite text in source order, all labels/header/caption fitting. First raster was rejected for a nearby sea and hanging objects; second removed those but left a duplicate hilltop temple. Final edited component replaces that view with inland Attic hills and low city roofs, preserving the cult image and lamp. It was inspected full-size. The statue is fully draped, the gold lamp distinct, there is no baked text, and the scene is explicitly interpretive rather than a claim to reconstruct the lost objects exactly. Historical cue, semantic fit, content suitability, orientation and art quality **PASS** against 1.1.4 and 1.1.5.

Final 1800×1600 PNG inspected at full size and in `tmp/1_26_6_comparison.png` beside the six actual predecessors. The broad upper art and three lower prose columns differ from both immediate predecessors. Among the candidate and five predecessors, this silhouette appears once; there is no tall left translation sidebar. The viewpoint, object balance, palette and lighting vary from 1.26.5 for passage-specific reasons. No irrelevant scenic inset, leader or locator. Thumbnail composition and variety **PASS**.

Bounded HTML/PDF build **PASS**: 167 illustrated passages, 168 PDF pages, final page visually inspected and consistent with the PNG. Combined backup push/verify **PASS** for 459 component assets. Finished-page SHA-256 `3ef5b98786d1e0f83c99a1b4bccbd1224e6fd63e336523f4be5a5a37baefb1f2` matches local, raksasa and independently downloaded S3; the accepted component SHA-256 `1d37623a0a9105d63613add78c4224b13e277a4db224fba9e3fea22e5bb5765c` matches local and downloaded S3. Source delivery pending.
