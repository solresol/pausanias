# Page plan — 1.23.7

Run 2026-09-21. Earliest missing numeric canonical image verified against the local SQLite `translations` table. The complete English translation is loaded verbatim by the renderer and retained in original order.

## Actual preceding PNG and plan review

The approved craft anchors 1.1.4 and 1.1.5 were opened together at useful scale. Seven actual recent PNGs (the six required predecessors plus 1.22.8 for broader context) were compared in `/tmp/pausanias-visual.AdSinA/recent.png`; plans were read where available. The actual PNGs, rather than the plans alone, establish the following layout history.

| Passage | Composition / translation placement | Scenic panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.23.1 | Unequal tall portrait diptych; compact upper-right prose | 2 | Medium frontal and three-quarter portraits | Burgundy, malachite; dim window light |
| 1.23.2 | Broad memorial scene above two lower prose columns | 1 | Low side view at pedestal height | Copper, blue, limestone; bright daylight |
| 1.23.3 | Alternating image/prose and prose/image rows | 2 | Frontal statue and deep street view | Smoky green and grey; overcast |
| 1.23.4 | Central tall sculpture with opposed prose blocks | 1 | Close low three-quarter | Bronze, umber, limestone; warm raking light |
| 1.23.5 | Broad maritime panorama above two prose columns | 1 | Distant sea-level view | Petrol blue and silver; storm daylight |
| 1.23.6 | Two equal tall scenic wings around central prose | 2 | Close onboard and medium shore figures | Wine, linen, jade, russet; clear lateral light |

## Three materially different compositions considered before art

1. **Selected — unequal architectural diptych with compact upper-right reading field.** A dominant tall Acropolis sculpture-court portrait occupies the left 61% of the page. The complete passage occupies a compact upper-right reading area, and a substantial wide Brauron sanctuary landscape fills the lower right. The two places are distinct without turning the page into a map. This family last appeared at 1.23.1, outside the candidate-plus-five window; it does not repeat either immediate predecessor. Text is not a tall left sidebar.
2. **Broad Acropolis panorama above two prose columns with a Brauron inset.** Rejected because the broad-image/lower-band family already occurs twice in the active window at 1.23.2 and 1.23.5, and an inset would make Brauron visually subordinate.
3. **Three alternating object-and-text rows for the boy, Perseus and Artemis.** Rejected because it would repeat 1.23.3's alternating-row rhythm and isolate the works as disconnected catalogue entries rather than locating them in the sanctuary landscape.

## Passage subjects and historical orientation

The left illustration places a fully clothed bronze boy with a lustral basin and a bronze Perseus within an evocative Acropolis enclosure associated with Artemis Brauronia. A larger-than-life, fully draped seated marble Artemis appears in architectural shade. Their arrangement and lost details are illustrative, not asserted as an exact reconstruction. Perseus' Medusa reference is a restrained gorgoneion emblem, not a severed head or violent scene. The right illustration shows the principal Brauron sanctuary within its Attic wetland setting, with a small subordinate wooden cult image in a shadowed shrine; it does not invent Tauris or a ritual event.

Official Acropolis Museum guidance consulted on 2026-09-21 states that the Acropolis sanctuary was the city branch of the main sanctuary at modern Vravrona, that its final form included an enclosure and stoa with two closed wings, and that temple traces are not preserved. The museum also identifies the surviving over-life-size Artemis head as probably belonging to a seated acrolithic cult statue attributed by Pausanias to Praxiteles. The art therefore avoids a confident temple reconstruction and treats the statue and arrangement as interpretive.

Orientation is local and textual: `ATHENS · THE ACROPOLIS · SOUTH OF THE PROPYLAIA` above the complete passage, and `BRAURON · EASTERN ATTICA` above the second scene. No locator or leader lines are needed. Both scenic panels should remain semantically legible if their captions are hidden.

## Pre-art geometry, text fit and art choices

