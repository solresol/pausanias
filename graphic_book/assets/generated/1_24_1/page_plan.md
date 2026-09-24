# Passage 1.24.1 — page plan

Run 2026-09-25. Earliest missing image verified from numeric SQLite translation order. The complete English passage is loaded verbatim by the renderer.

## Six preceding accepted pages, inspected as PNGs

| Passage | Composition and translation placement | Panels | Viewpoint | Dominant palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.23.5 | Broad maritime art above two prose columns | 1 | Distant, sea-level | Petrol blue, silver; storm daylight |
| 1.23.6 | Equal vertical scenic wings around central prose | 2 | Close shipboard and medium shore | Wine, linen, jade; clear lateral daylight |
| 1.23.7 | Tall architectural art left; prose and art stacked right | 2 | Oblique court and low wetland | Bronze, indigo, celadon; cool mixed light |
| 1.23.8 | Broad bronze-horse art above two prose columns | 1 | Close low front-quarter | Charcoal bronze, rose, violet; hard dawn |
| 1.23.9 | Staggered prose/art then art/prose rows | 2 | Medium, eye-level exteriors | Pale stone, blue-green shadow; midday |
| 1.23.10 | Central tall civic portrait with opposed prose | 1 | Close eye-level interior | Slate, indigo, silver; north/window and lamp light |

Approved craft references: 1.1.4 and 1.1.5, inspected visually. Their sidebar and ochre arrangement are not reused.

## Three compositions considered before art

1. **Selected: one panoramic sculptural-gallery view above a broad, two-part reading band.** The single art field presents two adjacent depicted myths as artworks on the Acropolis, so the visual directly answers the passage's repeated “represented” and “depiction.” The first sentence reads in the left lower field, and the remainder reads in the right lower field. The image-to-text silhouette belongs to the broad-art/lower-band family, last seen at 1.23.8: twice in the candidate-plus-five window, and neither immediate predecessor. No tall left translation sidebar.
2. Two equal facing myth scenes with a central narrow prose column. Rejected: repeats 1.23.6's art–text–art massing and implies that Pausanias witnesses live mythic events.
3. Athena portrait above a Theseus portrait with a central prose strip. Rejected: very wide, shallow art crops would weaken figure detail, and the duplicated horizontals overpower the short first sentence.

## Content, orientation, and art instructions

The first subject is Athena striking Marsyas the Silenus after he takes up discarded flutes. The second is the represented battle of Theseus and the Minotaur. The page should make clear that these are representations encountered in the Acropolis account, not documentary reconstructions of the mythic events. The local heading identifies the Acropolis. A caption states interpretive depiction. Avoid pseudo-writing, invented inscriptions, or a categorical image claim about the creature's nature: Pausanias explicitly gives “whether it was a man or beast.” Use a restrained hybrid form compatible with the received account, without gore or nudity. No locator map is necessary because the Acropolis setting is visible and named.

Art prompt: 16:9 to 2:1 horizontal scene for a 1752×890 target. Medium-wide oblique view along an ancient Acropolis gallery court, two richly modelled sculptural groups, Athena/Marsyas left and Theseus/Minotaur right. Avoid a didactic split-panel look. Cool pearly daylight, weathered pale marble, dark bronze, olive-green shadow. Compared with 1.23.10: wider camera distance and oblique viewpoint replace close frontal interior; daylight and marble/olive bronze replace dim slate/indigo lamplight; artworks and architectural setting replace the table of people and objects. Each change follows Pausanias' description of depicted mythic works.

Canvas 1800×1600. Header and orientation `(24,20)–(1776,122)`. Art `(24,136)–(1776,1036)`, aspect 1.947:1. Short caption `(24,1043)–(1776,1103)`. Lower first translation `(24,1150)–(865,1540)`; second `(925,1150)–(1776,1540)`. Numbered reading heads above both. Complete source passage is split only at “Beyond these things I have described”; the renderer checks the reconstructed exact whitespace-normalized text against SQLite. All text uses deterministic fitting with 12-pixel padding; minimum passage size 29px and minimum auxiliary size 24px. The preflight must pass before art generation. No text or label is requested in generated art.

## Post-render review

Built-in image generation supplied a first panoramic component and one targeted background correction. The first included a modern-looking distant settlement and a temple-topped hill despite the scene already being on the Acropolis; it was rejected. The corrected art retains the four foreground bronze figures and replaces that distant background with unbuilt Attic hills and olive groves. Both raster versions are retained under distinct ignored component filenames; both prompts are tracked.

Full-size candidate review: 1800×1600 PNG, richly modelled bronze, fabric, marble, hands and architectural depth. The two depicted myths read clearly without invented labels. No pseudo-writing, modern city, schematic art, nudity, gore, misleading callouts or cramped local text. Pausanias' uncertainty about the Minotaur remains explicit in the verbatim prose and the caption identifies the artwork as interpretive. The Acropolis heading and court establish orientation. The one panoramic field is visually strong beside 1.1.4 and 1.1.5.

Deterministic fit: eight measured text blocks with 12px padding; complete SQLite translation in original order at 36px; auxiliary minimum 27px. Text fit PASS. Variety: broad-image/lower-band family occurs at 1.23.8 and 1.24.1, twice in the candidate-plus-five window. The candidate does not repeat 1.23.9's alternating rows or 1.23.10's central portrait. No tall left sidebar. Compared with 1.23.10, camera distance, viewing angle, daylight palette and subject balance all vary. Visual and variety checks PASS.

Local reader build PASS: 146 illustrated passages; passage reader 146 of 146; PDF 147 pages, with page 147 visually inspected. Combined backup push/verify PASS with 408 component assets. Finished page SHA-256 `8698aafc0ca7b2e018f80a62305dc63c083f28d1c0668214f96a5f2a55962c5e` independently matches local, raksasa, and downloaded S3. Selected component SHA-256 `87a5847556e9ec0e9a6c3e67db21a04768bc95c7af60e80563e407904636a539` matches local and downloaded S3. No full website generation was run.
