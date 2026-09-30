# Passage 1.24.7 — page plan (2026-10-01)

## Source and six preceding accepted pages

The complete English translation is read verbatim from the local SQLite `translations` table. It describes the standing Athena Parthenos: long robe, ivory Medusa head, Nike, spear, shield, nearby serpent and Pandora relief on the pedestal. It then mentions Hadrian and Iphicrates. The visual is an interpretive reconstruction of Pausanias's description, not a claim that the lost statue's exact appearance is known.

Craft anchors visually inspected: 1.1.4 and 1.1.5. Their finish and typography are references; their left sidebars, ochre palette and inset furniture are not copied. Actual preceding PNGs were compared at thumbnail scale in `tmp/2026-10-01-preceding-contact.jpg`; their plans were read.

| Passage | Large image/text masses and translation placement | Scenic panels | Viewpoint | Dominant palette and light |
| --- | --- | ---: | --- | --- |
| 1.24.1 | Broad upper gallery; two prose fields below | 1 | medium-wide oblique | pale marble and bronze; pearly daylight |
| 1.24.2 | Four prose fields above broad bull image | 1 | low close terrace | teal patina and grey; overcast |
| 1.24.3 | Square upper-left statue; prose right and below | 1 | eye-level medium | storm blue-grey; diffuse |
| 1.24.4 | Central wide ritual scene between upper and lower prose | 1 | ground-level wide | limestone and olive; clear morning |
| 1.24.5 | Diagonal pediment and helmet diptych; prose opposite | 2 | oblique facade, close object | marble blue and gold; midday and cool spot light |
| 1.24.6 | Wide upper griffin panorama; two prose columns below | 1 | low, near foreground | lapis/slate/muted gold; cold dawn |

## Three compositions considered before art

1. **Selected: full-height sculptural portrait with ordered right-hand reading sections.** A tall, finely modelled view of Athena and the pedestal occupies the left half; three measured prose sections descend on the right, covering statue, pedestal/Pandora, and Hadrian/Iphicrates in source order. One strong art panel provides the best scale for Medusa, Nike, shield, serpent and Pandora. The image extends almost the full page height, unlike 1.24.3's upper-left square with prose both to the right and below. It is visibly different from both immediate predecessors and has no left-hand translation sidebar.
2. A wide, low close-up of the pedestal above a prose band. Rejected because it would hide the upright statue and repeat 1.24.6's large-upper-art/lower-text mass.
3. A diagonal diptych of Athena and the entrance monuments. Rejected because it repeats 1.24.5 at thumbnail scale and would imply an unsupported exact arrangement of Hadrian and Iphicrates.

## Pre-art text fit and illustration brief

Canvas 1800×1600. Header `(35,16)–(1765,126)`. Tall art `(35,145)–(925,1514)` (aspect 0.650); a narrow caption follows below. Right-hand ordered prose fields at x=`957–1765`: first five sentences through Erichthonius, Pandora account, then Hadrian/Iphicrates. Subject headings and an orientation line are separate measured blocks. Reading order is top to bottom on the right; the complete translation is asserted against SQLite. Minimum body size 28px, preferred 34px; 12px internal padding. All blocks must fit before art is commissioned. The first rendered version had a tall left prose field, so it was rejected at thumbnail review and the geometry revised before acceptance.

Illustration: one sophisticated painterly historical reconstruction, generated at portrait aspect 0.630 and cropped minimally to 0.650. Eye-level but slightly upward view from within the fifth-century BCE Parthenon cella, near enough to read the statue's surface and pedestal relief, far enough to show full standing figure and feet. Athena is fully robed to the feet, carries a spear, holds a small winged Nike, wears an ivory Medusa head on her breast, with shield at feet and a single serpent beside the spear. A modest relief on the pedestal evokes Pandora's birth, without lettering or spurious certainty about exact lost forms. Warm ivory, aged gold, deep green-black shadow and restrained cool daylight entering the interior. The bright detailed statue must dominate over architecture. No separate Hadrian or Iphicrates figures are invented. No modern building, exposed body, pseudo-inscription, extra appendage, diagrammatic rendering or generated text. The first art version exposed the central figure in the relief; a targeted edit clothed it and that corrected component is used. Compared with 1.24.6, the scene changes from wide outdoor legendary landscape to close vertical architectural/object portrait; cold dawn slate changes to warm ivory and green-black interior light; no humans or wild terrain.

## Review status

Pre-art and final deterministic fit PASS: ten measured text items, 12px padding, complete verbatim SQLite translation reconstructed in source order in three fields, all body text 34px and auxiliary text 23px or larger. The first full-size render was rejected because its tall left text field broke the five-page sidebar limit. Revised final 1800×1600 PNG was visually inspected at full size and against the six actual predecessor PNGs in `tmp/2026-10-01-comparison-final.jpg`. The one tall left image and three right reading sections differ from both 1.24.5 and 1.24.6 at thumbnail scale. Its composition occurs once in candidate plus five; no left translation sidebar. The visual has clear Acropolis/Parthenon orientation in the local header, and the caption marks the art as interpretive. Medusa, Nike, spear, shield, serpent and pedestal relief are legible; the corrected relief is fully clothed. Text, caption, labels and art have no clipped or crowded edges. Compared with 1.24.6, camera distance, viewpoint, palette, lighting and landscape/object balance all change. Full-size art quality, semantic/historical care, spatial orientation and variety PASS against 1.1.4 and 1.1.5.

Bounded build PASS: 152 illustrated passages; reader `1/24/7.html` identifies 152 of 152 and the correct PNG; PDF has 153 pages and final page 153 was rasterised and visually inspected with full text and no clipping. Combined backup push/verify PASS: 421 component assets; local assets, S3 manifest, S3 finished pages and raksasa pages match. Independent local/raksasa/downloaded-S3 finished-page SHA-256 `72500e594036b8b98316c5013380ca77f71d7d8a11c0cc83fb01e4416b4ec3bf`; corrected component local/downloaded-S3 SHA-256 `bd840b685e4c0fc380bc4c6adb87baa20d39b9b6c78e4b89c4e82dec2481118e`. Source commit and push pending.
