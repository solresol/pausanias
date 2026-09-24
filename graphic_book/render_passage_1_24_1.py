#!/usr/bin/env python3
"""Render Pausanias 1.24.1 as a sculptural gallery over a reading band."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_24_1"


def render(output: Path, preflight: bool = False) -> None:
    """Measure all local text, then render the accepted raster component."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?", ("1.24.1",)
        ).fetchone()[0]
    split = "Beyond these things I have described"
    first, rest = passage.split(split, 1)
    second = split + rest

    page = Image.new("RGB", (1800, 1600), "#eeeae1")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    art_rect = (24, 136, 1776, 1036)
    if not preflight:
        art = Image.open(ASSETS / "acropolis_myth_gallery.png").convert("RGB")
        fitted = ImageOps.fit(
            art, (art_rect[2] - art_rect[0], art_rect[3] - art_rect[1]),
            method=Image.Resampling.LANCZOS, centering=(0.5, 0.5),
        )
        page.paste(fitted, art_rect[:2])

    def text(name: str, rect: tuple[int, int, int, int], content: str,
             size: int, minimum: int, *, title: bool = False,
             fill: str = "#27363c") -> None:
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

    text("passage-id", (24, 18, 370, 83), "PASSAGE 1.24.1", 31, 28, title=True)
    text("title", (380, 18, 1776, 83), "ATHENA, MARSYAS AND THESEUS", 42, 32, title=True)
    text("orientation", (24, 80, 1776, 130), "ATHENS · THE ACROPOLIS · REPRESENTATIONS OF MYTH", 28, 24, title=True)
    text("caption", (24, 1044, 1776, 1110),
         "An interpretive view of the two depicted myths Pausanias describes; their lost forms are uncertain.",
         27, 24)
    text("heading-1", (24, 1116, 865, 1175), "1 · ATHENA AND MARSYAS", 29, 25, title=True)
    text("translation-1", (24, 1180, 865, 1544), first, 36, 29)
    text("heading-2", (925, 1116, 1776, 1175), "2 · THESEUS AND THE MINOTAUR", 29, 25, title=True)
    text("translation-2", (925, 1180, 1776, 1564), second, 36, 29)
    validate_fit_records(records)
    reconstructed = " ".join(
        " ".join(record.text.split()) for record in records
        if record.name.startswith("translation-")
    )
    assert reconstructed == " ".join(passage.split())
    report = {"passage_id": "1.24.1", "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(record) for record in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_1_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    print("Font sizes:", [(record.name, record.font_size) for record in records])
    if not preflight:
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite existing output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/24/1.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
