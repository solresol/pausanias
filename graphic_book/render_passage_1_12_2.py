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


PASSAGE_ID = "1.12.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_12_2"
MAIN_ART = ASSET_DIR / "main_pyrrhus_transport_preparations.png"
BATTLE_ART = ASSET_DIR / "pyrrhus_surprise_battle_inset.png"


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


def make_campaign_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "UNSEEN CROSSING",
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
    relief = Image.effect_noise(map_size, 34).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#73633d", white="#efd7a0")
    sea_noise = Image.effect_noise(map_size, 15).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#3f6978", white="#adc3bc")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (120, 0), (106, 32), (86, 76), (94, 118), (60, 152), (0, 152)], fill=225)
    mdraw.polygon([(208, 0), (328, 0), (318, 44), (290, 76), (304, 116), (262, 152), (198, 152), (182, 112), (206, 72)], fill=228)
    mdraw.polygon([(234, 78), (328, 84), (328, 152), (244, 152), (224, 122)], fill=223)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 76, map_rect[1] + 82),
        "TARENTUM": (map_rect[0] + 232, map_rect[1] + 112),
        "ROME": (map_rect[0] + 250, map_rect[1] + 36),
        "IONIAN": (map_rect[0] + 154, map_rect[1] + 96),
        "HIDDEN": (map_rect[0] + 104, map_rect[1] + 132),
    }
    draw.line([points["EPIRUS"], points["TARENTUM"], points["ROME"]], fill="#704235", width=4)
    draw.line([points["EPIRUS"], points["TARENTUM"], points["ROME"]], fill="#f4ead6", width=1)
    draw.line((map_rect[0] + 94, map_rect[1] + 112, map_rect[0] + 222, map_rect[1] + 112), fill="#416b75", width=4)
    draw.line((points["EPIRUS"], points["HIDDEN"], points["TARENTUM"]), fill="#5a6670", width=3)
    draw.line((points["EPIRUS"], points["HIDDEN"], points["TARENTUM"]), fill="#f4ead6", width=1)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("EPIRUS", (48, 126, 124, 150), "locator:epirus"),
        ("IONIAN", (124, 172, 204, 196), "locator:ionian"),
        ("TARENTUM", (204, 178, 312, 202), "locator:tarentum"),
        ("ROME", (238, 98, 296, 122), "locator:rome"),
        ("HIDDEN ROUTE", (38, 204, 160, 228), "locator:hidden-route"),
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

    caption = "Warships and transports carry Pyrrhus out of sight before his sudden arrival."
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


def make_source_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "WHAT PAUSANIAS ADMIRES",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="source:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("DECISION", "Once resolved, Pyrrhus delays over nothing."),
        ("TRANSPORTS", "Warships and merchant vessels carry cavalry and infantry."),
        ("CONCEALMENT", "The crossing keeps his force out of Roman sight."),
        ("SURPRISE", "His first appearance in battle throws the Romans into confusion."),
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
                max_size=11,
                min_size=6,
                padding=2,
                name=f"source:name:{idx}",
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
                name=f"source:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, BATTLE_ART]:
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
            "PASSAGE 1.12.2",
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
    title_rect = (678, 54, 1256, 116)
    paste_with_shadow(
        page,
        make_label("PYRRHUS PREPARES IN SECRET", title_rect, records, font_path=TITLE_FONT, max_size=20, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PYRRHUS", (548, 164, 724, 212), (584, 354), 17),
        ("WARSHIPS", (818, 164, 1012, 212), (842, 354), 15),
        ("MERCHANT TRANSPORTS", (1054, 176, 1324, 224), (1178, 414), 12),
        ("CAVALRY", (520, 504, 700, 552), (510, 434), 15),
        ("INFANTRY AND STORES", (836, 542, 1118, 590), (882, 464), 12),
    ]
    for text, rect, point, max_size in label_specs:
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        else:
            endpoint = (rect[0] if point[0] < rect[0] else rect[2], rect[1] + (rect[3] - rect[1]) // 2)
        draw_leader(draw, point, endpoint)
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    crossing_note = make_compact_callout(
        "Warships and merchant vessels make the expedition both military and logistical.",
        (438, 88),
        "callout:crossing",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(456, 654), (566, 612), (802, 594), (842, 354)])
    paste_with_shadow(page, crossing_note, (456, 642))

    achilles_note = make_compact_callout(
        "Pausanias stresses foresight: Pyrrhus crosses unseen before appearing in battle.",
        (470, 90),
        "callout:achilles",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(900, 654), (1032, 610), (1178, 414)])
    paste_with_shadow(page, achilles_note, (896, 642))

    locator_panel = make_campaign_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    battle_crop = crop_to_fill(BATTLE_ART, (420, 198), centering=(0.48, 0.50))
    battle_crop = warm_art(battle_crop, grain_strength=0.018)
    battle_panel = make_inset_panel(
        battle_crop,
        "After the unseen crossing, Pyrrhus' arrival unsettles the Roman line.",
        94,
        "inset:battle-caption",
        records,
    )
    paste_with_shadow(page, battle_panel, (440, 756))
    inset_label = (548, 774, 780, 810)
    draw_leader(draw, (714, 862), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("SUDDEN ARRIVAL", inset_label, records, max_size=13, min_size=6), (inset_label[0], inset_label[1]))

    source_panel = make_source_panel(records)
    paste_with_shadow(page, source_panel, (904, 758))

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
            "graphic_book/images/1/12/1.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f3897-e34a-7e82-924a-09e70f2af89c/ig_0822fcbc549971ea016a4bedd890a0819190ab18bf324dcae1.png",
                "description": "Generated raster main panel showing Pyrrhus directing warships, merchant transports, cavalry, infantry, and stores before the unseen crossing.",
            },
            {
                "path": str(BATTLE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f3897-e34a-7e82-924a-09e70f2af89c/ig_0822fcbc549971ea016a4bee74b0788191adf0f36d5ddfaa76.png",
                "description": "Generated raster scenic inset showing Pyrrhus' sudden arrival throwing the Roman line into confusion.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_12_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "12" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
