# Pausanias 1.24.4 — page plan

Run 2026-09-28 Australia/Sydney. Earliest numeric translation gap in local SQLite: 1.24.4. The complete English translation is loaded directly from SQLite and checked against the four measured reading blocks before art generation.

## Preceding accepted pages and quality references

Actual PNGs were compared at thumbnail scale, and available plans read. Approved craft references 1.1.4 and 1.1.5 were inspected; their old sidebar, ochre palette, map furniture and callout density are not layout models.

| Passage | Actual composition / translation placement | Scenic panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.23.8 | Broad horse portrait above two prose columns | 1 | Close, low front quarter | Charcoal, rose, violet; dawn |
| 1.23.9 | Staggered prose/art and art/prose rows | 2 | Medium eye level | Pale stone, blue-green shadow; midday |
| 1.23.10 | Tall central civic portrait between opposed prose | 1 | Close eye-level interior | Slate, indigo; window and lamp |
| 1.24.1 | Wide sculpture gallery over two prose fields | 1 | Medium-wide oblique terrace | Marble, olive, bronze; pearly daylight |
| 1.24.2 | Four prose fields over a wide bronze-bull scene | 1 | Close low oblique terrace | Teal patina, grey; overcast |
| 1.24.3 | Near-square Earth statue upper left, prose at right and foot | 1 | Eye-level statue study | Blue-grey, green, umber; storm light |

## Three compositions considered before art

1. **Selected: four ordered prose fields above and below one panoramic central scene.** Short opening and grain descriptions sit side by side above the image; the guarded ox and axe-trial sequence continue in two fields below. The art is a long horizontal visual pause at the precise instant when the ox approaches the grain altar. This wide central art band between prose bands differs at thumbnail scale from the two preceding pages, and occurs once in the candidate-plus-five window. There is no tall left translation sidebar.
2. **Rejected: large altar portrait on the right with a left prose rail.** This would read as the old tall-left-sidebar arrangement and would make the long ritual account too narrow.
3. **Rejected: four successive ritual scenes in a grid.** It would invite anachronistic reconstructions of the axe trial, scatter the main historical and geographic subject, and make the complete prose too small.

## Content, orientation, geometry and pre-art fit

Pausanias describes two statues of Zeus, the custom of Zeus Polieus, unguarded mixed grain on the altar, the guarded ox approaching and touching it, the bouphonos killing the ox and fleeing after discarding the axe, the axe's formal trial, and entry into the Parthenon. The illustration shows **only the moment before the killing**: the living ox nearing mixed grain on a plain altar, ancient attendants at a respectful distance, and the Parthenon visible beyond the Acropolis court. The later action belongs to the exact prose. The view is interpretive; it makes no claim to the altar's excavated form or precise placement. No visible violence or graphic injury, no invented inscriptions or labels baked into art, and no modern skyline.

Canvas 1800×1600. Header `(24,16)–(1776,134)`. Top reading fields `(24,145)–(872,435)` and `(910,145)–(1776,435)`. Main art `(24,456)–(1776,1111)`, a 1752:655 panoramic crop. Caption `(24,1117)–(1776,1171)`. Lower reading fields `(24,1177)–(872,1538)` and `(910,1177)–(1776,1538)`, with a short footer. Reading order: upper-left 1, upper-right 2, lower-left 3, lower-right 4. All text rectangles have 12px padding and a measured minimum size; no prose is placed inside the art. Initial preflight passed: 13 measured blocks; four translation blocks exactly reproduce SQLite in order, all at 32px; auxiliary minimum 23px.

Art direction: finished, sophisticated painterly archaeological panorama of the ancient Athenian Acropolis in clear early morning. A **living, uninjured ox** approaches a plain stone altar on which mixed barley and wheat are visibly scattered; a few fully clothed ancient Greek attendants watch from a distance, one priest may be among them but no weapon is raised. The Parthenon must appear recognisably beyond, in credible ancient setting; frame the ox and grain as foreground subject with the temple as spatial orientation. Ground-level three-quarter camera, wide panorama 1752:655, broad depth and rich stone, animal, cloth and landscape texture. Palette of cool limestone, muted olive, deep ultramarine shadow, pale gold grain; crisp soft morning illumination. No text, inscriptions, maps, diagrams, ornamental panels, nudity, injury, blood, modern structures, or invented ritual objects. Compared with 1.24.3, change camera from near-square statue study to ground-level wide ritual landscape, shift from storm blue-grey to clear morning limestone and olive, and change subject balance from sculptural figure to living ox/people/architecture.

## Post-render review and verification

The initial raster was strong but placed a modern-looking city below a separate Parthenon hill. The selected revision moves the Parthenon onto the same plateau as the altar, removes the city and unrelated statues, and retains the richly modelled ox, grain, attendants and Attic distance. Both component versions are retained in the asset cache. The selected component and final PNG were opened at full size. The main art has credible depth and finish beside 1.1.4 and 1.1.5, directly depicts the ox approaching the grain, and provides Acropolis orientation. No exposed bodies, violence, pseudo-writing, irrelevant leaders or cramped captions appear. Art, semantic fit, historical care, suitability, hierarchy and text checks PASS.

The actual PNGs for 1.23.8–1.24.4 were compared at thumbnail scale in `tmp/1_24_4-comparison.jpg`. The central horizontal art band between upper and lower prose is distinct from 1.24.2's top-text/lower-art split and 1.24.3's upper-left square/right-prose/lower-prose layout. It occurs once in the candidate-plus-five window; there is no tall left sidebar. Camera distance, aspect ratio, palette, lighting and balance of living ox, people and architecture vary from 1.24.3. Variety PASS.

Final renderer check PASS: all 13 text items fit with 12px padding, complete SQLite passage exactly in order at 32px, auxiliary text at 23px or larger. Bounded local HTML/PDF build PASS: 149 illustrated passages, reader page 1/24/4 references the new PNG, PDF has 150 pages, and its final page was rasterised and visually inspected. Combined backup push/verify PASS: 414 asset files, with local cache, S3 manifest, S3 pages and raksasa pages matching. Independently checked local, raksasa and downloaded-S3 finished-page SHA-256 `ac70532a1ff87473953bcd40cfbcd0f5b18cdc296f33f3e5e0d8762a0a9fc826`; selected component local/downloaded-S3 SHA-256 `ad5102b23f4e8519fd37da05fb94828a028428153d7b521157d7b6a4e5399ace`. Source commit/push pending.
