#!/usr/bin/env python3
"""Render the Academy road memorial and the complete exported English passage."""

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
from graphic_book_fonts import BODY_FONT, TITLE_FONT

PASSAGE = "1.29.11"
ASSET = ROOT / "graphic_book/assets/generated/1_29_11/academy-road.png"
OUTPUT = ROOT / "graphic_book/images/1/29/11.png"
CANVAS = (3200, 2500)
ART = (900, 405, 2300, 2185)
PAPER = "#f3eddf"
INK = "#28221e"
ACCENT = "#704033"
RULE = "#997a68"
PADDING = 14
SPACING_RATIO = 0.26
BODY_MINIMUM = 49
SECOND = "After describing those who died at Corinth,"


def render(output: Path, preflight: bool, report: Path | None) -> None:
    """Measure every text field before opening the art or creating the output."""
    english = load_translation(PASSAGE)
    first, marker, remainder = english.partition(" " + SECOND)
    if not marker or not first.endswith("."):
        raise RuntimeError("The intended sentence break is missing from the export")
    second = marker[1:] + remainder

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

    measure("title", (107, 94, 2340, 253), "Fortune and the fallen", TITLE_FONT, 121, 100)
    measure("orientation", (110, 276, 2260, 349),
            "ATHENS  ·  THE PUBLIC GRAVES ON THE ACADEMY ROAD", TITLE_FONT, 35, 32, ACCENT)
    measure("passage-id", (2450, 134, 3080, 212),
            f"PAUSANIAS {PASSAGE}", TITLE_FONT, 44, 39, ACCENT)

    measure("first-heading", (105, 610, 820, 698),
            "1. Corinth and Leuctra", TITLE_FONT, 46, 40, ACCENT)
    first_lines = measure("first-reading", (105, 731, 820, 2050),
                          first, BODY_FONT, 53, BODY_MINIMUM)
    measure("second-heading", (2380, 822, 3095, 910),
            "2. The elegiac verses", TITLE_FONT, 46, 40, ACCENT)
    second_lines = measure("second-reading", (2380, 943, 3095, 2080),
                           second, BODY_FONT, 53, BODY_MINIMUM)
    reconstructed = " ".join((first_lines.replace("\n", " "), second_lines.replace("\n", " ")))
    if reconstructed != english:
        raise RuntimeError("The fitted reading is not verbatim")

    measure("caption", (900, 2220, 2300, 2380),
            "An imagined view of the public graves on the Academy road, informed by "
            "surviving Athenian casualty stelai.", BODY_FONT, 34, 31, ACCENT)

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        x0, y0, x1, y1 = ART
        page.paste(crop_to_fill(ASSET, (x1 - x0, y1 - y0)), (x0, y0))
        draw.rectangle((x0 - 2, y0 - 2, x1 + 1, y1 + 1), outline=RULE, width=2)
        draw.line((119, 371, 3081, 371), fill=RULE, width=2)
        draw.line((119, 707, 805, 707), fill=RULE, width=2)
        draw.line((2394, 919, 3081, 919), fill=RULE, width=2)
        for origin, lines, font, spacing, color in lettering:
            draw.multiline_text(origin, lines, font=font, spacing=spacing, fill=color)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if report is not None:
        report.write_text(json.dumps({
            "passage": PASSAGE,
            "canvas": CANVAS,
            "art": ART,
            "text_padding_px": PADDING,
            "minimum_body_px": BODY_MINIMUM,
            "english_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "english_word_count": len(english.split()),
            "fields": [asdict(record) for record in records],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: {len(english.split())} words, {len(records)} measured fields, "
          f"{records[4].font_size}px and {records[6].font_size}px body text")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--layout-report", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
