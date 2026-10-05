# Pausanias 1.25.4 — the alliance and the Boeotian exception

Earliest translated passage lacking a canonical image on 2026-10-06: **1.25.4**. The 540-character SQLite translation lists allies from the Peloponnese, then communities beyond the Isthmus, before explaining why the Boeotians supported Macedonia. The last point is Pausanias's reported motive, not a depicted council meeting.

Approved craft references inspected as actual PNGs: **1.1.4** and **1.1.5**. Their rich art and typography are the quality standard; their ochre palette, tall left translation sidebar, and callouts are not reused. Six actual preceding PNGs inspected together:

| Passage | Actual composition / translation placement | Scenic panels | Viewpoint | Dominant palette and light |
| --- | --- | ---: | --- | --- |
| 1.24.6 | Wide upper griffin art, two lower prose columns | 1 | close low landscape | cold slate/lapis, dawn |
| 1.24.7 | Full-height Athena left, ordered right prose | 1 | upward sculpture portrait | ivory/gold/green-black, side light |
| 1.24.8 | Apollo upper left, Sipylus lower panorama, prose opposite and foot | 2 | eye-height object, distant valley | bronze/green/mauve, silver daylight |
| 1.25.1 | Central statue group, prose both sides | 1 | frontal medium sculpture court | pale marble/terracotta, morning |
| 1.25.2 | Two upper prose fields, broad lower sculpture terrace | 1 | low oblique terrace | verdigris/limestone, side light |
| 1.25.3 | Two upper prose fields, central battlefield, three lower fields | 1 | ground-level wide battlefield | blue-grey/umber/olive, diffuse post-storm |

## Three compositions considered before art

1. **Selected: one high oblique Boeotian landscape over two equal lower reading fields.** The rich terrain scene gives the political exception a specific place; the paired lower prose fields separate the alliance lists from Boeotia. This broad-upper-art/lower-prose family resembles 1.24.6, sixth predecessor, but is absent from the five-predecessor window and differs from both immediate predecessors. No left translation sidebar. One image, no scenic insets.
2. **Rejected: central relief map with prose in four corners.** Too many tiny exact place labels and too little space for the third sentence; a map of the whole coalition would likely become the dominant classroom-like diagram.
3. **Rejected: four-part city and envoy sequence.** It would imply gatherings and events that the passage only lists, and force several weak invented scenes.

Canvas 1800×1600. Header and orientation occupy y=16–140. Main image rectangle `(34,155)–(1766,1080)`, aspect 1.872:1. Caption `(34,1092)–(1766,1143)`. Complete translation is split after sentence two: Peloponnesian and beyond-Isthmus allies at `(34,1164)–(875,1572)`; Boeotian sentence at `(925,1164)–(1766,1572)`. Reading order left then right. Renderer reads SQLite, asserts exact reconstruction, measures every text rectangle with 12px padding and checks final glyph bounds. Minimum body 29px; auxiliary minimum 20px. No art generation until the preflight passes.

Art composition: a single sophisticated painterly high oblique panorama over the Boeotian plain and the old Theban site, with a subtle ruined ancient city in the middle distance and rugged enclosing hills. This interprets the deserted Theban territory in the passage, without asserting archaeological detail or showing a particular unreported incident. The view must feel geographically grounded and spatially deep, but it is a historical landscape rather than an exact map of every named ally. Orientation is carried by the locally typeset subtitle and caption identifying Boeotia, Thebes, the Isthmus and the alliance. No pseudo-writing or labels baked into the raster. No battle, modern settlement, reconstructed intact Thebes, or visible nudity. Target wide landscape crop 1.872:1. Camera high oblique and substantially farther from architecture than 1.25.3's ground-level battlefield; blue-green/limestone/violet palette with clear cool early-morning light, unlike 1.25.3's storm-blue/umber diffuse aftermath. Balance shifts from arms and figures to inhabited political geography and terrain. The colour, camera and subject changes are tied to the passage's place-based contrast.

## Review status

Pre-art and final deterministic fit **PASS**: eight measured blocks with 12px inset and final glyph-bounds checks; both prose fields use 34px body, auxiliary type is 23px or larger, and the complete SQLite passage reconstructs in source order. The initial raster's tower-like ruin was historically ambiguous; the corrected component replaces it with low ancient wall foundations and retains the initial component for provenance. The final 1800×1600 PNG was inspected full size and beside actual 1.24.6–1.25.3 PNGs at thumbnail scale in `tmp/1_25_4_comparison.png`. The rich terrain and ruin setting directly support the Boeotian exception; the caption explicitly limits the image to an interpretive view, while the subtitle locates the wider coalition. No graphic battle, modern object, nudity, pseudo-writing, irrelevant callout or text touching borders. Art quality, semantic fit, historical orientation, content suitability and hierarchy **PASS** against 1.1.4 and 1.1.5. Its upper-art/lower-prose silhouette repeats the sixth predecessor 1.24.6 but neither immediate predecessor, and occurs once in candidate plus five; no tall left sidebar. High oblique, far landscape view, blue-green/violet palette and clear morning light differ from 1.25.3's ground-level battlefield and diffuse storm light. Variety **PASS**.

The textual sequence and Theban-territory framing were checked against [Pausanias 1.25.4 at Theoi](https://www.theoi.com/Text/Pausanias1B.html); exact page prose comes from local SQLite. Build and backup results belong in the generation report.

Bounded local build **PASS**: 157 illustrated passages, reader 157 of 157, 158-page PDF; final PDF page inspected visually. Combined backup push and verify **PASS** with 431 component assets. Finished PNG SHA-256 `386c64d04925c2075856d202cb6a36e53798a0b6e7893539771491ee6a54d464` independently matches local, raksasa and downloaded S3 copies. Corrected component SHA-256 `c7e3b5eaa7b056001d434a5404cfb392e89bd315339aa7cd568d88381f54d2b0` matches local and downloaded S3 copies.
