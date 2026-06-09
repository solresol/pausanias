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
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.8.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_8_3"
MAIN_ART = ASSET_DIR / "main_demosthenes_calaureia.png"
ARCHIAS_ART = ASSET_DIR / "archias_antipater_exiles.png"


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
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.96)
    image = ImageEnhance.Sharpness(image).enhance(1.03)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.04)
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
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 338))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "EXILE AND PURSUIT",
            TITLE_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 238)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.35, 0.47))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.4)), grain_strength=0.05)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.28)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "LAMIA": (82, 94),
        "ATHENS": (98, 146),
        "TROEZEN": (224, 184),
        "CALAUREIA": (270, 134),
    }
    draw.line([points["LAMIA"], points["ATHENS"]], fill="#526b73", width=3)
    draw.line([points["ATHENS"], points["TROEZEN"], points["CALAUREIA"]], fill="#7b493a", width=3)
    for name, color in [
        ("LAMIA", "#7f4e35"),
        ("ATHENS", "#3f5f72"),
        ("TROEZEN", "#6b5735"),
        ("CALAUREIA", "#7b493a"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    label_specs = [
        ("LAMIA", (46, 96, 120, 120), "locator:lamia"),
        ("ATHENS", (58, 152, 142, 176), "locator:athens"),
        ("TROEZEN", (184, 190, 276, 214), "locator:troezen"),
        ("CALAUREIA", (222, 112, 336, 136), "locator:calaureia"),
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

    caption = "After the defeat in Thessaly, Demosthenes' route runs from Athens to Calaureia off Troezen."
    records.append(
        draw_fitted_text(
            draw,
            (22, 252, panel.width - 22, panel.height - 14),
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
    for asset in [MAIN_ART, ARCHIAS_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 660)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.56, 0.48))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 706)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.8.3",
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
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (590, 54, 1214, 116)
    paste_with_shadow(
        page,
        make_label("DEMOSTHENES AT CALAUREIA", title_rect, records, font_path=TITLE_FONT, max_size=21, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("SARONIC GULF", (476, 150, 696, 196), (572, 238), 15),
        ("TROEZEN MAINLAND", (566, 274, 842, 320), (650, 352), 14),
        ("SANCTUARY OF POSEIDON", (922, 138, 1282, 184), (1010, 246), 14),
        ("DEMOSTHENES' CUP", (962, 430, 1238, 476), (1086, 408), 14),
        ("ARCHIAS' MEN APPROACH", (510, 520, 838, 566), (648, 518), 13),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    final_note = make_compact_callout(
        "The sanctuary becomes the last refuge: Pausanias frames the death as the cost of democratic loyalty.",
        (456, 94),
        "callout:sanctuary-refuge",
        records,
    )
    draw_polyline_leader(draw, [(1178, 648), (1128, 584), (1094, 408)])
    paste_with_shadow(page, final_note, (916, 648))

    pursuit_note = make_compact_callout(
        "Archias' pursuit turns a political defeat into a purge of Greek opponents of Macedon.",
        (420, 94),
        "callout:pursuit",
        records,
    )
    draw_polyline_leader(draw, [(496, 650), (574, 590), (648, 518)])
    paste_with_shadow(page, pursuit_note, (430, 648))

    locator = make_locator(records)
    paste_with_shadow(page, locator, (32, 748))

    archias_art = warm_art(crop_to_fill(ARCHIAS_ART, (514, 218), centering=(0.52, 0.50)), grain_strength=0.018)
    archias_panel = make_inset_panel(
        archias_art,
        "Archias of Thurii delivers anti-Macedonian exiles to Antipater's punishment.",
        92,
        "inset:archias-caption",
        records,
    )
    paste_with_shadow(page, archias_panel, (430, 752))
    archias_label = (554, 772, 824, 808)
    draw_leader(draw, (678, 872), (archias_label[0], archias_label[1] + 18))
    paste_with_shadow(page, make_label("ARCHIAS BEFORE ANTIPATER", archias_label, records, max_size=11, min_size=6), (archias_label[0], archias_label[1]))

    legacy_panel = framed_panel((420, 336))
    legacy_draw = ImageDraw.Draw(legacy_panel)
    legacy_title = (24, 18, legacy_panel.width - 24, 66)
    legacy_draw.rounded_rectangle(legacy_title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            legacy_draw,
            legacy_title,
            "THE ATHENIAN VERDICT",
            TITLE_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="legacy:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            legacy_draw,
            (34, 92, legacy_panel.width - 34, 190),
            "Pausanias singles out Demosthenes as the one exile not handed over by Archias.",
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=7,
            name="legacy:note1",
            align="center",
            spacing_ratio=0.14,
        )
    )
    records.append(
        draw_fitted_text(
            legacy_draw,
            (34, 212, legacy_panel.width - 34, legacy_panel.height - 28),
            "The closing judgement links his death to reckless public service and a stubborn faith in democracy.",
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=7,
            name="legacy:note2",
            align="center",
            spacing_ratio=0.14,
        )
    )
    paste_with_shadow(page, legacy_panel, (952, 752))

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
            "graphic_book/images/1/8/2.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e98f1-a998-7101-8ecd-af5ff2d8501f/ig_081c67830d1303fd016a230f6487a4819198c9758097137fe1.png",
                "description": "Generated raster main panel: Demosthenes at the sanctuary of Poseidon on Calaureia with Saronic geography and approaching pursuers.",
            },
            {
                "path": str(ARCHIAS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e98f1-a998-7101-8ecd-af5ff2d8501f/ig_081c67830d1303fd016a23106aaff48191a8cb54aa6dc1bbbd.png",
                "description": "Generated raster inset: Archias-style hand-over of Greek exiles before a Macedonian commander.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_8_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "8" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
