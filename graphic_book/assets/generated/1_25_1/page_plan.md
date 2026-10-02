# Pausanias 1.25.1 — page plan (2026-10-03)

## Source and recent visual history

Earliest translated passage in numeric local SQLite order without a canonical image: 1.25.1. Complete translation: 799 characters, loaded by the renderer from SQLite. Approved visual quality anchors 1.1.4 and 1.1.5 and actual PNGs 1.24.3–1.24.8 inspected at thumbnail scale, with their plans read. Anchor finish and typography guide the page, not their left sidebar or ochre layout.

| Passage | Actual composition and translation placement | Scenic panels | Viewpoint | Dominant palette and lighting |
| --- | --- | ---: | --- | --- |
| 1.24.3 | Square Earth statue upper left; prose right and foot | 1 | eye-level statue court | storm blue-grey and green; diffuse |
| 1.24.4 | Broad ox scene centred between upper and lower prose | 1 | wide ground-level | limestone/olive; clear morning |
| 1.24.5 | Diagonal pediment/helmet art with opposed prose | 2 | oblique architecture and close object | marble blue/gold; crisp and spot light |
| 1.24.6 | Wide upper griffin landscape, prose below | 1 | low, near foreground | slate/lapis; cold dawn |
| 1.24.7 | Full-height Athena image left, prose in right sections | 1 | upward interior portrait | ivory/gold/green-black; side light |
| 1.24.8 | Upper-left Apollo, lower panoramic Sipylus; prose upper right and foot | 2 | eye-height object and distant terrain | blue-green bronze/mauve; silver daylight |

## Three compositions considered before art

1. **Selected: central tall sculpture-court portrait, with the translation in two ordered side reading fields.** A single richly modelled Acropolis gallery view shows the relationship between Xanthippus and Anacreon and keeps Pericles visibly separate. The women's statues may occupy the further side of the court. The passage reads down the left field, then down the right. It is a different large-mass silhouette from both preceding pages and appears once in the candidate-plus-five window. No tall left translation sidebar: the left reading field is balanced by a same-size right field around central art.
2. **Rejected: full-width gallery above two prose columns.** The broad upper-art/lower-text arrangement repeats 1.24.6 at thumbnail scale and makes the several statues small.
3. **Rejected: four sculpture insets in a grid.** It risks a specimen-sheet effect, asks the art to assert exact lost forms, and weakens the coherent Acropolis orientation.

## Pre-art geometry and subject

Canvas 1800×1600. Header and orientation span width. Central art `(430,162)–(1370,1494)`, a tall 940:1332 portrait after thumbnail revision. Left measured prose `(34,230)–(412,1460)` and right prose `(1388,230)–(1766,1460)`; each has a compact heading. Reading order left then right. Passage split at the sentence beginning “His image is posed”; concatenated parts are checked against SQLite exactly. A short measured caption below the central image states that the lost works and their spatial arrangement are interpreted. Every title, orientation, body text and caption is fit into a target rectangle at or above a specified minimum with 12px padding; overflow fails before image creation.

A sophisticated historical illustration of an imagined fifth-century BCE Athenian Acropolis sculpture court: a draped, bearded Xanthippus statue beside a draped lyric-poet Anacreon statue with open singing posture, Pericles's draped statesman statue separated further back; two fully clothed female statues of Io and Callisto in the side depth. Their exact lost forms and arrangement are unknown, so do not imply an archaeological reconstruction. Stone platforms, Parthenon colonnade glimpsed in correct Acropolis context, distant Attic sky. The mythical transformation into cow and bear belongs to the prose, not a staged event. No inscriptions, labels, readable text, bare bodies, contemporary objects, crowd, or modern Athens. Portrait aspect ratio 940:1332 after crop; mid-distance and low human eye-height, richly textured sculptural detail and deep court perspective. Dominant cool white marble, muted terracotta, olive-grey stone, with clear neutral morning light and soft blue shadows. Reserve no text area inside art. Relative to 1.24.8, this shifts from two separate outdoor scenes and landscape stripe to one enclosed vertical architectural scene; from bronze/mountain palette and silvery weather to cool marble/terracotta; and from bronze object plus landscape to a group of human-form statuary. Camera distance, subject balance, palette and geometry all change for the passage's statue catalogue.

## Review and verification

Pre-art and final deterministic fit PASS: eight measured blocks, 12px padding, exact complete SQLite passage in two ordered fields at 37px on the final geometry, auxiliary type 23px or above. The central art was widened from 616 to 940px after the first thumbnail review because the narrower image left excess side space. A second fit and full render passed.

The first generated component had the poet's chest exposed and placed a second Acropolis and town in the distance. A targeted edit fully draped the poet and replaced the distant false landmark with Attic hills. Both components and the revision instruction are retained in the asset cache. Final image inspected at full size: five fully clothed statues, rich carving, clear Acropolis court orientation, no pseudo-inscriptions, inappropriate bodies, or irrelevant callouts. The exact lost figures and layout are described as interpretive. Art quality, semantic fit, historical care, content suitability, hierarchy, orientation, caption and text PASS beside 1.1.4 and 1.1.5.

Actual PNGs 1.24.3–1.24.8 and the final candidate compared at thumbnail scale in `tmp/2026-10-03-comparison.png`. The central dominant vertical art flanked by prose differs from 1.24.7's left art/right prose and 1.24.8's stacked Athens/Sipylus scenes. It appears once in the candidate-plus-five window. 1.24.3 has a smaller upper-left art block and lower prose band. No repeated tall left translation sidebar in the preceding five, and this page balances its left prose with a matching right field. Palette, camera scale, architecture/statuary balance and daylight differ from 1.24.8. Variety PASS.

Bounded local build PASS: 154 illustrated passages; reader page 1/25/1 displays passage 154 of 154 and references the new image; PDF has 155 pages, and page 155 was rasterised and visually inspected. Combined backup and source push pending.

Combined backup push/verify PASS with 426 component assets. Local asset cache, S3 asset manifest, S3 finished pages, and raksasa finished pages agree. Independent local/raksasa/downloaded-S3 final-page SHA-256: `c5d84c928ecda952218f3f6286efc23cb90930d8a375335bb746fd9bf18a9597`; selected component local/downloaded-S3 SHA-256: `17bd5981ec1ef5ed71584c4681c44b5ca73a983940fc4a936beb542eabfc2f09`. Source commit/push pending.
