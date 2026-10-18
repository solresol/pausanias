# Pausanias 1.27.1 — Athena Polias's offerings

Run: 2026-10-18 Australia/Sydney. Source is the complete exported English translation from `graphic_book_corpus.load_translation("1.27.1")`, 736 characters. Approved craft anchors 1.1.4 and 1.1.5 were inspected as actual PNGs. Actual accepted PNGs 1.26.2–1.26.7 were compared in `/tmp/pausanias_1271_refs.jpg`; their plans were read as supporting evidence.

| Preceding passage | Actual composition and translation placement | Scenic panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.26.2 | Tall central shield, four corner text fields | 1 | close eye-level object | malachite, bronze, slate; cool side light |
| 1.26.3 | Four upper text columns, broad lower Eleusinian panorama | 1 | ground-level wide landscape | indigo, olive, chalk; clear post-rain day |
| 1.26.4 | Two upper sculpture portraits, two lower prose fields | 2 | close oblique figures | verdigris, pale stone; diffuse day |
| 1.26.5 | Wide middle architectural band, text above and below | 1 | low interior sweep | sea green, blue grey; doorway shaft |
| 1.26.6 | Broad upper sanctuary scene, three lower columns | 1 | human-height room view | gold, painted wood; subdued morning |
| 1.26.7 | Tall left lamp and palm scene, three stacked right fields | 1 | close and slightly low interior | deep teal, bronze, blue grey; flame and dawn |

## Three pre-art compositions

1. **Selected: upper paired prose fields and a lower asymmetric pair, with one dominant object-rich interior at lower left and the final reasoning passage at lower right.** Reading order is upper left, upper right, then lower right. The large image is low and left, while text forms a wide top band and a narrower right continuation. At thumbnail scale this L-shaped arrangement differs from 1.26.6's upper image/lower three columns and 1.26.7's full-height left art/right stacked prose. It also differs from 1.26.3's full-width lower panorama. No tall left translation sidebar; this silhouette occurs once in candidate plus five predecessors.
2. Rejected: broad upper temple panorama and three lower columns. This directly repeats 1.26.6, and renders the individual votives too small.
3. Rejected: tall temple portrait at left with three right text fields. This would mirror 1.26.7 at thumbnail scale and blur the comparison between ancient offerings and Persian spoils.

## Content, measured placement and visual direction

Canvas 1800×1600. Header and Acropolis orientation occupy y=16–151. Text fields are `(28,173)–(870,563)`, `(930,173)–(1772,563)`, and `(1230,590)–(1772,1564)`. First field contains the obscured wooden Hermes and Daedalus's folding chair; second the Persian spoils; third Pausanias's distinction between the known death of Masistius and his doubt concerning Mardonius's dagger. The source text is split only before “Among spoils taken” and “I know that Masistius”; joining the fields with spaces equals the complete translation exactly. Main raster `(28,590)–(1200,1564)` has a 1.20:1 aspect ratio. No text is baked into it. Pre-art deterministic Pillow fit passed for all six blocks with 12px padding, glyph-bound checks, and 42px translation type. The right field is tall but not a left sidebar; it gives the skeptical closing argument room to breathe.

The scene is an interpretive study inside the temple of Athena Polias on the Athenian Acropolis, not an exact reconstruction of the lost objects or their display. In a cohesive stone interior, myrtle partly conceals a small ancient wooden Hermes image; a carefully made folding chair and worn Persian-style cavalry breastplate are distinct votives nearby; a sheathed dagger can be present without implying ownership is established. The passage itself questions that claim. Materials should be tactile and historically restrained: carved aged wood, woven seat, dark iron/bronze armour, myrtle foliage, limestone, modest painted details. Avoid legible inscriptions, exact heraldry, ceremonial action, people, extra temples, sea views, and modern objects. Single sophisticated painterly raster, no scenic inset, leader lines, or diagram. Header locates the Acropolis; the image places the objects within a plausible temple interior. Cool soft daylight and a restrained plum, deep green and silvery stone palette move away from 1.26.7's gold lamp, bronze palm, blue-grey dawn and low upward view. Camera becomes a medium eye-level ensemble rather than a close vertical object portrait; balance shifts from a single lamp/palm apparatus to a set of votives. These choices follow the inventory and the disputed dagger's status.

## Review

The first generated component was visually rich but introduced an unrelated distant statue and narrative wall relief. The second image removed those elements and retained the wooden Hermes, chair, breastplate, dagger, myrtle, and temple interior. Both components are preserved. The accepted raster is interpretive and does not assert the exact lost object designs or Mardonius's ownership of the dagger.

The final 1800×1600 PNG was inspected at full size: the text is clear of every border, the passage ID and entire English text appear in source order, and the image has the material finish and visual hierarchy expected beside 1.1.4 and 1.1.5. No baked lettering, visible nudity, generic callout, extraneous temple, modern object, or schematic inset appears. The heading identifies the Athenian Acropolis; the myrtle-obscured wooden Hermes, folding chair, breastplate and dagger each directly support the passage. Art quality, semantic fit, historical restraint, content suitability, orientation, and measured typography **PASS**.

The actual seven-page thumbnail sheet `/tmp/pausanias_1271_comparison.jpg` places this page beside 1.26.2–1.26.7. Its upper two-column text band, lower-left dominant scene, and lower-right reasoning field differ from both immediate predecessors and from 1.26.3's full-width lower panorama. The composition occurs once in the candidate-plus-five window; no tall left translation sidebar. Camera distance, palette, light and balance of objects vary from 1.26.7 for the passage-specific reasons given above. Thumbnail variety **PASS**.

Local bounded build **PASS**: 169 illustrated passages; `1/27/1.html` identifies this as 169 of 169 and links the correct PNG; PDF 170 pages. PDF page 170 was rasterized and visually inspected, with the full text and image intact. Exchange checkpoint and overnight PostgreSQL/site import remain separate.
