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
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    make_compact_callout,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.13.8"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_8"
MAIN_ART = ASSET_DIR / "main_pyrrhus_argos.png"
SANCTUARY_ART = ASSET_DIR / "demeter_sanctuary.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_sanctuary_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(SANCTUARY_ART, (388, 204), centering=(0.52, 0.55)),
        grain_strength=0.012,
    )
    panel = make_inset_panel(
        art,
        "At the place where Pyrrhus died, the Argives maintained a sanctuary of Demeter.",
        98,
        "inset:sanctuary-caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("DEMETER PRECINCT", (20, 24, 164, 52), (114, 102)),
        ("ROOF TILE", (270, 158, 374, 186), (310, 198)),
    ]
    for index, (text, rect, point) in enumerate(labels):
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        label = make_label(
            text,
            rect,
            records,
            font_path=BODY_FONT,
            max_size=8,
            min_size=6,
        )
        panel.alpha_composite(label, rect[:2])
    return panel


def make_street_inset(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(
            MAIN_ART,
            (420, 202),
            source_box=(0, 170, 1130, 980),
            centering=(0.50, 0.55),
        ),
        grain_strength=0.014,
    )
    panel = make_inset_panel(
        art,
        "Roof, street, and sanctuary converge in the Argive account of Pyrrhus's death.",
        96,
        "inset:street-caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("ROOFTOP", (20, 26, 116, 54), (104, 72)),
        ("FALLING TILE", (144, 36, 270, 64), (283, 73)),
        ("PYRRHUS", (236, 150, 332, 178), (303, 129)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        label = make_label(
            text,
            rect,
            records,
            font_path=BODY_FONT,
            max_size=8,
            min_size=6,
        )
        panel.alpha_composite(label, rect[:2])
    return panel


def make_accounts_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title = (24, 16, panel.width - 24, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "THREE LAYERS OF MEMORY",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="accounts:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    entries = [
        ("1", "EVENT", "A roof tile struck Pyrrhus during confused street fighting."),
        ("2", "ARGIVE CLAIM", "Demeter herself acted in the form of a woman."),
        ("3", "LOCAL RECORD", "Lyceas preserved the account in verse."),
        ("4", "PLACE", "A sanctuary of Demeter marked the death site."),
    ]
    for index, (number, heading, note) in enumerate(entries):
        y0 = 72 + index * 59
        y1 = y0 + 49
        draw.ellipse((24, y0 + 5, 62, y0 + 43), fill="#d2ad70", outline="#795331", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (24, y0 + 5, 62, y0 + 43),
                number,
                TITLE_FONT,
                max_size=15,
                min_size=9,
                padding=8,
                name=f"accounts:number:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        draw.rounded_rectangle((72, y0, 428, y1), radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (80, y0 + 3, 178, y1 - 3),
                heading,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=3,
                name=f"accounts:heading:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (184, y0 + 3, 420, y1 - 3),
                note,
                BODY_FONT,
                max_size=9,
                min_size=7,
                padding=3,
                name=f"accounts:note:{index}",
                align="center",
                spacing_ratio=0.05,
            )
        )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, SANCTUARY_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    main_rect = (430, 36, 1374, 628)
    art = warm_art(
        crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.53)),
        grain_strength=0.012,
    )
    main_panel = framed_panel((art.width + 28, art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + art.width, 14 + art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left = framed_panel((378, 706))
    left_draw = ImageDraw.Draw(left)
    title_band = (18, 14, left.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.13.8",
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
            (24, 92, left.width - 24, left.height - 24),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left, (32, 36))

    title_rect = (612, 54, 1128, 116)
    paste_with_shadow(
        page,
        make_label("THE DEATH OF PYRRHUS AT ARGOS", title_rect, records, font_path=TITLE_FONT, max_size=19, min_size=10),
        title_rect[:2],
    )
    labels = [
        ("LARISA HILL", (1040, 132, 1190, 176), (1008, 46)),
        ("ARGIVE ROOFTOP", (454, 178, 626, 222), (544, 274)),
        ("FALLING TILE", (636, 252, 790, 296), (876, 266)),
        ("PYRRHUS", (762, 476, 888, 520), (918, 348)),
        ("DEMETER PRECINCT", (1110, 400, 1312, 444), (1190, 342)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=11, min_size=7),
            rect[:2],
        )

    note1 = make_compact_callout(
        "The fighting contracted into houses, sanctuaries, and narrow streets until Pyrrhus stood isolated.",
        (440, 86),
        "callout:isolation",
        records,
        max_size=13,
    )
    draw_polyline_leader(draw, [(448, 652), (698, 566), (914, 406)])
    paste_with_shadow(page, note1, (448, 642))
    note2 = make_compact_callout(
        "A woman cast the tile; Argive tradition identified the agent as Demeter in human form.",
        (448, 86),
        "callout:demeter",
        records,
        max_size=13,
    )
    draw_polyline_leader(draw, [(904, 652), (938, 474), (876, 266)])
    paste_with_shadow(page, note2, (904, 642))

    paste_with_shadow(page, make_sanctuary_panel(records), (32, 780))
    paste_with_shadow(page, make_street_inset(records), (440, 780))
    paste_with_shadow(page, make_accounts_panel(records), (904, 780))
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
        "continuity_reference_pages": ["graphic_book/images/1/13/7.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f713d-83f2-79f0-8665-6cd2049d4034/exec-6e1a61ee-57fa-4cdd-b957-66ac7f4ccc95.png",
                "description": "Generated raster reconstruction of Pyrrhus's death in the streets of Argos.",
            },
            {
                "path": str(SANCTUARY_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f713d-83f2-79f0-8665-6cd2049d4034/exec-a7ed698e-0ddd-48de-9966-e1ab47cf6d9d.png",
                "description": "Generated archaeological reconstruction of the Demeter sanctuary marking the death site.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_13_8_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/13/8.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
