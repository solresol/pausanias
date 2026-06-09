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


PASSAGE_ID = "1.8.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_8_6"
MAIN_ART = ASSET_DIR / "main_odeion_ptolemies.png"
STATUE_ART = ASSET_DIR / "ptolemaic_statues_inset.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.022) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.045)
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Sharpness(image).enhance(1.03)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.045)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


def crop_fraction(path: Path, box: tuple[float, float, float, float], size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    w, h = image.size
    crop_box = (
        round(box[0] * w),
        round(box[1] * h),
        round(box[2] * w),
        round(box[3] * h),
    )
    return ImageOps.fit(image.crop(crop_box), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


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
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((378, 338))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "PTOLEMIES IN ATHENS",
            TITLE_FONT,
            max_size=18,
            min_size=10,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 234)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 24).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#84794f", white="#f3dcaa")
    sea = Image.new("RGB", land.size, "#78979b")
    mask = Image.new("L", land.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (122, 0), (108, 42), (150, 80), (114, 120), (86, 162), (0, 162)], fill=215)
    mdraw.polygon([(232, 74), (318, 98), (318, 162), (206, 162), (210, 122)], fill=210)
    mdraw.ellipse((132, 72, 178, 106), fill=190)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(7)))
    base = warm_art(base, grain_strength=0.06)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "ATHENS": (94, 70),
        "RHODES": (156, 100),
        "ALEXANDRIA": (226, 130),
    }
    route = [points["ALEXANDRIA"], points["RHODES"], points["ATHENS"]]
    route_abs = [(map_rect[0] + x, map_rect[1] + y) for x, y in route]
    draw.line(route_abs, fill="#7b493a", width=4)
    draw.line(route_abs, fill="#f4ead6", width=1)
    for x, y in route_abs:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("ATHENS", (58, 88, 136, 112), "locator:athens"),
        ("RHODES", (146, 150, 228, 174), "locator:rhodes"),
        ("EGYPT", (238, 186, 310, 210), "locator:egypt"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=10,
                min_size=6,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "Pausanias' statue row makes Egyptian dynastic memory part of the Agora's civic route."
    records.append(
        draw_fitted_text(
            draw,
            (22, 248, panel.width - 22, panel.height - 14),
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


def make_names_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 318))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 64)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "ONE ROYAL NAME, MANY SURNAMES",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="names:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("PTOLEMY SOTER", "son of Lagus; named Savior by the Rhodians"),
        ("PTOLEMY PHILADELPHOS", "the dynastic name recalled among the Eponymous Heroes"),
        ("PTOLEMY PHILOMETOR", "another royal statue, introduced before the next excursus"),
        ("ARSINOE", "sister and queen, honored close by"),
    ]
    y = 82
    for idx, (name, note) in enumerate(rows):
        row_rect = (24, y, panel.width - 24, y + 48)
        draw.rounded_rectangle(row_rect, radius=9, fill="#f3dfb4" if idx % 2 == 0 else "#f7e8c8", outline="#b8945a", width=1)
        name_rect = (34, y + 6, 174, y + 42)
        note_rect = (184, y + 5, panel.width - 34, y + 43)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"names:name:{idx}",
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
                max_size=11,
                min_size=7,
                padding=2,
                name=f"names:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 54
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, STATUE_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 622)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.51))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 704)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.8.6",
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
            min_size=10,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (616, 54, 1120, 116)
    paste_with_shadow(
        page,
        make_label("PTOLEMIES AT THE ODEION", title_rect, records, font_path=TITLE_FONT, max_size=21, min_size=11),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ACROPOLIS", (470, 122, 650, 168), (526, 120), 15),
        ("ODEION ENTRANCE", (1000, 126, 1300, 174), (1114, 240), 15),
        ("PTOLEMAIC KINGS", (760, 360, 1044, 408), (830, 476), 15),
        ("ARSINOE", (1128, 430, 1286, 478), (1216, 450), 15),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    soter_note = make_compact_callout(
        "The title Soter, Savior, was attached to Ptolemy son of Lagus by the Rhodians.",
        (418, 92),
        "callout:soter",
        records,
    )
    draw_polyline_leader(draw, [(512, 636), (666, 552), (742, 448)])
    paste_with_shadow(page, soter_note, (462, 634))

    arsinoe_note = make_compact_callout(
        "A nearby image of Arsinoe turns the royal row into a dynastic display, not just a list of kings.",
        (438, 92),
        "callout:arsinoe",
        records,
    )
    draw_polyline_leader(draw, [(918, 636), (1052, 548), (1216, 450)])
    paste_with_shadow(page, arsinoe_note, (912, 634))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 736))

    statue_crop = crop_fraction(STATUE_ART, (0.00, 0.01, 0.93, 0.88), (420, 220))
    statue_crop = warm_art(statue_crop, grain_strength=0.018)
    statue_panel = make_inset_panel(
        statue_crop,
        "The female royal image beside the Ptolemies gives Pausanias' statue row a dynastic frame.",
        92,
        "inset:statues-caption",
        records,
    )
    paste_with_shadow(page, statue_panel, (440, 754))
    statue_label = (552, 772, 760, 808)
    draw_leader(draw, (670, 880), (statue_label[0], statue_label[1] + 18))
    paste_with_shadow(page, make_label("ARSINOE NEARBY", statue_label, records, max_size=12, min_size=6), (statue_label[0], statue_label[1]))

    names_panel = make_names_panel(records)
    paste_with_shadow(page, names_panel, (904, 754))

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
            "graphic_book/images/1/8/5.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ea866-1673-7842-9819-a268aa475f1c/ig_0a7e71d3e0dd33a3016a2703eca8f4819183098a2fae3a2567.png",
                "description": "Generated raster main panel: Odeion entrance in the Athenian Agora with Ptolemaic royal statues and Acropolis background.",
            },
            {
                "path": str(STATUE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ea866-1673-7842-9819-a268aa475f1c/ig_0a7e71d3e0dd33a3016a27046b34e481919de2d385d15665a0.png",
                "description": "Generated raster inset: close study of Ptolemaic royal statues with Arsinoe-like female figure.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_8_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "8" / "6.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
