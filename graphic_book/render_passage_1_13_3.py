#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw

from graphic_book.render_passage_1_3_2 import (
    BODY_FONT, DISPLAY_FONT, FitRecord, HEIGHT, PARCHMENT_DEEP, RULE, TITLE_FONT,
    WIDTH, add_border, draw_fitted_text, draw_leader, draw_polyline_leader,
    framed_panel, make_inset_panel, make_label, make_parchment,
    paste_with_shadow, root_dir,
)
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill, make_compact_callout, validate_fit_records, warm_art,
)

PASSAGE_ID = "1.13.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_3"
MAIN_ART = ASSET_DIR / "main_dodona_shields.png"
COMMAND_ART = ASSET_DIR / "cleonymus_command.png"
LOCATOR_ART = ASSET_DIR / "epirus_macedonia_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((408, 332))
    draw = ImageDraw.Draw(panel)
    title = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(draw, title, "TROPHIES ACROSS THE KINGDOMS", TITLE_FONT,
        max_size=15, min_size=8, padding=6, name="locator:title", align="center", spacing_ratio=0.06))
    rect = (22, 70, panel.width - 22, 236)
    art = warm_art(crop_to_fill(LOCATOR_ART, (rect[2]-rect[0], rect[3]-rect[1]), centering=(0.5, 0.52)), grain_strength=0.012)
    panel.paste(art, rect[:2]); draw.rounded_rectangle(rect, radius=12, outline="#8d693f", width=2)
    points = {"DODONA": (86, 170), "MACEDONIA": (288, 116), "ATHENA ITONIA": (314, 194)}
    draw.line([points["DODONA"], points["MACEDONIA"], points["ATHENA ITONIA"]], fill="#f5ead2", width=7)
    draw.line([points["DODONA"], points["MACEDONIA"], points["ATHENA ITONIA"]], fill="#7c4033", width=3)
    label_rects = {
        "DODONA": (36, 172, 130, 198), "MACEDONIA": (238, 90, 360, 118),
        "ATHENA ITONIA": (256, 196, 386, 224), "PINDUS": (142, 122, 226, 148),
    }
    for index, (text, label_rect) in enumerate(label_rects.items()):
        draw.rounded_rectangle(label_rect, radius=7, fill="#f4dfb2", outline="#9c7443", width=1)
        records.append(draw_fitted_text(draw, label_rect, text, DISPLAY_FONT, max_size=9,
            min_size=6, padding=3, name=f"locator:label:{index}", align="center", spacing_ratio=0.04))
    records.append(draw_fitted_text(draw, (24, 248, panel.width-24, panel.height-14),
        "Gallic trophies stood in Thessaly; Macedonian shields crossed the Pindus to Zeus at Dodona.",
        BODY_FONT, max_size=12, min_size=8, padding=5, name="locator:caption", align="center", spacing_ratio=0.09))
    return panel


