#!/usr/bin/env python3
"""Render Pausanias 1.25.3 around a Chaeronea landscape."""
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

PASSAGE_ID = "1.25.3"
ART = ROOT / "graphic_book/assets/generated/1_25_3/chaeronea_panorama.png"


def render(output: Path, preflight: bool = False) -> None:
    """Measure and draw all text, checking verbatim passage and glyph bounds."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    sentences = [s.strip() for s in passage.split(". ")]
    sentences = [s if s.endswith(".") else s + "." for s in sentences]
    if len(sentences) != 5 or " ".join(sentences) != passage:
        raise RuntimeError("Unexpected sentence split or changed SQLite text")

    page = Image.new("RGB", (1800, 1600), "#e8e9e8")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False,
              colour: str = "#25333a") -> None:
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

    block("id", (34, 17, 415, 69), "PASSAGE 1.25.3", 31, 26, heading=True)
    block("title", (427, 17, 1766, 69), "FROM CHAERONEA TO RESISTANCE", 42, 31, heading=True)
    block("orientation", (34, 79, 1766, 131),
          "BOEOTIA · ATHENS   /   MACEDONIAN DOMINION AND THE ATHENIAN RESPONSE",
          24, 21, heading=True)
    top = [(34, 174, 870, 415), (920, 174, 1766, 415)]
    bottom = [(34, 1230, 576, 1575), (629, 1230, 1171, 1575),
              (1224, 1230, 1766, 1575)]
    for i, rect in enumerate(top + bottom):
        block(f"translation-{i+1}", rect, sentences[i], 34, 29)
    block("caption", (34, 1162, 1766, 1219),
          "Chaeronea marks the defeat; the later Athenian decision belongs to the years after Alexander's death.",
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
    (ROOT / "tmp/passage_1_25_3_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output}")
    if not ART.exists():
        raise RuntimeError(f"Missing art: {ART}")
    rect = (34, 403, 1766, 1150)
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art, (rect[2]-rect[0], rect[3]-rect[1]),
                            method=Image.Resampling.LANCZOS), rect[:2])
    ImageDraw.Draw(page).rectangle((rect[0]-1, rect[1]-1, rect[2], rect[3]),
                                   outline="#68757b", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/25/3.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
