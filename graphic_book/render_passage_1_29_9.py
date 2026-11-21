#!/usr/bin/env python3
"""Render the two phases of Pausanias's Tanagra account in reading order."""

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
from graphic_book.render_passage_1_10_1 import validate_fit_records
from graphic_book_corpus import load_translation
from graphic_book_fonts import BODY_FONT, TITLE_FONT

PASSAGE = "1.29.9"
ASSETS = ROOT / "graphic_book/assets/generated/1_29_9"
CANVAS = (3100, 2500)
ART = (
    ((75, 310, 1815, 1210), "tanagra_infantry.png"),
    ((1465, 1370, 3025, 2260), "tanagra_cavalry.png"),
)
BODY_RECTANGLES = ((1885, 458, 3025, 1220), (75, 1518, 1345, 2220))
PAD = 24
BODY_MINIMUM = 50
LINE_SPACING = 0.26
PAPER = "#f1ece2"
INK = "#282d36"
ACCENT = "#504158"
RULE = "#a69a91"


def render(output: Path, preflight: bool) -> None:
    """Measure every field before accepting raster inputs or writing the page."""
    passage = load_translation(PASSAGE)
    first, separator, second = passage.partition(" At first,")
    if not separator:
        raise RuntimeError("Expected sentence boundary missing from exported English")
    parts = (first, separator[1:] + second)
    if " ".join(parts) != passage:
        raise RuntimeError("English fragments failed exact source reassembly")

    page = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rectangle, content, font_path, maximum, minimum, color=INK):
        font, wrapped, _, fit = fit_text_block(
            draw, rectangle, content, font_path, maximum, minimum, PAD, name,
            LINE_SPACING,
        )
        spacing = max(2, round(fit.font_size * LINE_SPACING))
        glyphs = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        x0, y0, x1, y1 = rectangle
        xy = (x0 + PAD - glyphs[0], y0 + PAD - glyphs[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < x0 + PAD or actual[1] < y0 + PAD
                or actual[2] > x1 - PAD or actual[3] > y1 - PAD):
            raise RuntimeError(f"{name}: glyphs overflow padded rectangle")
        records.append(FitRecord(name, rectangle, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing, color))

    measure("title", (51, 45, 1770, 205), "At Tanagra", TITLE_FONT, 112, 96)
    measure(
        "passage-id", (1885, 66, 3025, 150), f"PAUSANIAS {PASSAGE}",
        TITLE_FONT, 40, 35, ACCENT,
    )
    measure(
        "orientation", (1885, 151, 3025, 238), "TANAGRA, BOEOTIA",
        TITLE_FONT, 37, 33, ACCENT,
    )
    measure(
        "phase-1", (1885, 310, 3025, 430), "1. Argos comes to aid Athens",
        TITLE_FONT, 50, 42, ACCENT,
    )
    measure(
        "phase-2", (75, 1370, 1345, 1488), "2. Nightfall and reversal",
        TITLE_FONT, 50, 42, ACCENT,
    )

    for size in range(60, BODY_MINIMUM - 1, -1):
        try:
            for index, (rect, text) in enumerate(zip(BODY_RECTANGLES, parts, strict=True), 1):
                fit_text_block(
                    draw, rect, text, BODY_FONT, size, size, PAD,
                    f"translation-{index}", LINE_SPACING,
                )
        except RuntimeError:
            continue
        break
    else:
        raise RuntimeError("The complete English exceeds the minimum readable layout")
    for index, (rect, text) in enumerate(zip(BODY_RECTANGLES, parts, strict=True), 1):
        measure(f"translation-{index}", rect, text, BODY_FONT, size, size)

    measure(
        "caption", (51, 2311, 3025, 2462),
        "Above, the Argive reinforcement. Below, Thessalian horsemen on the field "
        "where they changed sides. Both scenes imagine the terrain and positions "
        "around Tanagra.",
        BODY_FONT, 40, 35,
    )
    validate_fit_records(records)
    wrapped_passage = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(wrapped_passage.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered English differs from the source beyond line breaks")

    report = {
        "passage_id": PASSAGE,
        "canvas": CANVAS,
        "preflight": preflight,
        "art": ART,
        "reading_order": ["upper right", "lower left"],
        "translation": passage,
        "translation_characters": len(passage),
        "translation_words": len(passage.split()),
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "body_pixels": size,
        "body_minimum": BODY_MINIMUM,
        "padding": PAD,
        "text": [asdict(record) for record in records],
    }
    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        for rectangle, name in ART:
            x0, y0, x1, y1 = rectangle
            with Image.open(ASSETS / name) as source:
                source_size = source.size
            page.paste(crop_to_fill(ASSETS / name, (x1 - x0, y1 - y0)), (x0, y0))
            draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=RULE, width=2)
            report.setdefault("component_dimensions", {})[name] = source_size
        for y in (266, 1290, 2302):
            draw.line((75, y, 3025, y), fill=RULE, width=2)
        for xy, text, font, spacing, color in placements:
            draw.multiline_text(xy, text, font=font, spacing=spacing, fill=color)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)

    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{PASSAGE}: {len(passage)} characters, {len(passage.split())} words, "
          f"{len(records)} measured fields, {size}px body type")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/29/9.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
