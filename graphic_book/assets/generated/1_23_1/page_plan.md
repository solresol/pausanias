# Page plan — 1.23.1

Daily run 2026-09-15. Earliest missing numeric passage checked against local SQLite translations (explicit user instruction governs). Full verbatim passage loaded from SQLite, kept as one block in original order.

## Actual recent PNG inspection

Six actual PNGs inspected in /tmp/pausanias-history.jpg before generation, with available plans for 1.22.4–8; no plan for 1.22.3. Quality anchors 1.1.4 and 1.1.5 opened individually for finish, not layout.

|Passage|Composition / translation placement|Scenic panels|Viewpoint|Palette / lighting|
|---|---|---|---|---|
|1.22.3|Tall left text, upper-right sanctuary, paired lower insets|3|Medium eye-level|Cream ochre green / warm daylight|
|1.22.4|Broad architecture above two prose columns|1|Low wide uphill|White slate / bright silver morning|
|1.22.5|Alternating image/prose rows|2|Sea-level ship and over-shoulder watcher|Teal charcoal wine / cloudy daylight|
|1.22.6|Two wide friezes enclosing central prose band|2|Frontal painted studies|Vermilion olive ivory / warm and diffuse|
|1.22.7|Upper reading band above one island panorama|1|Distant oblique aerial|Indigo celadon purple / overcast maritime|
|1.22.8|Central vertical sculpture with opposed short prose blocks|1|Close rear three-quarter|Ivory charcoal terracotta / reflected portico light|

## Three alternatives before art

1. SELECTED: unequal portrait diptych. Tall Hippias portrait occupies the left 56% almost full height; complete translation fills the upper right; smaller Leaena portrait fills the lower right. Two unequal adjacent image masses, one compact reading block, no tall translation sidebar. This is not a mirrored old sidebar: the right is split roughly equally between prose and substantial scenic portrait, with no lower pair of insets. Unlike 1.22.8's central narrow sculpture with prose on both sides and 1.22.7's horizontal bands. Composition appears once in candidate-plus-five. Also unlike the comparable diagonal narrative panels of 1.22.5.
2. Single civic panorama with translation underneath: rejected as third broad-image/band composition in candidate-plus-five, and less direct about the personal turn to anger.
3. Seven sages in a ring around a text center: rejected because the passage supplies neither a full list nor reliable likenesses and this would invent a definitive council scene.

## Subjects and orientation

Pausanias' translation supplies all narrative facts. Imagined fully clothed portraits of Hippias and Leaena, shown separately, do not assert a documented encounter, punishment, or known likeness. Hippias' tense bearing interprets the explicit turn to rage; Leaena's dignified portrait foregrounds the named woman without picturing torture or inventing its details. Do not show Hipparchus' murder, a lion monument from the next passage, a seven-sage meeting, or invented specific governance acts. Athens and the rule of Hippias are stated locally. Restrained sixth-century BCE Athenian interiors, no later Acropolis monuments, crowns or Roman costume. No external reconstruction claim needed; all appearances explicitly imaginative.

Art choices versus 1.22.8: living human figures instead of carved objects; frontal/three-quarter faces instead of rear sculpture; deep malachite and muted burgundy instead of ivory/charcoal; low diffuse window light instead of raking portico illumination. These emphasize character and the contrast between power and its target. Rich modeled faces, cloth and rough plaster; two raster panels, no locator or leaders. No nudity or violence.

## Measured preflight before commission

Canvas 1600x1400. Tall art (24,100)-(900,1290), aspect 0.736:1. Smaller portrait (940,720)-(1576,1210), aspect 1.298:1. No reserved text inside either art image. Complete translation (940,205)-(1576,660), single obvious reading order. All eight actual bounding-box checks PASS with 12px padding; body 29px, minimum allowed 26px; smallest auxiliary 23px. Exact passage equivalence asserted after wrapping. Fail rather than save overflow. Header, labels and captions all locally measured and rendered.

## Review gate pending

Inspect full-size candidate and compare all six actual predecessors at thumbnail scale; assess anchor craft, orientation, semantic fit, suitable clothing, labels and exact text. No sidebar; chosen layout once in candidate-plus-five; both immediate predecessor arrangements avoided. Then build and inspect HTML/PDF, backup push and verify before scoped commit/push. Existing README change excluded.

## Accepted full-size and thumbnail review

Built-in imagegen supplied two components, prompts retained alongside this plan. Full 1600x1400 PNG inspected: rich naturalistic cloth, modeled faces/hands and textured interiors meet the craft anchors. Both figures fully clothed, no violence or pseudo-writing. Distant architecture is incidental illustrative scenery, not an asserted monument identification. Separate portraits support the passage's ruler/target turn without inventing an encounter. Athens and Hippias' rule are explicit; portrait interpretation is disclosed. No leaders or locator needed. Every text block has generous clearance; complete verbatim passage and ID present.

Actual seven-page comparison at graphic_book/output/1_23_1-comparison.jpg PASS: unequal vertical diptych with compact upper-right prose differs from both immediate predecessors and appears once in candidate-plus-five. Not a mirrored full-height sidebar: the right contains a substantial second portrait below a short reading area. Human figures, frontal faces, burgundy/malachite and diffuse interior light vary from the preceding rear marble study. Eight measured text boxes PASS with 12px padding; body 29px, smallest auxiliary 23px. Accepted candidate copied unchanged to canonical path.

## Build and backup verification

Requested local HTML/PDF build PASS: 136 illustrated passages, 137 PDF pages. HTML identifies 1.23.1 as 136 of 136 and references the correct PNG. PDF page 137 rasterized and visually inspected: full art and readable text, no clipping. Full create_website.py not run.

Combined backup push and verify PASS: raksasa finished-page mirror, S3 pages, component cache and remote manifest agree. Two new components uploaded; all 379 assets match the manifest. Independent local/raksasa/downloaded-S3 page SHA-256: f4a412269450dea9d235c62e5e9eeb8bd110c6be7e9ac351b3b5cd54206e5dc4. Initial sandbox DNS failure resolved by authorized network execution; final backup commands exited successfully.
