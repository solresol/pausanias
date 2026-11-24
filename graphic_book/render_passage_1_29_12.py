#!/usr/bin/env python3
"""Render the Sicilian surrender and the complete exported passage."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphic_book.render_passage_1_3_2 import FitRecord, crop_to_fill, fit_text_block
from graphic_book_corpus import load_translation
from graphic_book_fonts import BODY_FONT, DISPLAY_FONT, TITLE_FONT

PASSAGE = "1.29.12"
ASSET = ROOT / "graphic_book/assets/generated/1_29_12/assinarus.png"
OUTPUT = ROOT / "graphic_book/images/1/29/12.png"
CANVAS = (3200, 2630)
ART = (90, 877, 3110, 2447)
PAPER = "#f3efe5"
INK = "#242a28"
ACCENT = "#3f5651"
PADDING = 21
BODY_MINIMUM = 54
SPACING_RATIO = 0.27


def render(output: Path, preflight: bool, report: Path | None) -> None:
    """Verify the entire reading and every glyph rectangle before saving."""
    english = load_translation(PASSAGE)
    page = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(page)
    records = []
    lettering = []

    def measure(name, rect, text, font_path, largest, smallest, color=INK):
        font, lines, _, fit = fit_text_block(
            draw, rect, text, font_path, largest, smallest, PADDING, name, SPACING_RATIO
        )
        spacing = max(2, round(fit.font_size * SPACING_RATIO))
        left, top, _, _ = draw.multiline_textbbox((0, 0), lines, font=font, spacing=spacing)
        x0, y0, x1, y1 = rect
        origin = (x0 + PADDING - left, y0 + PADDING - top)
        bounds = draw.multiline_textbbox(origin, lines, font=font, spacing=spacing)
        if not (x0 + PADDING <= bounds[0] <= bounds[2] <= x1 - PADDING
                and y0 + PADDING <= bounds[1] <= bounds[3] <= y1 - PADDING):
            raise RuntimeError(f"{name} exceeds its padded rectangle")
        records.append(FitRecord(name, rect, font_path, fit.font_size, bounds, lines))
        lettering.append((origin, lines, font, spacing, color))
        return lines

    measure("passage-id", (69, 91, 1150, 175), f"PAUSANIAS {PASSAGE}", TITLE_FONT, 38, 33, ACCENT)
    measure("title", (66, 199, 1139, 518), "The missing\nname", DISPLAY_FONT, 151, 121)
    measure("site", (69, 548, 1150, 631), "ATHENS  ·  THE ACADEMY ROAD", TITLE_FONT, 36, 32, ACCENT)
    reading = measure("translation", (1170, 82, 3125, 820), english, BODY_FONT, 65, BODY_MINIMUM)
    if reading.replace("\n", " ") != english:
        raise RuntimeError("The measured reading differs from the exact exported text")
    measure("caption", (69, 2471, 3127, 2582),
            "Sicily, 413 BCE  ·  An imagined view of Nicias surrendering at the Assinarus.",
            BODY_FONT, 42, 37, ACCENT)

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        x0, y0, x1, y1 = ART
        page.paste(crop_to_fill(ASSET, (x1 - x0, y1 - y0)), (x0, y0))
        draw.line((90, 846, 3110, 846), fill="#88968b", width=2)
        for origin, lines, font, spacing, color in lettering:
            draw.multiline_text(origin, lines, font=font, spacing=spacing, fill=color)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if report is not None:
        report.write_text(json.dumps({
            "passage": PASSAGE,
            "canvas": CANVAS,
            "art": ART,
            "minimum_body_px": BODY_MINIMUM,
            "padding_px": PADDING,
            "english_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "english_characters": len(english),
            "english_words": len(english.split()),
            "fields": [asdict(record) for record in records],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: {len(english.split())} words, {len(records)} measured fields, "
          f"{records[3].font_size}px body")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--layout-report", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
