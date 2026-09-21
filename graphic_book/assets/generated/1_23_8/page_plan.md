# Page plan — 1.23.8

Run 2026-09-22. The earliest missing canonical image was verified in numeric passage order against the local SQLite `translations` table. The renderer loads the complete English passage verbatim and preserves its original order.

## Actual preceding PNG and plan review

The approved craft anchors 1.1.4 and 1.1.5 and the six required preceding PNGs were compared together at useful scale. Available plans were read, but the actual PNGs establish the layout history below.

| Passage | Composition / translation placement | Scenic panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.23.2 | Broad memorial scene above two lower prose columns | 1 | Low side view at pedestal height | Copper, blue, limestone; bright daylight |
| 1.23.3 | Alternating image/prose and prose/image rows | 2 | Frontal statue and deep street view | Smoky green and grey; overcast |
| 1.23.4 | Central tall sculpture with opposed prose blocks | 1 | Close low three-quarter | Bronze, umber, limestone; warm raking light |
| 1.23.5 | Broad maritime panorama above two prose columns | 1 | Distant sea-level view | Petrol blue and silver; storm daylight |
| 1.23.6 | Two equal tall scenic wings around central prose | 2 | Close onboard and medium shore figures | Wine, linen, jade, russet; clear lateral light |
| 1.23.7 | Unequal architectural diptych; compact upper-right prose | 2 | Oblique court and low wetland approach | Bronze, malachite, indigo, celadon; cool clear/overcast light |

## Three materially different compositions considered before art

1. **Selected — close sculptural panorama above two reading columns.** One broad, low-angle portrait of the bronze Trojan Horse fills the upper two-thirds. The prose sits in two measured columns below, divided at the passage's turn from Pausanias' argument to the reported occupants. This gives the tangible Acropolis dedication visual priority while allowing Menestheus, Teucer and Theseus' sons to remain legible in the sculpture. The broad-image/lower-band family appears once among the five predecessors, at 1.23.5, and therefore twice in the candidate-plus-five window. It repeats neither immediate predecessor and has no tall sidebar.
2. **Immersive full-page horse with prose in reserved sky and paving.** Rejected because long exact prose over generated texture would weaken legibility and turn the reserved areas into an artificial template.
3. **Three-part narrative sequence of Epeius, hidden warriors and the Acropolis bronze.** Rejected because it would invent workshop and siege actions not described as things Pausanias sees here, and would diminish the surviving textual focus on the bronze work.

## Passage subject and orientation

The single scene is an interpretive bronze dedication on the Athenian Acropolis: a monumental hollow horse on a plain stone plinth, viewed close and low from the front quarter. Discreet rectangular openings in its upper flank and neck reveal several fully clothed bronze warrior figures, with three most legible as Menestheus, Teucer and the sons of Theseus. The object must read as a bronze sculptural work, not a living wooden horse, battlefield reconstruction, museum display, or literal cutaway diagram. No inscriptions, modern railings, visitors, combat, corpses, flames, exposed anatomy or pseudo-text. The exact lost appearance and placement are not asserted. A locally rendered orientation line names Athens and the Acropolis, and the caption identifies the figures as Pausanias' description of the bronze work. No locator, inset or leader line is needed.

## Pre-art geometry, text fit and art choices

Canvas 1800×1500. Main art `(24,140)–(1776,1040)`, ratio 1.947:1. Caption `(24,1048)–(1776,1112)`. The passage reads in two numbered columns, `(24,1180)–(866,1476)` then `(920,1180)–(1776,1476)`, split before “It is told”. All exact text is locally rendered and measured with 12px internal padding. Body text must fit at no less than 29px and auxiliary text at no less than 25px; the renderer fails rather than saving on overflow and asserts normalized equality with SQLite.

Compared with 1.23.7, the design changes one tall architectural scene plus an offset text/landscape stack into a single horizontal object portrait over a low reading band. The camera moves from medium-wide oblique sanctuary views to a close ground-level three-quarter view. Hard rose dawn light, charcoal bronze, pale limestone and a restrained violet sky replace cool malachite/indigo/celadon. One monumental object replaces the prior balance of multiple statues, architecture and wetland landscape. These choices make the horse's construction and visible occupants immediately intelligible without inventing a siege scene.

## Review gate pending

Require full-size visual inspection and an actual seven-page thumbnail comparison; craft against 1.1.4 and 1.1.5; complete passage and ID; semantic and Acropolis orientation; content suitability; no pseudo-text or diagrammatic cutaway; and measured clearance for every block. Then inspect the built HTML/PDF, complete combined backup push/verify, and commit/push only scoped source artifacts while preserving the pre-existing README modification.

## Accepted full-size and thumbnail review

Built-in image generation supplied the panorama and one retained initial version. The first image had strong modeling but failed the background and general-audience checks because a dense distant settlement could read as modern and the horse's underside was unnecessarily anatomical. A targeted edit replaced only those details with sparse unbuilt Attic terrain and a dignified stylized bronze belly while preserving the crop, figures, openings, surface, plinth, masonry and rose dawn light.

The corrected 1800×1500 candidate was inspected at full size. The horse reads immediately as monumental aged bronze: subtle plates, seams, patina, hammered texture and integral bronze warriors are visible without becoming a schematic cutaway. Stone, vegetation, dawn sky and receding hills are richly modeled. All figures are fully clothed; there is no combat, nudity, explicit anatomy, modern skyline, pseudo-text, naive locator, filler inset or misleading callout. The panel remains directly relevant without its caption, while the local header supplies Acropolis orientation and the caption attributes the visible occupants to Pausanias' description.

Actual seven-page thumbnail comparison at `graphic_book/output/1_23_8-comparison.jpg` PASS. The single horizontal object portrait over a low reading band differs from 1.23.6's art–text–art wings and 1.23.7's unequal architectural diptych. The broad-image/lower-band family occurs only at 1.23.5 among the five predecessors, so it appears twice in the candidate-plus-five window. There is no tall left sidebar. Close ground-level object emphasis, hard rose dawn light and charcoal bronze/violet palette vary from 1.23.7's medium-wide sanctuary architecture, cool light and bronze/malachite/celadon balance.

Deterministic text fit PASS: eight actual bounding boxes with 12px padding; complete SQLite translation in original order at 33px; auxiliary minimum 28px (all above the planned minimums). Full-size visual inspection confirms complete passage ID, prose, orientation, headings and caption with no crowding, clipping or border contact. The corrected candidate is accepted for the canonical path.

## Build and backup verification

Requested local graphic-book build PASS: 143 illustrated passages and 144 PDF pages. Reader HTML identifies 1.23.8 as 143 of 143 and references the correct PNG. The rasterized final PDF page 144 was inspected at useful scale; the complete artwork, passage and captions are legible and unclipped. Full `create_website.py` was not run.

Combined backup push and verify PASS. The raksasa finished-page mirror, S3 finished pages, two new component rasters, S3 component manifest and local asset manifest agree; 402 component assets verified. Independent local, `pausanias@raksasa`, and downloaded-S3 finished-page SHA-256 is `7dab0b54dffeb0f32baaae484b34ca2f8284f757577763f33df58ce7c73975ac`. The selected local and downloaded-S3 component SHA-256 is `8c458d47022515daebe86774ab74222b3f57f39b5594508d4a9576d42b8eb8dd`.
