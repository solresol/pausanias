# Page plan — 1.23.6

Run 2026-09-20. Earliest numeric missing page verified from the local SQLite translations table, as explicitly requested. Complete translation preserved in original order.

## Actual PNG and plan review before generation

Quality anchors 1.1.4 and 1.1.5 viewed individually. Six preceding actual PNGs compared in /tmp/pausanias-preceding.png; all six plans read.

|Passage|Composition / translation|Panels|Viewpoint|Palette / lighting|
|---|---|---|---|---|
|1.22.8|Central sculpture, opposed short prose|1|Close rear three-quarter|Ivory charcoal terracotta, reflected portico light|
|1.23.1|Unequal portrait diptych, upper-right prose|2|Medium portraits|Burgundy malachite, dim window light|
|1.23.2|Broad memorial above two prose columns|1|Low side view|Copper blue limestone, bright daylight|
|1.23.3|Alternating image/prose and prose/town rows|2|Frontal statue and street depth|Smoky green grey, overcast|
|1.23.4|Central sculptural portrait, opposed prose|1|Close low three-quarter|Bronze umber limestone, warm raking light|
|1.23.5|Broad maritime panorama over two columns|1|Distant ship, sea-level|Petrol blue silver, storm daylight|

## Three materially different alternatives

1. SELECTED: two tall, equal scenic wings flank a central, uninterrupted prose column. Left: close onboard apprehension; right: island shore with the reported tailed inhabitants. The strong vertical art/text/art rhythm puts the account between its two parties. Two full-height scenic masses, no insets. Unlike the previous central single sculpture with outer text and the panorama with lower prose, and unlike the unequal diptych's short upper-right prose and lower portrait. This composition occurs once in candidate-plus-five. No left translation sidebar.
2. Broad shore panorama with lower prose: rejected for repeating immediate 1.23.5 and the twice-used broad-image family.
3. Alternating ship/prose and prose/island rows: rejected as too close to 1.23.3; the central reading column better preserves uninterrupted testimony.

## Subject, meaning and orientation

Pausanias' text is a reported story, not a verified ethnographic description or identified geography. One panel evokes the sailors' reluctance to land, with fully clothed adult sailors and passengers looking towards an offshore island. Other panel evokes tawny-haired mythical inhabitants with long horse-like tails, fully covered by simple woven garments, descending the rocky shore. No sexual assault, touching, abandonment, nudity, injury or racial caricature is depicted. The entire difficult source passage remains verbatim; the art does not recreate its violence. No precise location, real population, recovered vessel or documented costume is asserted. Caption and header attribute the subject to Euphemus and the sailors; no speculative map. No filler insets, labels in art or leader lines.

Art changes versus 1.23.5: close eye-level onboard people and medium shore figures replace a distant seascape; wine-red cloth, dark wood, pale jade water and russet vegetation replace petrol/silver; clear lateral morning light replaces a storm. These make the encounter, rather than navigation, the visual subject. Rich dimensional faces, timber, ropes, rocks and sea; compatible serif typography and restrained ivory paper areas.

## Pre-art measured geometry

1800x1500 page. Left art (24,160)-(585,1380), right art (1215,160)-(1776,1380), each ratio 0.46:1. Central translation (615,305)-(1185,1280), a single uninterrupted block. Desired body 33px, minimum 30px, all blocks 12px padding; local measured headings and captions. No text reserved within either artwork. Renderer reuses only fitting helpers and defines fresh rectangles. Preflight must pass before generation; fail rather than save if any actual bounding box overflows.

## Review pending

Require full-size and seven-page thumbnail comparison, anchor craft, complete exact text and ID, orientation, semantic fit, modesty, no pseudo-text and no clipping. Build and inspect HTML/PDF, backup push/verify, then scoped source commit/push. Preserve pre-existing README edit.

## Accepted visual review

Built-in imagegen supplied two sophisticated raster panels; exact prompts retained. Full 1800x1500 page inspected (viewer display 1728x1440), followed by actual seven-page thumbnail comparison at graphic_book/output/1_23_6-comparison.jpg. Rich cloth, faces, hands, rigging, modeled stone, atmospheric sea and horse-like tails meet the craft anchors. Actual palette is natural blue/jade, linen, wine-red and sunlit russet; lighting is clear and lateral. Shore figures walk/look towards the water rather than depicting the reported attack; the image illustrates the parties to the account, not every narrated action. All figures clothed, no sexual or other violence, pseudo-text, modern fittings, schematic art or misleading callouts. Source attribution and unlocated island context are explicit. No locator or leaders required.

Variety PASS: two equal vertical art wings around a single central prose column appear once in candidate-plus-five and visibly differ from both immediate predecessors, 1.23.4 and 1.23.5. No left sidebar. Close human view, warm clear lighting and wine/linen/russet palette differ from the previous distant storm-sea scene. Text fit PASS: seven measured actual bounding boxes with 12px padding; complete SQLite passage in original order at 32px, auxiliary minimum 28px. Full-size review shows ample clearance, complete ID/text and no clipping. Candidate accepted unchanged.

## Build and backup verification

Requested local HTML/PDF build PASS: 141 illustrated passages and 142 PDF pages. Reader identifies 1.23.6 as 141 of 141, points to the correct PNG; PDF page 142 rasterized and visually inspected with complete art/text and no clipping. Full create_website.py not run.

Combined backup push and verify PASS: raksasa finished-page mirror, S3 finished pages, two new component assets and remote manifest agree; 390 component assets verified. Independent local/raksasa/downloaded-S3 finished-page SHA-256 all equal a70ae74c4b4b9256aae0eb967b5f6f39716d9605c3e2f2afb6f5ed62cbdd471b.
