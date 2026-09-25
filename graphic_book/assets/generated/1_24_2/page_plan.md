# Pausanias 1.24.2 — page plan

Run 2026-09-26 Australia/Sydney. Earliest missing image checked against numeric SQLite passage order. The renderer loads the complete English translation verbatim.

## Six preceding accepted pages, actual PNGs and plans reviewed

| Passage | Composition / translation placement | Panels | Viewpoint | Palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.23.6 | Equal scenic wings around central prose | 2 | Close shipboard and medium shore | Wine, linen, jade; lateral daylight |
| 1.23.7 | Tall art left, prose and inset right | 2 | Oblique court, low wetland | Bronze, indigo, celadon; cool light |
| 1.23.8 | Broad bronze-horse art above prose | 1 | Close low front-quarter | Charcoal, rose, violet; dawn |
| 1.23.9 | Alternating prose/art rows | 2 | Medium eye-level exteriors | Pale stone, blue-green shadow; midday |
| 1.23.10 | Central civic portrait, opposed prose | 1 | Close eye-level interior | Slate, indigo; window and lamp |
| 1.24.1 | Wide sculpture gallery above two lower prose columns | 1 | Medium-wide oblique terrace | Marble, olive, bronze; pearly day |

Quality references 1.1.4 and 1.1.5 inspected at full useful size. Their left prose sidebars, ochre palette, leaders and insets are not copied.

## Three materially different compositions considered before art

1. **Selected: four ordered text fields above one immersive sculpture scene.** Four prose fields follow the passage's four beats: Phrixus's journey; his ritual; neighbouring Heracles and Athena works; the Areopagus bull. A broad bottom scene orients all as dedications on the Athenian Acropolis. The bull is the strong foreground object; a draped Phrixus figure and restrained neighbouring votive works may recede. The upper prose occupies the full page width, so there is no tall left translation sidebar. This text-top/art-bottom silhouette differs from the last two pages and occurs once in the candidate-plus-five window.
2. **Rejected: another panoramic gallery above lower prose.** It would repeat the immediately preceding page's large masses.
3. **Rejected: central bull portrait with prose on both sides.** It would repeat 1.23.10's opposed-prose silhouette and leave too little room for the complete passage.

## Content, layout and art brief

This is Pausanias describing representations, not a report of events occurring together. The visual should read as an interpretive ancient display of lost works on the Athenian Acropolis, without asserting their exact archaeological appearance or adjacency. The main panel shows the bronze bull, with the draped Phrixus-and-ram dedication set back. Other works can be suggested as distant sculptural presences, without trying to render every complex myth in one crowded image. No live sacrifice, gore, exposed bodies, pseudo-inscriptions or modern Athens. A short local caption will state uncertainty. Orientation appears in the local header and sculptural setting. One panel; no locator, insets or leader lines.

Canvas 1800×1600. Header `(24,18)–(1776,125)`. Four ordered prose fields `(24,166)–(444,704)`, `(468,166)–(888,704)`, `(912,166)–(1332,704)`, `(1356,166)–(1776,704)`. A sequence line above the fields marks 1–4. Main art `(24,680)–(1776,1510)` ratio 2.111:1; caption `(24,1517)–(1776,1579)`. The measured actual prose ends above y=560, leaving a clear gap before the art despite their outer layout rectangles overlapping. Reading order is left to right, then art. Each text field, caption and header is fitted and checked with 12px padding before art generation; passage minimum 27px, auxiliary minimum 23px. The renderer compares the joined passage blocks to SQLite and fails on mismatch or overflow.

Art prompt: wide 2.3:1 source cropped to 2.111:1 on page, low human-height oblique view across an ancient Acropolis votive terrace; weathered bronze bull in near foreground, draped Phrixus with ram as a secondary sculptural group behind, Attic landscape and ancient masonry giving orientation. Overcast luminous sky, desaturated teal patina, grey limestone and muted red-brown accents. Finished painterly archaeological illustration, rich material texture and atmospheric depth. Reserve no text area within art: all prose is above. Compared with 1.24.1, camera is close and low rather than medium-wide; dominant teal/grey replaces pale marble/olive; soft overcast replaces pearly direct day; one dominant animal object replaces two equal myth groups.

## Preflight and post-render review

Preflight PASS before art: 12 measured text blocks, complete verbatim SQLite translation in order, 12px padding, passage at 32px except the long ritual block at 30px, auxiliary minimum 26px. The first render exposed a bad one-word line in the ritual field; reducing only that field to 30px removed it. Final actual bounding boxes remain inside their target rectangles. Translation reconstruction check PASS.

Built-in image generation supplied a detailed bronze-bull scene. The first version introduced an unrelated little horse and owl at the far left; a targeted edit removed those two sculptures without changing the bull, draped figure, ram, terrace or landscape. Both component versions and their prompts are retained. Full-size inspection of the final page found complete passage ID and prose, no overflow, clipped captions, pseudo-writing, nudity, violence, schematic work or irrelevant callouts. The bronze, stone, distant landscape and statues have rich material modelling. The single panel directly depicts two subjects named in the passage; the local header identifies the Acropolis and the caption explicitly avoids claiming exact lost forms or placement. Visual quality and semantic orientation PASS against 1.1.4 and 1.1.5.

The seven-page thumbnail comparison at `tmp/1_24_2-comparison.jpg` shows a distinct text-first/art-bottom mass arrangement. It does not repeat 1.23.10's central portrait or 1.24.1's art-first/lower-prose spread. This composition appears once in the candidate-plus-five window; no tall left sidebar. Close low object view, teal patina and cool grey, overcast light, and bull-led object balance vary camera distance, angle, palette, lighting and subject balance from 1.24.1. Variety PASS.

Bounded local HTML/PDF build PASS: 147 illustrated passages, reader 147 of 147, PDF 148 pages. PDF page 148 was rasterised and visually inspected. Combined backup push/verify PASS: 410 component assets; local manifest, S3 assets and finished pages, and raksasa finished pages agree. Independent local, raksasa and downloaded S3 finished-page SHA-256: `8493f42c78fa9884e753e83b2ad6acd74a79f2655b48feead2b6406ba3b056db`. Selected component local/downloaded S3 SHA-256: `dd0f998413bae1ecd6bc5dd9815f112b246d0005331824468e4f371c2aa2e47b`.
