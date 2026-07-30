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


PASSAGE_ID = "1.16.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_16_1"
MAIN_ART = ASSET_DIR / "main_stoa_statues.png"
PELLA_ART = ASSET_DIR / "pella_omen.png"
ATLAS_ART = ASSET_DIR / "hellenistic_atlas.png"
VICTORY_ART = ASSET_DIR / "victory_captivity.png"


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
    """Return the closest useful point on a label edge."""
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
    name: str,
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    """Draw one measured label and semantic leader inside an inset panel."""
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
    """Build the subordinate geographic orientation panel."""
    art = warm_art(
        crop_to_fill(ATLAS_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Three theatres of Seleucus's story: Macedonia, Egypt, and Babylon.",
        58,
        "atlas:caption",
        records,
    )
    add_panel_label(
        panel,
        records,
        "PELLA · MACEDONIA",
        (28, 32, 166, 68),
        (82, 82),
        "atlas:pella",
    )
    add_panel_label(
        panel,
        records,
        "EGYPT · PTOLEMY",
        (28, 230, 160, 266),
        (118, 220),
        "atlas:egypt",
    )
    add_panel_label(
        panel,
        records,
        "BABYLON",
        (296, 78, 390, 114),
        (336, 166),
        "atlas:babylon",
    )
    return panel


def make_pella_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Pella sacrifice and omen panel."""
    art = warm_art(
        crop_to_fill(PELLA_ART, (390, 280), centering=(0.55, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "At Pella, the altar wood moved toward Zeus and caught fire without a flame.",
        58,
        "pella:caption",
        records,
    )
    add_panel_label(
        panel,
        records,
        "SELEUCUS",
        (26, 44, 118, 80),
        (138, 148),
        "pella:seleucus",
    )
    add_panel_label(
        panel,
        records,
        "SELF-KINDLING ALTAR",
        (214, 226, 390, 264),
        (286, 184),
        "pella:altar",
    )
    return panel


def make_victory_panel(records: list[FitRecord]) -> Image.Image:
    """Build the victory and later captivity panel."""
    art = warm_art(
        crop_to_fill(VICTORY_ART, (438, 280), centering=(0.51, 0.52)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Seleucus defeated Antigonus and later captured Demetrius.",
        58,
        "victory:caption",
        records,
    )
    add_panel_label(
        panel,
        records,
        "SELEUCUS",
        (28, 226, 126, 264),
        (145, 178),
        "victory:seleucus",
    )
    add_panel_label(
        panel,
        records,
        "DEMETRIUS CAPTURED",
        (252, 38, 440, 76),
        (346, 164),
        "victory:demetrius",
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, PELLA_ART, ATLAS_ART, VICTORY_ART):
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
            "PASSAGE 1.16.1",
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
            (28, 92, passage_panel.width - 28, 472),
            translation,
            BODY_FONT,
            max_size=17,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 490, 346, 596)
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
            "From an omen before Alexander's expedition to exile, return, victory, and captivity, Pausanias compresses a dynastic career into one statue.",
            BODY_FONT,
            max_size=14,
            min_size=9,
            padding=11,
            name="passage:career-note",
            align="center",
            spacing_ratio=0.10,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (42, 610, 328, 640),
            "ATHENS · BEFORE THE PAINTED STOA",
            TITLE_FONT,
            max_size=10,
            min_size=7,
            padding=3,
            name="passage:location",
            align="center",
            spacing_ratio=0.04,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.51)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (616, 40, 1168, 98)
    paste_with_shadow(
        page,
        make_label(
            "SOLON AND SELEUCUS BEFORE THE STOA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=17,
            min_size=10,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("SOLON · LAWGIVER", (430, 128, 622, 170), (612, 320)),
        ("SELEUCUS · KING", (1090, 126, 1328, 168), (1086, 310)),
        ("THE PAINTED STOA", (742, 550, 1000, 594), (910, 424)),
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

    orientation_rect = (820, 614, 1348, 654)
    paste_with_shadow(
        page,
        make_label(
            "ATHENS · BRONZE HONORIFIC STATUES IN THE AGORA",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_atlas_panel(records), (28, 700))
    paste_with_shadow(page, make_pella_panel(records), (462, 700))
    paste_with_shadow(page, make_victory_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/15/4.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb42f-cbcb-70a3-8daa-bf8eaec9d9fb/call_ktWNWx1fdRBCxFUEpEJMhKoV.png",
                "description": "Generated reconstruction of the Solon and Seleucus statues before the Painted Stoa.",
            },
            {
                "path": str(PELLA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb42f-cbcb-70a3-8daa-bf8eaec9d9fb/call_TivsEIEvNx9HIjiRowLmNXB0.png",
                "description": "Generated sacrifice and self-kindling altar omen at Pella.",
            },
            {
                "path": str(ATLAS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb42f-cbcb-70a3-8daa-bf8eaec9d9fb/call_rNL9hv1QbwGB2MHbNsV7O3S1.png",
                "description": "Generated eastern Mediterranean and Mesopotamian relief atlas.",
            },
            {
                "path": str(VICTORY_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb42f-cbcb-70a3-8daa-bf8eaec9d9fb/call_BTfw0jdt7zsGwaUnD4F9nz3e.png",
                "description": "Generated Seleucus victory and Demetrius captivity tableau.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_16_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/16/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
