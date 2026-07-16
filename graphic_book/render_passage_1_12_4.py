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

from PIL import Image, ImageDraw, ImageFilter, ImageOps

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
from graphic_book.render_passage_1_10_1 import crop_to_fill, make_compact_callout, validate_fit_records, warm_art


PASSAGE_ID = "1.12.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_12_4"
MAIN_ART = ASSET_DIR / "main_ivory_elephant_knowledge.png"


def load_translation() -> str:
    db_path = root_dir() / "pausanias.sqlite"
    if not db_path.exists():
        raise RuntimeError(f"Missing local SQLite database: {db_path}")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_knowledge_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((392, 332))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "KNOWLEDGE ROUTES",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 226)
    size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(size, 33).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#74613d", white="#efd9a2")
    sea_noise = Image.effect_noise(size, 18).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#446d78", white="#adc1b7")
    mask = Image.new("L", size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (146, 0), (132, 40), (92, 68), (82, 112), (0, 136)], fill=224)
    mdraw.polygon([(124, 28), (332, 6), (332, 152), (186, 152), (160, 112), (182, 70)], fill=230)
    mdraw.polygon([(0, 120), (88, 110), (134, 152), (0, 152)], fill=220)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "GREECE": (map_rect[0] + 82, map_rect[1] + 80),
        "ASIA": (map_rect[0] + 164, map_rect[1] + 66),
        "INDIA": (map_rect[0] + 282, map_rect[1] + 82),
        "LIBYA": (map_rect[0] + 92, map_rect[1] + 130),
    }
    route = [points["GREECE"], points["ASIA"], points["INDIA"]]
    draw.line(route, fill="#704737", width=4)
    draw.line(route, fill="#f4ead6", width=1)
    draw.line((points["GREECE"], points["LIBYA"]), fill="#6a5538", width=3)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("GREECE", (44, 128, 124, 152), "locator:greece"),
        ("ASIA", (150, 108, 208, 132), "locator:asia"),
        ("INDIA", (252, 140, 316, 164), "locator:india"),
        ("LIBYA", (58, 188, 126, 212), "locator:libya"),
        ("SEA", (170, 188, 224, 212), "locator:sea"),
    ]
    for text, rect, name in labels:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=8,
                min_size=5,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.04,
            )
        )

    caption = "Ivory was familiar in Greek luxury, but living elephants belonged to India, Libya, and the lands beyond ordinary Greek sight."
    records.append(
        draw_fitted_text(
            draw,
            (22, 258, panel.width - 22, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="locator:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def make_evidence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "PAUSANIAS' ARGUMENT",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="evidence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("IVORY", "Known through craft, luxury, couches, and decorated houses."),
        ("ANIMAL", "Unknown to Greeks before the Macedonian invasion of Asia."),
        ("HOMER", "Names ivory wealth, but never describes the elephant itself."),
        ("BOUNDARY", "India and Libya mark the living animal's familiar world."),
    ]
    y = 78
    for idx, (name, note) in enumerate(rows):
        row_rect = (24, y, panel.width - 24, y + 52)
        draw.rounded_rectangle(
            row_rect,
            radius=9,
            fill="#f3dfb4" if idx % 2 == 0 else "#f7e8c8",
            outline="#b8945a",
            width=1,
        )
        name_rect = (34, y + 7, 148, y + 45)
        note_rect = (160, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=10,
                min_size=6,
                padding=2,
                name=f"evidence:name:{idx}",
                align="center",
                spacing_ratio=0.05,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                note_rect,
                note,
                BODY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"evidence:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not MAIN_ART.exists():
        raise RuntimeError(f"Missing generated art asset: {MAIN_ART}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        source_box=(0, 0, 1536, 690),
        centering=(0.51, 0.49),
    )
    main_art = warm_art(main_art, grain_strength=0.014)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 720)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.12.4",
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
            (24, 92, left_panel.width - 24, left_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=16,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (646, 54, 1270, 116)
    paste_with_shadow(
        page,
        make_label("IVORY KNOWN, ELEPHANT UNKNOWN", title_rect, records, font_path=TITLE_FONT, max_size=19, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("IVORY CRAFT", (548, 152, 742, 200), (578, 492), 13),
        ("HOMERIC EVIDENCE", (748, 150, 990, 198), (760, 406), 13),
        ("ASIA ROUTE", (928, 332, 1090, 378), (1026, 314), 12),
        ("DISTANT ELEPHANT", (1130, 152, 1322, 200), (1244, 226), 12),
        ("NOT YET SEEN IN GREECE", (1048, 514, 1324, 562), (1224, 438), 12),
    ]
    for text, rect, point, max_size in label_specs:
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        else:
            endpoint = (rect[0] if point[0] < rect[0] else rect[2], rect[1] + (rect[3] - rect[1]) // 2)
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=max_size, min_size=7),
            (rect[0], rect[1]),
        )

    craft_note = make_compact_callout(
        "Pausanias separates familiar ivory objects from direct knowledge of the living beast.",
        (446, 88),
        "callout:craft",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(456, 652), (530, 610), (578, 492)])
    paste_with_shadow(page, craft_note, (456, 642))

    homer_note = make_compact_callout(
        "Homer can mention ivory wealth without ever naming the animal that produced it.",
        (448, 88),
        "callout:homer",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 652), (820, 548), (760, 406)])
    paste_with_shadow(page, homer_note, (904, 642))

    locator_panel = make_knowledge_locator(records)
    paste_with_shadow(page, locator_panel, (32, 760))

    ivory_crop = crop_to_fill(
        MAIN_ART,
        (420, 202),
        source_box=(0, 250, 650, 860),
        centering=(0.48, 0.38),
    )
    ivory_crop = warm_art(ivory_crop, grain_strength=0.018)
    ivory_panel = make_inset_panel(
        ivory_crop,
        "The passage begins with the familiar material: ivory already moved through craft, luxury, and poetry.",
        92,
        "inset:ivory-caption",
        records,
    )
    paste_with_shadow(page, ivory_panel, (438, 760))
    inset_label = (526, 780, 778, 816)
    draw_leader(draw, (640, 900), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("CRAFT BEFORE ENCOUNTER", inset_label, records, font_path=BODY_FONT, max_size=12, min_size=6),
        (inset_label[0], inset_label[1]),
    )

    evidence_panel = make_evidence_panel(records)
    paste_with_shadow(page, evidence_panel, (904, 760))

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
        "continuity_reference_pages": [
            "graphic_book/images/1/12/3.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f42e3-d1a7-71d1-8d30-f7f0aad6906c/ig_0f7be39ca114083d016a4e90a4d2388191b8b648bcce71234a.png",
                "description": "Generated raster main panel showing Greek ivory craft and a remote eastward elephant horizon.",
            }
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_12_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "12" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
