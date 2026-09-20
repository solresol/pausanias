# Replacement page plan — 1.16.3

Replacement run `20260920T181257Z`, selected by the recorded 2026-09-21 optional-replacement draw and fixed shuffle. Original canonical SHA-256 before any candidate work: `44576508259723c68baff97142485ab7da2e29e06ae44cae14e3271db167b305`. The canonical original remains in place during planning and review. Its previous renderer and page plan are preserved under `revisions/20260920T181257Z/`.

## Why this page qualified

The actual original PNG was inspected at full size. It uses the repetitive arrangement targeted by the replacement procedure: a full-height left translation panel, one dominant upper-right landscape, and a row of three lower insets. It also carries many rounded labels and leaders, small prose, and a locator inset with substantial visual weight. The revision must abandon that arrangement while retaining the complete passage and its three linked historical acts.

## Target-context PNG comparison

The original, six preceding actual PNGs and two following actual PNGs were compared in `/tmp/pausanias-1-16-3-neighbors.png`; all available plans were read.

| Passage | Composition / translation | Panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.15.1 | Tall left prose; main upper-right Agora; three lower panels | 4 | Street-level/oblique Agora plus relief | Ochre, blue, parchment; warm daylight |
| 1.15.2 | Tall left prose; main upper-right stoa; three lower panels | 4 | Interior architectural view and narrative scenes | Red, ochre, blue; warm diffuse light |
| 1.15.3 | Tall left prose; main upper-right Marathon; three lower panels | 3 | Elevated battlefield panorama and close studies | Dry gold, blue, olive; daylight |
| 1.15.4 | Tall left prose; main upper-right shield display; two lower panels | 3 | Oblique object wall, aerial coast, close object | Bronze, pitch black, blue; warm light |
| 1.16.1 | Tall left prose; main upper-right statues; three lower panels | 4 | Civic oblique view and narrative scenes | Ochre, bronze, blue; warm daylight |
| 1.16.2 | Tall left prose; main upper-right road scene; three lower panels | 4 | Eye-level road, relief map and narrative scenes | Brown, blue-grey, parchment; overcast daylight |
| **Original 1.16.3** | Tall left prose; main upper-right Seleucia; three lower panels | 4 | Elevated river-city panorama and insets | Gold, blue, parchment; clear daylight |
| 1.17.1 | Tall left prose; main upper-right Agora; three lower panels | 4 | Oblique civic scene, aerial and close scenes | Ochre, green, parchment; warm daylight |
| 1.17.2 | Tall left prose; main upper-right approach; three lower panels | 4 | Oblique civic architecture and narrative insets | Ochre, blue, parchment; warm daylight |

The whole neighborhood repeats essentially the same thumbnail-scale structure. The candidate must be unique in the target-plus-five window and must not copy either following page.

## Three materially different replacement compositions

1. **Selected — asymmetric historical tableau above two prose columns.** A broad Seleucia-on-the-Tigris panorama occupies the upper-left two-thirds; two smaller but substantial horizontal scenes stack at upper right, Apollo at Branchidae above Babylon and Bel below. The lower third becomes two large numbered prose columns in original order. This gives the page a strong art band and a spacious reading band, removes the sidebar and lower inset strip, and lets each of Seleucus' three acts remain visible without a locator map.
2. **Single river panorama with prose below.** Rejected because it would make the Apollo restitution and preservation of Babylon depend entirely on prose, weakening the passage's three-part historical logic.
3. **Central bronze Apollo object study with opposed prose and a low twin-city frieze.** Rejected because it would overstate one object, visually diminish Seleucia and Babylon, and require a speculative composite geographic frieze implying the two cities were seen together.

## Subjects, orientation and evidence boundary

The broad panel is a rich illustrative reconstruction of Seleucia's river approach: Tigris, masonry quays, arriving Babylonian households and a planned Hellenistic city. The upper-right scene shows the fully draped bronze Apollo returned to Branchidae. The lower-right scene shows Babylon's wall, sanctuary of Bel and Chaldean community continuing. None asserts an exact recovered city plan, ceremony or sanctuary appearance. The route atlas is removed rather than given main-page authority; local scene labels provide the needed geographic sequence: `SELEUCIA · THE TIGRIS`, `BRANCHIDAE · IONIA`, and `BABYLON · THE SANCTUARY OF BEL`.

