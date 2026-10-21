# Pausanias 1.27.3 — the Arrephoroi's night descent

Run 8a9968934b00499da99a67ea7e5c2ff2, 2026-10-21 UTC. Source is the complete 977-character, 168-word PostgreSQL-exported English passage, validated with `graphic_book_corpus.snapshot_path()` and read with `load_translation("1.27.3")`. No PostgreSQL or legacy SQLite access. Craft anchors 1.1.4 and 1.1.5 were inspected as actual PNGs for finish and readable typography, not as layout templates.

## Actual six preceding accepted pages

The catalogue hashes of all six PNGs were verified against S3. Their actual images were compared in `/tmp/pausanias-1273-refs/preceding-six.jpg`, and all six available page plans were read.

| Passage | Actual composition / translation | Panels | Viewpoint | Palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.26.4 | Paired upper sculpture portraits over paired lower prose | 2 | close oblique sculpture | verdigris and pale stone; diffuse daylight |
| 1.26.5 | Broad middle architectural band with prose above and below | 1 | low oblique interior | sea green, grey stone, blue shadow; doorway shaft |
| 1.26.6 | Broad upper sanctuary image over three lower prose columns | 1 | human-height interior | gold, painted wood; subdued daylight |
| 1.26.7 | Full-height left lamp/palm art beside three right prose fields | 1 | close and slightly low | bronze, deep teal, blue-grey; flame and dawn |
| 1.27.1 | Two upper prose fields; lower-left votive scene and lower-right prose | 1 | medium eye-level ensemble | plum, green, silvery stone; cool daylight |
| 1.27.2 | Single upper statement, deep central courtyard panorama, two lower prose fields | 1 | broad ground-level exterior | silver olive, limestone, sky blue; bright morning |

## Three compositions considered before commissioning art

1. **Selected: one tall central nocturnal descent, with four numbered translation fields in two flanking prose wings.** Reading order is upper left, lower left, upper right, lower right, explicitly numbered 1–4. The image's vertical depth serves the natural underground passage. It is a central portrait flanked by text, rather than a large right scene beside one left sidebar. This mass arrangement differs from both immediate predecessors and occurs once in the candidate-plus-five window. None of the preceding five has a tall left translation sidebar, so even a conservative reading of the left prose wing passes that restriction.
2. Rejected: a three-scene horizontal narrative strip showing presentation, descent and return. It would fragment the scene, reduce the illustration's scale, and invite invented details of a deliberately secret rite.
3. Rejected: a broad upper night panorama over three lower prose columns. This repeats 1.26.6 within the recent window and gives less emphasis to the underground descent; a central panorama between text bands would directly repeat 1.27.2.

## Subjects, geometry and historical restraint

Canvas 2000×1800. Single art rectangle `(528,175)–(1472,1670)`, 944×1495 (0.6314:1 portrait). Four complete prose substrings, split only at “They remain for a certain period”, “Within the city”, and “Below they leave”, concatenate with single spaces to reproduce the exact exported passage. Their rectangles are `(28,225)–(490,835)`, `(28,925)–(490,1750)`, `(1510,225)–(1972,920)`, `(1510,1010)–(1972,1750)`. All translation fields use a common measured body size, minimum 36px, with 14px padding. The passage ID, title, Athens/Acropolis/Aphrodite orientation, numbered headings and interpretive caption are independently measured and fail on glyph overflow. Preflight must pass before art generation.

Main subjects: two fully clothed young female attendants carrying completely covered sacred objects on their heads at night, descending into a natural limestone passage within a sacred garden enclosure. The contents are intentionally invisible: neither snakes nor identifiable sacred objects may be invented. No priestess handover or exchange is shown; those would require additional sequential scenes. The view looks from lower in the rough natural passage toward the garden threshold. Garments, baskets, limestone and vegetation provide tactile detail. No exact archaeological route, monument design, precinct plan or particular age is claimed. Caption explicitly identifies the scene as interpretive. No nudity, theatrical supernatural event, invented inscription, modern building, nearby sea, diagram, leader line, locator or scenic inset.

Compared with 1.27.2, choose a closer low viewpoint instead of the broad ground-level courtyard; midnight indigo, silver and muted earth rather than silvery olive and bright sky blue; moonlit chiaroscuro instead of morning daylight; two moving attendants and natural rock instead of an olive tree between temple facades. At least four art choices change for passage-specific reasons. The centrally descending path gives spatial orientation; the local header identifies Athens, the Acropolis and Aphrodite in the Gardens without claiming a precise route map.

## Review

Pre-art and final deterministic fit **PASS**. All 977 exported characters are preserved in source order, four translation fields use common 37px type (36px minimum), and all 12 text blocks have 14px padding with measured glyph-bound checks. The original UTF-8 translation SHA-256 is `0e11c6a67348b75dbbc666083eca7bd11c0e50e77a5f9634484c82e7883c9eb9`. `layout_report.json` records every rectangle, font size and actual text bound. No art was commissioned until the preflight passed.

The generated component and final 2000×1800 PNG were inspected at full size. Exactly two modestly clothed attendants visibly descend through the rocky threshold; both head-borne containers are completely covered, and their contents remain unknown. The moonlit garden opening, enclosure wall and natural stone establish the night descent without asserting an exact archaeological route. Garment folds, hands, wicker, rough stone and depth have sophisticated raster finish. There is no nudity, baked lettering, irrelevant event, imaginary revealed object, modern fixture, gratuitous callout or schematic inset. The independently typeset header supplies the Athens/Acropolis/Aphrodite orientation. Art quality, semantic fit, historical restraint, suitability, hierarchy, complete passage and text clearance **PASS** beside anchors 1.1.4 and 1.1.5.

The actual seven-PNG comparison `/tmp/pausanias-1273-comparison.jpg` shows 1.26.4–1.27.3. The tall central art mass with four flanking prose fields differs from both immediate predecessors: 1.27.1's upper prose/lower-left art L and 1.27.2's broad middle panorama between upper and lower prose. It is also distinct from 1.26.7's full-height left art/right prose. The selected composition occurs once in candidate plus five predecessors. No preceding-five page has a tall left translation sidebar. The low close viewpoint, indigo/silver night palette, moonlight and moving human subjects change four art choices from 1.27.2 for passage-specific reasons. Variety **PASS**.

Local bounded HTML/PDF build **PASS**: 171 illustrated passages plus the existing title page, 172 PDF pages. Reader `1/27/3.html` identifies 171 of 171 and links a byte-identical copy of the reviewed PNG. PDF page 172 was rasterized and visually inspected; the complete translation, ordered fields and illustration remain intact. Local final PNG SHA-256 `d7b2e5d8901427177b464521131bdffb95ce696fdbc4d698c17e05dfcc749184`; component SHA-256 `1a33bda6337197819f71dca1e0b105310970fcbade9373f09e6a09ce02d8cd3e`. These are local checks, separate from the exchange checkpoint and overnight website publication.
