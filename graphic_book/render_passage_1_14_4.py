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
    DISPLAY_FONT,
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


PASSAGE_ID = "1.14.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_14_4"
MAIN_ART = ASSET_DIR / "main_temple_forecourt.png"
CAVE_ART = ASSET_DIR / "cave_sleep.png"
RELIEF_ART = ASSET_DIR / "southern_greece_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_cave_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(CAVE_ART, (460, 214), centering=(0.52, 0.50)), grain_strength=0.008)
    panel = make_inset_panel(
        art,
        "In the Cretan countryside, Epimenides entered a cave and slept until the fortieth year.",
        86,
        "cave:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    point = (346, 132)
    rect = (286, 26, 468, 62)
    draw_leader(draw, point, (rect[0] + 24, rect[3]))
    panel.alpha_composite(
        make_label("FORTY YEARS ASLEEP", rect, records, font_path=TITLE_FONT, max_size=10, min_size=7),
        rect[:2],
    )
    return panel


def make_orientation_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((430, 344))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "CRETE, ATHENS, AND SPARTA",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="orientation:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    art = warm_art(crop_to_fill(RELIEF_ART, (402, 244), centering=(0.50, 0.52)), grain_strength=0.006)
    panel.paste(art, (14, 68))
    draw.rectangle((14, 68, 416, 312), outline=RULE, width=2)

    # Points are measured against the generated relief base and then labeled locally.
    places = [
        ("SPARTA", (142, 154), (82, 124, 160, 148)),
        ("ATHENS", (292, 128), (300, 94, 400, 120)),
        ("GORTYN", (205, 270), (134, 278, 226, 304)),
        ("KNOSSOS", (246, 260), (248, 276, 352, 302)),
    ]
    for text, point, rect in places:
        draw.line((point, ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)), fill="#f4e5bd", width=2)
        draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill="#7d4c28", outline="#f4e5bd", width=1)
        panel.alpha_composite(
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )
    return panel


def make_comparison_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((406, 344))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "TWO CRETAN PURIFIERS",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="comparison:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    entries = [
        ("EPIMENIDES", "From Knossos. Poet and purifier of cities, including Athens."),
        ("THALES", "From Gortyn. He ended the plague among the Spartans."),
    ]
    for index, (name, note) in enumerate(entries):
        y0 = 76 + index * 96
        y1 = y0 + 82
        draw.rounded_rectangle((22, y0, 384, y1), radius=9, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (30, y0 + 6, 150, y1 - 6),
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=8,
                padding=4,
                name=f"comparison:name:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (158, y0 + 6, 376, y1 - 6),
                note,
                BODY_FONT,
                max_size=11,
                min_size=8,
                padding=5,
                name=f"comparison:note:{index}",
                align="center",
                spacing_ratio=0.08,
            )
        )
    records.append(
        draw_fitted_text(
            draw,
            (32, 278, 374, 326),
            "Pausanias insists: neither kin nor from the same city.",
            BODY_FONT,
            max_size=12,
            min_size=9,
            padding=5,
            name="comparison:distinction",
            align="center",
            spacing_ratio=0.08,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, CAVE_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 720))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.14.4",
            TITLE_FONT,
            max_size=28,
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
            (26, 96, passage_panel.width - 26, passage_panel.height - 28),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=10,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.11,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    art = warm_art(crop_to_fill(MAIN_ART, (944, 620), centering=(0.50, 0.50)), grain_strength=0.006)
    art_panel = framed_panel((972, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 958, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (416, 22))

    callouts = [
        ("ATHENS — THE ACROPOLIS", (450, 42, 714, 88), (632, 208)),
        ("THE TEMPLE FORECOURT", (1084, 42, 1352, 88), (1230, 194)),
        ("BRONZE OX", (456, 586, 636, 632), (584, 438)),
        ("SEATED EPIMENIDES", (1110, 578, 1350, 630), (1094, 382)),
    ]
    for text, rect, point in callouts:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=13, min_size=8),
            rect[:2],
        )

    paste_with_shadow(page, make_cave_panel(records), (28, 760))
    paste_with_shadow(page, make_orientation_panel(records), (532, 760))
    paste_with_shadow(page, make_comparison_panel(records), (970, 760))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/14/3.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f8afc-6000-7503-9bcc-576ab4002935/exec-0db5d6f3-e483-428c-852f-eee5ebffeed7.png",
                "description": "Generated Athenian temple forecourt with the bronze ox and seated Epimenides monuments.",
            },
            {
                "path": str(CAVE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f8afc-6000-7503-9bcc-576ab4002935/exec-2224598d-3adf-4623-8964-055a30a5b2e9.png",
                "description": "Generated Cretan cave scene of Epimenides's forty-year sleep.",
            },
            {
                "path": str(RELIEF_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f8afc-6000-7503-9bcc-576ab4002935/exec-603bd8f2-5768-4791-a982-6194e4c1448a.png",
                "description": "Generated unlabeled painterly relief base of southern Greece and Crete.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_14_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/14/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
