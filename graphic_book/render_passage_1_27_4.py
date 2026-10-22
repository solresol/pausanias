#!/usr/bin/env python3
"""Render two interpretive sculpture studies from the exact exported passage."""
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

PASSAGE_ID = "1.27.4"
ASSETS = ROOT / "graphic_book/assets/generated/1_27_4"
ART_PANELS = ((ASSETS / "handmaid_study.png", (28, 164, 574, 1108)),
              (ASSETS / "opposing_bronzes.png", (620, 164, 1772, 1108)))
TEXT_RECTS = ((28, 1254, 574, 1568), (620, 1254, 1772, 1568))


def render(output: Path, preflight: bool = False) -> None:
    """Measure every text block before loading or saving any illustrated page."""
    snapshot_path()
    passage = load_translation(PASSAGE_ID)
    position = passage.index("There are also")
    chunks = [passage[:position].rstrip(), passage[position:]]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation split does not preserve the exact export")
    page = Image.new("RGB", (1800, 1600), "#ebe7e2")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    for body_size in range(44, 35, -1):
        try:
            for text, rect in zip(chunks, TEXT_RECTS):
                fit_text_block(draw, rect, text, BODY_FONT, body_size, body_size, 12, "preflight", .16)
        except RuntimeError:
            continue
        break
    else:
        raise RuntimeError("Full passage cannot fit at a readable minimum size")

    def block(name: str, rect: tuple[int, int, int, int], text: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=.16)
        spacing = max(2, round(fit.font_size * .16))
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - bounds[0], rect[1] + 12 - bounds[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyphs overflow the padded rectangle")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#302c32")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("passage-id", (28, 18, 385, 82), "PASSAGE 1.27.4", 31, 27, heading=True)
    block("title", (409, 18, 1772, 82), "SMALL IMAGE, BRONZE OPPONENTS", 41, 32, heading=True)
    block("orientation", (28, 98, 1772, 150),
          "ATHENS  |  THE ACROPOLIS  |  NEAR THE TEMPLE OF ATHENA", 26, 22, heading=True)
    block("handmaid-caption", (28, 1120, 574, 1173), "Small image — interpretive study.", 24, 21)
    block("bronzes-caption", (620, 1120, 1772, 1173),
          "Interpretive bronzes; names and inherited tradition are distinguished below.", 24, 21)
    for index, (heading, rect, chunk) in enumerate(zip(
            ("1  THE HANDMAID", "2  THE OPPONENTS AND THE TRADITION"), TEXT_RECTS, chunks), 1):
        block(f"section-{index}", (rect[0], 1200, rect[2], 1248), heading, 26, 22, heading=True)
        block(f"translation-{index}", rect, chunk, body_size, body_size)
    validate_fit_records(records)
    rendered = " ".join(record.text for record in records if record.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered passage is incomplete or out of source order")
    ASSETS.mkdir(parents=True, exist_ok=True)
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_characters": len(passage), "translation_matches_export": True,
              "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
              "body_font_size": body_size, "padding": 12, "canvas": [1800, 1600],
              "reading_order": "numbered lower fields, left then right",
              "text_blocks_checked": len(records), "fit_records": [asdict(record) for record in records]}
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite {output}")
    for path, rect in ART_PANELS:
        with Image.open(path) as source:
            art = ImageOps.fit(source.convert("RGB"), (rect[2] - rect[0], rect[3] - rect[1]),
                               method=Image.Resampling.LANCZOS)
        page.paste(art, rect[:2])
        draw.rectangle((rect[0] - 1, rect[1] - 1, rect[2], rect[3]), outline="#77716e", width=2)
    draw.line((28, 154, 1772, 154), fill="#aba29f", width=2)
    draw.line((28, 1189, 1772, 1189), fill="#b5a8a1", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/4.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
