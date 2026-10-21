#!/usr/bin/env python3
"""Render the Arrephoroi's nocturnal descent around one vertical illustration."""
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

PASSAGE_ID = "1.27.3"
ASSETS = ROOT / "graphic_book/assets/generated/1_27_3"
ART = ASSETS / "arrephoroi_descent.png"
ART_RECT = (528, 175, 1472, 1670)
TEXT_RECTS = ((28, 225, 490, 835), (28, 925, 490, 1750),
              (1510, 225, 1972, 920), (1510, 1010, 1972, 1750))
HEAD_RECTS = ((28, 175, 490, 219), (28, 875, 490, 919),
              (1510, 175, 1972, 219), (1510, 960, 1972, 1004))
HEADINGS = ("1  THE ATTENDANTS", "2  THE NIGHT RITE", "3  THE DESCENT", "4  THE RETURN")


def render(output: Path, preflight: bool = False) -> None:
    """Fail before saving if any text escapes its measured padded rectangle."""
    snapshot_path()
    passage = load_translation(PASSAGE_ID)
    markers = ("They remain for a certain period", "Within the city", "Below they leave")
    positions = [0] + [passage.index(marker) for marker in markers] + [len(passage)]
    if positions != sorted(set(positions)):
        raise RuntimeError("Translation split markers missing or out of order")
    chunks = [passage[positions[i]:positions[i + 1]].rstrip() for i in range(4)]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation chunks do not preserve the exact exported text")

    page = Image.new("RGB", (2000, 1800), "#eae8df")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    for body_size in range(42, 35, -1):
        try:
            for text, rect in zip(chunks, TEXT_RECTS):
                fit_text_block(draw, rect, text, BODY_FONT, body_size, body_size, 14, "preflight", .17)
        except RuntimeError:
            continue
        break
    else:
        raise RuntimeError("Complete passage cannot fit at the minimum readable body size")

    def block(name: str, rect: tuple[int, int, int, int], text: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 14, name, spacing_ratio=.17)
        spacing = max(2, round(fit.font_size * .17))
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 14 - bounds[0], rect[1] + 14 - bounds[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 14 or actual[1] < rect[1] + 14 or
                actual[2] > rect[2] - 14 or actual[3] > rect[3] - 14):
            raise RuntimeError(f"{name}: glyphs overflow the padded rectangle")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#253139")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("passage-id", (28, 18, 454, 88), "PASSAGE 1.27.3", 35, 29, heading=True)
    block("title", (492, 18, 1972, 88), "THE ARREPHOROI: A NIGHT DESCENT", 46, 35, heading=True)
    block("orientation", (28, 101, 1972, 154),
          "ATHENS  |  THE ACROPOLIS  |  APHRODITE IN THE GARDENS", 27, 23, heading=True)
    for index, (heading, head_rect, rect, chunk) in enumerate(zip(HEADINGS, HEAD_RECTS, TEXT_RECTS, chunks), 1):
        block(f"section-{index}", head_rect, heading, 26, 22, heading=True)
        block(f"translation-{index}", rect, chunk, body_size, body_size)
    block("interpretation-caption", (528, 1684, 1472, 1750),
          "Interpretive nocturne; the sacred contents remain concealed.", 25, 21)
    validate_fit_records(records)
    rendered = " ".join(record.text for record in records if record.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from the exported translation")
    ASSETS.mkdir(parents=True, exist_ok=True)
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_characters": len(passage), "translation_matches_export": True,
              "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
              "body_font_size": body_size, "padding": 14, "canvas": [2000, 1800],
              "reading_order": "upper left, lower left, upper right, lower right (numbered 1–4)",
              "text_blocks_checked": len(records), "fit_records": [asdict(record) for record in records]}
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite {output}")
    with Image.open(ART) as source:
        art = ImageOps.fit(source.convert("RGB"), (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((ART_RECT[0] - 1, ART_RECT[1] - 1, ART_RECT[2], ART_RECT[3]),
                   outline="#6f797a", width=2)
    draw.line((28, 158, 1972, 158), fill="#9ca7a6", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/3.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
