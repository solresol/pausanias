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


PASSAGE_ID = "1.20.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_20_5"
MAIN_ART = ASSET_DIR / "main_attica_retreat.png"
ARISTION_ART = ASSET_DIR / "aristion_assembly.png"
SIPYLUS_ART = ASSET_DIR / "sipylus_battle.png"


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


def make_aristion_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(ARISTION_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Aristion won the turbulent popular faction, while prominent Athenians went over to the Romans.",
        58,
        "aristion:caption",
        records,
    )
    add_panel_label(panel, records, "ARISTION", (18, 22, 160, 66), (202, 124), max_size=9)
    add_panel_label(panel, records, "POPULAR FACTION", (18, 190, 202, 234), (132, 170), max_size=8)
    add_panel_label(panel, records, "NOTABLES LEAVING", (354, 22, 532, 66), (404, 150), max_size=8)
    add_panel_label(panel, records, "ROMAN ENVOYS", (476, 190, 610, 234), (564, 154), max_size=8)
    return panel


def make_sipylus_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(SIPYLUS_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Earlier, the Magnesians around Sipylus wounded Archelaus and destroyed most of his invading force.",
        58,
        "sipylus:caption",
        records,
    )
    add_panel_label(panel, records, "MOUNT SIPYLUS", (210, 22, 410, 66), (320, 92), max_size=9)
    add_panel_label(panel, records, "MAGNESIANS", (18, 190, 170, 234), (172, 178), max_size=8)
    add_panel_label(panel, records, "ARCHELAUS", (448, 190, 610, 234), (412, 178), max_size=9)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, ARISTION_ART, SIPYLUS_ART):
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
        passage_draw, title_rect, "PASSAGE 1.20.5", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 88, passage_panel.width - 28, 480), translation, BODY_FONT,
        max_size=18, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.07,
    ))
    note_rect = (24, 494, 354, 592)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "The battlefield location, troop formations, routes, and gestures are reconstructed; the destinations and sequence follow Pausanias.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 606, 344, 638), "ATHENS · PIRAEUS · SIPYLUS · 88–86 BCE", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (674, 40, 1128, 98)
    paste_with_shadow(page, make_label(
        "THE TWO RETREATS FROM BATTLE",
        heading_rect, records, font_path=TITLE_FONT, max_size=15, min_size=10,
    ), heading_rect[:2])

    callouts = [
        ("PIRAEUS", (442, 510, 604, 558), (604, 472), 10),
        ("LONG WALLS CORRIDOR", (560, 278, 774, 326), (686, 338), 8),
        ("ROMAN VICTORY", (806, 386, 974, 434), (934, 340), 9),
        ("ATHENIANS TO THE CITY", (966, 260, 1234, 308), (1112, 292), 8),
        ("ATHENS", (1126, 116, 1300, 164), (1150, 186), 10),
        ("ARCHELAUS TO PIRAEUS", (1010, 506, 1314, 554), (1068, 470), 8),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    route_rect = (758, 594, 1340, 644)
    route = make_label(
        "CITY PURSUIT · PORT WITHDRAWAL · ATTIC COASTAL PLAIN",
        route_rect, records, font_path=BODY_FONT, max_size=10, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_aristion_panel(records), (28, 700))
    paste_with_shadow(page, make_sipylus_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/20/4.png"],
        "evidence_boundary": "Pausanias supplies Aristion's role, the divided Athenian response, Roman victory, retreats to Athens and Piraeus, and Archelaus's earlier defeat near Sipylus. Battlefield location, routes, formations, attire, gestures, and viewpoints are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated oblique Attica orientation reconstruction separating Athens and Piraeus."},
            {"path": str(ARISTION_ART), "description": "Generated civic assembly tableau showing Aristion and the divided Athenian response."},
            {"path": str(SIPYLUS_ART), "description": "Generated non-graphic Mount Sipylus battle landscape showing Archelaus's wounding."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_20_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/20/5.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
