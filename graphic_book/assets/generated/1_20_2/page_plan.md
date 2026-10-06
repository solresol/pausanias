# Pausanias 1.20.2 replacement — 2026-10-07

replacement_status: accepted
run: 20261006T171310Z
original_sha256: e7cfb57f99126ef8fe84edfc7829b38abcf631dc89daca6a7c5a6ba42bd3ff49

The 604-character SQLite passage recounts Praxiteles' reaction to a false fire alarm, Phryne's choice of Eros, and two displays in the nearby Dionysus temple. The original is a tall left translation sidebar, large right temple art and two lower insets. Its previous renderer and plan were copied to `revisions/20261006T171310Z/`; its three old component images remain intact.

Actual craft anchors 1.1.4 and 1.1.5 inspected. Their rich raster finish and legible type set the quality bar, while their ochre atlas frame and sidebar do not govern this replacement. Target context, actual PNGs and plans:

| ID | Image/text masses | Panels | Viewpoint | Palette/light |
| --- | --- | ---: | --- | --- |
| 1.19.2 | Left prose, right sanctuary, three lower insets | 4 | oblique garden | green/ochre day |
| 1.19.3 | Left prose, right landscape, three lower insets | 4 | high landscape | olive/ochre day |
| 1.19.4 | Left prose, right tomb, two lower insets | 3 | oblique tomb/harbor | gold/blue day/night |
| 1.19.5 | Left prose, right river, two lower insets | 3 | elevated valley | green/ochre day |
| 1.19.6 | Left prose, right stadium, two lower insets | 3 | elevated architecture | stone/olive day |
| 1.20.1 | Left prose, right street, two lower insets | 3 | oblique street | ochre warm day |
| 1.20.2 original | Left prose, right temple, two lower insets | 3 | oblique interior | amber warm interior |
| 1.20.3 following | Left prose, right sanctuary, two lower insets | 3 | oblique sanctuary | ochre/olive day |
| 1.20.4 following | Left prose, right odeion, two lower insets | 3 | elevated architecture | ochre/blue day/night |

## Three compositions considered before art

1. **Selected: one expansive workshop tableau above two ordered prose fields.** Near eye level, Praxiteles' alarm and Phryne's calm sit beside the two sculptural works. The full passage reads left then right below. One image and two lower text masses abandon the old sidebar, differ from the six predecessors and avoid both following pages.
2. A workshop-and-temple diptych above prose. Rejected: it divides attention and adds a second image that does little for orientation.
3. A central standing Eros object portrait with text on both sides. Rejected: the lost work's exact form is unknown, and the human stratagem would disappear.

Canvas 1800×1600. Header y=16–133; art `(34,151)–(1766,1120)`, aspect 1.79:1 after final review; caption y=1130–1182; headings y=1190–1238; translation left `(34,1238)–(875,1572)` for sentences 1–2, right `(925,1238)–(1766,1572)` for sentences 3–5. Reading order left to right. Renderer loads SQLite, asserts exact reconstruction, wraps each text block with Pillow, reserves 12px padding, checks actual glyph bounds and fails below 29px body minimum. Text fit preceded art generation.

Art: one sophisticated painterly fourth-century BCE Athenian workshop scene, medium-wide eye-level through a doorway. Fully clothed Praxiteles hurries in, fully clothed Phryne remains calm, and two distinct carved works—young Satyr with cup and fully draped Eros—are visible. The arrangement and likenesses are interpretive. No actual flame, smoke, injury, nudity, modern object or baked-in lettering. Cool doorway daylight, warm reflected marble, charcoal/slate shadow and muted terracotta change camera, palette, lighting and people/object balance from 1.20.1's elevated ochre street. Local orientation names Athens and the nearby Dionysus precinct without assigning an exact workshop address.

## Review and promotion

The first component was corrected because the Satyr appeared too mature and Eros did not clearly read as a youthful male figure. The accepted revised component has a cup-bearing boy Satyr and a fully clothed youthful Eros. The initial component is retained. The first page render left excess blank lower space; the art and text masses were adjusted before final candidate review. Eight deterministically measured blocks **PASS**, 12px padding, complete exact SQLite translation in order at 34px body and at least 23px auxiliary type.

Final `candidate.png` inspected at full size, beside the original and the six preceding/two following actual PNGs in `graphic_book/output/replacements/1_20_2/20261006T171310Z/comparison.png`. The single broad workshop image and lower prose pair are visibly distinct from the repeated left-sidebar arrangement and a stronger first-glance page than the original. The false alarm, the choice of Eros and the two statues are directly legible; the temple catalogue remains verbatim in prose. Art quality, historical framing, orientation, semantic fit, content suitability, text clearance and variety **PASS**. The preview image tree substituted only the candidate, built 158 illustrated passages and a 159-page PDF; reader identifies 1.20.2 as 115 of 158. Temporary PDF page 116 was visually inspected and **PASS**.

The original `graphic_book/images/1/20/2.png` SHA-256 `e7cfb57f99126ef8fe84edfc7829b38abcf631dc89daca6a7c5a6ba42bd3ff49` was copied to `revisions/20261006T171310Z/previous-page.png` alongside previous renderer and page-plan text; local copy and downloaded S3 asset both matched. S3 archive key: `s3://pausanias-graphic-book-assets-849621205733/assets/generated/1_20_2/revisions/20261006T171310Z/previous-page.png`. After archive verification and a final original-hash recheck, the candidate was atomically promoted. Accepted image SHA-256 `2d74d5f6e072a0d36869c05890403238518edcd88d13241b3daaa94c5d57ba59` matches local, raksasa and downloaded S3 copies independently. Accepted component hash `53f9cd4ce8412baab5d03f3de3e0a5de7f4eadd3beb70ece3eb1ef96159504bf` matches local and downloaded S3 asset. Normal bounded build **PASS**, 158 illustrated passages and 159 PDF pages. Combined backup push/verify **PASS**, 438 component assets, matching local/S3 manifest and finished pages on raksasa/S3. The normal PDF page 116 raster matched the reviewed temporary PDF page. Replacement source commit `fe5eb27e4a809ec405eb7155a340565b5cbb1909` was pushed to `origin/main`.
