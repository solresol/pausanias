#!/usr/bin/env python3
"""Render Philippides and Pan around a measured, continuous reading field."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book_corpus import load_translation, snapshot_path
from graphic_book_fonts import BODY_FONT, TITLE_FONT
from graphic_book.render_passage_1_3_2 import FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

ASSETS = ROOT / "graphic_book/assets/generated/1_28_4"
ART_RECT = (36, 220, 2364, 2250)
READING_PANEL = (66, 1000, 1390, 2220)
BODY_RECT = (96, 1110, 1358, 2188)
CAPTION = (
    "Philippides's reported encounter on Mount Parthenion. Interpretive scene: "
    "figures, dress and landscape are conjectural. The spring and Apollo's cave belong to Athens."
)


def render(output: Path, preflight: bool = False) -> None:
    """Require exact source order and padded actual glyph bounds before saving."""
    snapshot_path()
    passage = load_translation("1.28.4")
    page = Image.new("RGB", (2400, 2400), "#efede4")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 18, name, .25,
        )
        spacing = max(2, round(fit.font_size * .25))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 18 - bbox[0], rect[1] + 18 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 18 or actual[1] < rect[1] + 18
                or actual[2] > rect[2] - 18 or actual[3] > rect[3] - 18):
            raise RuntimeError(name + ": glyphs overflow padded target")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing, heading))

    measure("passage-id", (36, 20, 620, 112), "PASSAGE 1.28.4", 42, 36, True)
    measure("title", (654, 20, 2364, 112), "THE MESSENGER AND PAN", 64, 46, True)
    measure("orientation", (36, 126, 2364, 196),
            "ATHENS, BELOW THE PROPYLAIA  |  PHILIPPIDES'S STORY: MOUNT PARTHENION", 33, 28, True)
    measure("reading-heading", (96, 1022, 1358, 1094),
            "PAUSANIAS'S ACCOUNT", 35, 30, True)
    measure("translation", BODY_RECT, passage, 52, 44)
    measure("interpretive-caption", (36, 2264, 2364, 2390), CAPTION, 32, 28)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == "translation")
    if " ".join(wrapped.split()) != " ".join(passage.split()):
        raise RuntimeError("Complete English must remain in exported order")
    report = {
        "passage_id": "1.28.4", "preflight": preflight, "canvas": [2400, 2400],
        "art_rectangle": ART_RECT, "reading_panel": READING_PANEL,
        "translation_rectangle": BODY_RECT,
        "reading_order": "one continuous inset English field, top to bottom",
        "translation_exact": passage,
        "translation_characters": len(passage), "translation_words": len(passage.split()),
        "translation_utf8_sha256": hashlib.sha256(passage.encode()).hexdigest(),
        "translation_matches_export": True, "minimum_body_font_size": 44,
        "body_font_size": next(r.font_size for r in records if r.name == "translation"),
        "padding": 18, "text_blocks_checked": len(records),
        "fit_records": [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "layout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("fit_records", "translation_exact")}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError("Refusing to overwrite " + str(output))
    with Image.open(ASSETS / "parthenion.png") as source:
        art = ImageOps.fit(source.convert("RGB"),
                           (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline="#8a8d7b", width=2)
    draw.rectangle(READING_PANEL, fill="#f3f0e5", outline="#8a8d7b", width=2)
    draw.line((36, 207, 2364, 207), fill="#b4ad98", width=2)
    for xy, text, font, spacing, heading in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing,
                            fill="#303b38" if heading else "#303633")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print("Saved", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "graphic_book/images/1/28/4.png")
    args = parser.parse_args()
    render(args.output, args.preflight)
