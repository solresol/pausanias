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


PASSAGE_ID = "1.19.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_19_3"
MAIN_ART = ASSET_DIR / "main_athens.png"
WHITE_DOG_ART = ASSET_DIR / "white_dog.png"
ALTARS_ART = ASSET_DIR / "altars.png"
LYCUS_ART = ASSET_DIR / "lycus_lycia.png"


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


def make_white_dog_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for Pausanias' unexplained white-dog oracle."""
    art = warm_art(
        crop_to_fill(WHITE_DOG_ART, (390, 280), centering=(0.53, 0.58)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Pausanias alludes to an oracle concerning a white dog, but does not preserve its wording here.",
        58,
        "dog:caption",
        records,
    )
    add_panel_label(panel, records, "WHITE DOG", (246, 174, 374, 216), (276, 158), max_size=8)
    add_panel_label(panel, records, "ORACLE CONSULTED", (18, 28, 172, 70), (160, 100), max_size=8)
    add_panel_label(panel, records, "SANCTUARY COURT", (218, 28, 374, 70), (292, 102), max_size=8)
    return panel


def make_altars_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for the four cult relationships at Cynosarges."""
    art = warm_art(
        crop_to_fill(ALTARS_ART, (390, 280), centering=(0.50, 0.54)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "The reconstructed altar court distinguishes Heracles, Hebe, Alcmena, and Iolaus.",
        58,
        "altars:caption",
        records,
    )
    add_panel_label(panel, records, "HERACLES", (16, 26, 102, 66), (58, 102), max_size=8)
    add_panel_label(panel, records, "HEBE", (112, 26, 184, 66), (142, 100), max_size=8)
    add_panel_label(panel, records, "ALCMENA", (204, 26, 292, 66), (244, 104), max_size=8)
    add_panel_label(panel, records, "IOLAUS", (302, 26, 376, 66), (338, 104), max_size=8)
    return panel


def make_lycus_panel(records: list[FitRecord]) -> Image.Image:
    """Build the migration-tradition inset for Lycus and the Termilae."""
    art = warm_art(
        crop_to_fill(LYCUS_ART, (438, 280), centering=(0.50, 0.54)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Reported tradition: Lycus fled Aegeus to the Termilae, whose later name was linked to him.",
        58,
        "lycus:caption",
        records,
    )
    add_panel_label(panel, records, "LYCUS FROM ATHENS", (18, 28, 178, 70), (154, 126), max_size=8)
    add_panel_label(panel, records, "TERMILAE", (324, 170, 424, 212), (344, 146), max_size=8)
    add_panel_label(panel, records, "LYCIAN LANDSCAPE", (238, 28, 422, 70), (304, 100), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, WHITE_DOG_ART, ALTARS_ART, LYCUS_ART):
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
            "PASSAGE 1.19.3",
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
            (28, 90, passage_panel.width - 28, 484),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.08,
        )
    )
    note_rect = (24, 500, 346, 584)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Recorded sanctuary names and relationships are separated from reconstructed locations, buildings, rituals, and the reported naming tradition.",
            BODY_FONT,
            max_size=11,
            min_size=8,
            padding=9,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.07,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (34, 604, 336, 640),
            "ATHENS · CYNOSARGES · LYCEUM · LYCIA",
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
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.52)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (704, 40, 1128, 98)
    paste_with_shadow(
        page,
        make_label(
            "CYNOSARGES AND THE LYCEUM",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=20,
            min_size=12,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACROPOLIS", (438, 104, 560, 146), (592, 104)),
        ("ILISSOS", (632, 256, 728, 298), (802, 318)),
        ("CYNOSARGES", (430, 484, 570, 528), (692, 514)),
        ("HERACLES SANCTUARY", (584, 552, 790, 596), (730, 518)),
        ("LYCEUM GROVE", (1052, 232, 1214, 276), (1050, 296)),
        ("APOLLO LYCEIUS", (1176, 382, 1334, 426), (1220, 354)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (814, 612, 1330, 654)
    paste_with_shadow(
        page,
        make_label(
            "RECONSTRUCTED PRECINCTS · ILISSOS AND ACROPOLIS ORIENT THE VIEW",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_white_dog_panel(records), (28, 700))
    paste_with_shadow(page, make_altars_panel(records), (462, 700))
    paste_with_shadow(page, make_lycus_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/19/2.png"],
        "evidence_boundary": "Recorded sanctuary names and relationships are separated from reconstructed locations, buildings, ritual scenes, and naming tradition.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated oblique reconstruction of Cynosarges, the Lyceum, Ilissos, and Athens."},
            {"path": str(WHITE_DOG_ART), "description": "Generated scenic treatment of the unexplained white-dog oracle allusion."},
            {"path": str(ALTARS_ART), "description": "Generated reconstruction of the four cult dedications at Cynosarges."},
            {"path": str(LYCUS_ART), "description": "Generated scenic treatment of Lycus' reported arrival among the Termilae."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_19_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/19/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
