# Replacement plan — Pausanias 1.21.7

replacement_status: accepted
Run: `20261008T171009Z` for daily generation date 2026-10-09. Original canonical SHA-256: `d8a4d4b743b8d0e38e4887bf0dac9d74e68200cc437a55802bb99d21f0a73110`. Original renderer and plan were copied to `revisions/20261008T171009Z/` before editing; original component art remains. The first shuffled eligible passage was 1.21.7, visually confirmed as a tall left prose panel, large right image, and two lower insets. Approved craft anchors 1.1.4 and 1.1.5 were inspected.

## Actual target-context PNGs

| Passage | Composition / prose | Panels | Viewpoint | Palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.21.1 | left sidebar, large right theatre scene, two lower scenes | 3 + locator | elevated theatre and medium scenes | ochre/blue, warm day |
| 1.21.2 | left sidebar, large right dream scene, two lower scenes | 3 + locator | mid-distance dream | brown/violet, dusk |
| 1.21.3 | left sidebar, large right slope scene, two lower scenes | 3 + locator | elevated slope | ochre/brown, daylight |
| 1.21.4 | upper paired prose, wide lower spring sanctuary | 1 | eye-level interior and water | cream/blue-green, diffused day |
| 1.21.5 | left sidebar, large right cuirass, two lower scenes | 3 + locator | close object and action | ochre/brown, warm day |
| 1.21.6 | left sidebar, large right armour workshop, two lower scenes | 3 + locator | close workshop | brown/bronze, warm indoor light |
| **1.21.7 original** | tall left prose, large right sanctuary, two lower material insets | 3 | oblique corselet and grove | ochre/green, warm day |
| 1.22.1 | left sidebar, large right Acropolis ascent, two lower scenes | 3 | elevated approach | ochre/green, sunlit |
| 1.22.2 | left sidebar, large right Phaedra scene, two lower scenes | 3 | medium figure | ochre/blue, sunlit |

The original and all eight neighbors were inspected as actual PNGs in `tmp/1_21_7_original_context.png`; plans were read where available. The original's repeated architecture is especially visible beside 1.21.5, 1.21.6, 1.22.1 and 1.22.2.

## Three compositions before art

1. **Selected: a single broad, close object-and-grove painting across the upper two thirds, with the complete passage in three ordered lower prose fields.** A linen corselet is the foreground subject; grove and sanctuary behind locate Gryneium. No insets or leader labels. The large image/text silhouette abandons the left sidebar and is unlike either predecessor or following page. In the candidate plus five predecessors, this upper-art/lower-three-prose layout appears once.
2. A central corselet detail with prose on both sides. Rejected because the narrow side text would echo the sidebar rhythm of 1.21.5 and 1.21.6, and a similar central-object distribution appears elsewhere nearby.
3. A horizontal sequence of linen, spear, hunting and dedication. Rejected because it would make the dramatic claims look like verified modern material tests, and four scenes would inherit the original's over-panelled impression.

## Pre-art fit and art direction

Canvas 1800×1600. Header and orientation occupy y=16–134. Main art `(34,150)–(1766,1055)`, aspect 1.91:1. A short measured caption sits below. Three exact SQLite sentences flow in source order through lower fields `(34,1140)–(560,1564)`, `(586,1140)–(1114,1564)`, `(1140,1140)–(1766,1564)`. The last is wider for the longest sentence. Text uses deterministic Pillow fit with 12px padding and an explicit minimum, before any art is commissioned.

Main raster: a museum-quality painterly, historically restrained close object study of a layered linen corselet hanging in an open Greek sanctuary portico at Gryneium, with a lush Apollo grove and hint of the Aeolian coast through the columns. Eye-height, near enough to see cloth weave and seams, one dominant cuirass, plausible timber suspension and restrained Greek masonry. Cool pearl and indigo shadow, fresh green foliage, soft sea daylight rather than the original's golden warmth. Fully clothed distant people only if needed for scale; no battle, wounded animal, lion, test spear, fake inscription, labels, letters or drawn callouts. Sanctuary architecture and corselet construction are interpretive rather than excavated facts. Gryneium is explicitly named in the orientation text as coastal Aeolis, western Asia Minor.

Compared with 1.21.6, this is a close outdoor/portico object study rather than a warm indoor workshop; the cool pearl/green palette and clear sea light replace brown/bronze and warm indoor light. The balance moves from craftsman/workbench to cloth object/grove. No tall left translation sidebar.

## Review and verification

The candidate at `graphic_book/output/replacements/1_21_7/20261008T171009Z/candidate.png` was opened at full 1800×1600 and compared beside the original, its six predecessors, and two followers in `tmp/1_21_7_candidate_context.png`. The one broad image above three prose fields visibly improves the hierarchy and escapes the target neighborhood's left-panel grid. It differs from preceding 1.21.5/1.21.6 and following 1.22.1/1.22.2, and appears once in candidate plus five predecessors. Rich fabric weave, distinct grove and coast, historical restraint, orientation, suitability, and no irrelevant callouts **PASS**. The scene is interpretive, with no staged material-performance claim. Seven measured blocks with 12px padding passed, including exact 468-character SQLite translation in order at 35px body type; no caption or label crowding.

A temporary image tree substituted only the candidate while the canonical original remained untouched. Temporary HTML/PDF build **PASS**: 160 illustrated passages, reader 1.21.7 is 127 of 160, and PDF has 161 pages. The temporary reader image and candidate hashes match `94669cc9995841e251e6357d7bab9d0f8198fa1a936f799b3035254bcb8930a7`; PDF page 128 was rasterized and visually inspected.

The original was copied to `graphic_book/assets/generated/1_21_7/revisions/20261008T171009Z/previous-page.png`, alongside the previous renderer and plan. Local original, archive, and downloaded S3 archive all have SHA-256 `d8a4d4b743b8d0e38e4887bf0dac9d74e68200cc437a55802bb99d21f0a73110`. S3 key: `s3://pausanias-graphic-book-assets-849621205733/assets/generated/1_21_7/revisions/20261008T171009Z/previous-page.png`. Asset push and verify **PASS**, with 444 assets; revised component's downloaded S3 SHA-256 equals local `382f5bbc00d5c93b9310593784f252d5f1c13cf845066d73e541fc27735e3764`.

After the canonical original hash was rechecked, the candidate was atomically promoted at the same passage path. Normal HTML/PDF build **PASS**: 160 illustrated passages and 161 PDF pages; page 128 was visually inspected again. Combined backup push/verify **PASS** for 444 assets. The new canonical page, generated site copy, raksasa mirror, and downloaded S3 finished page have matching SHA-256 `94669cc9995841e251e6357d7bab9d0f8198fa1a936f799b3035254bcb8930a7`. The binary archive remains outside `graphic_book/images/` and no additional book page was created.
