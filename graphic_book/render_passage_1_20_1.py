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


PASSAGE_ID = "1.20.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_20_1"
MAIN_ART = ASSET_DIR / "main_street_tripods.png"
SATYR_ART = ASSET_DIR / "praxiteles_satyr.png"
WORKSHOP_ART = ASSET_DIR / "workshop_alarm.png"


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


def make_satyr_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(SATYR_ART, (634, 280), centering=(0.50, 0.20)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Praxiteles was said to value this satyr especially highly among his own creations.",
        58,
        "satyr:caption",
        records,
    )
    add_panel_label(panel, records, "PRAXITELES' SATYR", (20, 24, 226, 68), (250, 116), max_size=10)
    add_panel_label(panel, records, "RELIEF", (470, 24, 610, 68), (500, 128), max_size=9)
    add_panel_label(panel, records, "BRONZE TRIPOD", (422, 190, 610, 234), (506, 220), max_size=9)
    return panel


def make_workshop_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(WORKSHOP_ART, (634, 280), centering=(0.50, 0.52)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Phryne's servant reports a false workshop fire; Praxiteles' alarm is meant to reveal his finest work.",
        58,
        "workshop:caption",
        records,
    )
    add_panel_label(panel, records, "PHRYNE", (20, 24, 142, 68), (112, 138), max_size=10)
    add_panel_label(panel, records, "THE SERVANT", (178, 188, 340, 234), (250, 132), max_size=9)
    add_panel_label(panel, records, "PRAXITELES", (442, 24, 610, 68), (414, 136), max_size=9)
    add_panel_label(panel, records, "PRIZED WORKS", (444, 188, 610, 234), (548, 120), max_size=9)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, SATYR_ART, WORKSHOP_ART):
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
        passage_draw, title_rect, "PASSAGE 1.20.1", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 90, passage_panel.width - 28, 488), translation, BODY_FONT,
        max_size=18, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.08,
    ))
    note_rect = (24, 500, 346, 582)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Street, monuments, tripods, reliefs, satyr, and workshop ruse are recorded; alignment, architecture, clothing, and gestures are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 598, 336, 636), "PRYTANEION · TRIPODS · ACROPOLIS", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (682, 40, 1160, 98)
    paste_with_shadow(page, make_label(
        "THE STREET OF THE TRIPODS", heading_rect, records,
        font_path=TITLE_FONT, max_size=18, min_size=11,
    ), heading_rect[:2])

    callouts = [
        ("ACROPOLIS", (446, 112, 584, 156), (894, 116), 10),
        ("PRYTANEION DIRECTION", (442, 500, 666, 548), (612, 430), 9),
        ("STREET OF THE TRIPODS", (622, 570, 862, 620), (730, 520), 9),
        ("CHORAGIC MONUMENT", (866, 420, 1086, 470), (1118, 410), 9),
        ("BRONZE TRIPOD", (1134, 112, 1326, 160), (1218, 132), 9),
        ("RELIEF PANEL", (1150, 488, 1326, 536), (1228, 430), 9),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    route_rect = (850, 594, 1328, 644)
    route = make_label(
        "PRYTANEION · TRIPOD STREET · THEATRE PRECINCT",
        route_rect, records, font_path=BODY_FONT, max_size=10, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_satyr_panel(records), (28, 700))
    paste_with_shadow(page, make_workshop_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/19/6.png"],
        "evidence_boundary": "Pausanias records the street, small monuments, bronze tripods, reliefs, prized satyr, Phryne's request, and workshop-fire ruse; alignment, architecture, clothing, workshop contents, and gestures are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated oblique reconstruction of the Street of the Tripods beneath the Acropolis."},
            {"path": str(SATYR_ART), "description": "Generated fully draped study of Praxiteles' prized satyr, tripod, and relief."},
            {"path": str(WORKSHOP_ART), "description": "Generated fully clothed workshop scene of Phryne's false-fire ruse."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_20_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/20/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
