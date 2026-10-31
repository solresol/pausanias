#!/usr/bin/env python3
"""Set two bronze dedications diagonally against ordered, exact English prose."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_28_2"
ART_RECTS = ((36, 220, 1376, 1440), (1270, 1490, 2364, 2280))
BODY_RECTS = ((1430, 350, 2364, 1440), (36, 1580, 1220, 2210))


def render(output: Path, preflight: bool = False) -> None:
    """Fit every glyph before reading art and reject unreadable or partial prose."""
    snapshot_path()
    passage = load_translation("1.28.2")
    first, boundary, rest = passage.partition(" There is also placed there")
    if not boundary:
        raise RuntimeError("Expected exported sentence boundary missing")
    chunks = (first, boundary[1:] + rest)
    if " ".join(chunks) != passage:
        raise RuntimeError("Exact source substring reassembly failed")
    page = Image.new("RGB", (2400, 2400), "#f0eee6")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 18, name, .24,
        )
        spacing = max(2, round(fit.font_size * .24))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 18 - bbox[0], rect[1] + 18 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 18 or actual[1] < rect[1] + 18
                or actual[2] > rect[2] - 18 or actual[3] > rect[3] - 18):
            raise RuntimeError(name + ": glyphs overflow padded target")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing, heading))

    measure("passage-id", (36, 20, 620, 112), "PASSAGE 1.28.2", 42, 36, True)
    measure("title", (654, 20, 2364, 112), "BRONZE DEDICATIONS", 62, 46, True)
    measure("orientation", (36, 126, 2364, 196),
            "ATHENS  |  THE ACROPOLIS  |  WAR SPOILS DEDICATED AS BRONZE", 34, 28, True)
    measure("reading-heading-1", (1430, 240, 2364, 320),
            "1  ATHENA AND THE SEA", 38, 32, True)
    measure("reading-heading-2", (36, 1490, 1220, 1560),
            "2  CHARIOT AND PORTRAITS", 38, 32, True)
    size = 46
    while True:
        try:
            for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
                fit_text_block(draw, rect, text, BODY_FONT, size, size, 18,
                               f"translation-{i+1}", .24)
            break
        except RuntimeError:
            size -= 1
            if size < 40:
                raise RuntimeError("Full English does not fit at the readable minimum")
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f"translation-{i+1}", rect, text, size, size)
    measure("interpretive-caption", (36, 2300, 2364, 2390),
            "Athena and the chariot: interpretive bronze studies. Lost forms, scale, setting and relative placement are uncertain; no distant sightline is reconstructed.", 30, 28)
    validate_fit_records(records)
    rendered = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("The complete English must remain in source order")
    report = {
        "passage_id": "1.28.2", "preflight": preflight, "canvas": [2400, 2400],
        "art_rectangles": ART_RECTS, "translation_rectangles": BODY_RECTS,
        "reading_order": "1: upper right top-to-bottom; 2: lower left top-to-bottom",
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
    for rect, filename in zip(ART_RECTS, ("athena.png", "chariot.png"), strict=True):
        with Image.open(ASSETS / filename) as source:
            art = ImageOps.fit(source.convert("RGB"),
                               (rect[2] - rect[0], rect[3] - rect[1]),
                               method=Image.Resampling.LANCZOS)
        page.paste(art, rect[:2])
        draw.rectangle(rect, outline="#8b918b", width=2)
    draw.line((36, 207, 2364, 207), fill="#b0a98c", width=2)
    draw.line((36, 2264, 1220, 2264), fill="#b0a98c", width=2)
    for xy, text, font, spacing, heading in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing,
                            fill="#283a47" if heading else "#30393a")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/28/2.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
