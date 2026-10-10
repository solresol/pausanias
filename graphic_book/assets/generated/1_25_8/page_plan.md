# Pausanias 1.25.8 — the Museum hill

Earliest translated passage without an image in numeric SQLite order: **1.25.8** (617 characters). The passage links Lachares's death, Demetrius's hold on Athens and Piraeus, and the Museum hill opposite the Acropolis, with traditions about Musaeus and a Syrian memorial. The art reconstructs the hill's location and fortified state without portraying an unrecorded event.

Approved craft references inspected as actual PNGs: **1.1.4, 1.1.5**. Their raster finish and typography set the standard, not their sidebars or palette.

| Passage | Actual composition / translation placement | Panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.25.2 | Two upper prose fields over sculpture terrace | 1 | low oblique | verdigris, limestone / side light |
| 1.25.3 | Upper prose, central battlefield, lower prose | 1 | ground-level wide | blue-grey, umber / diffuse |
| 1.25.4 | Broad upper Boeotian landscape over lower prose | 1 | high oblique | blue-green, violet / cool morning |
| 1.25.5 | Diagonal two-art/two-prose harbor diptych | 2 | eye-level maritime | teal, iron-red / daylight and overcast |
| 1.25.6 | Large left fort, right prose/shore, lower prose | 2 | low architecture, distant coast | pine, grey / misty morning |
| 1.25.7 | Two tall art leaves flanking central prose | 2 | close interior, ground-level wall | violet bronze, blue-grey / side and cloudy light |

## Three pre-art compositions

1. **Selected: one continuous upper hill prospect over four ordered lower prose fields.** The Museum ridge, Athens and the Acropolis need to be seen in relation. One wide scene gives geographic orientation without a map or speculative action. Four lower fields retain a comfortable type size and read left to right. This silhouette occurs once among the preceding five (1.25.4), so twice in the candidate-plus-five window; it repeats neither immediate predecessor. No tall left sidebar.
2. A large right hill portrait with left prose and a lower prose strip. Rejected because at thumbnail scale it mirrors 1.25.6's large lateral art plus prose.
3. A Musaeus tomb study surrounded by prose. Rejected because the described tomb is a reported tradition with no known form; it would make a conjectural object the page's main identity and obscure the Athens geography.

## Pre-art layout and direction

Canvas 1800×1600. Header `(28,16)–(1772,135)`. One raster view `(28,151)–(1772,1045)`, aspect 1.95:1. A short measured orientation caption sits beneath it. Four ordered translation fields occupy `(28,1116)–(449,1580)`, `(469,1116)–(890,1580)`, `(910,1116)–(1331,1580)`, `(1351,1116)–(1772,1580)`. They split only at source punctuation; local rendering verifies their concatenation equals the verbatim SQLite translation and checks glyph bounds with 12px padding and body minimum 30px. Text preflight passed at 35px body before art generation; the scene was enlarged after thumbnail review and the revised geometry was remeasured.

Selected main art: sophisticated painterly historical landscape reconstruction of late fourth-century BCE Athens from a high rocky vantage east of the Museum hill, looking southwest. The Museum hill is the clear near-middle-ground subject, its low Hellenistic stone fortification and small fully clothed garrison integrated into real terrain. The Acropolis is recognisable across the valley on the right, and distant land falls toward the Saronic coast, without pretending that the Piraeus and all landmarks are simultaneously visible in photographic precision. The hilltop has **no later Roman Philopappos monument**; do not invent a marked tomb for Musaeus or the Syrian, or stage Lachares's death. Rich ancient urban fabric, nuanced stone and vegetation, deep atmospheric perspective. A cool blue-lilac dawn with pale silver light, darker cypress and shadowed marble; no golden sunset, modern buildings, Roman/medieval features, inscriptions, labels, visible nudity or text in the raster. Local header/caption orient Athens, Acropolis and Museum hill. No inset or callout is necessary.

Relative to 1.25.7, the camera becomes high and distant instead of close/ground-level, the palette shifts to blue-lilac and silver from violet bronze and grey stone, the light becomes dawn instead of side-lit/cloudy late morning, and the balance moves from objects/buildings to topography and urban setting. The passage's repeated spatial relation between hill and Acropolis warrants those choices.

## Post-render review

The first raster was rejected because it placed the coast beyond the Acropolis in an uncertain geographic arrangement. Its retained component is `museum_hill_initial.png`. The accepted `museum_hill.png` uses a north-side prospect: Acropolis at left, distinct fortified Museum ridge at right, city between, and no implausibly placed sea. The view remains an interpretive reconstruction, with no identifiable tomb, later Philopappos monument, invented battle, visible nudity, baked text or misleading callout.

The final 1800×1600 PNG was inspected at full size, and `tmp/1_25_8_comparison.png` puts it beside actual PNGs 1.25.2–1.25.7 at thumbnail scale. Its one upper panorama and four lower prose fields are distinct from 1.25.6 and 1.25.7; the broad upper-image/lower-prose family appears in 1.25.4 and this candidate only in the six-page window. No tall left translation sidebar. Relative to 1.25.7, high/distant viewpoint, blue-lilac/silver palette, dawn light, and topographic rather than object-led balance satisfy the art-variety rule. Raster finish, semantic and geographic orientation, historical restraint, hierarchy, suitability and text clearance **PASS** beside anchors 1.1.4 and 1.1.5.

Preflight and final render measured eight text blocks with 12px padding; all four translation blocks use 35px body. The complete 617-character SQLite translation is present verbatim in its original order; actual glyph bounds **PASS**. Initial full-size review found excess lower whitespace, so the scene was enlarged and all blocks remeasured. The bounded local build **PASS**: 161 illustrated passages, reader 161/161, PDF 162 pages; its final page was rasterized and visually reviewed.

Combined backup push and verify **PASS** for 446 component assets: local cache, S3 manifest, S3 finished pages and raksasa pages match. Independent local/raksasa/downloaded-S3 finished-page SHA-256: `246c64418e506ab8edd536c1c9464d246b51f2542d15db2d61f1917e6d963f7d`. Accepted component local/downloaded-S3 SHA-256: `8773a762fe8966e285d0e486447ade0d387fd0108546bfa56b6553d80a2a67eb`.
