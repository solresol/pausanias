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

from PIL import Image, ImageDraw

from graphic_book.render_passage_1_3_2 import (
    BODY_FONT,
    FitRecord,
    HEIGHT,
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    draw_fitted_text,
    draw_leader,
    framed_panel,
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)
from graphic_book.render_passage_1_10_1 import crop_to_fill, validate_fit_records, warm_art


PASSAGE_ID = "1.21.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_21_6"
MAIN_ART = ASSET_DIR / "main_hoof_workshop.png"
PINE_ART = ASSET_DIR / "pine_cone_analogy.png"
CAMP_ART = ASSET_DIR / "horse_camp.png"
RELIEF_ART = ASSET_DIR / "athens_steppe_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return row[0]


def leader_endpoint(rect: tuple[int, int, int, int], point: tuple[int, int]) -> tuple[int, int]:
    if rect[0] <= point[0] <= rect[2]:
        return (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)


def add_page_label(
    page: Image.Image,
    draw: ImageDraw.ImageDraw,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    draw_leader(draw, point, leader_endpoint(rect, point))
    paste_with_shadow(
        page,
        make_label(text, rect, records, font_path=TITLE_FONT, max_size=max_size, min_size=min_size),
        rect[:2],
    )


def add_panel_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 8,
    min_size: int = 6,
) -> None:
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    panel.alpha_composite(
        make_label(text, rect, records, font_path=TITLE_FONT, max_size=max_size, min_size=min_size),
        rect[:2],
    )


def make_orientation_strip(records: list[FitRecord]) -> Image.Image:
    relief = warm_art(
        crop_to_fill(RELIEF_ART, (326, 108), centering=(0.50, 0.52)),
        grain_strength=0.003,
    ).convert("RGBA")
    strip = framed_panel((338, 120))
    strip.paste(relief, (6, 6))
    draw = ImageDraw.Draw(strip)
    athens = (58, 82)
    black_sea = (192, 62)
    steppe = (246, 25)
    draw.line((athens, black_sea, steppe), fill="#f0dba7", width=4)
    draw.line((athens, black_sea, steppe), fill="#76502c", width=2)
    for point in (athens, black_sea, steppe):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#76502c",
            outline="#f4deb0",
            width=2,
        )
    labels = [
        ("ATHENS", (8, 78, 92, 110)),
        ("BLACK SEA", (128, 60, 230, 92)),
        ("SARMATIAN STEPPE", (208, 6, 332, 38)),
    ]
    for text, rect in labels:
        strip.alpha_composite(
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=7, min_size=6),
            rect[:2],
        )
    return strip


def make_pine_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(PINE_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Pausanias compares the overlapping hoof scales to the scales of a green pine cone.",
        58,
        "pine:caption",
        records,
    )
    add_panel_label(panel, records, "GREEN PINE CONE", (18, 18, 172, 60), (142, 128), max_size=7)
    add_panel_label(panel, records, "PIERCED HOOF SCALES", (220, 194, 404, 238), (314, 164), max_size=7)
    add_panel_label(panel, records, "OVERLAPPING SAMPLE", (438, 18, 616, 60), (520, 120), max_size=7)
    return panel


def make_camp_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(CAMP_ART, (634, 280), centering=(0.50, 0.54)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Many horses sustained Sarmatian movement, warfare, ritual, food, and material craft.",
        58,
        "camp:caption",
        records,
    )
    add_panel_label(panel, records, "MOBILE CAMP", (420, 18, 552, 60), (462, 118), max_size=7)
    add_panel_label(panel, records, "HORSE HERD", (210, 194, 340, 236), (310, 148), max_size=7)
    add_panel_label(panel, records, "STEPPE PASTURE", (18, 18, 174, 60), (160, 176), max_size=7)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, PINE_ART, CAMP_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.21.6",
            TITLE_FONT,
            max_size=27,
            min_size=18,
            padding=10,
            name="passage:title",
            align="center",
            spacing_ratio=0.07,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (28, 88, passage_panel.width - 28, 464),
            translation,
            BODY_FONT,
            max_size=17,
            min_size=11,
            padding=5,
            name="passage:translation",
            spacing_ratio=0.055,
        )
    )
    note_rect = (24, 474, 354, 524)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias supplies the material and method; workshop, tools, makers, clothing, and exact cuirass form are reconstructed.",
            BODY_FONT,
            max_size=10,
            min_size=7,
            padding=7,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.05,
        )
    )
    passage_panel.alpha_composite(make_orientation_strip(records), (20, 528))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (690, 40, 1142, 98)
    paste_with_shadow(
        page,
        make_label(
            "MAKING HOOF-SCALE ARMOUR",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=14,
            min_size=9,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("PIERCING THE SCALE", (438, 116, 622, 162), (798, 306), 7),
        ("SINEW THREAD", (438, 322, 588, 368), (823, 392), 8),
        ("PREPARED HOOF SCALES", (438, 522, 644, 568), (712, 548), 7),
        ("CLEANED, SPLIT HOOFS", (1110, 486, 1348, 534), (1198, 506), 7),
        ("FINISHED CUIRASS", (1114, 174, 1328, 220), (974, 322), 8),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    summary_rect = (720, 610, 1166, 658)
    paste_with_shadow(
        page,
        make_label(
            "BEAUTIFUL, STRONG, AND NON-IRON",
            summary_rect,
            records,
            font_path=BODY_FONT,
            max_size=10,
            min_size=7,
        ),
        summary_rect[:2],
    )

    paste_with_shadow(page, make_pine_panel(records), (28, 700))
    paste_with_shadow(page, make_camp_panel(records), (718, 700))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "translation_font_size": next(
            record.font_size for record in records if record.name == "passage:translation"
        ),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/21/5.png"],
        "evidence_boundary": "Pausanias supplies the nomadic setting, many horses, their military, ritual, and food uses, hoof preparation, pine-cone comparison, piercing, sinew sewing, and assessment of beauty and strength. Workshop architecture, tools, clothing, makers, herd arrangement, and exact cuirass form are reconstructed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated reconstruction of hoof-scale armour manufacture in a Sarmatian steppe workshop.",
            },
            {
                "path": str(PINE_ART),
                "description": "Generated pine-cone and hoof-scale comparison still life.",
            },
            {
                "path": str(CAMP_ART),
                "description": "Generated Sarmatian horse-herd and mobile-camp context scene.",
            },
            {
                "path": str(RELIEF_ART),
                "description": "Generated relief base for subordinate Athens-to-north-Pontic orientation.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_21_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/21/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