The complete exact SQLite text is split only at the sentence beginning `It was also Seleucus`, so the left column contains Seleucus' character and Apollo restitution, and the right column continues with Seleucia's foundation and Babylon's preservation. Reading order is explicitly numbered 1 then 2.

## Art and variety choices

The revision uses retained high-quality raster art under distinct `rev_20260920_*.png` filenames; the old components remain untouched. Enlarging these scenes and removing the old map, excess leaders and label boxes makes the scenic layer more legible and less diagrammatic without fabricating new events.

Compared with immediate predecessor 1.16.2, the candidate changes from an eye-level assassination road scene to a distant elevated river-city panorama; from a people/violence-led tableau to architecture, water, restoration and civic continuity; and from subdued brown/blue-grey overcast to bright river blue, bronze and sunlit masonry. These choices follow the passage's change from dynastic violence to public benefaction. No new nudity, violence or unsupported landmark is introduced.

## Measured preflight geometry

Canvas 1800×1500. Main art `(24,110)–(1180,850)`; Apollo `(1210,110)–(1776,455)`; Babylon `(1210,505)–(1776,850)`. Local labels sit within measured opaque strips at the top of each art rectangle. Captions occupy `(24,860)–(1180,945)` and `(1210,860)–(1776,945)`. Numbered reading headers are at y=965–1028; prose rectangles are `(24,1035)–(870,1476)` and `(930,1035)–(1776,1476)`. Body target 33px, minimum 29px; auxiliary minimum 23px; 12px padding. The renderer asserts exact normalized reconstruction and fails rather than saving on overflow.

## Review gate pending

Render only to `graphic_book/output/replacements/1_16_3/20260920T181257Z/candidate.png`. Inspect full size and compare against the original, 1.15.1–1.16.2 and 1.17.1–1.17.2 at thumbnail scale. Require complete text, clear orientation, direct semantic fit, suitability, absence of pseudo-text and measured clearance. Build and inspect a temporary HTML/PDF tree substituting only the candidate. If it is not a visible improvement, leave the canonical original unchanged and record rejection. `replacement_status` remains pending until archive, promotion, normal build, remote hashes, scoped commit and push all succeed.

## Accepted review and verification

replacement_status: accepted

Full-size candidate inspection PASS. All three retained raster scenes remain rich, dimensional and semantically direct; no scenic element is flat, schematic or newly fabricated. Local scene labels are exact and uncrowded. The page contains no nudity, violence, pseudo-writing, misleading leader or locator-map dominance. Eleven actual measured text blocks PASS with 12px padding; the complete SQLite translation is reconstructed exactly in original order at 33px, with auxiliary text no smaller than 25px.

Thumbnail comparison at `graphic_book/output/replacements/1_16_3/20260920T181257Z/comparison.png` PASS against the original, six predecessors and two following pages. The broad upper tableau and two-column lower reading band appear once in the target-plus-five window and do not copy 1.17.1 or 1.17.2. The candidate is visibly more focused and legible than the original: no sidebar, no lower inset strip, no locator, fewer panels and no leaders.

Temporary preview PASS using a temporary hard-linked image tree with only 1.16.3 substituted: 142 illustrations, 143 PDF pages; reader position 92 of 142 and PDF page 93 inspected. The canonical original remained at its recorded hash during preview. Original copied to `revisions/20260920T181257Z/previous-page.png`; local archive, independently downloaded S3 archive and canonical original all matched SHA-256 `44576508259723c68baff97142485ab7da2e29e06ae44cae14e3271db167b305`. Archive S3 key: `assets/generated/1_16_3/revisions/20260920T181257Z/previous-page.png`.

After the archive asset push/verify, the canonical hash was rechecked and the reviewed candidate atomically promoted. Candidate retained at `graphic_book/output/replacements/1_16_3/20260920T181257Z/candidate.png`; canonical `graphic_book/images/1/16/3.png`. After SHA-256: `c6f5ca56156c641185b80e8b0c7ea094d02aaabff3f474de6d2e5219cad39e87`. Normal rebuild PASS with 142 illustrations and 143 pages; final PDF page 93 raster is byte-identical to the reviewed temporary preview. Combined backup push/verify PASS with 400 component/archive assets. Independent local, raksasa and downloaded-S3 replacement hashes match. The new 1.23.7 page remained unchanged.
