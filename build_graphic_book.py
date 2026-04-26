#!/usr/bin/env python

"""Build the Pausanias graphic-book HTML and PDF from passage images."""

from __future__ import annotations

import argparse
import html
import posixpath
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

    @property
    def passage_href(self) -> str:
        book, chapter, section = self.passage_id.split(".")
        return f"{book}/{chapter}/{section}.html"


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


def relative_href(from_page: str, target: str) -> str:
    """Return a POSIX relative URL from one generated graphic-book page."""
    from_dir = posixpath.dirname(from_page) or "."
    return posixpath.relpath(target, start=from_dir)


def render_graphic_nav(prefix: str, active: str = "graphic") -> str:
    links = [
        ("../index.html", "Home", "home"),
        ("../translation/index.html", "Translation", "translation"),
        ("index.html", "Graphic Book", "graphic"),
    ]
    parts = []
    for href, label, key in links:
        cls = ' class="active"' if key == active else ""
        parts.append(f'<a href="{html.escape(relative_href(prefix, href))}"{cls}>{label}</a>')
    return "<nav>\n        " + "\n        ".join(parts) + "\n    </nav>"


def graphic_book_css() -> str:
    return """
        :root {
            color-scheme: light;
            --ink: #241b12;
            --muted: #6d5a42;
            --paper: #f6efe0;
            --paper-deep: #ead8b5;
            --paper-soft: #fffaf0;
            --rule: #8a7350;
            --sea: #2c5f78;
            --shadow: rgba(19, 14, 9, 0.28);
        }
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            background: #1f1a14;
            color: var(--ink);
            font-family: Georgia, "Times New Roman", serif;
        }
        header {
            background: var(--paper);
            border-bottom: 4px solid var(--rule);
            padding: 28px 24px;
            text-align: center;
        }
        header h1 {
            margin: 0 0 6px;
            letter-spacing: 0;
            color: var(--ink);
        }
        header p {
            margin: 0;
            color: var(--muted);
            font-size: 1.15rem;
        }
        nav {
            background: #5c5142;
            padding: 10px;
            text-align: center;
        }
        nav a {
            color: #fff;
            display: inline-block;
            font-weight: bold;
            margin: 4px 12px;
            text-decoration: none;
        }
        nav a.active,
        nav a:hover {
            text-decoration: underline;
        }
        main {
            max-width: 1180px;
            margin: 0 auto;
            padding: 26px 18px 60px;
        }
        .book-actions,
        .reader-toolbar,
        .reader-meta,
        .toc-panel,
        .empty-state {
            background: var(--paper);
            border: 1px solid var(--rule);
        }
        .book-actions,
        .reader-toolbar,
        .reader-meta {
            align-items: center;
            display: flex;
            gap: 14px;
            justify-content: space-between;
            margin-bottom: 18px;
            padding: 14px 16px;
        }
        .reader-toolbar {
            position: sticky;
            top: 0;
            z-index: 2;
        }
        .reader-position {
            color: var(--muted);
            font-weight: bold;
            text-align: center;
        }
        .button,
        .download,
        .primary-action {
            background: var(--sea);
            color: white;
            display: inline-block;
            font-weight: bold;
            padding: 8px 12px;
            text-decoration: none;
        }
        .button.secondary {
            background: #5c5142;
        }
        .button.disabled {
            background: #b9ab92;
            color: #4f463a;
        }
        .reader-image-frame {
            background: var(--paper-deep);
            border: 1px solid var(--rule);
            box-shadow: 0 18px 50px var(--shadow);
            margin: 0 auto;
            padding: 16px;
        }
        .reader-image-frame img {
            background: #ddd0b3;
            display: block;
            height: auto;
            width: 100%;
        }
        .reader-meta {
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .reader-meta h2 {
            margin: 0;
        }
        .reader-links {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .toc-panel,
        .empty-state {
            padding: 18px;
        }
        .toc-panel h2 {
            margin-top: 0;
        }
        .toc-list {
            column-width: 220px;
            margin-bottom: 0;
            padding-left: 1.5rem;
        }
        .toc-list li {
            break-inside: avoid;
            margin-bottom: 8px;
        }
        .toc-list a {
            color: var(--sea);
            font-weight: bold;
        }
        .translation-inline {
            font-size: 0.85em;
            margin-left: 8px;
            white-space: nowrap;
        }
        footer {
            color: #eee2c8;
            margin-top: 30px;
            text-align: center;
        }
        @media (max-width: 700px) {
            main {
                padding: 18px 10px 42px;
            }
            .book-actions,
            .reader-toolbar,
            .reader-meta {
                align-items: stretch;
                flex-direction: column;
            }
            .reader-position {
                order: -1;
            }
            .button,
            .download,
            .primary-action {
                text-align: center;
                width: 100%;
            }
            .reader-image-frame {
                padding: 8px;
            }
        }
        @media print {
            body {
                background: white;
            }
            header,
            nav,
            .book-actions,
            .reader-toolbar,
            .reader-meta,
            footer {
                display: none;
            }
            main {
                max-width: none;
                padding: 0;
            }
            .reader-image-frame {
                border: 0;
                box-shadow: none;
                margin: 0;
                padding: 0;
            }
        }
    """


