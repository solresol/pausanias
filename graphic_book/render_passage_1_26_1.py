#!/usr/bin/env python3
"""Render Pausanias 1.26.1: tall narrative art beside ordered prose."""
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
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records
PASSAGE_ID = "1.26.1"
ASSETS = ROOT / "graphic_book/assets/generated/1_26_1"
ART = ASSETS / "mouseion_advance.png"
ART_RECT = (28, 151, 1125, 1508)
TEXT_RECTS = [(1170, 216, 1772, 636), (1170, 735, 1772, 1140), (1170, 1239, 1772, 1578)]

def render(output: Path, preflight: bool = False) -> None:
    """Fit every text block and verify exact translation before saving."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing translation")
    passage = row[0]
    chunks = passage.split(". ")
    chunks = [s + "." if i < len(chunks)-1 else s for i,s in enumerate(chunks)]
    if len(chunks) != 3 or " ".join(chunks) != passage:
        raise RuntimeError("Translation splitting mismatch")
    page = Image.new("RGB", (1800,1600), "#eee9df")
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

    block("id", (28,16,350,73), "PASSAGE 1.26.1", 31,26,heading=True)
    block("title", (375,16,1772,73), "OLYMPIODORUS AND THE MOUSEION", 42,31,heading=True)
    block("orientation", (28,83,1772,135), "ATHENS · MOUSEION / MUSEUM HILL · SOUTHWEST OF THE ACROPOLIS",25,20,heading=True)
    block("caption", (28,1520,1125,1580), "The advance toward the Mouseion — interpretive historical scene.",24,20)
    for i,(rect,chunk,heading) in enumerate(zip(TEXT_RECTS,chunks,["1  THE CHOICE OF GENERAL","2  OLDER MEN AND YOUTHS","3  THE HILL CAPTURED"]),1):
        block(f"heading-{i}",(rect[0],rect[1]-65,rect[2],rect[1]-8),heading,27,20,heading=True)
        block(f"translation-{i}",rect,chunk,39,31)
    validate_fit_records(records)
    rendered = " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-"))
    if rendered != " ".join(passage.split()):
        raise RuntimeError("Rendered passage differs from SQLite")
    report={"passage_id":PASSAGE_ID,"preflight":preflight,"translation_matches_sqlite":True,"translation_characters":len(passage),"text_blocks_checked":len(records),"fit_records":[asdict(r) for r in records]}
    (ROOT/"tmp").mkdir(exist_ok=True)
    (ROOT/"tmp/passage_1_26_1_layout_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != "fit_records"}))
    print("Font sizes:",[(r.name,r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art=Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art,(ART_RECT[2]-ART_RECT[0],ART_RECT[3]-ART_RECT[1]),method=Image.Resampling.LANCZOS),ART_RECT[:2])
    draw.rectangle((ART_RECT[0]-1,ART_RECT[1]-1,ART_RECT[2],ART_RECT[3]),outline="#7a7164",width=2)
    output.parent.mkdir(parents=True,exist_ok=True)
    page.save(output)

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"graphic_book/images/1/26/1.png")
    parser.add_argument("--preflight",action="store_true")
    args=parser.parse_args()
    render(args.output,args.preflight)
