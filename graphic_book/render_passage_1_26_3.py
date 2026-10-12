#!/usr/bin/env python3
"""Render Pausanias 1.26.3 as ordered prose over an Eleusinian panorama."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

PASSAGE_ID = "1.26.3"
ART = ROOT / "graphic_book/assets/generated/1_26_3/eleusis_defenders.png"
ART_RECT = (28, 777, 1772, 1531)
TEXT_RECTS = [(28, 207, 440, 730), (472, 207, 884, 730),
              (916, 207, 1328, 730), (1360, 207, 1772, 730)]
HEADING_RECTS = [(x, 151, x + 412, 200) for x in (28, 472, 916, 1360)]


def render(output: Path, preflight: bool = False) -> None:
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing SQLite translation")
    passage = row[0]
    sentences = passage.split(". ")
    chunks = [s + ("." if i < len(sentences) - 1 else "") for i, s in enumerate(sentences)]
    if len(chunks) != 4 or " ".join(chunks) != passage:
        raise RuntimeError("Sentence split changed SQLite translation")

    page = Image.new("RGB", (1800, 1600), "#e8e9e5")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=0.17)
        spacing = max(2, round(fit.font_size * 0.17))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - bbox[0], rect[1] + 12 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyph overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#26343a")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 346, 68), "PASSAGE 1.26.3", 30, 25, heading=True)
    block("title", (366, 16, 1772, 68), "OLYMPIODORUS AT ELEUSIS", 43, 31, heading=True)
    block("orientation", (28, 82, 1772, 134),
          "ELEUSIS · WESTERN ATTICA  |  AETOLIA · ATHENS · ELATEIA · DELPHI",
          25, 20, heading=True)
    headings = ["1  ELEUSIS", "2  AETOLIAN AID", "3  ATHENIAN HONORS", "4  DELPHI"]
    for i, (heading, hrect, rect, chunk) in enumerate(zip(headings, HEADING_RECTS, TEXT_RECTS, chunks), 1):
        block(f"heading-{i}", hrect, heading, 25, 20, heading=True)
        block(f"translation-{i}", rect, chunk, 38, 30)
    block("caption", (28, 1535, 1772, 1585),
          "Eleusis and the Macedonian incursion — interpretive historical scene.", 24, 20)
    validate_fit_records(records)
    rendered = " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-"))
    if rendered != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "translation_characters": len(passage),
              "text_blocks_checked": len(records), "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_26_3_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                            method=Image.Resampling.LANCZOS), ART_RECT[:2])
    draw.rectangle((ART_RECT[0]-1, ART_RECT[1]-1, ART_RECT[2], ART_RECT[3]),
                   outline="#667570", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/26/3.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