def make_inscription_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332)); draw = ImageDraw.Draw(panel)
    title = (24, 16, panel.width-24, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(draw, title, "THE TURN OF FORTUNE", TITLE_FONT,
        max_size=16, min_size=8, padding=6, name="inscription:title", align="center", spacing_ratio=0.06))
    quote = ('“These shields once devastated the gold-rich land of Asia; these shields bestowed servitude '
             'upon the Greeks. Now they lie ownerless beside the columns of Zeus’s temple, the spoils from boastful Macedonia.”')
    records.append(draw_fitted_text(draw, (30, 76, panel.width-30, 218), quote, BODY_FONT,
        max_size=15, min_size=9, padding=9, name="inscription:quote", align="center", spacing_ratio=0.12))
    rule_y = 232; draw.line((54, rule_y, panel.width-54, rule_y), fill="#9b7347", width=2)
    records.append(draw_fitted_text(draw, (32, 244, panel.width-32, panel.height-20),
        "The verse makes Macedonia’s former conquest of Asia and Greece answer for itself at Dodona.",
        BODY_FONT, max_size=12, min_size=8, padding=5, name="inscription:note", align="center", spacing_ratio=0.09))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, COMMAND_ART, LOCATOR_ART):
        if not asset.exists(): raise RuntimeError(f"Missing generated art asset: {asset}")
    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA"); draw = ImageDraw.Draw(page)
    main_rect = (430, 36, 1374, 628)
    art = warm_art(crop_to_fill(MAIN_ART, (main_rect[2]-main_rect[0], main_rect[3]-main_rect[1]), centering=(0.51, 0.50)), grain_strength=0.012)
    main_panel = framed_panel((art.width+28, art.height+28), fill=PARCHMENT_DEEP); main_panel.paste(art, (14,14))
    ImageDraw.Draw(main_panel).rectangle((14,14,14+art.width,14+art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0]-14, main_rect[1]-14))

    left = framed_panel((378, 706)); ld = ImageDraw.Draw(left); band = (18,14,left.width-18,72)
    ld.rounded_rectangle(band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(ld, band, "PASSAGE 1.13.3", TITLE_FONT, max_size=29,
        min_size=18, padding=10, name="panel:title", align="center", spacing_ratio=0.08))
    records.append(draw_fitted_text(ld, (24,92,left.width-24,left.height-24), translation, BODY_FONT,
        max_size=15, min_size=8, padding=8, name="panel:translation", spacing_ratio=0.12))
    paste_with_shadow(page, left, (32,36))

    title_rect = (644,54,1248,116)
    paste_with_shadow(page, make_label("THE SHIELDS AT DODONA", title_rect, records,
        font_path=TITLE_FONT, max_size=20, min_size=10), title_rect[:2])
    labels = [
        ("SACRED OAK", (458,164,610,208), (526,118)),
        ("ZEUS’S COLUMNS", (1004,142,1250,188), (1110,310)),
        ("MACEDONIAN SHIELDS", (946,494,1252,542), (1092,438)),
        ("EPIROTE MOUNTAINS", (518,506,770,552), (704,292)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1]+rect[3])//2)
        if rect[0] <= point[0] <= rect[2]: endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(page, make_label(text, rect, records, font_path=BODY_FONT,
            max_size=12, min_size=7), rect[:2])
    note1 = make_compact_callout("At Dodona, conquest became a dedication to Zeus.", (440,86), "callout:dodona", records, max_size=14)
    draw_polyline_leader(draw, [(448,652),(620,600),(872,430)]); paste_with_shadow(page,note1,(448,642))
    note2 = make_compact_callout("The ownerless shields reverse Macedonia’s old boast.", (448,86), "callout:reversal", records, max_size=14)
    draw_polyline_leader(draw, [(904,652),(1060,590),(1134,444)]); paste_with_shadow(page,note2,(904,642))

    paste_with_shadow(page, make_locator(records), (32,780))
    command = warm_art(crop_to_fill(COMMAND_ART, (420,202), centering=(0.50,0.48)), grain_strength=0.014)
    inset = make_inset_panel(command,
        "Cleonymus kept Pyrrhus from turning a near-total victory into the complete subjugation of Macedonia.",
        92, "inset:command-caption", records)
    paste_with_shadow(page, inset, (450,780))
    lr=(540,800,780,836); draw_leader(draw,(664,920),(lr[0],lr[1]+18))
    paste_with_shadow(page, make_label("CONQUEST LEFT INCOMPLETE",lr,records,font_path=BODY_FONT,max_size=11,min_size=7),lr[:2])
    paste_with_shadow(page, make_inscription_panel(records), (904,780))
    add_border(draw); validate_fit_records(records)
    output_path.parent.mkdir(parents=True, exist_ok=True); page.convert("RGB").save(output_path, quality=95)
    report = {"passage_id":PASSAGE_ID,"output_path":str(output_path),"text_blocks_checked":len(records),
        "minimum_font_size_used":min(r.font_size for r in records),"fit_records":[asdict(r) for r in records],
        "page_plan":str(ASSET_DIR/"page_plan.md"),"approved_reference_pages":["graphic_book/images/1/1/4.png","graphic_book/images/1/1/5.png"],
        "continuity_reference_pages":["graphic_book/images/1/13/2.png"]}
    path=root_dir()/"tmp/passage_1_13_3_layout_report.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,indent=2))
    return report


def main() -> None:
    print(json.dumps(render_page(root_dir()/"graphic_book/images/1/13/3.png"), indent=2))


if __name__ == "__main__":
    main()
