# Replacement plan — 1.4.1

replacement_status: accepted
Daily run 2026-09-13, revision 20260912T180610Z. Fixed draw 0.09354287015668927; second inspected shuffled candidate, first qualifying. Original SHA-256 69f290dc69646c662a6e373f6130d0a8b5db0af2441ae1ab9108054d799ac633. Previous source preserved in revisions/20260912T180610Z before edits. Canonical original remains in place pending candidate review and verified S3 archive.

## Actual PNG context inspected before art

Contact sheet replacement-1_4_1-context.jpg inspected, all available neighboring plans read. Quality anchors 1.1.4/1.1.5 inspected individually during daily run.

|Passage|Large masses / prose|Panels|Viewpoint|Palette / light|
|---|---|---|---|---|
|1.2.6|Left prose, upper-right Attica, two lower scenes and succession inset|3 + diagram|Elevated landscape|Ochre olive, warm haze|
|1.3.1|Left prose, upper-right city, two lower scenes and locator|3 + locator|Elevated urban|Ochre blue, warm side light|
|1.3.2|Left prose, upper-right Agora, two lower scenes and locator|3 + locator|Elevated urban|Ochre olive, warm daylight|
|1.3.3|Left prose, upper-right stoas, two lower scenes and locator|3 + locator|Elevated architectural|Ochre green, warm daylight|
|1.3.4|One wide cavalry painting above three prose columns|1|Frontal painted battle|Ivory umber, diffuse interior|
|1.3.5|Left prose, upper-right civic scene, two lower scenes and locator|3 + locator|Elevated Agora|Ochre olive, warm daylight|
|1.4.1 original|Full-height left prose, upper-right antique map, two lower scenes|Map + 2 scenes|Map overhead / eye-level studies|Tan olive, diffuse|
|1.4.2 following|Left prose, large right pass, locator and lower captions|1 + locator|Oblique pass|Ochre, warm haze|
|1.4.3 following|Left prose, large right battle shore, locator and lower captions|1 + locator|Elevated shoreline|Ochre olive, warm haze|

## Three alternatives

1. SELECTED: unequal side-by-side scenic diptych above two prose columns and a textual invasion-sequence ribbon. Left 876x685 tidal outer-sea shore, right 654x685 mythic riverbank. Two equally tall but unequal-width image masses, separated by a strong gutter, give the geography/myth opening room without a sidebar. No locator or callout boxes. Distinct from both immediately preceding pages, including 1.3.4's undivided panorama; occurs once in candidate-plus-five context, no copying following pages.
2. Single immersive coastal panorama with lower prose: rejected because it would repeat the overall composition of second predecessor 1.3.4.
3. Central European route map with prose around its edges: rejected because it risks another map/sidebar identity and forces questionable precise identification of Pausanias' northern river geography.

## Art and semantic choices

Generate a purpose-made detailed tidal shore with broad exposed intertidal rocks and pools, distant outer sea and clouded horizon. No modern tower or unrelated Dutch coastal painting. This illustrates the passage's explicit ebbing and flowing rather than claiming a named coast. Do not invent specific sea beasts. Reuse the already generated, inspected Heliades riverbank painting as the second scenic mass; it directly depicts mourning, has rich paint and fully opaque robes. Retain all old components. The old map's confident Eridanos/Rhine identification is not reproduced; caption explicitly disclaims a definite modern river or coastline. Place sequence Illyria, Macedonia, Thessaly, Thermopylae added as exact measured text, not a misleading measured route map. It provides clear historical orientation for the second half.

Relative to 1.3.5, change elevated city to low shore/eye-level myth, architecture to nature, dominant ochre to silver blue/sea green for the larger panel, warm sun to diffuse maritime light. Secondary river art retains warm olive/amber to distinguish story from coast. Parchment only in margins and reading area. No nudity, gore, modern objects, pseudo-text or irrelevant leaders.

## Pre-art text fit

Canvas 1600x1450; scene rectangles (24,90,900,775) and (922,90,1576,775). Caption band y783–880; prose at (24,906,780,1325) and (808,906,1576,1325), followed by invasion sequence and interpretation boundary. Complete SQLite translation split exactly at 'Having assembled'; source has no space after 'peoples.' and exact concatenation of source blocks is checked. No words or punctuation omitted; column break provides reading separation. Eight actual bounds checks with 12px padding passed before generation; body 27/28px, auxiliary minimum 22px; body minimum allowed 25px. Fail on overflow. Renderer defaults to temporary candidate, never canonical replacement.

## Review requirements

Full-size candidate and thumbnail comparison versus original and six preceding/two following pages; reject if diptych is not visibly richer and clearer. Temporary full-book HTML/PDF tree substituting only candidate must pass visual review. Archive original PNG outside canonical images, verify checksum, push/verify assets and download archive from S3 to confirm bytes. Recheck canonical original hash, atomically promote, rebuild and combined backup push/verify, independently compare three page hashes. Only then mark accepted and commit/push scoped sources.

## Candidate acceptance review before promotion

Full-size final PNG and ten-image comparison (original, six predecessors, two following, candidate) reviewed. PASS: unequal side-by-side scenic masses and lower reading band visibly abandon the full-height sidebar; differs from both immediate predecessors and both following pages. Occurs once in candidate-plus-five context. Rich wet rock, kelp, reflections and layered clouds paired with modeled mourning figures and textured paint meet anchors 1.1.4/1.1.5. More legible prose and stronger scenic identity than original map/inset arrangement. Historical orientation preserved by explicit invasion sequence; northern geography kept interpretive.

Initial assembly revealed unsupported arrow glyphs; replaced with measured slash separators. Cropping old wide Heliades art cut figures, so built-in imagegen recomposed that art as a distinct near-square revision, retaining original raster and prompt. Final shows all four fully clothed figures and river without clipped bodies; removes distant chariot spectacle. All eight actual bounding boxes pass with 12px padding; complete source text preserved, body 27/28px, auxiliary minimum 22px. No text collisions, pseudo-writing, unsuitable exposure or primitive/diagrammatic art.

Temporary full-book preview built from a separate tree substituting only the candidate: PASS, 134 illustrated passages / 135 PDF pages. HTML reader correctly identifies 1.4.1 as 17 of 134; PDF page 18 rasterized and visually inspected, complete and unclipped. Canonical original unchanged throughout this review.


## Verified promotion and final backups

Original archived at graphic_book/assets/generated/1_4_1/revisions/20260912T180610Z/previous-page.png alongside previous renderer and plan. Archive SHA-256 69f290dc69646c662a6e373f6130d0a8b5db0af2441ae1ab9108054d799ac633 verified locally and from a downloaded S3 object at assets/generated/1_4_1/revisions/20260912T180610Z/previous-page.png after asset push and verify. Old component art retained. Canonical original rechecked against that hash immediately before atomic promotion.

Reviewed candidate remains at graphic_book/output/replacements/1_4_1/20260912T180610Z/candidate.png. Accepted canonical path graphic_book/images/1/4/1.png. After SHA-256 afc5c660266396dd266a24064a090cc40062fc782aa35d5a7badb10f684a214c independently matches local, raksasa and downloaded-S3 final PNG bytes.

Normal HTML/PDF rebuild PASS: 134 illustrations, 135 pages; reader 17 of 134. Normal PDF page 18 raster is byte-identical to visually reviewed temporary PDF page. Combined backup push and verify PASS: raksasa pages, S3 finished pages, 376 component/archive assets and manifests match. New passage 1.22.7 hash unchanged. Marked accepted only after all these checks passed.
