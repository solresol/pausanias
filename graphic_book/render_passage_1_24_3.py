#!/usr/bin/env python3
"""Render the Acropolis catalogue in Pausanias 1.24.3."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_24_3"


def divide_passage(passage: str) -> list[str]:
    """Divide at explicit catalogue turns and retain every character."""
    ends = ["deity of earnestness.", "fingernails from silver.",
            "Conon himself."]
    chunks = []
    start = 0
    for phrase in ends:
        stop = passage.index(phrase, start) + len(phrase)
        chunks.append(passage[start:stop].strip())
        start = stop
    chunks.append(passage[start:].strip())
    if " ".join(chunks) != passage:
        raise RuntimeError("Passage split is not verbatim")
    return chunks


def render(output: Path, preflight: bool = False) -> None:
    """Measure and draw every text block; refuse overflow or a partial passage."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?", ("1.24.3",)
        ).fetchone()[0]
    parts = divide_passage(passage)
    page = Image.new("RGB", (1800, 1600), "#e9e9e3")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    if not preflight:
        art = Image.open(ASSETS / "earth_rain_acropolis.png").convert("RGB")
        page.paste(ImageOps.fit(art, (1056, 1066), method=Image.Resampling.LANCZOS,
                                centering=(0.5, 0.5)), (24, 154))
        draw = ImageDraw.Draw(page)

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            size, minimum, 12, name, spacing_ratio=0.17,
        )
        spacing = max(2, round(fit.font_size * 0.17))
        raw = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - raw[0], rect[1] + 12 - raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0]+12 or actual[1] < rect[1]+12 or
                actual[2] > rect[2]-12 or actual[3] > rect[3]-12):
            raise RuntimeError(f"{name}: rendered glyphs overflow target")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing,
                            fill="#243139")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size,
                                 actual, wrapped))

    block("id", (24, 18, 400, 76), "PASSAGE 1.24.3", 31, 27, heading=True)
    block("title", (408, 18, 1776, 76), "THE WORKS OF THE ACROPOLIS", 40, 30, heading=True)
    block("orientation", (24, 80, 1776, 132), "ATHENS · THE ACROPOLIS · PAUSANIAS' CATALOGUE", 27, 23, heading=True)
    block("heading-1", (1110, 166, 1776, 225), "1 · DIVINE WORKS", 29, 25, heading=True)
    block("translation-1", (1110, 230, 1776, 655), parts[0], 34, 29)
    block("heading-2", (1110, 666, 1776, 722), "2 · CLEOETAS", 29, 25, heading=True)
    block("translation-2", (1110, 728, 1776, 1210), parts[1], 34, 29)
    block("heading-3", (24, 1234, 865, 1288), "3 · EARTH AND THE TOMBS", 29, 25, heading=True)
    block("translation-3", (24, 1290, 865, 1530), parts[2], 32, 28)
    block("heading-4", (895, 1234, 1776, 1288), "4 · PROCNE AND THE SACRED SIGNS", 29, 25, heading=True)
    block("translation-4", (895, 1290, 1776, 1530), parts[3], 32, 28)
    block("caption", (24, 1538, 1776, 1584),
          "An interpretive Acropolis setting for the lost Earth dedication; the works' exact forms and placement are unknown.",
          24, 21)

    validate_fit_records(records)
    reconstructed = " ".join(" ".join(r.text.split()) for r in records
                             if r.name.startswith("translation-"))
    if reconstructed != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": "1.24.3", "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_3_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if not preflight:
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite existing output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/24/3.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
