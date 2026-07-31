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


PASSAGE_ID = "1.16.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_16_2"
MAIN_ART = ASSET_DIR / "main_lysimacheia.png"
ATLAS_ART = ASSET_DIR / "route_atlas.png"
GAUL_ART = ASSET_DIR / "ceraunus_gauls.png"
ANTIGONUS_ART = ASSET_DIR / "antigonus_return.png"


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
    """Build the subordinate route and succession atlas."""
    art = warm_art(
        crop_to_fill(ATLAS_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Antiochus received Asia while Seleucus marched west toward Macedonia.",
        58,
        "atlas:caption",
        records,
    )
    add_panel_label(panel, records, "MACEDONIA", (20, 34, 128, 70), (78, 92))
    add_panel_label(panel, records, "LYSIMACHEIA", (118, 88, 244, 124), (136, 148))
    add_panel_label(panel, records, "ASIA · ANTIOCHUS", (238, 214, 390, 252), (300, 180))
    return panel


def make_gaul_panel(records: list[FitRecord]) -> Image.Image:
    """Build the non-graphic Galatian battle panel."""
    art = warm_art(
        crop_to_fill(GAUL_ART, (390, 280), centering=(0.53, 0.51)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Ceraunus resisted the invading Gauls and was killed in battle.",
        58,
        "gauls:caption",
        records,
    )
    add_panel_label(panel, records, "PTOLEMY CERAUNUS", (194, 32, 390, 70), (280, 154))
    add_panel_label(panel, records, "GALATIAN CHARGE", (18, 224, 170, 262), (116, 166))
    return panel


def make_antigonus_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Macedonian restoration panel."""
    art = warm_art(
        crop_to_fill(ANTIGONUS_ART, (438, 280), centering=(0.54, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Antigonus, son of Demetrius, recovered the Macedonian kingdom.",
        58,
        "antigonus:caption",
        records,
    )
    add_panel_label(panel, records, "ANTIGONUS GONATAS", (208, 34, 430, 72), (272, 150))
    add_panel_label(panel, records, "MACEDONIA RESTORED", (20, 224, 210, 262), (150, 182))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, ATLAS_ART, GAUL_ART, ANTIGONUS_ART):
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
            "PASSAGE 1.16.2",
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
            "One murder near Lysimacheia opened a violent struggle for Macedonia: Ceraunus seized it, fell to the Gauls, and Antigonus recovered it.",
            BODY_FONT,
            max_size=13,
            min_size=9,
            padding=10,
            name="passage:succession-note",
            align="center",
            spacing_ratio=0.09,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (40, 612, 330, 640),
            "THRACE · MACEDONIA · 281–279 BCE",
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

    heading_rect = (650, 40, 1160, 98)
    paste_with_shadow(
        page,
        make_label(
            "MURDER ON THE ROAD TO LYSIMACHEIA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=16,
            min_size=10,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("SELEUCUS", (614, 474, 788, 516), (786, 452)),
        ("PTOLEMY CERAUNUS", (1070, 120, 1324, 164), (1085, 350)),
        ("LYSIMACHEIA", (842, 200, 1038, 242), (963, 302)),
        ("THRACIAN CHERSONESE", (1080, 510, 1338, 554), (1135, 238)),
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

    orientation_rect = (742, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "281 BCE · SELEUCUS'S WESTWARD MARCH ENDS AT THE GATEWAY TO MACEDONIA",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_atlas_panel(records), (28, 700))
    paste_with_shadow(page, make_gaul_panel(records), (462, 700))
    paste_with_shadow(page, make_antigonus_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/16/1.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb956-3c14-72d1-921b-5b2a38b0afcc/exec-ad59fd42-6e5e-46ff-957d-a6ef651a3848.png",
                "description": "Generated non-graphic reconstruction of Seleucus's murder near Lysimacheia.",
            },
            {
                "path": str(ATLAS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb956-3c14-72d1-921b-5b2a38b0afcc/exec-a18ec3f6-40e9-4da9-82d4-83a53566c8f9.png",
                "description": "Generated Hellenistic relief atlas and westward route.",
            },
            {
                "path": str(GAUL_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb956-3c14-72d1-921b-5b2a38b0afcc/exec-e3320d1f-29de-4848-b1b4-38a5ea7c42d4.png",
                "description": "Generated non-graphic Ceraunus and Galatian battlefield tableau.",
            },
            {
                "path": str(ANTIGONUS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fb956-3c14-72d1-921b-5b2a38b0afcc/exec-0df3495e-8728-473b-8305-280edcfd47e1.png",
                "description": "Generated reconstruction of Antigonus recovering Macedonia.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_16_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/16/2.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
