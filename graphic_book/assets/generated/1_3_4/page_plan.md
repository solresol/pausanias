# Replacement page plan — 1.3.4

replacement_status: accepted
Run: 20260910T180903Z, daily report 2026-09-11-generation.md. Trigger draw 0.041928847856475326. First shuffled eligible candidate visually confirmed repetitive; no second target will be attempted. Original SHA-256 dac90939ab52eab0b0cb8f938f448c1da92792ff34dd9d047c06594355dde640. Previous renderer and plan preserved in revisions/20260910T180903Z; original PNG remains canonical during work.

## Actual neighboring PNGs and plans inspected

|Passage|Large masses and translation placement|Panels|Viewpoint|Palette/light|
|---|---|---|---|---|
|1.2.4|Tall left text; upper-right city; lower locator + two scenic insets|3 + locator|Elevated approach|Ochre/olive, warm daylight|
|1.2.5|Tall left text; upper-right stoas; lower locator + two scenic insets|3 + locator|Elevated urban view|Olive/tan, warm daylight|
|1.2.6|Tall left text; upper-right Attic panorama; two lower scenes + succession diagram|3 + diagram|Elevated landscape|Ochre/olive, warm haze|
|1.3.1|Tall left text; upper-right city; lower locator + two scenic insets|3 + locator|Elevated city, close roof study|Ochre/blue, warm side light|
|1.3.2|Tall left text; upper-right Agora; lower locator + two scenic insets|3 + locator|Elevated Agora|Ochre/olive, warm daylight|
|1.3.3|Tall left text; upper-right Agora; lower locator + two scenic insets|3 + locator|Elevated porticoes|Ochre/green, warm daylight|
|1.3.4 original|Tall left text; large right wall painting; lower flat locator, paired statue study and captions|1 + paired study + locator|Frontal painting|Ochre/brown, warm interior|
|1.3.5 following|Tall left text; upper-right civic scene; lower locator + two scenic insets|3 + locator|Elevated Agora|Ochre/olive, warm daylight|
|1.4.1 following|Tall left text; large upper-right antique map; two lower scenes|map + 2 scenes|Map overhead; eye-level insets|Tan/olive, diffuse light|

Actual nine-page contact sheet inspected, not inferred from plans. Available plans read (none for 1.2.5). Approved craft anchors 1.1.4 and 1.1.5 inspected this run.

## Three alternatives

1. SELECTED: one full-width monumental wall-painting portrait above three generous prose columns. Main subject remains Euphranor's cavalry engagement, now without labels obscuring riders or a schematic locator. Much larger legible text. Historical orientation explicitly connects Mantineia to its representation in the Athenian Agora.
2. Asymmetric diptych of cavalry painting and Apollo sanctuary, with prose across a middle band. Rejected: adds reconstructed sanctuary architecture and divides the lost painting's impact.
3. Central Apollo object study surrounded by text and a narrow cavalry strip. Rejected: the longer first half concerns the painting; reversing hierarchy would weaken its emphasis.

## Geometry, fit, and meaning

1800x1440 canvas. Art (24,100)-(1776,920), aspect ratio 2.14:1. Three translation columns at (30,1008)-(587,1356), (622,1008)-(1179,1356), (1214,1008)-(1771,1356); left-to-right reading order. The entire verbatim SQLite passage is split by word count into balanced columns and rejoined exactly. Preflight before commissioning art: all seven actual text bounding boxes pass 12px padding, body 26px (minimum 24px), smallest auxiliary 21px.

Art is an explicitly interpretive reconstruction of a lost painting seen within a portico. Cavalry visibly engage in the wall painting, not a literal battle inside Athens. Avoid identifying individual painted figures with speculative exact portraits. Apollo's three statues and reported plague tradition remain in the full translation; no invented temple image is needed. No locator/insets/leaders. Local heading locates Athenian Agora and explains the Mantineia subject. No claim to recovered ancient pigment, original composition or archaeological measurements.

Compared with 1.3.3 change: elevated city to close eye-level interior, architecture/crowds to cavalry artwork, ochre/green to slate blue, ivory and muted russet, warm side light to cool indirect portico daylight. These emphasize public historical painting as the subject. Composition unlike either preceding or following page, occurs once in candidate-plus-five window, no tall left translation sidebar.

## Review and promotion gates

Candidate output graphic_book/output/replacements/1_3_4/20260910T180903Z/candidate.png. Compare full-size and thumbnails with original, six predecessors and two successors. Require improvement and measured fit. Build and review temporary complete image-tree HTML/PDF before promotion. Archive original PNG beside previous source files, checksum it, upload/verify assets, download its S3 key and compare checksum. Recheck canonical original then atomic promotion. Normal rebuild, combined backup verification, and independent local/raksasa/S3 new-image hashes before accepted status and scoped commit/push.

## Final acceptance and archive verification

Full-size candidate and contact sheet reviewed against original, six preceding pages and two following pages: PASS. Wide painted wall and three lower prose columns abandon the old sidebar and remove flat locator/crowded callouts. The cavalry painting is unobscured, cooler, finely textured and directly relevant; type is substantially larger. Both art and text hierarchy improve the page. All figures clothed, no graphic injury or pseudo-writing; decorative meander is ornament. The frame and floor establish a painting in a portico rather than an actual battle in Athens. The orientation heading and complete text preserve the Mantineia/Athens distinction. No exact portrait identification is asserted. Composition occurs once in the local candidate-plus-five window and copies neither following page. Craft anchors 1.1.4 and 1.1.5 remain the standard.

All seven actual bounding-box checks PASS, 12px padding, complete SQLite translation at 26px, minimum auxiliary 21px. Temporary full-tree HTML/PDF build PASS: 132 illustrations, 133 PDF pages. Reader 15 of 132 uses candidate bytes; PDF page 16 visually reviewed complete and unclipped. Temporary preview substituted only target image; all 131 other images linked unchanged.

Original archived at graphic_book/assets/generated/1_3_4/revisions/20260910T180903Z/previous-page.png with previous-renderer.py and previous-page-plan.md alongside. Before SHA-256: dac90939ab52eab0b0cb8f938f448c1da92792ff34dd9d047c06594355dde640. Asset push/verify succeeded and downloaded S3 archive matched that hash. S3 key: assets/generated/1_3_4/revisions/20260910T180903Z/previous-page.png in pausanias-graphic-book-assets-849621205733. Old component art retained.

Canonical original rechecked immediately before atomic replacement. Reviewed candidate retained at graphic_book/output/replacements/1_3_4/20260910T180903Z/candidate.png. After image: graphic_book/images/1/3/4.png. After SHA-256: a1b702486fd69b76d3279d29e305ca15625daee00bc452c8e50e93ef8bb18d91.

Normal HTML/PDF rebuild PASS, 132 illustrations and 133 PDF pages; final PDF page 16 visually checked. Combined backup push/verify PASS: raksasa finished pages, S3 finished pages/assets and 366-entry manifest agree. Independent local/raksasa/downloaded-S3 replacement PNG hashes all equal the after hash. Accepted only after all these checks. Source commit/push is recorded by the automation run memory and final response.
