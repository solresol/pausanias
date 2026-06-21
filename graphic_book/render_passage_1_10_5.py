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


PASSAGE_ID = "1.10.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_10_5"
MAIN_ART = ASSET_DIR / "main_lysimachus_seleucus_battle.png"
TOMB_ART = ASSET_DIR / "alexander_chersonese_tomb.png"


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
            "ASIA AND THE TOMB",
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
    relief = Image.effect_noise(map_size, 31).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#70623f", white="#efd6a0")
    sea_noise = Image.effect_noise(map_size, 17).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#3f6875", white="#9eb6ad")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (142, 0), (126, 44), (92, 72), (58, 100), (0, 118)], fill=224)
    mdraw.polygon([(0, 108), (112, 92), (178, 102), (328, 92), (328, 152), (0, 152)], fill=228)
    mdraw.polygon([(150, 0), (328, 0), (328, 84), (222, 72), (184, 44)], fill=220)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.05)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "THRACE": (map_rect[0] + 70, map_rect[1] + 42),
        "CHERSONESE": (map_rect[0] + 124, map_rect[1] + 78),
        "ASIA": (map_rect[0] + 224, map_rect[1] + 96),
        "BATTLE": (map_rect[0] + 274, map_rect[1] + 112),
    }
    crossing = [points["THRACE"], points["CHERSONESE"], points["ASIA"], points["BATTLE"]]
    draw.line(crossing, fill="#7b493a", width=4)
    draw.line(crossing, fill="#f2dfb8", width=1)
    draw.line((map_rect[0] + 40, map_rect[1] + 106, map_rect[0] + 308, map_rect[1] + 94), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("THRACE", (50, 112, 122, 136), "locator:thrace"),
        ("CHERSONESE", (104, 146, 218, 170), "locator:chersonese"),
        ("ASIA", (218, 126, 272, 150), "locator:asia"),
        ("BATTLE", (262, 172, 334, 196), "locator:battle"),
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

    caption = "Lysimachus crosses into Asia; Alexander returns him to the Chersonese tomb."
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


def make_aftermath_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "DEFEAT AND MEMORY",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="aftermath:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("CROSSED ASIA", "Lysimachus initiates war against Seleucus."),
        ("BATTLE", "Seleucus wins decisively; Lysimachus dies."),
        ("ALEXANDER", "After entreaties, he obtains his father's body."),
        ("TOMB", "Burial lies between Cardia and Pactye."),
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
                name=f"aftermath:name:{idx}",
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
                name=f"aftermath:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, TOMB_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.50),
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
            "PASSAGE 1.10.5",
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
    title_rect = (608, 54, 1218, 116)
    paste_with_shadow(
        page,
        make_label("LYSIMACHUS' LAST BATTLE", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("LYSIMACHUS", (616, 520, 802, 566), (716, 494), 18),
        ("SELEUCUS' ADVANCE", (1050, 486, 1334, 532), (1114, 296), 15),
        ("ASIAN BATTLEFIELD", (820, 136, 1122, 182), (940, 244), 15),
        ("BROKEN LINE", (500, 384, 710, 430), (596, 424), 16),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    battle_note = make_compact_callout(
        "After crossing into Asia, Lysimachus meets Seleucus and is decisively defeated.",
        (438, 88),
        "callout:battle",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(462, 648), (654, 612), (716, 494)])
    paste_with_shadow(page, battle_note, (462, 642))

    tomb_note = make_compact_callout(
        "Alexander recovers the body and buries it on the Chersonese between Cardia and Pactye.",
        (462, 90),
        "callout:tomb",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(906, 648), (1166, 604), (1114, 296)])
    paste_with_shadow(page, tomb_note, (894, 642))

    locator_panel = make_route_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    tomb_crop = crop_to_fill(TOMB_ART, (420, 198), centering=(0.48, 0.47))
    tomb_crop = warm_art(tomb_crop, grain_strength=0.018)
    tomb_panel = make_inset_panel(
        tomb_crop,
        "On the Chersonese, Alexander buries Lysimachus where Pausanias says the tomb remained visible.",
        94,
        "inset:tomb-caption",
        records,
    )
    paste_with_shadow(page, tomb_panel, (440, 756))
    tomb_label = (522, 774, 784, 810)
    draw_leader(draw, (728, 860), (tomb_label[0], tomb_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("CHERSONESE TOMB", tomb_label, records, max_size=14, min_size=6),
        (tomb_label[0], tomb_label[1]),
    )

    aftermath_panel = make_aftermath_panel(records)
    paste_with_shadow(page, aftermath_panel, (904, 758))

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
            "graphic_book/images/1/10/3.png",
            "graphic_book/images/1/10/4.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019eeb58-8114-7403-9e63-db34f7711a38/ig_0790fbe7eb383e27016a38275a3fe88191862e59cca989f33a.png",
                "description": "Generated raster art for Lysimachus' defeat by Seleucus after crossing into Asia.",
            },
            {
                "path": str(TOMB_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019eeb58-8114-7403-9e63-db34f7711a38/ig_0790fbe7eb383e27016a382810a9a88191b1497ba6ac492b1d.png",
                "description": "Generated raster art for Alexander burying Lysimachus on the Chersonese between Cardia and Pactye.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_10_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "10" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
