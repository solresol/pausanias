# Page plan — 1.23.9

Run 2026-09-23. The earliest missing canonical image was verified in numeric passage order against the local SQLite `translations` table. The renderer loads the complete English passage verbatim and preserves its original order.

## Actual preceding PNG and plan review

The approved craft anchors 1.1.4 and 1.1.5 and the six required preceding PNGs were compared together at useful scale. Available plans were read; the actual PNGs establish this layout history.

| Passage | Composition / translation placement | Scenic panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.23.3 | Alternating image/prose and prose/image rows | 2 | Frontal statue and deep street view | Smoky green and grey; overcast |
| 1.23.4 | Central tall sculpture with opposed prose blocks | 1 | Close low three-quarter | Bronze, umber, limestone; warm raking light |
| 1.23.5 | Broad maritime panorama above two prose columns | 1 | Distant sea-level view | Petrol blue and silver; storm daylight |
| 1.23.6 | Two equal tall scenic wings around central prose | 2 | Close onboard and medium shore figures | Wine, linen, jade, russet; clear lateral light |
| 1.23.7 | Unequal architectural diptych; compact upper-right prose | 2 | Oblique court and low wetland approach | Bronze, malachite, indigo, celadon; cool clear/overcast light |
| 1.23.8 | Broad bronze-horse portrait over two prose columns | 1 | Close low front-quarter | Charcoal bronze, rose, violet; hard dawn light |

## Three materially different compositions considered before art

1. **Selected — staggered two-row narrative.** The upper row pairs the first prose block at left with a substantial close study of Kritias' bronze Epicharinos at right. The lower row reverses the weight: a wide road, gate and tomb scene at left is paired with the second prose block at right. The diagonal reading rhythm separates the two subjects while retaining their order. This family last occurred at 1.23.3, outside the candidate-plus-five window, so it occurs once in the active six-page window. It repeats neither 1.23.7 nor 1.23.8 and uses no tall left sidebar.
2. **Central gate-and-tomb portrait with opposed prose and a runner inset.** Rejected because its large-image/text silhouette would be too close to 1.23.4 and would make the Acropolis statue visually incidental.
3. **Immersive Acropolis sculpture court with prose in reserved paving and a distant gate vignette.** Rejected because generated reserved areas would compromise exact-text legibility and spatially conflate the Acropolis with the Melitid gate.

## Passage subjects and historical orientation

The upper illustration is an interpretive bronze statue of Epicharinos as a hoplitodromos runner, fully clothed in a short belted chiton and helmet, carrying a round shield but no spear. He is represented as a public dedication beyond the bronze horse on the Acropolis, not as a living athlete or a reconstruction of an identified surviving statue. The lower illustration evokes the road just outside the Melitid gate with a sober uninscribed tomb beside it, walls and the distant city beyond. It does not depict Thucydides' murder, body, or an unsupported precise tomb form; it provides orientation for the explicit location and exile-return history. A small group of travellers may establish scale but must not be presented as Thucydides or his killers.

Local headings distinguish `ATHENS · THE ACROPOLIS · BEYOND THE BRONZE HORSE` from `ATHENS · NEAR THE MELITID GATE`. Captions identify the interpretive statue and the tomb location without claiming exact appearance. No map, leaders, pseudo-inscriptions, battle, corpse, murder scene, modern skyline, Roman imperial armour or nude athlete is needed.

## Pre-art geometry, text fit and art choices

Canvas 1800×1600. First prose group `(24,145)–(760,700)`; runner art `(800,125)–(1776,735)`, ratio 1.60:1. Tomb-road art `(24,840)–(1050,1510)`, ratio 1.53:1; second prose group `(1090,830)–(1776,1515)`. Captions and headings are outside art. The passage splits only before “There is also”, with the two complete blocks read upper-left then lower-right. All local text is measured with 12px padding; body text must fit at no less than 29px and auxiliary text at no less than 24px. The renderer fails before saving on any overflow and asserts normalized equality with SQLite.

Compared with 1.23.8, this page changes a single monumental low-angle object portrait and lower reading band into two staggered historical scenes with diagonally opposed prose. Camera distance changes to eye-level medium views; crisp pale midday and cool blue-green shadows replace rose dawn; people, road and architecture balance the bronze object rather than leaving one object dominant. These choices serve the passage's movement from public athletic honour to return, gate and tomb.

## Review gate pending

Require full-size inspection and actual seven-page thumbnail comparison; craft against 1.1.4 and 1.1.5; complete passage and ID; semantic and geographic orientation; no invented event, pseudo-text or schematic art; and measured clearance for every block. Then inspect the local HTML/PDF, complete combined backup push/verify, and commit/push only scoped source artifacts while preserving the pre-existing README modification.

## Accepted full-size and thumbnail review

Built-in image generation supplied two final scenic components. The 1800×1600 page was inspected at full size. The Epicharinos panel has finely modeled verdigris, cloth folds, shield, stone and atmospheric court depth; the cropped horse supplies the passage's local sequence without competing with the runner. The gate panel has a legible road-to-gate recession, sober uninscribed tomb, weathered masonry, vegetation and small anonymous travellers for scale. Both meet the craft of 1.1.4 and 1.1.5. The runner is fully clothed and reads as sculpture; there is no murder, corpse, combat, pseudo-text, modern object, schematic map or misleading callout. Local headings and captions distinguish the Acropolis dedication from the tomb near the Melitid gate, and the art does not claim exact lost forms.

The actual candidate-plus-five comparison at `graphic_book/output/1_23_9-comparison.jpg` PASS. The staggered prose/art then art/prose rows differ at thumbnail scale from 1.23.7's dominant tall scene with offset stack and 1.23.8's single broad object portrait over a lower reading band. The alternating-row family last appeared at 1.23.3, outside the five-predecessor window, so it occurs once in the active window. There is no tall left translation sidebar. Eye-level medium scenes, pale midday light, cool blue-green shadows, road, people and architecture vary from the preceding page's close low-angle bronze object, rose-violet dawn and single-object dominance.

Deterministic text fit PASS: ten measured blocks with 12px padding; complete SQLite translation in original order at 34px; auxiliary minimum 25px. Full-size inspection confirms the passage ID, prose, headings, orientation and captions are present and do not touch or cross borders. The candidate was accepted unchanged for the canonical path.

## Build and backup verification

The requested bounded graphic-book build PASS: 144 illustrated passages and 145 PDF pages. Reader HTML identifies 1.23.9 as 144 of 144 and references the correct PNG. PDF page 145 was rasterized and visually inspected; art and text are complete, legible and unclipped. Full `create_website.py` was not run.

Combined backup push and verify PASS. Two new component rasters were uploaded; 404 component assets, the local/S3 manifest, S3 finished pages and the raksasa finished-page mirror agree. Independent local, raksasa and downloaded-S3 finished-page SHA-256 is `03a27b7ac11241185d63dab8de2b075cde344c2ebc83fd11032f125eac54c9d3`. The Epicharinos component local/downloaded-S3 SHA-256 is `9e5a4fa9a2221375cf6ee6942f8a68ac72db1842c065d40e140c653a0bbfb664`; the gate component hash is `5b63c4dfe5cdf550a3a2dab62233a2969a88b769b79a090628961fa6a3e3f857` in both stores.