Canvas 1800×1600. Main art `(24,125)–(900,1450)`, ratio 0.661:1, preserving the full 2:3 generated portrait without trimming the boy's feet. Complete translation `(940,220)–(1776,690)`. Brauron art `(940,820)–(1776,1450)`, ratio 1.327:1. Captions and labels sit outside the art. Reading order is the single uninterrupted prose block. All locally drawn text is measured with 12px internal padding; the passage is required to fit at no less than 29px, and auxiliary text no less than 23px. The renderer asserts exact normalized equality with SQLite and fails rather than saving on overflow.

Compared with 1.23.6, the new page replaces two equal scenic wings and a central prose column with one dominant architectural field plus an offset prose/landscape stack. It replaces living figures and the sea encounter with sculpture and sanctuary architecture; changes close eye-level people to an oblique medium-wide court view and low wetland approach; and changes wine/jade/russet sunlight to bronze/malachite, indigo architectural shade and pearly celadon overcast light. These changes arise from the passage's paired Acropolis/Brauron geography.

## Review gate pending

Require full-size inspection and actual seven-page thumbnail comparison; craft against 1.1.4 and 1.1.5; exact passage and ID; semantic and geographic orientation; content suitability; absence of pseudo-text; measured clearance for every text block; and confirmation that the unequal diptych occurs once in the candidate-plus-five window. Then inspect built HTML/PDF, complete combined backup push/verify, and commit/push only the scoped source artifacts. Preserve and exclude the pre-existing README modification.

## Accepted full-size and thumbnail review

Built-in image generation supplied two final scenic components and one retained earlier main-art version. The initial Acropolis component failed the historical-background check because a modern-looking city and hilltop monument appeared beyond the stoa. A targeted edit removed only that skyline and replaced it with unbuilt Attic hills; the corrected art retains the statues, court, crop, lighting and palette. Full-size inspection of the 1800×1600 page found richly modeled bronze, marble, worn masonry, wetland water, reeds and atmospheric hills. The boy, Perseus and Artemis are fully clothed; there is no violence, nudity, pseudo-writing, modern skyline, schematic panel or misleading leader. The boy's entire figure and pedestal are preserved after revising the page geometry away from an over-wide fill crop.

Both panels remain semantically direct without their captions: the principal scene shows the basin-bearing bronze boy, Perseus with a restrained Medusa emblem and the seated Artemis within a sanctuary court; the second shows Brauron's stoa, wetland setting and subordinate wooden image. The locally rendered orientation distinguishes the Acropolis city branch from the principal sanctuary in eastern Attica. Lost appearances and arrangement are explicitly described as illustrative.

Actual seven-page thumbnail comparison at `graphic_book/output/1_23_7-comparison.png` PASS. The dominant tall architectural scene with an offset prose/landscape stack is unlike 1.23.5's broad panorama and 1.23.6's equal art–text–art wings. It belongs to the unequal-diptych family last used at 1.23.1, outside the candidate-plus-five window, so the layout occurs once in the active window. No tall left translation sidebar. Sculpture/architecture, oblique court depth, bronze/malachite and cool clear light vary from the preceding page's living figures, close paired viewpoints, wine/jade/russet and clear lateral shore light.

Deterministic text fit PASS after final geometry: seven actual text blocks with 12px padding; complete SQLite translation in original order at 32px; auxiliary minimum 26px, with captions at 27px. Visual inspection confirms the passage ID, full passage, orientation, captions and all clearance. Candidate accepted for the canonical path.

## Build and backup verification

Requested local graphic-book build PASS: 142 illustrated passages and 143 PDF pages. Reader HTML identifies 1.23.7 as 142 of 142 and references the correct PNG. The rasterized final PDF page 143 was inspected at useful scale: complete artwork, passage and captions are legible and unclipped. Full `create_website.py` was not run.

Combined backup push and verify PASS. The raksasa finished-page mirror, S3 finished pages, three new component rasters, S3 component manifest and local asset manifest agree; 396 component assets verified. Independent local, raksasa and downloaded-S3 finished-page SHA-256 is `73aa2d99028771a4985bcc79093ab0967bf77f797995ba7b1ec82cfd4fbcdda3`.
