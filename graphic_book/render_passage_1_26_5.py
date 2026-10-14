#!/usr/bin/env python3
"""Render Pausanias 1.26.5 with an architectural panorama between prose bands."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import sqlite3
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

PASSAGE_ID = "1.26.5"
ART = ROOT / "graphic_book/assets/generated/1_26_5/erechtheion_interior.png"
ART_RECT = (28, 449, 1772, 1128)


def render(output: Path, preflight: bool = False) -> None:
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing SQLite translation")
    passage = row[0]
    sentences = re.split(r"(?<=\.) (?=[A-Z])", passage)
    if len(sentences) != 6 or " ".join(sentences) != passage:
        raise RuntimeError("Sentence split changed SQLite translation")
    fifth = sentences[4]
    marker = "the inhabitants of Aphrodisias"
    cut = fifth.find(marker)
    if cut < 0:
        raise RuntimeError("Expected sentence-five clause is missing")
    chunks = [" ".join(sentences[:2]), sentences[2],
              sentences[3] + " " + fifth[:cut].rstrip(),
              fifth[cut:] + " " + sentences[5]]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation chunks do not preserve source")

    page = Image.new("RGB", (1800, 1600), "#e7e8e4")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
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
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#26353b")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 365, 67), "PASSAGE 1.26.5", 30, 25, heading=True)
    block("title", (390, 16, 1772, 67), "THE ERECHTHEION: SIGNS OF POSEIDON", 43, 30, heading=True)
    block("orientation", (28, 79, 1772, 129),
          "ATHENS  |  THE ACROPOLIS  |  ALTARS, A SEAWATER WELL AND A TRIDENT MARK",
          25, 20, heading=True)
    text_rects = [(28, 154, 865, 421), (935, 154, 1772, 421),
                  (28, 1190, 865, 1560), (935, 1190, 1772, 1560)]
    for index, (rect, chunk) in enumerate(zip(text_rects, chunks), 1):
        block(f"translation-{index}", rect, chunk, 38, 30)
    block("caption", (28, 1133, 1772, 1182),
          "The Erechtheion interior — interpretive view of the features described by Pausanias.",
          23, 19)
    validate_fit_records(records)
    rendered = " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-"))
    if rendered != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "translation_characters": len(passage),
              "text_blocks_checked": len(records), "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_26_5_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                            method=Image.Resampling.LANCZOS), ART_RECT[:2])
    draw.rectangle((ART_RECT[0]-1, ART_RECT[1]-1, ART_RECT[2], ART_RECT[3]),
                   outline="#738989", width=2)
    draw.line((900, 154, 900, 421), fill="#b8c3c2", width=2)
    draw.line((900, 1190, 900, 1560), fill="#b8c3c2", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/26/5.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
