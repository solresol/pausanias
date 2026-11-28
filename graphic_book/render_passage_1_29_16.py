#!/usr/bin/env python3
"""Set Pausanias 1.29.16 with two reconstructions of Lycurgus's works."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphic_book.render_passage_1_29_15 import measure
from graphic_book.render_passage_1_3_2 import crop_to_fill
from graphic_book_corpus import load_translation
from graphic_book_fonts import BODY_FONT, DISPLAY_FONT, TITLE_FONT

PASSAGE = "1.29.16"
ASSETS = ROOT / "graphic_book/assets/generated/1_29_16"
OUTPUT = ROOT / "graphic_book/images/1/29/16.png"
CANVAS = (3840, 2560)
PAPER = "#f3eee2"
INK = "#202827"
ACCENT = "#374c51"
RULE = "#9b8870"
HERO = (112, 270, 3728, 1718)
OBJECTS = (2724, 1856, 3728, 2399)
READING = ((105, 1853, 1297, 2499), (1353, 1853, 2624, 2499))


def artwork(page: Image.Image, rect: tuple[int, int, int, int], name: str) -> None:
    left, top, right, bottom = rect
    plate = crop_to_fill(ASSETS / name, (right - left, bottom - top))
    page.paste(plate, (left, top))


def render(output: Path, preflight: bool, audit: Path | None) -> None:
    english = load_translation(PASSAGE)
    split = english.index(" As for building projects,")
    parts = (english[:split], english[split + 1 :])

    page = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(page)
    # Both columns share a type size and read downward, then left to right.
    reading = [
        measure(draw, f"translation-{index}", rect, part, BODY_FONT, (49, 49), INK)
        for index, (rect, part) in enumerate(zip(READING, parts, strict=True), 1)
    ]
    if " ".join(block.fit.text.replace("\n", " ") for block in reading) != english:
        raise ValueError("The laid-out English differs from the complete corpus translation")

    fields = [
        measure(draw, "location", (101, 67, 1920, 116),
                "ATHENS AND PIRAEUS", TITLE_FONT, (32, 32), ACCENT),
        measure(draw, "passage", (3340, 67, 3728, 116),
                f"PAUSANIAS  {PASSAGE}", TITLE_FONT, (32, 32), ACCENT),
        measure(draw, "title", (97, 122, 3700, 257),
                "The works of Lycurgus", DISPLAY_FONT, (105, 105), INK),
        measure(draw, "shipshed-caption", (105, 1735, 3728, 1796),
                "Zea Harbour, Piraeus. Reconstruction of fourth-century BCE shipsheds and a trireme undergoing repairs.",
                BODY_FONT, (38, 38), ACCENT),
        *reading,
        measure(draw, "dedications-caption", (2715, 2410, 3728, 2524),
                "Acropolis dedications, reconstructed from the decree’s literary account.",
                BODY_FONT, (34, 34), ACCENT),
    ]

    if not preflight:
        if output.exists():
            raise FileExistsError(output)
        artwork(page, HERO, "zea_shipsheds.png")
        artwork(page, OBJECTS, "acropolis_dedications.png")
        draw.line((112, 1818, 3728, 1818), fill=RULE, width=3)
        draw.line((1326, 1864, 1326, 2454), fill=RULE, width=2)
        for field in fields:
            field.draw(draw)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output, dpi=(300, 300))

    if audit is not None:
        audit.write_text(json.dumps({
            "passage": PASSAGE,
            "canvas": CANVAS,
            "english_sha256": hashlib.sha256(english.encode()).hexdigest(),
            "english_characters": len(english),
            "english_words": len(english.split()),
            "art_rectangles": [HERO, OBJECTS],
            "fields": [vars(field.fit) for field in fields],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{PASSAGE}: all {len(english.split())} words verified across two columns, "
          f"{len(fields)} measured fields")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--layout-report", type=Path)
    args = parser.parse_args()
    render(args.output, args.preflight, args.layout_report)
