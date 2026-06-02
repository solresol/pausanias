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
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.6.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_3"
MAIN_ART = ASSET_DIR / "main_memphis_ptolemy_funeral.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.026) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.92)
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
            min_size=11,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.15,
        )
    )
    return panel


def make_campaign_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 226))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "EGYPT HELD, ROUTE DIVERTED",
            TITLE_FONT,
            max_size=18,
            min_size=10,
            padding=6,
            name="campaign-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 72, panel.width - 28, 164)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.52, 0.58))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.6)), grain_strength=0.045)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.45)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "AEGAE": (74, 116),
        "MEMPHIS": (194, 136),
        "EGYPT": (242, 144),
        "PERDICCAS": (276, 102),
    }
    draw.line([points["AEGAE"], points["MEMPHIS"]], fill="#8a5d34", width=3)
    draw.line([points["PERDICCAS"], points["EGYPT"]], fill="#5f4f72", width=3)
    for point, color in [
        (points["AEGAE"], "#6b5a78"),
        (points["MEMPHIS"], "#8c6a2f"),
        (points["EGYPT"], "#3f5f72"),
        (points["PERDICCAS"], "#7b493a"),
    ]:
        draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("AEGAE", (42, 88, 110, 112), "campaign-key:aegae"),
        ("MEMPHIS", (152, 138, 236, 162), "campaign-key:memphis"),
        ("EGYPT", (238, 146, 304, 170), "campaign-key:egypt"),
        ("PERDICCAS", (236, 76, 326, 100), "campaign-key:perdiccas"),
    ]:
        draw.rounded_rectangle(rect, radius=8, fill="#f5e3ba", outline="#b8945a", width=1)
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

    caption = "The funeral road to Aegae becomes a Memphis burial; Perdiccas' march turns back from guarded Egypt."
    records.append(
        draw_fitted_text(
            draw,
            (24, 176, panel.width - 24, panel.height - 12),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=9,
            padding=5,
            name="campaign-key:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not MAIN_ART.exists():
        raise RuntimeError(f"Missing generated art asset: {MAIN_ART}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 738)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.6.3",
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
            min_size=11,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.15,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (608, 56, 1226, 118)
    paste_with_shadow(
        page,
        make_label("PTOLEMY SECURES EGYPT", title_rect, records, font_path=TITLE_FONT, max_size=25, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ALEXANDER'S BODY", (468, 406, 718, 458), (610, 432)),
        ("PTOLEMY", (748, 462, 882, 514), (770, 408)),
        ("MEMPHIS", (620, 156, 774, 208), (684, 246)),
        ("NILE", (838, 542, 934, 594), (918, 432)),
        ("EGYPT GUARDED", (958, 524, 1168, 576), (1078, 438)),
        ("PERDICCAS' ARMY", (1120, 294, 1350, 346), (1192, 322)),
        ("ROAD TO AEGAE DIVERTED", (464, 526, 782, 578), (548, 500)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=18, min_size=8), (rect[0], rect[1]))

    campaign_key = make_campaign_key(records)
    paste_with_shadow(page, campaign_key, (32, 756))

    cleomenes_note = make_compact_callout(
        "Cleomenes, Alexander's satrap in Egypt, is removed as Ptolemy takes direct control.",
        (374, 92),
        "callout:cleomenes",
        records,
    )
    paste_with_shadow(page, cleomenes_note, (32, 1000))
    draw_polyline_leader(draw, [(406, 1044), (448, 1028), (664, 392)])

    funeral_note = make_compact_callout(
        "The body intended for Aegae is claimed for Memphis, turning royal burial into a political anchor for Egypt.",
        (416, 118),
        "callout:funeral",
        records,
    )
    paste_with_shadow(page, funeral_note, (444, 706))
    draw_polyline_leader(draw, [(652, 706), (640, 640), (610, 432)])

    war_note = make_compact_callout(
        "Perdiccas campaigns with Arrhidaeus and young Alexander as royal cover, but his attack on Egypt collapses.",
        (424, 118),
        "callout:perdiccas",
        records,
    )
    paste_with_shadow(page, war_note, (922, 706))
    draw_polyline_leader(draw, [(1134, 706), (1168, 638), (1192, 322)])

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
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Ptolemy at Memphis with Alexander's covered funeral wagon, Nile setting, guarded Egypt, and Perdiccas' distant army.",
            }
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
