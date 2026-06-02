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


PASSAGE_ID = "1.7.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_7_1"
MAIN_ART = ASSET_DIR / "main_alexander_transfer_egypt.png"
MEMPHIS_ART = ASSET_DIR / "memphis_sarcophagus_procession.png"
CYRENE_ART = ASSET_DIR / "magas_cyrene_march.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.024) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Sharpness(image).enhance(1.03)
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
            max_size=16,
            min_size=9,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_locator_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 340))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "CYRENE TO EGYPT",
            TITLE_FONT,
            max_size=18,
            min_size=10,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 244)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.54, 0.50))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.5)), grain_strength=0.05)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.38)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "CYRENE": (76, 188),
        "ALEXANDRIA": (192, 168),
        "MEMPHIS": (210, 214),
        "CYPRUS": (254, 120),
    }
    draw.line([points["CYRENE"], points["ALEXANDRIA"], points["MEMPHIS"]], fill="#7f4e35", width=4)
    draw.line([points["ALEXANDRIA"], points["CYPRUS"]], fill="#365c75", width=3)
    for name, color in [
        ("CYRENE", "#7f4e35"),
        ("ALEXANDRIA", "#7b493a"),
        ("MEMPHIS", "#8a6c31"),
        ("CYPRUS", "#365c75"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("CYRENE", (40, 194, 118, 218), "locator:cyrene"),
        ("ALEXANDRIA", (138, 142, 252, 166), "locator:alexandria"),
        ("MEMPHIS", (178, 218, 262, 242), "locator:memphis"),
        ("CYPRUS", (222, 94, 294, 118), "locator:cyprus"),
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

    caption = "Magas wins Cyrene and marches east against Egypt while Ptolemy's dynastic violence keeps the story anchored in Alexandria and Memphis."
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


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, MEMPHIS_ART, CYRENE_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 642)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 688)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.7.1",
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
            max_size=17,
            min_size=10,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (668, 56, 1144, 118)
    paste_with_shadow(
        page,
        make_label("PTOLEMY II AND ALEXANDER", title_rect, records, font_path=TITLE_FONT, max_size=21, min_size=11),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ALEXANDRIA", (692, 126, 884, 174), (790, 162)),
        ("NILE DELTA", (820, 342, 1008, 388), (912, 380)),
        ("MEMPHIS", (1120, 478, 1260, 524), (1168, 520)),
        ("ALEXANDER'S BODY", (516, 524, 756, 572), (566, 514)),
        ("CYPRUS", (1190, 156, 1316, 202), (1242, 180)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=17, min_size=8), (rect[0], rect[1]))

    route_note = make_compact_callout(
        "Pausanias says this Ptolemy transferred Alexander's corpse from Memphis.",
        (372, 86),
        "callout:alexander-transfer",
        records,
    )
    draw_polyline_leader(draw, [(794, 654), (710, 586), (590, 520)])
    paste_with_shadow(page, route_note, (604, 650))

    dynastic_note = make_compact_callout(
        "The same passage turns dynastic: Arsinoe, Argaeus, Eurydice's son, and a threatened revolt in Cyprus.",
        (400, 96),
        "callout:dynastic-violence",
        records,
    )
    draw_polyline_leader(draw, [(1122, 650), (1166, 560), (1246, 180)])
    paste_with_shadow(page, dynastic_note, (944, 646))

    locator = make_locator_key(records)
    paste_with_shadow(page, locator, (32, 724))

    memphis_art = warm_art(crop_to_fill(MEMPHIS_ART, (420, 218), centering=(0.52, 0.50)), grain_strength=0.02)
    memphis_panel = make_inset_panel(
        memphis_art,
        "At Memphis, Alexander's body becomes a Ptolemaic object of rule before its transfer north.",
        78,
        "inset:memphis-caption",
        records,
    )
    paste_with_shadow(page, memphis_panel, (430, 760))
    memphis_label = (552, 780, 786, 816)
    draw_leader(draw, (652, 878), (memphis_label[0], memphis_label[1] + 18))
    paste_with_shadow(page, make_label("MEMPHIS PROCESSION", memphis_label, records, max_size=13, min_size=7), (memphis_label[0], memphis_label[1]))

    cyrene_art = warm_art(crop_to_fill(CYRENE_ART, (404, 218), centering=(0.50, 0.52)), grain_strength=0.02)
    cyrene_panel = make_inset_panel(
        cyrene_art,
        "Magas wins over the Cyreneans and marches from Libya toward Egypt.",
        78,
        "inset:cyrene-caption",
        records,
    )
    paste_with_shadow(page, cyrene_panel, (918, 760))
    cyrene_label = (1040, 780, 1196, 816)
    draw_leader(draw, (1082, 884), (cyrene_label[0], cyrene_label[1] + 18))
    paste_with_shadow(page, make_label("MAGAS", cyrene_label, records, max_size=15, min_size=8), (cyrene_label[0], cyrene_label[1]))

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
            "graphic_book/images/1/6/8.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Ptolemaic Egypt with Alexander's sarcophagus transfer from Memphis toward Alexandria.",
            },
            {
                "path": str(MEMPHIS_ART),
                "description": "Generated raster inset: Memphis procession and Alexander's sarcophagus.",
            },
            {
                "path": str(CYRENE_ART),
                "description": "Generated raster inset: Magas and Cyrenaean forces marching east.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_7_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "7" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
