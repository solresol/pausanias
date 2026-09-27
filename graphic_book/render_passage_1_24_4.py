#!/usr/bin/env python3
"""Render the Zeus Polieus sacrifice at Pausanias 1.24.4."""
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

PASSAGE_ID = "1.24.4"
ASSETS = ROOT / "graphic_book/assets/generated/1_24_4"
ART = ASSETS / "zeus_polieus_altar.png"


def divide_passage(passage: str) -> list[str]:
    """Keep the account in four exact, ordered reading blocks."""
    ends = ["traditionally offered for them.", "without setting any guard over them.",
            "flees swiftly away."]
    parts: list[str] = []
    start = 0
    for ending in ends:
        stop = passage.index(ending, start) + len(ending)
        parts.append(passage[start:stop].strip())
        start = stop
    parts.append(passage[start:].strip())
    if " ".join(parts) != passage:
        raise RuntimeError("Passage division is not verbatim")
    return parts


def render(output: Path, preflight: bool = False) -> None:
    """Fit each text item before drawing; refuse clipped or incomplete text."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?",
                           (PASSAGE_ID,)).fetchone()
    if not row:
        raise RuntimeError(f"Missing {PASSAGE_ID} translation")
    passage = row[0]
    parts = divide_passage(passage)
    page = Image.new("RGB", (1800, 1600), "#eeeae1")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    if not preflight:
        if not ART.exists():
            raise RuntimeError(f"Missing art: {ART}")
        art = Image.open(ART).convert("RGB")
        page.paste(ImageOps.fit(art, (1752, 655), method=Image.Resampling.LANCZOS,
                                centering=(0.5, 0.49)), (24, 456))
        draw = ImageDraw.Draw(page)
        draw.rectangle((23, 455, 1777, 1112), outline="#6d695e", width=2)

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
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyphs overflow target")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#293036")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (24, 16, 390, 76), "PASSAGE 1.24.4", 31, 27, heading=True)
    block("title", (395, 16, 1776, 76), "ZEUS POLIEUS AND THE OX SACRIFICE", 39, 30, heading=True)
    block("orientation", (24, 78, 1776, 134), "ATHENS · THE ACROPOLIS · THE BOUPHONIA", 27, 23, heading=True)
    block("heading-1", (24, 145, 872, 190), "1 · THE STATUES AND THE CUSTOM", 27, 23, heading=True)
    block("translation-1", (24, 194, 872, 435), parts[0], 32, 29)
    block("heading-2", (910, 145, 1776, 190), "2 · GRAIN UPON THE ALTAR", 27, 23, heading=True)
    block("translation-2", (910, 194, 1776, 435), parts[1], 32, 29)
    block("caption", (24, 1117, 1776, 1171),
          "An interpretive view of the ox approaching the grain altar of Zeus Polieus; the Parthenon stands beyond.",
          25, 22)
    block("heading-3", (24, 1177, 872, 1224), "3 · THE GUARDED OX", 27, 23, heading=True)
    block("translation-3", (24, 1228, 872, 1538), parts[2], 32, 28)
    block("heading-4", (910, 1177, 1776, 1224), "4 · THE AXE ON TRIAL", 27, 23, heading=True)
    block("translation-4", (910, 1228, 1776, 1538), parts[3], 32, 28)
    block("footer", (24, 1542, 1776, 1592),
          "The scene depicts the moment before the sacrifice; the later trial of the axe is described in the passage.",
          23, 20)

    validate_fit_records(records)
    reconstructed = " ".join(" ".join(r.text.split()) for r in records
                             if r.name.startswith("translation-"))
    if reconstructed != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_4_layout_report.json").write_text(json.dumps(report, indent=2))
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
                        default=ROOT / "graphic_book/images/1/24/4.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
