#!/usr/bin/env python3
"""Render Pausanias 1.26.2 as a central dedication study with ordered prose."""
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

PASSAGE_ID = "1.26.2"
ASSETS = ROOT / "graphic_book/assets/generated/1_26_2"
ART = ASSETS / "leokritos_shield.png"
ART_RECT = (550, 174, 1250, 1486)
TEXT_RECTS = [(28, 230, 523, 745), (1277, 230, 1772, 745),
              (28, 851, 523, 1475), (1277, 851, 1772, 1475)]

def render(output: Path, preflight: bool = False) -> None:
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute("SELECT english_translation FROM translations WHERE passage_id = ?", (PASSAGE_ID,)).fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing SQLite translation")
    passage = row[0]
    markers = ["fought in a manner worthy of mention, ",
               "first to leap into the Mouseion. ",
               "honored him with various distinctions, "]
    cuts = [passage.index(marker) + len(marker) for marker in markers]
    chunks = [passage[:cuts[0]].rstrip(), passage[cuts[0]:cuts[1]].rstrip(),
              passage[cuts[1]:cuts[2]].rstrip(), passage[cuts[2]:]]
    if len(chunks) != 4 or " ".join(chunks) != passage:
        raise RuntimeError("Translation segmentation changed SQLite text")
    page = Image.new("RGB", (1800,1600), "#e9ece9")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    def block(name: str, rect: tuple[int,int,int,int], content: str,
              maximum: int, minimum: int, *, heading: bool = False) -> None:
        font, wrapped, _, fit = fit_text_block(draw, rect, content,
            TITLE_FONT if heading else BODY_FONT, maximum, minimum, 12, name,
            spacing_ratio=0.17)
        spacing = max(2, round(fit.font_size * 0.17))
        raw = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=spacing)
        xy = (rect[0]+12-raw[0], rect[1]+12-raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0]+12 or actual[1] < rect[1]+12 or
                actual[2] > rect[2]-12 or actual[3] > rect[3]-12):
            raise RuntimeError(f"{name}: glyph overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill="#26353a")
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
    block("id", (28,16,350,72), "PASSAGE 1.26.2",31,26,heading=True)
    block("title", (375,16,1772,72), "LEOKRITOS AND HIS SHIELD",43,31,heading=True)
    block("orientation", (28,83,1772,135),
          "ATHENS · MOUSEION HILL · SANCTUARY OF ZEUS ELEUTHERIOS",25,20,heading=True)
    headings = ["1  ATHENS FREED", "2  LEOKRITOS", "3  HIS FALL", "4  THE DEDICATION"]
    heading_rects = [(28,166,523,222),(1277,166,1772,222),
                     (28,787,523,843),(1277,787,1772,843)]
    for i, (rect, heading_rect, chunk, heading) in enumerate(zip(TEXT_RECTS,heading_rects,chunks,headings),1):
        block(f"heading-{i}",heading_rect,heading,27,20,heading=True)
        block(f"translation-{i}",rect,chunk,39,30)
    block("caption",(550,1500,1250,1575),
          "Shield dedication to Zeus Eleutherios — interpretive object study.",24,20)
    validate_fit_records(records)
    rendered = " ".join(" ".join(r.text.split()) for r in records if r.name.startswith("translation-"))
    if rendered != " ".join(passage.split()):
        raise RuntimeError("Rendered text differs from SQLite")
    report = {"passage_id":PASSAGE_ID,"preflight":preflight,
              "translation_matches_sqlite":True,"translation_characters":len(passage),
              "text_blocks_checked":len(records),"fit_records":[asdict(r) for r in records]}
    (ROOT/"tmp").mkdir(exist_ok=True)
    (ROOT/"tmp/passage_1_26_2_layout_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != "fit_records"}))
    print("Font sizes:",[(r.name,r.font_size) for r in records])
    if preflight:
        return
    if output.exists():
        raise RuntimeError(f"Refusing overwrite: {output}")
    art = Image.open(ART).convert("RGB")
    page.paste(ImageOps.fit(art,(ART_RECT[2]-ART_RECT[0],ART_RECT[3]-ART_RECT[1]),
                            method=Image.Resampling.LANCZOS),ART_RECT[:2])
    draw.rectangle((ART_RECT[0]-1,ART_RECT[1]-1,ART_RECT[2],ART_RECT[3]),
                   outline="#68736e",width=2)
    output.parent.mkdir(parents=True,exist_ok=True)
    page.save(output)

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"graphic_book/images/1/26/2.png")
    parser.add_argument("--preflight",action="store_true")
    args=parser.parse_args()
    render(args.output,args.preflight)
