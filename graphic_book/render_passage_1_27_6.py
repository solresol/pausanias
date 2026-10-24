#!/usr/bin/env python3
"""Render the fire-darkened sculptures with the exact exported English text."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_27_6"
ART_RECT = (36, 184, 1236, 1664)
TEXT_RECT = (1284, 274, 1964, 1664)


def render(output: Path, preflight: bool = False) -> None:
    """Measure every block before opening art or saving the final page."""
    snapshot_path()
    passage = load_translation("1.27.6")
    page = Image.new("RGB", (2000, 1800), "#eee9dd")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 18, name, .22,
        )
        spacing = max(2, round(fit.font_size * .22))
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 18 - bounds[0], rect[1] + 18 - bounds[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 18 or actual[1] < rect[1] + 18
                or actual[2] > rect[2] - 18 or actual[3] > rect[3] - 18):
            raise RuntimeError(name + ": glyph overflow inside padding")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#283a39")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("passage-id", (36, 18, 476, 102), "PASSAGE 1.27.6", 38, 32, True)
    block("title", (510, 18, 1964, 102), "SCULPTURES THAT SURVIVED THE FIRE", 45, 34, True)
    block("orientation", (36, 108, 1964, 170),
          "ATHENS  |  THE ACROPOLIS  |  ANCIENT SCULPTURES AND THE PERSIAN SACK", 29, 25, True)
    block("reading-heading", (1284, 184, 1964, 268), "PAUSANIAS ON THE SURVIVORS", 31, 27, True)
    block("translation", TEXT_RECT, passage, 44, 38)
    block("interpretive-caption", (36, 1688, 1964, 1780),
          "Interpretive bronze studies: Cycnus and Heracles, with a boar hunt beyond. "
          "Their lost forms and original placement remain uncertain, as does the hunt’s identity.", 29, 26)
    validate_fit_records(records)
    rendered = next(r.text for r in records if r.name == "translation")
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered English differs from the complete export")
    report = {
        "passage_id": "1.27.6", "preflight": preflight,
        "canvas": [2000, 1800], "art_rectangle": ART_RECT,
        "reading_order": "single continuous right-hand translation, top to bottom",
        "translation_characters": len(passage),
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 38,
        "padding": 18, "text_blocks_checked": len(records),
        "fit_records": [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Body font:", next(r.font_size for r in records if r.name == "translation"))
    if preflight:
        return
    if output.exists():
        raise RuntimeError("Refusing to overwrite " + str(output))
    with Image.open(ASSETS / "darkened_sculptures.png") as source:
        art = ImageOps.fit(source.convert("RGB"), (1200, 1480),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((35, 183, 1236, 1664), outline="#7b8980", width=2)
    draw.line((36, 173, 1964, 173), fill="#a3aba1", width=2)
    draw.line((1258, 184, 1258, 1664), fill="#b4b9ae", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/6.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
