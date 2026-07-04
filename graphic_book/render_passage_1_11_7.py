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


PASSAGE_ID = "1.11.7"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_11_7"
MAIN_ART = ASSET_DIR / "main_pyrrhus_rome_threshold.png"
LUCANIA_ART = ASSET_DIR / "alexander_lucania_inset.png"


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


def make_italy_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "GREECE TO ITALY",
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
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(map_size, 33).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#76653f", white="#efd8a1")
    sea_noise = Image.effect_noise(map_size, 15).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#416975", white="#adc2bd")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (116, 0), (104, 38), (82, 76), (94, 114), (64, 152), (0, 152)], fill=224)
    mdraw.polygon([(184, 0), (292, 0), (276, 34), (250, 58), (260, 96), (214, 134), (166, 152), (154, 116), (184, 76)], fill=228)
    mdraw.polygon([(258, 92), (328, 82), (328, 152), (254, 152), (238, 126)], fill=225)
    mdraw.ellipse((70, 106, 138, 154), fill=214)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 78, map_rect[1] + 80),
        "LUCANIA": (map_rect[0] + 216, map_rect[1] + 118),
        "ROME": (map_rect[0] + 236, map_rect[1] + 34),
        "SYRACUSE": (map_rect[0] + 114, map_rect[1] + 136),
        "IONIAN": (map_rect[0] + 148, map_rect[1] + 104),
    }
    draw.line([points["EPIRUS"], points["LUCANIA"], points["ROME"]], fill="#704235", width=4)
    draw.line([points["EPIRUS"], points["LUCANIA"], points["ROME"]], fill="#f4ead6", width=1)
    draw.line([points["EPIRUS"], points["SYRACUSE"]], fill="#4f6870", width=4)
    draw.line([points["EPIRUS"], points["SYRACUSE"]], fill="#f4ead6", width=1)
    draw.line((map_rect[0] + 90, map_rect[1] + 112, map_rect[0] + 214, map_rect[1] + 112), fill="#416b75", width=4)
    for point in points.values():
        x, y = point
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("EPIRUS", (52, 126, 126, 150), "locator:epirus"),
        ("IONIAN", (126, 172, 204, 196), "locator:ionian"),
        ("LUCANIA", (210, 178, 302, 202), "locator:lucania"),
        ("ROME", (232, 98, 292, 122), "locator:rome"),
        ("SYRACUSE", (76, 206, 176, 230), "locator:syracuse"),
    ]
    for text, rect, name in label_specs:
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

    caption = "Pausanias frames Pyrrhus as the first Greek whose westward war reaches Rome."
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


def make_precedent_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "BEFORE PYRRHUS",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="precedent:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("DIOMEDES", "No later battle is told between Diomedes' Argives and Aeneas."),
        ("ATHENS", "Athenian hopes for Italy stop at the disaster before Syracuse."),
        ("ALEXANDER", "Neoptolemus' son dies among the Lucanians before Rome."),
        ("PYRRHUS", "The first Greek war against the Romans now comes into view."),
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
        name_rect = (34, y + 7, 154, y + 45)
        note_rect = (166, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"precedent:name:{idx}",
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
                name=f"precedent:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, LUCANIA_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 634)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.48),
    )
    main_art = warm_art(main_art, grain_strength=0.014)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 716)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.11.7",
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
            max_size=18,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (690, 54, 1248, 116)
    paste_with_shadow(
        page,
        make_label("PYRRHUS AND ROME", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PYRRHUS", (536, 154, 724, 202), (590, 342), 17),
        ("IONIAN SEA", (750, 508, 980, 556), (828, 404), 15),
        ("SOUTHERN ITALY", (1054, 426, 1302, 474), (1112, 374), 15),
        ("ROMAN POWER", (1088, 150, 1326, 198), (1214, 238), 15),
        ("WESTWARD ROUTE", (804, 250, 1076, 298), (902, 368), 15),
    ]
    for text, rect, point, max_size in label_specs:
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        else:
            endpoint = (rect[0] if point[0] < rect[0] else rect[2], rect[1] + (rect[3] - rect[1]) // 2)
        draw_leader(draw, point, endpoint)
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    first_war_note = make_compact_callout(
        "Pausanias says no Greek before Pyrrhus had carried war against the Romans.",
        (408, 88),
        "callout:first-war",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(456, 654), (548, 612), (700, 604), (590, 342)])
    paste_with_shadow(page, first_war_note, (456, 642))

    limits_note = make_compact_callout(
        "Earlier western ambitions stop short: Syracuse blocks Athens, and Alexander dies in Lucania.",
        (466, 90),
        "callout:limits",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 654), (1032, 604), (1148, 444)])
    paste_with_shadow(page, limits_note, (898, 642))

    locator_panel = make_italy_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    lucania_crop = crop_to_fill(LUCANIA_ART, (420, 198), centering=(0.52, 0.52))
    lucania_crop = warm_art(lucania_crop, grain_strength=0.018)
    lucania_panel = make_inset_panel(
        lucania_crop,
        "Alexander of Epirus reaches Lucanian country, but not a Roman battle.",
        94,
        "inset:lucania-caption",
        records,
    )
    paste_with_shadow(page, lucania_panel, (440, 756))
    inset_label = (542, 774, 786, 810)
    draw_leader(draw, (716, 862), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("LUCANIAN LIMIT", inset_label, records, max_size=13, min_size=6), (inset_label[0], inset_label[1]))

    precedent_panel = make_precedent_panel(records)
    paste_with_shadow(page, precedent_panel, (904, 758))

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
            "graphic_book/images/1/11/5.png",
            "graphic_book/images/1/11/6.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f2e49-ff31-7a31-9642-fb068ed08e63/ig_0e46a5338eecc911016a494a9a6430819186e3197554f05bec.png",
                "description": "Generated raster main panel showing Pyrrhus looking west across the Ionian toward Italy and Rome's sphere.",
            },
            {
                "path": str(LUCANIA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f2e49-ff31-7a31-9642-fb068ed08e63/ig_0e46a5338eecc911016a494b5138b88191b145c103d82df3b8.png",
                "description": "Generated raster scenic inset showing Alexander of Epirus' Lucanian limit without gore.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_11_7_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "11" / "7.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
