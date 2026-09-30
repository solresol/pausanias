#!/usr/bin/env python3
"""Render the interpreted Athena Parthenos of Pausanias 1.24.7."""
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

PASSAGE_ID = "1.24.7"
ART = ROOT / "graphic_book/assets/generated/1_24_7/athena_parthenos.png"


def render(output: Path, preflight: bool = False) -> None:
    """Measure exact source text before placing the portrait artwork."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?",
                           (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    marker = "This serpent may represent Erichthonius."
    cut = passage.index(marker) + len(marker)
    next_marker = "Here I saw also"
    cut2 = passage.index(next_marker)
    parts = [passage[:cut].strip(), passage[cut:cut2].strip(), passage[cut2:].strip()]
    if " ".join(parts) != passage:
        raise RuntimeError("Passage division changed the SQLite text")

    page = Image.new("RGB", (1800, 1600), "#efede6")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False,
              colour: str = "#29322d") -> None:
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

    block("id", (35, 16, 340, 69), "PASSAGE 1.24.7", 29, 25, heading=True)
    block("title", (342, 16, 1765, 69), "ATHENA PARTHENOS", 43, 34, heading=True)
    block("orientation", (35, 79, 1765, 126),
          "ATHENS · ACROPOLIS · THE STATUE AND ITS NEIGHBOURS", 25, 21, heading=True)
    block("heading-1", (957, 169, 1765, 224), "1 · THE STATUE", 29, 23, heading=True)
    block("translation-1", (957, 230, 1765, 710), parts[0], 34, 28)
    block("heading-2", (957, 742, 1765, 797), "2 · THE PEDESTAL", 29, 23, heading=True)
    block("translation-2", (957, 804, 1765, 1147), parts[1], 34, 28)
    block("heading-3", (957, 1176, 1765, 1231), "3 · THE OTHER STATUES", 29, 23, heading=True)
    block("translation-3", (957, 1238, 1765, 1485), parts[2], 34, 28)
    block("caption", (35, 1521, 925, 1581),
          "Interpretive reconstruction of the lost cult statue; exact details are unknown.",
          23, 20)

    validate_fit_records(records)
    actual_passage = " ".join(" ".join(r.text.split()) for r in records
                              if r.name.startswith("translation-"))
    if actual_passage != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")

    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_7_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])

    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output}")
    if not ART.exists():
        raise RuntimeError(f"Missing art: {ART}")
    rect = (35, 145, 925, 1514)
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (rect[2] - rect[0], rect[3] - rect[1]),
                            method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)), rect[:2])
    ImageDraw.Draw(page).rectangle((rect[0]-1, rect[1]-1, rect[2], rect[3]),
                                   outline="#677369", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/24/7.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
