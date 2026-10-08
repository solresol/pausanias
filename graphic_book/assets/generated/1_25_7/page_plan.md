# Pausanias 1.25.7 — Lachares and Athena's adornments

Earliest translated passage without an image in numeric SQLite order: **1.25.7**, 758 characters. The passage moves from Cassander's support for Lachares, to Demetrius's overthrow, Lachares's flight as Athens's walls were taken, and the removed Acropolis shields and Athena adornments. Approved quality anchors: actual PNGs 1.1.4 and 1.1.5, for finished raster craft and type quality, not their layout.

| Passage | Actual composition / translation placement | Panels | Viewpoint | Palette and light |
| --- | --- | ---: | --- | --- |
| 1.25.1 | Tall central statue court, prose on both sides | 1 | frontal medium | marble/terracotta; neutral morning |
| 1.25.2 | Two upper prose fields, broad lower sculpture terrace | 1 | low oblique terrace | verdigris/limestone; side light |
| 1.25.3 | Upper prose, central battlefield, three lower prose fields | 1 | ground-level wide | blue-grey/umber/olive; post-storm diffuse |
| 1.25.4 | Broad upper Boeotian landscape, two lower fields | 1 | high oblique distant | blue-green/violet; cool early morning |
| 1.25.5 | Diagonal two-art/two-prose harbor diptych | 2 | eye-level sea return and oblique harbor | teal/limestone/iron-red; daylight and overcast late day |
| 1.25.6 | Large left fort, smaller right shore, paired lower prose | 2 | close low architecture and distant island | pine/grey and silver-blue; misty morning |

## Three pre-art compositions

1. **Selected: two tall full-height illustrated leaves flanking a continuous central translation column.** The left art studies the stripped sanctuary; the right art looks outward from Athens's walls toward Boeotia. The prose runs down the central column in four ordered sections. At thumbnail scale, the dominant silhouette is two tall image masses divided by text; this differs from the two predecessors and appears once in the candidate-plus-five window. It is not a left translation sidebar.
2. A wide city-wall panorama above three lower prose columns. Rejected because 1.25.4 already has the same image/text silhouette and the passage's religious violation would be visually secondary.
3. A chronological four-panel sequence. Rejected because it would need portraits and precise scenes of persuasion and overthrow that the passage does not describe.

## Pre-art layout and direction

Canvas 1800×1600. Header `(28,16)–(1772,130)`. Left art `(28,147)–(565,1518)`, portrait aspect 0.392. Central text column `(588,145)–(1212,1548)`. Right art `(1235,147)–(1772,1518)`, portrait aspect 0.392. Four source sentences are assigned in order to measured text blocks in the central column. The complete SQLite translation was fitted before art generation; local rendering will assert exact ordered text and glyph bounds with 12px padding. The two scenes remain independent, without a false spatial montage.

Left art: an interpretive early Hellenistic Acropolis sanctuary interior, close and eye-level, tactile marble and bronze, the fully clothed sacred image of Athena in dignified shadow with detachable adornment absent and vacant places where golden shields have been removed. No nudity, gore, portrait of Lachares, exact claim about the lost image's appearance, Roman or medieval features, letters, labels, or text. Dominant palette cool violet stone, oxidized bronze, muted gold; clear light from a high side opening. Right art: an interpretive wide ground-level view near Athens's ancient walls during their capture, with a small cloaked fugitive on a road toward distant Boeotian hills; credible Greek stonework and terrain, fully clothed figures, restrained smoke rather than a fabricated battle. Deep blue-grey and olive, cloudy late morning. No modern/medieval architecture, inscriptions, labels, or text. Local captions will name the interpretive subjects.

Relative to 1.25.6, camera distance shifts to close interior and a separate ground-level exterior rather than fort approach and island prospect; the dominant palette changes from pine/grey to violet/bronze and blue-grey; lighting changes from misty dawn to side-lit interior and overcast day. People are subordinate to sacred object and city architecture. Athens, its Acropolis, walls, and Boeotia are explicitly named in the passage and page furniture, giving historical and geographic orientation without a schematic main map.

## Review and verification

The first Athena component incorrectly retained a gold shield and adornments, so it was revised before acceptance; the unused first raster remains in the imagegen cache. The final sanctuary panel shows a fully clothed stripped image and no prominent remaining shield. The walls panel uses a plausible Greek stone gate and a small departing figure; it does not identify the figure or stage an unreported battle. Both source panels and the final crop were inspected for semantic fit, historical restraint, visible exposure, baked-in text, and art quality. These checks **PASS**.

The final 1800×1600 PNG was opened at full size. The seven-page comparison sheet `tmp/1_25_7_comparison.png` places 1.25.1–1.25.6 beside the candidate. Its two tall art leaves and uninterrupted center prose differ from the last two pages' diagonal diptych and large-left/lower-prose structures; the candidate layout occurs once in candidate plus five predecessors. There is no tall left translation sidebar. The close object interior and ground-level wall road, violet/bronze and blue-grey/olive colours, and mixed side/cloudy light vary at least two art choices from 1.25.6. Quality, orientation, hierarchy, callout relevance (none used), suitability and variety **PASS** against the anchors 1.1.4 and 1.1.5.

Deterministic preflight and final render checked ten measured blocks with 12px padding; all four translation blocks use 36px body type. The complete 758-character SQLite translation is present verbatim in original order, and actual glyph bounds fit. Caption overflow caught at preflight was corrected before art. Text fit **PASS**. Local bounded build **PASS**: 160 illustrated passages; reader 1.25.7 reports 160 of 160 and points to the accepted PNG; PDF has 161 pages. Final PDF page was rasterized and reviewed.

Combined backup push and verify **PASS** for 442 component assets. Independent local/raksasa/downloaded-S3 finished-page SHA-256: `bc96ed5e57fef346634aeccaaf73ad806c68ecf3abe572c5d82caa18cb961570`. Downloaded S3 component checksums match local: Athena `17d1df222b92b3ceeb2c8fb62f2126c7081c38c6b488da557097a7d96f6662f6`; walls `ca5a98e07b4c6ee145f4a5bbfdc6b7a643d4b5941c31319478fa21a63eb7e42e`. Source commit and push follow.
