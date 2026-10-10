# Pausanias 1.26.1 — Olympiodorus and the Mouseion

Run: 2026-10-11. Earliest numeric translated passage lacking a canonical image, verified against local SQLite and image tree: **1.26.1**. Full passage retained in three ordered sentence blocks.

## References and actual recent-page inspection

Approved PNG craft anchors **1.1.4 and 1.1.5** inspected. Detailed raster finish, readable Georgia typography and historical care guide the page; their left sidebar, ochre colouring and inset furniture are not copied. Actual PNGs and plans of six predecessors inspected:

| Passage | Large masses / translation placement | Panels | Viewpoint | Palette / light |
| --- | --- | ---: | --- | --- |
| 1.25.3 | Upper prose, central wide battlefield, three lower prose fields | 1 | low ground-level distant | blue-grey/umber/olive, diffuse post-storm |
| 1.25.4 | Upper broad landscape, two lower prose fields | 1 | high oblique distant | blue-green/violet, cool morning |
| 1.25.5 | Diagonal art/prose checkerboard | 2 | eye-level maritime / oblique harbor | teal/limestone/iron-red, clear and overcast day |
| 1.25.6 | Large upper-left fort, right prelude and shore, two lower prose fields | 2 | low close architecture / distant coast | pine/grey/silver-blue, misty morning |
| 1.25.7 | Two tall art leaves around central continuous prose | 2 | close interior / ground-level street | violet/bronze/blue-grey, side and cloudy light |
| 1.25.8 | Upper broad hill prospect, four lower prose fields | 1 | elevated distant | blue-lilac/silver, dawn |

## Three materially different alternatives

1. **Selected: full-height left narrative scene occupying about two thirds of the page, three ordered prose blocks in the remaining right column.** The close approach from mixed-age Athenian fighters toward the hill fort makes the passage's unusual force and objective legible together. A single continuous scene gives depth; no inset, locator or leader required. Its art-left/prose-right silhouette differs from both immediate predecessors and appears once in candidate plus five. No tall left translation sidebar; this is not a mirror of the old left-sidebar template (no right image/inset stack or callout furniture).
2. **Rejected: broad upper battlefield panorama above lower prose.** Repeats 1.25.8 and the family already reaches its window limit with 1.25.4/1.25.8.
3. **Rejected: central shield/object study surrounded by four prose islands.** A shield is incidental; it would fail to explain the mixed-age force and capture of the Mouseion and introduce unnecessary reading-order complexity.

## Fresh measured geometry and reading order

1800×1600 canvas. Header y=16–135. Main art `(28,151)–(1125,1508)`, aspect 0.8084:1; caption below `(28,1520)–(1125,1580)`. Right prose column x=1170–1772; numbered headings and three sentence blocks progress top to bottom. Blocks are measured before art generation with Pillow, 12px padding, minimum 31px body and 20px auxiliary. Exact source text reconstructed from chunks and from wrapped rendering; actual glyph bounds checked before saving. No text is baked into the art; no reserved text area inside the raster.

## Selected art direction and orientation

One rich painterly early Hellenistic Athenian historical scene. Ground-level three-quarter view uphill toward a modest stone fortified ridge of the Mouseion, southwest of the Acropolis. Older men and young adult men fully clothed in tunics and cloaks, with simple plausible Greek shields and spears, advance together; figures are human-scale and not stylised icons. No identifiable invented portrait of Olympiodorus, gore, precise undocumented battle manoeuvre, later Philopappos monument, medieval crenellations, Roman legion equipment, modern structures or lettering. The composition is an interpretive evocation of the passage's advance and captured hill, not an archaeological reconstruction or an invented additional event. Modest fort occupies upper middle distance; layered paths, limestone outcrops and sparse Mediterranean vegetation support spatial depth. Main palette dry earth, muted terracotta textile, olive and clear pale blue; bright neutral midday light with natural shadows. Fine oil-painted surfaces and atmospheric recession, credible anatomy and material texture, coffee-table-book finish. No scenic inset.

Relative to 1.25.8: elevated distant prospect becomes close ground-level human-scale approach; blue-lilac dawn becomes dry earth/terracotta/olive under neutral midday; terrain/city balance becomes mixed-age people and hill fort. Three art choices change for reasons stated in the passage. Local heading and caption name Athens and Mouseion (Museum hill) southwest of the Acropolis, giving clear geographic/historical orientation without speculative landmark placement. Passage sequence cross-checked with Pausanias's primary text at https://www.theoi.com/Text/Pausanias1B.html; verbatim page translation comes only from SQLite.

## Review

Pending preflight and raster review.

Pre-art preflight **PASS** before commissioning raster: ten measured blocks, all three translation blocks at 39px; auxiliary 24px or greater, 12px padding and actual glyph clearance. Complete 573-character SQLite passage in original order.

Final PNG inspected at full 1800×1600 size and against the six actual preceding PNGs in `tmp/1_26_1_comparison.png`. Art quality, mixed-age semantic fit, Mouseion orientation, historical restraint, suitable clothing, no baked text, no irrelevant callout, text clearance and hierarchy **PASS** against 1.1.4 and 1.1.5. Its one tall left narrative art and three right prose blocks differ from both immediate predecessors; no recent left prose sidebar and this silhouette appears once in candidate plus five. Close ground-level, earth/olive/terracotta midday changes viewpoint, palette, lighting and subject balance from 1.25.8; variety **PASS**. Final deterministic fit **PASS**: ten measured blocks with 12px padding, all translation at 39px and exact 573-character SQLite text in order.

Bounded HTML/PDF build **PASS**: 162 illustrated passages; reader shows 162 of 162 with the new PNG; PDF 163 pages and final page visually reviewed. Combined backup push and verify **PASS**: 449 local assets match the S3 asset manifest; local, S3 and raksasa finished-page trees match. New-page PNG local/raksasa/downloaded-S3 SHA-256 `cfed0d1e42b61d336dd9b2a6f0184f94acf9fdd4b0ca43b16573ef045d41b008`. New component local/downloaded-S3 SHA-256 `a2624b0e98f5cc51bae68df99e17048ecbb5319113d125fe22d5aff9fbfcf0b0`. The combined uploader also saw two local cache assets belonging to the 2026-10-10 unfinished optional replacement; those source files are outside this page's source commit.
