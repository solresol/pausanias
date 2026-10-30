#!/usr/bin/env python3
"""Place Cylon's uncertain dedication in two ordered wings around a bronze study."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_28_1"
ART_RECT = (510, 220, 1890, 2040)
BODY_RECTS = ((36, 430, 474, 1390), (1926, 740, 2364, 2040))


def render(output: Path, preflight: bool = False) -> None:
    """Measure every text target before art access; fail at the readable minimum."""
    snapshot_path()
    passage = load_translation("1.28.1")
    first, boundary, rest = passage.partition(" However, my inference")
    if not boundary:
        raise RuntimeError("Expected exported sentence boundary missing")
    chunks = (first, boundary[1:] + rest)
    if " ".join(chunks) != passage:
        raise RuntimeError("Exact source substring reassembly failed")
    page = Image.new("RGB", (2400, 2100), "#edece6")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 16, name, .24,
        )
        spacing = max(2, round(fit.font_size * .24))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 16 - bbox[0], rect[1] + 16 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 16 or actual[1] < rect[1] + 16
                or actual[2] > rect[2] - 16 or actual[3] > rect[3] - 16):
            raise RuntimeError(name + ": glyphs overflow padded target")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing, heading))

    measure("passage-id", (36, 20, 620, 112), "PASSAGE 1.28.1", 42, 36, True)
    measure("title", (654, 20, 2364, 112), "CYLON: AN UNCERTAIN HONOUR", 60, 44, True)
    measure("orientation", (36, 126, 2364, 196),
            "ATHENS, THE ACROPOLIS  |  A BRONZE PORTRAIT AND PAUSANIAS'S INFERENCE", 32, 28, True)
    measure("reading-heading-1", (36, 274, 474, 402), "1  THE\nDEDICATION", 34, 30, True)
    measure("reading-heading-2", (1926, 560, 2364, 712), "2  HIS\nINFERENCE", 34, 30, True)
    size = 44
    while True:
        try:
            for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
                fit_text_block(draw, rect, text, BODY_FONT, size, size, 16, f"translation-{i+1}", .24)
            break
        except RuntimeError:
            size -= 1
            if size < 38:
                raise RuntimeError("Full English does not fit at the readable minimum")
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f"translation-{i+1}", rect, text, size, size)
    measure("interpretive-caption", (36, 1538, 474, 2040),
            "An interpretive bronze study. Cylon's appearance, the statue's design and its original placement are unknown; the dedication's reason remains uncertain.", 30, 28)
    validate_fit_records(records)
    rendered = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("The complete English must remain in source order")
    report = {
        "passage_id": "1.28.1", "preflight": preflight, "canvas": [2400, 2100],
        "art_rectangle": ART_RECT, "translation_rectangles": BODY_RECTS,
        "reading_order": "1: upper left top-to-bottom; 2: right top-to-bottom",
        "translation_characters": len(passage), "translation_words": len(passage.split()),
        "translation_exact": passage, "translation_chunks": chunks,
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 38,
        "body_font_size": size, "padding": 16,
        "text_blocks_checked": len(records), "fit_records": [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("fit_records", "translation_exact", "translation_chunks")}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError("Refusing to overwrite " + str(output))
    with Image.open(ASSETS / "cylon_bronze.png") as source:
        art = ImageOps.fit(source.convert("RGB"), (1380, 1820), method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((509, 219, 1890, 2040), outline="#7b827b", width=2)
    draw.line((36, 207, 2364, 207), fill="#aaa58e", width=2)
    draw.line((52, 1488, 458, 1488), fill="#aaa58e", width=2)
    for xy, text, font, spacing, heading in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing,
                            fill="#2b3a3b" if heading else "#30393a")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/28/1.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
