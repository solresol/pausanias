# Pausanias Graphic Book Images

This directory defines the local working layout for illustrated Pausanias
passages. The bulk image corpus is intentionally not tracked in Git: a complete
run will eventually be many gigabytes.

## Canonical Image Layout

Store images by passage ID:

```text
graphic_book/images/<book>/<chapter>/<section>.png
```

Examples:

```text
graphic_book/images/1/1/1.png
graphic_book/images/1/1/2.png
```

The PDF title-page graphic is stored separately:

```text
graphic_book/assets/pausanias-title-page.png
```

`build_graphic_book.py` scans this tree and writes:

```text
pausanias_site/graphic-book/index.html
pausanias_site/graphic-book/<book>/<chapter>/<section>.html
pausanias_site/graphic-book/pausanias-graphic-book.pdf
pausanias_site/graphic-book/images/...
```

Each illustrated passage has a stable reader URL, for example:

```text
pausanias_site/graphic-book/1/1/3.html
```

The formal translation generator links to those reader pages when it sees a
matching image in the configured graphic-book image directory.

The existing daily script then publishes `pausanias_site/` to
`pausanias.symmachus.org`.

## Storage Contract

The repo-local `graphic_book/images/` tree is the local working copy. The
standing remote mirror is:

```text
pausanias@raksasa:~/pausanias-graphic-book/images/
```

Use:

```bash
./sync_graphic_book_images.sh push
./sync_graphic_book_images.sh pull
```

If an S3 primary is configured later, set:

```bash
PAUSANIAS_GRAPHIC_BOOK_S3_URI=s3://bucket-or-prefix
```

and `sync_graphic_book_images.sh push` will also sync the image tree to S3.

The renderer source files and the smaller generated component artwork under
`graphic_book/assets/generated/` are tracked in Git because they are needed to
rebuild a passage page. The completed passage pages under `graphic_book/images/`
remain ignored and externally mirrored because the final image corpus is the
bulk output.

## Visual Quality Baseline

The approved style anchors are:

```text
graphic_book/images/1/1/4.png
graphic_book/images/1/1/5.png
```

These pages set the current minimum standard for visual ambition: parchment
atlas grammar, rich scenic or map art, legible callouts, local text rendering,
and a coffee-table-book impression at first glance. Do not let weaker, crude,
schematic, or placeholder pages redefine the standard.

Every scenic panel must look like finished art. This applies to main panels and
insets. A panel is not acceptable if it reads as a classroom diagram, flat vector
terrain, icon sheet, placeholder storyboard, or simple Pillow/SVG construction.
Locator maps are allowed only as clearly subordinate orientation insets, never
as the main visual identity or as a substitute for scenic art. Even a
subordinate locator must meet the house style: use a sourced, generated, or
richly textured raster/relief base whenever possible, then add exact labels and
routes locally. Do not use flat solid-color polygons, blunt block mountains,
rectangular seas, sticker-like labels, or simple classroom-diagram geometry for
finished locator insets.

Procedural drawing is acceptable for:

- frames, shadows, parchment backgrounds, route strokes, leader lines, labels,
  callout boxes, and typography;
- restrained overlays on locator maps, such as route strokes, pins, masks,
  scale marks, and locally rendered labels;
- minor paint-over repairs, masks, tinting, and texture unification.

Procedural drawing is not acceptable for:

- scenic insets;
- people, ships, animals, gods, buildings, landscapes, battles, temples, tombs,
  coastlines, rivers, or myth scenes that are meant to be looked at as art;
- anything that would be described as stick figures, circles-and-lines, flat
  color bands, repeated wave strokes, or generic iconography.

For main art and scenic insets, use high-quality generated or sourced raster art,
then add exact labels, captions, leader lines, frames, and long text locally.
The image model or source artwork must not be trusted for exact long text.

## Semantic Fit

Every scenic image must be an illustration of the passage, not merely attractive
art that can be captioned into relevance. If the caption and labels were hidden,
the panel should still visibly support the passage's place, event, object,
person, or mythic reference.

