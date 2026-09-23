# Page plan — 1.23.10

Run 2026-09-24. The earliest missing canonical image was verified in numeric passage order against the local SQLite `translations` table. The renderer loads the complete English passage verbatim and preserves its original order.

## Actual preceding PNG and plan review

The approved craft anchors 1.1.4 and 1.1.5 and the six required preceding PNGs were inspected individually at useful scale. Available plans were read; the actual PNGs establish the layout history below.

| Passage | Composition / translation placement | Scenic panels | Viewpoint | Dominant palette / lighting |
| --- | --- | ---: | --- | --- |
| 1.23.4 | Central tall sculpture with opposed prose blocks | 1 | Close low three-quarter | Bronze, umber, limestone; warm raking light |
| 1.23.5 | Broad maritime panorama above two prose columns | 1 | Distant sea-level | Petrol blue and silver; storm daylight |
| 1.23.6 | Two equal tall scenic wings around central prose | 2 | Close onboard and medium shore figures | Wine, linen, jade and russet; clear lateral light |
| 1.23.7 | Unequal architectural diptych; compact upper-right prose | 2 | Oblique court and low wetland approach | Bronze, malachite, indigo and celadon; cool clear/overcast light |
| 1.23.8 | Broad bronze-horse portrait over two prose columns | 1 | Close low front-quarter | Charcoal bronze, rose and violet; hard dawn light |
| 1.23.9 | Staggered prose/art then art/prose rows | 2 | Eye-level medium outdoor scenes | Pale stone and blue-green shadow; crisp midday light |

## Three materially different compositions considered before art

1. **Selected — central civic portrait with opposed prose.** One tall, richly detailed scene of Phormio and the Athenian settlement of his debts occupies the middle of the page. The first prose block at left covers his standing, debt and retirement to Paiania; the second at right covers his election, refusal to sail and the Athenians' response. This family last occurs at 1.23.4, outside the five-predecessor counting window, so it appears once in the candidate-plus-five window. It repeats neither 1.23.8 nor 1.23.9 and uses no tall left translation sidebar.
2. **Three-part narrative sequence: Paiania, election, fleet.** Rejected because three scenic panels would encourage invented successive action and reduce the public debt settlement to a small illustration.
3. **Broad harbour scene above two prose columns.** Rejected because it would be a third broad-image/lower-band page in the active six-page window and would imply a voyage that Phormio explicitly says he cannot yet undertake.

## Passage subject and historical orientation

The single scene is an interpretive civic moment in Athens after Phormio has been chosen as admiral: a mature, dignified Phormio in a plain dark-blue himation stands beside an Athenian magistrate at a wooden table where weighed silver and tied wax tablets represent the public settlement of debts. Two soberly dressed creditors or witnesses receive the settlement; an admiral's folded cloak and command staff lie ready but are not yet worn. Through a deep colonnade, only trireme masts and rigging are visible, making the purpose of the decision legible without depicting a departure or battle. No readable inscription, decree text, coin enlargement, literal cancellation marks, triumphal gesture, courtroom drama, modern ledger, armour fantasy or unsupported named building.

The local orientation line names Athens and the naval command; the first prose heading names Paiania so the earlier retirement remains geographically clear. The artwork is explicitly interpretive and does not claim the exact mechanism, room or appearance of the lost event. It remains semantically direct without its caption: civic payment, a reluctant commander and the waiting fleet are visible together.

## Pre-art geometry, text fit and art choices

Canvas 1800×1600. Central art `(520,138)–(1280,1460)`, ratio 0.575:1. Left prose group uses `(24,170)–(485,1185)` and the right group `(1315,270)–(1776,1335)`, split exactly before “When the Athenians elected”. The left orientation sits below its prose; the central caption sits below the art. All exact text is locally rendered and measured with 12px padding. Body text must fit at no less than 29px and auxiliary text at no less than 24px; the renderer fails before saving on overflow and asserts normalized equality with SQLite.

