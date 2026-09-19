# Replacement page plan — 1.13.9

Daily run 2026-09-20; revision 20260919T180836Z. replacement_status: accepted
Original SHA-256: c6015cca7e0e06e8d5827d654f5ba0b1c66e1728f2891a52cbfa5862ca3e1633
Previous renderer and plan preserved in revisions/20260919T180836Z/ before editing. All previous raster components retained. Canonical original remains untouched pending review and archive verification.

## Actual PNG context and available plans read

Original: tall left prose panel, large upper-right mythic death triptych, small lower court scene and two information panels; ochre uniformity and tiny dense labels dilute the strongest art. Full original visually inspected. Anchors 1.1.4/1.1.5 inspected for craft only. Eight neighbouring PNGs viewed in /tmp/pausanias-replacement-neighbors.png with all plans read.

|Passage|Composition / text placement|Scenic panels|Viewpoint|Palette / light|
|---|---|---|---|---|
|1.13.3|Tall left prose; right main; lower inset/map|3|Close shield shrine, distant valley|Ochre olive; warm diffuse|
|1.13.4|Tall left prose; right main; lower inset/map|3|Elevated army approach and close leaders|Ochre sage; hazy daylight|
|1.13.5|Tall left prose; right main; lower locator/dynasty|2|Broad elevated battle|Bronze ochre; bright haze|
|1.13.6|Tall left prose; right main; lower map/detail|3|Oblique elevated assault|Ochre tan; dusty daylight|
|1.13.7|Tall left prose; right main; lower map/detail|3|Oblique city entry|Ochre umber; warm haze|
|1.13.8|Tall left prose; right main; lower sanctuary/detail|3|Bird's-eye urban conflict|Ochre terracotta; warm daylight|
|1.14.1 following|Tall left prose; right fountain; lower text panels|1|Eye-level architecture|Ochre cream; bright daylight|
|1.14.2 following|Tall left prose; right journey panorama; lower text panels|1 continuous multi-scene panorama|Elevated landscape|Ochre sage; warm daylight|

## Three alternatives before art

1. SELECTED: one broad, immersive Hellenistic historian-at-court painting over two generous numbered reading columns. Close foreground writer, distant royal presence. Gives the historiographic turn its own visual weight after six pages of battles and politics. Whole translation, including the three Aeacids, remains in order. The caption attributes the argument to Pausanias. No unnecessary maps, violent reenactments or filler insets. New broad-image/lower-text family occurs once in target-plus-five and repeats neither preceding nor following page.
2. Three vertical death portraits with interleaved prose: rejected as retaining too much of the original mythic triptych and compressing the text; subjects have already appeared in the narrative.
3. Central burial monument with surrounding prose: rejected because no reliable tomb appearance is provided and it would underrepresent the passage's lengthy historical-source criticism.

## Art and historical orientation

One imagined scene of Hieronymus writing near the royal milieu of Antigonus. Fully clothed older Greek historian at a plain wooden writing table, reed pen and blank/indistinct papyrus, distant seated Hellenistic royal patron in simple mantle and narrow cloth diadem, no throne spectacle or Roman imperial dress. No claim to a recorded meeting, exact portrait or recovered palace. Visualizes the text's connection between historian and patron, with no invented exchange or dictation. Header locates the opening burial discussion at Argos and names the historical relationship, without locating this imagined interior at Argos. Exact claims stay in the verbatim text. No carved or generated words. No specific buildings, maps, gods or deaths to misidentify.

Changes versus 1.13.8: near eye-level indoor human study instead of elevated urban combat; blue-grey and ink-green with muted burgundy instead of ochre/terracotta; soft cool window light instead of warm open sunlight; writer and patron replace crowds and architecture. These serve the pivot from narrated deaths to reliability of sources. Rich hands, cloth, wood, parchment and architectural recession. One scenic panel, no inset or leader.

## Pre-art measured layout

1800x1600 canvas; wide art (24,145)-(1776,995), ratio 2.06:1; no text reserved inside art. Two reading blocks (24,1150)-(866,1576) and (920,1150)-(1776,1576), split before 'Yet these accounts', read left then right. Desired 32px/minimum29px body; all blocks 12px padding. Font and wrapping helpers reused, page rectangles freshly designed. Renderer requires explicit output, candidate path graphic_book/output/replacements/1_13_9/20260919T180836Z/candidate.png. All exact text locally rendered. Preflight must pass before art.

