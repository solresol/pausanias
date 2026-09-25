#!/usr/bin/env python3
"""Render Pausanias 1.24.2 with ordered upper prose and a lower votive scene."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block  # noqa: E402
from graphic_book.render_passage_1_10_1 import validate_fit_records  # noqa: E402

ASSETS = ROOT / "graphic_book/assets/generated/1_24_2"


def render(output: Path, preflight: bool = False) -> None:
    """Measure complete SQLite prose and local labels before saving a page."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?", ("1.24.2",)
        ).fetchone()[0]
    sentences = passage.split(". ")
    if len(sentences) != 5:
        raise RuntimeError(f"Unexpected passage sentence count: {len(sentences)}")
    parts = [sentences[0] + ".", sentences[1] + ".",
             sentences[2] + ". " + sentences[3] + ".", sentences[4]]

    page = Image.new("RGB", (1800, 1600), "#ecece7")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    art_rect = (24, 680, 1776, 1510)
    if not preflight:
        art = Image.open(ASSETS / "acropolis_bronze_bull.png").convert("RGB")
        fitted = ImageOps.fit(art, (1752, 830), method=Image.Resampling.LANCZOS,
                              centering=(0.5, 0.55))
        page.paste(fitted, art_rect[:2])

    def text(name: str, rect: tuple[int, int, int, int], content: str,
             size: int, minimum: int, *, title: bool = False,
             fill: str = "#263338") -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if title else BODY_FONT,
            size, minimum, 12, name, spacing_ratio=0.18,
        )
        spacing = max(2, round(fit.font_size * 0.18))
        raw = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - raw[0], rect[1] + 12 - raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12
                or actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill=fill)
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    text("passage-id", (24, 18, 400, 82), "PASSAGE 1.24.2", 31, 27, title=True)
    text("title", (407, 18, 1776, 82), "PHRIXUS, THE BRONZE BULL AND THE VOTIVE WORKS", 39, 30, title=True)
    text("orientation", (24, 83, 1776, 136), "ATHENS · THE ACROPOLIS · WORKS DESCRIBED BY PAUSANIAS", 27, 23, title=True)
    headings = ["1 · PHRIXUS", "2 · THE RITUAL", "3 · OTHER WORKS", "4 · THE BRONZE BULL"]
    xs = [24, 468, 912, 1356]
    for i, (x, heading, part) in enumerate(zip(xs, headings, parts, strict=True)):
        text(f"heading-{i+1}", (x, 166, x + 420, 226), heading, 28, 24, title=True)
        text(f"translation-{i+1}", (x, 232, x + 420, 704), part,
             30 if i == 1 else 32, 27)
    text("caption", (24, 1517, 1776, 1579),
         "An interpretive Acropolis setting for the bronze bull and Phrixus dedication; the lost works' precise forms are unknown.",
         26, 23)

    validate_fit_records(records)
    reconstructed = " ".join(" ".join(r.text.split()) for r in records
                             if r.name.startswith("translation-"))
    if reconstructed != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": "1.24.2", "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(record) for record in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_2_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if not preflight:
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite existing output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/24/2.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
