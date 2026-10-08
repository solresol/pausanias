#!/usr/bin/env python3
"""Render Pausanias 1.25.7 as two illustrated leaves around ordered prose."""
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

PASSAGE_ID = "1.25.7"
ASSETS = ROOT / "graphic_book/assets/generated/1_25_7"
ART = ((ASSETS / "athena_sanctuary.png", (28, 147, 565, 1518)),
       (ASSETS / "athens_walls.png", (1235, 147, 1772, 1518)))


def render(output: Path, preflight: bool = False) -> None:
    """Measure every string, assert SQLite fidelity, and compose the page."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    sentences = [part if part.endswith(".") else part + "." for part in passage.split(". ")]
    if len(sentences) != 4 or " ".join(sentences) != passage:
        raise RuntimeError("Unexpected SQLite sentence split")

    page = Image.new("RGB", (1800, 1600), "#e9e8e3")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False,
              colour: str = "#26323a") -> None:
        font, wrapped, _, fit = fit_text_block(
            draw, rect, content, TITLE_FONT if heading else BODY_FONT,
            size, minimum, 12, name, spacing_ratio=0.17,
        )
        spacing = max(2, round(fit.font_size * 0.17))
        raw = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - raw[0], rect[1] + 12 - raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyphs overflow target rectangle")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill=colour)
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (28, 16, 335, 72), "PASSAGE 1.25.7", 31, 26, heading=True)
    block("title", (350, 16, 1772, 72), "LACHARES AND ATHENA'S ADORNMENTS", 43, 31, heading=True)
    block("orientation", (28, 82, 1772, 132),
          "ATHENS  ·  ACROPOLIS  ·  CITY WALLS  ·  BOEOTIA", 25, 20, heading=True)
    block("central-heading", (588, 150, 1212, 205), "TYRANNY AND FLIGHT", 27, 22, heading=True)
    block("translation-1", (588, 212, 1212, 730), sentences[0], 36, 30)
    block("translation-2", (588, 744, 1212, 1035), sentences[1], 36, 30)
    block("translation-3", (588, 1048, 1212, 1208), sentences[2], 36, 30)
    block("translation-4", (588, 1221, 1212, 1548), sentences[3], 36, 30)
    block("left-caption", (28, 1528, 565, 1586),
          "Athena's stripped image — interpretive view.", 23, 19)
    block("right-caption", (1235, 1528, 1772, 1586),
          "Athens's walls — interpretive view.", 23, 19)

    validate_fit_records(records)
    actual_passage = " ".join(" ".join(r.text.split()) for r in records
                              if r.name.startswith("translation-"))
    if actual_passage != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_25_7_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output}")
    for source, rect in ART:
        if not source.exists():
            raise RuntimeError(f"Missing art: {source}")
        art = Image.open(source).convert("RGB")
        page.paste(ImageOps.fit(art, (rect[2]-rect[0], rect[3]-rect[1]),
                                method=Image.Resampling.LANCZOS), rect[:2])
        ImageDraw.Draw(page).rectangle((rect[0]-1, rect[1]-1, rect[2], rect[3]),
                                       outline="#58626a", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/25/7.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
