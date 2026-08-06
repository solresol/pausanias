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


PASSAGE_ID = "1.17.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_17_5"
MAIN_ART = ASSET_DIR / "main_acheron.png"
DODONA_ART = ASSET_DIR / "dodona_oak.png"
APHIDNA_ART = ASSET_DIR / "aphidna_capture.png"
MAP_ART = ASSET_DIR / "epirus_attica_relief.png"


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
    """Draw a fitted label and semantic leader inside an inset."""
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


def make_dodona_panel(records: list[FitRecord]) -> Image.Image:
    """Build the sanctuary and sacred-oak inset."""
    art = warm_art(
        crop_to_fill(DODONA_ART, (390, 280), centering=(0.58, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "At Dodona, Zeus' sanctuary was centred on the sacred oak and its oracular signs.",
        58,
        "dodona:caption",
        records,
    )
    add_panel_label(panel, records, "SACRED OAK", (240, 30, 414, 68), (264, 118))
    add_panel_label(panel, records, "BRONZE OFFERINGS", (12, 202, 194, 240), (212, 184))
    return panel


def make_aphidna_panel(records: list[FitRecord]) -> Image.Image:
    """Build the capture-of-Aphidna narrative inset."""
    art = warm_art(
        crop_to_fill(APHIDNA_ART, (390, 280), centering=(0.56, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "While Theseus was absent, the sons of Tyndareus captured Aphidna and installed Menestheus.",
        58,
        "aphidna:caption",
        records,
    )
    add_panel_label(panel, records, "APHIDNA", (280, 30, 414, 68), (300, 112))
    add_panel_label(panel, records, "BREACHED GATE", (12, 202, 170, 240), (206, 118))
    add_panel_label(panel, records, "ADVANCE", (298, 202, 414, 240), (284, 188))
    return panel


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build a rich but subordinate regional orientation inset."""
    art = warm_art(
        crop_to_fill(MAP_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    dodona = (104, 76)
    cichyrus = (78, 132)
    aphidna = (332, 212)
    context = [cichyrus, (154, 154), (232, 180), aphidna]
    draw.line(context, fill="#f6e2ad", width=6)
    draw.line(context, fill=RULE, width=2)
    for point in (dodona, cichyrus, aphidna):
        draw.ellipse(
            (point[0] - 6, point[1] - 6, point[0] + 6, point[1] + 6),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "Dodona and Cichyrus lie in north-west Greece; Aphidna belongs to Attica.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "DODONA", (12, 30, 122, 68), (122, 94))
    add_panel_label(panel, records, "CICHYRUS", (12, 202, 130, 240), (96, 150))
    add_panel_label(panel, records, "APHIDNA", (354, 202, 462, 240), (350, 230))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, DODONA_ART, APHIDNA_ART, MAP_ART):
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
            "PASSAGE 1.17.5",
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
            (28, 92, passage_panel.width - 28, 442),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 464, 346, 586)
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
            "Pausanias links a real Thesprotian landscape to Homer's poetic underworld. Shorelines, river courses, sanctuaries, and settlements shown here are reconstructions.",
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
            (38, 604, 332, 640),
            "THESPROTIA · DODONA · APHIDNA",
            TITLE_FONT,
            max_size=10,
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
        grain_strength=0.005,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (686, 40, 1112, 98)
    paste_with_shadow(
        page,
        make_label(
            "RIVERS AT THE EDGE OF HADES",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=19,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACHERON", (438, 446, 584, 490), (650, 492)),
        ("CICHYRUS", (448, 126, 602, 170), (874, 292)),
        ("LAKE ACHERUSIA", (1118, 126, 1348, 170), (1090, 274)),
        ("COCYTUS", (1168, 446, 1316, 490), (1142, 510)),
        ("RIVER CONFLUENCE", (934, 548, 1190, 592), (932, 526)),
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

    orientation_rect = (650, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "PAUSANIAS SAYS HOMER ADOPTED THESE THESPROTIAN NAMES FOR THE UNDERWORLD",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_dodona_panel(records), (28, 700))
    paste_with_shadow(page, make_aphidna_panel(records), (462, 700))
    paste_with_shadow(page, make_map_panel(records), (896, 700))

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
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/17/4.png"],
        "evidence_boundary": "The ancient shorelines, river courses, sanctuary furnishings, settlement forms, and Aphidna assault are reconstructed; no surveyed plan is claimed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd83c-1117-7a42-b252-04bf3e04cbe2/exec-21782b2e-c85d-497f-bd8f-39f04e687bfb.png",
                "description": "Generated reconstruction of Lake Acherusia, Acheron, Cocytus, and Cichyrus in Thesprotia.",
            },
            {
                "path": str(DODONA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd83c-1117-7a42-b252-04bf3e04cbe2/exec-fa7f7bf1-7725-4420-b516-0af8adeceec8.png",
                "description": "Generated reconstruction of the sanctuary and sacred oak of Zeus at Dodona.",
            },
            {
                "path": str(APHIDNA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd83c-1117-7a42-b252-04bf3e04cbe2/exec-a86fc8c0-12d3-4bb2-b54e-198cd92043c6.png",
                "description": "Generated Bronze Age reconstruction of Aphidna's capture by the sons of Tyndareus.",
            },
            {
                "path": str(MAP_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd83c-1117-7a42-b252-04bf3e04cbe2/exec-df776492-7aec-466b-bd88-2a7e56d22922.png",
                "description": "Generated textured relief base used only as a subordinate orientation inset.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_17_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/17/5.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
