# Pausanias 1.24.3 — page plan

Run 2026-09-27 Australia/Sydney. Earliest untranslated-image gap checked in numeric passage order against local SQLite. The renderer loads and verifies the complete English translation.

## Preceding accepted pages

Actual PNGs and available plans inspected; approved craft references 1.1.4 and 1.1.5 also inspected. Their old sidebar and ochre framing are quality references, not layout models.

| Passage | Composition / translation placement | Scenic panels | Viewpoint | Palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.23.7 | Tall art left; compact upper-right prose and lower-right art | 2 | Oblique court and low wetland | Bronze, indigo, celadon; cool daylight |
| 1.23.8 | Broad bronze horse above two prose fields | 1 | Close low front-quarter | Charcoal, rose, violet; dawn |
| 1.23.9 | Staggered prose/art then art/prose rows | 2 | Medium eye-level exteriors | Pale stone and blue-green shadow; midday |
| 1.23.10 | Central civic portrait with opposed prose | 1 | Close eye-level interior | Slate and indigo; window and lamp |
| 1.24.1 | Wide sculpture gallery above two prose fields | 1 | Medium-wide oblique terrace | Marble, olive, bronze; pearly day |
| 1.24.2 | Four upper prose fields over a broad bronze-bull scene | 1 | Close low oblique terrace | Teal patina and grey; overcast |

## Three compositions considered before art

1. **Selected: dominant square sculpture study at upper left, two reading blocks at right, then two broad concluding blocks across the foot.** The art concentrates on the statue of Earth beseeching rain, with Acropolis context and an olive tree/wave reference. The lower band carries the catalogue's later entries without requiring another illustration. The footprint differs from the preceding two pages: neither the 1.24.1 image-first/lower-prose structure nor 1.24.2 text-first/lower-image structure. One scenic panel, no tall left text sidebar. The general tall-art/side-text family is present once in the six preceding pages, at 1.23.7, so it occurs twice in the candidate-plus-five window only if counted broadly; in that narrower window it occurs once.
2. **Rejected: wide Acropolis panorama with two lower prose columns.** This repeats 1.24.1's large masses and would spread a catalogue of small works across an indistinct scene.
3. **Rejected: four equal object panels with a central prose spine.** It resembles a diagrammatic specimen sheet, makes the long verbatim prose difficult to read, and implies confident reconstructions of several lost works.

## Content and pre-art geometry

The passage is an Acropolis catalogue: Athena Ergane, Hermae, the deity of earnestness, Cleoetas' helmeted man with silver fingernails, Earth beseeching Zeus for rain, the tombs of Timotheus and Conon, Procne and Itys, Athena's olive tree and Poseidon's wave. The main illustration should show a fully draped sculpted Earth, arms raised toward heavy rain clouds above an ancient Athenian sanctuary court. A mature olive tree and a carved wave motif may appear in the setting. These are interpretive representations of works, not a claim about exact surviving shapes, relative placement, or a literal encounter with Zeus. No invented inscription, thunderbolt, child-harm scene, exposed body, modern Athens, or readable text baked into art. The local header names Athens and the Acropolis; the caption states the interpretive status.

Canvas 1800×1600. Header across `(24,18)–(1776,130)`. Art `(24,154)–(1080,1220)` (near-square, eye-level art). Right reading field `(1110,172)–(1776,1220)`, split into two parts. Lower reading band `(24,1242)–(1776,1530)`, split into two parts. Reading order: right-top 1, right-lower 2, lower-left 3, lower-right 4. The art does not carry long text. Every locally drawn title, label, prose block and caption is measured in a target rectangle with padding and a minimum font size; the joined prose must exactly match SQLite before art generation.

Art prompt: near-square high-resolution finished painterly archaeological illustration, eye-level close view of an imagined fully draped ancient Greek votive statue of Earth with uplifted hands, on a plain stone base within an Athenian Acropolis sanctuary court. A mature olive tree at one edge and a small carved sea-wave relief on a distant block, historically plausible architecture and Attic hills visible, gathering blue-grey rain clouds but dry stone in the foreground. Rich stone, bronze and leaf texture, deep spatial layers, restrained muted blue/green/umber palette, cool diffuse storm light. No text, inscriptions, borders, nudity, violence or modern structures. Reserve no text area within the art; target crop ratio 1056:1066. Compared with 1.24.2: eye-level near-square statue study rather than low wide bronze-animal view; blue-grey storm atmosphere rather than teal/grey luminous overcast; the balance favours a draped human-form statue and olive tree rather than a single foreground animal.

## Review and verification

Preflight and final render PASS: 12 deterministically measured blocks with 12px padding; all text is within its target rectangle. Passage text is 34/32px, auxiliary minimum 23px. The four translation blocks reproduce SQLite exactly and in order.

The initial generated art placed a second Acropolis in the distance, modern-looking rooftops, and unrelated small sculpture. A targeted edit retained the Earth statue, olive tree, clouds and wave motif while replacing the horizon with Attic hills and removing the extra statuary. Initial and accepted component binaries are retained in the asset cache. The final page was opened at full size; the statue is richly modelled, the page has clear Acropolis orientation, the art directly illustrates the rain petition and olive/wave subjects, and there are no pseudo-inscriptions, exposed bodies, irrelevant leaders or cramped boxes. Art, semantic fit, historical care, suitability, hierarchy and text checks PASS against 1.1.4 and 1.1.5.

The seven-page thumbnail comparison at `tmp/1_24_3-comparison.jpg` shows a dominant near-square image with right-side reading blocks and a lower concluding band. It is distinct from the immediately preceding text-top/art-bottom and art-top/text-bottom silhouettes. The family occurs at most twice in the candidate-plus-five window, with no tall left translation sidebar. Eye-level statue study, near-square viewpoint, blue-grey storm palette and human/olive focus vary camera angle, subject balance, palette and lighting from 1.24.2. Variety PASS.

Bounded HTML/PDF build PASS: 148 illustrated passages, reader page 1/24/3 links to the new PNG, PDF has 149 pages; PDF page 149 was rasterised and visually inspected. Combined backup push/verify PASS: 412 asset files; local asset cache, S3 manifest, S3 pages and raksasa pages agree. Independent local/raksasa/downloaded-S3 finished-page SHA-256 `1967f108364a2d943ba346651b5a4ec65cf78e3f730a65b32caddedc31278792`; selected component local/downloaded-S3 SHA-256 `d9b1f9d02a9ca7065783a16f67fa97759b3f14cd3a75ea335b643320408d7f1f`. Source commit pending.
