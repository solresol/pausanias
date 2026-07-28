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
    DISPLAY_FONT,
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


PASSAGE_ID = "1.15.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_15_3"
MAIN_ART = ASSET_DIR / "main_marathon.png"
HERO_ART = ASSET_DIR / "hero_epiphany.png"
COMMANDERS_ART = ASSET_DIR / "commanders.png"


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


def leader_endpoint(rect: tuple[int, int, int, int], point: tuple[int, int]) -> tuple[int, int]:
    """Return the nearest useful edge point of a callout rectangle."""
    endpoint = (
        rect[0] if point[0] < rect[0] else rect[2],
        (rect[1] + rect[3]) // 2,
    )
    if rect[0] <= point[0] <= rect[2]:
        endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return endpoint


def add_local_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 10,
    min_size: int = 7,
) -> None:
    """Add one measured label and a semantic leader to an inset."""
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


def make_hero_panel(records: list[FitRecord]) -> Image.Image:
    """Build the heroic-epiphany inset from generated raster art."""
    art = warm_art(
        crop_to_fill(HERO_ART, (614, 278), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "The painting placed local hero, earth-born founder, and divine patrons on the field.",
        88,
        "heroes:caption",
        records,
    )
    add_local_label(panel, records, "MARATHON", (16, 18, 132, 58), (102, 138))
    add_local_label(panel, records, "THEREUS", (228, 224, 340, 264), (298, 164))
    add_local_label(panel, records, "ATHENA", (390, 18, 492, 58), (454, 132))
    add_local_label(panel, records, "HERACLES", (514, 224, 632, 264), (562, 138))
    return panel


def make_commanders_panel(records: list[FitRecord]) -> Image.Image:
    """Build the named-commanders inset from generated raster art."""
    art = warm_art(
        crop_to_fill(COMMANDERS_ART, (624, 278), centering=(0.50, 0.52)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Callimachus and Miltiades stand prominent; Echetlos fights with the plough.",
        88,
        "commanders:caption",
        records,
    )
    add_local_label(panel, records, "CALLIMACHUS", (18, 18, 160, 58), (186, 150), max_size=9)
    add_local_label(panel, records, "MILTIADES", (250, 18, 376, 58), (326, 142), max_size=9)
    add_local_label(panel, records, "ECHETLOS", (510, 18, 632, 58), (492, 154), max_size=9)
    add_local_label(
        panel,
        records,
        "ATHENIAN & PLATAEAN LINE",
        (204, 224, 456, 264),
        (392, 188),
        max_size=8,
        min_size=6,
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render the page, validate every text block, and write a fit report."""
    translation = load_translation()
    for asset in (MAIN_ART, HERO_ART, COMMANDERS_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 648))
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
            "PASSAGE 1.15.3",
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
            (26, 94, passage_panel.width - 26, passage_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 620), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((968, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (650, 42, 1136, 98)
    paste_with_shadow(
        page,
        make_label(
            "THE PLAIN OF MARATHON",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=19,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("INLAND HEIGHTS", (438, 112, 610, 154), (560, 184)),
        ("ATHENIANS & PLATAEANS", (430, 544, 688, 588), (674, 432)),
        ("PERSIAN LINE", (770, 502, 926, 544), (894, 398)),
        ("THE MARSH", (1110, 150, 1248, 192), (1136, 282)),
        ("PHOENICIAN SHIPS", (1120, 558, 1348, 602), (1238, 484)),
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

    sequence_points = [(694, 444), (984, 376), (1218, 478)]
    draw.line(sequence_points, fill="#f6e7bd", width=7, joint="curve")
    draw.line(sequence_points, fill="#7d4c28", width=3, joint="curve")
    for point in sequence_points:
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#7d4c28",
            outline="#f6e7bd",
            width=2,
        )
    sequence_labels = [
        ("EVENLY MATCHED", (606, 374, 786, 414), sequence_points[0]),
        ("ROUT THROUGH MARSH", (902, 298, 1120, 340), sequence_points[1]),
        ("FIGHT AT THE SHIPS", (1144, 398, 1350, 440), sequence_points[2]),
    ]
    for text, rect, point in sequence_labels:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=8,
                min_size=6,
            ),
            rect[:2],
        )

    orientation_rect = (1000, 616, 1350, 656)
    paste_with_shadow(
        page,
        make_label(
            "MARATHON · NORTHEAST ATTICA · BAY TO THE EAST",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=8,
            min_size=6,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_hero_panel(records), (28, 692))
    paste_with_shadow(page, make_commanders_panel(records), (706, 692))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/15/2.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa9e2-ef4b-73f1-8156-1e7ad7b46562/call_Vj1id9GczLpLUwckfU4aUim2.png",
                "description": "Generated oblique panorama of the Marathon plain, marsh, battle, bay, and Phoenician ships.",
            },
            {
                "path": str(HERO_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa9e2-ef4b-73f1-8156-1e7ad7b46562/call_XsqxjVHZ5jdGczjW5yNvGQKY.png",
                "description": "Generated heroic epiphany, locally labeled Thereus to match the database translation, with Marathon, Athena, and Heracles.",
            },
            {
                "path": str(COMMANDERS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa9e2-ef4b-73f1-8156-1e7ad7b46562/call_r9eSDUlqbXzIWsC25Y4aVKIf.png",
                "description": "Generated commander tableau with Callimachus, Miltiades, Echetlos, and the Greek line.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_15_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/15/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
