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
from graphic_book.render_passage_1_10_1 import crop_to_fill, make_compact_callout, validate_fit_records, warm_art


PASSAGE_ID = "1.11.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_11_4"
MAIN_ART = ASSET_DIR / "main_oeniadae_aeacides_wounded.png"
COUNCIL_ART = ASSET_DIR / "epirote_council_forgiveness.png"


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


def make_western_greece_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "EPIRUS TO OENIADAE",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 226)
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(map_size, 34).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#6f603e", white="#efd8a1")
    sea_noise = Image.effect_noise(map_size, 18).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#3f6772", white="#aebcaf")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(84, 0), (328, 0), (328, 152), (168, 152), (138, 118), (150, 86), (116, 48)], fill=228)
    mdraw.polygon([(0, 0), (114, 0), (106, 50), (126, 86), (96, 124), (72, 152), (0, 152)], fill=216)
    mdraw.polygon([(112, 82), (162, 100), (202, 136), (170, 152), (106, 142), (88, 118)], fill=235)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 126, map_rect[1] + 42),
        "MACEDON": (map_rect[0] + 232, map_rect[1] + 46),
        "OENIADAE": (map_rect[0] + 166, map_rect[1] + 122),
    }
    draw.line([points["EPIRUS"], points["OENIADAE"]], fill="#7b493a", width=4)
    draw.line([points["EPIRUS"], points["OENIADAE"]], fill="#f3dfb4", width=1)
    draw.line([points["MACEDON"], points["OENIADAE"]], fill="#6f5130", width=3)
    draw.line((map_rect[0] + 108, map_rect[1] + 88, map_rect[0] + 214, map_rect[1] + 138), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("EPIRUS", (70, 106, 142, 130), "locator:epirus"),
        ("MACEDON", (216, 108, 306, 132), "locator:macedon"),
        ("OENIADAE", (138, 176, 230, 200), "locator:oeniadae"),
        ("IONIAN SEA", (42, 184, 144, 208), "locator:ionian"),
        ("ACHELOUS", (206, 162, 306, 186), "locator:achelous"),
    ]
    for text, rect, name in labels:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=8,
                min_size=5,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.04,
            )
        )

    caption = "Cassander's opposition pulls Aeacides from Epirus toward a fatal fight near Oeniadae."
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


def make_sequence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "FALL OF AEACIDES",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="sequence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("OLYMPIAS", "Her impious acts make hatred turn against Aeacides."),
        ("EPIROTES", "They first refuse him, then grant forgiveness."),
        ("CASSANDER", "He still blocks the return to Epirus."),
        ("OENIADAE", "Aeacides is wounded and soon meets his fate."),
    ]
    y = 78
    for idx, (name, note) in enumerate(rows):
        row_rect = (24, y, panel.width - 24, y + 52)
        draw.rounded_rectangle(
            row_rect,
            radius=9,
            fill="#f3dfb4" if idx % 2 == 0 else "#f7e8c8",
            outline="#b8945a",
            width=1,
        )
        name_rect = (34, y + 7, 154, y + 45)
        note_rect = (166, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"sequence:name:{idx}",
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
                max_size=12,
                min_size=7,
                padding=2,
                name=f"sequence:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, COUNCIL_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 634)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.49),
    )
    main_art = warm_art(ImageEnhance.Contrast(main_art).enhance(1.02), grain_strength=0.014)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 716)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.11.4",
            TITLE_FONT,
            max_size=29,
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
            min_size=9,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (698, 54, 1324, 116)
    paste_with_shadow(
        page,
        make_label("AEACIDES AT OENIADAE", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("OENIADAE", (1000, 132, 1198, 180), (1018, 240), 20),
        ("ACHELOUS WETLANDS", (1114, 432, 1370, 480), (1038, 392), 15),
        ("AEACIDES WOUNDED", (548, 476, 856, 524), (662, 512), 15),
        ("PHILIP'S FORCES", (1006, 538, 1266, 586), (1054, 502), 16),
        ("EPIROTE GUARD", (478, 162, 724, 210), (538, 462), 16),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    cassander_note = make_compact_callout(
        "Cassander will not allow Aeacides' return to settle quietly.",
        (408, 88),
        "callout:cassander",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(458, 654), (554, 584), (662, 512)])
    paste_with_shadow(page, cassander_note, (458, 642))

    wound_note = make_compact_callout(
        "Near Oeniadae, Philip defeats Aeacides; the wound is followed by his death.",
        (466, 88),
        "callout:wound",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 654), (792, 574), (662, 512)])
    paste_with_shadow(page, wound_note, (898, 642))

    locator_panel = make_western_greece_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    council_crop = crop_to_fill(COUNCIL_ART, (420, 198), centering=(0.50, 0.50))
    council_crop = warm_art(council_crop, grain_strength=0.018)
    council_panel = make_inset_panel(
        council_crop,
        "The Epirotes first reject Aeacides because Olympias' crimes have made his cause hateful.",
        94,
        "inset:council-caption",
        records,
    )
    paste_with_shadow(page, council_panel, (440, 756))
    inset_label = (516, 774, 806, 810)
    draw_leader(draw, (716, 864), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("EPIROTE FORGIVENESS", inset_label, records, max_size=13, min_size=6), (inset_label[0], inset_label[1]))

    sequence_panel = make_sequence_panel(records)
    paste_with_shadow(page, sequence_panel, (904, 758))

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
            "graphic_book/images/1/11/3.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f1ed6-fecb-76d3-87eb-5a7f6c46c39c/ig_038381ea71b3b966016a45561b205c81919a8980c7ea090a1f.png",
                "description": "Generated raster main panel showing Aeacides wounded in the battle near Oeniadae amid Achelous wetlands.",
            },
            {
                "path": str(COUNCIL_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f1ed6-fecb-76d3-87eb-5a7f6c46c39c/ig_038381ea71b3b966016a45566370908191a0dceebc48f8de76.png",
                "description": "Generated raster scenic inset showing an Epirote council weighing Aeacides' return and forgiveness.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_11_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "11" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
