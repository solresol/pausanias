#!/usr/bin/env python3
"""Render the Parthenon pediments and Athena's helmet at Pausanias 1.24.5."""
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

PASSAGE_ID = "1.24.5"
ASSETS = ROOT / "graphic_book/assets/generated/1_24_5"
PEDIMENT = ASSETS / "east_pediment_draped.png"
ATHENA = ASSETS / "athena_helmet_draped.png"


def render(output: Path, preflight: bool = False) -> None:
    """Measure all exact text before placing art or saving the page."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?",
                           (PASSAGE_ID,)).fetchone()
    if not row:
        raise RuntimeError(f"Missing {PASSAGE_ID} translation")
    passage = row[0]
    marker = "The statue itself is made from ivory and gold."
    cut = passage.index(marker) + len(marker)
    parts = [passage[:cut].strip(), passage[cut:].strip()]
    if " ".join(parts) != passage:
        raise RuntimeError("Passage division is not verbatim")

    page = Image.new("RGB", (1800, 1600), "#eeece5")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False) -> None:
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
            raise RuntimeError(f"{name}: glyphs overflow target")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#27313a")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))

    block("id", (24, 16, 370, 76), "PASSAGE 1.24.5", 31, 27, heading=True)
    block("title", (380, 16, 1776, 76), "THE PEDIMENTS AND ATHENA'S HELMET", 39, 30, heading=True)
    block("orientation", (24, 79, 1776, 128), "ATHENS · THE ACROPOLIS · THE PARTHENON", 26, 23, heading=True)
    block("heading-1", (24, 153, 610, 204), "1 · THE PEDIMENTS", 29, 25, heading=True)
    block("translation-1", (24, 212, 610, 678), parts[0], 36, 30)
    block("note-1", (24, 680, 610, 731), "East: Athena's birth. West: Athena and Poseidon.", 25, 22)
    block("caption-1", (640, 742, 1776, 800),
          "East facade of the Parthenon; an interpretive view of the lost pediment sculpture.", 24, 22)
    block("caption-2", (24, 1510, 1160, 1568),
          "An imagined detail of Athena's gold-and-ivory helmet, with Sphinx and griffins.", 24, 22)
    block("heading-2", (1190, 816, 1776, 866), "2 · THE STATUE AND HELMET", 29, 25, heading=True)
    block("translation-2", (1190, 874, 1776, 1462), parts[1], 36, 30)
    block("footer", (1190, 1470, 1776, 1568),
          "The original cult statue is lost; this detail is interpretive, not a surviving object.", 24, 22)

    validate_fit_records(records)
    reconstructed = " ".join(" ".join(r.text.split()) for r in records
                             if r.name.startswith("translation-"))
    if reconstructed != " ".join(passage.split()):
        raise RuntimeError("Rendered translation differs from SQLite")

    if not preflight:
        for path in (PEDIMENT, ATHENA):
            if not path.exists():
                raise RuntimeError(f"Missing art: {path}")
        for path, rect, center in ((PEDIMENT, (640, 145, 1776, 735), (0.5, 0.52)),
                                   (ATHENA, (24, 805, 1160, 1504), (0.5, 0.0))):
            art = Image.open(path).convert("RGB")
            page.paste(ImageOps.fit(art, (rect[2]-rect[0], rect[3]-rect[1]),
                                    method=Image.Resampling.LANCZOS, centering=center), rect[:2])
            ImageDraw.Draw(page).rectangle((rect[0]-1, rect[1]-1, rect[2], rect[3]),
                                           outline="#777467", width=2)

    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_5_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])
    if not preflight:
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite existing output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/24/5.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
