#!/usr/bin/env python3
"""Typeset Pausanias's full Marathon-bull account above a panoramic journey."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_27_10"
ART_RECT = (36, 1000, 2364, 2000)
BODY_RECTS = ((36, 282, 1170, 944), (1230, 282, 2364, 944))


def render(output: Path, preflight: bool = False) -> None:
    """Measure all text before touching art and fail on unreadable overflow."""
    snapshot_path()
    passage = load_translation("1.27.10")
    first, boundary, rest = passage.partition(" Consequently Minos")
    if not boundary:
        raise RuntimeError("Expected exported sentence boundary missing")
    chunks = (first, boundary[1:] + rest)
    if " ".join(chunks) != passage:
        raise RuntimeError("Exact source substring reassembly failed")
    page = Image.new("RGB", (2400, 2100), "#eeebe4")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 18, name, .22,
        )
        spacing = max(2, round(fit.font_size * .22))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 18 - bbox[0], rect[1] + 18 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 18 or actual[1] < rect[1] + 18
                or actual[2] > rect[2] - 18 or actual[3] > rect[3] - 18):
            raise RuntimeError(name + ": glyphs overflow padded target")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure("passage-id", (36, 20, 650, 110), "PASSAGE 1.27.10", 42, 36, True)
    measure("title", (680, 20, 2364, 110), "FROM MARATHON TO THE ACROPOLIS", 54, 42, True)
    measure("orientation", (36, 118, 2364, 188),
            "ATTICA, THE PLAIN OF MARATHON  |  THESEUS DRIVES THE BULL TOWARD ATHENS", 33, 28, True)
    measure("interpretive-caption", (36, 2016, 2364, 2098),
            "Theseus and the Marathon bull, before the offering. Interpretive scene: figures, dress and landscape are conjectural; no exact route is asserted.", 31, 27)
    for i, (rect, heading) in enumerate(zip(
        ((36, 204, 1170, 278), (1230, 204, 2364, 278)),
        ("1  THE BULL REACHES MARATHON", "2  MINOS'S DEMAND AND THESEUS'S OFFERING"), strict=True,
    )):
        measure(f"reading-heading-{i+1}", rect, heading, 33, 28, True)
    # Both source-order fields use the same size, determined before art access.
    size = 46
    while True:
        try:
            for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
                fit_text_block(draw, rect, text, BODY_FONT, size, size, 18, f"translation-{i+1}", .22)
            break
        except RuntimeError:
            size -= 1
            if size < 40:
                raise RuntimeError("Full English does not fit at the readable minimum")
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f"translation-{i+1}", rect, text, size, size)
    validate_fit_records(records)
    rendered = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("The complete English must remain in source order")
    report = {
        "passage_id": "1.27.10", "preflight": preflight, "canvas": [2400, 2100],
        "art_rectangle": ART_RECT, "translation_rectangles": BODY_RECTS,
        "reading_order": "numbered upper columns: left top-to-bottom, then right top-to-bottom",
        "translation_characters": len(passage), "translation_words": len(passage.split()),
        "translation_exact": passage, "translation_chunks": chunks,
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 40,
        "body_font_size": size, "padding": 18,
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
    with Image.open(ASSETS / "marathon_journey.png") as source:
        art = ImageOps.fit(source.convert("RGB"), (2328, 1000), method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((35, 999, 2364, 2000), outline="#7f7976", width=2)
    draw.line((36, 198, 2364, 198), fill="#aaa194", width=2)
    draw.line((36, 974, 2364, 974), fill="#aaa194", width=2)
    draw.line((1200, 220, 1200, 944), fill="#b7ada2", width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill="#302f38")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/10.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
