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


PASSAGE_ID = "1.21.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_21_4"
MAIN_ART = ASSET_DIR / "main_asclepieion_ascent.png"
WORKSHOP_ART = ASSET_DIR / "daedalus_kalos_workshop.png"
TRIAL_ART = ASSET_DIR / "ares_homicide_trial.png"
RELIEF_ART = ASSET_DIR / "mediterranean_relief.png"


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


def make_flight_strip(records: list[FitRecord]) -> Image.Image:
    relief = warm_art(
        crop_to_fill(RELIEF_ART, (326, 96), centering=(0.50, 0.56)),
        grain_strength=0.003,
    ).convert("RGBA")
    strip = framed_panel((338, 108))
    strip.paste(relief, (6, 6))
    draw = ImageDraw.Draw(strip)
    athens = (214, 41)
    crete = (201, 81)
    sicily = (54, 63)
    draw.line((athens, crete, sicily), fill="#f2dfae", width=4)
    draw.line((athens, crete, sicily), fill="#76502c", width=2)
    for point in (athens, crete, sicily):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#76502c",
            outline="#f4deb0",
            width=2,
        )
    labels = [
        ("ATHENS", (220, 8, 332, 36)),
        ("CRETE", (214, 72, 306, 102)),
        ("SICILY", (6, 70, 100, 102)),
    ]
    for text, rect in labels:
        strip.alpha_composite(
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=7, min_size=6),
            rect[:2],
        )
    return strip


def make_workshop_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(WORKSHOP_ART, (634, 280), centering=(0.50, 0.46)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Before the crime, Daedalus' gifted nephew and pupil Kalos shared his workshop and craft.",
        58,
        "workshop:caption",
        records,
    )
    add_panel_label(panel, records, "DAEDALUS", (18, 20, 156, 62), (202, 126), max_size=8)
    add_panel_label(panel, records, "KALOS · PUPIL", (470, 20, 616, 62), (442, 128), max_size=8)
    add_panel_label(panel, records, "COMPASS · SAW · CRAFT", (218, 196, 430, 238), (330, 160), max_size=7)
    return panel


def make_trial_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(TRIAL_ART, (634, 280), centering=(0.50, 0.48)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "The spring tradition led to Ares' trial: Athens' first judgment concerning homicide.",
        58,
        "trial:caption",
        records,
    )
    add_panel_label(panel, records, "ARES", (18, 20, 132, 62), (206, 142), max_size=8)
    add_panel_label(panel, records, "ALCIPPE", (18, 192, 146, 234), (126, 142), max_size=8)
    add_panel_label(panel, records, "COUNCIL OF JUDGES", (420, 20, 616, 62), (416, 126), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, WORKSHOP_ART, TRIAL_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.21.4",
            TITLE_FONT,
            max_size=27,
            min_size=18,
            padding=10,
            name="passage:title",
            align="center",
            spacing_ratio=0.07,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (28, 88, passage_panel.width - 28, 424),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=5,
            name="passage:translation",
            spacing_ratio=0.06,
        )
    )
    note_rect = (24, 436, 354, 524)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias supplies the route, grave, kinship, flight stages, sanctuary contents, spring, killing tradition, and first-trial claim. Architecture, objects, clothing, and trial scene are reconstructed.",
            BODY_FONT,
            max_size=10,
            min_size=7,
            padding=7,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.055,
        )
    )
    passage_panel.alpha_composite(make_flight_strip(records), (20, 534))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (650, 40, 1164, 98)
    paste_with_shadow(
        page,
        make_label(
            "THE ROAD TO ASCLEPIUS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=14,
            min_size=9,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("THEATRE OF DIONYSUS", (438, 540, 646, 586), (548, 522), 8),
        ("ROAD TO ACROPOLIS", (438, 374, 628, 420), (842, 456), 8),
        ("KALOS' GRAVE", (620, 470, 766, 516), (736, 418), 8),
        ("ASCLEPIEION", (1036, 182, 1204, 228), (1080, 310), 9),
        ("ASCLEPIUS AND CHILDREN", (1122, 292, 1348, 340), (1130, 356), 7),
        ("VOTIVE PAINTINGS", (820, 204, 1000, 250), (938, 314), 8),
        ("SACRED SPRING", (1156, 518, 1336, 566), (1244, 520), 8),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    sequence_rect = (656, 612, 1164, 658)
    paste_with_shadow(
        page,
        make_label(
            "THEATRE · KALOS' GRAVE · ASCLEPIEION · ACROPOLIS",
            sequence_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        sequence_rect[:2],
    )

    paste_with_shadow(page, make_workshop_panel(records), (28, 700))
    paste_with_shadow(page, make_trial_panel(records), (718, 700))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "translation_font_size": next(
            record.font_size for record in records if record.name == "passage:translation"
        ),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/21/3.png"],
        "evidence_boundary": "Pausanias supplies the road endpoints, Kalos' burial and kinship, Daedalus' flight stages, the sanctuary contents and spring, and the killing and first-trial traditions. Architecture, grave form, statue and painting arrangement, route geometry, clothing, activity, lighting, and trial composition are reconstructed. The assault and killing are not depicted.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated south-slope ascent reconstruction with theatre, road, grave, Asclepieion, statues, paintings, spring, and Acropolis wall.",
            },
            {
                "path": str(WORKSHOP_ART),
                "description": "Generated pre-crime workshop scene of fully clothed Daedalus and Kalos with craft tools.",
            },
            {
                "path": str(TRIAL_ART),
                "description": "Generated non-graphic Areopagus trial scene with fully clothed Ares, Alcippe, and council.",
            },
            {
                "path": str(RELIEF_ART),
                "description": "Generated central and eastern Mediterranean relief used as a subordinate Athens-Crete-Sicily orientation strip.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_21_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/21/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
