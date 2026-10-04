# Pausanias 1.25.3 page plan — 2026-10-05

Earliest translated passage without a canonical image: **1.25.3**. The complete SQLite English translation is 834 characters, five sentences. It moves from the defeat at Chaeronea, through Philip's and Alexander's reigns, to the Athenian decision after Alexander's death. The visual treats Chaeronea as the turning point and does not stage all later events as simultaneous.

Approved craft references inspected as actual PNGs: **1.1.4** and **1.1.5**. Their raster finish and legibility set the standard; their left sidebar and ochre diagram layout are not copied. The six actual preceding pages were compared at thumbnail scale and their plans read:

| Passage | Composition / translation placement | Scenic panels | Viewpoint | Palette and light |
| --- | --- | ---: | --- | --- |
| 1.24.5 | Diagonal architecture/object diptych; prose upper left and lower right | 2 | oblique facade and close object | marble blue/gold; day and cool spot |
| 1.24.6 | Broad upper griffin landscape, two prose columns below | 1 | low foreground | slate/lapis; cold dawn |
| 1.24.7 | Full-height Athena portrait left, three prose sections right | 1 | upward interior portrait | ivory/gold/green-black; side light |
| 1.24.8 | Apollo upper left, Sipylus lower strip; prose upper right and foot | 2 | eye-height object and distant terrain | bronze/green/mauve; silver daylight |
| 1.25.1 | Tall central sculpture court, prose in opposed side fields | 1 | eye-height medium | white marble/terracotta/olive; neutral morning |
| 1.25.2 | Two upper prose fields, broad sculpture terrace below | 1 | low oblique terrace | verdigris/charcoal/limestone; late-morning side light |

## Three compositions considered before art

1. **Selected: central wide battlefield panorama between upper and lower prose.** The two upper sentences establish the defeat and Philip's measures, then one long landscape panel separates them from three ordered lower prose blocks narrating the later decision. This gives the passage's time change a visible hinge. It differs at thumbnail scale from both immediate predecessors and occurs once in the candidate-plus-five window. No tall left translation sidebar.
2. **Rejected: full-height left battlefield portrait with right prose.** This echoes 1.24.7 within the recent window and the 834-character passage would leave the image too narrow.
3. **Rejected: three successive scenes for Philip, Alexander and Antipater.** The text names rule and political decisions rather than visible episodes; staging three tableaux would imply details the passage does not give.

## Geometry and pre-art text fit

Canvas 1800×1600. Header and orientation occupy y=17–131. Sentence 1 in `(34,174)–(870,415)`, sentence 2 in `(920,174)–(1766,415)`; reading order left to right. One image at `(34,403)–(1766,1150)` (crop aspect 2.32:1 from a wider source). A measured historical-time caption below. Sentences 3–5 in three ordered lower columns at x=34–576, 629–1171 and 1224–1766, y=1230–1575. All nine blocks use 12px padding, Pillow wrapping and glyph-bounds checks; body minimum 29px and auxiliary minimum 20px. The renderer asserts the five sentences reconstruct the complete SQLite passage exactly. **Pre-art preflight PASS:** nine measured blocks, body 34px, caption 23px, all text verbatim and in order. The image was enlarged and the lower blocks moved after a first-render review found excessive empty space.

## Art direction

One finished, wide historical landscape painting of the aftermath of the Battle of Chaeronea in Boeotia, 338 BCE. Ground-level low view from a stony field toward the foothills and an ancient Greek plain; a few abandoned shields and spears in near foreground, fully clothed small distant Greek and Macedonian formations withdrawing or standing apart. No prominent invented combat action, portrait of Philip or Alexander, city, lion monument, inscription, map symbols, text or gore. Historically plausible hoplite and Macedonian equipment, restrained and not presented as an archaeological reconstruction. Wide 2.80:1 crop, deep terrain and atmospheric distance; cool storm-cleared blue-grey sky, umber earth and muted olive, crisp overcast light. No text reserved inside the art. The local title/caption provide historical orientation. One image only; no decorative insets.

Relative to 1.25.2, the view moves from a low oblique architectural terrace to a ground-level expansive battlefield, the dominant palette moves from verdigris/limestone to storm blue/umber/olive, and lighting changes from side-lit late morning to diffuse post-storm. The subject balance shifts from sculpture and architecture to landscape and material aftermath. These changes arise from the passage's historical pivot rather than invented narrative.

## Post-render review

The first render was revised because the lower page had too much empty area; the panorama was enlarged and the three lower text blocks moved down. The final 1800×1600 PNG was inspected at full size and against the six actual preceding PNGs at thumbnail scale. Its upper prose / middle landscape / lower prose silhouette repeats neither 1.25.1 nor 1.25.2 and occurs once in the candidate-plus-five window. No tall left sidebar. Ground-level battlefield distance, blue-grey/umber palette, diffuse light and landscape-led balance differ from the preceding sculpture terrace. Variety **PASS**.

The scene directly supports the Chaeronea opening; the local Boeotia/Athens line and caption distinguish the battlefield from the later Athenian decision. The field, equipment, formations and terrain read as finished historical illustration rather than a schematic locator. No visible nudity or gore; no unrelated inset or misleading callout. Art quality, historical/semantic fit, orientation, content suitability, hierarchy and text clearance **PASS** against craft anchors 1.1.4 and 1.1.5. Nine measured blocks with 12px padding pass glyph-bounds checks; body 34px, auxiliary 23px or larger, complete SQLite translation in order. The bounded build produced 156 illustrated passages, reader 156 of 156 and a 157-page PDF; its last page was visually inspected and **PASS**.
