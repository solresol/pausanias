# Page plan — 1.22.5

2026-09-11 daily run. Earliest missing translated passage verified by numeric sorting of local SQLite translations. User's explicit SQLite instruction takes precedence over the general PostgreSQL guidance. Complete original English loaded unchanged by renderer.

## Six preceding accepted pages: actual PNG comparison

Viewed actual PNGs together at thumbnail scale; quality anchors 1.1.4 and 1.1.5 also inspected individually. Available plans read for 1.21.6, 1.21.7, 1.22.1 and 1.22.4; no plans present for 1.22.2 or 1.22.3.

| Passage | Composition and translation | Scenic panels | Viewpoint | Palette and lighting |
|---|---|---|---|---|
|1.21.6|Tall left translation; upper-right workshop; two lower insets plus locator|3 + locator|Close angled workbench|Umber/tan; warm interior|
|1.21.7|Tall left translation; upper-right dedication; two lower studies|3|Close object/eye-level grove|Olive/tan; filtered warm daylight|
|1.22.1|Tall left translation; upper-right ascent; two lower insets|3|Distant oblique uphill|Ochre/olive; warm side light|
|1.22.2|Tall left translation; upper-right courtyard; two lower insets|3|Medium courtyard|Ochre/green; warm daylight|
|1.22.3|Tall left translation; upper-right sanctuary; two lower insets|3|Medium eye-level|Cream/ochre/green; warm daylight|
|1.22.4|Broad architectural panorama over two bottom translation columns|1|Low uphill wide approach|White/slate blue; silver morning|

## Three materially different alternatives

1. SELECTED: two alternating narrative rows. Upper-left broad ship scene and upper-right first translation; lower-left concluding translation and lower-right Aegeus scene. Two comparable scenic masses form a diagonal, not a full-height sidebar or a single panorama over text. Numbered headings make reading order unambiguous.
2. Central black-sail object study with four surrounding prose blocks. Rejected: weakens the human consequence and fragments a short passage.
3. Immersive full-bleed seascape with top and bottom reserved prose zones. Rejected: too close in large-mass structure to the immediate predecessor's panorama/lower text band and harder to preserve generous text contrast.

## Geometry and text preflight before art

Canvas 1600x1280. Main art (24,104)-(956,662), second art (732,718)-(1576,1218). Translation 1 (990,192)-(1576,642); translation 2 (24,820)-(698,1164), split exactly before 'However,'. Reading order upper row then lower row. Original text concatenation checked against SQLite. All 9 actual text bounding boxes pass 12px padding, body 28px (minimum acceptable 25px), smallest auxiliary 19px. No optional callouts or locator insets needed.

## Subjects, orientation and art choices

Pausanias' supplied translation is the narrative authority: a black-sailed ship returns from Crete; Theseus forgot the promised white sail; Aegeus mistakes the signal; Athens has a Heroön of Aegeus. Show the return and Aegeus watching BEFORE the fatal act, not a fall or invented burial. Do not invent a form for the Heroön. Local orientation explicitly names Athens and return from Crete. Viewpoint is interpretive, not a claim that the sea lies directly below the Acropolis. Aegeus may be shown on high rocky ground overlooking the distant Attic coastal plain and sea, without later classical monuments or a sheer sea cliff.

Change from preceding architecture page: camera distance to close ship/medium human portrait; angle to sea-level and over-shoulder; palette to deep teal/charcoal with muted wine cloth; lighting to diffuse clouded daylight; subject balance to ship and watcher instead of architecture. Changes emphasize the dark signal and human misunderstanding. Two text-free raster illustrations; exact copy rendered locally. Figures fully clothed; no nudity, gore, pseudo-text, modern rigging or identifiable invented landmarks.

## Planned review

Full-size and seven-page thumbnail review against six predecessors, with anchors for craft. Selected composition occurs once in candidate-plus-five window; no tall left sidebar; unlike both immediate predecessors. Validate semantic fit, geographic boundary, text clearance, suitability and raster richness. Build and inspect HTML/PDF; combined backup push/verify before scoped commit/push. Preserve existing README modification.

## Accepted visual review

Built-in imagegen generated both scenes. Initial ship background incorrectly added a later classical temple; a targeted imagegen edit removed the buildings and replaced the shore with unbuilt hills. Initial and corrected components retained. Aegeus scene needed no revision.

Full-size 1600x1280 candidate inspected: rich sail weave, wood, sea, cloth and layered landscape; no crude or diagrammatic scenic art. Both scenes directly depict the passage, including the black sail, without relying on captions. Fully clothed figures, no bodily exposure or fatal act. No pseudo-text or unnecessary leaders. Athens/Crete orientation and interpretive boundary present; no invented Heroön architecture. Typography clear and uncrowded, no border collisions.

Seven-page thumbnail comparison against 1.21.6, 1.21.7, 1.22.1, 1.22.2, 1.22.3, 1.22.4: PASS. Two alternating narrative rows visibly differ from both preceding layouts; composition occurs once in candidate-plus-five window. No tall left sidebar. Camera distance, angle, palette and subject balance vary from 1.22.4; cloudy maritime light replaces its clear architectural morning. Richness meets craft anchors 1.1.4 and 1.1.5. Contact sheet retained locally at graphic_book/output/1_22_5-comparison.jpg.

Text fit PASS: all 9 actual bounding-box checks within 12px padding, both complete verbatim SQLite blocks at 28px in original order; smallest auxiliary 19px. Candidate accepted and copied unchanged into canonical image tree.

## Build and backup verification

Local graphic-book build PASS: 132 illustrated passages, 133 PDF pages. HTML reader identifies 1.22.5 as 132 of 132 and uses its correct image. Rasterized PDF page 133 inspected: full page present, type clear, no clipping. Full create_website.py was not run.

Combined backup push and verify PASS: raksasa finished-page mirror, S3 finished pages, component asset cache and manifest agree. Three components uploaded (Aegeus, original ship, corrected ship); 364 total assets verified against the manifest. Independent local/raksasa/downloaded-S3 finished-page SHA-256 all equal `2fb805843c814e43719e6b108b4779e55bb49ea786dc87486288219bd938283a`.
