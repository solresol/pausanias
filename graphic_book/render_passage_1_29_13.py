#!/usr/bin/env python3
"""Render the Academy road memorials with the complete exported English."""

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

PASSAGE = "1.29.13"
ASSETS = ROOT / "graphic_book/assets/generated/1_29_13"
OUTPUT = ROOT / "graphic_book/images/1/29/13.png"
CANVAS = (3936, 2350)
ROAD = (98, 377, 1528, 2167)
STELE = (3010, 650, 3838, 1870)
PAPER = "#f3eee4"
INK = "#272b24"
ACCENT = "#704b3e"
PADDING = 24
BODY_SIZE = 61
SPACING_RATIO = 0.28


def render(output: Path, preflight: bool, layout_report: Path | None) -> None:
    """Measure all lettering and verify the reading before loading any art."""
    english = load_translation(PASSAGE)
    split = english.index(" Buried here, too,")
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
        record = FitRecord(name, rect, font_path, fit.font_size, bounds, lines)
        records.append(record)
        lettering.append((origin, lines, font, spacing, color))
        return record

    measure("passage-id", (74, 45, 1460, 132), f"PAUSANIAS  {PASSAGE}", TITLE_FONT, 41, 39, ACCENT)
    measure("title", (74, 148, 2895, 316), "The names along the road", DISPLAY_FONT, 114, 104)
    measure("location", (2890, 225, 3862, 315), "ATHENS  ·  THE ACADEMY ROAD", TITLE_FONT, 38, 35, ACCENT)

    first = measure("translation-first", (1576, 397, 2956, 1070), english[:split],
                    BODY_FONT, BODY_SIZE, BODY_SIZE)
    second = measure("translation-second", (1576, first.text_bbox[3] + 51, 2956, 2167),
                     english[split + 1:], BODY_FONT, BODY_SIZE, BODY_SIZE)
    reading = " ".join(field.text.replace("\n", " ") for field in (first, second))
    if reading != english:
        raise RuntimeError("The measured reading differs from the exact exported English")

    measure("road-caption", (74, 2194, 1552, 2326),
            "The Athenian public burial ground on the road to the Academy, imagined.",
            BODY_FONT, 39, 35, ACCENT)
    measure("stele-caption", (2986, 1895, 3862, 2055), "An imagined detail of a memorial stele.",
            BODY_FONT, 37, 35, ACCENT)

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        for asset, rect in (("academy-road.png", ROAD), ("stele-detail.png", STELE)):
            x0, y0, x1, y1 = rect
            page.paste(crop_to_fill(ASSETS / asset, (x1 - x0, y1 - y0)), (x0, y0))
        draw.line((98, 340, 3838, 340), fill="#a59080", width=2)
        for origin, lines, font, spacing, color in lettering:
            draw.multiline_text(origin, lines, font=font, spacing=spacing, fill=color)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if layout_report is not None:
        layout_report.write_text(json.dumps({
            "passage": PASSAGE,
            "canvas": CANVAS,
            "art_rectangles": (ROAD, STELE),
            "padding_px": PADDING,
            "english_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "english_characters": len(english),
            "english_words": len(english.split()),
            "fields": [asdict(record) for record in records],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: {len(english.split())} words, {len(records)} measured fields, {BODY_SIZE}px English")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--layout-report", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
