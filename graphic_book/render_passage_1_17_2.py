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


PASSAGE_ID = "1.17.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_17_2"
MAIN_ART = ASSET_DIR / "main_approach.png"
AMAZON_ART = ASSET_DIR / "amazons.png"
CENTAURO_ART = ASSET_DIR / "centaurs.png"
MEMORY_ART = ASSET_DIR / "gymnasium_memory.png"


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
    """Return a label-edge endpoint that keeps the leader out of the text."""
    endpoint = (
        rect[0] if point[0] < rect[0] else rect[2],
        (rect[1] + rect[3]) // 2,
    )
    if rect[0] <= point[0] <= rect[2]:
        endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return endpoint


def add_panel_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    """Draw a fitted label and semantic leader within an inset."""
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    label = make_label(
        text,
        rect,
        records,
        font_path=TITLE_FONT,
        max_size=max_size,
        min_size=min_size,
    )
    panel.alpha_composite(label, rect[:2])


def make_amazon_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Amazonomachy painting study."""
    art = warm_art(
        crop_to_fill(AMAZON_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "The sanctuary painting set Athenians against the Amazons.",
        58,
        "amazons:caption",
        records,
    )
    add_panel_label(panel, records, "ATHENIANS", (12, 202, 130, 240), (118, 158))
    add_panel_label(panel, records, "AMAZONS", (268, 30, 378, 68), (286, 132))
    return panel


def make_centaur_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Centauromachy painting study."""
    art = warm_art(
        crop_to_fill(CENTAURO_ART, (390, 280), centering=(0.48, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Theseus has slain one Centaur; the wider struggle remains balanced.",
        58,
        "centaurs:caption",
        records,
    )
    add_panel_label(panel, records, "THESEUS", (12, 30, 116, 68), (116, 124))
    add_panel_label(
        panel,
        records,
        "FALLEN CENTAUR",
        (238, 202, 378, 240),
        (188, 222),
    )
    return panel


def make_memory_panel(records: list[FitRecord]) -> Image.Image:
    """Build the gymnasium sculpture and burial study."""
    art = warm_art(
        crop_to_fill(MEMORY_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Stone Herms and bronze Ptolemy stood near the graves of Juba and Chrysippus.",
        58,
        "memory:caption",
        records,
    )
    add_panel_label(panel, records, "STONE HERMS", (10, 30, 128, 68), (96, 154))
    add_panel_label(
        panel,
        records,
        "BRONZE PTOLEMY",
        (150, 202, 292, 240),
        (220, 140),
    )
    add_panel_label(
        panel,
        records,
        "JUBA · CHRYSIPPUS",
        (298, 30, 428, 68),
        (354, 160),
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, AMAZON_ART, CENTAURO_ART, MEMORY_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 650))
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
            "PASSAGE 1.17.2",
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
            (28, 92, passage_panel.width - 28, 462),
            translation,
            BODY_FONT,
            max_size=17,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 478, 346, 602)
    passage_draw.rounded_rectangle(
        note_rect,
        radius=12,
        fill="#f0ddb5",
        outline="#a57a44",
        width=2,
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "The precise archaeological positions of the gymnasium and sanctuary are not asserted here; the reconstruction provides civic and topographic orientation.",
            BODY_FONT,
            max_size=12,
            min_size=9,
            padding=10,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.09,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (40, 612, 330, 640),
            "ATHENS · SECOND CENTURY CE",
            TITLE_FONT,
            max_size=10,
            min_size=7,
            padding=3,
            name="passage:orientation",
            align="center",
            spacing_ratio=0.04,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (626, 40, 1192, 98)
    paste_with_shadow(
        page,
        make_label(
            "PTOLEMY'S GYMNASIUM AND THE THESEUS SANCTUARY",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=16,
            min_size=9,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("PTOLEMY'S GYMNASIUM", (448, 210, 674, 254), (720, 334)),
        ("BRONZE PTOLEMY", (448, 458, 642, 502), (678, 426)),
        ("THE ACROPOLIS", (1110, 118, 1328, 162), (1022, 190)),
        ("THESEUS SANCTUARY", (1102, 360, 1328, 404), (1116, 426)),
        ("PAINTED BATTLES", (1084, 500, 1300, 544), (1144, 454)),
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

    orientation_rect = (700, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "CIVIC MEMORY, HEROIC PAINTING, AND THE APPROACH TO THE ACROPOLIS",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_amazon_panel(records), (28, 700))
    paste_with_shadow(page, make_centaur_panel(records), (462, 700))
    paste_with_shadow(page, make_memory_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/17/1.png"],
        "evidence_boundary": "Exact archaeological placement is not claimed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc8c9-9e85-7a01-931f-b5655fbf85ae/exec-b075ec20-d874-4c18-b4d5-699d8d879067.png",
                "description": "Generated reconstruction of Ptolemy's Gymnasium and the Theseus sanctuary with the Acropolis beyond.",
            },
            {
                "path": str(AMAZON_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc8c9-9e85-7a01-931f-b5655fbf85ae/exec-47ce9f12-53a4-468a-86a1-78afe98cc7f4.png",
                "description": "Generated reconstruction of the Amazon battle painting.",
            },
            {
                "path": str(CENTAURO_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc8c9-9e85-7a01-931f-b5655fbf85ae/exec-fde047d4-3f8a-4830-8b75-d88854de5a47.png",
                "description": "Generated content-suitable reconstruction of Theseus in the Centaur-Lapith battle painting.",
            },
            {
                "path": str(MEMORY_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc8c9-9e85-7a01-931f-b5655fbf85ae/exec-7ba56525-040c-454b-928d-823a8fe4be6e.png",
                "description": "Generated gymnasium sculpture and burial study.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_17_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/17/2.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
