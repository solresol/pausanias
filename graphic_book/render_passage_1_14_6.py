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
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    draw_fitted_text,
    draw_leader,
    framed_panel,
    make_inset_panel,
    make_label,
    make_note_panel,
    make_parchment,
    paste_with_shadow,
    root_dir,
)
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.14.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_14_6"
MAIN_ART = ASSET_DIR / "main_hephaestus_temple.png"
LAKE_ART = ASSET_DIR / "lake_tritonis.png"
RELIEF_ART = ASSET_DIR / "agora_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_lake_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(LAKE_ART, (464, 274), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "At Lake Tritonis, a Libyan tradition made Athena the daughter of Poseidon and the lake.",
        84,
        "lake:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("ATHENA", (28, 26, 150, 66), (86, 142)),
        ("POSEIDON", (158, 26, 292, 66), (156, 146)),
        ("LAKE TRITONIS", (300, 242, 482, 282), (346, 212)),
    ]
    for text, rect, point in labels:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[3])
        draw_leader(draw, point, endpoint)
        panel.alpha_composite(
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=11,
                min_size=8,
            ),
            rect[:2],
        )
    return panel


def make_orientation_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((822, 410))
    draw = ImageDraw.Draw(panel)
    art = warm_art(
        crop_to_fill(RELIEF_ART, (786, 294), centering=(0.50, 0.54)),
        grain_strength=0.006,
    )
    panel.paste(art, (18, 18))
    draw.rectangle((18, 18, 804, 312), outline=RULE, width=2)

    labels = [
        ("TEMPLE OF HEPHAESTUS", (30, 26, 252, 66), (202, 108)),
        ("BASILEIOS STOA", (38, 246, 202, 284), (310, 178)),
        ("CERAMEICUS", (224, 258, 368, 296), (176, 266)),
        ("AGORA", (494, 250, 594, 288), (490, 190)),
        ("ACROPOLIS", (644, 32, 790, 72), (680, 92)),
    ]
    for text, rect, point in labels:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        panel.alpha_composite(
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=10,
                min_size=7,
            ),
            rect[:2],
        )

    records.append(
        draw_fitted_text(
            draw,
            (34, 326, panel.width - 34, panel.height - 18),
            "The temple stood above the Cerameicus and the Basileios Stoa on the Agora's western rise.",
            BODY_FONT,
            max_size=17,
            min_size=11,
            padding=7,
            name="orientation:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, LAKE_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 520))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(
        title_rect,
        radius=12,
        fill="#ead2a0",
        outline=RULE,
        width=2,
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.14.6",
            TITLE_FONT,
            max_size=28,
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
            (26, 96, passage_panel.width - 26, passage_panel.height - 28),
            translation,
            BODY_FONT,
            max_size=20,
            min_size=12,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    note = make_note_panel(
        "Pausanias reads an Athenian statue through a Libyan geography: the colour of Athena's eyes becomes evidence of origin.",
        (378, 112),
        "interpretive:note",
        records,
    )
    paste_with_shadow(page, note, (28, 554))

    art = warm_art(
        crop_to_fill(MAIN_ART, (944, 620), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((972, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 958, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (416, 22))

    heading_rect = (660, 42, 1138, 96)
    paste_with_shadow(
        page,
        make_label(
            "HEPHAESTUS AND ATHENA ABOVE THE AGORA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=17,
            min_size=10,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACROPOLIS", (438, 104, 614, 150), (548, 258)),
        ("TEMPLE OF HEPHAESTUS", (1118, 112, 1364, 160), (1194, 194)),
        ("HEPHAESTUS", (956, 250, 1112, 294), (1070, 330)),
        ("ATHENA", (1198, 250, 1328, 294), (1160, 330)),
        ("BASILEIOS STOA", (438, 430, 638, 476), (650, 454)),
        ("CERAMEICUS", (454, 584, 632, 630), (664, 560)),
    ]
    for text, rect, point in callouts:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=12,
                min_size=8,
            ),
            rect[:2],
        )

    paste_with_shadow(page, make_lake_panel(records), (28, 692))
    paste_with_shadow(page, make_orientation_panel(records), (558, 692))

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
        "continuity_reference_pages": ["graphic_book/images/1/14/5.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9549-5cb1-7692-915e-5b2995119c2f/call_XizMWpN7wld5zfNNrViU7ffI.png",
                "description": "Generated reconstruction of the Hephaestus temple, paired cult statues, Agora, and Acropolis.",
            },
            {
                "path": str(LAKE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9549-5cb1-7692-915e-5b2995119c2f/call_wFChA2MrwFOG8Om6gi2JSTTF.png",
                "description": "Generated Lake Tritonis sanctuary landscape with Athena and Poseidon cult statues.",
            },
            {
                "path": str(RELIEF_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9549-5cb1-7692-915e-5b2995119c2f/call_UA6nskb3OLYzysHBxUS95Qle.png",
                "description": "Generated oblique Agora and Acropolis relief used as the orientation base.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_14_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/14/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
