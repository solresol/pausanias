#!/usr/bin/env python3
"""Render the triremes of Pausanias 1.29.14 beside the exported English."""

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

PASSAGE = "1.29.14"
ASSETS = ROOT / "graphic_book/assets/generated/1_29_14"
OUTPUT = ROOT / "graphic_book/images/1/29/14.png"
CANVAS = (3840, 2350)
ART = (0, 0, 2360, 2350)
PAPER = "#f2eee4"
INK = "#242e2b"
ACCENT = "#445e58"
PADDING = 24
SPACING_RATIO = 0.29


def render(output: Path, preflight: bool, report: Path | None) -> None:
    """Check the full reading and every glyph rectangle before drawing."""
    english = load_translation(PASSAGE)
    page = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(page)
    records = []
    lettering = []

    def measure(name, rect, content, font_path, largest, smallest, color=INK):
        font, lines, _, fit = fit_text_block(
            draw, rect, content, font_path, largest, smallest, PADDING, name, SPACING_RATIO
        )
        spacing = max(2, round(fit.font_size * SPACING_RATIO))
        left, top, _, _ = draw.multiline_textbbox((0, 0), lines, font=font, spacing=spacing)
        x0, y0, x1, y1 = rect
        origin = (x0 + PADDING - left, y0 + PADDING - top)
        bounds = draw.multiline_textbbox(origin, lines, font=font, spacing=spacing)
        if not (
            x0 + PADDING <= bounds[0] <= bounds[2] <= x1 - PADDING
            and y0 + PADDING <= bounds[1] <= bounds[3] <= y1 - PADDING
        ):
            raise RuntimeError(f"{name} exceeds its padded rectangle")
        record = FitRecord(name, rect, font_path, fit.font_size, bounds, lines)
        records.append(record)
        lettering.append((origin, lines, font, spacing, color))
        return record

    measure("passage-id", (2456, 145, 3730, 228), f"PAUSANIAS  {PASSAGE}", TITLE_FONT, 44, 40, ACCENT)
    measure("title", (2456, 253, 3764, 461), "Five Attic triremes", DISPLAY_FONT, 120, 108)
    measure(
        "location", (2456, 477, 3730, 572), "ATHENS  ·  THE ACADEMY ROAD",
        TITLE_FONT, 39, 36, ACCENT,
    )
    reading = measure("translation", (2456, 653, 3742, 1986), english, BODY_FONT, 62, 58)
    if reading.text.replace("\n", " ") != english:
        raise RuntimeError("The measured reading differs from the exact exported English")
    caption_top = reading.text_bbox[3] + 108
    measure(
        "caption", (2456, caption_top, 3742, min(caption_top + 160, 2240)),
        "The Athenian squadron in Pausanias’ account, imagined.",
        BODY_FONT, 42, 38, ACCENT,
    )

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        x0, y0, x1, y1 = ART
        page.paste(crop_to_fill(ASSETS / "triremes.png", (x1 - x0, y1 - y0)), (x0, y0))
        draw.line((2480, caption_top - 16, 2820, caption_top - 16), fill="#84968c", width=3)
        for origin, lines, font, spacing, color in lettering:
            draw.multiline_text(origin, lines, font=font, spacing=spacing, fill=color)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if report is not None:
        report.write_text(json.dumps({
            "passage": PASSAGE,
            "canvas": CANVAS,
            "art_rectangle": ART,
            "padding_px": PADDING,
            "english_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "english_characters": len(english),
            "english_words": len(english.split()),
            "fields": [asdict(record) for record in records],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: {len(english.split())} words, {len(records)} measured fields, {reading.font_size}px English")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--layout-report", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
