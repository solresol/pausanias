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
    BODY_FONT,
    FitRecord,
    HEIGHT,
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    draw_fitted_text,
    draw_leader,
    framed_panel,
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)
from graphic_book.render_passage_1_10_1 import crop_to_fill, validate_fit_records, warm_art


PASSAGE_ID = "1.21.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_21_2"
MAIN_ART = ASSET_DIR / "main_vineyard_dream.png"
PORTRAIT_ART = ASSET_DIR / "later_portrait.png"
MARATHON_ART = ASSET_DIR / "marathon_painting.png"
RELIEF_ART = root_dir() / "graphic_book/assets/generated/1_14_4/southern_greece_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return row[0]


def leader_endpoint(rect: tuple[int, int, int, int], point: tuple[int, int]) -> tuple[int, int]:
    if rect[0] <= point[0] <= rect[2]:
        return (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)


def add_page_label(
    page: Image.Image,
    draw: ImageDraw.ImageDraw,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    draw_leader(draw, point, leader_endpoint(rect, point))
    paste_with_shadow(
        page,
        make_label(text, rect, records, font_path=TITLE_FONT, max_size=max_size, min_size=min_size),
        rect[:2],
    )


def add_panel_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    panel.alpha_composite(
        make_label(text, rect, records, font_path=TITLE_FONT, max_size=max_size, min_size=min_size),
        rect[:2],
    )


def make_orientation_strip(records: list[FitRecord]) -> Image.Image:
    relief = warm_art(
        crop_to_fill(RELIEF_ART, (326, 96), centering=(0.76, 0.30)),
        grain_strength=0.003,
    ).convert("RGBA")
    strip = framed_panel((338, 108))
    strip.paste(relief, (6, 6))
    draw = ImageDraw.Draw(strip)
    athens = (193, 70)
    marathon = (270, 46)
    draw.line((athens, marathon), fill="#ead7a5", width=3)
    for point in (athens, marathon):
        draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5), fill="#76502c", outline="#f4deb0", width=2)
    athens_rect = (80, 72, 188, 100)
    marathon_rect = (214, 8, 326, 36)
    strip.alpha_composite(
        make_label("ATHENS", athens_rect, records, font_path=TITLE_FONT, max_size=7, min_size=6),
        athens_rect[:2],
    )
    strip.alpha_composite(
        make_label("MARATHON", marathon_rect, records, font_path=TITLE_FONT, max_size=7, min_size=6),
        marathon_rect[:2],
    )
    return strip


def make_portrait_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(PORTRAIT_ART, (634, 280), centering=(0.61, 0.00)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Pausanias judged Aeschylus' theatre portrait to be a substantially later commemoration.",
        58,
        "portrait:caption",
        records,
    )
    add_panel_label(panel, records, "LATER PORTRAIT", (18, 20, 190, 64), (388, 122), max_size=8)
    add_panel_label(panel, records, "OLDER MONUMENTS", (18, 190, 206, 234), (210, 126), max_size=8)
    add_panel_label(panel, records, "THEATRE", (470, 190, 616, 234), (486, 144), max_size=8)
    return panel


def make_marathon_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(MARATHON_ART, (634, 280), centering=(0.50, 0.46)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "The Marathon painting already belonged to Athenian civic memory before the portrait was made.",
        58,
        "marathon:caption",
        records,
    )
    add_panel_label(panel, records, "PAINTED MARATHON", (18, 20, 210, 64), (328, 104), max_size=8)
    add_panel_label(panel, records, "HOPLITE LINE", (18, 190, 166, 234), (202, 136), max_size=8)
    add_panel_label(panel, records, "SHORE AND SHIPS", (436, 190, 616, 234), (478, 116), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, PORTRAIT_ART, MARATHON_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(
        passage_draw, title_rect, "PASSAGE 1.21.2", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 88, passage_panel.width - 28, 398), translation, BODY_FONT,
        max_size=19, min_size=11, padding=5, name="passage:translation", spacing_ratio=0.065,
    ))
    note_rect = (24, 408, 354, 524)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Pausanias supplies the relative chronology, youthful field watch, sleep, grape clusters, Dionysian command, daybreak, eagerness, and first attempt; locations, statue installation, objects, gestures, and the painting's display are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=8, name="passage:evidence-note", align="center", spacing_ratio=0.06,
    ))
    passage_panel.alpha_composite(make_orientation_strip(records), (20, 534))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (680, 40, 1124, 98)
    paste_with_shadow(page, make_label(
        "AESCHYLUS · THE VINEYARD DREAM",
        heading_rect, records, font_path=TITLE_FONT, max_size=14, min_size=9,
    ), heading_rect[:2])

    callouts = [
        ("GRAPE WATCH", (438, 118, 610, 166), (520, 190), 9),
        ("YOUNG AESCHYLUS", (438, 520, 650, 568), (642, 478), 8),
        ("DIONYSUS", (1082, 116, 1248, 164), (966, 270), 9),
        ("WAX TABLET", (906, 536, 1074, 584), (956, 584), 8),
        ("DAYBREAK", (1160, 504, 1324, 552), (1288, 320), 9),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    chronology_rect = (676, 612, 1138, 658)
    paste_with_shadow(page, make_label(
        "MARATHON PAINTING · AESCHYLUS DIES · LATER PORTRAIT",
        chronology_rect, records, font_path=BODY_FONT, max_size=9, min_size=7,
    ), chronology_rect[:2])

    paste_with_shadow(page, make_portrait_panel(records), (28, 700))
    paste_with_shadow(page, make_marathon_panel(records), (718, 700))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "translation_font_size": next(record.font_size for record in records if record.name == "passage:translation"),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/21/1.png"],
        "evidence_boundary": "Pausanias supplies relative chronology, the youthful field watch, sleep, grape clusters, Dionysian command, daybreak, eagerness, and first attempt. Locations, portrait installation, objects, gestures, and the painting display are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated vineyard dream with young Aeschylus, fully robed Dionysus, grapes, tablet, mask, and daybreak."},
            {"path": str(PORTRAIT_ART), "description": "Generated Roman-period theatre portrait-installation scene."},
            {"path": str(MARATHON_ART), "description": "Generated non-graphic display of an ancient painted Marathon commemoration."},
            {"path": str(RELIEF_ART), "description": "Existing generated southern-Greece relief reused as a subordinate Attica orientation strip."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_21_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/21/2.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
