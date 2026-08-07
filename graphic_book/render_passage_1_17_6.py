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


PASSAGE_ID = "1.17.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_17_6"
MAIN_ART = ASSET_DIR / "main_scyros.png"
VOYAGE_ART = ASSET_DIR / "storm_voyage.png"
CIMON_ART = ASSET_DIR / "cimon_recovery.png"
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


def make_voyage_panel(records: list[FitRecord]) -> Image.Image:
    """Build the storm-diversion scenic inset."""
    art = warm_art(
        crop_to_fill(VOYAGE_ART, (390, 280), centering=(0.53, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Winds drove Theseus away from Crete and toward the steep island of Scyros.",
        58,
        "voyage:caption",
        records,
    )
    add_panel_label(panel, records, "THESEUS' SHIP", (12, 202, 180, 240), (210, 196))
    add_panel_label(panel, records, "SCYROS", (292, 30, 414, 68), (336, 114))
    return panel


def make_cimon_panel(records: list[FitRecord]) -> Image.Image:
    """Build the recovery-and-return narrative inset."""
    art = warm_art(
        crop_to_fill(CIMON_ART, (390, 280), centering=(0.50, 0.54)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "After Marathon, Cimon conquered Scyros, avenged Theseus, and carried his remains home.",
        58,
        "cimon:caption",
        records,
    )
    add_panel_label(panel, records, "CIMON", (12, 30, 124, 68), (82, 120))
    add_panel_label(panel, records, "CLOSED RELIQUARY", (210, 202, 414, 240), (244, 178))
    return panel


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build a rich but subordinate Aegean orientation inset."""
    art = warm_art(
        crop_to_fill(MAP_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    athens = (110, 82)
    euboea = (195, 72)
    scyros = (314, 66)
    crete = (220, 236)
    marathon = (134, 72)
    intended = [athens, (150, 132), (188, 186), crete]
    diversion = [(150, 132), (218, 114), (272, 88), scyros]
    draw.line(intended, fill="#f6e2ad", width=7)
    draw.line(intended, fill=RULE, width=2)
    draw.line(diversion, fill="#f3c66d", width=7)
    draw.line(diversion, fill="#7b493a", width=2)
    for point in (athens, euboea, scyros, crete, marathon):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "The intended route led to Crete; the storm diversion ended on Scyros east of Euboea.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ATHENS", (12, 30, 116, 68), (128, 100))
    add_panel_label(panel, records, "EUBOEA", (134, 30, 246, 68), (213, 90))
    add_panel_label(panel, records, "SCYROS", (342, 30, 462, 68), (332, 84))
    add_panel_label(panel, records, "CRETE", (164, 202, 270, 240), (238, 246))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, VOYAGE_ART, CIMON_ART, MAP_ART):
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
            "PASSAGE 1.17.6",
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
            (28, 92, passage_panel.width - 28, 470),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 486, 346, 586)
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
            "Pausanias gives the political sequence and locations, but not the precise cliff, route, tomb form, or manner of Lycomedes' plot shown in this reconstruction.",
            BODY_FONT,
            max_size=11,
            min_size=8,
            padding=9,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (38, 604, 332, 640),
            "ATHENS · CRETE · SCYROS",
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

    heading_rect = (704, 40, 1088, 98)
    paste_with_shadow(
        page,
        make_label(
            "THESEUS ON SCYROS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=20,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("SCYROS HARBOUR", (438, 480, 648, 524), (606, 438)),
        ("THESEUS", (600, 126, 738, 170), (836, 398)),
        ("LYCOMEDES", (1044, 126, 1216, 170), (980, 386)),
        ("CLIFF PATH", (1128, 478, 1288, 522), (1202, 456)),
        ("LYCOMEDES' PLOT", (804, 554, 1058, 598), (1095, 300)),
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
            "HOSPITALITY ON THE ISLAND MASKS LYCOMEDES' PLOT AGAINST THESEUS",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_voyage_panel(records), (28, 700))
    paste_with_shadow(page, make_cimon_panel(records), (462, 700))
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
        "continuity_reference_pages": ["graphic_book/images/1/17/5.png"],
        "evidence_boundary": "The cliff, route, tomb form, garments, ships, and precise mechanics of the plot are reconstructed; no eyewitness or surveyed plan is claimed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fdd62-fea4-7523-87dc-5059e4236f78/exec-1a5c1c0a-b91f-47d8-ae16-91623e1de037.png",
                "description": "Generated reconstruction of Theseus and Lycomedes on the cliffs of Scyros.",
            },
            {
                "path": str(VOYAGE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fdd62-fea4-7523-87dc-5059e4236f78/exec-c2285318-e7b0-4bd7-8d52-39dfdb5cc413.png",
                "description": "Generated Bronze Age voyage scene showing the storm diversion toward Scyros.",
            },
            {
                "path": str(CIMON_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fdd62-fea4-7523-87dc-5059e4236f78/exec-b6fb26b1-9064-4687-8e53-7e264ab2156f.png",
                "description": "Generated respectful reconstruction of Cimon recovering the closed remains container.",
            },
            {
                "path": str(MAP_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fdd62-fea4-7523-87dc-5059e4236f78/exec-a797b246-84ed-4f6b-bf0f-6c67c6aadb8e.png",
                "description": "Generated textured Aegean relief base used only as a subordinate orientation inset.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_17_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/17/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
