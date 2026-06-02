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


PASSAGE_ID = "1.6.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_2"
MAIN_ART = ASSET_DIR / "main_ptolemy_partition_tableau.png"
OXYDRACAE_ART = ASSET_DIR / "oxydracae_rescue.png"
PARTITION_ART = ASSET_DIR / "babylon_partition_council.png"


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
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.90)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.05)
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


def make_route_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 230))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "FROM COMPANION TO KING",
            TITLE_FONT,
            max_size=19,
            min_size=11,
            padding=6,
            name="route-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 72, panel.width - 28, 164)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.52, 0.72))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.8)), grain_strength=0.045)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.42)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "MACEDONIA": (76, 128),
        "BABYLON": (188, 112),
        "EGYPT": (144, 148),
        "OXYDRACAE": (282, 124),
    }
    route = [points["MACEDONIA"], points["BABYLON"], points["OXYDRACAE"]]
    draw.line(route, fill="#8a5d34", width=3)
    draw.line([points["BABYLON"], points["EGYPT"]], fill="#8a5d34", width=3)
    for point, color in [
        (points["MACEDONIA"], "#5f4f72"),
        (points["BABYLON"], "#8c6a2f"),
        (points["EGYPT"], "#3f5f72"),
        (points["OXYDRACAE"], "#76533b"),
    ]:
        draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("MACEDONIA", (44, 94, 134, 118), "route-key:macedonia"),
        ("BABYLON", (152, 82, 224, 106), "route-key:babylon"),
        ("EGYPT", (118, 154, 190, 178), "route-key:egypt"),
        ("OXYDRACAE", (234, 130, 322, 154), "route-key:oxydracae"),
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

    caption = (
        "Pausanias frames Ptolemy through Asian service, succession politics, "
        "and the turn toward Egypt."
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
            name="route-key:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, OXYDRACAE_ART, PARTITION_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.49, 0.52))
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
            "PASSAGE 1.6.2",
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
    title_rect = (626, 56, 1216, 118)
    paste_with_shadow(
        page,
        make_label("PTOLEMY: COMPANION, RESCUER, KINGMAKER", title_rect, records, font_path=TITLE_FONT, max_size=21, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("PTOLEMY", (740, 420, 890, 472), (830, 374)),
        ("ARRHIDAEUS", (524, 192, 718, 244), (610, 334)),
        ("BABYLON", (1002, 186, 1150, 238), (1016, 326)),
        ("MACEDONIA", (476, 492, 660, 544), (616, 482)),
        ("EGYPT", (732, 560, 852, 612), (792, 520)),
        ("OXYDRACAE / INDUS", (1044, 502, 1292, 554), (1030, 454)),
        ("SEPARATE KINGDOMS", (978, 394, 1278, 446), (952, 446)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=18, min_size=8), (rect[0], rect[1]))

    route_key = make_route_key(records)
    paste_with_shadow(page, route_key, (32, 748))

    lineage_note = make_compact_callout(
        "Pausanias preserves the Macedonian claim that Ptolemy was truly Philip's son, though named as Lagus' son.",
        (374, 114),
        "callout:lineage-note",
        records,
    )
    paste_with_shadow(page, lineage_note, (32, 990))
    draw_polyline_leader(draw, [(406, 1046), (440, 1040), (572, 224)])

    rescue_art = crop_to_fill(OXYDRACAE_ART, (416, 238), centering=(0.50, 0.48))
    rescue_art = warm_art(rescue_art, grain_strength=0.022)
    rescue_panel = make_inset_panel(
        rescue_art,
        "Among Alexander's companions, Ptolemy is singled out for protecting him in danger among the Oxydracae.",
        106,
        "caption:rescue",
        records,
    )
    paste_with_shadow(page, rescue_panel, (434, 714))
    paste_with_shadow(page, make_label("OXYDRACAE RESCUE", (494, 734, 788, 782), records, max_size=18, min_size=9), (494, 734))
    draw_leader(draw, (640, 812), (640, 780))

    partition_art = crop_to_fill(PARTITION_ART, (384, 238), centering=(0.50, 0.50))
    partition_art = warm_art(partition_art, grain_strength=0.022)
    partition_panel = make_inset_panel(
        partition_art,
        "After Alexander's death, Ptolemy opposed full power for Arrhidaeus and helped turn satrapies into kingdoms.",
        106,
        "caption:partition",
        records,
    )
    paste_with_shadow(page, partition_panel, (930, 714))
    paste_with_shadow(page, make_label("THE PARTITION", (998, 734, 1264, 782), records, max_size=18, min_size=9), (998, 734))
    draw_leader(draw, (1130, 812), (1130, 780))

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
            {"path": str(MAIN_ART), "description": "Generated raster main panel: Ptolemy and the post-Alexander partition at Babylon with geographic map table."},
            {"path": str(OXYDRACAE_ART), "description": "Generated raster inset: Ptolemy protecting Alexander among the Oxydracae."},
            {"path": str(PARTITION_ART), "description": "Generated raster inset: commanders debating Arrhidaeus and separate kingdoms."},
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
