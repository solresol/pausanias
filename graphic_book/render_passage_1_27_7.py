#!/usr/bin/env python3
"""Typeset the complete Troezenian story into a reserved corner of raster art."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book_corpus import load_translation, snapshot_path
from graphic_book_fonts import BODY_FONT, TITLE_FONT
from graphic_book.render_passage_1_3_2 import FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

ASSETS = ROOT / "graphic_book/assets/generated/1_27_7"
ART_RECT = (36, 182, 1964, 1764)
READING_PANEL = (36, 1030, 1135, 1764)
BODY_RECT = (64, 1114, 1105, 1640)


def render(output: Path, preflight: bool = False) -> None:
    """Fail on any text overflow before reading art or saving the composite."""
    snapshot_path()
    passage = load_translation("1.27.7")
    page = Image.new("RGB", (2000, 1800), "#eee9df")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 16, name, .22,
        )
        spacing = max(2, round(fit.font_size * .22))
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 16 - bounds[0], rect[1] + 16 - bounds[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 16 or actual[1] < rect[1] + 16
                or actual[2] > rect[2] - 16 or actual[3] > rect[3] - 16):
            raise RuntimeError(name + ": glyph overflow inside padding")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure("passage-id", (36, 18, 476, 102), "PASSAGE 1.27.7", 38, 32, True)
    measure("title", (510, 18, 1964, 102), "THESEUS AND THE LION SKIN", 48, 36, True)
    measure("orientation", (36, 108, 1964, 170),
            "TROEZEN  |  THE HOUSEHOLD OF PITTHEUS  |  A STORY OF THESEUS'S CHILDHOOD", 29, 25, True)
    measure("reading-heading", (64, 1046, 1105, 1108), "THE STORY TOLD IN TROEZEN", 31, 27, True)
    measure("translation", BODY_RECT, passage, 44, 38)
    measure("interpretive-caption", (64, 1650, 1105, 1740),
            "Interpretive scene of the local story; the household, dress and figures are conjectural.", 26, 24)
    validate_fit_records(records)
    wrapped_passage = next(r.text for r in records if r.name == "translation")
    if " ".join(wrapped_passage.split()) != " ".join(passage.split()):
        raise RuntimeError("The complete exported English must remain in source order")
    report = {
        "passage_id": "1.27.7", "preflight": preflight,
        "canvas": [2000, 1800], "art_rectangle": ART_RECT,
        "reading_panel": READING_PANEL,
        "reading_order": "one continuous lower-left field, top to bottom",
        "translation_characters": len(passage), "translation_exact": passage,
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 38,
        "padding": 16, "text_blocks_checked": len(records),
        "fit_records": [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("fit_records", "translation_exact")}))
    print("Body font:", next(r.font_size for r in records if r.name == "translation"))
    if preflight:
        return
    if output.exists():
        raise RuntimeError("Refusing to overwrite " + str(output))
    with Image.open(ASSETS / "theseus_dinner.png") as source:
        art = ImageOps.fit(source.convert("RGB"), (1928, 1582),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(READING_PANEL, fill="#eee9df")
    draw.rectangle((35, 181, 1964, 1764), outline="#8a8173", width=2)
    draw.line((36, 173, 1964, 173), fill="#aba294", width=2)
    draw.line((1135, 1030, 1135, 1764), fill="#aba294", width=2)
    draw.line((36, 1030, 1135, 1030), fill="#aba294", width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill="#312f31")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/7.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
