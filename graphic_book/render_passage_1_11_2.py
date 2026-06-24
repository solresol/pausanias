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


PASSAGE_ID = "1.11.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_11_2"
MAIN_ART = ASSET_DIR / "main_pergamus_teuthrania.png"
THYAMIS_ART = ASSET_DIR / "cestrinus_thyamis_crossing.png"


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
            "EPIRUS TO MYSIA",
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
    relief = Image.effect_noise(map_size, 38).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#74613e", white="#efd7a0")
    sea_noise = Image.effect_noise(map_size, 16).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#456d78", white="#a9b9ad")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (112, 0), (128, 52), (86, 112), (14, 142), (0, 152)], fill=226)
    mdraw.polygon([(204, 8), (328, 0), (328, 152), (248, 142), (214, 96), (188, 46)], fill=230)
    mdraw.polygon([(66, 122), (148, 100), (230, 126), (328, 116), (328, 152), (0, 152)], fill=218)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 72, map_rect[1] + 82),
        "THYAMIS": (map_rect[0] + 82, map_rect[1] + 116),
        "AEGEAN": (map_rect[0] + 162, map_rect[1] + 112),
        "MYSIA": (map_rect[0] + 252, map_rect[1] + 78),
        "PERGAMUM": (map_rect[0] + 270, map_rect[1] + 110),
    }
    route = [points["EPIRUS"], points["THYAMIS"], points["AEGEAN"], points["MYSIA"], points["PERGAMUM"]]
    draw.line(route, fill="#7b493a", width=4)
    draw.line(route, fill="#f2dfb8", width=1)
    draw.line((map_rect[0] + 116, map_rect[1] + 22, map_rect[0] + 176, map_rect[1] + 146), fill="#486b72", width=4)
    draw.line((map_rect[0] + 94, map_rect[1] + 118, map_rect[0] + 118, map_rect[1] + 94), fill="#376f7a", width=3)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("EPIRUS", (44, 136, 116, 160), "locator:epirus"),
        ("THYAMIS", (70, 174, 154, 198), "locator:thyamis"),
        ("AEGEAN", (134, 192, 210, 216), "locator:aegean"),
        ("MYSIA", (246, 124, 310, 148), "locator:mysia"),
        ("PERGAMUM", (220, 174, 324, 198), "locator:pergamum"),
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

    caption = "The passage splits Helenus' heirs between Epirus and the Mysian city renamed for Pergamus."
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


def make_succession_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "HEIRS OF HELENUS",
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
        ("MOLOSSUS", "Receives authority from Helenus."),
        ("CESTRINUS", "Crosses beyond the Thyamis with Epeirotes."),
        ("PERGAMUS", "Wins Teuthrania and gives Pergamum its name."),
        ("PIELUS", "Stays in Epirus; Pausanias traces Pyrrhus' line to him."),
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
    for asset in [MAIN_ART, THYAMIS_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 634)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.50),
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
            "PASSAGE 1.11.2",
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
            min_size=10,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.15,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (760, 54, 1312, 116)
    paste_with_shadow(
        page,
        make_label("PERGAMUS AND TEUTHRANIA", title_rect, records, font_path=TITLE_FONT, max_size=23, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PERGAMUM", (920, 126, 1114, 174), (1070, 252), 18),
        ("TEUTHRANIA", (1108, 492, 1328, 540), (1142, 454), 17),
        ("PERGAMUS", (586, 470, 784, 518), (656, 444), 17),
        ("ANDROMACHE", (482, 390, 706, 438), (592, 454), 16),
        ("ARMS OF AREIUS", (788, 556, 1030, 604), (914, 552), 15),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    city_note = make_compact_callout(
        "Pergamus wins Teuthrania in single combat and gives the city his name.",
        (466, 88),
        "callout:city",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(502, 662), (652, 554), (656, 444)])
    paste_with_shadow(page, city_note, (458, 648))

    heroon_note = make_compact_callout(
        "Andromache accompanies Pergamus; Pausanias says her heroön still stood there.",
        (466, 88),
        "callout:heroon",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(930, 662), (790, 486), (592, 454)])
    paste_with_shadow(page, heroon_note, (900, 648))

    locator_panel = make_route_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    thyamis_crop = crop_to_fill(THYAMIS_ART, (420, 198), centering=(0.50, 0.56))
    thyamis_crop = warm_art(thyamis_crop, grain_strength=0.018)
    thyamis_panel = make_inset_panel(
        thyamis_crop,
        "Cestrinus takes consenting Epeirotes beyond the Thyamis; Pielus remains in Epirus.",
        94,
        "inset:thyamis-caption",
        records,
    )
    paste_with_shadow(page, thyamis_panel, (440, 756))
    inset_label = (520, 774, 798, 810)
    draw_leader(draw, (678, 876), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("THYAMIS CROSSING", inset_label, records, max_size=14, min_size=6), (inset_label[0], inset_label[1]))

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
            "graphic_book/images/1/11/1.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ef5a4-9587-7da2-b9c8-0a8d652cc95d/ig_020f0a5c5aa69f6b016a3aca3084a08191b938ecd3ce8b48bb.png",
                "description": "Generated raster art for Pergamus taking Teuthrania and giving Pergamum its name.",
            },
            {
                "path": str(THYAMIS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ef5a4-9587-7da2-b9c8-0a8d652cc95d/ig_020f0a5c5aa69f6b016a3acacb4f188191b315403f540ac0ff.png",
                "description": "Generated raster art for Cestrinus crossing the Thyamis with Epeirotes.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_11_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "11" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
