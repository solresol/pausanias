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


PASSAGE_ID = "1.16.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_16_3"
MAIN_ART = ASSET_DIR / "main_seleucia.png"
ATLAS_ART = ASSET_DIR / "route_atlas.png"
APOLLO_ART = ASSET_DIR / "apollo_return.png"
BABYLON_ART = ASSET_DIR / "babylon_bel.png"


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


def make_atlas_panel(records: list[FitRecord]) -> Image.Image:
    """Build the east-west restitution and Mesopotamian migration atlas."""
    art = warm_art(
        crop_to_fill(ATLAS_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Apollo travelled west from Media; Babylonian settlers moved east to Seleucia.",
        58,
        "atlas:caption",
        records,
    )
    add_panel_label(panel, records, "BRANCHIDAE", (14, 194, 126, 230), (66, 154))
    add_panel_label(panel, records, "ECBATANA", (262, 30, 378, 66), (312, 110))
    add_panel_label(panel, records, "BABYLON", (176, 194, 276, 230), (238, 166))
    add_panel_label(panel, records, "SELEUCIA", (278, 212, 388, 248), (330, 180))
    return panel


def make_apollo_panel(records: list[FitRecord]) -> Image.Image:
    """Build the ceremonial restitution panel at Branchidae."""
    art = warm_art(
        crop_to_fill(APOLLO_ART, (390, 280), centering=(0.55, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Seleucus restored the bronze Apollo carried away by Xerxes.",
        58,
        "apollo:caption",
        records,
    )
    add_panel_label(panel, records, "BRONZE APOLLO", (210, 30, 378, 68), (264, 132))
    add_panel_label(panel, records, "RETURN TO BRANCHIDAE", (16, 214, 202, 252), (166, 170))
    return panel


def make_babylon_panel(records: list[FitRecord]) -> Image.Image:
    """Build the preserved Babylonian sanctuary panel."""
    art = warm_art(
        crop_to_fill(BABYLON_ART, (438, 280), centering=(0.52, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Babylon's wall, Bel's sanctuary, and its Chaldean community remained.",
        58,
        "babylon:caption",
        records,
    )
    add_panel_label(panel, records, "SANCTUARY OF BEL", (172, 30, 352, 68), (235, 130))
    add_panel_label(panel, records, "CHALDEAN SCHOLARS", (14, 214, 196, 252), (92, 170))
    add_panel_label(panel, records, "BABYLON'S WALL", (294, 206, 430, 244), (370, 146))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, ATLAS_ART, APOLLO_ART, BABYLON_ART):
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
            "PASSAGE 1.16.3",
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
            (28, 92, passage_panel.width - 28, 492),
            translation,
            BODY_FONT,
            max_size=17,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 508, 346, 600)
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
            "Pausanias measures Seleucus by three acts: returning a god, founding a city, and preserving an older sacred community.",
            BODY_FONT,
            max_size=13,
            min_size=9,
            padding=10,
            name="passage:interpretive-note",
            align="center",
            spacing_ratio=0.09,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (40, 612, 330, 640),
            "IONIA · MEDIA · MESOPOTAMIA",
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

    heading_rect = (650, 40, 1210, 98)
    paste_with_shadow(
        page,
        make_label(
            "SELEUCIA RISES BESIDE THE TIGRIS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=16,
            min_size=10,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("THE TIGRIS", (442, 134, 590, 176), (620, 280)),
        ("BABYLONIAN SETTLERS", (480, 510, 720, 554), (812, 528)),
        ("MASONRY QUAYS", (486, 366, 660, 408), (758, 402)),
        ("PLANNED HELLENISTIC CITY", (1040, 188, 1334, 232), (1060, 320)),
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

    orientation_rect = (768, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "EARLY THIRD CENTURY BCE · A NEW CAPITAL ON AN ANCIENT RIVER",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_atlas_panel(records), (28, 700))
    paste_with_shadow(page, make_apollo_panel(records), (462, 700))
    paste_with_shadow(page, make_babylon_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/16/2.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fbe7c-52e4-74e0-96b3-0878762c85e1/exec-e2ec47da-caac-4fed-9126-e8491f36893d.png",
                "description": "Generated archaeological reconstruction of Seleucia on the Tigris.",
            },
            {
                "path": str(ATLAS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fbe7c-52e4-74e0-96b3-0878762c85e1/exec-119b6b3a-8c7d-4951-a754-4ab0b928b9b4.png",
                "description": "Generated relief atlas joining Ionia, Media, Babylon, and Seleucia.",
            },
            {
                "path": str(APOLLO_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fbe7c-52e4-74e0-96b3-0878762c85e1/exec-0541f8c4-5cd1-4d25-bf11-fd284b406224.png",
                "description": "Generated ceremonial return of the draped bronze Apollo to Branchidae.",
            },
            {
                "path": str(BABYLON_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fbe7c-52e4-74e0-96b3-0878762c85e1/exec-1c3b1ffe-4ec8-40d1-8147-4995de35b7d2.png",
                "description": "Generated Babylonian sanctuary and Chaldean scholarly community.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_16_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/16/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
