#!/usr/bin/env python3
"""Render Pausanias 1.25.8 with a broad hill prospect and ordered prose."""
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
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block  # noqa: E402
from graphic_book.render_passage_1_10_1 import validate_fit_records  # noqa: E402

PASSAGE_ID = "1.25.8"
ASSETS = ROOT / "graphic_book/assets/generated/1_25_8"
ART = ASSETS / "museum_hill.png"
ART_RECT = (28, 151, 1772, 1045)
TEXT_RECTS = [(28, 1116, 449, 1580), (469, 1116, 890, 1580),
              (910, 1116, 1331, 1580), (1351, 1116, 1772, 1580)]


def render(output: Path, preflight: bool = False) -> None:
    """Measure and draw all text, asserting complete SQLite fidelity."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    first, rest = passage.split("; later, ", 1)
    first += ";"
    second, rest = rest.split(". Within ", 1)
    second = "later, " + second + "."
    third, fourth = ("Within " + rest).split(". Later, ", 1)
    third += "."
    fourth = "Later, " + fourth
    chunks = [first, second, third, fourth]
    if " ".join(chunks) != passage:
        raise RuntimeError("Translation split changed SQLite text")

    page = Image.new("RGB", (1800, 1600), "#e6e9e9")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 12, name, spacing_ratio=0.17,
        )
        spacing = max(2, round(fit.font_size * 0.17))
        raw = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - raw[0], rect[1] + 12 - raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyphs overflow target rectangle")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#26323a")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 340, 72), "PASSAGE 1.25.8", 31, 26, heading=True)
    block("title", (357, 16, 1772, 72), "THE MUSEUM HILL", 43, 31, heading=True)
    block("orientation", (28, 83, 1772, 135),
          "ATHENS  ·  MUSEUM HILL  ·  ACROPOLIS  ·  PIRAEUS", 25, 20, heading=True)
    block("caption", (28, 1052, 1772, 1109),
          "The Museum hill opposite the Acropolis, with Demetrius's fortification — interpretive reconstruction.",
          24, 20)
    for i, (rect, chunk) in enumerate(zip(TEXT_RECTS, chunks), 1):
        block(f"translation-{i}", rect, chunk, 35, 30)

    validate_fit_records(records)
    if " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-")) != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_25_8_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output}")
    if not ART.exists():
        raise RuntimeError(f"Missing art: {ART}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                            method=Image.Resampling.LANCZOS), ART_RECT[:2])
    ImageDraw.Draw(page).rectangle((ART_RECT[0]-1, ART_RECT[1]-1, ART_RECT[2], ART_RECT[3]),
                                   outline="#66727a", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/25/8.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
