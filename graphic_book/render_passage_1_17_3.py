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


PASSAGE_ID = "1.17.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_17_3"
MAIN_ART = ASSET_DIR / "main_return.png"
SHIP_ART = ASSET_DIR / "ship_challenge.png"
MICON_ART = ASSET_DIR / "micon_wall.png"
MAP_ART = ASSET_DIR / "aegean_relief.png"


def load_translation() -> str:
    """Load the exact English translation from the requested local database."""
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
    """Return the closest useful label edge for a semantic leader."""
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


def make_ship_panel(records: list[FitRecord]) -> Image.Image:
    """Build the shipboard challenge study."""
    art = warm_art(
        crop_to_fill(SHIP_ART, (390, 280), centering=(0.51, 0.49)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Theseus opposes Minos; the king raises the seal-ring as his challenge.",
        58,
        "ship:caption",
        records,
    )
    add_panel_label(panel, records, "PERIBOIA", (12, 202, 116, 240), (118, 146))
    add_panel_label(panel, records, "THESEUS", (136, 30, 240, 68), (224, 150))
    add_panel_label(panel, records, "MINOS · RING", (268, 202, 414, 240), (330, 74))
    return panel


def make_micon_panel(records: list[FitRecord]) -> Image.Image:
    """Build the damaged third-wall painting study."""
    art = warm_art(
        crop_to_fill(MICON_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Age and Micon's omissions made the third-wall narrative hard to read.",
        58,
        "micon:caption",
        records,
    )
    add_panel_label(panel, records, "SURVIVING SCENE", (12, 30, 154, 68), (176, 152))
    add_panel_label(panel, records, "LOST PLASTER", (264, 202, 414, 240), (330, 142))
    return panel


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build a rich subordinate Aegean orientation inset."""
    art = warm_art(
        crop_to_fill(MAP_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    athens = (104, 66)
    crete = (244, 236)
    route = [athens, (148, 104), (178, 150), (218, 190), crete]
    draw.line(route, fill="#f6e2ad", width=6)
    draw.line(route, fill=RULE, width=2)
    for point in (athens, crete):
        draw.ellipse(
            (point[0] - 6, point[1] - 6, point[0] + 6, point[1] + 6),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "The ordeal belongs to the Aegean voyage from Athens toward Crete.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ATHENS", (12, 30, 112, 68), (122, 84))
    add_panel_label(panel, records, "CRETE", (174, 202, 274, 240), (262, 254))
    add_panel_label(panel, records, "AEGEAN CROSSING", (290, 30, 462, 68), (236, 146))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, SHIP_ART, MICON_ART, MAP_ART):
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
            "PASSAGE 1.17.3",
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
            (28, 92, passage_panel.width - 28, 500),
            translation,
            BODY_FONT,
            max_size=17,
            min_size=10,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.09,
        )
    )

    note_rect = (24, 514, 346, 602)
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
            "The reconstruction restores the story Pausanias says Micon's aged and incomplete painting no longer made clear.",
            BODY_FONT,
            max_size=12,
            min_size=9,
            padding=9,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (40, 612, 330, 640),
            "ATHENS · THE THESEUS SANCTUARY",
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
        grain_strength=0.005,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (648, 40, 1150, 98)
    paste_with_shadow(
        page,
        make_label(
            "THE RING AND AMPHITRITE'S CROWN",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=18,
            min_size=10,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("MINOS'S SHIP", (448, 126, 632, 170), (866, 120)),
        ("YOUTHS AT THE RAIL", (1150, 126, 1328, 170), (820, 92)),
        ("THE RECOVERED RING", (448, 438, 682, 482), (804, 388)),
        ("AMPHITRITE'S CROWN", (1084, 374, 1328, 418), (1084, 286)),
        ("THESEUS RISES", (1060, 548, 1276, 592), (890, 382)),
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

    orientation_rect = (700, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "THESEUS RETURNS FROM THE DEEP WITH BOTH TOKENS OF HIS DIVINE DESCENT",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_ship_panel(records), (28, 700))
    paste_with_shadow(page, make_micon_panel(records), (462, 700))
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
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/17/2.png"],
        "evidence_boundary": "The lost composition is reconstructed; no exact arrangement of Micon's wall painting is claimed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fcdef-2b2b-7322-b33f-dd143b7193b9/exec-c1c9892b-8fe4-4276-9b9e-93a1857f84b3.png",
                "description": "Generated reconstruction of Theseus returning beneath Minos's ship with the ring and crown.",
            },
            {
                "path": str(SHIP_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fcdef-2b2b-7322-b33f-dd143b7193b9/exec-74c2c336-6a18-446e-83a3-43ef4b354aa9.png",
                "description": "Generated content-suitable reconstruction of Minos's shipboard challenge.",
            },
            {
                "path": str(MICON_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fcdef-2b2b-7322-b33f-dd143b7193b9/exec-54a65bdb-73d9-4e98-b262-47ca246c6668.png",
                "description": "Generated archaeological study of Micon's damaged and incomplete wall painting.",
            },
            {
                "path": str(MAP_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fcdef-2b2b-7322-b33f-dd143b7193b9/exec-0c828afe-12c9-4e85-93fe-bb09d2608d36.png",
                "description": "Generated textured Aegean relief base used only as a subordinate orientation inset.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_17_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/17/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
