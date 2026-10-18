#!/usr/bin/env python3
"""Render Pausanias 1.27.1 with measured text and an object-rich temple study."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphic_book_corpus import load_translation
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

PASSAGE_ID = "1.27.1"
ART = ROOT / "graphic_book/assets/generated/1_27_1/polias_offerings.png"
ART_RECT = (28, 590, 1200, 1564)
TEXT_RECTS = ((28, 173, 870, 563), (930, 173, 1772, 563), (1230, 590, 1772, 1564))


def render(output: Path, preflight: bool = False) -> None:
    passage = load_translation(PASSAGE_ID)
    markers = ("Among spoils taken", "I know that Masistius")
    positions = [passage.find(marker) for marker in markers]
    if positions[0] <= 0 or positions[1] <= positions[0]:
        raise RuntimeError("Translation split markers missing or out of order")
    chunks = [passage[:positions[0]].rstrip(), passage[positions[0]:positions[1]].rstrip(), passage[positions[1]:]]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation chunks do not preserve exported text")

    page = Image.new("RGB", (1800, 1600), "#e9e8e3")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              maximum: int, minimum: int, *, heading: bool = False, ink: str = "#25313a") -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=0.16)
        spacing = max(2, round(fit.font_size * 0.16))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - bbox[0], rect[1] + 12 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyph overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill=ink)
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 377, 72), "PASSAGE 1.27.1", 30, 25, heading=True)
    block("title", (399, 16, 1772, 72), "OFFERINGS IN ATHENA POLIAS'S TEMPLE", 41, 30, heading=True)
    block("orientation", (28, 87, 1772, 151),
          "ATHENS  |  THE ACROPOLIS  |  ANCIENT DEDICATIONS AND PERSIAN SPOILS", 25, 20, heading=True)
    for index, (rect, chunk) in enumerate(zip(TEXT_RECTS, chunks), 1):
        block(f"translation-{index}", rect, chunk, 42, 30)
    validate_fit_records(records)
    rendered = " ".join(r.text for r in records if r.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from exported text")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_export": True, "translation_characters": len(passage),
              "text_blocks_checked": len(records), "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_27_1_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                            method=Image.Resampling.LANCZOS), ART_RECT[:2])
    draw.rectangle((ART_RECT[0] - 1, ART_RECT[1] - 1, ART_RECT[2], ART_RECT[3]),
                   outline="#6a7471", width=2)
    draw.line((899, 173, 899, 563), fill="#b6bcb9", width=2)
    draw.line((28, 576, 1772, 576), fill="#b6bcb9", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/27/1.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
