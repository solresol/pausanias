#!/usr/bin/env python

"""Build the Pausanias graphic-book HTML and PDF from passage images."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image


PASSAGE_IMAGE_RE = re.compile(r"^(?P<section>\d+)\.(?:png|jpg|jpeg|webp)$", re.IGNORECASE)
PASSAGE_ID_RE = re.compile(r"^(?P<book>\d+)\.(?P<chapter>\d+)\.(?P<section>\d+)$")
DEFAULT_TITLE = "Time Traveller's Tourist Guides, Volume 23: 2nd Century Greece"
DEFAULT_BYLINE = "by Pausanias the Geographer"


@dataclass(frozen=True)
class GraphicPage:
    """One illustrated passage page."""

    passage_id: str
    source_path: Path
    site_image_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build HTML and PDF outputs for the Pausanias graphic book."
    )
    parser.add_argument("--image-dir", default="graphic_book/images")
    parser.add_argument("--output-dir", default="pausanias_site/graphic-book")
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--byline", default=DEFAULT_BYLINE)
    parser.add_argument("--pdf-name", default="pausanias-graphic-book.pdf")
    parser.add_argument("--title-page", default="graphic_book/assets/pausanias-title-page.png")
    return parser.parse_args()


def passage_sort_key(passage_id: str) -> tuple[int, int, int]:
    match = PASSAGE_ID_RE.match(passage_id)
    if not match:
        return (9999, 9999, 9999)
    return tuple(int(match.group(name)) for name in ("book", "chapter", "section"))


def discover_images(image_dir: Path) -> dict[str, Path]:
    """Return passage IDs mapped to canonical image paths.

    The canonical layout is:

        images/<book>/<chapter>/<section>.png
    """
    images: dict[str, Path] = {}
    if not image_dir.exists():
        return images

    for path in image_dir.rglob("*"):
        if not path.is_file():
            continue
        match = PASSAGE_IMAGE_RE.match(path.name)
        if not match:
            continue
        try:
            chapter = path.parent.name
            book = path.parent.parent.name
            int(book)
            int(chapter)
        except (ValueError, IndexError):
            continue
        passage_id = f"{book}.{chapter}.{match.group('section')}"
        images[passage_id] = path

    return dict(sorted(images.items(), key=lambda item: passage_sort_key(item[0])))


def build_pages(image_dir: Path, output_dir: Path) -> list[GraphicPage]:
    image_paths = discover_images(image_dir)
    pages: list[GraphicPage] = []

    site_images_dir = output_dir / "images"
    site_images_dir.mkdir(parents=True, exist_ok=True)

    for passage_id, source_path in image_paths.items():
        book, chapter, section = passage_id.split(".")
        site_rel = Path("images") / book / chapter / f"{section}{source_path.suffix.lower()}"
        dest = output_dir / site_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        dest.chmod(0o644)

        pages.append(
            GraphicPage(
                passage_id=passage_id,
                source_path=source_path,
                site_image_path=site_rel.as_posix(),
            )
        )

    return pages


def write_index(
    output_dir: Path, title: str, byline: str, pages: list[GraphicPage], pdf_name: str
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    build_version = datetime.now().strftime("%Y%m%d%H%M%S")
    page_cards = []

    for page in pages:
        book, chapter, section = page.passage_id.split(".")
        translation_href = f"../translation/{book}/{chapter}/{section}.html"
        page_cards.append(
            f"""
        <article class="graphic-page" id="p-{html.escape(page.passage_id)}">
            <div class="page-heading">
                <h2>Passage {html.escape(page.passage_id)}</h2>
                <a href="{translation_href}">Translation page</a>
            </div>
            <img src="{html.escape(page.site_image_path)}?v={build_version}" alt="Illustrated page for Pausanias {html.escape(page.passage_id)}">
        </article>
"""
        )

    if page_cards:
        body = "\n".join(page_cards)
    else:
        body = """
        <section class="empty-state">
            <h2>No illustrated passages yet</h2>
            <p>Add images under <code>graphic_book/images/&lt;book&gt;/&lt;chapter&gt;/&lt;section&gt;.png</code>.</p>
        </section>
