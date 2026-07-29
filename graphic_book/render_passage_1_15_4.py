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
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.15.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_15_4"
MAIN_ART = ASSET_DIR / "main_trophy_display.png"
SPHACTERIA_ART = ASSET_DIR / "sphacteria.png"
SHIELD_STUDY_ART = ASSET_DIR / "shield_study.png"


def load_translation() -> str:
    """Load the exact English translation from the local SQLite database."""
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def leader_endpoint(
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
) -> tuple[int, int]:
    """Return the closest useful point on a label edge."""
    endpoint = (
        rect[0] if point[0] < rect[0] else rect[2],
        (rect[1] + rect[3]) // 2,
    )
    if rect[0] <= point[0] <= rect[2]:
        endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return endpoint


def add_local_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 10,
    min_size: int = 7,
) -> None:
    """Draw one measured inset label with a semantic leader."""
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    panel.alpha_composite(
        make_label(
            text,
            rect,
            records,
            font_path=TITLE_FONT,
            max_size=max_size,
            min_size=min_size,
        ),
        rect[:2],
    )


def make_sphacteria_panel(records: list[FitRecord]) -> Image.Image:
    """Build the geographic-historical orientation panel."""
    art = warm_art(
        crop_to_fill(SPHACTERIA_ART, (610, 270), centering=(0.50, 0.52)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "At Sphacteria in 425 BCE, the Athenian blockade trapped and captured a Spartan force.",
        78,
        "sphacteria:caption",
        records,
    )
    add_local_label(panel, records, "PYLOS BAY", (30, 186, 146, 224), (220, 164))
    add_local_label(panel, records, "SPHACTERIA", (270, 34, 420, 74), (360, 148))
    add_local_label(
        panel,
        records,
        "ATHENIAN BLOCKADE",
        (420, 214, 620, 252),
        (536, 176),
        max_size=9,
    )
    return panel


def make_shield_study_panel(records: list[FitRecord]) -> Image.Image:
    """Build the material and inscription close-study panel."""
    art = warm_art(
        crop_to_fill(SHIELD_STUDY_ART, (610, 270), centering=(0.50, 0.49)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Bronze carried the dedication; pitch protected the captured shields from time and rust.",
        78,
        "shield-study:caption",
        records,
    )
    add_local_label(
        panel,
        records,
        "INSCRIPTION BAND",
        (20, 18, 176, 56),
        (190, 70),
        max_size=9,
    )
    add_local_label(panel, records, "BRONZE FACE", (24, 212, 154, 250), (236, 146))
    add_local_label(
        panel,
        records,
        "PITCH COATING",
        (456, 18, 606, 56),
        (490, 140),
        max_size=9,
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, SPHACTERIA_ART, SHIELD_STUDY_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 648))
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
            "PASSAGE 1.15.4",
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
            (28, 100, passage_panel.width - 28, 316),
            translation,
            BODY_FONT,
            max_size=20,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.12,
        )
    )

    for rect, text, name in [
        (
            (24, 348, 346, 452),
            "The shields were public trophies: their inscriptions recorded defeated enemies and allies.",
            "passage:inscriptions-note",
        ),
        (
            (24, 474, 346, 588),
            "The dark coating turns preservation into evidence—the Sphacteria shields remained visible in Athens.",
            "passage:pitch-note",
        ),
    ]:
        passage_draw.rounded_rectangle(
            rect,
            radius=12,
            fill="#f0ddb5",
            outline="#a57a44",
            width=2,
        )
        records.append(
            draw_fitted_text(
                passage_draw,
                rect,
                text,
                BODY_FONT,
                max_size=15,
                min_size=10,
                padding=12,
                name=name,
                align="center",
                spacing_ratio=0.12,
            )
        )
    records.append(
        draw_fitted_text(
            passage_draw,
            (48, 606, 322, 638),
            "ATHENS · PAINTED STOA",
            TITLE_FONT,
            max_size=11,
            min_size=8,
            padding=4,
            name="passage:location",
            align="center",
            spacing_ratio=0.05,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 620), centering=(0.49, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((968, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (620, 42, 1168, 100)
    paste_with_shadow(
        page,
        make_label(
            "TROPHIES AT THE PAINTED STOA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=18,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("BRONZE SHIELDS", (430, 130, 608, 172), (576, 266)),
        ("SICYONIANS & ALLIES", (432, 542, 664, 586), (646, 430)),
        ("PITCH-COATED SHIELDS", (868, 126, 1120, 170), (1000, 304)),
        ("SPHACTERIA PRISONERS", (1100, 544, 1350, 590), (1058, 446)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
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

    orientation_rect = (830, 614, 1348, 654)
    paste_with_shadow(
        page,
        make_label(
            "ATHENS · FIFTH-CENTURY TROPHY DISPLAY",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_sphacteria_panel(records), (28, 692))
    paste_with_shadow(page, make_shield_study_panel(records), (706, 692))

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
            record.font_size
            for record in records
            if record.name == "passage:translation"
        ),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/15/3.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019faf09-d299-7a62-b053-e85291d35183/call_YaTCf9283tVWtz5ikCFIPbgo.png",
                "description": "Generated Painted Stoa trophy display with bronze and pitch-coated shield groups.",
            },
            {
                "path": str(SPHACTERIA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019faf09-d299-7a62-b053-e85291d35183/call_uGKNAiNxyK23U9qQ7CxT6Mic.png",
                "description": "Generated oblique Pylos Bay and Sphacteria blockade landscape.",
            },
            {
                "path": str(SHIELD_STUDY_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019faf09-d299-7a62-b053-e85291d35183/call_FdSoe4e4nS6Nq4p4cNqpz0aZ.png",
                "description": "Generated archaeological study of bronze, inscription band, fittings, and pitch.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_15_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/15/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