Compared with 1.23.9, the page changes two staggered exterior scenes and diagonal prose rhythm into one close central interior with balanced opposed reading fields. Camera distance moves from medium environmental views to an intimate eye-level civic tableau; cool slate, faded indigo, silver and muted red replace pale stone and clear blue-green midday. People, hands, tablets and coin dominate over road, tomb and outdoor architecture. Strong north light enters through the colonnade, with warm lamplight at the table rather than the preceding page's even midday illumination. These choices directly serve the passage's tension between private debt and public command.

## Review gate pending

Require full-size inspection and an actual seven-page thumbnail comparison; craft against 1.1.4 and 1.1.5; complete passage and ID; semantic and geographic orientation; no invented voyage, pseudo-text, schematic art or modern objects; and measured clearance for every block. Then inspect the bounded local HTML/PDF build, complete combined backup push/verify, and commit/push only scoped source artifacts while preserving the pre-existing README modification.

## Accepted full-size and thumbnail review

Built-in image generation supplied an initial scene and one targeted correction. The first image had the intended people, payment table, harbour depth and finish, but failed the no-pseudo-writing gate because generated marks appeared on several tablets. The correction removed those marks and left plain bound wooden or wax tablet surfaces while preserving the figures, silver, balance, table, lamp, command staff, folded cloak, columns, ships, crop, palette and lighting. Both generated versions are retained under distinct component filenames; both prompts are recorded.

The corrected 1800×1600 candidate was inspected at full size. Phormio remains a dignified, visually dominant figure; the magistrate's balance and silver, blank bound tablets, witnesses, command staff and waiting ships make the passage's civic decision legible without a battle or departure. Linen, wool, wood, stone, metal, skin and harbour atmosphere are richly modelled at the anchor standard. All figures are fully clothed. There is no readable or pseudo-writing, nudity, violence, triumphal crowd, modern object, schematic inset or misleading callout. The owl device on the folded cloak reads as restrained Athenian symbolism, not a textual inscription. The local headings distinguish Paiania retirement from Athenian naval command, and the caption marks the scene as interpretive.

The actual candidate-plus-six comparison at `graphic_book/output/1_23_10-comparison.jpg` PASS. The single tall central scene with opposed prose differs at thumbnail scale from 1.23.8's broad object portrait over prose and 1.23.9's staggered two-row layout. Its family last occurs at 1.23.4, outside the five-predecessor counting window, so it appears once in the candidate-plus-five window. There is no tall left translation sidebar. Close eye-level interior portraiture, cool slate and indigo, warm table light, people, hands and civic objects vary from 1.23.9's two medium outdoor scenes, pale stone, blue-green shadow, road and sculpture.

Deterministic text fit PASS: nine measured actual text blocks with 12px padding; complete SQLite translation in original order at 34px and 32px; auxiliary minimum 27px. Full-size inspection confirms the passage ID, passage, headings, orientation and caption are complete, legible and clear of all borders. The corrected candidate is accepted for the canonical path.

## Build and backup verification

The requested bounded graphic-book build PASS: 145 illustrated passages and 146 PDF pages. Reader HTML identifies 1.23.10 as 145 of 145 and references the correct PNG. PDF page 146 was rasterised and visually inspected; the artwork and complete passage are legible and unclipped. Full `create_website.py` was not run.

Combined backup push and verify PASS. The raksasa finished-page mirror, S3 finished pages, two new component rasters, S3 component manifest and local asset manifest agree; 406 component assets verified. Independent local, `pausanias@raksasa`, and downloaded-S3 finished-page SHA-256 is `caccb874fa5f4a6a6190e101c90a8b15a29bb119ac9c81719f727e12010fc79a`. The corrected component local/downloaded-S3 SHA-256 is `f5ed5004005420ba10402a74c11cee2f1489a94f91f58e3928ca80169fcd4c02`.