## Review gates pending

Full-size candidate and original/neighbour thumbnail comparison; complete exact prose, orientation, art richness and variety. Temporary full-book HTML/PDF with candidate substituted only at 1/13/9.png, visually review target. Archive original PNG with source files, hash-check, S3 asset push/verify and independent archive download/hash before canonical original hash recheck and atomic promotion. Rebuild normal book, backup push/verify and three-store hashes before marking accepted.


## Candidate review and temporary book

Full 1800x1600 candidate inspected; first generated art's unsupported Acropolis-like coastal city and star banner removed by targeted imagegen edit. Initial and revised rasters retained. Final scene has finely modeled faces/hands, reed pen, blank papyrus, dimensional fabric, architecture and cool garden light; no invented geographic landmark, pseudo-text, violence, nudity or primitive scenic construction. Imagined royal context rather than an asserted recorded meeting. Caption ties the writer to the exact passage's source criticism. Stronger first-glance focus than the original four-scene montage with tiny boxed notes; materially larger and clearer complete prose.

Comparison with original, six preceding pages 1.13.3–1.13.8 and two following 1.14.1–1.14.2 PASS at output/replacements/1_13_9/20260919T180836Z/comparison.jpg. Broad image plus lower prose columns occur once in target-plus-five; neither preceding nor following composition copied; old sidebar abandoned. Cool eye-level writing scene contrasts with warm elevated urban battle. Anchor craft, historical orientation, semantic fit, suitability and variety PASS.

Eight measured text blocks PASS with 12px padding; complete exact SQLite passage in original order at 32px, auxiliary minimum 28px. No crowding, clipping or border collision. Temporary full-book HTML/PDF PASS: 141 illustrations, 142 PDF pages; reader 1.13.9 is 78 of 141 and uses reviewed candidate. PDF page 79 rasterized and visually inspected; complete and legible. Verified only 1/13/9.png differs in the temporary image tree and its built reader image matches candidate bytes. Original canonical hash remains unchanged. Candidate accepted for promotion subject to archive verification.

Original PNG now copied to revisions/20260919T180836Z/previous-page.png beside preserved renderer and plan; local copied hash matches recorded original. S3 archive key: assets/generated/1_13_9/revisions/20260919T180836Z/previous-page.png. Archive upload/download verification pending.

Archive asset push/verify PASS (393 assets), independent S3 download SHA-256 matches original c6015cca7e0e06e8d5827d654f5ba0b1c66e1728f2891a52cbfa5862ca3e1633. Canonical original hash rechecked before atomic promotion. Reviewed candidate promoted at original path; new hash 5b0d6758c141d22eb8b2443c2e3ba4e987ba75c74d01710c3ddf032af8e39f9b. Normal rebuild and combined backup verification pending.


## Final promotion verification

replacement_status: accepted
Normal HTML/PDF rebuild PASS: 141 illustrations, 142 PDF pages. Rasterized page 79 is byte-identical to the reviewed temporary preview. Combined backup push and verify PASS: local assets, S3 manifest/pages and raksasa pages match; 393 component assets. Independent local/raksasa/downloaded-S3 replacement hashes all equal 5b0d6758c141d22eb8b2443c2e3ba4e987ba75c74d01710c3ddf032af8e39f9b.

Before: canonical graphic_book/images/1/13/9.png, SHA-256 c6015cca7e0e06e8d5827d654f5ba0b1c66e1728f2891a52cbfa5862ca3e1633; preserved as graphic_book/assets/generated/1_13_9/revisions/20260919T180836Z/previous-page.png. S3 key assets/generated/1_13_9/revisions/20260919T180836Z/previous-page.png independently downloaded and hash-verified before swap.
After: canonical graphic_book/images/1/13/9.png; reviewed candidate retained at graphic_book/output/replacements/1_13_9/20260919T180836Z/candidate.png. Both have the final hash above. Previous renderer/plan and all previous art retained. No second replacement attempted. Source-only commit/push follows; binary assets remain ignored.
