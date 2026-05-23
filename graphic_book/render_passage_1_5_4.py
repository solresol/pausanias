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
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.5.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_5_4"
MAIN_ART = ASSET_DIR / "main_aegeus_return.png"
THRACE_ART = ASSET_DIR / "thracian_alliance.png"
STATUE_ART = ASSET_DIR / "pandion_acropolis_statue.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.028) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Sharpness(image).enhance(1.04)
    wash = Image.new("RGB", image.size, "#e1c188")
    image = Image.blend(image, wash, 0.06)
    grain = Image.effect_noise(image.size, 5).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#967044", white="#fff1ce")
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
            max_size=17,
            min_size=12,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.15,
        )
    )
    return panel


def make_route_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 236))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 54)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "RETURN, ALLIANCE, STATUE",
            TITLE_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="route:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 70, panel.width - 28, 174)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.58, 0.52))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.6)), grain_strength=0.04)
    tint = Image.new("RGB", base.size, "#ecd9b2")
    base = Image.blend(base, tint, 0.46)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    megara = (76, 138)
    athens = (244, 108)
    acropolis = (290, 84)
    thrace = (300, 154)
    draw.line([megara, athens, acropolis], fill="#7d5430", width=5, joint="curve")
    draw.line([athens, thrace], fill="#9b6b3d", width=3)
    for point, color in [(megara, "#7d5430"), (athens, "#3f5f72"), (acropolis, "#8c3d2e"), (thrace, "#56715a")]:
        draw.ellipse((point[0] - 8, point[1] - 8, point[0] + 8, point[1] + 8), fill=color, outline="#f5e3ba", width=2)

    label_specs = [
        ("MEGARA", (42, 90, 116, 116), "route:megara"),
        ("ATHENS", (204, 114, 286, 140), "route:athens"),
        ("ACROPOLIS", (236, 58, 340, 84), "route:acropolis"),
        ("THRACE", (286, 160, 356, 186), "route:thrace"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=8, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=12,
                min_size=8,
                padding=3,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    records.append(
        draw_fitted_text(
            draw,
            (24, 184, panel.width - 24, panel.height - 14),
            "Aegeus returns locally; Thrace and the Acropolis keep the wider frame.",
            BODY_FONT,
            max_size=13,
            min_size=10,
            padding=3,
            name="route:caption",
            align="center",
            spacing_ratio=0.10,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, THRACE_ART, STATUE_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 642)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.52, 0.50),
    )
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
            "PASSAGE 1.5.4",
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
            max_size=18,
            min_size=12,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.15,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (650, 54, 1212, 118)
    paste_with_shadow(
        page,
        make_label("AEGEUS RETURNS TO ATHENS", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=13),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("RETURNED SONS", (500, 154, 774, 206), (634, 302)),
        ("AEGEUS", (704, 258, 864, 310), (770, 342)),
        ("ROAD FROM MEGARA", (506, 488, 836, 540), (614, 504)),
        ("ATHENS", (920, 394, 1104, 446), (980, 430)),
        ("ACROPOLIS", (1084, 150, 1292, 202), (1148, 208)),
        ("CITIZENS RECEIVE HIM", (1010, 514, 1340, 566), (1110, 526)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=21, min_size=10), (rect[0], rect[1]))

    route_key = make_route_key(records)
    paste_with_shadow(page, route_key, (32, 748))

    fate_note = make_compact_callout(
        "Pausanias frames the dynastic repair against a darker rule: human planning cannot step around what is assigned by the god.",
        (374, 106),
        "callout:fate",
        records,
    )
    paste_with_shadow(page, fate_note, (32, 990))
    draw_polyline_leader(draw, [(406, 1042), (424, 1042), (450, 990)])

    thrace_art = crop_to_fill(THRACE_ART, (416, 248), centering=(0.50, 0.49))
    thrace_art = warm_art(thrace_art, grain_strength=0.022)
    thrace_panel = make_inset_panel(
        thrace_art,
        "Pandion's marriage alliance with the Thracian Tereus promises power, but the daughters' story turns toward vengeance.",
        102,
        "caption:thrace",
        records,
    )
    paste_with_shadow(page, thrace_panel, (434, 714))
    paste_with_shadow(page, make_label("THRACIAN ALLIANCE", (514, 734, 782, 782), records, max_size=19, min_size=10), (514, 734))
    draw_leader(draw, (648, 812), (648, 780))

    statue_art = crop_to_fill(STATUE_ART, (384, 248), centering=(0.48, 0.50))
    statue_art = warm_art(statue_art, grain_strength=0.024)
    statue_panel = make_inset_panel(
        statue_art,
        "The passage ends by returning the reader to Athens: another statue of Pandion stood on the Acropolis.",
        102,
        "caption:statue",
        records,
    )
    paste_with_shadow(page, statue_panel, (930, 714))
    paste_with_shadow(page, make_label("PANDION ON THE ACROPOLIS", (964, 734, 1280, 782), records, max_size=17, min_size=9), (964, 734))
    draw_leader(draw, (1124, 812), (1124, 780))

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
            {"path": str(MAIN_ART), "description": "Generated raster main panel: Aegeus and the sons of Pandion return from Megara to Athens."},
            {"path": str(THRACE_ART), "description": "Generated raster inset: restrained Thracian alliance tableau for Procne, Philomela, and Tereus."},
            {"path": str(STATUE_ART), "description": "Generated raster inset: Pandion statue on the Athenian Acropolis."},
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_5_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "5" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
