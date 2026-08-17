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


PASSAGE_ID = "1.19.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_19_1"
MAIN_ART = ASSET_DIR / "main_delphinion.png"
LOCATOR_ART = ASSET_DIR / "locator.png"
APOLLO_ART = ASSET_DIR / "apollo_pythios.png"
ARRIVAL_ART = ASSET_DIR / "arrival.png"


def load_translation() -> str:
    """Load the exact English translation from the requested local database."""
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return row[0]


def leader_endpoint(
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
) -> tuple[int, int]:
    """Return the nearest suitable label edge for a semantic leader."""
    if rect[0] <= point[0] <= rect[2]:
        return (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return (
        rect[0] if point[0] < rect[0] else rect[2],
        (rect[1] + rect[3]) // 2,
    )


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
    """Draw a measured inset label and a leader ending on a named feature."""
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


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    """Build the textured Roman-period southeast-Athens orientation inset."""
    art = warm_art(
        crop_to_fill(LOCATOR_ART, (390, 280), centering=(0.50, 0.31)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Pausanias moves beyond the Olympieion among southeast Athens' Apollo monuments.",
        58,
        "locator:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (166, 28, 276, 66), (215, 94), max_size=8)
    add_panel_label(panel, records, "ILISSOS", (26, 182, 108, 220), (116, 180), max_size=8)
    add_panel_label(panel, records, "OLYMPIEION", (230, 188, 374, 228), (255, 166), max_size=8)
    add_panel_label(panel, records, "DELPHINION ZONE?", (20, 92, 166, 132), (185, 158), max_size=8)
    return panel


def make_apollo_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for the Pythian Apollo monument."""
    art = warm_art(
        crop_to_fill(APOLLO_ART, (390, 280), centering=(0.49, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "A statue of Apollo Pythios stood close by, beyond Olympian Zeus.",
        58,
        "apollo:caption",
        records,
    )
    add_panel_label(panel, records, "APOLLO PYTHIOS", (22, 30, 170, 70), (122, 150), max_size=8)
    add_panel_label(panel, records, "OLYMPIEION", (238, 34, 372, 74), (286, 122), max_size=8)
    return panel


def make_arrival_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for Theseus's unknown arrival and the builders' mockery."""
    art = warm_art(
        crop_to_fill(ARRIVAL_ART, (438, 280), centering=(0.52, 0.49)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Unknown in Athens, the robed Theseus was mocked by the builders before answering with strength.",
        58,
        "arrival:caption",
        records,
    )
    add_panel_label(panel, records, "THESEUS", (22, 190, 122, 230), (146, 162), max_size=8)
    add_panel_label(panel, records, "LONG ROBE", (128, 30, 240, 68), (158, 142), max_size=8)
    add_panel_label(panel, records, "ROOF BUILDERS", (282, 30, 426, 70), (328, 110), max_size=8)
    add_panel_label(panel, records, "CART", (326, 190, 414, 230), (342, 172), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, LOCATOR_ART, APOLLO_ART, ARRIVAL_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.19.1",
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
            (28, 92, passage_panel.width - 28, 438),
            translation,
            BODY_FONT,
            max_size=19,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    note_rect = (24, 454, 346, 584)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias records the monuments and legendary feat. Exact sanctuary positions, architecture, and action are reconstructed; the locator shows his later Roman-period route.",
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=10,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (36, 606, 334, 640),
            "ATHENS · OLYMPIEION · DELPHINION",
            TITLE_FONT,
            max_size=9,
            min_size=7,
            padding=4,
            name="passage:orientation",
            align="center",
            spacing_ratio=0.04,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.38)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (690, 40, 1190, 98)
    paste_with_shadow(
        page,
        make_label(
            "THESEUS AT THE UNFINISHED DELPHINION",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=18,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("UNFINISHED ROOF", (438, 178, 630, 220), (690, 238)),
        ("ROOF BUILDERS", (438, 340, 610, 382), (694, 205)),
        ("AIRBORNE CART", (1060, 96, 1280, 140), (976, 122)),
        ("THESEUS", (726, 512, 852, 554), (858, 468)),
        ("UNYOKED OXEN", (1114, 506, 1304, 550), (1192, 492)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (618, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "THE CART ROSE ABOVE THE BUILDERS · THE OXEN HAD BEEN LOOSED",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=10,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_locator_panel(records), (28, 700))
    paste_with_shadow(page, make_apollo_panel(records), (462, 700))
    paste_with_shadow(page, make_arrival_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/18/9.png"],
        "evidence_boundary": "Recorded monuments and legendary details are distinguished from reconstructed positions, forms, and action.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of Theseus hurling the cart above the unfinished Delphinion."},
            {"path": str(LOCATOR_ART), "description": "Generated textured reconstruction of Roman-period southeast Athens."},
            {"path": str(APOLLO_ART), "description": "Generated study of the Pythian Apollo monument near the Olympieion."},
            {"path": str(ARRIVAL_ART), "description": "Generated narrative study of the robed Theseus and mocking builders."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_19_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/19/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
