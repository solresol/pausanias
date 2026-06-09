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


PASSAGE_ID = "1.8.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_8_1"
MAIN_ART = ASSET_DIR / "main_pergamon_mysia.png"
DOCIMUS_ART = ASSET_DIR / "docimus_lysimachus_philetaerus.png"
HANDOVER_ART = ASSET_DIR / "eumenes_attalus_handover.png"


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
    image = ImageEnhance.Color(image).enhance(0.93)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.045)
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


def make_locator_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ATTALID ORIGINS",
            TITLE_FONT,
            max_size=20,
            min_size=11,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 238)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.42, 0.50))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.5)), grain_strength=0.05)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.36)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "ATHENS": (78, 178),
        "THRACE": (132, 104),
        "PAPH": (238, 92),
        "PERGAMON": (194, 156),
        "SELEUCID": (270, 184),
    }
    for start, end, color, width in [
        ("ATHENS", "PERGAMON", "#526b73", 3),
        ("THRACE", "PERGAMON", "#7f4e35", 3),
        ("PAPH", "PERGAMON", "#6b5735", 3),
        ("PERGAMON", "SELEUCID", "#7b493a", 3),
    ]:
        draw.line([points[start], points[end]], fill=color, width=width)
    for name, color in [
        ("ATHENS", "#3f5f72"),
        ("THRACE", "#7f4e35"),
        ("PAPH", "#6b5735"),
        ("PERGAMON", "#7b493a"),
        ("SELEUCID", "#8c6a2f"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("ATHENS", (42, 184, 118, 208), "locator:athens"),
        ("THRACE", (96, 80, 172, 104), "locator:thrace"),
        ("PAPHLAGONIA", (190, 70, 306, 94), "locator:paphlagonia"),
        ("PERGAMON", (152, 158, 244, 182), "locator:pergamon"),
        ("SELEUCID ASIA", (220, 194, 330, 218), "locator:seleucid"),
    ]:
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

    caption = "Athens honors Attalus by tribe-name; Pausanias traces the royal power back through Pergamon, Philetaerus, and Seleucid conflict."
    records.append(
        draw_fitted_text(
            draw,
            (22, 250, panel.width - 22, panel.height - 14),
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
    for asset in [MAIN_ART, DOCIMUS_ART, HANDOVER_ART]:
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

    left_panel_rect = (32, 36, 406, 706)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.8.1",
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
    title_rect = (614, 56, 1218, 118)
    paste_with_shadow(
        page,
        make_label("PERGAMON AND THE RISE OF ATTALUS", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("MYSIAN COAST", (494, 166, 730, 214), (604, 230)),
        ("PERGAMON", (934, 138, 1126, 186), (1034, 282)),
        ("TREASURY CITADEL", (1052, 304, 1322, 352), (1118, 356)),
        ("GALATIANS DRIVEN INLAND", (516, 498, 852, 546), (642, 560)),
        ("ROAD FROM THE COAST", (736, 384, 1010, 432), (812, 470)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=16, min_size=8), (rect[0], rect[1]))

    dynastic_note = make_compact_callout(
        "Pausanias uses Attalus' Athenian tribal honor to open a Pergamene royal genealogy.",
        (408, 94),
        "callout:dynastic-genealogy",
        records,
    )
    draw_polyline_leader(draw, [(560, 654), (650, 596), (704, 534)])
    paste_with_shadow(page, dynastic_note, (498, 648))

    coast_note = make_compact_callout(
        "Attalus' remembered victory pushes the Gauls away from the sea and into the interior.",
        (386, 94),
        "callout:gauls-inland",
        records,
    )
    draw_polyline_leader(draw, [(1070, 654), (980, 590), (716, 560)])
    paste_with_shadow(page, coast_note, (984, 648))

    locator = make_locator_key(records)
    paste_with_shadow(page, locator, (32, 748))

    docimus_art = warm_art(crop_to_fill(DOCIMUS_ART, (420, 218), centering=(0.50, 0.50)), grain_strength=0.02)
    docimus_panel = make_inset_panel(
        docimus_art,
        "Docimus passes from Antigonus to Lysimachus; Philetaerus stands near the documents and chests.",
        86,
        "inset:docimus-caption",
        records,
    )
    paste_with_shadow(page, docimus_panel, (430, 752))
    docimus_label = (532, 772, 804, 808)
    draw_leader(draw, (642, 874), (docimus_label[0], docimus_label[1] + 18))
    paste_with_shadow(page, make_label("DOCIMUS AND PHILETAERUS", docimus_label, records, max_size=12, min_size=6), (docimus_label[0], docimus_label[1]))

    handover_art = warm_art(crop_to_fill(HANDOVER_ART, (404, 218), centering=(0.50, 0.50)), grain_strength=0.02)
    handover_panel = make_inset_panel(
        handover_art,
        "Eumenes hands rule to Attalus, who becomes the royal figure Athens later honors by tribe-name.",
        86,
        "inset:handover-caption",
        records,
    )
    paste_with_shadow(page, handover_panel, (918, 752))
    handover_label = (1034, 772, 1226, 808)
    draw_leader(draw, (1118, 874), (handover_label[0], handover_label[1] + 18))
    paste_with_shadow(page, make_label("EUMENES TO ATTALUS", handover_label, records, max_size=12, min_size=6), (handover_label[0], handover_label[1]))

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
            "graphic_book/images/1/7/3.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e8ea5-7ac3-7a82-82a3-e282a4d241d8/ig_0c5560e6948ffb1c016a206c30374881918cc82aced389f113.png",
                "description": "Generated raster main panel: oblique Pergamon and Mysia landscape with citadel, coast, roads, and Galatians moving inland.",
            },
            {
                "path": str(DOCIMUS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e8ea5-7ac3-7a82-82a3-e282a4d241d8/ig_0c5560e6948ffb1c016a206cc625e08191bb10772fac4cabf3.png",
                "description": "Generated raster inset: Docimus submitting to Lysimachus with Philetaerus near chests and documents.",
            },
            {
                "path": str(HANDOVER_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e8ea5-7ac3-7a82-82a3-e282a4d241d8/ig_0c5560e6948ffb1c016a206d1112808191b71d448f8bc51ee5.png",
                "description": "Generated raster inset: Eumenes transferring authority to Attalus before the Pergamene treasury.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_8_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "8" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
