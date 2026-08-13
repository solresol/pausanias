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


PASSAGE_ID = "1.18.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_6"
MAIN_ART = ASSET_DIR / "main_olympieion.png"
MAP_ART = ASSET_DIR / "athens_relief.png"
ZEUS_ART = ASSET_DIR / "zeus_cella.png"
COLONIES_ART = ASSET_DIR / "hadrian_colonies.png"


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
        crop_to_fill(MAP_ART, (390, 280), centering=(0.50, 0.53)),
        grain_strength=0.003,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    acropolis = (105, 118)
    olympieion = (205, 216)
    ilissos = (326, 220)
    route = [acropolis, (150, 164), olympieion, ilissos]
    draw.line(route, fill="#f6e4b6", width=7)
    draw.line(route, fill=RULE, width=2)
    for point in (acropolis, olympieion, ilissos):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "The Olympieion stood southeast of the Acropolis beside the Ilissos corridor.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (10, 30, 142, 68), acropolis, max_size=8)
    add_panel_label(panel, records, "OLYMPIEION", (124, 186, 264, 224), olympieion, max_size=8)
    add_panel_label(panel, records, "ILISSOS", (282, 142, 380, 180), ilissos, max_size=8)
    return panel


def make_zeus_panel(records: list[FitRecord]) -> Image.Image:
    """Build the chryselephantine Zeus and scale inset."""
    art = warm_art(
        crop_to_fill(ZEUS_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Inside, the colossal seated Zeus combined ivory surfaces with worked gold.",
        58,
        "zeus:caption",
        records,
    )
    add_panel_label(panel, records, "IVORY SURFACES", (12, 30, 158, 68), (204, 84), max_size=8)
    add_panel_label(panel, records, "GOLD DRAPERY", (250, 30, 380, 68), (228, 144), max_size=8)
    add_panel_label(panel, records, "HUMAN SCALE", (12, 204, 138, 242), (108, 226), max_size=8)
    return panel


def make_colonies_panel(records: list[FitRecord]) -> Image.Image:
    """Build the stone Hadrians and bronze colonies inset."""
    art = warm_art(
        crop_to_fill(COLONIES_ART, (438, 280), centering=(0.49, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Four stone Hadrians stood apart from the bronze civic figures called colonies.",
        58,
        "colonies:caption",
        records,
    )
    add_panel_label(panel, records, "TWO THASIAN", (12, 30, 138, 68), (92, 140), max_size=8)
    add_panel_label(panel, records, "TWO EGYPTIAN", (144, 30, 282, 68), (198, 142), max_size=8)
    add_panel_label(panel, records, "BRONZE COLONIES", (282, 192, 430, 232), (354, 150), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, MAP_ART, ZEUS_ART, COLONIES_ART):
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
            "PASSAGE 1.18.6",
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
            (28, 92, passage_panel.width - 28, 430),
            translation,
            BODY_FONT,
            max_size=19,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.08,
        )
    )
    note_rect = (24, 448, 346, 586)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias records the materials, scale, statue groups, and enclosure size. Their exact appearance and placement here are reconstructed; the locator shows broad historical relationships rather than a surveyed plan.",
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
            (38, 606, 332, 640),
            "ACROPOLIS · OLYMPIEION · ILISSOS",
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
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.51, 0.50)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (650, 40, 1138, 98)
    paste_with_shadow(
        page,
        make_label(
            "HADRIAN'S OLYMPIEION",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=20,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACROPOLIS", (438, 112, 570, 156), (584, 156)),
        ("CORINTHIAN COLONNADE", (470, 238, 696, 282), (790, 312)),
        ("CITY DEDICATIONS", (456, 520, 650, 564), (612, 490)),
        ("FOUR-STADE ENCLOSURE", (1028, 540, 1262, 584), (1266, 570)),
        ("ATHENIAN COLOSSUS", (1110, 210, 1314, 254), (1240, 268)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (646, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "A COMPLETED TEMPLE WITH AN ENCLOSURE CROWDED BY IMPERIAL AND CIVIC DEDICATIONS",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_map_panel(records), (28, 700))
    paste_with_shadow(page, make_zeus_panel(records), (462, 700))
    paste_with_shadow(page, make_colonies_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/18/5.png"],
        "evidence_boundary": "The recorded materials, scale, statue groupings, and enclosure size are distinguished from reconstructed appearance and placement.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the completed Olympieion and its statue-filled precinct."},
            {"path": str(MAP_ART), "description": "Generated textured central-Athens relief used only as a subordinate locator."},
            {"path": str(ZEUS_ART), "description": "Generated and content-suitability-corrected reconstruction of the chryselephantine Zeus."},
            {"path": str(COLONIES_ART), "description": "Generated reconstruction distinguishing four stone Hadrians from bronze colony figures."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
