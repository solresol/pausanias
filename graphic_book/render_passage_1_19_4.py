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


PASSAGE_ID = "1.19.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_19_4"
MAIN_ART = ASSET_DIR / "main_tomb.png"
SIEGE_ART = ASSET_DIR / "nisaea_siege.png"
SCYLLA_ART = ASSET_DIR / "scylla_lock.png"


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


def make_siege_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(SIEGE_ART, (634, 280), centering=(0.52, 0.53)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "The Cretan fleet closes on Nisaea, the fortified harbour where Nisus made his stand.",
        58,
        "siege:caption",
        records,
    )
    add_panel_label(panel, records, "NISAEA", (430, 28, 610, 72), (490, 104), max_size=10)
    add_panel_label(panel, records, "CRETAN FLEET", (22, 188, 186, 232), (220, 188), max_size=9)
    add_panel_label(panel, records, "SIEGE CAMP", (438, 190, 610, 234), (446, 166), max_size=9)
    return panel


def make_scylla_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(SCYLLA_ART, (634, 280), centering=(0.57, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "The myth makes Nisus' purple lock the condition of his life—and his daughter Scylla its betrayer.",
        58,
        "scylla:caption",
        records,
    )
    add_panel_label(panel, records, "SCYLLA", (24, 28, 138, 72), (320, 88), max_size=9)
    add_panel_label(panel, records, "PURPLE LOCK", (342, 28, 514, 72), (410, 116), max_size=9)
    add_panel_label(panel, records, "NISUS", (500, 190, 610, 234), (470, 168), max_size=9)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, SIEGE_ART, SCYLLA_ART):
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
        passage_draw, title_rect, "PASSAGE 1.19.4", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 90, passage_panel.width - 28, 480), translation, BODY_FONT,
        max_size=18, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.08,
    ))
    note_rect = (24, 496, 346, 578)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Pausanias records the tomb and the myth; monument form, exact placement, siege, and chamber are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 596, 336, 636), "ATHENS · MEGARA · NISAEA · CRETE", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.51)), grain_strength=0.004)
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (704, 40, 1116, 98)
    paste_with_shadow(page, make_label(
        "THE TOMB BEHIND THE LYCEUM", heading_rect, records,
        font_path=TITLE_FONT, max_size=19, min_size=12,
    ), heading_rect[:2])

    callouts = [
        ("ACROPOLIS", (438, 104, 568, 148), (598, 118)),
        ("TOMB OF NISUS", (438, 500, 616, 546), (676, 500)),
        ("LYCEUM GROVE", (1044, 292, 1216, 336), (1060, 354)),
        ("SACRED ROAD", (1052, 500, 1210, 544), (1030, 492)),
        ("ATHENS", (596, 202, 716, 244), (748, 202)),
    ]
    for text, rect, point in callouts:
        add_page_label(page, draw, records, text, rect, point)

    route_rect = (770, 592, 1330, 654)
    route = make_label(
        "ATHENS · TOMB TRADITION · MEGARA / NISAEA · CRETAN WAR",
        route_rect, records, font_path=BODY_FONT, max_size=11, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_siege_panel(records), (28, 700))
    paste_with_shadow(page, make_scylla_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/19/3.png"],
        "evidence_boundary": "The recorded tomb and myth are distinguished from reconstructed monument, placement, siege, clothing, and chamber.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the tomb of Nisus behind the Lyceum."},
            {"path": str(SIEGE_ART), "description": "Generated reconstruction of the Cretan siege of Nisaea."},
            {"path": str(SCYLLA_ART), "description": "Generated non-graphic narrative scene of Scylla cutting Nisus' purple lock."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_19_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/19/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
