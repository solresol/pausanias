# Pausanias 1.26.5 — Erechtheion

Run: 2026-10-15 Australia/Sydney. Source: complete 939-character `pausanias.sqlite` English translation. Approved craft anchors inspected as actual PNGs: 1.1.4 and 1.1.5.

## Six preceding accepted pages (actual PNGs and plans)

| Passage | Composition and translation placement | Scenic panels | Viewpoint | Dominant palette and light |
| --- | --- | ---: | --- | --- |
| 1.25.7 | Two full-height art leaves flank central prose | 2 | Close interior and ground-level road | Violet bronze and blue grey; side light/overcast |
| 1.25.8 | Wide upper panorama, four lower prose fields | 1 | High distant city prospect | Blue lilac and silver dawn |
| 1.26.1 | Tall left hill approach, three right prose blocks | 1 | Ground-level human-scale uphill | Dry earth, terracotta, olive; neutral midday |
| 1.26.2 | Central shield with four corner prose fields | 1 | Close eye-level object study | Green bronze and slate; cool side light |
| 1.26.3 | Four upper prose fields over broad lower historical scene | 1 | Wide ground-level plain | Indigo, olive, chalk; cool daylight after rain |
| 1.26.4 | Paired upper statue portraits, paired lower prose fields | 2 | Close oblique sculpture portraits | Verdigris and pale stone; diffuse daylight |

## Three compositions before art

1. **Selected: one long architectural interior band between two upper and two lower translation fields.** The interior makes the altars, painted walls, seawater well and trident-bearing rock legible as related features of the Erechtheion. Text reads upper left, upper right, lower left, lower right. One scene, no scenic insets, no tall sidebar. At thumbnail scale a central horizontal art mass interrupts two text bands; this is distinct from both immediate predecessors and occurs once in candidate plus five predecessors.
2. Rejected: paired close object studies of the seawater well and trident mark over two prose fields. This would repeat 1.26.4's paired upper art/lower prose silhouette and obscure the building's spatial relation.
3. Rejected: full-page aerial cutaway with text at the edges. It could turn disputed ancient reconstruction into false certainty and would risk schematic architecture.

## Selected geometry and interpretation

Canvas 1800×1600. Header `(28,16)–(1772,130)`. Upper translation fields `(28,154)–(865,421)` and `(935,154)–(1772,421)`. Single wide art panel `(28,449)–(1772,1128)` (about 2.57:1). Caption `(28,1133)–(1772,1182)`. Lower translation fields `(28,1190)–(865,1560)` and `(935,1190)–(1772,1560)`. Source sentences 1–2, sentence 3, sentence 4 plus sentence 5 up to “the inhabitants of Aphrodisias”, and the remainder of sentence 5 plus sentence 6 form the four blocks. Their concatenation must equal the SQLite text exactly, in original order. Pre-art Pillow fit must pass at readable body size with 12px padding before image generation.

The main art is an explicitly interpretive, historically restrained view of the ancient Erechtheion on the Athenian Acropolis, looking obliquely from a shadowed entrance toward a double interior. Foreground rock and a small seawater well give Poseidon's claims physical focus; plain altars and faint mural surfaces recede deeper into the building. No attempt to identify which surviving architectural feature corresponds to each reported object. The caption will say this is an interpretive interior, not a precise reconstruction. Passage ID, names and complete prose are rendered locally, never by the image model. No optional locator, route, leader, or callout is needed: header and caption locate the building on the Acropolis and the scene itself orients the reported features.

Relative to 1.26.4: the camera moves from two close sculpture portraits to a low, wide architectural interior; the dominant palette moves from verdigris/pale stone to sea green, cool grey stone and deep blue shadow; light changes from diffuse exterior daylight to a directional shaft through a doorway; the subject balance moves from statues to architecture, water and rock. Each choice follows this passage's description of the building and its signs. No invented people, ritual action, legible wall paintings, certain ancient floor plan, nudity, Roman/medieval details or pseudo-inscriptions.

## Review and delivery

Pre-art measured text fit **PASS**: eight blocks with 12px padding; all four translation fields at 38px, complete exact 939-character SQLite passage in original order. Caption 23px. The first generated raster showed a misleading near-sea exterior; it was edited to show Athens, the Attic plain and distant hills while preserving the Erechtheion interior, well, altars and trident mark. The corrected component and 1800×1600 page were inspected at full size. No missing passage text, edge collisions, illegible writing, inappropriate exposure, irrelevant callouts, or schematic art. This is an interpretive visualization, not a precise archaeological reconstruction. Art finish, semantic fit, orientation, historical care, typography and suitability **PASS** against 1.1.4/1.1.5.

The actual seven-page thumbnail sheet `tmp/1_26_5_comparison.png` places 1.25.7–1.26.4 beside the candidate. Its single central horizontal interior between upper and lower prose bands differs from both immediate predecessors (1.26.3 upper prose/lower battle and 1.26.4 paired upper statues/lower prose). This silhouette occurs once in candidate plus five predecessors; no tall left translation sidebar. Low architectural interior, sea-green/blue-grey palette and doorway light change viewpoint, subject balance, palette and lighting from 1.26.4. Variety **PASS**.

Local bounded HTML/PDF build **PASS**: 166 illustrated passages, 167 PDF pages; final PDF page 167 was rasterized and visually reviewed. Combined backup push and verify **PASS** for 458 component assets. Finished page SHA-256 `df4bf5ba47dacd50613e08ca879f89c7444d4126ce1e29f69f69afa4673f9e68` matched local, raksasa and downloaded S3. Accepted component SHA-256 `c6b58b6bb0cde2cf59436ec58722092ff8ee99a187cae57eab3012ff2d4593ba` matched local and downloaded S3. Source push: pending.
