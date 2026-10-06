#!/usr/bin/env python3
"""Render the reviewed 1.20.2 workshop candidate to an explicit path."""
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

PASSAGE_ID = "1.20.2"
ART = ROOT / "graphic_book/assets/generated/1_20_2/workshop_revision_20261006.png"
ART_RECT = (34, 151, 1766, 1120)


def render(output: Path, preflight: bool = False) -> None:
    """Check every text rectangle against SQLite and draw the replacement."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    sentences = [part if part.endswith(".") else part + "." for part in passage.split(". ")]
    if len(sentences) != 5 or " ".join(sentences) != passage:
        raise RuntimeError("Unexpected SQLite sentence split")
    prose = (" ".join(sentences[:2]), " ".join(sentences[2:]))
    page = Image.new("RGB", (1800, 1600), "#e9e8e3")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(draw, rect, content,
            TITLE_FONT if heading else BODY_FONT, size, minimum, 12, name, spacing_ratio=0.17)
        spacing = max(2, round(fit.font_size * 0.17))
        raw = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - raw[0], rect[1] + 12 - raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 12 or actual[1] < rect[1] + 12 or
                actual[2] > rect[2] - 12 or actual[3] > rect[3] - 12):
            raise RuntimeError(f"{name}: glyphs overflow target rectangle")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#293139")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (34, 16, 403, 72), "PASSAGE 1.20.2", 31, 26, True)
    block("title", (405, 16, 1766, 72), "THE CHOICE OF EROS", 44, 32, True)
    block("orientation", (34, 82, 1766, 133),
          "ATHENS · PRAXITELES' WORKSHOP · NEARBY DIONYSUS PRECINCT", 24, 20, True)
    block("caption", (34, 1130, 1766, 1182),
          "Phryne's false alarm exposes Praxiteles' preference; the workshop arrangement is interpretive.", 23, 20)
    block("section-1", (34, 1190, 875, 1238), "THE STRATAGEM", 23, 20, True)
    block("section-2", (925, 1190, 1766, 1238), "THE CHOICE AND THE TEMPLE", 23, 20, True)
    block("translation-1", (34, 1238, 875, 1572), prose[0], 34, 29)
    block("translation-2", (925, 1238, 1766, 1572), prose[1], 34, 29)
    validate_fit_records(records)
    reconstructed = " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-"))
    if reconstructed != " ".join(passage.split()):
        raise RuntimeError("Rendered prose differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/1_20_2_replacement_layout.json").write_text(json.dumps(report, indent=2))
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
                                   outline="#685d52", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
