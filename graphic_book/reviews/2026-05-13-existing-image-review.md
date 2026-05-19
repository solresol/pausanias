# Existing Graphic-Book Image Review: 2026-05-13

Scope: all current passage images under `graphic_book/images/`, reviewed against
the `graphic_book/README.md` visual quality baseline and post-render review
gate.

Approved anchors used for comparison:

- `graphic_book/images/1/1/4.png`
- `graphic_book/images/1/1/5.png`

## Resolved During Follow-Up

### `1.4.1`

Original flag: **primitive-art failure / art quality failure**.

Follow-up action: replaced the two primitive procedural scenic insets with
sourced raster art:

- `graphic_book/assets/generated/1_4_1/seashore_source.jpg`
- `graphic_book/assets/generated/1_4_1/eridanos_heliades_generated.png`

The revised page keeps the secondary `INVASION ROUTE` diagram but no longer uses
procedural drawing for scenic inset art. The `INVASION ROUTE` callout was also
reworked onto an antique map crop so it no longer reads as a flat node-and-line
placeholder.

Additional follow-up: the intermediate Phaethon engraving introduced visible
nudity and was rejected under the new content-suitability rule. A later
poplars-only source avoided nudity but failed semantic fit because it did not
actually illustrate the passage. It was replaced with purpose-generated non-nude
Eridanos/Heliades art showing mourners, poplars, amber tears, and distant
Phaethon.

## Content Suitability Review

Flag added after follow-up: **content suitability failure**.

The intermediate `1.4.1` revision used a Phaethon/Heliades engraving that showed
visible nudity in the bottom-right scenic inset. That source has been removed
from the renderer and replaced with `eridanos_poplars_source.jpg`.

Current status: no visible nudity found in the regenerated contact sheet for the
current image corpus. Higher-risk myth/statue pages checked at full size:

- `1.2.1`
- `1.2.4`
- `1.2.6`
- `1.3.1`
- `1.4.1`

## Semantic Fit Review

Flag added after follow-up: **semantic-fit failure**.

The intermediate `1.4.1` poplars/river replacement was attractive and non-nude,
but it had no specific relationship to the caption or passage except the broad
presence of trees. It has been replaced with generated Eridanos/Heliades imagery
that directly depicts the mythic riverbank, mourning daughters of Helios,
poplars, amber tears, and Phaethon's distant fall.

## Hard Art-Quality Failures

None remaining from this pass.

## Original Hard Art-Quality Finding

### `1.4.1`

Original flag: **primitive-art failure / art quality failure**.

The bottom-left tidal outer-sea panel and bottom-right Eridanos/Phaethon panel
were scenic insets, but they looked procedurally sketched rather than
illustrated. They used flat color bands, repeated wave strokes, geometric trees,
circular sun forms, stick-like silhouettes, and symbolic droplets. These were
not acceptable as finished scenic art for a professional graphic book.

The route-key panel is schematic too, but that panel is a secondary diagram and
can be acceptable as a locator. The failure is specifically that the two scenic
bottom panels were diagrammatic placeholder art.

Resolution: fixed during follow-up.

## Text or Metadata Failures

### `1.1.1`

Flag: **text failure: passage ID missing**.

The page has strong atlas art and readable passage text, but it does not show an
explicit `PASSAGE 1.1.1` identifier. Under the current rules the passage ID must
be visible on the finished PNG.

Required action: add a local passage-ID label without degrading the existing
composition.

### `1.1.2`

Flag: **text failure: passage ID missing**.

The page has strong scenic art and a clear topic title, but it does not show an
explicit `PASSAGE 1.1.2` identifier. Under the current rules the passage ID must
be visible on the finished PNG.

Required action: add a local passage-ID label without degrading the existing
composition.

## Layout and Legibility Cleanups

### `1.2.4`

Flag: **label/callout crowding**.

The main panel and scenic insets are acceptable, and the bottom-left Kerameikos
locator is allowed as a secondary diagram. The crowded main-panel label/callout
stack should be checked, especially the `PANATHENAIC WAY` label, which reads as
partly occluded or clipped in the final composition.

Required action: review label placement and callout hierarchy; revise if the
label is actually clipped in the source image.

### `1.2.5`

Flag: **secondary locator crowding**.

The main panel and scenic insets are acceptable. The bottom-left `INNER
KERAMEIKOS` locator is allowed as a diagram, but its internal labels and caption
are cramped, especially around `SACRED GATE`.

Required action: tighten or simplify the locator layout if this page is revised.

## Accepted Schematic Panels

These panels are schematic, but they are not flagged as art failures because
they are subordinate locator or conceptual diagrams rather than scenic panels:

- `1.2.4` bottom-left `KERAMEIKOS ENTRY` locator.
- `1.2.5` bottom-left `INNER KERAMEIKOS` locator, aside from the crowding noted
  above.
- `1.2.6` bottom-left `ROYAL SUCCESSION` conceptual diagram.
- `1.3.2` bottom-left `NORTH-WEST AGORA` locator.
- `1.3.4` bottom-left `WAR CONTEXT` diagram.
- `1.3.5` bottom-left `CIVIC PRECINCT` locator.
- `1.4.1` `INVASION ROUTE` diagram, provided the scenic insets are replaced.

## No Current Flag

No current review flag from this pass:

- `1.1.3`
- `1.1.4`
- `1.1.5`
- `1.2.1`
- `1.2.2`
- `1.2.3`
- `1.2.6`
- `1.3.1`
- `1.3.2`
- `1.3.3`
- `1.3.4`
- `1.3.5`

This does not mean the pages are final forever; it means they did not trip the
new post-render gate during this pass.
