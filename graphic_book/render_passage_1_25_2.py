#!/usr/bin/env python3
"""Render Pausanias 1.25.2 with ordered prose above a sculpture terrace."""
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

PASSAGE_ID = "1.25.2"
ART = ROOT / "graphic_book/assets/generated/1_25_2/south_wall_sculptures.png"


def render(output: Path, preflight: bool = False) -> None:
    """Measure each text rectangle and draw the complete translation."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?",
                           (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    cut = passage.index("There also stands")
    parts = [passage[:cut].strip(), passage[cut:].strip()]
    if " ".join(parts) != passage:
        raise RuntimeError("Passage division changed SQLite text")

    page = Image.new("RGB", (1800, 1600), "#e8e8e3")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False,
              colour: str = "#273137") -> None:
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

    block("id", (34, 18, 430, 72), "PASSAGE 1.25.2", 31, 26, heading=True)
    block("title", (444, 18, 1766, 72), "ATTALUS AND OLYMPIODORUS", 43, 31, heading=True)
    block("orientation", (34, 83, 1766, 137),
          "ATHENS · ACROPOLIS   /   THE SOUTH WALL AND ITS DEDICATIONS",
          26, 22, heading=True)
    block("attalus-heading", (34, 147, 1050, 187), "ATTALUS'S DEDICATION", 27, 22, heading=True)
    block("olympiodorus-heading", (1080, 147, 1766, 187), "OLYMPIODORUS", 27, 22, heading=True)
    block("translation-1", (34, 191, 1050, 535), parts[0], 39, 30)
    block("translation-2", (1080, 191, 1766, 535), parts[1], 39, 30)
    block("caption", (34, 1506, 1766, 1578),
          "Interpretive view of lost bronze dedications; their precise forms and positions are unknown.",
          25, 20)

    validate_fit_records(records)
    actual_passage = " ".join(" ".join(r.text.split()) for r in records
                              if r.name.startswith("translation-"))
    if actual_passage != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_25_2_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output}")
    if not ART.exists():
        raise RuntimeError(f"Missing art: {ART}")
    rect = (34, 570, 1766, 1492)
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (rect[2]-rect[0], rect[3]-rect[1]),
                            method=Image.Resampling.LANCZOS), rect[:2])
    ImageDraw.Draw(page).rectangle((rect[0]-1, rect[1]-1, rect[2], rect[3]),
                                   outline="#627077", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/25/2.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
