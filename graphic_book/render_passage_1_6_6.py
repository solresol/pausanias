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
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.6.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_6"
MAIN_ART = ASSET_DIR / "main_pelusium_defense.png"
CYPRUS_ART = ASSET_DIR / "cyprus_naval_battle.png"
RHODES_ART = ASSET_DIR / "rhodes_siege.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.025) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.90)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.035)
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
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_route_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 300))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "CYPRUS TO EGYPT TO RHODES",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="route-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 202)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.62, 0.42))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.6)), grain_strength=0.045)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.56)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "CYPRUS": (238, 122),
        "PELUSIUM": (170, 170),
        "RHODES": (112, 100),
        "ANTIGONUS": (94, 160),
        "DEMETRIUS": (238, 96),
    }
    draw.line([points["CYPRUS"], points["PELUSIUM"]], fill="#3f6275", width=4)
    draw.line([points["PELUSIUM"], points["RHODES"]], fill="#7f4e35", width=3)
    draw.line([points["ANTIGONUS"], points["PELUSIUM"]], fill="#6b5735", width=3)
    draw.line([points["DEMETRIUS"], points["PELUSIUM"]], fill="#3f6275", width=2)

    for name, color in [
        ("RHODES", "#7f4e35"),
        ("CYPRUS", "#3f6275"),
        ("PELUSIUM", "#365c75"),
        ("ANTIGONUS", "#6b5735"),
        ("DEMETRIUS", "#3f6275"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("RHODES", (70, 78, 142, 100), "route-key:rhodes"),
        ("CYPRUS", (214, 122, 288, 144), "route-key:cyprus"),
        ("PELUSIUM", (128, 178, 218, 200), "route-key:pelusium"),
        ("LAND", (48, 148, 100, 170), "route-key:land"),
        ("SEA", (244, 78, 294, 100), "route-key:sea"),
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

    caption = "Cyprus gives Demetrius the naval advantage; Pelusium stops Egypt from falling; Rhodes becomes the next target."
    records.append(
        draw_fitted_text(
            draw,
            (24, 214, panel.width - 24, panel.height - 12),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="route-key:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, CYPRUS_ART, RHODES_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 628)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 734)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.6.6",
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
            min_size=10,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.14,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (608, 56, 1204, 118)
    paste_with_shadow(
        page,
        make_label("EGYPT HOLDS AT PELUSIUM", title_rect, records, font_path=TITLE_FONT, max_size=23, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ANTIGONUS BY LAND", (500, 202, 728, 252), (620, 350)),
        ("PTOLEMAIC CAMP", (486, 472, 704, 522), (512, 496)),
        ("PELUSIUM", (752, 506, 900, 556), (720, 542)),
        ("NILE MOUTH", (900, 356, 1058, 406), (940, 414)),
        ("DEMETRIUS BY SEA", (1054, 466, 1302, 516), (1126, 516)),
        ("EGYPT", (1194, 558, 1306, 606), (1030, 558)),
    ]

    route_key = make_route_key(records)
    paste_with_shadow(page, route_key, (32, 752))

    draw_polyline_leader(draw, [(630, 656), (650, 612), (620, 350)])
    draw_polyline_leader(draw, [(730, 656), (910, 612), (1126, 516)])
    pressure_note = make_compact_callout(
        "Antigonus attacks Egypt by land while Demetrius threatens from the water after Cyprus.",
        (398, 98),
        "callout:two-front-pressure",
        records,
    )
    paste_with_shadow(page, pressure_note, (430, 656))

    draw_polyline_leader(draw, [(1080, 656), (920, 602), (720, 542)])
    draw_polyline_leader(draw, [(1160, 656), (1034, 584), (940, 414)])
    defense_note = make_compact_callout(
        "Ptolemy survives by guarding Pelusium and setting his fleet on the river.",
        (398, 98),
        "callout:pelusium-defense",
        records,
    )
    paste_with_shadow(page, defense_note, (882, 656))

    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=18, min_size=8), (rect[0], rect[1]))

    cyprus_art = warm_art(crop_to_fill(CYPRUS_ART, (360, 208), centering=(0.52, 0.50)), grain_strength=0.02)
    cyprus_panel = make_inset_panel(
        cyprus_art,
        "Off Cyprus, Demetrius defeats Menelaus and then Ptolemy himself.",
        66,
        "inset:cyprus-caption",
        records,
    )
    paste_with_shadow(page, cyprus_panel, (430, 792))

    rhodes_art = warm_art(crop_to_fill(RHODES_ART, (360, 208), centering=(0.50, 0.50)), grain_strength=0.02)
    rhodes_panel = make_inset_panel(
        rhodes_art,
        "When Egypt cannot be taken, Antigonus sends Demetrius against Rhodes.",
        66,
        "inset:rhodes-caption",
        records,
    )
    paste_with_shadow(page, rhodes_panel, (904, 792))

    for text, rect, point in [
        ("CYPRUS", (472, 804, 590, 842), (620, 906)),
        ("RHODES", (944, 804, 1068, 842), (1070, 902)),
    ]:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=15, min_size=8), (rect[0], rect[1]))

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
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Ptolemaic defense of Pelusium and the Nile mouth under land-and-sea pressure.",
            },
            {
                "path": str(CYPRUS_ART),
                "description": "Generated raster inset: Demetrius' naval victory off Cyprus.",
            },
            {
                "path": str(RHODES_ART),
                "description": "Generated raster inset: siege preparations before Rhodes.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "6.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
