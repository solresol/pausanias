# Page plan — 1.23.2

Run 2026-09-16. Earliest numeric missing image selected from local SQLite translations, as explicitly requested. Original complete prose loaded by renderer in original order.

## Actual PNG history reviewed before art

Anchors 1.1.4 and 1.1.5 inspected individually for raster craft, typography and finish. All six predecessors compared in tmp/recent-pages.png and available plans read.

|Passage|Composition / translation|Scenic panels|Viewpoint|Palette / lighting|
|---|---|---|---|---|
|1.22.4|Broad architecture above two lower prose columns|1|Low wide uphill|White/slate, silver daylight|
|1.22.5|Two alternating image/text rows|2|Sea-level ship, over-shoulder watcher|Teal/charcoal/wine, clouded daylight|
|1.22.6|Two painted friezes enclosing central prose|2|Frontal painting studies|Mineral red/olive/ivory, diffuse warm light|
|1.22.7|Upper two-column reading band above panorama|1|Oblique aerial, distant island|Indigo/celadon/purple, maritime overcast|
|1.22.8|Central vertical sculpture, opposed short prose blocks|1|Close rear three-quarter|Ivory/charcoal/terracotta, reflected portico light|
|1.23.1|Unequal vertical portrait diptych, compact upper-right prose|2|Medium frontal and three-quarter portraits|Burgundy/malachite, dim window light|

## Three alternatives

1. SELECTED: broad low-view bronze memorial scene above two prose columns. Lioness dominates horizontally, with the draped Aphrodite beside it, smaller in perspective. One scenic panel, no inset. Full translation sits below in original order. This directly links remembrance and the neighbouring dedication, lets the bronze animal read instantly, and keeps the long prose spacious.
2. Central tall lioness study surrounded by prose: rejected because it repeats 1.22.8 and poorly suits a horizontal animal.
3. Alternating narrative scenes of imprisonment and dedication: rejected because it echoes 1.22.5 and requires invented actions; the memorial is the passage's tangible subject.

## Art and orientation

One sophisticated raster illustration of an imagined bronze lioness memorial and adjacent fully draped Aphrodite statue in the ancient Athenian Acropolis setting. The translation supplies the account and attribution; sculptural appearance, pose and setting are artistic interpretation, not identification of a surviving original. No torture scene, murder, inscriptions, exposed anatomy, modern museum furnishings or unsupported detailed architectural reconstruction. Low three-quarter side view, broad horizontal composition, dominant dark copper/verdigris with pale limestone and clear light blue sky. Bright early daylight models bronze and stone, replacing the prior page's dark interior. Sculpture and outdoor spatial depth replace living portraits; camera angle drops toward pedestal level. These changes serve a public memorial.

Orientation header explicitly names Athens and the Acropolis; adjacent lower captions identify the lioness and Aphrodite in their respective left/right positions. No locator or leaders needed. No unnecessary caveat footer. Art prompt requests no lettering; all exact text rendered locally.

## Pre-art geometry and variety

Canvas 1600x1320. Single art rectangle (24,100)-(1576,900), aspect 1.94:1. Reserve upper-left sky for a small local orientation strip, not translation. Captions y905–963. Complete translation splits only before 'In recognition', first column (24,985)-(775,1295), then second (805,985)-(1576,1295). Measured font minimum 26px, desired 29px, padding 12px. Each actual bounding box validated before save; reconstruction checked against complete SQLite passage.

Broad-image/band family occurs twice in candidate plus five (including 1.22.7); 1.22.4 is outside that window. Neither immediate predecessor matches. No tall left sidebar. Rectangles defined afresh; only measured text helpers reused.

## Review pending

Full-size and thumbnail comparison, text integrity, geographic/historical orientation, raster quality against anchors, modesty and all label clearance required before acceptance. Then local HTML/PDF visual check, combined backup push/verify and narrow source commit/push. Existing README edit excluded.

## Accepted visual and text review

Built-in imagegen produced the main art; initial and corrected components retained. Initial art incorrectly put an Acropolis hill behind the memorial and crowded the ears against the top. Targeted imagegen revision removed that hill/temple and widened framing. Final art inspected at full page size: modeled bronze with fine patina, convincing feline form, dimensional stone and fully draped Aphrodite; no crude/flat/diagrammatic panels, pseudo-text, nudity or violent depiction. Ancient city and distant hills provide spatial depth while the orientation locates the memorial. Both relevant captions sit under their corresponding objects; no leaders required. Sculptural appearance remains an artistic interpretation recorded above.

Seven-page actual thumbnail comparison at graphic_book/output/1_23_2-comparison.jpg PASS. The broad image/lower columns differ from the central portrait and unequal diptych of both immediate predecessors. Broad-image/band family appears twice in candidate plus five, meeting the limit; no tall translation sidebar. Low view, bronze/blue outdoor palette, daylight and object emphasis all differ from the preceding interior portraits. Craft/finish meets anchors 1.1.4 and 1.1.5.

Text-fit PASS before generation and after render: all seven actual bounding boxes within 12px padding. Complete verbatim SQLite text in original order at 29px; auxiliary minimum 25px. Full-size inspection finds no clipping, crowding or border collisions. Accepted candidate copied unchanged to canonical path.

## Build and backup verification

Requested local graphic-book build PASS: 137 illustrated passages, 138 PDF pages. HTML reader identifies 1.23.2 as 137 of 137 with correct image path. Rasterized final PDF page 138 visually inspected: complete, legible and unclipped. Full create_website.py not run.

Combined backup push and verify PASS: raksasa image mirror, S3 finished-page mirror and component cache agree. Two component assets uploaded; 383 assets in the verified manifest. Independent local/raksasa/downloaded-S3 page SHA-256 matches: ab0921ad92a0ded0ef15f7d04269ad28620c92ecfa5d5d4736185b885b195c98.
