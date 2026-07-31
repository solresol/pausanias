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


PASSAGE_ID = "1.14.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_14_5"
MAIN_ART = ASSET_DIR / "main_eukleia_temple.png"
AESCHYLUS_ART = ASSET_DIR / "aeschylus_memorial.png"
RELIEF_ART = ASSET_DIR / "attica_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_aeschylus_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(AESCHYLUS_ART, (480, 214), centering=(0.50, 0.48)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Near life's end, Aeschylus made Marathon and the Persians witnesses to his valor.",
        86,
        "aeschylus:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    face = (202, 66)
    rect = (326, 26, 500, 62)
    draw_leader(draw, face, (rect[0], (rect[1] + rect[3]) // 2))
    panel.alpha_composite(
        make_label(
            "AESCHYLUS",
            rect,
            records,
            font_path=TITLE_FONT,
            max_size=11,
            min_size=8,
        ),
        rect[:2],
    )
    return panel


def make_orientation_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((400, 344))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THE FOUR PLACES",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="orientation:title",
            align="center",
            spacing_ratio=0.06,
        )
    )

    art = Image.open(RELIEF_ART).convert("RGB")
    art.thumbnail((168, 252), Image.Resampling.LANCZOS)
    art = warm_art(art, grain_strength=0.006)
    art_xy = (18, 74)
    panel.paste(art, art_xy)
    draw.rectangle(
        (art_xy[0], art_xy[1], art_xy[0] + art.width, art_xy[1] + art.height),
        outline=RULE,
        width=2,
    )

    points = [
        ("ARTEMISIUM", (142, 114), (204, 78, 382, 118)),
        ("MARATHON", (150, 226), (204, 140, 382, 180)),
        ("ATHENS", (108, 258), (204, 202, 382, 242)),
        ("SALAMIS", (74, 272), (204, 264, 382, 304)),
    ]
    for text, point, rect in points:
        endpoint = (rect[0], (rect[1] + rect[3]) // 2)
        draw.line((point, endpoint), fill="#f4e5bd", width=4)
        draw.line((point, endpoint), fill="#6f5130", width=2)
        draw.ellipse(
            (point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4),
            fill="#7d4c28",
            outline="#f4e5bd",
            width=1,
        )
        panel.alpha_composite(
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=9,
                min_size=7,
            ),
            rect[:2],
        )
    return panel


def make_memorial_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((406, 344))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "WHAT THE MEMORIAL CHOSE",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="memorial:title",
            align="center",
            spacing_ratio=0.06,
        )
    )

    entries = [
        (
            "NAMED",
            "His name, his father's name, his city, the grove at Marathon, and the Persians.",
        ),
        (
            "UNSAID",
            "His poetic fame, the fighting at Artemisium, and the naval battle at Salamis.",
        ),
    ]
    for index, (name, note) in enumerate(entries):
        y0 = 76 + index * 98
        y1 = y0 + 84
        draw.rounded_rectangle(
            (22, y0, 384, y1),
            radius=9,
            fill="#f4dfb2",
            outline="#9c7443",
            width=2,
        )
        records.append(
            draw_fitted_text(
                draw,
                (30, y0 + 6, 132, y1 - 6),
                name,
                DISPLAY_FONT,
                max_size=13,
                min_size=9,
                padding=4,
                name=f"memorial:name:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (140, y0 + 6, 376, y1 - 6),
                note,
                BODY_FONT,
                max_size=11,
                min_size=8,
                padding=5,
                name=f"memorial:note:{index}",
                align="center",
                spacing_ratio=0.08,
            )
        )
    records.append(
        draw_fitted_text(
            draw,
            (32, 282, 374, 328),
            "For Pausanias, Marathon eclipsed every other achievement.",
            BODY_FONT,
            max_size=11,
            min_size=8,
            padding=5,
            name="memorial:conclusion",
            align="center",
            spacing_ratio=0.08,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, AESCHYLUS_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 720))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(
        title_rect,
        radius=12,
        fill="#ead2a0",
        outline=RULE,
        width=2,
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.14.5",
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

    art = warm_art(
        crop_to_fill(MAIN_ART, (944, 620), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((972, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 958, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (416, 22))

    callouts = [
        ("ATHENS — THE ACROPOLIS", (450, 42, 724, 88), (672, 168)),
        ("TEMPLE OF EUKLEIA", (1082, 42, 1352, 88), (1162, 178)),
        ("MARATHON RELIEF", (454, 374, 674, 420), (744, 354)),
        ("PERSIAN SPOILS", (456, 586, 666, 632), (560, 528)),
    ]
    for text, rect, point in callouts:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=13,
                min_size=8,
            ),
            rect[:2],
        )

    paste_with_shadow(page, make_aeschylus_panel(records), (28, 760))
    paste_with_shadow(page, make_orientation_panel(records), (558, 760))
    paste_with_shadow(page, make_memorial_panel(records), (972, 760))

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
        "continuity_reference_pages": ["graphic_book/images/1/14/4.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9024-49c9-7b12-8d8c-8be9d74bfa68/call_DznnsZ8HYfIy09sKDdLCdLfK.png",
                "description": "Generated Temple of Eukleia reconstruction with Marathon spoils and votive relief.",
            },
            {
                "path": str(AESCHYLUS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9024-49c9-7b12-8d8c-8be9d74bfa68/call_t43paXRrQpElBh8UU6O46n1B.png",
                "description": "Generated memorial scene of Aeschylus, shield, blank stele, grove, and Persian landing.",
            },
            {
                "path": str(RELIEF_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9024-49c9-7b12-8d8c-8be9d74bfa68/call_YTXdT2vGmGBsWoHbfKeNAzBH.png",
                "description": "Generated unlabeled painterly relief base for Attica, Euboea, and the Saronic Gulf.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_14_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/14/5.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
