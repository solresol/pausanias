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


PASSAGE_ID = "1.18.7"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_7"
MAIN_ART = ASSET_DIR / "main_earth_olympias.png"
MAP_ART = ASSET_DIR / "athens_precinct_relief.png"
TEMPLE_ART = ASSET_DIR / "cronus_rhea_zeus.png"
FLOOD_ART = ASSET_DIR / "deucalion_flood.png"


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
    """Draw a measured label and a leader ending on the named feature."""
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


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build the subordinate central-Athens relief locator."""
    art = warm_art(
        crop_to_fill(MAP_ART, (390, 280), centering=(0.50, 0.52)),
        grain_strength=0.003,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    acropolis = (93, 91)
    olympieion = (266, 190)
    earth = (238, 217)
    route = [acropolis, (160, 130), olympieion, earth]
    draw.line(route, fill="#f6e4b6", width=7)
    draw.line(route, fill=RULE, width=2)
    for point in (acropolis, olympieion, earth):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "Earth Olympias lay within the Olympieion enclosure, southeast of the Acropolis.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (10, 30, 142, 68), acropolis, max_size=8)
    add_panel_label(panel, records, "OLYMPIEION", (238, 102, 380, 140), olympieion, max_size=8)
    add_panel_label(panel, records, "EARTH OLYMPIAS", (188, 220, 372, 258), earth, max_size=8)
    return panel


def make_temple_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Cronus-Rhea temple and ancient bronze Zeus inset."""
    art = warm_art(
        crop_to_fill(TEMPLE_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Pausanias distinguishes the Cronus-Rhea temple from the ancient bronze Zeus.",
        58,
        "temple:caption",
        records,
    )
    add_panel_label(panel, records, "CRONUS AND RHEA", (12, 30, 174, 68), (167, 122), max_size=8)
    add_panel_label(panel, records, "ANCIENT BRONZE ZEUS", (204, 30, 380, 68), (320, 138), max_size=8)
    return panel


def make_flood_panel(records: list[FitRecord]) -> Image.Image:
    """Build the reported Deucalion flood tradition inset."""
    art = warm_art(
        crop_to_fill(FLOOD_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Athenians said the water of Deucalion's flood drained away through the fissure.",
        58,
        "flood:caption",
        records,
    )
    add_panel_label(panel, records, "DEUCALION AND PYRRHA", (12, 30, 206, 68), (93, 150), max_size=8)
    add_panel_label(panel, records, "RECEDING WATER", (242, 30, 430, 68), (292, 132), max_size=8)
    add_panel_label(panel, records, "REPORTED DRAINAGE", (232, 202, 430, 242), (326, 223), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, MAP_ART, TEMPLE_ART, FLOOD_ART):
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
            "PASSAGE 1.18.7",
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
            (28, 102, passage_panel.width - 28, 342),
            translation,
            BODY_FONT,
            max_size=22,
            min_size=13,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    note_rect = (24, 374, 346, 558)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias records the cult places, the fissure's approximate width, the annual offering, and the local flood tradition. Their exact appearance and placement here are reconstructed; the locator shows broad historical relationships rather than a surveyed plan.",
            BODY_FONT,
            max_size=13,
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
            (36, 596, 334, 636),
            "ATHENS · OLYMPIEION · EARTH OLYMPIAS",
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
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (650, 40, 1134, 98)
    paste_with_shadow(
        page,
        make_label(
            "EARTH OLYMPIAS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=21,
            min_size=12,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ANCIENT BRONZE ZEUS", (438, 118, 634, 162), (520, 242)),
        ("TEMPLE OF CRONUS AND RHEA", (604, 344, 844, 388), (744, 340)),
        ("WHEAT MEAL AND HONEY", (816, 512, 1022, 556), (1008, 514)),
        ("ONE-CUBIT FISSURE", (1082, 558, 1270, 602), (1044, 574)),
        ("OLYMPIEION COLUMNS", (1120, 134, 1318, 178), (1246, 210)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (674, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "AN ANNUAL OFFERING AT A FISSURE LINKED TO THE MEMORY OF DEUCALION'S FLOOD",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_map_panel(records), (28, 700))
    paste_with_shadow(page, make_temple_panel(records), (462, 700))
    paste_with_shadow(page, make_flood_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/18/6.png"],
        "evidence_boundary": "Recorded cult places, fissure size, annual offering, and reported flood tradition are distinguished from reconstructed appearance and placement.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the Earth Olympias fissure offering within the Olympieion enclosure."},
            {"path": str(MAP_ART), "description": "Generated textured central-Athens relief used only as a subordinate locator."},
            {"path": str(TEMPLE_ART), "description": "Generated and content-suitability-corrected reconstruction of the Cronus-Rhea temple and ancient bronze Zeus."},
            {"path": str(FLOOD_ART), "description": "Generated reconstruction of the reported Deucalion flood drainage tradition."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_7_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/7.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
