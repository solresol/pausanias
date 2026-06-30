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


PASSAGE_ID = "1.11.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_11_3"
MAIN_ART = ASSET_DIR / "main_epirus_co_kings_aeacides.png"
OLYMPIAS_ART = ASSET_DIR / "olympias_epirus_return.png"


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
            "EPIRUS, MACEDON, LUCANIA",
            TITLE_FONT,
            max_size=15,
            min_size=7,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 226)
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(map_size, 36).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#75613d", white="#efd7a0")
    sea_noise = Image.effect_noise(map_size, 15).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#446b75", white="#aabbb0")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 8), (104, 0), (130, 48), (106, 106), (46, 144), (0, 152)], fill=226)
    mdraw.polygon([(118, 12), (316, 0), (328, 116), (266, 150), (184, 128), (142, 76)], fill=232)
    mdraw.polygon([(0, 126), (88, 112), (170, 132), (328, 122), (328, 152), (0, 152)], fill=218)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "LUCANIA": (map_rect[0] + 54, map_rect[1] + 94),
        "EPIRUS": (map_rect[0] + 142, map_rect[1] + 98),
        "MACEDON": (map_rect[0] + 228, map_rect[1] + 70),
        "AIGAI": (map_rect[0] + 238, map_rect[1] + 108),
    }
    draw.line([points["LUCANIA"], points["EPIRUS"]], fill="#7b493a", width=4)
    draw.line([points["LUCANIA"], points["EPIRUS"]], fill="#f3dfb4", width=1)
    draw.line([points["EPIRUS"], points["MACEDON"], points["AIGAI"]], fill="#6f5130", width=3)
    draw.line((map_rect[0] + 112, map_rect[1] + 20, map_rect[0] + 148, map_rect[1] + 146), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("LUCANIA", (42, 154, 128, 178), "locator:lucania"),
        ("EPIRUS", (126, 176, 200, 200), "locator:epirus"),
        ("MACEDON", (216, 126, 306, 150), "locator:macedon"),
        ("IONIAN SEA", (70, 202, 174, 226), "locator:ionian"),
        ("AEGEAN", (232, 190, 306, 214), "locator:aegean"),
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

    caption = "The episode links Alexander's death in Lucania, Olympias' refuge in Epirus, and the Macedonian succession war."
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


def make_crisis_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "EPIRUS' ROYAL CRISIS",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="crisis:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("ALCETAS", "Epirus keeps single rule until Alcetas' time."),
        ("CO-RULE", "His sons settle quarrels by ruling as equals."),
        ("OLYMPIAS", "After Lucania, she returns to Epirus fearing Antipater."),
        ("AEACIDES", "He aids her against Arrhidaeus despite Epirote reluctance."),
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
                name=f"crisis:name:{idx}",
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
                name=f"crisis:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, OLYMPIAS_ART]:
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
    main_art = warm_art(ImageEnhance.Contrast(main_art).enhance(1.02), grain_strength=0.014)
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
            "PASSAGE 1.11.3",
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
            max_size=20,
            min_size=9,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (716, 54, 1320, 116)
    paste_with_shadow(
        page,
        make_label("EPIRUS AND OLYMPIAS", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ALCETAS' SONS", (520, 132, 792, 180), (638, 278), 17),
        ("AEACIDES", (600, 536, 790, 584), (690, 492), 19),
        ("OLYMPIAS RETURNS", (816, 486, 1132, 534), (1034, 446), 16),
        ("MACEDONIAN HOST", (1054, 356, 1322, 404), (1050, 318), 16),
        ("EPIRUS", (1126, 140, 1262, 188), (1090, 252), 20),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    co_rule_note = make_compact_callout(
        "The quarrelling sons of Alcetas settle on equal rule and keep peace thereafter.",
        (428, 88),
        "callout:co-rule",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(470, 656), (554, 566), (638, 278)])
    paste_with_shadow(page, co_rule_note, (458, 642))

    aeacides_note = make_compact_callout(
        "Aeacides obeys Olympias and helps her against Arrhidaeus, though the Epirotes resist.",
        (466, 88),
        "callout:aeacides",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(928, 656), (812, 592), (690, 492)])
    paste_with_shadow(page, aeacides_note, (900, 642))

    locator_panel = make_epirus_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    olympias_crop = crop_to_fill(OLYMPIAS_ART, (420, 198), centering=(0.50, 0.56))
    olympias_crop = warm_art(olympias_crop, grain_strength=0.018)
    olympias_panel = make_inset_panel(
        olympias_crop,
        "After Alexander's death among the Lucanians, Olympias returns to Epirus in fear of Antipater.",
        94,
        "inset:olympias-caption",
        records,
    )
    paste_with_shadow(page, olympias_panel, (440, 756))
    inset_label = (522, 774, 798, 810)
    draw_leader(draw, (704, 872), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("OLYMPIAS' RETURN", inset_label, records, max_size=14, min_size=6), (inset_label[0], inset_label[1]))

    crisis_panel = make_crisis_panel(records)
    paste_with_shadow(page, crisis_panel, (904, 758))

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
            "graphic_book/images/1/11/2.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f19b1-b610-7a82-a874-dff76f10253f/ig_0a92c16086125372016a4404d9e0248191b39f9c1c4671211a.png",
                "description": "Generated raster main panel showing Epirote co-rulers, Aeacides' military support for Olympias, and Macedonian pressure beyond the valley.",
            },
            {
                "path": str(OLYMPIAS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f19b1-b610-7a82-a874-dff76f10253f/ig_0a92c16086125372016a44058e8c0881919f60076cf69d84da.png",
                "description": "Generated raster scenic inset for Olympias returning through Epirus.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_11_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "11" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
