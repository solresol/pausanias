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
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.4.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_4_6"
MAIN_ART = ASSET_DIR / "main_pergamene_spoils.png"
CABEIRI_ART = ASSET_DIR / "cabeiri_sacred_land.png"
TELEPHUS_ART = ASSET_DIR / "telephus_mysia.png"


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
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.95)
    image = ImageEnhance.Sharpness(image).enhance(1.035)
    wash = Image.new("RGB", image.size, "#e7c995")
    image = Image.blend(image, wash, 0.05)
    grain = Image.effect_noise(image.size, 5).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#a77b45", white="#fff0ca")
    return Image.blend(image, grain_rgb, 0.032)


def make_compact_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=17,
            min_size=12,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.15,
        )
    )
    return panel


def make_claims_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((364, 176))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 12, panel.width - 18, 48)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "PERGAMENE CLAIMS",
            TITLE_FONT,
            max_size=18,
            min_size=13,
            padding=6,
            name="claims:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    items = [
        "rule over Lower Asia",
        "repulse of the Galatians",
        "Telephus against Agamemnon",
    ]
    y = 64
    for idx, item in enumerate(items, start=1):
        draw.ellipse((24, y + 4, 38, y + 18), fill="#7d5430", outline="#f0d492", width=1)
        records.append(
            draw_fitted_text(
                draw,
                (48, y - 2, panel.width - 22, y + 28),
                f"{idx}. {item}",
                BODY_FONT,
                max_size=15,
                min_size=11,
                padding=3,
                name=f"claims:item:{idx}",
                spacing_ratio=0.10,
            )
        )
        y += 36
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, CABEIRI_ART, TELEPHUS_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 38, 1372, 666)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.51, 0.53))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 724)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.4.6",
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
            spacing_ratio=0.17,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (648, 54, 1194, 118)
    paste_with_shadow(
        page,
        make_label("PERGAMON REMEMBERS", title_rect, records, font_path=TITLE_FONT, max_size=25, min_size=15),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("LOWER ASIA", (500, 152, 690, 204), (536, 372)),
        ("PERGAMON", (742, 158, 930, 210), (786, 330)),
        ("BATTLE PAINTING", (982, 162, 1268, 216), (1108, 294)),
        ("GALATIAN ARMS", (936, 510, 1190, 564), (1018, 548)),
        ("SPOILS TAKEN", (632, 538, 858, 592), (720, 548)),
        ("SACRED TERRITORY", (474, 236, 762, 288), (556, 454)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=22, min_size=11), (rect[0], rect[1]))

    claims_key = make_claims_key(records)
    paste_with_shadow(page, claims_key, (34, 790))

    memory_callout = make_compact_callout(
        "Pausanias shifts from Galatian movement to Pergamene memory: trophies, claims of origin, and a heroic Mysian past.",
        (364, 112),
        "callout:memory",
        records,
    )
    paste_with_shadow(page, memory_callout, (34, 986))
    draw_polyline_leader(draw, [(404, 1038), (510, 930), (672, 588)])

    cabeiri_art = warm_art(crop_to_fill(CABEIRI_ART, (398, 214), centering=(0.52, 0.50)))
    cabeiri_panel = make_inset_panel(
        cabeiri_art,
        "The Pergamenes claimed the land as formerly sacred to the Cabeiri.",
        90,
        "caption:cabeiri",
        records,
    )
    paste_with_shadow(page, cabeiri_panel, (438, 742))
    paste_with_shadow(page, make_label("CABEIRI LAND", (542, 760, 760, 808), records, max_size=22, min_size=12), (542, 760))
    draw_leader(draw, (650, 842), (650, 806))

    telephus_art = warm_art(crop_to_fill(TELEPHUS_ART, (404, 214), centering=(0.48, 0.50)))
    telephus_panel = make_inset_panel(
        telephus_art,
        "Telephus' defense of Mysia anchors the Pergamene claim of Arcadian descent.",
        90,
        "caption:telephus",
        records,
    )
    paste_with_shadow(page, telephus_panel, (914, 742))
    paste_with_shadow(page, make_label("TELEPHUS IN MYSIA", (1012, 760, 1280, 808), records, max_size=22, min_size=12), (1012, 760))
    draw_leader(draw, (1148, 842), (1148, 806))

    achievement_callout = make_compact_callout(
        "The passage names three remembered achievements: dominion, Galatian defeat, and Telephus' heroic struggle.",
        (430, 108),
        "callout:achievements",
        records,
    )
    paste_with_shadow(page, achievement_callout, (620, 620))
    draw_polyline_leader(draw, [(828, 620), (888, 586), (1028, 542)])

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
    report_path = root_dir() / "tmp" / "passage_1_4_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "4" / "6.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
