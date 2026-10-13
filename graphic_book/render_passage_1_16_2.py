#!/usr/bin/env python3
"""Render the reviewed 1.16.2 replacement as a central historical tableau."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import sqlite3
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

PASSAGE_ID = "1.16.2"
ART = ROOT / "graphic_book/assets/generated/1_16_2/replacement_lysimacheia_20261014.png"
ART_RECT = (28, 535, 1772, 1230)


def render(output: Path, preflight: bool = False) -> None:
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing SQLite translation")
    passage = row[0]
    sentences = re.split(r"(?<=\.) ", passage)
    if len(sentences) != 5 or " ".join(sentences) != passage:
        raise RuntimeError("Sentence split changed SQLite translation")
    chunks = [" ".join(sentences[:2]), sentences[2], " ".join(sentences[3:])]

    page = Image.new("RGB", (1800, 1600), "#e9e8e2")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=0.17)
        spacing = max(2, round(fit.font_size * 0.17))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - bbox[0], rect[1] + 12 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyph overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#243138")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 350, 68), "PASSAGE 1.16.2", 30, 25, heading=True)
    block("title", (370, 16, 1772, 68), "SELEUCUS AT LYSIMACHEIA", 43, 30, heading=True)
    block("orientation", (28, 82, 1772, 134),
          "ASIA  |  THRACIAN CHERSONESE  |  MACEDONIA  |  281 BCE",
          25, 20, heading=True)
    block("heading-1", (28, 145, 868, 184), "I. ASIA AND THE WESTWARD MARCH", 26, 21, heading=True)
    block("heading-2", (932, 145, 1772, 184), "II. CERAUNUS AT LYSIMACHEIA", 26, 21, heading=True)
    block("translation-1", (28, 185, 868, 525), chunks[0], 39, 29)
    block("translation-2", (932, 185, 1772, 525), chunks[1], 39, 29)
    block("caption", (28, 1234, 1772, 1280),
          "Near Lysimacheia: interpretive aftermath on Seleucus' road to Macedonia.", 23, 19)
    block("heading-3", (28, 1285, 1772, 1324), "III. MACEDONIA AFTER SELEUCUS", 26, 21, heading=True)
    block("translation-3", (28, 1325, 1772, 1550), chunks[2], 39, 29)
    validate_fit_records(records)
    rendered = " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-"))
    if rendered != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "translation_characters": len(passage),
              "text_blocks_checked": len(records), "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_16_2_replacement_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                            method=Image.Resampling.LANCZOS), ART_RECT[:2])
    draw.rectangle((ART_RECT[0]-1, ART_RECT[1]-1, ART_RECT[2], ART_RECT[3]),
                   outline="#667570", width=2)
    draw.line((900, 145, 900, 525), fill="#b8b6ac", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/output/replacements/1_16_2/2026-10-14/candidate.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
