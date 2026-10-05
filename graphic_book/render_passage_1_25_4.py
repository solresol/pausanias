#!/usr/bin/env python3
"""Render Pausanias 1.25.4 as a Boeotian landscape and paired prose."""
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

PASSAGE_ID = "1.25.4"
ART = ROOT / "graphic_book/assets/generated/1_25_4/boeotian_plain.png"
ART_RECT = (34, 155, 1766, 1080)


def render(output: Path, preflight: bool = False) -> None:
    """Measure every text item and preserve the complete SQLite translation."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    sentences = [part if part.endswith(".") else part + "." for part in passage.split(". ")]
    if len(sentences) != 3 or " ".join(sentences) != passage:
        raise RuntimeError("Unexpected sentence split or changed SQLite translation")
    prose = (" ".join(sentences[:2]), sentences[2])

    page = Image.new("RGB", (1800, 1600), "#e9eeed")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False,
              colour: str = "#23343a") -> None:
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

    block("id", (34, 16, 405, 72), "PASSAGE 1.25.4", 31, 26, heading=True)
    block("title", (410, 16, 1766, 72), "THE ALLIANCE AND BOEOTIA", 43, 31, heading=True)
    block("orientation", (34, 82, 1766, 140),
          "PELOPONNESE · ISTHMUS OF CORINTH · BOEOTIA   /   AFTER ALEXANDER",
          25, 20, heading=True)
    block("caption", (34, 1092, 1766, 1143),
          "The former Theban territory in Boeotia, shown as an interpretive landscape; the alliance extended far beyond this view.",
          24, 20)
    block("group-1", (34, 1157, 875, 1199), "THE ALLIED COMMUNITIES", 23, 20, heading=True)
    block("group-2", (925, 1157, 1766, 1199), "THE BOEOTIAN EXCEPTION", 23, 20, heading=True)
    block("translation-1", (34, 1201, 875, 1575), prose[0], 34, 29)
    block("translation-2", (925, 1201, 1766, 1575), prose[1], 34, 29)

    validate_fit_records(records)
    actual_passage = " ".join(" ".join(r.text.split()) for r in records
                              if r.name.startswith("translation-"))
    if actual_passage != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_25_4_layout_report.json").write_text(json.dumps(report, indent=2))
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
                                   outline="#58767a", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/25/4.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
