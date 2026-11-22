#!/usr/bin/env python3
"""Render the Perinthus seascape and its complete exported English passage."""

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

PASSAGE = "1.29.10"
ASSETS = ROOT / "graphic_book/assets/generated/1_29_10"
CANVAS = (3200, 2500)
PANEL = (340, 1630, 2860, 2360)
BODY_RECT = (380, 1662, 2820, 2212)
CAPTION_RECT = (380, 2235, 2820, 2340)
TITLE_RECT = (90, 80, 1870, 241)
LOCATION_RECT = (94, 261, 1920, 348)
ID_RECT = (2360, 91, 3125, 192)
PAPER = "#f5f0e6"
INK = "#192b2c"
ACCENT = "#2e494b"
RULE = "#a49a85"
PADDING = 24
BODY_MINIMUM = 50
SPACING_RATIO = 0.24


def render(output: Path, preflight: bool, layout_report: Path | None) -> None:
    """Fit and verify all lettering before loading art or saving a page."""
    english = load_translation(PASSAGE)
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    records = []
    placements = []

    def measure(name, rect, words, font_path, maximum, minimum, fill=INK):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, words, font_path, maximum, minimum, PADDING, name,
            SPACING_RATIO,
        )
        spacing = max(2, round(fit.font_size * SPACING_RATIO))
        left, top, _, _ = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        x0, y0, x1, y1 = rect
        origin = (x0 + PADDING - left, y0 + PADDING - top)
        bounds = draw.multiline_textbbox(origin, wrapped, font=font, spacing=spacing)
        if not (x0 + PADDING <= bounds[0] <= bounds[2] <= x1 - PADDING
                and y0 + PADDING <= bounds[1] <= bounds[3] <= y1 - PADDING):
            raise RuntimeError(f"{name}: glyphs overflow padded rectangle")
        records.append(FitRecord(name, rect, font_path, fit.font_size, bounds, wrapped))
        placements.append((origin, wrapped, font, spacing, fill))

    measure("title", TITLE_RECT, "Perinthus holds", TITLE_FONT, 116, 95)
    measure("orientation", LOCATION_RECT, "NORTHERN PROPONTIS · c. 340 BCE", TITLE_FONT, 36, 32, ACCENT)
    measure("passage-id", ID_RECT, f"PAUSANIAS {PASSAGE}", TITLE_FONT, 42, 38, ACCENT)
    measure("translation", BODY_RECT, english, BODY_FONT, 58, BODY_MINIMUM)
    if records[-1].text.replace("\n", " ") != english:
        raise RuntimeError("Text wrapping changed the exported English beyond display line breaks")
    measure(
        "caption", CAPTION_RECT,
        "An imagined view of Perinthus during Philip’s siege, following Diodorus. "
        "Pausanias recalls it at Athens’s public burial ground.",
        BODY_FONT, 33, 29, ACCENT,
    )

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        page = crop_to_fill(ASSETS / "perinthus.png", CANVAS)
        panel_art = page.crop(PANEL)
        paper = Image.new("RGB", panel_art.size, PAPER)
        page.paste(Image.blend(panel_art, paper, 0.98), PANEL[:2])
        draw = ImageDraw.Draw(page)
        draw.rectangle((PANEL[0], PANEL[1], PANEL[2] - 1, PANEL[3] - 1), outline=RULE, width=2)
        draw.line((404, 2224, 2796, 2224), fill=RULE, width=2)
        for origin, wrapped, font, spacing, fill in placements:
            draw.multiline_text(origin, wrapped, font=font, spacing=spacing, fill=fill)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if layout_report is not None:
        layout_report.parent.mkdir(parents=True, exist_ok=True)
        layout_report.write_text(json.dumps({
            "passage_id": PASSAGE,
            "canvas": CANVAS,
            "text_panel": PANEL,
            "padding": PADDING,
            "translation_minimum": BODY_MINIMUM,
            "translation_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "text": [asdict(record) for record in records],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: {len(english)} characters, {len(english.split())} words, "
          f"{len(records)} measured fields, {records[3].font_size}px English")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--layout-report", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/29/10.png")
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
