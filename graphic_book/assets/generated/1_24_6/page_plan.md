# Passage 1.24.6 — page plan (2026-09-30)

## Source and recent visual history

The exact English translation is read from local `pausanias.sqlite`. It reports Aristeas of Proconnesus's verses about griffins guarding gold against the Arimaspi beyond the Issedones, then describes the legendary beings. The page presents this as reported tradition, not observed zoology or a mapped historical fact.

Approved craft anchors inspected as PNGs: 1.1.4 and 1.1.5. Their polished raster finish and legible typography set the quality bar; their ochre mapping, left sidebar and inset furniture are not reused. Actual six predecessor PNGs and plans inspected:

| ID | Actual composition / translation placement | Scenic panels | Viewpoint | Palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.23.10 | Tall central civic portrait; prose on both sides | 1 | close eye-level interior | slate/indigo; window and lamp |
| 1.24.1 | Broad gallery image above two prose fields | 1 | medium-wide oblique terrace | pale marble/bronze; pearly day |
| 1.24.2 | Four prose fields above broad bull study | 1 | close low terrace | teal patina/grey; overcast |
| 1.24.3 | Near-square statue upper left; prose right and below | 1 | eye-level sculpture | storm blue-grey; diffuse |
| 1.24.4 | Central broad ox scene between upper/lower prose | 1 | ground-level panorama | limestone/olive; clear morning |
| 1.24.5 | Diagonal pediment/helmet diptych; prose opposite each | 2 | oblique facade and close object | marble blue/gold; midday and controlled cool light |

## Three compositions considered before art

1. **Selected: immersive wide mythic landscape over a unified two-column reading band.** A single large low viewpoint places a richly detailed eagle-headed, winged lion griffin beside gold-bearing rock in the foreground; a small, clothed human presence and austere northern terrain establish the reported conflict without pretending to map the Issedones or authenticate the legend. The two balanced text columns below carry the entire translation, in source order. The landscape occupies more height than 1.24.1's gallery and there are no scenic insets. Its broad-art/lower-prose family occurs at 1.24.1 among the five predecessors, so twice at most in candidate plus five; neither immediate predecessor uses it. No tall left translation sidebar.
2. A central griffin/object portrait flanked by prose. Rejected because its thumbnail masses resemble 1.23.10 and leave too little landscape context for the distant-place story.
3. Two stacked narrative scenes, Aristeas reciting and griffins guarding gold, with staggered text. Rejected because the poet's act is not described and would invent a scene; the reported creatures are the point.

## Pre-art geometry and art direction

Canvas 1800×1600. Header and orientation in `(34,19)–(1766,132)`. Main raster panel `(34,151)–(1766,1039)`, aspect 1.95:1. A short locally rendered caption sits `(44,1052)–(1756,1099)`. Ordered translation fields: left `(47,1156)–(878,1536)`, right `(922,1156)–(1753,1536)`; source division after the first sentence ending “earth itself.” Reading order is left then right. Two headings sit above the translation. The body minimum is 31px, preferred 39px; all text rectangles include 12px padding, measured before generating art. An explicit exact-text assertion rejects omission or reordering.

Art prompt: sophisticated painterly historical fantasy, printed-book finish, target panoramic 1.95:1 crop. Close low three-quarter view from the gold-bearing rock, not an elevated Acropolis view. Griffin morphology follows the passage: lion body, eagle beak and wings; no horns, dragon parts or additional heads. Clothed, distant Arimaspi figures may be partly visible, without asserting an exact reconstruction of their legendary single eye. Rugged mineral terrain and cold far mountains orient the imagined place beyond the Issedones. Dominant palette: lapis, cold slate, iron grey, and muted gold, with dramatic cold dawn backlight and precise warmer gold accents. This changes camera distance, subject balance, palette and lighting from 1.24.5's architecture/object diptych. No text, pseudo-writing, labels, borders, modern objects, gore or nudity. A local line names Aristeas and the reported region; it does not make a false cartographic claim. One scenic panel only; no locator is needed because the passage locates its action relationally, beyond the Issedones.

## Review

Pre-art and final deterministic fit PASS: nine text items measured with 12px internal padding, verbatim SQLite translation reconstructed in source order, both main body blocks at 39px, auxiliary items at 23–43px. Every glyph rectangle remains inside its target. Exact English prose is visible and legible in the final page.

Full-size PNG and seven-page thumbnail contact sheet `tmp/1_24_6_comparison.jpg` inspected. The single panoramic image is a rich textured and spatially legible griffin/gold scene, with humans subordinate; the caption marks it as imagined and the orientation line marks the geography as reported. No visible nudity, gore, pseudo-writing, primitive art, irrelevant leader, cropped label or cramped text. Against craft references 1.1.4 and 1.1.5, art quality and print hierarchy PASS. Candidate differs from 1.24.4's central ox band and 1.24.5's diagonal diptych; broad-art/lower-prose family occurs only here and 1.24.1 within candidate plus five. No tall left translation sidebar. Camera distance, landscape/object balance, palette and light differ from 1.24.5. Variety, semantic fit, orientation, historical framing and content suitability PASS.

Bounded build PASS: 151 illustrated passages; reader `1/24/6.html` identifies 151 of 151 and the correct image; PDF has 152 pages. Final page 152 was rasterised and visually inspected, with no clipped text or image. Combined backup push/verify PASS: 419 component assets; local assets, S3 manifest, S3 finished pages and raksasa pages match. Independent local/raksasa/downloaded-S3 final-page SHA-256 `8f9484351966b83f5b020f047806bb89b5cb0d641988198f2fa11daf8e25d133`; local/downloaded-S3 component SHA-256 `009069500e8aa6719621771b75f8d32aa7b6e8f1aa988ee68b11ca83bf3b44e7`. Source commit and push pending.
