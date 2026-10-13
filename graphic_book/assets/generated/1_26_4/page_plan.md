# Pausanias 1.26.4 — page plan

Run: 2026-10-14. Earliest translated passage without a canonical image: **1.26.4**. Approved craft references: actual PNGs **1.1.4** and **1.1.5**, used for raster finish and readable typography, not layout.

## Six preceding accepted pages, checked as PNGs

| Passage | Actual large masses / translation | Scenic panels | Viewpoint | Dominant palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.25.6 | Large upper-left fort, right prose and shore inset; two lower prose fields | 2 | Low approach to fort; distant island | Pine and grey; misty morning |
| 1.25.7 | Two tall art leaves flanking central prose | 2 | Eye-level interior and ground-level city exterior | Violet bronze and blue-grey; side light/cloud |
| 1.25.8 | Wide upper landscape over three lower prose fields | 1 | Elevated Athens/Mouseion prospect | Blue-lilac dawn |
| 1.26.1 | Tall left action scene with three right prose fields | 1 | Ground-level uphill approach | Earth, terracotta and olive; clear midday |
| 1.26.2 | Tall central shield with four corner prose fields | 1 | Close eye-level object study | Malachite, bronze and slate; cool side light |
| 1.26.3 | Four upper prose columns over one lower panorama | 1 | Wide ground-level Eleusinian scene | Indigo, olive and chalk; clear post-rain light |

## Three pre-art compositions

1. **Selected: paired statue portraits over paired translation fields.** Artemis and the seated Athena each receive a substantial vertical image in the upper portion, with their related prose immediately below. Left field carries sentences 1–2; right field carries sentences 3–5, including the transition. Clear left-to-right reading order. Two upper art masses over two lower text masses differ from both immediate predecessors and occur once in the candidate-plus-five window. No tall left translation sidebar.
2. A central shared Acropolis scene with the two statues and marginal prose. Rejected because the exact spatial relationship of the statues is uncertain and a composite would imply a reconstruction.
3. A tall right Athena portrait with an upper-left Artemis inset and one continuous left prose field. Rejected because it reintroduces a tall left prose sidebar and makes the Artemis dedication subordinate.

## Content, geometry and art direction

Canvas 1800×1600. Header and orientation occupy y=16–134. Two separately framed art panels `(28,170)–(866,924)` and `(934,170)–(1772,924)`, aspect 1.11. Captions occupy y=928–970, headings y=990–1034, and paired lower text fields `(28,1040)–(866,1550)` and `(934,1040)–(1772,1550)`. Read left panel and its prose, then right panel and its prose. All passage words stay verbatim in source order. Text fit was checked before commissioning art.

Subjects: the bronze Artemis Leukophryene dedicated by Themistocles' sons, and Endoeus' seated Athena dedicated by Callias. These are interpretive, non-portrait statue studies, not claims about the lost works' exact appearance. Architecture situates them in ancient Athens; a local orientation line names Magnesia on the Maeander as the place associated with Artemis' cult and Themistocles' governorship. No invented ceremony, inscription lettering, scenic inset or leader line. Captions distinguish interpretive reconstruction from surviving evidence.

Left raster prompt: painterly high-detail archaeological/historical illustration, close oblique view of a modest bronze standing Artemis statue, fully draped and modest, in a restrained ancient Athenian sanctuary setting; tactile aged bronze, limestone and muted verdigris, diffuse cool daylight. Right raster prompt: painterly high-detail historical illustration, seated fully draped archaic Greek Athena statue on a plain stone base in an ancient Athenian sanctuary, close low three-quarter view, tactile pale stone and subtle pigment traces, cool lavender shadow with soft morning light. No legible writing, labels, modern objects, nudity, mythic action, crowds, or Roman/medieval details. The paired images use distinct angles and materials. Relative to 1.26.3, camera changes from wide outdoor landscape to close object portraits, palette shifts from indigo/olive terrain to verdigris/stone, and people/landscape give way to sculpture/architecture; the passage itself moves from military action to dedications and memorials.

## Review status

Pre-art measured fit **PASS**: nine blocks, each with 12px padding and glyph-bound checks; both translation fields at 40px, auxiliary fields at 19px or larger. The two prose fields concatenate to the complete exact 613-character SQLite translation in original order. A first Athena component with an anachronistic Classical Parthenon in the distance was rejected; a second edit removed that monument and retained the seated, draped statue. No component contains legible text or inappropriate exposure.

Final 1800×1600 PNG inspected at full size and alongside actual preceding PNGs 1.25.6–1.26.3 in `tmp/1_26_4_comparison.png`. Two upper sculpture studies over their own prose fields have a different thumbnail silhouette from 1.26.2's central object/four-corner prose and 1.26.3's upper prose/lower panorama. No tall left translation sidebar; this composition occurs once in the candidate-plus-five window. Compared with 1.26.3, camera distance, subject balance, palette and lighting change for the dedication passage. The corrected raster art, paired subjects, Athens/Magnesia orientation, historical restraint, suitability, text clearance and hierarchy **PASS** against 1.1.4/1.1.5. No leader or locator is used.

Bounded local build **PASS**: 165 illustrated passages, reader HTML 1.26.4 links its image, 166-page PDF with last page visually reviewed. Combined backup push and verify **PASS** for 454 component assets. Finished page SHA-256 `56eae4bda9cfa60045c68bfc2679384137edd9e61832bd6e9f2a3a95e0af6a74` matches local, raksasa and independently downloaded S3 image. Both accepted component hashes match downloaded S3 assets: Artemis `502ae1cff9d6233533a7426ae1964707d07b46352fbb2a430391467a991ceaf0`, Athena `3ab5ffe5c01d97ae15b9b2c30ca4a189abadaea0ecea27692eabeb5b2ecfb3ec`.
