# Pausanias 1.25.2 page plan — 2026-10-04

Earliest numeric translated passage without a canonical image: **1.25.2**. The renderer reads the complete English translation from local SQLite and checks the reconstructed text word for word. The passage moves from Attalus's small sculptural dedication near the Acropolis south wall to the separate statue of Olympiodorus. The images of war are represented works of art, not a claim that those events occurred together at Athens.

Approved craft anchors inspected as PNGs: **1.1.4** and **1.1.5**. Their detailed raster finish and legible typography guide the page; their left sidebars, ochre frame and callout pattern do not. The six actual preceding PNGs were viewed together at thumbnail scale and their plans read:

| Passage | Actual composition / translation placement | Scenic panels | Viewpoint | Dominant palette and light |
| --- | --- | ---: | --- | --- |
| 1.24.4 | Central wide ox scene between upper and lower prose | 1 | wide ground-level | limestone/olive; clear morning |
| 1.24.5 | Diagonal pediment/helmet diptych, prose opposite | 2 | oblique facade and close object | marble blue/gold; daylight and cool spot |
| 1.24.6 | Wide upper griffin landscape, two prose columns below | 1 | low, near foreground | slate/lapis; cold dawn |
| 1.24.7 | Full-height Athena portrait left, prose in right sections | 1 | upward interior portrait | ivory/gold/green-black; side light |
| 1.24.8 | Upper-left Apollo and lower Sipylus panorama, prose upper right and foot | 2 | eye-height object and distant terrain | bronze/green/mauve; silver daylight |
| 1.25.1 | Central tall sculpture court, opposed prose columns | 1 | eye-height medium | white marble/terracotta/olive; neutral morning |

## Three compositions considered before art

1. **Selected: two unequal upper reading fields over one immersive sculpture terrace.** The wide left field holds the Attalus sentence; the narrower right field holds Olympiodorus. The shared full-width lower image gives the small votive figures, wall and separate statesman statue a coherent spatial relationship. Source order is left then right. This top-prose/lower-art silhouette differs from both immediate predecessors and does not occur among the five preceding pages. It is closest to 1.24.2, outside that window. No tall left sidebar.
2. **Rejected: broad upper panorama over two equal prose columns.** The art would be strong, but the large masses repeat 1.24.6 within the five-page window and weaken this passage's deliberate change from artworks to Olympiodorus.
3. **Rejected: four miniature battle panels around a central Olympiodorus portrait.** It suggests precise lost iconography and makes the illustration read like a diagram; it also spends area on scenes that the source only names.

## Geometry and pre-art text fit

Canvas 1800×1600. Measured header and orientation occupy y=18–137. Translation rectangles: Attalus `(34,191)–(1050,535)`; Olympiodorus `(1080,191)–(1766,535)`. Split exactly before “There also stands”; source order left then right. The single raster scene occupies `(34,570)–(1766,1492)` (aspect 1.88:1), with a short measured interpretive caption at the foot. All text uses 12px padding, Pillow wrapping and glyph-bounds checks; minimum body 30px and auxiliary 20px. The renderer must fail on overflow and on any change to the original translation. Preflight completed before art generation: **PASS**, eight blocks; exact SQLite translation in order, body at 39 and 37px, auxiliary at 22px or more.

## Art direction

One finished painterly historical illustration, viewed from low pedestrian height along the southern Acropolis wall. A coherent terrace scene shows a row of small bronze votive sculptural groups, roughly two cubits high in the source, on modest bases near the wall. Their varied draped/armoured forms suggest four different represented combats without pretending to reconstruct lost details. A separate, larger fully clothed bronze honorific statue of Olympiodorus stands farther along the same terrace, visibly distinct from Attalus's series. The south wall and distant Attic hills give orientation; do not add a second Acropolis, a modern city, inscriptions, pseudo-writing, invented battle action, or nudity. No text is baked into art. Wide 1.88:1 composition, low oblique view, cool verdigris bronze, charcoal blue shadow and pale weathered limestone; clear late-morning side light. A single image, no scenic insets. Local title and caption identify Athens and mark the reconstruction as interpretive.

Relative to 1.25.1, shift from a medium frontal white-marble figure group to a low oblique view along a wall, from white marble/terracotta to verdigris/charcoal/limestone, and from neutral frontal morning to crisp side light. The balance moves from human-scale statuary to small votive groups and a surrounding architectural terrace. These choices follow the described scale and location, without inventing the figures' lost forms.

## Post-render review

First raster was rejected because its distant city and hilltop landmark appeared modern and implied a second Acropolis. A targeted edit replaced that background with a sparse Attic valley while preserving the bronze groups, terrace and separate statue. Both components are retained; `south_wall_sculptures.png` is the accepted art.

The final 1800×1600 PNG was inspected at full size and against the six actual predecessors in `tmp/1_25_2_comparison.png`. The two upper prose fields over a single broad lower scene repeat neither 1.24.8 nor 1.25.1 and occur once in the candidate-plus-five window. There is no tall left sidebar. Low oblique view, verdigris/charcoal/limestone palette and late-morning side light change at least viewpoint, palette, lighting and subject balance from 1.25.1. Variety **PASS**. The wall, ancient setting and local title orient the image; the sculpture groups are recognisably artworks and the caption marks all lost forms as interpretive. Full-size art finish, semantic/historical fit, content suitability, hierarchy, label/caption clearance and text legibility **PASS** beside the 1.1.4/1.1.5 craft anchors. The complete SQLite translation appears in original order; eight deterministically measured blocks pass 12px padding and glyph-bounds checks, body 39/37px and auxiliary 22px or greater. Reader HTML lists passage 1.25.2 as 155 of 155; bounded build produced a 156-page PDF and the final PDF page was visually inspected. Backup verification is recorded in the generation report.
