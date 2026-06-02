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
    crop_to_fill,
    draw_fitted_text,
    draw_leader,
    draw_polyline_leader,
    framed_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.6.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_4"
MAIN_ART = ASSET_DIR / "main_ptolemy_coalition_council.png"


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


def validate_fit_records(records: list[FitRecord]) -> None:
    for record in records:
        rx0, ry0, rx1, ry1 = record.rect
        bx0, by0, bx1, by1 = record.text_bbox
        if bx0 < rx0 or by0 < ry0 or bx1 > rx1 or by1 > ry1:
            raise RuntimeError(f"{record.name}: measured text bbox escapes target rect")


def warm_art(image: Image.Image, *, grain_strength: float = 0.026) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.90)
    image = ImageEnhance.Sharpness(image).enhance(1.045)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.045)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


def make_compact_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=18,
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_alliance_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 244))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ALLIANCE AGAINST ANTIGONUS",
            TITLE_FONT,
            max_size=17,
            min_size=9,
            padding=6,
            name="alliance-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 174)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.50, 0.66))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.8)), grain_strength=0.048)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.53)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EGYPT": (104, 150),
        "SYRIA": (208, 128),
        "PHOENICIA": (190, 142),
        "MACEDON": (118, 94),
        "THRACE": (150, 88),
        "ANTIGONUS": (260, 96),
    }
    for route in [
        ("EGYPT", "SYRIA", "#8a5d34"),
        ("EGYPT", "PHOENICIA", "#8a5d34"),
        ("MACEDON", "EGYPT", "#5f5c78"),
        ("THRACE", "EGYPT", "#5f5c78"),
        ("ANTIGONUS", "SYRIA", "#7b493a"),
    ]:
        a, b, color = route
        draw.line([points[a], points[b]], fill=color, width=3)

    for name, color in [
        ("EGYPT", "#3f5f72"),
        ("SYRIA", "#8c6a2f"),
        ("PHOENICIA", "#8c6a2f"),
        ("MACEDON", "#6b5a78"),
        ("THRACE", "#6b5a78"),
        ("ANTIGONUS", "#7b493a"),
    ]:
        point = points[name]
        draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("EGYPT", (72, 152, 136, 174), "alliance-key:egypt"),
        ("SYRIA", (190, 106, 250, 128), "alliance-key:syria"),
        ("PHOENICIA", (164, 144, 254, 166), "alliance-key:phoenicia"),
        ("MACEDON", (70, 76, 144, 98), "alliance-key:macedon"),
        ("THRACE", (134, 62, 200, 84), "alliance-key:thrace"),
        ("ANTIGONUS", (230, 72, 318, 94), "alliance-key:antigonus"),
    ]:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "Ptolemy holds the southern base, secures the Levantine coast, and draws Macedon and Thrace into common cause."
    records.append(
        draw_fitted_text(
            draw,
            (24, 184, panel.width - 24, panel.height - 12),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="alliance-key:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not MAIN_ART.exists():
        raise RuntimeError(f"Missing generated art asset: {MAIN_ART}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 738)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.6.4",
            TITLE_FONT,
            max_size=30,
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
            min_size=12,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.15,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (608, 56, 1226, 118)
    paste_with_shadow(
        page,
        make_label("PTOLEMY'S COALITION", title_rect, records, font_path=TITLE_FONT, max_size=25, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PTOLEMY", (514, 276, 652, 328), (574, 358)),
        ("SELEUCUS IN REFUGE", (750, 232, 1010, 284), (810, 350)),
        ("CASSANDER'S ENVOY", (464, 498, 736, 550), (534, 380)),
        ("LYSIMACHUS' ENVOY", (1036, 478, 1304, 530), (1110, 400)),
        ("ANTIGONUS' THREAT", (1084, 150, 1350, 202), (1230, 220)),
        ("SYRIA & PHOENICIA", (704, 552, 956, 604), (820, 612)),
        ("EASTERN SEA ROUTES", (978, 564, 1244, 616), (872, 592)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=18, min_size=8), (rect[0], rect[1]))

    alliance_key = make_alliance_key(records)
    paste_with_shadow(page, alliance_key, (32, 756))

    state_note = make_compact_callout(
        "Perdiccas' death opens the field: Ptolemy moves from holding Egypt to securing Syria and Phoenicia.",
        (424, 116),
        "callout:state",
        records,
    )
    paste_with_shadow(page, state_note, (444, 706))
    draw_polyline_leader(draw, [(656, 706), (668, 654), (820, 612)])

    seleucus_note = make_compact_callout(
        "Seleucus' flight turns Antigonus' growth from rumor into a shared political danger.",
        (396, 104),
        "callout:seleucus",
        records,
    )
    paste_with_shadow(page, seleucus_note, (926, 706))
    draw_polyline_leader(draw, [(1124, 706), (1118, 642), (1230, 220)])

    coalition_note = make_compact_callout(
        "Cassander in Macedon and Lysimachus in Thrace are brought into the war as Ptolemy builds a wider coalition.",
        (374, 104),
        "callout:coalition",
        records,
    )
    paste_with_shadow(page, coalition_note, (32, 1012))
    draw_polyline_leader(draw, [(406, 1056), (466, 1016), (536, 380)])

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
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Ptolemy's council receiving Seleucus and coordinating Cassander and Lysimachus against Antigonus.",
            }
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