Sourced artwork is allowed only when it directly depicts the subject or provides
a historically/geographically specific base that the local labels clarify. Do
not use a loosely related painting as a substitute for illustration. For bespoke
mythic scenes, local topographic reconstructions, or passage-specific moments,
prefer purpose-generated raster art with explicit subject, modesty, and
historical-style constraints.

Reject a scenic panel if:

- the caption is doing all the semantic work;
- the image could be swapped into a different passage without anyone noticing;
- the image is relevant only by broad theme, mood, palette, or public-domain
  availability;
- a reader would not understand why that picture belongs on this page after
  looking at the page for a few seconds.

## Content Suitability

The graphic book should be suitable for a general professional audience. Do not
use source or generated artwork with visible nudity, eroticized poses, or
gratuitous bodily exposure. This includes exposed genitals, buttocks, or
breasts, even when the source is classical, mythological, or museum art.

When using historical or mythological source art, inspect the source and the
final crop before rendering. If the source contains nudity, prefer a different
source. Use a crop only when the final rendered panel clearly contains no
visible nudity and the crop choice is documented in the page plan.

## Post-Render Review Gate

Before accepting a page, inspect the final PNG at full size and reject it if any
of these are true:

- **Art quality failure:** the main panel or any scenic inset looks crude,
  sparse, flat, diagrammatic, cartoony, icon-like, or procedurally sketched.
- **Reference mismatch:** the page would look obviously weaker beside
  `1.1.4` and `1.1.5` in a printed spread.
- **Primitive-art failure:** a scenic panel appears to be built from simple
  geometric primitives, repeated strokes, stock shapes, or symbolic silhouettes.
- **Naive-locator failure:** a locator inset reads as a flat classroom diagram:
  solid-color land/sea blocks, blunt mountain shapes, rectangular water,
  oversized sticker labels, or route strokes that do not sit on credible
  topography.
- **Orientation failure:** the reader cannot tell where the passage is located
  or why the chosen visual subject matters historically or geographically.
- **Semantic-fit failure:** a scenic panel does not directly depict or clarify
  the passage's place, event, object, person, or mythic reference.
- **Callout failure:** leaders point to generic empty areas or to features that
  do not correspond to the label or caption.
- **Text failure:** the passage ID, English passage text, labels, captions, or
  notes are missing, cramped, touching borders, clipped, or baked into the art
  with unreliable spelling.
- **Content suitability failure:** the page or any inset contains visible
  nudity, eroticized figures, or gratuitous bodily exposure.
- **Hierarchy failure:** the page is dominated by a secondary locator diagram,
  decorative map, or filler panel rather than a strong visual interpretation of
  the passage.

The deterministic text-fit check is necessary but not sufficient. Passing layout
metrics does not make a page acceptable if the art layer fails this review gate.

## Daily Image Generation Checklist

For each new passage image:

1. Select the earliest translated passage that does not yet have an image in the
   canonical image tree.
2. Make a brief page plan: passage ID, key places/events/objects, main visual,
   scenic insets, orientation strategy, and approved reference pages.
3. Use the approved anchors (`1.1.4` and `1.1.5`) for visual quality, and use
   other existing pages only as continuity references for layout conventions.
4. Generate or source high-quality raster art for the main panel and every
   scenic inset. Keep exact text, labels, callouts, and borders out of the
   raster prompt/source whenever possible so they can be added locally.
5. Confirm that every scenic panel passes the semantic-fit rule without relying
   on its caption to explain why it belongs on the page.
6. Confirm that every source image and final crop satisfies the content
   suitability rule, especially for mythological scenes.
7. Add exact readable passage text, labels, captions, leader lines, frames, and
   callouts locally after art generation.
8. Use deterministic measured layout for every text panel, caption, and label.
   Fail the run rather than save if any text block overflows at the minimum
   acceptable size.
9. Apply the full post-render review gate above. Reject and revise if any scenic
   panel is primitive, crude, or placeholder-like, even if text fitting passed.
10. Save the accepted result at
   `graphic_book/images/<book>/<chapter>/<section>.png`.
11. Run `uv run build_graphic_book.py --image-dir graphic_book/images --output-dir pausanias_site/graphic-book`
   and inspect the generated HTML/PDF.
12. Run `./sync_graphic_book_images.sh push` so `raksasa` has the mirror copy.
