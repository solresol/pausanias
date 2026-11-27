#!/usr/bin/env python3
"""Render Pausanias 1.29.15 over a reconstruction of the Academy Road."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphic_book.render_passage_1_3_2 import FitRecord, crop_to_fill, fit_text_block
from graphic_book_corpus import load_translation
from graphic_book_fonts import BODY_FONT, DISPLAY_FONT, TITLE_FONT

PASSAGE = "1.29.15"
ASSETS = ROOT / "graphic_book/assets/generated/1_29_15"
OUTPUT = ROOT / "graphic_book/images/1/29/15.png"
CANVAS = (3840, 2160)
OPENING = (104, 104, 1516, 747)
CONTINUATION = (1810, 1400, 3736, 2100)
PAPER = "#f4eee0"
RULE = "#aa8b70"
INK = "#242c24"
ACCENT = "#694735"
SPACING_RATIO = 0.31
PADDING = 12
Box = tuple[int, int, int, int]


@dataclass
class TextField:
    """A measured local text field and the exact drawing parameters."""

    fit: FitRecord
    origin: tuple[int, int]
    font: ImageFont.FreeTypeFont
    spacing: int
    color: str

    def draw(self, surface: ImageDraw.ImageDraw) -> None:
        surface.multiline_text(
            self.origin, self.fit.text, font=self.font, spacing=self.spacing, fill=self.color
        )


def measure(
    surface: ImageDraw.ImageDraw,
    name: str,
    box: Box,
    text: str,
    font_path: str,
    sizes: tuple[int, int],
    color: str = INK,
) -> TextField:
    """Check actual glyph bounds against all four padded edges."""
    font, wrapped, _, fit = fit_text_block(
        surface, box, text, font_path, *sizes, PADDING, name, SPACING_RATIO
    )
    spacing = max(2, round(fit.font_size * SPACING_RATIO))
    left, top, _, _ = surface.multiline_textbbox(
        (0, 0), wrapped, font=font, spacing=spacing
    )
    x0, y0, x1, y1 = box
    origin = (x0 + PADDING - left, y0 + PADDING - top)
    bounds = surface.multiline_textbbox(origin, wrapped, font=font, spacing=spacing)
    if not (
        x0 + PADDING <= bounds[0] <= bounds[2] <= x1 - PADDING
        and y0 + PADDING <= bounds[1] <= bounds[3] <= y1 - PADDING
    ):
        raise RuntimeError(f"{name} exceeds its padded rectangle")
    fit.text_bbox = bounds
    return TextField(fit, origin, font, spacing, color)


def render(output: Path, preflight: bool, report: Path | None) -> None:
    english = load_translation(PASSAGE)
    split = english.index(". Here too lies ") + 1
    opening = english[:split]
    continuation = english[split + 1 :]
    page = Image.new("RGB", CANVAS)
    surface = ImageDraw.Draw(page)

    title = measure(surface, "title", (156, 229, 1464, 370),
                    "Graves by the Academy", DISPLAY_FONT, (103, 92))
    first = measure(surface, "translation-1", (156, 439, 1464, 725),
                    opening, BODY_FONT, (54, 54))
    second = measure(surface, "translation-2", (1862, 1490, 3684, 1930),
                     continuation, BODY_FONT, (54, 54))
    reconstructed = " ".join(
        field.fit.text.replace("\n", " ") for field in (first, second)
    )
    if reconstructed != english:
        raise RuntimeError("The measured text differs from the complete exported English")

    fields = [
        measure(surface, "passage-id", (156, 153, 1464, 218),
                f"PAUSANIAS  {PASSAGE}   ·   ATHENS", TITLE_FONT, (40, 37), ACCENT),
        title,
        measure(surface, "first-reading-marker", (156, 375, 1464, 435),
                "I", TITLE_FONT, (36, 34), ACCENT),
        first,
        measure(surface, "second-reading-marker", (1862, 1434, 3684, 1488),
                "II", TITLE_FONT, (35, 32), ACCENT),
        second,
        measure(surface, "reconstruction-caption", (1862, 1944, 3684, 2061),
                "Reconstruction based on Lycurgus’s excavated family plot. "
                "The precise grave Pausanias saw remains uncertain.",
                BODY_FONT, (41, 38), ACCENT),
    ]

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        page.paste(crop_to_fill(ASSETS / "academy_road.png", CANVAS))
        for box in (OPENING, CONTINUATION):
            surface.rectangle(box, fill=PAPER, outline=RULE, width=3)
        surface.line((1874, 1931, 2155, 1931), fill=RULE, width=3)
        for field in fields:
            field.draw(surface)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if report is not None:
        audit = {
            "passage": PASSAGE,
            "canvas": CANVAS,
            "paper_rectangles": [OPENING, CONTINUATION],
            "padding_px": PADDING,
            "english_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "english_characters": len(english),
            "english_words": len(english.split()),
            "fields": [asdict(field.fit) for field in fields],
        }
        report.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: {len(english.split())} exact words at {first.fit.font_size} px; "
          f"{len(fields)} measured fields")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--layout-report", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
