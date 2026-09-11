# Page plan — 1.22.6

Run 2026-09-12. Earliest missing image selected in numeric local SQLite translation order. Exact complete English preserved including final semicolon. User SQLite instruction governs this run.

## Actual six-page inspection before art

Approved craft anchors 1.1.4 and 1.1.5 inspected individually. Actual six preceding PNGs inspected, with available plans (1.22.2 and 1.22.3 have no plans).

|Passage|Composition / translation placement|Panels|Viewpoint|Palette / lighting|
|---|---|---|---|---|
|1.21.7|Tall left text, right dedication, paired lower studies|3|Close object / eye-level grove|Olive tan / filtered daylight|
|1.22.1|Tall left text, right ascent, paired lower insets|3|Distant oblique uphill|Ochre olive / warm side light|
|1.22.2|Tall left text, right courtyard, paired lower insets|3|Medium courtyard|Ochre green / warm daylight|
|1.22.3|Tall left text, right sanctuary, paired lower insets|3|Medium eye-level|Cream ochre green / warm daylight|
|1.22.4|Single broad architecture above two prose columns|1|Low wide uphill|White slate / bright silver morning|
|1.22.5|Two alternating image/text narrative rows|2|Sea-level ship and over-shoulder watcher|Teal charcoal wine / cloudy daylight|

## Three alternatives

1. SELECTED: two full-width painted friezes enclosing a central two-column reading band. Upper scene is Diomedes carrying Athena's image from Troy; lower scene is Odysseus encountering Nausicaa's laundry party. Emphasizes paintings as objects of viewing and frames Pausanias' critical discussion between two surviving subjects in his account.
2. Gallery interior with central perspective and lower prose: rejected because a single broad image over text repeats 1.22.4 and invents too much gallery architecture.
3. Six small painting vignettes with short interleaved prose: rejected because it crowds the full translation and encourages abbreviated or unnecessarily violent illustrations.

## Art, orientation and variety

Two panoramic frontal painted studies, with mineral red, ivory, muted malachite and carbon outlines; even raking gallery light on pigment and fine plaster texture. Rich painterly modelling, expressive fully clothed figures and textured landscapes within ancient-inspired painting. Not flat vector silhouettes or a purported exact reconstruction of Polygnotus. Compared to 1.22.5 change angle (frontal painted surface), palette (mineral red/ivory/green), lighting (even raking surface illumination), subject balance (painted figures/objects instead of maritime landscape). These choices serve a passage about looking at paintings.

Athens and left side of the Propylaia stated explicitly in local orientation. Troy caption identifies the upper subject. No invented building plan, no locator required. Paintings' appearances expressly unknown. No sacrifice or killings pictured; all translated references remain intact. Odysseus wears a modest opaque cloak; no nudity anywhere.

## Pre-art layout

Final canvas 1600x1610. Art rectangles (24,90)-(1576,608) and (24,1020)-(1576,1538). Full exact prose flows left to right in middle band, split before 'Homer did well'. Body minimum 25px; measured all blocks with 12px padding and actual bounding boxes. Titles and captions deterministic. Fit must pass before art generation. This image/text/image horizontal stacking is neither a mirrored sidebar nor the prior alternating grid, and differs from both immediate predecessors. Selected composition occurs once in candidate plus five predecessors; no left sidebar.


## Accepted full-size and thumbnail review

Built-in imagegen used. Both initial rasters retained alongside corrected versions. Diomedes initially had an invented burning-city backdrop and soldiers; removed them, the gateway lion and the helmet crop. Nausicaa initially had a prominent classical temple; removed all background buildings. Final painted studies are explicitly interpretive, not claims about lost originals. Final actual palette is vermilion/bronze/ivory above and olive/ivory below; fine pigment surface, modeled faces and drapery, detailed terrain and water meet anchors 1.1.4/1.1.5. Raking surface texture distinguishes the art from the prior maritime scenes; the upper picture contains warm sunset within the painting rather than the planned uniform illumination.

First assembled candidate had excess whitespace below prose; reduced middle-band height by 230px. Final full-size 1600x1610 PNG and seven-page thumbnail sheet reviewed. PASS: two full-width image masses separated by central prose differ from both immediate predecessors and occur once in candidate-plus-five window; no sidebar. Front-facing painted studies, close object emphasis and vermilion/olive palette vary from prior teal maritime / over-shoulder page. Both scenes semantically specific, all figures modestly clothed, no depicted violence or pseudo-text, no irrelevant leaders. Athens/Propylaia location and Troy subject labeled. Rich raster finish passes craft comparison. Complete translation including trailing semicolon preserved in original order. All seven actual bounding-box checks pass 12px padding; body 27px, smallest auxiliary 21px. No crowded or clipped text. Review sheet: graphic_book/output/1_22_6-comparison.jpg. Reviewed candidate copied unchanged to canonical path.

## Build and backup verification

Local requested build PASS: 133 illustrated passages and 134 PDF pages. HTML identifies 1.22.6 as 133 of 133 and references the correct image. Rasterized PDF page 134 visually inspected: complete art, clear text and no clipping. Full create_website.py was not run.

Combined backup push and verify PASS: raksasa finished-page mirror, S3 finished page, all four initial/corrected component assets and checksum manifest agree. 370 component assets verified locally; four new components uploaded. Independent local, raksasa and downloaded-S3 finished-page SHA-256 all equal `29a0a3f87ae8d9db0267a641b1b20c866c6f0f0930a80434b56bb85f09cc07d7`.
