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


PASSAGE_ID = "1.18.9"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_9"
MAIN_ART = ASSET_DIR / "main_sanctuary.png"
TEMPLE_ART = ASSET_DIR / "hera_zeus_temple.png"
LIBRARY_ART = ASSET_DIR / "library_room.png"
GYMNASIUM_ART = ASSET_DIR / "gymnasium.png"


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


def make_temple_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for the shared temple of Hera and Zeus Panhellenios."""
    art = warm_art(
        crop_to_fill(TEMPLE_ART, (390, 280), centering=(0.53, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Hadrian built a temple shared by Hera and Zeus Panhellenios.",
        58,
        "temple:caption",
        records,
    )
    add_panel_label(panel, records, "HERA", (204, 30, 278, 68), (236, 156), max_size=8)
    add_panel_label(panel, records, "ZEUS PANHELLENIOS", (260, 188, 380, 230), (276, 155), max_size=8)
    return panel


def make_library_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for the sanctuary's decorated book room."""
    art = warm_art(
        crop_to_fill(LIBRARY_ART, (390, 280), centering=(0.54, 0.48)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Gilt and alabaster framed statues, paintings, and rooms furnished with books.",
        58,
        "library:caption",
        records,
    )
    add_panel_label(panel, records, "GILT CEILING", (12, 30, 138, 68), (152, 56), max_size=8)
    add_panel_label(panel, records, "ALABASTER", (12, 192, 126, 232), (170, 126), max_size=8)
    add_panel_label(panel, records, "SCROLL CUPBOARDS", (236, 30, 380, 68), (334, 138), max_size=8)
    return panel


def make_gymnasium_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for Hadrian's hundred-column gymnasium."""
    art = warm_art(
        crop_to_fill(GYMNASIUM_ART, (438, 280), centering=(0.56, 0.51)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Hadrian's gymnasium likewise had one hundred columns, quarried in Libya.",
        58,
        "gymnasium:caption",
        records,
    )
    add_panel_label(panel, records, "LIBYAN STONE", (12, 30, 148, 68), (178, 140), max_size=8)
    add_panel_label(panel, records, "PALAESTRA", (292, 188, 426, 228), (258, 158), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, TEMPLE_ART, LIBRARY_ART, GYMNASIUM_ART):
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
            "PASSAGE 1.18.9",
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
            (28, 92, passage_panel.width - 28, 384),
            translation,
            BODY_FONT,
            max_size=20,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    note_rect = (24, 404, 346, 578)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias records the buildings, column counts, materials, decoration, statues, paintings, and books. Exact plans, appearances, and sites are uncertain; these are evidence-led reconstructions.",
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
            (36, 602, 334, 640),
            "HADRIANIC ATHENS · SANCTUARY · GYMNASIUM",
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
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.51, 0.49)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (728, 40, 1242, 98)
    paste_with_shadow(
        page,
        make_label(
            "HADRIAN'S SANCTUARY OF ALL THE GODS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=18,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACROPOLIS", (438, 108, 568, 150), (594, 190)),
        ("OLYMPIEION", (438, 274, 578, 316), (622, 266)),
        ("SANCTUARY COURT", (482, 528, 662, 570), (668, 448)),
        ("PHRYGIAN-MARBLE COLUMNS", (812, 526, 1064, 570), (958, 342)),
        ("MATCHING PORTICO WALL", (1090, 470, 1320, 514), (1060, 248)),
        ("GILT CEILINGS", (1104, 112, 1280, 154), (1168, 180)),
        ("BOOK ROOMS", (1134, 250, 1298, 292), (1214, 318)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (652, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "ONE HUNDRED PHRYGIAN-MARBLE COLUMNS · EXACT PLAN AND SITE UNCERTAIN",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_temple_panel(records), (28, 700))
    paste_with_shadow(page, make_library_panel(records), (462, 700))
    paste_with_shadow(page, make_gymnasium_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/18/8.png"],
        "evidence_boundary": "Recorded buildings, counts, materials, decoration, artworks, and books are distinguished from reconstructed appearance and placement.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the Phrygian-marble common sanctuary and decorated rooms."},
            {"path": str(TEMPLE_ART), "description": "Generated reconstruction of the shared Hera and Zeus Panhellenios temple."},
            {"path": str(LIBRARY_ART), "description": "Generated reconstruction of a gilt-and-alabaster book and gallery room."},
            {"path": str(GYMNASIUM_ART), "description": "Generated reconstruction of the Libyan-stone hundred-column gymnasium."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_9_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/9.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
