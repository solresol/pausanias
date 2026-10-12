# Pausanias 1.26.3 — Olympiodorus across Attica

Run: 2026-10-13. Earliest numeric translated passage without a canonical PNG: **1.26.3** (788 characters). Approved craft anchors 1.1.4 and 1.1.5 were inspected as actual PNGs for raster finish and readable typography. Their ochre maps and left prose bars are not adopted.

## Six actual predecessors

| Passage | Composition and translation placement | Panels | Viewpoint | Palette and light |
| --- | --- | ---: | --- | --- |
| 1.25.5 | Diagonal sea/harbor art and opposed prose | 2 | eye-level maritime, oblique harbor | teal/iron-red, open day/overcast |
| 1.25.6 | Fort upper left, prose and coast on right, prose below | 2 | close low fort, distant shore | pine/grey, misty morning |
| 1.25.7 | Two tall art leaves flanking central prose | 2 | close interior, ground-level wall | violet/bronze/blue-grey, side/cloudy light |
| 1.25.8 | Broad upper Athens prospect, four lower prose fields | 1 | high distant prospect | blue-lilac/silver, dawn |
| 1.26.1 | Tall left narrative art, three right prose blocks | 1 | close ground-level ascent | earth/terracotta/olive, midday |
| 1.26.2 | Central vertical shield art, four corner prose fields | 1 | close eye-level object study | bronze/slate/malachite, cool side light |

The actual PNGs were compared together at `tmp/1_26_3_refs.png`. Plans were read where present; the PNGs control the thumbnail-scale comparison.

## Three pre-art compositions

1. **Selected: four ordered prose columns across the upper portion, with a single wide immersive Eleusinian plain scene across the lower portion.** The prose can carry the passage's movements among several places without forcing them into a false composite map. The illustrated episode is the stated greatest deed at Eleusis. The image/text silhouette differs from 1.26.1 and 1.26.2, has no tall left sidebar, and occurs once in candidate plus five. The upper-text/lower-art arrangement is materially distinct from 1.25.8's upper-art/lower-text arrangement.
2. Rejected: alternating four-scene travel strip from Aetolia through Delphi. This would require speculative scenes for acts the text only reports and dilute Eleusis.
3. Rejected: monumental statue at right with a tall left translation field. It would repeat the prohibited sidebar pattern and overemphasize the final memorial over the principal event.

## Subjects, orientation, geometry, and art direction

The four sentences remain four verbatim, ordered text blocks: Eleusis and the Macedonian incursion; earlier Aetolian aid against Cassander; honors at Athens and Eleusis; Phokian dedication at Delphi. Their original order matters because the second sentence explicitly reaches backward. A locally typeset orientation line identifies Eleusis in western Attica, Aetolia, Athens, Elateia, and Delphi. The image is an interpretive reconstruction of an Eleusinian defensive gathering and approaching Macedonian incursion, not an asserted battle plan, identifiable portrait, or claim about the exact lost built environment.

Canvas 1800×1600. Header y=16–132. Four numbered headings at x=28/472/916/1360, y=151–200. Four prose rectangles `(28,207)–(440,730)`, `(472,207)–(884,730)`, `(916,207)–(1328,730)`, `(1360,207)–(1772,730)`. Wide art `(28,777)–(1772,1531)`, aspect 2.31:1; a short caption sits at y=1535–1585. Every text block is measured with 12px padding before art generation, minimum 30px body, and glyph-bounds checks; fail if any does not fit. No text, labels, or reserved text areas inside the raster.

Main art prompt: sophisticated, detailed historical oil-painted panorama, very wide composition, close but expansive ground-level three-quarter view across the Eleusinian plain in the late fourth century BCE. At foreground left, a believable group of fully clothed local Greek defenders gathers under the direction of an unidentifiable leader near ancient Eleusis; at a credible distance, a small Macedonian force approaches across the plain. The settlement and its sanctuary precinct are spatial anchors, without pretending to reconstruct specific lost facades. Human figures remain natural and period-plausible; tactile ground, fabric, shields, stone and distant hills. No gore or fabricated decisive action. Clear cool daylight after rain, muted indigo, olive, chalk and restrained red accents; natural depth and atmospheric perspective. Compared with 1.26.2, camera moves from close object to wide human landscape, palette moves from green-bronze interior to indigo/olive open air, and balance moves from a solitary object to people and terrain. These choices follow the passage's Eleusinian incursion. No inset, map, leader, or decorative callout is needed.

## Review

Pre-art fit **PASS**: all 788 SQLite characters are reconstructed in original order from the four rendered sentence blocks. Twelve text blocks have deterministic wrap, 12px padding, and actual glyph-bound checks; body sizes are 35, 36, 38 and 38px, auxiliary text at least 24px. No block crosses its rectangle.

The first raster's purple military standards looked too much like later imagery. It is retained as `eleusis_defenders_initial.png`; an edited component removed those standards and is the accepted art. The scene retains one credible distant incursion, the local Eleusinian gathering, landscape depth, and richly finished materials. Its building silhouettes are interpretive, not a claim to reconstruct the Eleusinian sanctuary. No baked text, nudity, modern objects, gore, or precise battle manoeuvre appears.

The final 1800×1600 PNG was inspected at full size. `tmp/1_26_3_comparison.png` places it beside actual 1.25.5–1.26.2 PNGs at thumbnail scale. Upper translation over one panoramic lower scene has a different silhouette from both immediate predecessors. No left sidebar; the composition occurs once in candidate plus five. Relative to 1.26.2, viewpoint, palette, lighting, and balance of people/landscape versus object/architecture all change for passage-specific reasons. Reference quality, semantic fit, spatial orientation, historical restraint, content suitability, hierarchy, and text clearance **PASS**. There are no leader lines or optional insets to assess.

Bounded HTML/PDF build **PASS**: 164 illustrated passages and a 165-page PDF. The 1.26.3 HTML links to the correct image; the final PDF page was rasterized and visually inspected at `tmp/1_26_3_pdf_page.png`.

Combined backup push/verify **PASS**: 452 assets match the local/S3 manifest, with S3 finished pages and raksasa mirror matching the local tree. The finished page SHA-256 is `5ad1b14226e8eec231ad091c4e4c14d9613ccc182869c16322567ee828f0b1cf` in the local file, raksasa mirror, and downloaded S3 page. Accepted component SHA-256 is `05b64ec7e2d519912cdf1198f48f7d2610be12cd661b3354e5879867efc1a375` locally and after independent S3 download. The initial component is retained and backed up too. The unrelated unfinished 1.20.4 replacement and its manifest rows remain outside this page's source commit.
