# Page plan — 1.23.5

Run 2026-09-19. Earliest missing numeric image verified against local SQLite translations, as explicitly requested. Complete passage retained in original order.

## Pre-art actual PNG and plan comparison

Anchors 1.1.4 and 1.1.5 inspected individually for craft. Six preceding actual PNGs inspected in /tmp/pausanias-history.png; all six page plans read.

|Passage|Composition / prose placement|Panels|Viewpoint|Palette / lighting|
|---|---|---|---|---|
|1.22.7|Broad island below upper reading band|1|Distant oblique aerial|Indigo celadon; overcast|
|1.22.8|Central sculpture with opposed short prose|1|Close rear three-quarter|Ivory charcoal terracotta; reflected light|
|1.23.1|Unequal portrait diptych; upper-right prose|2|Medium human portraits|Burgundy malachite; dim window light|
|1.23.2|Broad memorial above two prose columns|1|Low side object view|Copper blue limestone; bright daylight|
|1.23.3|Alternating image/prose rows|2|Frontal statue and street depth|Smoky green grey; overcast|
|1.23.4|Central sculpture with opposed prose|1|Close low three-quarter|Bronze umber limestone; warm raking light|

## Three alternatives

1. SELECTED: broad maritime panorama over two numbered reading columns. The voyage occupies the principal art; the first column preserves the Athenian stone and Sileni discussion, the second Euphemus' account. Same broad-image/band family as 1.23.2: twice in candidate-plus-five, with 1.22.7 outside that window. Neither immediate predecessor matches. No tall translation sidebar.
2. Central stone surrounded by text: rejected as repeating immediate 1.23.4 and giving an unremarkable stone more visual weight than the lengthy seafaring report.
3. Two alternating rows, Silenus and the voyage: rejected as repeating 1.23.3 and unnecessarily literalising a reported mythic visit.

## Subject and orientation

One sophisticated raster scene: a small ancient Mediterranean merchant vessel being driven through rough open water, with distant uninhabited rocky islands. Sea-level broad view, boat at left third, wind-filled reduced square sail, fully clothed sailors, dimensional water and atmospheric islands. No modern vessel, named island, mapped coordinates, shipwreck, monsters, encounter or invented violence. The distant islands are illustrative, not identified geography. No depiction of the passage's purported island inhabitants; the complete reported account remains verbatim. No claim to reconstruct a specific surviving ship or the voyage's route. Athens/Acropolis locates Pausanias' starting observation; Italy is the reported intended destination, not the location shown. No map or filler inset needed. Caption attributes the report to Euphemus.

Compared with 1.23.4: distant vessel/landscape rather than close sculpture; horizontal sea-level rather than upward portico view; deep petrol blue and silver rather than bronze/umber; diffuse storm daylight rather than warm raking light. These express the explicitly reported wind-driven displacement. Art contains no text or reserved text area; all typography outside art locally measured.

## Measured pre-art layout

Canvas 1800x1500. Art (24,140)-(1776,940), aspect 2.19:1. Two prose rectangles (24,1105)-(866,1476) and (920,1105)-(1776,1476), reading left then right, split exactly before Euphemus. Eight actual bounding boxes pass with 12px padding. Complete SQLite passage at 32px (minimum 29px); smallest auxiliary 28px. Exact normalized reconstruction asserted. Fail before saving on overflow. Shared font/measurement helpers reused; page rectangles freshly designed.

## Review pending

Full-size and thumbnail review against six predecessors, craft anchors, semantic fit, historical orientation, modesty, no pseudo-text, measured text clearance. Build and inspect local HTML/PDF, then combined backup push/verify before source commit/push. Existing README change excluded.

## Accepted image review

Full-size 1800x1500 candidate inspected (viewer displayed at 1728x1440); finely modeled waves, dimensional ship and sail, coherent atmospheric islands and silver cloud detail meet the craft anchors 1.1.4/1.1.5. Actual sail is fully set rather than visibly reduced; this does not contradict the passage. No invented wreck, pseudo-text, nude figures, schematic art, misleading callouts or modern fittings. The maritime scene directly illustrates the reported voyage, with clear attribution and geographic orientation outside the art. Original exact passage and ID present. Eight measured blocks pass with 12px padding, body 32px, auxiliary minimum 28px; no visual crowding or clipping.

Actual seven-page thumbnail comparison graphic_book/output/1_23_5-comparison.jpg PASS: broad image with lower prose differs from immediate alternating-row 1.23.3 and central-sculpture 1.23.4. Broad-image/band family occurs twice in candidate-plus-five (with 1.23.2). 1.22.7 is outside that counting window. No tall sidebar. Distance, angle, cool palette, storm light and landscape emphasis vary from preceding warm sculpture. Accepted candidate copied unchanged to canonical image path.

## Build and backup verification

Requested local graphic-book HTML/PDF build PASS: 140 illustrations, 141 PDF pages. Reader identifies 1.23.5 as 140 of 140 and uses correct image. Rasterized PDF page 141 visually reviewed: complete, legible, unclipped. Full create_website.py not run.

Combined backup push and verify PASS: raksasa finished-page mirror, S3 finished pages, new component raster and 388-asset manifest agree. Independent local/raksasa/downloaded-S3 finished-page SHA-256: 3137620aa2c27cea4db30ad219d05d2e79c1c2a8a59bd28781be77fcb62e2111.
