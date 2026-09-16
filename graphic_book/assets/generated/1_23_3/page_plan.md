# Page plan — 1.23.3

Run 2026-09-17. Earliest numeric gap verified from local SQLite translations; explicit task instruction governs SQLite use. Preserve complete text and its original place-name spellings.

## Actual history inspected before generation

Quality anchors 1.1.4 and 1.1.5 viewed individually. Six actual preceding PNGs compared in tmp/recent.png and all six page plans read.

|Passage|Composition and prose|Panels|Viewpoint|Palette and lighting|
|---|---|---|---|---|
|1.22.5|Alternating narrative image/prose rows|2|Sea-level ship and over-shoulder watcher|Teal charcoal wine; cloudy|
|1.22.6|Two wide friezes around central reading band|2|Frontal painted studies|Vermilion olive ivory; warm and diffuse|
|1.22.7|Upper reading band above broad island|1|Oblique distant aerial|Indigo celadon purple; maritime overcast|
|1.22.8|Central sculpture between opposed short prose|1|Close rear three-quarter|Ivory charcoal terracotta; reflected light|
|1.23.1|Unequal vertical portrait diptych; upper-right prose|2|Medium portraits|Burgundy malachite; dim window light|
|1.23.2|Broad memorial over two prose columns|1|Low three-quarter object view|Copper blue limestone; bright daylight|

## Three alternatives

1. SELECTED: two alternating narrative rows. Upper-left bronze statue, upper-right first prose; lower-left concluding prose, lower-right deserted Mykalessos. Comparable diagonal image masses, numbered reading order. Connects the honoured figure with the town whose fate Pausanias describes. This family last occurs six predecessors ago (1.22.5), outside candidate-plus-five; once in active six-page window. Neither immediate predecessor matches; no tall left sidebar.
2. Central bronze statue with surrounding text: rejected as too close to 1.22.8 and insufficient attention to the town.
3. Single Boeotian panorama over prose: rejected because it repeats immediate 1.23.2 and the twice-used broad-image/band family.

## Subjects and historical orientation

Upper scene: imagined bronze Diitrephes pierced by arrows, wearing a short chiton and cuirass, on an unlettered stone base in an Acropolis setting. This is sculpture, no flesh injury or battle. Exact appearance is not claimed. Lower scene: imagined deserted inland Boeotian town after its destruction; roofless domestic buildings, weeds and a street toward low hills, no corpses, violence, fire, survivors or sea immediately beside this inland town. No invented event. The empty city visualizes the explicit final argument about failure to recover. Complete passage retains the account of women and children killed. Local captions distinguish Athens/Acropolis from inland Mykalessos near Euripus. No speculative locator required. No unnecessary caveat footer.

## Art choices

Versus prior bright low-view memorial, use near-eye-level closer frontal bronze statue and street-level deep perspective for town. Dominant smoky green/graphite and muted earth with cool grey sky, soft overcast light instead of copper/blue sunshine. Change balance from two pristine sculptures to one damaged-looking sculptural subject plus vacant architecture. These serve the passage's transition from public honour to devastation. Sophisticated painterly raster surfaces, modeled bronze, masonry and plants; no primitives, pseudo-text or nudity. Two substantial panels, no small insets or leaders.

## Pre-art geometry

1600x1600 canvas. Statue (24,100)-(830,785), ratio 1.177:1; town (770,860)-(1576,1510), ratio 1.24:1. No text reserved inside art. First prose (860,195)-(1576,760); second (24,960)-(735,1490), split before The Thracians, in original order. Desired 30px body, minimum 27px; measured actual bounding boxes, 12px padding for every heading/caption/prose. Fail on overflow. Reuse font/measurement helpers only; rectangles newly designed.

## Review pending

Require full-size PNG and seven-page thumbnail comparison; anchor craft, text, semantic fit, suitability, orientation and variety. Build local HTML/PDF, inspect, combined backup push and verify before scoped commit/push. Preserve existing README edit.

## Accepted review

Built-in imagegen produced two scenes and one targeted statue revision. Initial ornate cuirass/greaves read too Roman; revised art removes the figural armour decoration and greaves. All original components retained. Full 1600x1600 revised PNG inspected: textured modeled bronze and arrows, credible stone/plant detail and deep inland street perspective; craft meets 1.1.4/1.1.5. No pseudo-text, exposed anatomy, depicted killings, schematic art or unnecessary leaders. Two local captions give distinct geographic orientation. The deserted town directly supports the last argument; sculpture directly supports the first sentence. Both appearances remain illustrative as documented above.

Eight measured text blocks PASS with 12px padding; complete SQLite translation in order at 30px, smallest auxiliary 25px. Full-size review finds no crowding or clipping. Seven-page thumbnail comparison graphic_book/output/1_23_3-comparison.jpg PASS: diagonal alternating rows differ from immediate diptych 1.23.1 and broad band 1.23.2; same family as 1.22.5 but that page is outside candidate-plus-five. Composition once in active window, no tall sidebar. Cool soft light, frontal statue and street-level architecture distinguish this from the prior bright low-angle bronze memorial. Accepted revised candidate copied unchanged to canonical path.

## Build and backup verification

Requested local HTML/PDF build PASS: 138 illustrations, 139 PDF pages. HTML reader identifies 1.23.3 as 138 of 138 and uses the correct PNG. PDF page 139 rasterized and visually inspected: complete, legible, no clipping. Full create_website.py not run.

Combined backup push and verify PASS: raksasa finished pages, S3 finished pages, component asset cache and manifest match. Three component rasters uploaded; 386 assets verified. Independent local/raksasa/downloaded-S3 finished-page SHA-256 all equal 30be67c4cd75ea6e1f3a3953d867497864d58af9e43cbccd867a4bc563351353.
