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


PASSAGE_ID = "1.6.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_1"
MAIN_ART = ASSET_DIR / "main_attalus_ptolemy_atlas.png"
EGYPT_ART = ASSET_DIR / "ptolemaic_egypt_archive.png"
MYSIA_ART = ASSET_DIR / "mysia_pergamon_archive.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.026) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.055)
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


def make_memory_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 230))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "DYNASTIC MEMORY",
            TITLE_FONT,
            max_size=20,
            min_size=12,
            padding=6,
            name="memory-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 72, panel.width - 28, 164)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.51, 0.52))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(2.2)), grain_strength=0.045)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.46)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    athens = (152, 126)
    mysia = (218, 96)
    egypt = (242, 146)
    for point in (mysia, egypt):
        draw.line([athens, point], fill="#8a5d34", width=3)
    for point, color in [(athens, "#3f5f72"), (mysia, "#6d5936"), (egypt, "#8c6a2f")]:
        draw.ellipse((point[0] - 8, point[1] - 8, point[0] + 8, point[1] + 8), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("ATHENS", (112, 132, 190, 158), "memory-key:athens"),
        ("MYSIA", (192, 78, 266, 104), "memory-key:mysia"),
        ("EGYPT", (218, 152, 294, 178), "memory-key:egypt"),
    ]:
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

    caption = (
        "Pausanias turns from Athenian tribal names to the older royal stories "
        "behind Attalus and Ptolemy."
    )
    records.append(
        draw_fitted_text(
            draw,
            (24, 178, panel.width - 24, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=13,
            min_size=9,
            padding=5,
            name="memory-key:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, EGYPT_ART, MYSIA_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
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
            "PASSAGE 1.6.1",
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
            spacing_ratio=0.15,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (602, 56, 1248, 118)
    paste_with_shadow(
        page,
        make_label("ATTALUS AND PTOLEMY: OLD FAME, FAINT ACCOUNTS", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("NEGLECTED ACCOUNTS", (462, 472, 768, 524), (560, 336)),
        ("MYSIA", (818, 226, 948, 278), (856, 326)),
        ("AEGEAN", (656, 308, 802, 360), (720, 402)),
        ("EGYPT", (1046, 520, 1184, 572), (1032, 500)),
        ("PTOLEMAIC COURT", (1134, 378, 1340, 430), (1146, 468)),
        ("ATTALID MEMORY", (490, 154, 726, 206), (536, 242)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=18, min_size=9), (rect[0], rect[1]))

    memory_key = make_memory_key(records)
    paste_with_shadow(page, memory_key, (32, 748))

    memory_note = make_compact_callout(
        "The excursus is prompted by a problem of evidence: fame has faded, and the writers Pausanias found had not cared enough.",
        (374, 114),
        "callout:memory-note",
        records,
    )
    paste_with_shadow(page, memory_note, (32, 990))
    draw_polyline_leader(draw, [(406, 1048), (424, 1042), (520, 502)])

    mysia_art = crop_to_fill(MYSIA_ART, (416, 248), centering=(0.50, 0.50))
    mysia_art = warm_art(mysia_art, grain_strength=0.022)
    mysia_panel = make_inset_panel(
        mysia_art,
        "Mysia frames Attalus: the Pergamene high city turns Pausanias' tribal name into a royal genealogy.",
        106,
        "caption:mysia",
        records,
    )
    paste_with_shadow(page, mysia_panel, (434, 714))
    paste_with_shadow(page, make_label("MYSIA AND ATTALUS", (496, 734, 788, 782), records, max_size=18, min_size=9), (496, 734))
    draw_leader(draw, (636, 812), (642, 780))

    egypt_art = crop_to_fill(EGYPT_ART, (384, 248), centering=(0.48, 0.50))
    egypt_art = warm_art(egypt_art, grain_strength=0.022)
    egypt_panel = make_inset_panel(
        egypt_art,
        "Egypt frames Ptolemy: Alexandria and the Nile stand for the kingdom whose earlier power Pausanias will recount.",
        106,
        "caption:egypt",
        records,
    )
    paste_with_shadow(page, egypt_panel, (930, 714))
    paste_with_shadow(page, make_label("EGYPT AND PTOLEMY", (982, 734, 1278, 782), records, max_size=18, min_size=9), (982, 734))
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
            {"path": str(MAIN_ART), "description": "Generated raster main panel: eastern Mediterranean atlas-tableau tying Attalus, Ptolemy, Egypt, Mysia, and historical memory."},
            {"path": str(EGYPT_ART), "description": "Generated raster inset: Ptolemaic Alexandria/Nile archive scene for Egypt and Ptolemy."},
            {"path": str(MYSIA_ART), "description": "Generated raster inset: Mysia/Pergamon archive-acropolis scene for Attalus."},
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
