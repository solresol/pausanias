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


PASSAGE_ID = "1.20.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_20_4"
MAIN_ART = ASSET_DIR / "main_odeion.png"
SULLA_ART = ASSET_DIR / "sulla_capture.png"
MITHRIDATES_ART = ASSET_DIR / "mithridates_orientation.png"


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


def make_sulla_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(SULLA_ART, (634, 280), centering=(0.50, 0.48)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "In 86 BCE the odeion burned amid Sulla's capture of Athens; ancient accounts differ over who ordered the fire.",
        58,
        "sulla:caption",
        records,
    )
    add_panel_label(panel, records, "BURNING ODEION", (18, 22, 194, 66), (250, 150), max_size=8)
    add_panel_label(panel, records, "ACROPOLIS", (466, 22, 610, 66), (468, 92), max_size=9)
    add_panel_label(panel, records, "SULLA'S ARMY", (430, 190, 610, 234), (448, 185), max_size=8)
    return panel


def make_mithridates_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(MITHRIDATES_ART, (634, 280), centering=(0.52, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "From his Euxine realm, Mithridates crossed into Asia; the conflict then reached Athens.",
        58,
        "mithridates:caption",
        records,
    )
    add_panel_label(panel, records, "EUXINE REALM", (18, 22, 184, 66), (218, 82), max_size=8)
    add_panel_label(panel, records, "ASIA MINOR", (224, 22, 372, 66), (322, 116), max_size=9)
    add_panel_label(panel, records, "AEGEAN TO ATHENS", (194, 190, 406, 234), (122, 190), max_size=8)
    add_panel_label(panel, records, "MITHRIDATES VI", (456, 190, 610, 234), (486, 160), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, SULLA_ART, MITHRIDATES_ART):
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
        passage_draw, title_rect, "PASSAGE 1.20.4", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 88, passage_panel.width - 28, 476), translation, BODY_FONT,
        max_size=18, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.07,
    ))
    note_rect = (24, 490, 354, 592)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "The identification as Pericles' odeion is conventional. Roof, cutaway, figures, and viewpoint are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 606, 344, 638), "ATHENS · SOUTH SLOPE · 86 BCE", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (696, 40, 1116, 98)
    paste_with_shadow(page, make_label(
        "THE ODEION LIKE XERXES' TENT", heading_rect, records,
        font_path=TITLE_FONT, max_size=15, min_size=10,
    ), heading_rect[:2])

    callouts = [
        ("ODEION OF PERICLES", (442, 116, 668, 162), (660, 410), 9),
        ("TENT-LIKE TIMBER ROOF", (442, 526, 702, 574), (668, 340), 8),
        ("MANY-COLUMNED INTERIOR", (716, 154, 976, 202), (754, 382), 8),
        ("THEATRE OF DIONYSUS", (1084, 506, 1338, 554), (1128, 456), 8),
        ("ACROPOLIS", (1108, 116, 1286, 162), (1144, 182), 10),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    route_rect = (786, 594, 1340, 644)
    route = make_label(
        "ODEION · THEATRE · SANCTUARY · ACROPOLIS",
        route_rect, records, font_path=BODY_FONT, max_size=10, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_sulla_panel(records), (28, 700))
    paste_with_shadow(page, make_mithridates_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/20/3.png"],
        "evidence_boundary": "Pausanias supplies the structure beside the sanctuary and theatre, its association with Xerxes' tent, rebuilding, Sulla's burning/capture, and Mithridates' Euxine realm and Asian conquests. The Odeion identification is conventional; roof form, cutaway, attire, fire, figures, and viewpoints are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated oblique reconstruction of the Odeion of Pericles beside the Theatre of Dionysus and Acropolis."},
            {"path": str(SULLA_ART), "description": "Generated non-graphic 86 BCE capture scene, revised to replace imperial segmented armour with late-Republican mail."},
            {"path": str(MITHRIDATES_ART), "description": "Generated oblique Euxine-to-Aegean orientation panorama with Mithridates VI and entourage."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_20_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/20/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
