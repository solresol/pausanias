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
    PARCHMENT_DEEP,
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    draw_fitted_text,
    draw_leader,
    draw_polyline_leader,
    framed_panel,
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    make_compact_callout,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.13.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_4"
MAIN_ART = ASSET_DIR / "main_cleonymus_pyrrhus_sparta.png"
LOCATOR_ART = ASSET_DIR / "epirus_laconia_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_route_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((408, 332))
    draw = ImageDraw.Draw(panel)
    title = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "FROM EPIRUS TO LACONIA",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    rect = (22, 70, panel.width - 22, 236)
    art = warm_art(
        crop_to_fill(LOCATOR_ART, (rect[2] - rect[0], rect[3] - rect[1]), centering=(0.50, 0.53)),
        grain_strength=0.012,
    )
    panel.paste(art, rect[:2])
    draw.rounded_rectangle(rect, radius=12, outline="#8d693f", width=2)

    points = [(94, 112), (174, 104), (254, 166), (306, 206)]
    draw.line(points, fill="#f5ead2", width=7)
    draw.line(points, fill="#7c4033", width=3)
    for x, y in points:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#734737", outline="#f7e8c7", width=2)

    labels = [
        ("EPIRUS", (42, 82, 116, 106)),
        ("MACEDONIA", (128, 74, 226, 100)),
        ("CORINTH", (218, 138, 292, 164)),
        ("SPARTA", (286, 204, 364, 230)),
    ]
    for index, (text, label_rect) in enumerate(labels):
        draw.rounded_rectangle(label_rect, radius=7, fill="#f4dfb2", outline="#9c7443", width=1)
        records.append(
            draw_fitted_text(
                draw,
                label_rect,
                text,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=3,
                name=f"locator:label:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
    records.append(
        draw_fitted_text(
            draw,
            (24, 248, panel.width - 24, panel.height - 14),
            "Cleonymus turned Pyrrhus away from Macedonian affairs and south into his own Lacedaemonian homeland.",
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="locator:caption",
            align="center",
            spacing_ratio=0.09,
        )
    )
    return panel


def make_genealogy_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title = (24, 16, panel.width - 24, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "THE SPARTAN ROYAL LINE",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="genealogy:title",
            align="center",
            spacing_ratio=0.06,
        )
    )

    records.append(
        draw_fitted_text(
            draw,
            (28, 66, 220, 88),
            "DESCENT",
            DISPLAY_FONT,
            max_size=9,
            min_size=6,
            padding=2,
            name="genealogy:descent-header",
            align="center",
            spacing_ratio=0.04,
        )
    )
    records.append(
        draw_fitted_text(
            draw,
            (238, 66, 424, 88),
            "SUCCESSION",
            DISPLAY_FONT,
            max_size=9,
            min_size=6,
            padding=2,
            name="genealogy:succession-header",
            align="center",
            spacing_ratio=0.04,
        )
    )
    boxes = [
        ("CLEOMBROTUS", "fell at Leuctra", (34, 90, 214, 134)),
        ("PAUSANIAS", "led at Plataea", (34, 158, 214, 202)),
        ("PLEISTOANAX", "son of Pausanias", (34, 226, 214, 270)),
        ("AGESIPOLIS", "died childless", (244, 108, 418, 154)),
        ("CLEOMENES", "inherited kingship", (244, 210, 418, 256)),
    ]
    draw.line((124, 134, 124, 158), fill="#815b36", width=3)
    draw.line((124, 202, 124, 226), fill="#815b36", width=3)
    draw.line((331, 154, 331, 210), fill="#815b36", width=3)
    draw.polygon([(325, 202), (337, 202), (331, 210)], fill="#815b36")
    for index, (name, note, rect) in enumerate(boxes):
        draw.rounded_rectangle(rect, radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (rect[0] + 4, rect[1] + 3, rect[2] - 4, rect[1] + 22),
                name,
                DISPLAY_FONT,
                max_size=10,
                min_size=6,
                padding=1,
                name=f"genealogy:name:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (rect[0] + 5, rect[1] + 21, rect[2] - 5, rect[3] - 3),
                note,
                BODY_FONT,
                max_size=10,
                min_size=7,
                padding=1,
                name=f"genealogy:note:{index}",
                align="center",
                spacing_ratio=0.05,
            )
        )
    records.append(
        draw_fitted_text(
            draw,
            (34, 284, panel.width - 34, panel.height - 14),
            "The passage shifts from descent to the transfer of kingship.",
            BODY_FONT,
            max_size=10,
            min_size=7,
            padding=3,
            name="genealogy:footer",
            align="center",
            spacing_ratio=0.07,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, LOCATOR_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    main_rect = (430, 36, 1374, 628)
    art = warm_art(
        crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.51)),
        grain_strength=0.012,
    )
    main_panel = framed_panel((art.width + 28, art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + art.width, 14 + art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left = framed_panel((378, 706))
    left_draw = ImageDraw.Draw(left)
    title_band = (18, 14, left.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.13.4",
            TITLE_FONT,
            max_size=29,
            min_size=18,
            padding=10,
            name="panel:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            left_draw,
            (24, 92, left.width - 24, left.height - 24),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left, (32, 36))

    title_rect = (640, 54, 1248, 116)
    paste_with_shadow(
        page,
        make_label("AN EXILE LEADS THE WAY", title_rect, records, font_path=TITLE_FONT, max_size=20, min_size=10),
        title_rect[:2],
    )
    labels = [
        ("PYRRHUS", (488, 230, 620, 274), (700, 382)),
        ("CLEONYMUS", (650, 230, 816, 274), (798, 382)),
        ("SPARTA", (946, 338, 1084, 382), (1032, 420)),
        ("EUROTAS VALLEY", (1000, 478, 1228, 524), (1056, 502)),
        ("TAYGETUS", (1152, 170, 1320, 216), (1192, 278)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=12, min_size=7),
            rect[:2],
        )

    note1 = make_compact_callout(
        "A Lacedaemonian exile brings a foreign army into his own country.",
        (440, 86),
        "callout:betrayal",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(448, 652), (580, 588), (704, 422)])
    paste_with_shadow(page, note1, (448, 642))
    note2 = make_compact_callout(
        "The open valley makes the approach to unwalled Sparta legible at a glance.",
        (448, 86),
        "callout:orientation",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 652), (1028, 590), (1040, 442)])
    paste_with_shadow(page, note2, (904, 642))

    paste_with_shadow(page, make_route_locator(records), (32, 780))

    leaders_crop = warm_art(
        crop_to_fill(MAIN_ART, (420, 202), source_box=(0, 260, 850, 960), centering=(0.50, 0.52)),
        grain_strength=0.014,
    )
    inset = make_inset_panel(
        leaders_crop,
        "Cleonymus points into Laconia while Pyrrhus weighs the road and the prize before him.",
        92,
        "inset:leaders-caption",
        records,
    )
    paste_with_shadow(page, inset, (450, 780))
    inset_label = (548, 800, 776, 836)
    draw_leader(draw, (662, 920), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("THE GUIDE AND THE KING", inset_label, records, font_path=BODY_FONT, max_size=11, min_size=7),
        inset_label[:2],
    )

    paste_with_shadow(page, make_genealogy_panel(records), (904, 780))
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
        "continuity_reference_pages": ["graphic_book/images/1/13/3.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f5ca3-3790-7f50-9c30-9aeb156a8861/exec-c87685ad-b22c-40ad-8bc6-a61f23db9a17.png",
                "description": "Generated raster scene of Cleonymus directing Pyrrhus toward Sparta.",
            },
            {
                "path": str(LOCATOR_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f5ca3-3790-7f50-9c30-9aeb156a8861/exec-db330eec-2150-4916-8a46-10f03f2658bf.png",
                "description": "Generated raster relief base for the Epirus-to-Laconia locator.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_13_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/13/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
