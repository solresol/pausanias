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


PASSAGE_ID = "1.18.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_1"
MAIN_ART = ASSET_DIR / "main_anakeion.png"
MARRIAGE_ART = ASSET_DIR / "polygnotus_marriage.png"
ARGONAUT_ART = ASSET_DIR / "micon_argonauts.png"
MAP_ART = ASSET_DIR / "athens_relief.png"


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
    """Draw a measured label and semantic leader inside an inset."""
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


def make_marriage_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Polygnotus mural reconstruction inset."""
    art = warm_art(
        crop_to_fill(MARRIAGE_ART, (390, 280), centering=(0.50, 0.52)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Polygnotus painted the marriage of Leucippus' daughters and the Dioscuri's role.",
        58,
        "marriage:caption",
        records,
    )
    add_panel_label(panel, records, "DAUGHTERS OF LEUCIPPUS", (12, 202, 224, 240), (198, 148))
    add_panel_label(panel, records, "THE DIOSCURI", (286, 30, 414, 68), (324, 132))
    return panel


def make_argonaut_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Micon Argonaut mural reconstruction inset."""
    art = warm_art(
        crop_to_fill(ARGONAUT_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Micon's Argonaut expedition gave special prominence to Acastus and his horses.",
        58,
        "argonaut:caption",
        records,
    )
    add_panel_label(panel, records, "ARGO AND ARGONAUTS", (12, 30, 202, 68), (118, 142))
    add_panel_label(panel, records, "ACASTUS & HORSES", (222, 202, 414, 240), (290, 142))
    return panel


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build a rich but subordinate Athens orientation inset."""
    art = warm_art(
        crop_to_fill(MAP_ART, (438, 280), centering=(0.50, 0.52)),
        grain_strength=0.003,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    acropolis = (206, 92)
    north_slope = (205, 148)
    agora = (320, 206)
    route = [agora, (275, 182), (236, 162), north_slope]
    draw.line(route, fill="#f5dfad", width=7)
    draw.line(route, fill=RULE, width=2)
    for point in (acropolis, north_slope, agora):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "The Anakeion's exact site is lost; scholarship places it conjecturally on the Acropolis north slope.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (126, 30, 250, 68), acropolis)
    add_panel_label(panel, records, "AGORA", (350, 202, 462, 240), agora)
    add_panel_label(
        panel,
        records,
        "CONJECTURAL ANAKEION ZONE",
        (12, 202, 242, 240),
        north_slope,
        max_size=8,
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, MARRIAGE_ART, ARGONAUT_ART, MAP_ART):
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
            "PASSAGE 1.18.1",
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
            (28, 96, passage_panel.width - 28, 374),
            translation,
            BODY_FONT,
            max_size=22,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    note_rect = (24, 404, 346, 574)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias names the statues, painters, subjects, and Acastus emphasis. The architecture, mural arrangements, and north-slope position shown here are informed reconstructions; no sanctuary footprint survives securely identified.",
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
            (38, 600, 332, 640),
            "ATHENS · ACROPOLIS NORTH SLOPE",
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
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (706, 40, 1084, 98)
    paste_with_shadow(
        page,
        make_label(
            "INSIDE THE ANAKEION",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=20,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("POLYGNOTUS' MARRIAGE", (432, 126, 654, 170), (598, 290)),
        ("STANDING DIOSCURI", (778, 126, 966, 170), (884, 378)),
        ("MICON'S ARGONAUTS", (1132, 126, 1334, 170), (1192, 300)),
        ("SONS ON HORSEBACK", (472, 500, 680, 544), (738, 410)),
        ("SONS ON HORSEBACK", (1092, 500, 1300, 544), (1058, 410)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (650, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "CULT IMAGES AND LOST PAINTINGS SHARED THE SANCTUARY INTERIOR",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_marriage_panel(records), (28, 700))
    paste_with_shadow(page, make_argonaut_panel(records), (462, 700))
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
            record.font_size for record in records if record.name == "passage:translation"
        ),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/17/6.png"],
        "evidence_boundary": "The sanctuary architecture, mural arrangement, and north-slope zone are reconstructed; the locator does not claim a discovered footprint.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated Anakeion interior reconstruction."},
            {"path": str(MARRIAGE_ART), "description": "Generated reconstruction of Polygnotus' marriage painting."},
            {"path": str(ARGONAUT_ART), "description": "Generated reconstruction of Micon's Argonaut painting."},
            {"path": str(MAP_ART), "description": "Generated textured Athens relief used only as a subordinate locator."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
