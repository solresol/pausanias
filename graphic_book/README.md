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
pausanias_site/graphic-book/pausanias-graphic-book.pdf
pausanias_site/graphic-book/images/...
```

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

## Daily Image Generation Checklist

For each new passage image:

1. Select the earliest translated passage that does not yet have an image in the
   canonical image tree.
2. Use the previous graphic-book pages as visual references, especially the
   parchment-map layout, passage text panels, inset illustrations, route lines,
   and leader-line callouts.
3. Generate the art without relying on the image model for exact long text.
4. Add exact readable text locally after generation.
5. Verify the final image visually:
   - the passage ID is clear;
   - English passage text is present;
   - text stays inside every box;
   - labels do not stick out over their backing boxes;
   - the image shows where the passage is geographically;
   - callouts point to the important places, people, objects, or events;
   - the result is saved at `graphic_book/images/<book>/<chapter>/<section>.png`.
6. Run `uv run build_graphic_book.py` and inspect the generated HTML/PDF.
7. Run `./sync_graphic_book_images.sh push` so `raksasa` has the mirror copy.
