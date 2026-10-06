# Pausanias 1.25.5 — Leosthenes and the garrison

The earliest numeric translated passage without a canonical image is **1.25.5** (843 characters). It moves from the allied command and Leosthenes' sea return of Greek mercenaries, through his death, to the Macedonian occupation of Munychia, Piraeus and the Long Walls. The exact English comes from local `pausanias.sqlite`.

Approved craft references inspected as actual PNGs: **1.1.4** and **1.1.5**. Their rich raster finish and legible typography are the standard; their ochre locator, callout density and left sidebar are not a layout template. Six preceding actual PNGs and plans were inspected:

| Passage | Composition and translation placement | Scenic panels | Viewpoint | Palette and light |
| --- | --- | ---: | --- | --- |
| 1.24.7 | Tall Athena art left; three prose sections right | 1 | upward sculptural portrait | ivory/gold/green-black; side light |
| 1.24.8 | Apollo upper left and Sipylus lower strip; prose upper right and foot | 2 | eye-height object and distant valley | bronze/green/mauve; silver day |
| 1.25.1 | Tall central statue court; prose on both sides | 1 | frontal medium | marble/terracotta; neutral morning |
| 1.25.2 | Two prose fields above a broad sculpture terrace | 1 | low oblique | verdigris/limestone; late-morning side light |
| 1.25.3 | Upper prose, central battlefield, lower prose | 1 | ground-level wide | blue-grey/umber/olive; post-storm diffuse |
| 1.25.4 | Broad upper Boeotian landscape; two lower prose fields | 1 | high oblique, distant | blue-green/violet; cool early morning |

## Compositions considered before art

1. **Selected: diagonal historical diptych with opposed reading fields.** An upper-left sea scene shows the return of Greek mercenaries; the complete first two sentences read at upper right. The next two sentences read at lower left, facing a lower-right view of the fortified harbor and Macedonian garrison. This four-quadrant rhythm gives the return and occupation different physical settings and a clear chronological turn. It resembles neither of the two preceding page silhouettes, and the diagonal diptych does not occur among the five predecessors. No tall left translation sidebar.
2. A single harbor panorama with all prose below. Rejected because its image/text masses resemble 1.25.4 and omit the earlier sea return.
3. A central standing portrait of Leosthenes with opposed columns. Rejected because no likeness is available, and it would echo 1.25.1 without orienting the two locations.

## Text geometry and art direction

Canvas 1800×1600. Header and orientation occupy y=16–139. Upper art `(34,155)–(870,765)`, aspect 1.37:1. First prose field `(916,171)–(1766,810)` contains sentences one and two, source order. Second prose field `(34,842)–(870,1430)` contains sentences three and four. Lower art `(916,839)–(1766,1550)`, aspect 1.20:1. Local short headings and art captions are measured in their own rectangles. Reading order is upper right then lower left, with section numbers 1 and 2. Body minimum 29px, 12px padding; renderer asserts complete verbatim reconstruction and checks each final glyph rectangle. Geometry was preflighted before image generation.

Both components are sophisticated painterly historical scenes for a coffee-table book, with no text, labels, pseudo-inscriptions, modern objects, nudity or gore. **Upper image:** medium-distance, eye-level maritime arrival at a Greek European shore, late fourth century BCE: ancient oared transport ships near a stone quay and fully clothed returning Greek mercenaries with bundles and equipment, without an invented identifiable portrait of Leosthenes or a claim to know the precise landing port. Deep teal water, weathered timber, sailcloth and cool bright open daylight. **Lower image:** closer oblique view of the Athenian Piraeus harbor with the Munychia height and connected Long Walls legible as coastal and inland fortifications; a modest, fully clothed Macedonian garrison presence, no staged combat, no modern skyline. Blue-green sea, pale limestone and muted iron-red textile accents in overcast late-day light. This is an interpretive reconstruction of the occupation sequence, not a survey map. Locally rendered headings and captions name the setting and limit what is inferred. Relative to 1.25.4, camera moves from distant elevated inland terrain to eye-level maritime and closer coastal architecture; palette and light also change. Art balance moves from unpeopled landscape to ships, people and fortifications. No locator inset is needed because the named harbor structures provide orientation.

## Review

The initial harbor raster was rejected because tower, battlement and roof shapes looked later than the passage. An architecture correction removed them, and a second edit changed Roman-looking foreground equipment to simpler Hellenistic Greek/Macedonian forms. All three revision components are retained. The sea-return raster was accepted without revision. Neither panel has baked-in lettering. The harbor remains an interpretive landscape: no exact historical plan is claimed.

The first page rendering left excessive whitespace in the prose fields. The renderer was revised to use 37px and 42px body type and place the second caption immediately beneath the passage. Final deterministic check **PASS**: nine blocks, each with 12px padding and glyph-bounds verification; both prose sections reconstruct the full 843-character SQLite translation in its original order. Auxiliary type is at least 23px.

Final PNG inspected at full size and beside the six actual predecessors in `tmp/1_25_5_comparison.png`. The diagonal two-art/two-prose checkerboard is absent from the five-predecessor window and unlike both immediate predecessors; there is no tall left sidebar. The eye-level maritime return and closer oblique harbor differ from 1.25.4's distant high inland view in camera, subject balance, palette and lighting. Variety **PASS**. Art quality, orientation, historical care, semantic fit, text clearance, hierarchy and content suitability **PASS** against the 1.1.4/1.1.5 quality anchors. There are no irrelevant callouts, flat locator or crude scenic insets.

Bounded local build **PASS**: 158 illustrated passages, reader 158 of 158, 159-page PDF; final PDF page visually inspected. Combined backup push and verify **PASS** with 435 component assets. Finished PNG SHA-256 `1283e738a88deab861f09ac0b4892d647c9d8ad991debf592a96576562475abd` independently matches local, raksasa and downloaded S3 copies. Accepted harbor component SHA-256 `1d1b379348a86e1c5e7afe3a5c6676c648e264be4769d5d4daee3f94f179271b` matches local and downloaded S3 copies. Source commit/push follows.
