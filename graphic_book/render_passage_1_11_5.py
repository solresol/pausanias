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

from PIL import Image, ImageDraw, ImageFilter, ImageOps

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


PASSAGE_ID = "1.11.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_11_5"
MAIN_ART = ASSET_DIR / "main_pyrrhus_egyptian_fleet.png"
UPRISING_ART = ASSET_DIR / "alcetas_night_uprising.png"


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


def make_return_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "FLIGHT AND RETURN",
            TITLE_FONT,
            max_size=17,
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
    land = ImageOps.colorize(relief, black="#70613f", white="#efd8a1")
    sea_noise = Image.effect_noise(map_size, 16).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#3f6976", white="#adc1bb")
    mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(72, 0), (206, 0), (190, 50), (160, 72), (154, 106), (126, 152), (54, 152), (46, 86)], fill=224)
    mdraw.polygon([(176, 0), (328, 0), (328, 86), (252, 90), (208, 60)], fill=230)
    mdraw.polygon([(210, 92), (328, 78), (328, 152), (238, 152), (206, 126)], fill=226)
    mdraw.polygon([(0, 132), (90, 120), (148, 152), (0, 152)], fill=218)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 108, map_rect[1] + 54),
        "MACEDON": (map_rect[0] + 220, map_rect[1] + 48),
        "EGYPT": (map_rect[0] + 250, map_rect[1] + 132),
        "IONIAN": (map_rect[0] + 126, map_rect[1] + 118),
    }
    draw.line([points["MACEDON"], points["EPIRUS"]], fill="#704235", width=4)
    draw.line([points["EPIRUS"], points["IONIAN"], points["EGYPT"]], fill="#f3dfb4", width=5)
    draw.line([points["EPIRUS"], points["IONIAN"], points["EGYPT"]], fill="#6b4c2d", width=2)
    draw.line((map_rect[0] + 86, map_rect[1] + 114, map_rect[0] + 230, map_rect[1] + 140), fill="#416b75", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("EPIRUS", (64, 100, 134, 124), "locator:epirus"),
        ("MACEDON", (210, 100, 298, 124), "locator:macedon"),
        ("EGYPT", (230, 180, 298, 204), "locator:egypt"),
        ("IONIAN SEA", (82, 176, 184, 200), "locator:ionian"),
        ("FLEET RETURN", (132, 138, 252, 162), "locator:return"),
    ]
    for text, rect, name in label_specs:
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

    caption = "Cassander's pressure drives Pyrrhus to Egypt; Ptolemy's fleet returns him to Epirus."
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
            "PYRRHUS RETURNS",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="sequence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("ALCETAS", "The Epeirots accept him, then rise against his violence."),
        ("PYRRHUS", "Aeacides' young son is recalled after Alcetas' death."),
        ("CASSANDER", "Macedonian pressure forces Pyrrhus into exile."),
        ("PTOLEMY", "Marriage alliance and an Egyptian fleet restore him."),
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
    for asset in [MAIN_ART, UPRISING_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 634)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.53, 0.49),
    )
    main_art = warm_art(main_art, grain_strength=0.014)
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
            "PASSAGE 1.11.5",
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
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (658, 54, 1266, 116)
    paste_with_shadow(
        page,
        make_label("PYRRHUS RESTORED BY FLEET", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("YOUNG PYRRHUS", (520, 500, 756, 548), (602, 454), 16),
        ("PTOLEMAIC FLEET", (778, 536, 1068, 584), (938, 470), 17),
        ("EPIROTE COAST", (1036, 132, 1286, 180), (1088, 262), 17),
        ("IONIAN CROSSING", (934, 432, 1212, 480), (924, 392), 15),
        ("EGYPTIAN SUPPORT", (478, 158, 766, 206), (560, 352), 15),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    cassander_note = make_compact_callout(
        "Cassander's advance prevents the young king from securing Epirus.",
        (408, 88),
        "callout:cassander",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(456, 654), (542, 584), (602, 454)])
    paste_with_shadow(page, cassander_note, (456, 642))

    ptolemy_note = make_compact_callout(
        "Ptolemy son of Lagus seals the alliance by marriage and sends the fleet that restores Pyrrhus.",
        (466, 90),
        "callout:ptolemy",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 654), (990, 592), (938, 470)])
    paste_with_shadow(page, ptolemy_note, (898, 642))

    locator_panel = make_return_locator(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    uprising_crop = crop_to_fill(UPRISING_ART, (420, 198), centering=(0.50, 0.50))
    uprising_crop = warm_art(uprising_crop, grain_strength=0.018)
    uprising_panel = make_inset_panel(
        uprising_crop,
        "The Epeirots first accept Alcetas, then rise at night against his violent rule.",
        94,
        "inset:uprising-caption",
        records,
    )
    paste_with_shadow(page, uprising_panel, (440, 756))
    inset_label = (522, 774, 798, 810)
    draw_leader(draw, (710, 864), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(page, make_label("ALCETAS OVERTHROWN", inset_label, records, max_size=13, min_size=6), (inset_label[0], inset_label[1]))

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
            "graphic_book/images/1/11/4.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f23fd-67b5-7bc1-b0aa-eba35c4c7c66/ig_0b5a4e97a34a14d8016a46a79f83b48191beeb5bf206a04739.png",
                "description": "Generated raster main panel showing Ptolemaic ships carrying young Pyrrhus toward the Epirote coast.",
            },
            {
                "path": str(UPRISING_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f23fd-67b5-7bc1-b0aa-eba35c4c7c66/ig_0b5a4e97a34a14d8016a46a83e819c81919b7aa9cc231a2811.png",
                "description": "Generated raster scenic inset showing the Epirote night uprising against Alcetas without gore.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_11_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "11" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
