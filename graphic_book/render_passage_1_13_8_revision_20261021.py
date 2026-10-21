#!/usr/bin/env python3
"""Render a reviewed replacement candidate without touching the canonical page."""
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

PASSAGE_ID = "1.13.8"
REVISION = "20261021T075600Z"
ASSETS = ROOT / "graphic_book/assets/generated/1_13_8/revisions" / REVISION
ART = ASSETS / "street_scene.png"
ART_RECT = (28, 630, 1772, 1516)
TEXT_RECTS = ((28, 225, 576, 602), (626, 225, 1174, 602), (1224, 225, 1772, 602))
DEFAULT_OUTPUT = ROOT / "graphic_book/output/replacements/1_13_8" / REVISION / "candidate.png"


def render(output: Path, preflight: bool = False) -> None:
    """Measure the complete passage and all labels before loading the art."""
    snapshot_path()
    passage = load_translation(PASSAGE_ID)
    markers = ("They say Pyrrhus died", "The Argives themselves")
    positions = [0] + [passage.index(marker) for marker in markers] + [len(passage)]
    if positions != sorted(set(positions)):
        raise RuntimeError("Translation markers are out of order")
    chunks = [passage[positions[i]:positions[i + 1]].rstrip() for i in range(3)]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation chunks differ from the exact export")
    page = Image.new("RGB", (1800, 1600), "#eae7e2")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    for body_size in range(42, 33, -1):
        try:
            for chunk, rect in zip(chunks, TEXT_RECTS):
                fit_text_block(draw, rect, chunk, BODY_FONT, body_size, body_size, 12, "preflight", .16)
        except RuntimeError:
            continue
        break
    else:
        raise RuntimeError("Full translation cannot fit at a readable minimum size")

    def block(name: str, rect: tuple[int, int, int, int], text: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=.16)
        spacing = max(2, round(fit.font_size * .16))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - bbox[0], rect[1] + 12 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyph overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#302c36")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("passage-id", (28, 18, 387, 83), "PASSAGE 1.13.8", 31, 27, heading=True)
    block("title", (411, 18, 1772, 83), "PYRRHUS IN THE STREETS OF ARGOS", 39, 31, heading=True)
    block("orientation", (28, 100, 1772, 151),
          "ARGOS  |  PYRRHUS'S DEATH  |  LOCAL TRADITION AND THE SANCTUARY OF DEMETER", 25, 20, heading=True)
    headings = ("1  THE ISOLATED KING", "2  THE TWO ACCOUNTS", "3  LOCAL MEMORY")
    for index, (rect, heading, chunk) in enumerate(zip(TEXT_RECTS, headings, chunks), 1):
        block(f"section-{index}", (rect[0], 175, rect[2], 219), heading, 25, 21, heading=True)
        block(f"translation-{index}", rect, chunk, body_size, body_size)
    block("interpretive-caption", (28, 1532, 1772, 1585),
          "Interpretive view of the reported roof-tile episode; the identification with Demeter is an Argive tradition.", 24, 20)
    validate_fit_records(records)
    rendered = " ".join(record.text for record in records if record.name.startswith("translation-"))
    if " ".join(rendered.split()) != " ".join(passage.split()):
        raise RuntimeError("Rendered translation is incomplete or out of order")
    ASSETS.mkdir(parents=True, exist_ok=True)
    report = {"passage_id": PASSAGE_ID, "revision": REVISION, "preflight": preflight,
              "translation_characters": len(passage), "translation_matches_export": True,
              "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
              "body_font_size": body_size, "padding": 12, "canvas": [1800, 1600],
              "reading_order": "three numbered upper prose fields, left to right",
              "text_blocks_checked": len(records), "fit_records": [asdict(record) for record in records]}
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    if preflight:
        return
    if output.resolve() == (ROOT / "graphic_book/images/1/13/8.png").resolve():
        raise RuntimeError("Replacement renderer must not overwrite the canonical original")
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    with Image.open(ART) as source:
        art = ImageOps.fit(source.convert("RGB"), (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle((ART_RECT[0] - 1, ART_RECT[1] - 1, ART_RECT[2], ART_RECT[3]), outline="#76727c", width=2)
    draw.line((28, 157, 1772, 157), fill="#b2abb4", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved candidate", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.output, args.preflight)