def reader_button(href: str | None, label: str, css_class: str = "button") -> str:
    if href is None:
        return f'<span class="{css_class} disabled">{html.escape(label)}</span>'
    return f'<a class="{css_class}" href="{html.escape(href)}">{html.escape(label)}</a>'


def write_index(
    output_dir: Path, title: str, byline: str, pages: list[GraphicPage], pdf_name: str
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    build_version = datetime.now().strftime("%Y%m%d%H%M%S")
    css = graphic_book_css()

    if pages:
        toc_items = []
        for page in pages:
            book, chapter, section = page.passage_id.split(".")
            translation_href = f"../translation/{book}/{chapter}/{section}.html"
            toc_items.append(
                f"""            <li>
                <a href="{html.escape(page.passage_href)}">Passage {html.escape(page.passage_id)}</a>
                <a class="translation-inline" href="{html.escape(translation_href)}">Translation</a>
            </li>
"""
            )
        body = f"""
        <section class="book-actions">
            <span>{len(pages)} illustrated passage{"s" if len(pages) != 1 else ""}</span>
            <a class="download" href="{html.escape(pdf_name)}?v={build_version}">Download PDF</a>
        </section>
        <section class="toc-panel">
            <h2>Graphic Book Reader</h2>
            <p><a class="primary-action" href="{html.escape(pages[0].passage_href)}">Start reading at Passage {html.escape(pages[0].passage_id)}</a></p>
            <ol class="toc-list">
{''.join(toc_items)}            </ol>
        </section>
"""
        hash_routes = "\n".join(
            f'            "{html.escape(page.passage_id)}": "{html.escape(page.passage_href)}",'
            for page in pages
        )
        hash_redirect_script = f"""
    <script>
        const passageRoutes = {{
{hash_routes}
        }};
        const hashPassage = window.location.hash.replace(/^#p-?/, "").replace(/^#/, "");
        if (passageRoutes[hashPassage]) {{
            window.location.replace(passageRoutes[hashPassage]);
        }}
    </script>
"""
    else:
        body = """
        <section class="empty-state">
            <h2>No illustrated passages yet</h2>
            <p>Add images under <code>graphic_book/images/&lt;book&gt;/&lt;chapter&gt;/&lt;section&gt;.png</code>.</p>
        </section>
"""
        hash_redirect_script = ""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
{css}
    </style>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(byline)}</p>
    </header>
    {render_graphic_nav("index.html")}
    <main>
{body}
        <footer>Generated on {timestamp}</footer>
    </main>
{hash_redirect_script}
</body>
</html>
"""
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    write_reader_pages(output_dir, title, byline, pages, pdf_name, timestamp, build_version, css)


def write_reader_pages(
    output_dir: Path,
    title: str,
    byline: str,
    pages: list[GraphicPage],
    pdf_name: str,
    timestamp: str,
    build_version: str,
    css: str,
) -> None:
    for index, page in enumerate(pages):
        book, chapter, section = page.passage_id.split(".")
        page_href = page.passage_href
        image_src = f"{relative_href(page_href, page.site_image_path)}?v={build_version}"
        translation_href = relative_href(
            page_href, f"../translation/{book}/{chapter}/{section}.html"
        )
        toc_href = relative_href(page_href, "index.html")
        pdf_href = f"{relative_href(page_href, pdf_name)}?v={build_version}"

        prev_href = None
        if index > 0:
            prev_href = relative_href(page_href, pages[index - 1].passage_href)
        next_href = None
        if index < len(pages) - 1:
            next_href = relative_href(page_href, pages[index + 1].passage_href)

        prev_button = reader_button(prev_href, "Previous", "button secondary")
        next_button = reader_button(next_href, "Next", "button secondary")

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Passage {html.escape(page.passage_id)}</title>
    <style>
{css}
    </style>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(byline)}</p>
    </header>
    {render_graphic_nav(page_href)}
    <main id="p-{html.escape(page.passage_id)}">
        <div class="reader-toolbar" aria-label="Reader navigation">
            {prev_button}
            <div class="reader-position">Passage {html.escape(page.passage_id)} ({index + 1} of {len(pages)})</div>
            {next_button}
        </div>

        <figure class="reader-image-frame">
            <img src="{html.escape(image_src)}" alt="Illustrated page for Pausanias {html.escape(page.passage_id)}">
        </figure>

        <section class="reader-meta">
            <h2>Passage {html.escape(page.passage_id)}</h2>
            <div class="reader-links">
                <a class="button" href="{html.escape(translation_href)}">Formal Translation</a>
                <a class="button secondary" href="{html.escape(toc_href)}">Contents</a>
                <a class="download" href="{html.escape(pdf_href)}">Download PDF</a>
            </div>
        </section>

        <footer>Generated on {timestamp}</footer>
    </main>
</body>
</html>
"""
        path = output_dir / page_href
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8")


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
