# Pausanias 1.24.8 — page plan (2026-10-02)

## Source and recent visual history

Earliest translated local SQLite passage without a canonical PNG, in numeric order: 1.24.8. The complete English translation is read directly by the renderer. Approved craft references 1.1.4 and 1.1.5 and the actual six preceding PNGs were inspected in a contact sheet; the references' left prose bars and ochre framing are not copied.

| Passage | Actual composition and translation placement | Scenic panels | Viewpoint | Dominant palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.24.2 | Four upper prose fields over a wide bronze bull | 1 | close low terrace | teal and grey; overcast |
| 1.24.3 | Near-square Earth statue upper left; prose right and foot | 1 | eye-level medium | blue-grey and green; storm light |
| 1.24.4 | Wide central ox scene between upper and lower prose | 1 | ground-level wide | limestone and olive; clear morning |
| 1.24.5 | Diagonal pediment/helmet diptych; prose opposite | 2 | oblique facade and close object | marble blue and gold; daylight and cool spot light |
| 1.24.6 | Wide upper griffin panorama; two prose columns below | 1 | low, near foreground | slate, lapis, muted gold; cold dawn |
| 1.24.7 | Full-height Athena portrait left; three prose sections right | 1 | slightly upward architectural portrait | ivory, gold, green-black; interior side light |

## Three compositions considered before generating art

1. **Selected: two-place sequence with an upper Athens object scene, a lower Sipylus landscape, and prose in separate ordered reading fields.** The bronze Apollo is the upper-left scenic mass, with the Athenian explanation in an upper-right field. A broad, low landscape stripe moves to Mount Sipylus; three prose columns below carry the three reported causes in source order. It keeps Athens and Sipylus explicitly distinct while letting the illustration change scale and location. Neither of the two preceding pages has this large-mass arrangement. The closest text-top/art-bottom and upper-left-object families each differ in both art and text placement. There is no tall left translation sidebar.
2. A single giant statue portrait surrounded by prose. Rejected: repeats 1.24.7's tall sculptural portrait at thumbnail scale and gives Sipylus no visual orientation.
3. A full-width mountainous panorama above two lower prose columns. Rejected: repeats 1.24.6's image-first/lower-text silhouette and would reduce Apollo to a caption.

## Pre-art fit and art direction

Canvas 1800×1600. Header y=18–129. Apollo art `(34,151)–(1020,741)`, ratio 1.67:1, with a measured caption beneath it; Athens reading field `(1047,164)–(1766,726)`. Sipylus art `(34,807)–(1766,1230)`, ratio 4.09:1 after review; the locally drawn transition heading follows at y=1237–1283 and three reading columns at y=1290–1548. Reading order: upper right, then lower columns left to right. A short lower caption clarifies that the three reported causes did not occur together. Every local text block uses a defined target rectangle, Pillow wrapping and glyph-bounds check with 12px padding. Pre-art PASS: eleven measured blocks; exact SQLite translation reconstructed in order, body at 33–35px, auxiliary at 20px or larger. No art commissioned before this fit check.

Athens art: sophisticated, richly textured painterly archaeological reconstruction of a **lost bronze Apollo statue** standing beyond an ancient Athenian temple. Low human eye-height three-quarter view, near enough to see aged dark bronze and sculptural craftsmanship, wide enough to see ancient temple masonry and Acropolis ground context. Apollo is an idealized fully clothed male figure in a long ancient garment; no nude classical anatomy. Cool blue-green bronze, soft grey limestone, restrained violet-brown shadows, cloudy silver daylight. No locust plague staged in Athens; no inscriptions or text. The exact lost form is unknown, so this is an interpretation, not a claim about Phidias's surviving work. Target crop 1.67:1.

Sipylus art: a **separate** historically grounded western Anatolian mountain landscape around Mount Sipylus, viewed from a low rocky slope across layered ridges and a cultivated plain. A small natural-looking locust swarm rides a visible strong wind through the sky. Distant cloud and light variation may suggest changeable weather but must not stage wind, burning heat and freezing cold as simultaneous literal incidents. Wide cinematic 4.77:1 crop with richly modelled rock, vegetation, terrain and atmosphere; cool basalt, muted green, mauve cloud, pale silver light. No giant insect, people, buildings, lettering, map diagram, or invented event. Weather mechanisms remain in the exact text.

Compared with 1.24.7, the page moves from one upward full-height interior portrait to an eye-height outdoor object scene plus a distant terrain panorama; ivory/gold interior glow becomes cool bronze/green and silver daylight; the visual balance moves from a single statue to statue and landscape. The change in distance, lighting, palette and subject balance is tied to Pausanias's move from Athens to Sipylus. The two generated scenes are separated rather than blended into one invented place.

## Post-render review and verification

The first Apollo component had a second monumental Acropolis and a town-like distant background. A targeted second version replaced those with open Attic hills and retained the bronze figure, nearby temple, surface detail and light. Both versions and the revision prompt remain in the asset cache. The Sipylus component has credible depth and a naturalistic locust swarm. The two scenes are interpretive, distinct in location and free of nudity, pseudo-writing, generic callout leaders or flat schematic terrain.

The final 1800×1600 PNG was opened at full size. Eleven measured blocks pass the 12px padding and glyph-bounds checks; exact SQLite translation appears in order, with body at 33–35px and auxiliary type at 20px or above. All labels and captions clear their borders. The large-mass shapes were compared with actual 1.24.2–1.24.7 PNGs in `tmp/2026-10-02-comparison.png`; the selected two-scene sequence occurs once in the candidate-plus-five window and repeats neither 1.24.6 nor 1.24.7. No tall left prose sidebar. Art, semantic fit, geographic orientation, historical caution, suitability, hierarchy and typography pass beside anchors 1.1.4 and 1.1.5. The lower landscape was enlarged after the first render to improve thumbnail balance, with measured text rechecked.

Bounded local build PASS: 153 illustrated passages, reader 1.24.8 shows 153 of 153 and the correct image, PDF 154 pages; page 154 was rasterised and visually inspected. Combined backup push/verify PASS: 424 component assets; local asset cache, S3 asset manifest, S3 pages and raksasa pages match. Independent local/raksasa/downloaded-S3 final-page SHA-256: `4ba276fe31a5873a4e9e8b017fd33a1d868df42562587dff0ec3ff4fcbeec1b6`. Selected Apollo component local/downloaded-S3 SHA-256: `c9dd67c19ea845f5609e55ca39744c675c27cb0a17db085c07954663652a2897`; Sipylus component local/downloaded-S3 SHA-256: `c7184caf79bc2de406060feda27f53e06a0e6ff0996c974eb8cc6db2254e56d3`.
