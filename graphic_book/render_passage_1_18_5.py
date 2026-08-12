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


PASSAGE_ID = "1.18.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_5"
MAIN_ART = ASSET_DIR / "main_athens_eileithyia.png"
MAP_ART = ASSET_DIR / "aegean_relief.png"
DELOS_ART = ASSET_DIR / "delos_hymn.png"
AMNISOS_ART = ASSET_DIR / "amnisos_cave.png"


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
    """Draw a measured label and a leader that terminates on a relevant feature."""
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
    """Build the subordinate Athens-Delos-Crete relief locator."""
    art = warm_art(
        crop_to_fill(MAP_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.003,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    athens = (68, 78)
    delos = (192, 116)
    amnisos = (236, 206)
    knossos = (226, 224)
    route = [athens, (122, 94), delos, (216, 158), amnisos]
    draw.line(route, fill="#f6e4b6", width=7)
    draw.line(route, fill=RULE, width=2)
    for point in (athens, delos, amnisos, knossos):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "Athens, Delos, and north-central Crete frame three competing traditions of Eileithyia.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ATHENS", (10, 30, 108, 66), athens)
    add_panel_label(panel, records, "DELOS", (128, 74, 224, 110), delos)
    add_panel_label(
        panel,
        records,
        "HYPERBOREAN TRADITION",
        (224, 30, 382, 68),
        delos,
        max_size=7,
        min_size=6,
    )
    add_panel_label(panel, records, "AMNISOS", (260, 174, 374, 210), amnisos, max_size=8)
    add_panel_label(panel, records, "KNOSSOS", (254, 214, 368, 250), knossos, max_size=8)
    return panel


def make_delos_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Delian hymn and birth-tradition inset."""
    art = warm_art(
        crop_to_fill(DELOS_ART, (390, 280), centering=(0.52, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "On Delos, women sacrificed and sang Olen's hymn to the goddess who aided Leto.",
        58,
        "delos:caption",
        records,
    )
    add_panel_label(panel, records, "DELIAN HYMN", (12, 30, 136, 68), (98, 128), max_size=8)
    add_panel_label(panel, records, "LETO", (248, 30, 338, 68), (270, 134))
    add_panel_label(panel, records, "SWADDLED TWINS", (226, 190, 392, 228), (286, 164), max_size=8)
    return panel


def make_amnisos_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Cretan origin-tradition inset."""
    art = warm_art(
        crop_to_fill(AMNISOS_ART, (438, 280), centering=(0.52, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Cretans around Knossos said Eileithyia was born at coastal Amnisos, daughter of Hera.",
        58,
        "amnisos:caption",
        records,
    )
    add_panel_label(panel, records, "AMNISOS CAVE", (250, 30, 408, 68), (350, 126), max_size=8)
    add_panel_label(panel, records, "OFFERINGS", (238, 190, 370, 228), (310, 166), max_size=8)
    add_panel_label(panel, records, "CRETAN COAST", (12, 176, 158, 214), (90, 146), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, MAP_ART, DELOS_ART, AMNISOS_ART):
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
            "PASSAGE 1.18.5",
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
            "The Athenian sanctuary, its exact site, and the appearance of the three wooden images are reconstructed. Delian and Cretan scenes illustrate traditions reported by Pausanias, not independently verified events.",
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
            "ATHENS · DELOS · AMNISOS · KNOSSOS",
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

    heading_rect = (674, 40, 1120, 98)
    paste_with_shadow(
        page,
        make_label(
            "EILEITHYIA: THREE CULT IMAGES",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=19,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("OLDEST · FROM DELOS", (444, 118, 630, 162), (682, 338)),
        ("TWO CRETAN IMAGES", (968, 118, 1168, 162), (1052, 328)),
        ("COVERED TO THE FEET", (1016, 520, 1236, 564), (1048, 544)),
        ("WOODEN CULT IMAGES", (486, 520, 704, 564), (770, 394)),
        ("WOMEN'S OFFERINGS", (1136, 388, 1324, 432), (1196, 496)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (662, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "ATHENIAN CULT OBJECTS LINKED TO DELIAN AND CRETAN ORIGIN TRADITIONS",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_map_panel(records), (28, 700))
    paste_with_shadow(page, make_delos_panel(records), (462, 700))
    paste_with_shadow(page, make_amnisos_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/18/4.png"],
        "evidence_boundary": "The Athenian sanctuary, its exact site, and the three images are reconstructed; Delian and Cretan scenes illustrate reported traditions.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the Athenian sanctuary and three draped wooden images."},
            {"path": str(MAP_ART), "description": "Generated textured Aegean relief used only as a subordinate locator."},
            {"path": str(DELOS_ART), "description": "Generated Delian hymn and post-birth tradition scene."},
            {"path": str(AMNISOS_ART), "description": "Generated reconstruction of the Eileithyia cave landscape at Amnisos."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/5.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
