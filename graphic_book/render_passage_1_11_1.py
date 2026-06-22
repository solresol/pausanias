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

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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


PASSAGE_ID = "1.11.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_11_1"
MAIN_ART = ASSET_DIR / "main_pyrrhus_statue_athens.png"
EPIRUS_ART = ASSET_DIR / "pyrrhus_epirus_settlement.png"


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


def make_epirus_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "AEACID ROUTES",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 226)
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(map_size, 34).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#69593b", white="#efd7a0")
    sea_noise = Image.effect_noise(map_size, 16).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#416878", white="#aab9ad")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 8), (114, 4), (164, 42), (136, 88), (70, 120), (0, 150)], fill=226)
    mdraw.polygon([(150, 18), (328, 0), (328, 152), (194, 144), (210, 88), (180, 54)], fill=230)
    mdraw.polygon([(0, 116), (126, 100), (198, 124), (328, 104), (328, 152), (0, 152)], fill=222)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.052)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "TROY": (map_rect[0] + 268, map_rect[1] + 88),
        "EPIRUS": (map_rect[0] + 92, map_rect[1] + 92),
        "DELPHI": (map_rect[0] + 144, map_rect[1] + 126),
        "THESSALY": (map_rect[0] + 158, map_rect[1] + 70),
        "ATHENS": (map_rect[0] + 188, map_rect[1] + 132),
    }
    route = [points["TROY"], (map_rect[0] + 210, map_rect[1] + 116), points["EPIRUS"]]
    draw.line(route, fill="#7b493a", width=4)
    draw.line(route, fill="#f2dfb8", width=1)
    draw.line([points["EPIRUS"], points["DELPHI"], points["ATHENS"]], fill="#4d5f5d", width=3)
    draw.line((map_rect[0] + 40, map_rect[1] + 112, map_rect[0] + 300, map_rect[1] + 116), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("EPIRUS", (48, 140, 118, 164), "locator:epirus"),
        ("TROY", (252, 122, 306, 146), "locator:troy"),
        ("DELPHI", (122, 182, 190, 206), "locator:delphi"),
        ("ATHENS", (188, 194, 266, 218), "locator:athens"),
        ("THESSALY", (130, 98, 220, 122), "locator:thessaly"),
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

    caption = "The first Pyrrhus avoids Thessaly, settles in Epirus, and the later statue stands in Athens."
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


def make_lineage_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "PYRRHUS' LINEAGE",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="lineage:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("ATHENS", "A statue honors Pyrrhus of Epirus."),
        ("AEACIDES", "His father links him to Arybbas and Alcetas."),
        ("OLYMPIAS", "Alexander is kin only through the older Aeacid line."),
        ("AFTER TROY", "The first Pyrrhus settles in Epirus by Helenus' oracle."),
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
        name_rect = (34, y + 7, 160, y + 45)
        note_rect = (174, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"lineage:name:{idx}",
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
                name=f"lineage:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, EPIRUS_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.48, 0.50),
    )
    main_art = warm_art(ImageEnhance.Contrast(main_art).enhance(1.02), grain_strength=0.014)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 726)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.11.1",
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
            max_size=15,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.10,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (800, 54, 1288, 116)
    paste_with_shadow(
        page,
        make_label("PYRRHUS IN ATHENS", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("BRONZE PYRRHUS", (500, 430, 752, 478), (696, 282), 17),
        ("ATHENS", (1042, 132, 1216, 180), (1116, 258), 18),
        ("AEACID SHIELD", (716, 536, 944, 582), (656, 452), 15),
        ("ACROPOLIS", (1080, 286, 1288, 332), (1104, 236), 16),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    statue_note = make_compact_callout(
        "Pausanias turns from Lysimachus to the Athenian statue of Pyrrhus.",
        (426, 88),
        "callout:statue",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(458, 650), (562, 542), (696, 282)])
    paste_with_shadow(page, statue_note, (458, 642))

    lineage_note = make_compact_callout(
        "His kinship with Alexander is only through the older Aeacid house.",
        (462, 88),
        "callout:lineage",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(906, 650), (756, 596), (656, 452)])
    paste_with_shadow(page, lineage_note, (896, 642))

    locator_panel = make_epirus_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    epirus_crop = crop_to_fill(EPIRUS_ART, (420, 198), centering=(0.44, 0.50))
    epirus_crop = warm_art(epirus_crop, grain_strength=0.018)
    epirus_panel = make_inset_panel(
        epirus_crop,
        "After Troy, the first Pyrrhus accepts Helenus' oracle and settles in Epirus.",
        94,
        "inset:epirus-caption",
        records,
    )
    paste_with_shadow(page, epirus_panel, (440, 756))
    inset_label = (504, 774, 802, 810)
    draw_leader(draw, (684, 870), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("HELENUS' ORACLE", inset_label, records, max_size=14, min_size=6), (inset_label[0], inset_label[1]))

    lineage_panel = make_lineage_panel(records)
    paste_with_shadow(page, lineage_panel, (904, 758))

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
            "graphic_book/images/1/10/4.png",
            "graphic_book/images/1/10/5.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ef07f-1152-7370-947a-0cb0ba00528c/ig_064d823cfbb03f44016a3978dcb0b08191a09f5982a9ce9a5a.png",
                "description": "Generated raster art for the bronze statue of Pyrrhus in Athens.",
            },
            {
                "path": str(EPIRUS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ef07f-1152-7370-947a-0cb0ba00528c/ig_064d823cfbb03f44016a3979a2dfc0819189b8380235278b59.png",
                "description": "Generated raster art for the first Pyrrhus settling in Epirus with Helenus and Andromache.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_11_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "11" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
