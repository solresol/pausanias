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


PASSAGE_ID = "1.17.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_17_1"
MAIN_ART = ASSET_DIR / "main_agora.png"
RELIEF_ART = ASSET_DIR / "athens_relief.png"
MERCY_ART = ASSET_DIR / "mercy_encounter.png"
ALTARS_ART = ASSET_DIR / "civic_altars.png"


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


def make_relief_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Athens and Saronic Gulf orientation inset."""
    art = warm_art(
        crop_to_fill(RELIEF_ART, (390, 280), centering=(0.50, 0.52)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "The Agora lay below the Acropolis, within the road network of Athens.",
        58,
        "relief:caption",
        records,
    )
    add_panel_label(panel, records, "SARONIC GULF", (12, 26, 130, 62), (88, 88))
    add_panel_label(panel, records, "ACROPOLIS", (256, 50, 378, 86), (300, 152))
    add_panel_label(panel, records, "ATHENIAN AGORA", (150, 204, 294, 242), (222, 184))
    return panel


def make_mercy_panel(records: list[FitRecord]) -> Image.Image:
    """Build the human encounter at the altar of Mercy."""
    art = warm_art(
        crop_to_fill(MERCY_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Mercy becomes civic practice when fortune turns against a family.",
        58,
        "mercy:caption",
        records,
    )
    add_panel_label(panel, records, "SUPPLIANTS", (12, 204, 126, 242), (108, 160))
    add_panel_label(panel, records, "CIVIC PROTECTION", (236, 36, 378, 74), (280, 142))
    return panel


def make_altars_panel(records: list[FitRecord]) -> Image.Image:
    """Build the associated civic-cult altar panel."""
    art = warm_art(
        crop_to_fill(ALTARS_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Pausanias also names Athenian altars of Shame, Rumor, and Impulse.",
        58,
        "altars:caption",
        records,
    )
    add_panel_label(panel, records, "SHAME", (10, 202, 112, 240), (88, 174))
    add_panel_label(panel, records, "RUMOR", (166, 36, 270, 74), (220, 158))
    add_panel_label(panel, records, "IMPULSE", (326, 202, 428, 240), (350, 174))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, RELIEF_ART, MERCY_ART, ALTARS_ART):
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
            "PASSAGE 1.17.1",
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
            (28, 92, passage_panel.width - 28, 458),
            translation,
            BODY_FONT,
            max_size=17,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 474, 346, 602)
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
            "Pausanias places Mercy in an Athenian marketplace; the altar's exact archaeological location remains uncertain.",
            BODY_FONT,
            max_size=13,
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
            (40, 612, 330, 640),
            "ATHENS · SECOND CENTURY CE",
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

    heading_rect = (626, 40, 1192, 98)
    paste_with_shadow(
        page,
        make_label(
            "MERCY IN THE ATHENIAN AGORA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=17,
            min_size=10,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("THE ACROPOLIS", (1112, 124, 1328, 168), (1000, 194)),
        ("ATHENIAN AGORA", (448, 248, 630, 292), (710, 338)),
        ("ALTAR OF MERCY", (1084, 470, 1328, 514), (992, 484)),
        ("SUPPLIANTS", (510, 506, 672, 550), (784, 480)),
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

    orientation_rect = (716, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "A CIVIC ALTAR FOR HUMAN LIFE AND THE REVERSALS OF FORTUNE",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_relief_panel(records), (28, 700))
    paste_with_shadow(page, make_mercy_panel(records), (462, 700))
    paste_with_shadow(page, make_altars_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/16/3.png"],
        "evidence_boundary": "The exact archaeological location of Pausanias's altar is not claimed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc3a3-a7d9-7ff2-affd-15c38b522ad4/exec-f448003e-249a-4e70-b625-3d50e13f97af.png",
                "description": "Generated reconstruction of mercy enacted at an altar in the Roman-era Athenian Agora.",
            },
            {
                "path": str(RELIEF_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc3a3-a7d9-7ff2-affd-15c38b522ad4/exec-3ef3643e-6d4b-4184-97f6-d718db8b16fe.png",
                "description": "Generated aerial relief reconstruction orienting the Agora, Acropolis, Athens, and Saronic Gulf.",
            },
            {
                "path": str(MERCY_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc3a3-a7d9-7ff2-affd-15c38b522ad4/exec-e032d3d6-0e72-4417-af20-092999abe37c.png",
                "description": "Generated close encounter between supplicants and a civic protector at an altar.",
            },
            {
                "path": str(ALTARS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fc3a3-a7d9-7ff2-affd-15c38b522ad4/exec-b093b871-471c-4105-92c7-08343846dce6.png",
                "description": "Generated scene of three associated civic altars in an Agora colonnade.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_17_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/17/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
