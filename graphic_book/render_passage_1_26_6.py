#!/usr/bin/env python3
"""Render Pausanias 1.26.6 with one sanctuary scene above three prose fields."""
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

from graphic_book_corpus import snapshot_path
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

PASSAGE_ID = "1.26.6"
ART = ROOT / "graphic_book/assets/generated/1_26_6/athena_lamp_sanctuary.png"
ART_RECT = (28, 145, 1772, 1045)


def render(output: Path, preflight: bool = False) -> None:
    with sqlite3.connect(snapshot_path()) as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing SQLite translation")
    passage = row[0]
    markers = ("But the holiest thing", "The tradition about it")
    positions = [passage.find(marker) for marker in markers]
    if positions[0] <= 0 or positions[1] <= positions[0]:
        raise RuntimeError("Expected translation split markers are absent or out of order")
    chunks = [passage[:positions[0]].rstrip(),
              passage[positions[0]:positions[1]].rstrip(),
              passage[positions[1]:]]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation chunks do not preserve SQLite text")

    page = Image.new("RGB", (1800, 1600), "#e9e9e4")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=0.16)
        spacing = max(2, round(fit.font_size * 0.16))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - bbox[0], rect[1] + 12 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyph overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#263437")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 367, 67), "PASSAGE 1.26.6", 30, 25, heading=True)
    block("title", (390, 16, 1772, 67), "ATHENA'S ANCIENT IMAGE AND THE GOLD LAMP", 43, 30, heading=True)
    block("orientation", (28, 79, 1772, 129),
          "ATHENS  |  THE ACROPOLIS  |  THE CULT IMAGE REVERED BY THE DEMES", 25, 20, heading=True)
    rects = [(28, 1120, 576, 1570), (626, 1120, 1174, 1570),
             (1224, 1120, 1772, 1570)]
    for index, (rect, chunk) in enumerate(zip(rects, chunks), 1):
        block(f"translation-{index}", rect, chunk, 39, 30)
    block("caption", (28, 1055, 1772, 1102),
          "The Acropolis cult image and Callimachus's lamp — an interpretive view of Pausanias's account.",
          23, 19)
    validate_fit_records(records)
    rendered = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "translation_characters": len(passage),
              "text_blocks_checked": len(records), "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_26_6_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                            method=Image.Resampling.LANCZOS), ART_RECT[:2])
    draw.rectangle((ART_RECT[0]-1, ART_RECT[1]-1, ART_RECT[2], ART_RECT[3]),
                   outline="#718487", width=2)
    for x in (601, 1199):
        draw.line((x, 1120, x, 1570), fill="#b9c0be", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/26/6.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
