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


PASSAGE_ID = "1.12.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_12_5"
MAIN_ART = ASSET_DIR / "main_syracuse_pyrrhus_carthage.png"
DEPARTURE_ART = ASSET_DIR / "tarentum_secret_departure_inset.png"


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


def make_sicily_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((392, 332))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "TARENTUM TO SYRACUSE",
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
    size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(size, 35).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#74613d", white="#efd9a2")
    sea_noise = Image.effect_noise(size, 19).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#376776", white="#b7c7b8")
    mask = Image.new("L", size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (146, 0), (128, 24), (110, 52), (66, 70), (32, 118), (0, 130)], fill=226)
    mdraw.polygon([(154, 44), (268, 34), (318, 74), (292, 122), (178, 138), (132, 102)], fill=224)
    mdraw.polygon([(88, 104), (140, 122), (116, 152), (44, 152), (26, 132)], fill=222)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "TARENTUM": (map_rect[0] + 82, map_rect[1] + 60),
        "SICILY": (map_rect[0] + 190, map_rect[1] + 96),
        "SYRACUSE": (map_rect[0] + 268, map_rect[1] + 112),
        "CARTHAGE": (map_rect[0] + 66, map_rect[1] + 138),
    }
    route = [points["TARENTUM"], points["SICILY"], points["SYRACUSE"]]
    draw.line(route, fill="#724436", width=4)
    draw.line(route, fill="#f4ead6", width=1)
    draw.line((points["CARTHAGE"], points["SYRACUSE"]), fill="#4d5f5d", width=3)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("TARENTUM", (40, 112, 128, 136), "locator:tarentum"),
        ("SICILY", (164, 144, 226, 168), "locator:sicily"),
        ("SYRACUSE", (242, 164, 328, 188), "locator:syracuse"),
        ("CARTHAGE", (42, 186, 128, 210), "locator:carthage"),
        ("IONIAN SEA", (136, 106, 238, 130), "locator:ionian"),
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

    caption = "The Sicilian detour begins as a rescue of Syracuse, but Pausanias pivots to Pyrrhus' mistake at sea."
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


def make_sequence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "THE SICILIAN TURN",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="sequence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("CALL", "Syracuse asks for help as Carthage presses the siege."),
        ("RELIEF", "Pyrrhus crosses from Italy and forces the siege to lift."),
        ("OVERREACH", "Confidence against Carthage becomes a naval gamble."),
        ("HOMER", "The Epirotes are measured against men who know neither sea nor salt."),
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
        name_rect = (34, y + 7, 146, y + 45)
        note_rect = (158, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=10,
                min_size=6,
                padding=2,
                name=f"sequence:name:{idx}",
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
                name=f"sequence:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, DEPARTURE_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.52, 0.47))
    main_art = warm_art(main_art, grain_strength=0.014)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 742)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.12.5",
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
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (642, 54, 1258, 116)
    paste_with_shadow(
        page,
        make_label("SYRACUSE RELIEVED, SEA MISREAD", title_rect, records, font_path=TITLE_FONT, max_size=19, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PYRRHUS", (520, 228, 650, 274), (604, 394), 13),
        ("SYRACUSE", (660, 152, 808, 198), (690, 292), 13),
        ("CARTHAGINIAN FLEET", (998, 146, 1248, 194), (1110, 292), 12),
        ("SIEGE LIFTED", (880, 506, 1054, 552), (876, 378), 12),
        ("NAVAL OVERREACH", (1102, 510, 1322, 556), (1200, 374), 12),
    ]
    for text, rect, point, max_size in label_specs:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], rect[1] + (rect[3] - rect[1]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=max_size, min_size=7),
            (rect[0], rect[1]),
        )

    syracuse_note = make_compact_callout(
        "The request from Syracuse turns a Roman retreat into a Sicilian campaign.",
        (430, 86),
        "callout:syracuse",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(448, 652), (536, 596), (604, 394)])
    paste_with_shadow(page, syracuse_note, (448, 642))

    salt_note = make_compact_callout(
        "Pausanias uses Homer to mark the Epirotes as land soldiers facing a maritime power.",
        (448, 86),
        "callout:salt",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 652), (1038, 604), (1200, 374)])
    paste_with_shadow(page, salt_note, (904, 642))

    locator_panel = make_sicily_locator(records)
    paste_with_shadow(page, locator_panel, (32, 780))

    departure_art = crop_to_fill(DEPARTURE_ART, (420, 202), centering=(0.47, 0.50))
    departure_art = warm_art(departure_art, grain_strength=0.018)
    departure_panel = make_inset_panel(
        departure_art,
        "By night from Tarentum, Pyrrhus' retreat becomes the crossing to Sicily.",
        92,
        "inset:departure-caption",
        records,
    )
    paste_with_shadow(page, departure_panel, (438, 780))
    departure_label = (548, 800, 776, 836)
    draw_leader(draw, (644, 900), (departure_label[0], departure_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("SECRET DEPARTURE", departure_label, records, font_path=BODY_FONT, max_size=12, min_size=6),
        (departure_label[0], departure_label[1]),
    )

    sequence_panel = make_sequence_panel(records)
    paste_with_shadow(page, sequence_panel, (904, 780))

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
            "graphic_book/images/1/12/4.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f4809-e1ba-75d0-afdf-1ea8dc9b0f92/ig_0aeac4b7822487c4016a4fe23b32008191bdcbe18c0f87741e.png",
                "description": "Generated raster main panel showing Pyrrhus relieving Syracuse and facing the Carthaginian fleet.",
            },
            {
                "path": str(DEPARTURE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f4809-e1ba-75d0-afdf-1ea8dc9b0f92/ig_0aeac4b7822487c4016a4fe2d443e08191be42bd3e5f434fba.png",
                "description": "Generated raster inset showing Pyrrhus' night departure from Tarentum toward Sicily.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_12_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "12" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
