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


PASSAGE_ID = "1.6.8"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_8"
MAIN_ART = ASSET_DIR / "main_ptolemaic_eastern_mediterranean.png"
SUCCESSION_ART = ASSET_DIR / "berenice_succession.png"
CYRENE_ART = ASSET_DIR / "cyrene_magas.png"


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


def make_dynastic_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 390))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "PTOLEMAIC REACH",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="dynastic-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 268)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.50, 0.54))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.25)), grain_strength=0.05)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.46)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "ALEXANDRIA": (172, 218),
        "CYPRUS": (218, 162),
        "SYRIA": (282, 132),
        "EPIRUS": (86, 100),
        "CYRENE": (92, 218),
    }
    draw.line([points["ALEXANDRIA"], points["CYPRUS"], points["SYRIA"]], fill="#365c75", width=3)
    draw.line([points["ALEXANDRIA"], points["CYRENE"]], fill="#7f4e35", width=3)
    draw.line([points["ALEXANDRIA"], points["EPIRUS"]], fill="#6b5735", width=3)

    for name, color in [
        ("ALEXANDRIA", "#7b493a"),
        ("CYPRUS", "#365c75"),
        ("SYRIA", "#8a6c31"),
        ("EPIRUS", "#6b5735"),
        ("CYRENE", "#7f4e35"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("EPIRUS", (46, 82, 124, 106), "dynastic-key:epirus"),
        ("SYRIA", (246, 108, 316, 132), "dynastic-key:syria"),
        ("CYPRUS", (182, 138, 260, 162), "dynastic-key:cyprus"),
        ("CYRENE", (52, 224, 132, 248), "dynastic-key:cyrene"),
        ("ALEXANDRIA", (124, 230, 230, 254), "dynastic-key:alexandria"),
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

    caption = "After Antigonus, Ptolemy's story ranges from Syria and Cyprus to Epirus and Cyrene, while succession returns the focus to Egypt."
    records.append(
        draw_fitted_text(
            draw,
            (22, 284, panel.width - 22, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=13,
            min_size=8,
            padding=5,
            name="dynastic-key:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, SUCCESSION_ART, CYRENE_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 626)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 636)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.6.8",
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
    title_rect = (658, 56, 1152, 118)
    paste_with_shadow(
        page,
        make_label("PTOLEMY'S SUCCESSION", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ALEXANDRIA", (606, 492, 792, 542), (650, 422)),
        ("NILE DELTA", (820, 408, 1018, 456), (868, 430)),
        ("CYPRUS", (780, 246, 928, 294), (798, 256)),
        ("SYRIA", (1084, 224, 1218, 272), (1130, 252)),
        ("PTOLEMAIC COURT", (1084, 382, 1320, 430), (1168, 466)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=17, min_size=8), (rect[0], rect[1]))

    dynastic_key = make_dynastic_key(records)
    paste_with_shadow(page, dynastic_key, (32, 662))

    draw_polyline_leader(draw, [(548, 652), (656, 588), (682, 486)])
    rule_note = make_compact_callout(
        "Ptolemy recovers Syria and Cyprus, then the passage turns from conquest to family succession.",
        (386, 96),
        "callout:recovery-succession",
        records,
    )
    paste_with_shadow(page, rule_note, (430, 648))

    succession_art = warm_art(crop_to_fill(SUCCESSION_ART, (420, 198), centering=(0.50, 0.49)), grain_strength=0.02)
    succession_panel = make_inset_panel(
        succession_art,
        "Berenice's son, not Eurydice's, receives Egypt; Pausanias links this heir to the Athenian tribal name.",
        84,
        "inset:succession-caption",
        records,
    )
    paste_with_shadow(page, succession_panel, (430, 768))
    succession_label = (584, 788, 786, 824)
    draw_leader(draw, (710, 882), (succession_label[0], succession_label[1] + 18))
    paste_with_shadow(page, make_label("BERENICE'S HEIR", succession_label, records, max_size=14, min_size=8), (succession_label[0], succession_label[1]))

    cyrene_art = warm_art(crop_to_fill(CYRENE_ART, (402, 214), centering=(0.48, 0.51)), grain_strength=0.02)
    cyrene_panel = make_inset_panel(
        cyrene_art,
        "Magas, Berenice's son, takes Cyrene in the fifth year after its revolt.",
        74,
        "inset:cyrene-caption",
        records,
    )
    paste_with_shadow(page, cyrene_panel, (916, 774))
    cyrene_label = (1038, 792, 1168, 828)
    draw_leader(draw, (1072, 894), (cyrene_label[0], cyrene_label[1] + 18))
    paste_with_shadow(page, make_label("CYRENE", cyrene_label, records, max_size=14, min_size=8), (cyrene_label[0], cyrene_label[1]))

    draw_polyline_leader(draw, [(1038, 654), (1122, 596), (1168, 466)])
    heir_note = make_compact_callout(
        "The Athenian tribe takes its name from the later Ptolemy, child of Berenice.",
        (394, 96),
        "callout:athenian-tribe",
        records,
    )
    paste_with_shadow(page, heir_note, (870, 648))

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
            "graphic_book/images/1/6/7.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Ptolemaic Alexandria and eastern Mediterranean orientation.",
            },
            {
                "path": str(SUCCESSION_ART),
                "description": "Generated raster inset: Berenice, Eurydice, and Ptolemaic succession.",
            },
            {
                "path": str(CYRENE_ART),
                "description": "Generated raster inset: Cyrene after revolt under Magas.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_8_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "8.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
