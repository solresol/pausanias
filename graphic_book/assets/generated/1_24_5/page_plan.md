# Passage 1.24.5 page plan — 2026-09-29

## Passage and visual history

Exact SQLite translation: “Everything depicted on what are called the pediments relates entirely to the birth of Athena, while on the rear is the contest between Poseidon and Athena over the land. The statue itself is made from ivory and gold. In the middle of her helmet is placed the figure of a Sphinx—I shall write about what is said regarding the Sphinx when my account comes to Boeotia—and on each side of the helmet are fashioned griffins.”

Approved craft references visually inspected: 1.1.4 and 1.1.5. Their old left prose sidebar, ochre map framing, and inset density are not templates. Six accepted predecessors' actual PNGs and available plans inspected:

| ID | Actual composition / translation | Panels | Viewpoint | Palette / light |
|---|---|---:|---|---|
| 1.23.9 | Alternating prose/art then art/prose rows | 2 | eye-level medium court and road | pale stone, blue-green midday |
| 1.23.10 | Central tall portrait, prose on both sides | 1 | close civic interior | indigo/slate, warm table light |
| 1.24.1 | Broad art above lower two-part prose | 1 | medium-wide oblique gallery | cool marble/bronze, pearly day |
| 1.24.2 | Four prose fields above broad lower art | 1 | low close bull study | teal patina/grey, overcast |
| 1.24.3 | Square art upper-left, two right and two lower prose fields | 1 | eye-level statue | storm blue-grey, diffuse |
| 1.24.4 | Two upper and two lower prose fields around central panorama | 1 | wide ground-level ritual scene | limestone/olive, clear morning |

## Three compositions considered before art

1. **Selected: diagonal architectural and object diptych.** Upper-left ordered prose (pediments and statue material) faces a substantial upper-right view of the Parthenon's east pediment. Lower-left close art of Athena's helmet faces lower-right prose (Sphinx and griffins). The diagonal prose/art then art/prose silhouette resembles 1.23.9, outside the five-predecessor window, so occurs once in candidate plus five. It differs from both immediate predecessors at thumbnail scale and has no tall left translation sidebar.
2. One full-width facade panorama above two lower prose columns. Rejected because its silhouette repeats 1.24.1's recent broad art over text and would make the helmet details too small.
3. Central full-height Athena portrait with prose on both sides. Rejected because its silhouette repeats 1.23.10 in the five-predecessor window and fails to show the architectural context of the pediments.

## Pre-art geometry and art direction

Canvas 1800×1600. Header `(24,16)–(1776,128)`. Upper-left reading area `(24,153)–(610,731)`, upper-right art `(640,145)–(1776,735)` (1136:590). Lower-left art `(24,805)–(1160,1504)` (1136:699); lower-right reading area `(1190,816)–(1776,1568)`. Captions in the 40–65px gaps and at the foot. Reading order: upper-left then lower-right. Exact two-part division after “The statue itself is made from ivory and gold.” Body minimum 30px, auxiliary minimum 22px, 12px padding, all measured before art; fail on overflow and assert exact translation in original order. The art rectangles were widened after the first thumbnail review to reduce empty space while retaining 36px body text.

Upper-right art: interpretive oblique close view of the east facade of the fifth-century BCE Parthenon on the Acropolis, with deeply modelled east pediment sculptures recalling Athena's birth, credible Doric columns and Attic sky. Do not suggest the precise lost forms are known. The rear Poseidon contest is stated in text, not falsely depicted on the front. Target 1136:590 crop; warm-white marble with cool blue shadow, crisp high midday light; no text or modern Athens.

Lower-left art: close, eye-level imagined study of Athena Parthenos's ivory-and-gold head and helmet, the small Sphinx at the helmet crest and a griffin to either side clearly visible, fully clothed/armoured bust, richly crafted gold and ivory. Target 1136:699 crop, aligned to the top so the Sphinx is fully visible; dark ultramarine background and directional cool light, gold highlights. No inscriptions, text, nudity, loose fantasy beasts, or claim of an exact surviving object. The two panels have different scales and lighting. Compared with 1.24.4, change from panoramic ground-level animal ritual to close architectural detail and object portrait; change limestone/olive morning to marble/blue midday and gold/ultramarine controlled light. A local orientation line identifies Athens, Acropolis and Parthenon.

## Review status

Preflight and final render PASS: 11 deterministically measured text items with 12px padding; both verbatim SQLite translation blocks in order at 36px, auxiliary text no smaller than 24px. Initial raster art had bare-chested figures in the pediment and Sphinx; targeted edits added marble drapery and gold clothing, retaining the initial components for provenance. Initial layout had excessive blank area; art was widened and text remeasured. The second layout's lower art crop cut off the Sphinx crest, so top-aligned crop was used. The final 1800×1600 PNG was inspected full size and against the six actual predecessor PNGs in `tmp/1_24_5-comparison-v2.jpg` (with final crop checked separately). Rich stone, ivory and gold texture, credible architectural context, no visible nudity or pseudo-writing, locally rendered exact captions and no irrelevant callouts. The deliberately interpretive caption avoids asserting the exact lost pediment or cult statue form. Full-size art, semantic fit, historical orientation, content suitability and hierarchy PASS against 1.1.4 and 1.1.5. Diagonal alternating masses resemble only 1.23.9, outside the candidate-plus-five window; they differ from 1.24.3 and 1.24.4. No tall left sidebar. Camera distance, palette, light and architecture/object balance all change from 1.24.4. Variety PASS.

Bounded HTML/PDF build PASS: 150 illustrated passages, reader `1/24/5.html` shows 150 of 150 and the correct image, PDF has 151 pages; final page 151 rasterised and visually inspected with complete text and no clipping. Combined backup push/verify PASS: 418 component assets, local assets, S3 manifest and finished pages, and raksasa pages match. Independent local/raksasa/downloaded-S3 finished-page SHA-256 `af91d7cd36735aa4b749a08a0b36ed05ccae82dc29b73211b3ff8d2f117d4e84`; selected pediment local/downloaded-S3 `6302d422fa25f546dc361a256a6185ea8ce4c9312d1369250a0fb8fa74e4e032`, selected helmet local/downloaded-S3 `370c939fae2566282539f930e2976ada314fb5c28be8f3f2114310d83a85cb8c`. Source commit/push pending.
