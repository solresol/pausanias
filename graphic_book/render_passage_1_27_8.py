#!/usr/bin/env python3
"""Typeset the Theseus tokens passage around an interpretive bronze study."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_27_8"
ART_RECT = (36, 340, 1964, 1250)
BODY_RECTS = ((36, 190, 1964, 320), (36, 1300, 1964, 1710))


def render(output: Path, preflight: bool = False) -> None:
    """Measure all text before accessing art; refuse overflow or overwritten art."""
    snapshot_path()
    passage = load_translation("1.27.8")
    split = " The one following it is"
    start, separator, end = passage.partition(split)
    if not separator:
        raise RuntimeError("Expected exported sentence boundary missing")
    chunks = (start, separator[1:] + end)
    if " ".join(chunks) != passage:
        raise RuntimeError("Exact translation split must preserve every character")
    page = Image.new("RGB", (2000, 1800), "#eeeee7")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 16, name, .22,
        )
        spacing = max(2, round(fit.font_size * .22))
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 16 - bounds[0], rect[1] + 16 - bounds[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 16 or actual[1] < rect[1] + 16
                or actual[2] > rect[2] - 16 or actual[3] > rect[3] - 16):
            raise RuntimeError(name + ": glyph overflow inside padding")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure("passage-id", (36, 18, 476, 102), "PASSAGE 1.27.8", 38, 32, True)
    measure("title", (510, 18, 1964, 102), "THESEUS AND THE HIDDEN TOKENS", 48, 36, True)
    measure("orientation", (36, 108, 1964, 170),
            "ATHENS, THE ACROPOLIS  |  A BRONZE REPRESENTATION OF THE TROIZENIAN STORY", 29, 25, True)
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f"translation-{i+1}", rect, text, 46, 40)
    measure("interpretive-caption", (36, 1720, 1964, 1790),
            "Interpretive study: bronze figure and tokens, natural stone rock. The lost design and original placement are uncertain.", 27, 24)
    validate_fit_records(records)
    rendered_passage = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(rendered_passage.split()) != " ".join(passage.split()):
        raise RuntimeError("The complete exported English must remain in source order")
    report = {
        "passage_id": "1.27.8", "preflight": preflight, "canvas": [2000, 1800],
        "art_rectangle": ART_RECT, "translation_rectangles": BODY_RECTS,
        "reading_order": "upper introductory sentence, then continuous lower continuation",
        "translation_characters": len(passage), "translation_exact": passage,
        "translation_chunks": chunks,
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 40,
        "padding": 16, "text_blocks_checked": len(records),
        "fit_records": [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("fit_records", "translation_exact", "translation_chunks")}))
    print("Body fonts:", [r.font_size for r in records if r.name.startswith("translation-")])
    if preflight:
        return
    if output.exists():
        raise RuntimeError("Refusing to overwrite " + str(output))
    with Image.open(ASSETS / "theseus_bronze_tokens.png") as source:
        art = ImageOps.fit(source.convert("RGB"), (1928, 910),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((35, 339, 1964, 1250), outline="#7c8583", width=2)
    draw.line((36, 173, 1964, 173), fill="#a3adaa", width=2)
    draw.line((36, 1280, 1964, 1280), fill="#a3adaa", width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill="#293433")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/8.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
