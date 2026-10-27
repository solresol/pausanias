#!/usr/bin/env python3
"""Typeset the complete Cretan-bull account beside an interpretive river scene."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_27_9"
ART_RECT = (36, 220, 1336, 1840)
BODY_RECT = (1380, 306, 2164, 1840)


def render(output: Path, preflight: bool = False) -> None:
    """Measure every glyph before art access and refuse unreadable overflow."""
    snapshot_path()
    passage = load_translation("1.27.9")
    page = Image.new("RGB", (2200, 2000), "#eeeade")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
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
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure("passage-id", (36, 20, 590, 114), "PASSAGE 1.27.9", 42, 36, True)
    measure("title", (630, 20, 2164, 114), "THE CRETAN BULL", 60, 44, True)
    measure("orientation", (36, 122, 2164, 194),
            "ATHENS, ACROPOLIS: A DEDICATION  |  CRETE: THE STORY OF THE BULL", 33, 28, True)
    measure("reading-heading", (1380, 220, 2164, 294),
            "THE ACCOUNT IN PAUSANIAS", 32, 28, True)
    measure("translation", BODY_RECT, passage, 46, 40)
    measure("interpretive-caption", (36, 1870, 2164, 1980),
            "Interpretive scene of the Cretan bull; the landscape and animal's appearance are conjectural. "
            "No precise site is asserted for the river Tethris.", 30, 27)
    validate_fit_records(records)
    rendered = next(r.text for r in records if r.name == "translation")
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("The complete exported English must remain in source order")
    report = {
        "passage_id": "1.27.9", "preflight": preflight, "canvas": [2200, 2000],
        "art_rectangle": ART_RECT, "translation_rectangle": BODY_RECT,
        "reading_order": "one continuous right-hand field, top to bottom",
        "translation_characters": len(passage), "translation_words": len(passage.split()),
        "translation_exact": passage,
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 40,
        "padding": 18, "text_blocks_checked": len(records),
        "fit_records": [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("fit_records", "translation_exact")}))
    print("Body font:", next(r.font_size for r in records if r.name == "translation"))
    if preflight:
        return
    if output.exists():
        raise RuntimeError("Refusing to overwrite " + str(output))
    with Image.open(ASSETS / "cretan_bull_river.png") as source:
        art = ImageOps.fit(source.convert("RGB"), (1300, 1620),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((35, 219, 1336, 1840), outline="#7f8772", width=2)
    draw.line((36, 202, 2164, 202), fill="#9da18b", width=2)
    draw.line((1358, 220, 1358, 1840), fill="#b4b49e", width=2)
    draw.line((36, 1856, 2164, 1856), fill="#9da18b", width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill="#29382f")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/9.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
