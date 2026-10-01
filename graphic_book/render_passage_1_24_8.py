#!/usr/bin/env python3
"""Render Pausanias 1.24.8 with distinct Athens and Sipylus scenes."""
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

PASSAGE_ID = "1.24.8"
ART_DIR = ROOT / "graphic_book/assets/generated/1_24_8"
APOLLO_ART = ART_DIR / "apollo_bronze_athens_v2.png"
SIPYLUS_ART = ART_DIR / "sipylus_locust_weather.png"


def render(output: Path, preflight: bool = False) -> None:
    """Measure all local type and assert exact source order before artwork."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?",
                           (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for {PASSAGE_ID}")
    passage = row[0]
    cuts = [passage.index("I myself know"), passage.index("another time"),
            passage.index("and finally")]
    parts = [passage[:cuts[0]].strip(), passage[cuts[0]:cuts[1]].strip(),
             passage[cuts[1]:cuts[2]].strip(), passage[cuts[2]:].strip()]
    if " ".join(parts) != passage:
        raise RuntimeError("Passage division changed the SQLite text")

    page = Image.new("RGB", (1800, 1600), "#e9e8e0")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    def block(name: str, rect: tuple[int, int, int, int], content: str,
              size: int, minimum: int, *, heading: bool = False,
              colour: str = "#273136") -> None:
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

    block("id", (34, 18, 376, 72), "PASSAGE 1.24.8", 31, 26, heading=True)
    block("title", (385, 18, 1766, 72), "APOLLO PARNOPIUS AND THE LOCUSTS", 42, 31, heading=True)
    block("orientation", (34, 81, 1766, 129),
          "ATHENS: BRONZE APOLLO   ·   MOUNT SIPYLUS: THREE REPORTED CAUSES",
          25, 21, heading=True)
    block("athens-heading", (1047, 164, 1766, 219), "1 · THE BRONZE APOLLO", 30, 24, heading=True)
    block("translation-1", (1047, 224, 1766, 726), parts[0], 35, 29)
    block("athens-caption", (42, 748, 1016, 794),
          "Interpretive view of the lost bronze statue near the temple.", 24, 21)
    block("sipylus-heading", (42, 1237, 1760, 1283),
          "2 · PAUSANIAS'S THREE ACCOUNTS FROM MOUNT SIPYLUS", 27, 22, heading=True)
    block("translation-2", (42, 1290, 592, 1548), parts[1], 34, 28)
    block("translation-3", (625, 1290, 1175, 1548), parts[2], 34, 28)
    block("translation-4", (1208, 1290, 1758, 1548), parts[3], 34, 28)
    block("sipylus-caption", (42, 1551, 1758, 1594),
          "Sipylus is a separate location; wind, heat and cold are reported explanations, not simultaneous events.",
          22, 20)

    validate_fit_records(records)
    actual_passage = " ".join(" ".join(r.text.split()) for r in records
                              if r.name.startswith("translation-"))
    if actual_passage != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")
    report = {"passage_id": PASSAGE_ID, "preflight": preflight,
              "translation_matches_sqlite": True, "text_blocks_checked": len(records),
              "fit_records": [asdict(r) for r in records]}
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_24_8_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit_records"}))
    print("Font sizes:", [(r.name, r.font_size) for r in records])

    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output}")
    for art_path, rect in [(APOLLO_ART, (34, 151, 1020, 741)),
                           (SIPYLUS_ART, (34, 807, 1766, 1230))]:
        if not art_path.exists():
            raise RuntimeError(f"Missing art: {art_path}")
        art = Image.open(art_path).convert("RGB")
        page.paste(ImageOps.fit(art, (rect[2] - rect[0], rect[3] - rect[1]),
                                method=Image.Resampling.LANCZOS), rect[:2])
        ImageDraw.Draw(page).rectangle((rect[0]-1, rect[1]-1, rect[2], rect[3]),
                                       outline="#657078", width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "graphic_book/images/1/24/8.png")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
