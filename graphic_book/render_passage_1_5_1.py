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


PASSAGE_ID = "1.5.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_5_1"
MAIN_ART = ASSET_DIR / "main_agora_tholos_bouleuterion.png"
RITUAL_ART = ASSET_DIR / "tholos_silver_statues.png"
HEROES_ART = ASSET_DIR / "eponymous_heroes_monument.png"


def load_translation() -> str:
    db_path = root_dir() / "pausanias.sqlite"
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


def warm_art(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.96)
    image = ImageEnhance.Sharpness(image).enhance(1.025)
    wash = Image.new("RGB", image.size, "#e4c58d")
    image = Image.blend(image, wash, 0.045)
    grain = Image.effect_noise(image.size, 5).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#987143", white="#fff1cf")
    return Image.blend(image, grain_rgb, 0.03)


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


def make_orientation_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((364, 186))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 12, panel.width - 18, 50)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "CIVIC SLOPE",
            TITLE_FONT,
            max_size=19,
            min_size=13,
            padding=6,
            name="orientation:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    items = [
        "Bouleuterion: council setting",
        "Tholos: Prytaneis sacrifice",
        "Higher: eponymous heroes",
    ]
    y = 66
    for idx, item in enumerate(items, start=1):
        draw.ellipse((24, y + 4, 38, y + 18), fill="#7d5430", outline="#f0d492", width=1)
        records.append(
            draw_fitted_text(
                draw,
                (48, y - 3, panel.width - 22, y + 30),
                f"{idx}. {item}",
                BODY_FONT,
                max_size=15,
                min_size=11,
                padding=3,
                name=f"orientation:item:{idx}",
                spacing_ratio=0.10,
            )
        )
        y += 39
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, RITUAL_ART, HEROES_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 38, 1372, 660)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.51, 0.50),
    )
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 714)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.5.1",
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
            max_size=23,
            min_size=13,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (646, 54, 1214, 118)
    paste_with_shadow(
        page,
        make_label("THOLOS AND TRIBAL HEROES", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=14),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("THOLOS", (594, 242, 738, 292), (706, 372)),
        ("COUNCIL HOUSE", (1112, 176, 1352, 228), (1168, 286)),
        ("PRYTANEIS SACRIFICE", (982, 522, 1312, 576), (1022, 546)),
        ("SILVER STATUES", (820, 150, 1064, 202), (956, 396)),
        ("EPONYMOUS HEROES", (496, 410, 806, 464), (666, 448)),
        ("UP THE CIVIC SLOPE", (452, 586, 742, 638), (574, 580)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=21, min_size=11), (rect[0], rect[1]))

    orientation_key = make_orientation_key(records)
    paste_with_shadow(page, orientation_key, (34, 754))

    note = make_compact_callout(
        "The passage moves a few steps in the Agora: from council administration to ritual dining and then to the tribal heroes above.",
        (364, 116),
        "callout:movement",
        records,
    )
    paste_with_shadow(page, note, (34, 974))
    draw_polyline_leader(draw, [(398, 1028), (508, 906), (620, 610)])

    ritual_art = warm_art(crop_to_fill(RITUAL_ART, (398, 222), centering=(0.54, 0.52)))
    ritual_panel = make_inset_panel(
        ritual_art,
        "The Prytaneis sacrifice in the Tholos, with small silver statues shown as votive markers.",
        92,
        "caption:ritual",
        records,
    )
    paste_with_shadow(page, ritual_panel, (438, 724))
    paste_with_shadow(page, make_label("RITUAL AND SILVER", (530, 742, 764, 790), records, max_size=21, min_size=12), (530, 742))
    draw_leader(draw, (646, 824), (646, 788))

    heroes_art = warm_art(crop_to_fill(HEROES_ART, (414, 222), centering=(0.36, 0.50)))
    heroes_panel = make_inset_panel(
        heroes_art,
        "The eponymous heroes turn the local monument into a map of Athenian tribal identity.",
        92,
        "caption:heroes",
        records,
    )
    paste_with_shadow(page, heroes_panel, (902, 724))
    paste_with_shadow(page, make_label("TEN TRIBAL NAMES", (1000, 742, 1284, 790), records, max_size=21, min_size=12), (1000, 742))
    draw_leader(draw, (1142, 824), (1142, 788))

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
    report_path = root_dir() / "tmp" / "passage_1_5_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "5" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
