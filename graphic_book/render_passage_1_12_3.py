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


PASSAGE_ID = "1.12.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_12_3"
MAIN_ART = ASSET_DIR / "main_pyrrhus_elephants.png"
ALEXANDER_ART = ASSET_DIR / "alexander_porus_elephants.png"


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


def make_elephant_provenance_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ELEPHANTS REACH ROME",
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
    relief = Image.effect_noise(map_size, 32).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#725f39", white="#efd6a0")
    sea_noise = Image.effect_noise(map_size, 18).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#416b78", white="#adc0b8")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (212, 0), (206, 32), (172, 50), (176, 82), (126, 104), (106, 152), (0, 152)], fill=226)
    mdraw.polygon([(184, 40), (328, 28), (328, 152), (200, 152), (166, 118), (188, 82)], fill=228)
    mdraw.polygon([(0, 118), (88, 106), (126, 152), (0, 152)], fill=218)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "INDIA": (map_rect[0] + 278, map_rect[1] + 96),
        "SUCCESSORS": (map_rect[0] + 186, map_rect[1] + 76),
        "DEMETRIUS": (map_rect[0] + 132, map_rect[1] + 104),
        "PYRRHUS": (map_rect[0] + 76, map_rect[1] + 92),
        "ROME": (map_rect[0] + 40, map_rect[1] + 62),
    }
    route = [points["INDIA"], points["SUCCESSORS"], points["DEMETRIUS"], points["PYRRHUS"], points["ROME"]]
    draw.line(route, fill="#724436", width=4)
    draw.line(route, fill="#f4ead6", width=1)
    for x, y in route:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("INDIA", (260, 148, 318, 172), "locator:india"),
        ("ALEXANDER", (170, 112, 260, 136), "locator:alexander"),
        ("DEMETRIUS", (110, 164, 206, 188), "locator:demetrius"),
        ("PYRRHUS", (52, 144, 126, 168), "locator:pyrrhus"),
        ("ROME", (30, 96, 88, 120), "locator:rome"),
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

    caption = "Pausanias frames Pyrrhus' beasts through Alexander, the Successors, Demetrius, and Rome."
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
            "WHY THE ELEPHANTS MATTER",
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
        ("ROMAN LIMIT", "Pyrrhus cannot overcome Rome by ordinary force."),
        ("ALEXANDER", "Porus' elephants become the Greek historical precedent."),
        ("SUCCESSORS", "Kings after Alexander maintain elephant corps."),
        ("TERROR", "The Romans read living animals as uncanny creatures."),
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
                max_size=10,
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
    for asset in [MAIN_ART, ALEXANDER_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 634)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.47),
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
            "PASSAGE 1.12.3",
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
    title_rect = (658, 54, 1270, 116)
    paste_with_shadow(
        page,
        make_label("PYRRHUS UNLEASHES ELEPHANTS", title_rect, records, font_path=TITLE_FONT, max_size=20, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PYRRHUS' ELEPHANTS", (548, 160, 778, 208), (596, 440), 13),
        ("EPIROTE HANDLERS", (776, 158, 1008, 206), (788, 360), 13),
        ("ROMAN LINE", (1058, 174, 1264, 222), (1162, 426), 15),
        ("TERROR AT THE UNKNOWN", (950, 528, 1280, 576), (1120, 500), 12),
        ("DUSTY ITALIAN FIELD", (560, 530, 806, 578), (744, 606), 12),
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

    strategy_note = make_compact_callout(
        "Pausanias makes the animals a strategic answer to Roman strength.",
        (438, 88),
        "callout:strategy",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(456, 654), (566, 612), (646, 516), (596, 440)])
    paste_with_shadow(page, strategy_note, (456, 642))

    terror_note = make_compact_callout(
        "The Romans fear the elephants as beings outside familiar categories.",
        (470, 90),
        "callout:terror",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(900, 654), (1028, 610), (1120, 500)])
    paste_with_shadow(page, terror_note, (896, 642))

    locator_panel = make_elephant_provenance_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    alexander_crop = crop_to_fill(ALEXANDER_ART, (420, 198), centering=(0.50, 0.51))
    alexander_crop = warm_art(alexander_crop, grain_strength=0.018)
    alexander_panel = make_inset_panel(
        alexander_crop,
        "Alexander's victory over Porus gives Pausanias the first Greek precedent for elephants.",
        94,
        "inset:alexander-caption",
        records,
    )
    paste_with_shadow(page, alexander_panel, (440, 756))
    inset_label = (550, 774, 782, 810)
    draw_leader(draw, (714, 862), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("ALEXANDER AND PORUS", inset_label, records, font_path=BODY_FONT, max_size=12, min_size=6),
        (inset_label[0], inset_label[1]),
    )

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
            "graphic_book/images/1/12/2.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f3dbe-4099-7671-9da8-2b3c52f21e4a/ig_03436f89a1304669016a4d3f53fd248191be3e508b2e3f5b8c.png",
                "description": "Generated raster main panel showing Pyrrhus' elephants advancing into a frightened Roman line.",
            },
            {
                "path": str(ALEXANDER_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f3dbe-4099-7671-9da8-2b3c52f21e4a/ig_0e22fada840bc7cf016a4d3ff675408191b8e8351b6a23ccc8.png",
                "description": "Generated raster scenic inset showing Alexander's army and Indian elephants after the conflict with Porus.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_12_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "12" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
