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


PASSAGE_ID = "1.10.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_10_4"
MAIN_ART = ASSET_DIR / "main_lysandra_babylon_petition.png"
PERGAMUM_ART = ASSET_DIR / "philetaerus_pergamum_treasury.png"


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


def make_route_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "FLIGHT TO SELEUCUS",
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
    relief = Image.effect_noise(map_size, 30).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#705f3e", white="#efd6a0")
    sea_noise = Image.effect_noise(map_size, 17).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#436977", white="#9eb6ad")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 22), (118, 6), (168, 44), (132, 88), (74, 116), (0, 148)], fill=226)
    mdraw.polygon([(134, 16), (328, 0), (328, 152), (166, 150), (198, 104), (174, 62)], fill=230)
    mdraw.polygon([(0, 122), (108, 108), (206, 126), (328, 112), (328, 152), (0, 152)], fill=220)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.052)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "KINGDOM": (map_rect[0] + 56, map_rect[1] + 88),
        "EGYPT": (map_rect[0] + 94, map_rect[1] + 130),
        "PERGAMUM": (map_rect[0] + 164, map_rect[1] + 76),
        "BABYLON": (map_rect[0] + 282, map_rect[1] + 108),
    }
    route = [points["KINGDOM"], points["EGYPT"], points["BABYLON"]]
    pergamum_line = [points["PERGAMUM"], (map_rect[0] + 214, map_rect[1] + 86), points["BABYLON"]]
    draw.line(route, fill="#7b493a", width=4)
    draw.line(route, fill="#f2dfb8", width=1)
    draw.line(pergamum_line, fill="#4d5f5d", width=4)
    draw.line(pergamum_line, fill="#f2dfb8", width=1)
    draw.line((map_rect[0] + 42, map_rect[1] + 120, map_rect[0] + 306, map_rect[1] + 116), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("LYSIMACHUS", (38, 142, 140, 166), "locator:kingdom"),
        ("EGYPT", (64, 196, 122, 220), "locator:egypt"),
        ("PERGAMUM", (132, 120, 228, 144), "locator:pergamum"),
        ("BABYLON", (262, 168, 334, 192), "locator:babylon"),
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

    caption = "The fugitives and the Pergamum treasury both turn eastward toward Seleucus."
    records.append(
        draw_fitted_text(
            draw,
            (22, 260, panel.width - 22, panel.height - 14),
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


def make_turning_points_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "TWO APPEALS TO SELEUCUS",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="turning:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("LYSANDRA", "Flees with children and brothers after Agathocles is killed."),
        ("ALEXANDER", "A son of Lysimachus joins the flight eastward."),
        ("BABYLON", "The refugees urge Seleucus to make war."),
        ("PHILETAERUS", "Offers Pergamum and the treasury to Seleucus."),
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
                name=f"turning:name:{idx}",
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
                name=f"turning:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, PERGAMUM_ART]:
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
    main_art = warm_art(ImageEnhance.Contrast(main_art).enhance(1.02), grain_strength=0.015)
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
            "PASSAGE 1.10.4",
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
            max_size=17,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (610, 54, 1216, 116)
    paste_with_shadow(
        page,
        make_label("THE FLIGHT TO SELEUCUS", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("LYSANDRA", (710, 342, 886, 388), (815, 312), 18),
        ("CHILDREN IN FLIGHT", (590, 520, 874, 566), (748, 442), 14),
        ("SELEUCUS' COURT", (1032, 510, 1326, 556), (1192, 338), 15),
        ("BABYLON", (510, 140, 664, 186), (592, 228), 20),
        ("TRAVELING COMPANIONS", (470, 410, 792, 456), (612, 336), 14),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    petition_note = make_compact_callout(
        "At Babylon the fugitives press Seleucus to make war against Lysimachus.",
        (420, 88),
        "callout:petition",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(462, 648), (720, 594), (815, 312)])
    paste_with_shadow(page, petition_note, (462, 642))

    philetaerus_note = make_compact_callout(
        "The crisis spreads when Philetaerus offers Pergamum and its treasury to Seleucus.",
        (462, 90),
        "callout:philetaerus",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(906, 648), (1188, 592), (1192, 338)])
    paste_with_shadow(page, philetaerus_note, (894, 642))

    locator_panel = make_route_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    pergamum_crop = crop_to_fill(PERGAMUM_ART, (420, 198), centering=(0.47, 0.48))
    pergamum_crop = warm_art(pergamum_crop, grain_strength=0.018)
    pergamum_panel = make_inset_panel(
        pergamum_crop,
        "At Pergamum on the upper Caicus, Philetaerus turns the stronghold and treasury toward Seleucus.",
        94,
        "inset:pergamum-caption",
        records,
    )
    paste_with_shadow(page, pergamum_panel, (440, 756))
    pergamum_label = (518, 774, 790, 810)
    draw_leader(draw, (698, 876), (pergamum_label[0], pergamum_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("PERGAMUM TREASURY", pergamum_label, records, max_size=14, min_size=6),
        (pergamum_label[0], pergamum_label[1]),
    )

    turning_panel = make_turning_points_panel(records)
    paste_with_shadow(page, turning_panel, (904, 758))

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
            "graphic_book/images/1/10/1.png",
            "graphic_book/images/1/10/2.png",
            "graphic_book/images/1/10/3.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ee631-28d5-7222-beb5-f918cd6970f2/ig_01a569cfbf3ae8c7016a36d58a51548191b6940daccf8021a5.png",
                "description": "Generated raster art for Lysandra's flight and petition to Seleucus at Babylon.",
            },
            {
                "path": str(PERGAMUM_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ee631-28d5-7222-beb5-f918cd6970f2/ig_01a569cfbf3ae8c7016a36d62ab89c819188752f748d8b6a27.png",
                "description": "Generated raster art for Philetaerus controlling Pergamum's treasury and sending a herald to Seleucus.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_10_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "10" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

