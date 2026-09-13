# Page plan — 1.22.8

Run 2026-09-14. Earliest missing image verified in numeric local SQLite translation order. Full original English preserved; explicit user SQLite instruction governs.

## Actual recent PNG inspection

Contact sheet inspected for six actual predecessors and anchors; anchors 1.1.4 and 1.1.5 also opened individually. Available plans read for 1.22.4–7; none available for 1.22.2/3.

|Passage|Composition / translation|Panels|Viewpoint|Palette / lighting|
|---|---|---|---|---|
|1.22.2|Tall left prose, upper-right courtyard, paired lower insets|3|Medium courtyard|Ochre green / warm daylight|
|1.22.3|Tall left prose, upper-right sanctuary, paired lower insets|3|Medium eye-level|Cream ochre green / warm daylight|
|1.22.4|Broad architecture over two prose columns|1|Low wide uphill|White slate / silver morning|
|1.22.5|Alternating image/prose rows|2|Sea-level ship, over-shoulder watcher|Teal charcoal wine / cloudy|
|1.22.6|Two wide painted friezes around central prose|2|Frontal painting studies|Vermilion olive ivory / warm and diffuse|
|1.22.7|Upper reading band above island panorama|1|Distant oblique aerial|Indigo celadon purple / overcast maritime|

## Three compositions considered before art

1. SELECTED: central vertical sculptural portrait, flanked by short prose blocks at upper left and lower right. Opposed small orientation/attribution blocks complete the page without extra scenic panels. This is an object study surrounded by text, not a broad image and band or full-height translation sidebar. Numbered prose gives reading order.
2. Broad gateway panorama above prose: rejected because it repeats 1.22.7 and 1.22.4 and puts architecture ahead of sculpture.
3. Two narrative rows of sculptor and oracle: rejected because it invents an actual working Socrates and oracle encounter and echoes 1.22.5.

## Pre-art measured layout

1600x1200 canvas. Central art rectangle (430,100,1170,1110), aspect 0.733:1. Complete prose split before 'That he', first rectangle (24,155,410,690), second (1190,540,1576,1080). Full passage fits at 28px, minimum allowed 25px, auxiliary minimum used 23px. Nine actual bounding-box checks pass with 12px padding. No baked-in text. Renderer reuses measured helpers but defines new geometry.

## Subject and historical orientation

Hermes herm viewed from behind, head in three-quarter profile, beside three fully draped Graces in a sculptural relief, within an evocative gateway setting. Rear view avoids exposing herm anatomy without inventing modern clothing on its shaft. No living Socrates portrait or literal oracle event. Exact attribution remains in the verbatim passage and is identified as Pausanias' report. Appearances and arrangement are explicitly illustrative, not recovered originals.

Primary context consulted 2026-09-14: Acropolis Museum https://www.theacropolismuseum.gr/en/node/1431 identifies a Hermes bust on a herm at the Propylaia; https://www.theacropolismuseum.gr/en/relief-graces notes Graces worship near the Propylaia but alternative identifications of its particular relief. Do not claim to reproduce that disputed relief or settle sculptural authorship. Passage is the narrative authority.

Change from 1.22.7: close object view rather than distant aerial; rear three-quarter angle rather than flying overview; charcoal/ivory/soft terracotta rather than maritime blues; raking reflected portico light rather than overcast sea. Sculpture and architectural shadow replace landscape and airborne person. Rich modeled marble, subtle age, drapery and carved hair; no schematic construction. One scenic panel, no locator or leaders needed. Athens / Acropolis entrance stated locally.

## Review required

Full-size and seven-page thumbnail comparison. Central portrait with opposed short text blocks occurs once in candidate-plus-five window; no full-height sidebar and no match to either immediate predecessor. Check actual art against anchors, text clearance, complete translation and ID, historical orientation and modesty. Build HTML/PDF and inspect before backup verification and scoped source commit/push. Existing README edit preserved.

## Accepted visual review

Built-in imagegen supplied one component. Full-size 1600x1200 candidate inspected: richly modeled marble curls, carved folds, dimensional portico and warm reflected highlights; no schematic or primitive scenic art. Hermes is rear-view and Graces fully draped. Interpretive winged headgear and relief arrangement are not asserted as recovered original details. Caption makes the reconstruction boundary explicit. No pseudo-text, unnecessary leaders, nudity or crowded type. Geographic orientation and complete passage ID/text present.

Actual seven-page thumbnail comparison at graphic_book/output/1_22_8-comparison.jpg PASS: dominant central vertical object mass with opposed short prose blocks visibly differs from both immediate predecessors. This layout occurs once in candidate-plus-five window. Left prose occupies only the upper portion of the page, not a tall sidebar. No boxed full-height left mass or large right landscape. Close rear object view, ivory/charcoal palette and raking portico illumination vary from prior aerial maritime scene. Craft checked against 1.1.4/1.1.5. Nine measured actual text bounds PASS, 12px padding; exact SQLite text in original order at 28px, auxiliary minimum 23px. Candidate accepted.

## Build and backup verification

Requested local HTML/PDF build PASS: 135 illustrations, 136 PDF pages. HTML identifies 1.22.8 as 135 of 135 with correct image. PDF page 136 rasterized and visually inspected: full art, readable type, no clipping. Full create_website.py not run.

Combined backup push and verify PASS: raksasa image mirror, S3 finished pages, new component and asset manifest agree. One changed component uploaded; all 377 assets match the manifest. Independent local/raksasa/downloaded-S3 finished-page SHA-256: `3bef8c9b88457dc1836aaef68e5fd792c1f0359834be113199c91880c5fe2712`.
