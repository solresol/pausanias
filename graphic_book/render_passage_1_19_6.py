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


PASSAGE_ID = "1.19.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_19_6"
MAIN_ART = ASSET_DIR / "main_agrai_stadium.png"
ARTEMIS_ART = ASSET_DIR / "artemis_hunt.png"
QUARRY_ART = ASSET_DIR / "pentelic_quarry.png"


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


def make_artemis_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(ARTEMIS_ART, (634, 280), centering=(0.50, 0.43)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Artemis begins her first hunt after Delos; Pausanias explains why her image at Agrai held a bow.",
        58,
        "artemis:caption",
        records,
    )
    add_panel_label(panel, records, "ARTEMIS", (450, 24, 610, 68), (468, 126), max_size=10)
    add_panel_label(panel, records, "BOW", (300, 24, 410, 68), (356, 122), max_size=10)
    add_panel_label(panel, records, "FIRST HUNT AFTER DELOS", (20, 188, 250, 234), (186, 164), max_size=9)
    return panel


def make_quarry_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(QUARRY_ART, (634, 280), centering=(0.50, 0.52)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Pentelic marble was quarried, lowered, and hauled toward Athens for Herodes' vast stadium.",
        58,
        "quarry:caption",
        records,
    )
    add_panel_label(panel, records, "PENTELIC QUARRY", (20, 24, 208, 68), (210, 105), max_size=10)
    add_panel_label(panel, records, "MARBLE BLOCK", (210, 190, 388, 234), (312, 150), max_size=10)
    add_panel_label(panel, records, "OX SLEDGE", (468, 190, 610, 234), (504, 158), max_size=10)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, ARTEMIS_ART, QUARRY_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(
        passage_draw, title_rect, "PASSAGE 1.19.6", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 90, passage_panel.width - 28, 486), translation, BODY_FONT,
        max_size=18, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.08,
    ))
    note_rect = (24, 500, 346, 582)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Named places, the hunt tradition, stadium form, builder, and marble source are recorded; viewpoint, architecture, and quarry operations are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 598, 336, 636), "ATHENS · ILISOS · AGRAI · PENTELICUS", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (680, 40, 1160, 98)
    paste_with_shadow(page, make_label(
        "AGRAI AND THE MARBLE STADIUM", heading_rect, records,
        font_path=TITLE_FONT, max_size=18, min_size=11,
    ), heading_rect[:2])

    callouts = [
        ("ACROPOLIS", (438, 118, 576, 162), (566, 184), 10),
        ("ATHENS", (452, 250, 574, 294), (644, 264), 10),
        ("ILISOS", (448, 526, 574, 570), (720, 522), 10),
        ("CROSSING TO AGRAI", (590, 566, 790, 614), (760, 548), 9),
        ("STADIUM OF HERODES", (776, 258, 1008, 308), (1012, 342), 10),
        ("TWO DESCENDING ARMS", (826, 448, 1058, 498), (946, 410), 9),
        ("ARTEMIS AGROTERA", (1128, 474, 1328, 524), (1210, 462), 9),
        ("MOUNT PENTELICUS", (1128, 116, 1328, 164), (1224, 86), 9),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    route_rect = (802, 606, 1328, 656)
    route = make_label(
        "PENTELICUS · ATHENS · ILISOS CROSSING · AGRAI",
        route_rect, records, font_path=BODY_FONT, max_size=10, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_artemis_panel(records), (28, 700))
    paste_with_shadow(page, make_quarry_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/19/5.png"],
        "evidence_boundary": "Pausanias records the places, Artemis tradition, bowed statue, stadium, hillside form, Herodes, and Pentelic marble claim; viewpoint, architecture, quarry operations, clothing, vegetation, and transport are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated oblique reconstruction of Agrai, the Ilisos, stadium, sanctuary, Athens, and Pentelicus."},
            {"path": str(ARTEMIS_ART), "description": "Generated, fully clothed scene of Artemis beginning her first hunt after Delos."},
            {"path": str(QUARRY_ART), "description": "Generated reconstruction of Pentelic marble extraction and transport preparation."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_19_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/19/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
