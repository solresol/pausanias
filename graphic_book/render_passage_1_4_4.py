#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pausanias_db import connect

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from graphic_book.render_passage_1_3_2 import (
    BODY_FONT,
    DISPLAY_FONT,
    FitRecord,
    HEIGHT,
    INK,
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


PASSAGE_ID = "1.4.4"
ART_PATH = root_dir() / "graphic_book/assets/generated/1_4_4/main_delphi_parnassus_galatian_attack.png"


def load_translation() -> str:
    with connect() as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = %s",
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


def warm_art(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Sharpness(image).enhance(1.06)
    overlay = Image.new("RGB", image.size, "#e7c98e")
    image = Image.blend(image, overlay, 0.07)
    grain = Image.effect_noise(image.size, 5).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#a77b45", white="#fff0ca")
    return Image.blend(image, grain_rgb, 0.035)


def make_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (16, 12, size[0] - 16, size[1] - 12),
            text,
            BODY_FONT,
            max_size=18,
            min_size=12,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.16,
        )
    )
    return panel


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((404, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THERMOPYLAE TO DELPHI",
            TITLE_FONT,
            max_size=22,
            min_size=15,
            padding=8,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 72, panel.width - 22, 238)
    x0, y0, x1, y1 = map_rect
    art = crop_to_fill(ART_PATH, (x1 - x0, y1 - y0), centering=(0.48, 0.48))
    art = warm_art(art)
    veil = Image.new("RGB", art.size, "#efd9ab")
    art = Image.blend(art, veil, 0.18)
    panel.paste(art, (x0, y0))
    draw.rounded_rectangle(map_rect, radius=16, outline="#7b5a32", width=3)
    draw.rounded_rectangle((x0 + 5, y0 + 5, x1 - 5, y1 - 5), radius=12, outline="#d9bf86", width=1)

    route = [(x0 + 42, y0 + 118), (x0 + 118, y0 + 96), (x0 + 196, y0 + 104), (x0 + 286, y0 + 132)]
    ridge = [(x0 + 152, y0 + 36), (x0 + 198, y0 + 66), (x0 + 252, y0 + 78), (x0 + 326, y0 + 58)]
    draw.line(route, fill="#4c2118", width=8, joint="curve")
    draw.line(route, fill="#e0b85e", width=3, joint="curve")
    draw.line(ridge, fill="#efe6c8", width=7, joint="curve")
    draw.line(ridge, fill="#6a5134", width=2, joint="curve")
    draw.ellipse((x0 + 272, y0 + 118, x0 + 294, y0 + 140), fill="#6f2d20", outline="#f0d492", width=2)
    draw.ellipse((x0 + 34, y0 + 108, x0 + 54, y0 + 128), fill="#213f45", outline="#f0d492", width=2)

    label_specs = [
        ("THERMOPYLAE", (30, 174, 152, 200), "locator:thermopylae"),
        ("PARNASSUS", (164, 86, 286, 112), "locator:parnassus"),
        ("DELPHI", (276, 184, 360, 210), "locator:delphi"),
        ("APPROACH", (122, 136, 236, 162), "locator:approach"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=7, fill="#f4e0b4", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=13,
                min_size=8,
                padding=4,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption_rect = (20, 256, panel.width - 20, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "The Galatian attack moves from Thermopylae toward Delphi, where the battle turns on Parnassus and the god's sanctuary.",
            BODY_FONT,
            max_size=15,
            min_size=11,
            padding=6,
            name="locator:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not ART_PATH.exists():
        raise RuntimeError(f"Missing generated art asset: {ART_PATH}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 42, 1372, 704)
    main_art = crop_to_fill(ART_PATH, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.52, 0.53))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 398, 706)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.4.4",
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
            max_size=21,
            min_size=13,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.17,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)

    title_rect = (590, 54, 1168, 116)
    paste_with_shadow(page, make_label("DELPHI UNDER PARNASSUS", title_rect, records, font_path=TITLE_FONT, max_size=26, min_size=15), (title_rect[0], title_rect[1]))

    callouts = [
        (
            "Pausanias links the defense of Delphi to local allies: Delphians, Phocians, and Aetolians.",
            (492, 760, 890, 884),
            [(1130, 590), (1068, 706), (510, 822)],
            "callout:defenders",
        ),
        (
            "The god's aid is narrated through weather and mountain: lightning strikes and Parnassus sends rocks down on the attackers.",
            (920, 746, 1344, 874),
            [(934, 274), (934, 708), (938, 810)],
            "callout:storm",
        ),
        (
            "The terrifying armed figures include Hyperochus, Amadocus, and Pyrrhus, son of Achilles.",
            (684, 934, 1160, 1048),
            [(1210, 264), (1008, 706), (702, 992)],
            "callout:apparitions",
        ),
    ]
    for _text, _rect, leader_points, _name in callouts:
        draw_polyline_leader(draw, leader_points)

    labels = [
        ("LIGHTNING", (482, 126, 668, 178), (620, 258)),
        ("PARNASSUS CLIFFS", (874, 126, 1192, 178), (1008, 220)),
        ("FALLING ROCKS", (760, 262, 1016, 314), (934, 274)),
        ("APPARITION WARRIORS", (1026, 304, 1352, 358), (1210, 264)),
        ("DELPHI SANCTUARY", (856, 476, 1190, 530), (1012, 432)),
        ("GALATIAN APPROACH", (486, 548, 830, 602), (684, 438)),
        ("GREEK DEFENDERS", (1052, 618, 1344, 672), (1130, 590)),
    ]
    for text, rect, point in labels:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=24, min_size=12), (rect[0], rect[1]))

    locator = make_locator_panel(records)
    paste_with_shadow(page, locator, (40, 746))

    for text, rect, _leader_points, name in callouts:
        panel = make_callout(text, (rect[2] - rect[0], rect[3] - rect[1]), name, records)
        paste_with_shadow(page, panel, (rect[0], rect[1]))

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
    }
    report_path = root_dir() / "tmp" / "passage_1_4_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "4" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
