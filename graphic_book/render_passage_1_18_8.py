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


PASSAGE_ID = "1.18.8"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_8"
MAIN_ART = ASSET_DIR / "main_monuments.png"
MAP_ART = ASSET_DIR / "athens_precinct_relief.png"
SCHOOL_ART = ASSET_DIR / "isocrates_school.png"
GRAVE_ART = ASSET_DIR / "deucalion_grave.png"


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
    acropolis = (95, 90)
    olympieion = (292, 196)
    grave_zone = (245, 226)
    route = [acropolis, (176, 138), olympieion, grave_zone]
    draw.line(route, fill="#f6e4b6", width=7)
    draw.line(route, fill=RULE, width=2)
    for point in (acropolis, olympieion, grave_zone):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "The grave was shown near the Olympieion; its exact position is not securely known.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (10, 30, 142, 68), acropolis, max_size=8)
    add_panel_label(panel, records, "OLYMPIEION", (238, 102, 380, 140), olympieion, max_size=8)
    add_panel_label(panel, records, "REPORTED GRAVE ZONE", (184, 220, 380, 258), grave_zone, max_size=8)
    return panel


def make_school_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset representing Isocrates' long teaching career."""
    art = warm_art(
        crop_to_fill(SCHOOL_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Isocrates continued teaching pupils without interruption into extreme old age.",
        58,
        "school:caption",
        records,
    )
    add_panel_label(panel, records, "ISOCRATES", (12, 30, 146, 68), (150, 132), max_size=8)
    add_panel_label(panel, records, "PUPILS", (266, 30, 378, 68), (280, 145), max_size=8)
    return panel


def make_grave_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for the reported grave of Deucalion."""
    art = warm_art(
        crop_to_fill(GRAVE_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Athenians pointed to this nearby grave as evidence that Deucalion lived in Athens.",
        58,
        "grave:caption",
        records,
    )
    add_panel_label(panel, records, "REPORTED GRAVE", (12, 30, 184, 68), (92, 150), max_size=8)
    add_panel_label(panel, records, "EARLY SANCTUARY", (244, 196, 430, 236), (320, 180), max_size=8)
    add_panel_label(panel, records, "LATER OLYMPIEION", (244, 30, 430, 68), (345, 102), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, MAP_ART, SCHOOL_ART, GRAVE_ART):
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
            "PASSAGE 1.18.8",
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
            max_size=18,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    note_rect = (24, 456, 346, 586)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias records the monuments, materials, three memorials of Isocrates, sanctuary tradition, and nearby grave. Exact forms and placements here are reconstructed; the locator is not a surveyed plan.",
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
            "ATHENS · OLYMPIEION · DEUCALION",
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
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.20)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (760, 40, 1218, 98)
    paste_with_shadow(
        page,
        make_label(
            "MONUMENTS AT THE OLYMPIEION",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=21,
            min_size=12,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ISOCRATES", (438, 118, 584, 162), (654, 70)),
        ("COLUMN-MOUNTED STATUE", (438, 344, 668, 388), (654, 270)),
        ("PHRYGIAN MARBLE FIGURES", (690, 508, 926, 552), (900, 456)),
        ("BRONZE TRIPOD", (926, 294, 1098, 338), (972, 270)),
        ("OLYMPIEION COLUMNS", (1120, 134, 1318, 178), (1244, 226)),
        ("ACROPOLIS", (438, 520, 568, 564), (570, 338)),
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
            "CIVIC MEMORY IN STATUE, STONE, BRONZE, TEACHING, AND LOCAL TRADITION",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_map_panel(records), (28, 700))
    paste_with_shadow(page, make_school_panel(records), (462, 700))
    paste_with_shadow(page, make_grave_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/18/7.png"],
        "evidence_boundary": "Recorded monuments, materials, Isocrates traditions, sanctuary foundation tradition, and nearby grave are distinguished from reconstructed appearance and placement.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the Isocrates column and Phrygian-marble Persian supports with bronze tripod."},
            {"path": str(MAP_ART), "description": "Generated textured central-Athens relief used only as a subordinate locator."},
            {"path": str(SCHOOL_ART), "description": "Generated reconstruction of elderly Isocrates teaching pupils."},
            {"path": str(GRAVE_ART), "description": "Generated archaeological landscape for the Athenian tradition of Deucalion's grave."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_8_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/8.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
