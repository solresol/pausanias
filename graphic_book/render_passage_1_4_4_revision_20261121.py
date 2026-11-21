#!/usr/bin/env python3
"""Render a review candidate for Pausanias's account of the storm at Delphi."""

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

PASSAGE = "1.4.4"
ASSETS = ROOT / "graphic_book/assets/generated/1_4_4/revisions/20261121"
OUTPUT = ROOT / "graphic_book/workflow/replacement-1_4_4-20261121/candidate.png"
CANVAS = (3100, 2950)
ART = (70, 860, 3030, 2260)
PAD = 24
MINIMUM = 51
LEADING = 0.25
PAPER = "#eae7df"
INK = "#262e31"
ACCENT = "#375157"
RULE = "#9aa6a2"


def render(output: Path, *, preflight: bool) -> None:
    """Measure the whole exact translation before attempting to open the art."""
    passage = load_translation(PASSAGE)
    before, boundary, after = passage.partition(" When the two sides")
    if not boundary:
        raise RuntimeError("Expected sentence boundary missing from exported 1.4.4")
    latter = boundary[1:] + after
    if before + " " + latter != passage:
        raise RuntimeError("Translation fragments did not reassemble exactly")

    page = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    positions = []

    def measure(name, bounds, text, maximum, minimum, *, heading=False):
        face = TITLE_FONT if heading else BODY_FONT
        font, wrapped, _, fit = fit_text_block(
            draw, bounds, text, face, maximum, minimum, PAD, name, LEADING,
        )
        spacing = max(2, round(fit.font_size * LEADING))
        measured = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        x0, y0, x1, y1 = bounds
        xy = (x0 + PAD - measured[0], y0 + PAD - measured[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < x0 + PAD or actual[1] < y0 + PAD
                or actual[2] > x1 - PAD or actual[3] > y1 - PAD):
            raise RuntimeError(f"{name}: text exceeds padded rectangle")
        records.append(FitRecord(name, bounds, face, fit.font_size, actual, wrapped))
        positions.append((xy, wrapped, font, spacing, ACCENT if heading else INK))

    measure("title", (46, 38, 1780, 200), "Storm at Delphi", 109, 93, heading=True)
    measure("passage-id", (1950, 59, 3030, 137), f"PAUSANIAS {PASSAGE}", 37, 33, heading=True)
    measure(
        "orientation", (1950, 140, 3030, 217), "DELPHI, MOUNT PARNASSUS",
        36, 32, heading=True,
    )
    measure("phase-1", (46, 259, 525, 460), "1. The approach to Delphi", 50, 43, heading=True)
    measure("phase-2", (46, 2318, 525, 2530), "2. The storm and the heroes", 50, 43, heading=True)
    body = (((556, 259, 3030, 797), before), ((556, 2318, 3030, 2778), latter))
    for size in range(59, MINIMUM - 1, -1):
        try:
            for i, (bounds, text) in enumerate(body, 1):
                fit_text_block(
                    draw, bounds, text, BODY_FONT, size, size, PAD, f"translation-{i}", LEADING,
                )
        except RuntimeError:
            continue
        break
    else:
        raise RuntimeError("Full 1.4.4 text exceeds the minimum readable layout")
    for i, (bounds, text) in enumerate(body, 1):
        measure(f"translation-{i}", bounds, text, size, size)
    measure(
        "caption", (46, 2814, 3030, 2938),
        "Apollo's sanctuary beneath the Phaedriades cliffs. The painting imagines "
        "the approach, rockfall and portents in Pausanias's account.",
        38, 35,
    )
    validate_fit_records(records)
    visual = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if visual.split() != passage.split():
        raise RuntimeError("Rendered English differs from the export beyond layout whitespace")

    result = {
        "passage": PASSAGE,
        "canvas": CANVAS,
        "art_rectangle": ART,
        "preflight": preflight,
        "reading_order": ["upper prose", "lower prose"],
        "english": passage,
        "english_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "body_px": size,
        "minimum_body_px": MINIMUM,
        "padding_px": PAD,
        "fields": [asdict(r) for r in records],
    }
    if not preflight:
        canonical = ROOT / "graphic_book/images/1/4/4.png"
        if output.resolve() == canonical.resolve() or output.exists():
            raise FileExistsError(output)
        component = ASSETS / "delphi_storm.png"
        with Image.open(component) as source:
            result["art_source_dimensions"] = source.size
        x0, y0, x1, y1 = ART
        page.paste(crop_to_fill(component, (x1 - x0, y1 - y0)), (x0, y0))
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=RULE, width=2)
        for y in (235, 822, 2287, 2801):
            draw.line((70, y, 3030, y), fill=RULE, width=2)
        for xy, wrapped, font, spacing, color in positions:
            draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill=color)
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)

    (ASSETS / "layout_report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{PASSAGE}: {len(passage)} characters, {len(passage.split())} words, "
          f"{len(records)} fields measured, {size}px body")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    render(args.output, preflight=args.preflight)
