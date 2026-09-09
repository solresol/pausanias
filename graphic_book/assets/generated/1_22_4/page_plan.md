# Page plan — 1.22.4

Selection: earliest numeric translated passage missing its PNG in local pausanias.sqlite, checked 2026-09-10. Exact complete translation is loaded by renderer; measured BEFORE generation. Original sentence order flows left to right through two lower columns. Both fit at 26px; auxiliary minimum actually used 20px, with 12px padding and actual bounding-box validation. Canvas 1600x1280; art rectangle (24,90)-(1576,910).

## Actual recent-image inspection

All six actual PNGs compared in a contact sheet, alongside approved craft anchors 1.1.4 and 1.1.5 (also opened individually). Plans read for 1.21.5, 1.21.6, 1.21.7 and 1.22.1; no page_plan.md present for 1.22.2 or 1.22.3.

| Passage | Large masses / translation | Scenic panels | Viewpoint | Palette / lighting |
| --- | --- | --- | --- | --- |
| 1.21.5 | tall left text, upper-right object, two lower insets; small locator | 3 + locator | close armour, eye-level gallery | bronze/brown, warm interior side light |
| 1.21.6 | tall left text, upper-right workshop, two lower insets; small locator | 3 + locator | close angled workbench | dark umber/tan, warm workshop light |
| 1.21.7 | tall left text, large upper-right art, paired lower panels | 3 | close dedication and eye-level grove | olive/tan, filtered warm daylight |
| 1.22.1 | tall left text, large upper-right art, paired lower panels | 3 | distant oblique ascent | ochre/olive, warm side light |
| 1.22.2 | tall left text, large upper-right art, paired lower panels | 3 | medium courtyard view | ochre/green, warm daylight |
| 1.22.3 | tall left text, large upper-right art, paired lower panels | 3 | medium eye-level sanctuary | cream/ochre/green, warm daylight |

## Three alternatives

1. SELECTED: one broad architectural portrait of the western approach, above a full-width two-column translation band. Explains the single entrance and Nike's position on the right; lets monumental stone dominate. No scenic insets. Top heading and restrained local identifiers; no leaders needed.
2. Asymmetric diptych: entrance beside a southwest sea view, translation in a shared lower band. Rejected because this divides the gateway's architectural scale and introduces a second panorama for a brief concluding reference.
3. Central roof/coffer study with four surrounding prose blocks. Rejected because it obscures the approach and temple relationship and fragments a short passage needlessly.

## Art and interpretation

A low western approach looking east, with Propylaia centered and the smaller Ionic Nike temple on its southwest bastion to viewer's right. White marble, cool slate-blue sky and silver morning light; tiny fully clothed visitors establish scale. Unidentified horseman statues, fully clothed, remain secondary. No Aegeus death scene, no attribution of riders to Xenophon's sons. Architecture is illustrative, not a measured reconstruction; no claim to exact sculptural appearances. No sea behind the gateway in this eastward view.

Compared with 1.22.3, change at least: camera distance (medium to broad), viewing angle (eye-level sanctuary to low uphill approach), dominant palette (ochre to cool white/slate), lighting (warm to silvery morning), subject balance (people/cult statues to monumental architecture). All serve the passage's scale and ascent.

Geographic orientation explicitly identifies Athens, western approach, looking east. Propylaia and Nike identifiers sit beneath their corresponding structures. Primary checks: Acropolis Museum, https://www.theacropolismuseum.gr/en/node/16471 and https://www.theacropolismuseum.gr/en/other-monuments-periklean-building-programme/temple-athena-nike (consulted 2026-09-10; Nike on southwest bastion). Translation remains the authority for Pausanias' uncertainty and Aegeus tradition.

## Planned acceptance gate

Inspect full-size candidate and seven-page contact sheet; reject flat/diagrammatic art, wrong temple relationship, crowds, unsuitable exposure, text collisions or missing passage content. Candidate has zero recent composition matches (allowed <=2) and no left sidebar. Build and inspect HTML/PDF, then combined push/verify and scoped source commit/push. Existing README edit remains unstaged.

## Acceptance review — 2026-09-10

Built-in generated art revised once to remove the invented central pedimental sculpture and clean the distant skyline; both initial and final component rasters retained. Orientation strip moved into clear upper-right sky so it does not obscure the gateway roof.

Full-size 1600x1280 PNG reviewed: rich marble, masonry and rocky approach with atmospheric depth; no crude primitives, pseudo-writing, crowding or visible inappropriate exposure. Passage subjects read directly from art. Low western approach and right-hand Nike bastion are clear; no speculative death scene. Architecture remains explicitly illustrative. Identifiers sit under relevant structures and need no leaders.

Seven-page thumbnail comparison includes 1.21.5, 1.21.6, 1.21.7, 1.22.1, 1.22.2, 1.22.3 and candidate. PASS: one broad image with a lower two-column text band visibly breaks the preceding sidebar/inset arrangement. Neither predecessor matches; selected composition occurs once in the candidate-plus-five window; zero tall left sidebar on candidate. Palette, distance, angle, lighting and subject balance differ from 1.22.3. Craft quality checked against 1.1.4 and 1.1.5.

Text-fit PASS: all 8 actual bounding boxes inside 12px padding; complete verbatim SQLite passage preserved in order at 26px; smallest auxiliary 20px. Reviewed candidate copied without re-rendering to canonical image.

Local HTML/PDF build PASS: 131 illustrated passages, 132 PDF pages; HTML reader identifies 1.22.4 as 131 of 131 and uses the correct image. Rasterized PDF page 132 visually reviewed, complete and unclipped.

Combined backup push and verify PASS: raksasa finished-page mirror, S3 finished pages, two new component assets (initial and corrected), and 361-entry asset manifest agree. Independently downloaded S3 page and remote raksasa sha256sum both match local SHA-256: `41addbb16f16a806050b3e34f15be052688a4509acbf4bfa23fadc46e8221e10`.
