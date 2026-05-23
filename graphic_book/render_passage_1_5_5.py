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


PASSAGE_ID = "1.5.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_5_5"
MAIN_ART = ASSET_DIR / "main_hadrianic_eponymous_heroes.png"
SANCTUARY_ART = ASSET_DIR / "common_sanctuary_register.png"
ENVOYS_ART = ASSET_DIR / "hadrian_benefaction_envoys.png"


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
    image = ImageEnhance.Contrast(image).enhance(1.05)
    image = ImageEnhance.Color(image).enhance(0.90)
    image = ImageEnhance.Sharpness(image).enhance(1.06)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.07)
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
            max_size=17,
            min_size=11,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.15,
        )
    )
    return panel


def make_wider_frame_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 236))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ATHENS AND THE WIDER FRAME",
            TITLE_FONT,
            max_size=17,
            min_size=10,
            padding=5,
            name="frame:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 70, panel.width - 28, 168)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.53, 0.48))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(2.0)), grain_strength=0.045)
    tint = Image.new("RGB", base.size, "#ead7ad")
    base = Image.blend(base, tint, 0.52)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    athens = (170, 126)
    mysia = (74, 98)
    egypt = (126, 150)
    judaea = (226, 148)
    cities = (266, 92)
    for point in [mysia, egypt, judaea, cities]:
        draw.line([athens, point], fill="#8a5d34", width=3)
    for point, color in [
        (athens, "#3f5f72"),
        (mysia, "#7d5430"),
        (egypt, "#8c6a2f"),
        (judaea, "#8c3d2e"),
        (cities, "#56715a"),
    ]:
        draw.ellipse((point[0] - 8, point[1] - 8, point[0] + 8, point[1] + 8), fill=color, outline="#f5e3ba", width=2)

    label_specs = [
        ("MYSIA", (42, 76, 108, 102), "frame:mysia"),
        ("ATHENS", (132, 130, 212, 156), "frame:athens"),
        ("EGYPT", (92, 158, 166, 184), "frame:egypt"),
        ("JUDAEA", (210, 156, 292, 182), "frame:judaea"),
        ("GREEK CITIES", (222, 66, 346, 92), "frame:cities"),
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
                min_size=7,
                padding=3,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "Later tribal names tie Athens to Mysia, Egypt, Greek cities, and Judaea."
    records.append(
        draw_fitted_text(
            draw,
            (24, 188, panel.width - 24, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=13,
            min_size=9,
            padding=5,
            name="frame:caption",
            align="center",
            spacing_ratio=0.13,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, SANCTUARY_ART, ENVOYS_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.48),
    )
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 720)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.5.5",
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
            max_size=19,
            min_size=12,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.15,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (642, 56, 1206, 118)
    paste_with_shadow(
        page,
        make_label("LATER TRIBAL FOUNDERS", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=13),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("EPONYMOUS HEROES", (502, 154, 824, 206), (628, 254)),
        ("ATTALUS", (520, 358, 684, 410), (578, 330)),
        ("PTOLEMY", (708, 312, 884, 364), (754, 306)),
        ("HADRIAN", (984, 214, 1168, 266), (1046, 266)),
        ("ACROPOLIS", (1092, 142, 1288, 194), (1162, 134)),
        ("ATHENS", (952, 456, 1112, 508), (1002, 488)),
        ("COMMON SANCTUARY", (1044, 542, 1340, 594), (1138, 518)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=19, min_size=9), (rect[0], rect[1]))

    frame_key = make_wider_frame_key(records)
    paste_with_shadow(page, frame_key, (32, 748))

    war_note = make_compact_callout(
        "Pausanias notes that Hadrian entered no voluntary war; the Jewish revolt sits apart from the catalogue of gifts.",
        (374, 114),
        "callout:war-note",
        records,
    )
    paste_with_shadow(page, war_note, (32, 990))
    draw_polyline_leader(draw, [(406, 1048), (424, 1048), (468, 956)])

    sanctuary_art = crop_to_fill(SANCTUARY_ART, (416, 248), centering=(0.55, 0.50))
    sanctuary_art = warm_art(sanctuary_art, grain_strength=0.022)
    sanctuary_panel = make_inset_panel(
        sanctuary_art,
        "At Athens, the common sanctuary of the gods recorded Hadrian's temples, offerings, constructions, and gifts.",
        106,
        "caption:sanctuary",
        records,
    )
    paste_with_shadow(page, sanctuary_panel, (434, 714))
    paste_with_shadow(page, make_label("COMMON SANCTUARY OF THE GODS", (474, 734, 810, 782), records, max_size=16, min_size=8), (474, 734))
    draw_leader(draw, (642, 812), (642, 780))

    envoys_art = crop_to_fill(ENVOYS_ART, (384, 248), centering=(0.48, 0.50))
    envoys_art = warm_art(envoys_art, grain_strength=0.022)
    envoys_panel = make_inset_panel(
        envoys_art,
        "The passage's Hadrian is chiefly a benefactor: Greek cities and others seeking aid receive plans, offerings, and support.",
        106,
        "caption:envoys",
        records,
    )
    paste_with_shadow(page, envoys_panel, (930, 714))
    paste_with_shadow(page, make_label("HADRIAN'S BENEFACTIONS", (976, 734, 1278, 782), records, max_size=18, min_size=9), (976, 734))
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
            {"path": str(MAIN_ART), "description": "Generated raster main panel: Hadrianic Athens and later tribal founders at the eponymous heroes monument."},
            {"path": str(SANCTUARY_ART), "description": "Generated raster inset: common sanctuary of the gods with votive offerings and unreadable benefaction register."},
            {"path": str(ENVOYS_ART), "description": "Generated raster inset: Hadrian receiving envoys, plans, and offerings as benefactor."},
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_5_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "5" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