"""

    pdf_link = (
        f'<a class="download" href="{html.escape(pdf_name)}?v={build_version}">Download PDF</a>'
        if pages
        else ""
    )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            color-scheme: light;
            --ink: #241b12;
            --muted: #6d5a42;
            --paper: #f6efe0;
            --paper-deep: #ead8b5;
            --rule: #8a7350;
            --sea: #2c5f78;
        }}
        body {{
            margin: 0;
            background: #1f1a14;
            color: var(--ink);
            font-family: Georgia, "Times New Roman", serif;
        }}
        header {{
            background: var(--paper);
            border-bottom: 4px solid var(--rule);
            padding: 28px 24px;
            text-align: center;
        }}
        header h1 {{
            margin: 0 0 6px;
            letter-spacing: 0;
            color: var(--ink);
        }}
        header p {{
            margin: 0;
            color: var(--muted);
            font-size: 1.15rem;
        }}
        nav {{
            background: #5c5142;
            padding: 10px;
            text-align: center;
        }}
        nav a {{
            color: #fff;
            font-weight: bold;
            margin: 0 12px;
            text-decoration: none;
        }}
        main {{
            max-width: 1180px;
            margin: 0 auto;
            padding: 26px 18px 60px;
        }}
        .book-actions {{
            align-items: center;
            background: var(--paper);
            border: 1px solid var(--rule);
            display: flex;
            justify-content: space-between;
            margin-bottom: 24px;
            padding: 14px 16px;
        }}
        .download {{
            background: var(--sea);
            color: white;
            font-weight: bold;
            padding: 8px 12px;
            text-decoration: none;
        }}
        .graphic-page {{
            background: var(--paper);
            border: 1px solid var(--rule);
            margin: 0 0 34px;
            padding: 16px;
        }}
        .page-heading {{
            align-items: baseline;
            display: flex;
            gap: 16px;
            justify-content: space-between;
        }}
        .page-heading h2 {{
            margin: 0 0 12px;
        }}
        .page-heading a {{
            color: var(--sea);
            font-weight: bold;
        }}
        .graphic-page img {{
            background: #ddd0b3;
            display: block;
            height: auto;
            width: 100%;
        }}
        footer {{
            color: #eee2c8;
            margin-top: 30px;
            text-align: center;
        }}
        @media print {{
            body {{ background: white; }}
            header, nav, .book-actions, footer {{ display: none; }}
            main {{ max-width: none; padding: 0; }}
            .graphic-page {{
                border: 0;
                break-after: page;
                margin: 0;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(byline)}</p>
    </header>
    <nav>
        <a href="../index.html">Home</a>
        <a href="../translation/index.html">Translation</a>
        <a href="index.html">Graphic Book</a>
    </nav>
    <main>
        <section class="book-actions">
            <span>{len(pages)} illustrated passage{"s" if len(pages) != 1 else ""}</span>
            {pdf_link}
        </section>
{body}
        <footer>Generated on {timestamp}</footer>
    </main>
</body>
</html>
"""
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def write_pdf(output_dir: Path, pages: list[GraphicPage], pdf_name: str, title_page: Path) -> None:
    if not pages and not title_page.exists():
        return

    pdf_images: list[Image.Image] = []
    try:
        if title_page.exists():
            with Image.open(title_page) as img:
                pdf_images.append(img.convert("RGB").copy())

        for page in pages:
            image_path = output_dir / page.site_image_path
            with Image.open(image_path) as img:
                rgb = img.convert("RGB")
                pdf_images.append(rgb.copy())

        if pdf_images:
            first, rest = pdf_images[0], pdf_images[1:]
            first.save(
                output_dir / pdf_name,
                "PDF",
                resolution=150.0,
                save_all=True,
                append_images=rest,
            )
    finally:
        for img in pdf_images:
            img.close()


def main() -> None:
    args = parse_args()
    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    pages = build_pages(image_dir, output_dir)
    write_index(output_dir, args.title, args.byline, pages, args.pdf_name)
    write_pdf(output_dir, pages, args.pdf_name, Path(args.title_page))
    print(f"Graphic book built in {output_dir} with {len(pages)} illustrated passages.")


if __name__ == "__main__":
    main()
