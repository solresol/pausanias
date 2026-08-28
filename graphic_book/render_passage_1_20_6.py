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


PASSAGE_ID = "1.20.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_20_6"
MAIN_ART = ASSET_DIR / "main_central_greece_campaign.png"
CHAERONEA_ART = ASSET_DIR / "chaeronea_battle.png"
CERAMEICUS_ART = ASSET_DIR / "cerameicus_lots.png"


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


def make_chaeronea_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(CHAERONEA_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Near Chaeronea, Sulla's Roman army defeated the forces commanded by Taxilus.",
        58,
        "chaeronea:caption",
        records,
    )
    add_panel_label(panel, records, "ROMAN LINE", (18, 190, 170, 234), (210, 184), max_size=8)
    add_panel_label(panel, records, "TAXILUS'S FORCE", (428, 190, 616, 234), (430, 172), max_size=8)
    add_panel_label(panel, records, "CHAERONEA PLAIN", (398, 20, 616, 64), (488, 100), max_size=8)
    return panel


def make_cerameicus_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(CERAMEICUS_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "In the Cerameicus, resisting Athenians were confined and one in ten was selected by lot.",
        58,
        "cerameicus:caption",
        records,
    )
    add_panel_label(panel, records, "CITY WALL", (18, 20, 150, 64), (130, 94), max_size=8)
    add_panel_label(panel, records, "ATHENIAN PRISONERS", (18, 190, 218, 234), (236, 170), max_size=8)
    add_panel_label(panel, records, "DRAWING LOTS", (402, 190, 616, 234), (378, 194), max_size=8)
    add_panel_label(panel, records, "CERAMEICUS", (438, 20, 616, 64), (486, 116), max_size=9)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, CHAERONEA_ART, CERAMEICUS_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(
        passage_draw, title_rect, "PASSAGE 1.20.6", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 88, passage_panel.width - 28, 492), translation, BODY_FONT,
        max_size=18, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.07,
    ))
    note_rect = (24, 504, 354, 592)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Routes, formations, viewpoints, attire, gestures, and the appearance of the lots are reconstructed; the named places and sequence follow Pausanias.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 606, 344, 638), "PHOCIS · BOEOTIA · ATHENS · 86 BCE", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (692, 40, 1122, 98)
    paste_with_shadow(page, make_label(
        "MARCHES AND MESSAGES · 86 BCE",
        heading_rect, records, font_path=TITLE_FONT, max_size=15, min_size=10,
    ), heading_rect[:2])

    callouts = [
        ("ELATEIA", (444, 118, 592, 166), (532, 202), 10),
        ("CHAERONEA", (682, 294, 856, 342), (824, 270), 9),
        ("LAKE COPAIS", (1028, 292, 1192, 340), (1106, 234), 9),
        ("ATHENS", (1170, 88, 1312, 136), (1232, 154), 10),
        ("TAXILUS SOUTH", (450, 430, 632, 478), (610, 394), 8),
        ("MESSENGERS", (716, 488, 884, 536), (820, 520), 9),
        ("SULLA NORTH", (1054, 500, 1246, 548), (1126, 574), 8),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    route_rect = (674, 594, 1340, 644)
    route = make_label(
        "ELATEIA · CHAERONEA · BOEOTIA · ATTICA",
        route_rect, records, font_path=BODY_FONT, max_size=10, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_chaeronea_panel(records), (28, 700))
    paste_with_shadow(page, make_cerameicus_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/20/5.png"],
        "evidence_boundary": "Pausanias supplies the named places, divided Roman force, marches, messages, victory near Chaeronea, fall of the Athenian wall, confinement in the Cerameicus, and selection by lot. Routes, formations, viewpoints, attire, gestures, architecture, and the appearance of the lots are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated oblique central-Greece campaign reconstruction from Elateia through Boeotia toward Athens."},
            {"path": str(CHAERONEA_ART), "description": "Generated non-graphic Chaeronea battle landscape."},
            {"path": str(CERAMEICUS_ART), "description": "Generated Cerameicus aftermath scene with a historically corrected grave stele and no execution depicted."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_20_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/20/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
