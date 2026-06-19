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
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    make_compact_callout,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.10.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_10_3"
MAIN_ART = ASSET_DIR / "main_lysimachus_court_intrigue.png"
AGATHOCLES_ART = ASSET_DIR / "agathocles_led_away.png"


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


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "LYSIMACHUS' KINGDOM",
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
    relief = Image.effect_noise(map_size, 28).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#6e603d", white="#ecd39a")
    sea_noise = Image.effect_noise(map_size, 18).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#3f6875", white="#9eb6ad")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 104), (82, 84), (138, 98), (194, 82), (328, 88), (328, 152), (0, 152)], fill=220)
    mdraw.polygon([(104, 0), (328, 0), (328, 72), (236, 74), (170, 58), (132, 36)], fill=218)
    mdraw.polygon([(0, 0), (74, 0), (92, 40), (56, 82), (0, 100)], fill=224)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.05)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "THRACE": (map_rect[0] + 112, map_rect[1] + 52),
        "LYSIMACHEIA": (map_rect[0] + 132, map_rect[1] + 82),
        "MACEDONIA": (map_rect[0] + 64, map_rect[1] + 112),
        "ASIA MINOR": (map_rect[0] + 262, map_rect[1] + 96),
    }
    route = [points["MACEDONIA"], points["LYSIMACHEIA"], points["ASIA MINOR"]]
    draw.line(route, fill="#724833", width=4)
    draw.line(route, fill="#f2dfb8", width=1)
    draw.line((map_rect[0] + 32, map_rect[1] + 122, map_rect[0] + 296, map_rect[1] + 116), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("THRACE", (78, 112, 150, 136), "locator:thrace"),
        ("LYSIMACHEIA", (122, 146, 232, 170), "locator:lysimacheia"),
        ("MACEDONIA", (38, 178, 138, 202), "locator:macedonia"),
        ("ASIA MINOR", (246, 158, 338, 182), "locator:asia-minor"),
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

    caption = "The household struggle unfolds inside a kingdom spanning Thrace, Macedonia, and Asia Minor."
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


def make_succession_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "SUCCESSION PRESSURE",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="succession:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("LYSIMACHUS", "Old, powerful, and increasingly isolated."),
        ("AGATHOCLES", "Son of Lysandra; feared as the future heir."),
        ("ARSINOE", "Wife of Lysimachus; protects her own children."),
        ("AFTERMATH", "The plot leaves the king bereft of friends."),
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
                name=f"succession:name:{idx}",
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
                name=f"succession:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, AGATHOCLES_ART]:
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
            "PASSAGE 1.10.3",
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
    title_rect = (642, 54, 1178, 116)
    paste_with_shadow(
        page,
        make_label("ARSINOE AND AGATHOCLES", title_rect, records, font_path=TITLE_FONT, max_size=23, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("LYSIMACHUS", (530, 398, 744, 444), (656, 356), 17),
        ("ARSINOE", (906, 154, 1064, 200), (980, 302), 18),
        ("AGATHOCLES", (1168, 170, 1370, 216), (1252, 314), 16),
        ("SEALED LETTERS", (486, 530, 716, 576), (592, 554), 15),
        ("WATCHING COURT", (736, 198, 978, 244), (812, 336), 15),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    fear_note = make_compact_callout(
        "Arsinoe fears that power will pass to Agathocles after Lysimachus' death.",
        (424, 88),
        "callout:fear",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(470, 648), (792, 606), (980, 302)])
    paste_with_shadow(page, fear_note, (456, 642))

    isolated_note = make_compact_callout(
        "The plot destroys the king's household trust; Pausanias says no advantage remained for him.",
        (446, 90),
        "callout:isolation",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(906, 650), (734, 582), (656, 356)])
    paste_with_shadow(page, isolated_note, (894, 642))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    agathocles_crop = crop_to_fill(AGATHOCLES_ART, (420, 198), centering=(0.52, 0.48))
    agathocles_crop = warm_art(agathocles_crop, grain_strength=0.018)
    agathocles_panel = make_inset_panel(
        agathocles_crop,
        "Agathocles' removal turns household rivalry into a dynastic catastrophe.",
        94,
        "inset:agathocles-caption",
        records,
    )
    paste_with_shadow(page, agathocles_panel, (440, 756))
    inset_label = (520, 774, 786, 810)
    draw_leader(draw, (694, 876), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("AGATHOCLES LED AWAY", inset_label, records, max_size=13, min_size=6),
        (inset_label[0], inset_label[1]),
    )

    succession_panel = make_succession_panel(records)
    paste_with_shadow(page, succession_panel, (904, 758))

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
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster art for the Hellenistic court-intrigue main panel.",
            },
            {
                "path": str(AGATHOCLES_ART),
                "description": "Generated raster art for the non-graphic Agathocles removal inset.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_10_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "10" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
