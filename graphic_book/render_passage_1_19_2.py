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


PASSAGE_ID = "1.19.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_19_2"
MAIN_ART = ASSET_DIR / "main_gardens.png"
LOCATOR_ART = ASSET_DIR / "locator.png"
HERM_ART = ASSET_DIR / "herm.png"
WORKSHOP_ART = ASSET_DIR / "alcamenes_workshop.png"


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
    """Draw a measured inset label and a leader ending on a named feature."""
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


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    """Build the textured Ilissos-region orientation inset."""
    art = warm_art(
        crop_to_fill(LOCATOR_ART, (390, 280), centering=(0.50, 0.53)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "The Gardens sanctuary is placed conjecturally in the Ilissos landscape beyond the Olympieion.",
        58,
        "locator:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (20, 26, 120, 64), (92, 88), max_size=8)
    add_panel_label(panel, records, "OLYMPIEION", (26, 144, 154, 184), (95, 126), max_size=8)
    add_panel_label(panel, records, "ILISSOS", (138, 210, 224, 248), (202, 188), max_size=8)
    add_panel_label(panel, records, "GARDENS ZONE?", (246, 182, 378, 224), (306, 170), max_size=8)
    return panel


def make_herm_panel(records: list[FitRecord]) -> Image.Image:
    """Build the object-study inset for the square Heavenly Aphrodite."""
    art = warm_art(
        crop_to_fill(HERM_ART, (390, 280), centering=(0.48, 0.52)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "The nearby square image was identified as Heavenly Aphrodite, eldest of the Fates.",
        58,
        "herm:caption",
        records,
    )
    add_panel_label(panel, records, "HEAVENLY APHRODITE", (18, 28, 182, 70), (160, 104), max_size=8)
    add_panel_label(panel, records, "SQUARE FORM", (20, 190, 142, 230), (168, 176), max_size=8)
    add_panel_label(panel, records, "FATE SYMBOLS", (244, 190, 374, 230), (252, 214), max_size=8)
    return panel


def make_workshop_panel(records: list[FitRecord]) -> Image.Image:
    """Build the inset for Alcamenes and his reconstructed statue."""
    art = warm_art(
        crop_to_fill(WORKSHOP_ART, (438, 280), centering=(0.52, 0.50)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Alcamenes' lost masterpiece is shown as a cautious, fully draped workshop reconstruction.",
        58,
        "workshop:caption",
        records,
    )
    add_panel_label(panel, records, "ALCAMENES", (126, 30, 238, 70), (230, 116), max_size=8)
    add_panel_label(panel, records, "DRAPED STATUE", (288, 30, 426, 70), (346, 112), max_size=8)
    add_panel_label(panel, records, "SCULPTOR'S TOOLS", (18, 190, 164, 230), (96, 178), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, LOCATOR_ART, HERM_ART, WORKSHOP_ART):
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
            "PASSAGE 1.19.2",
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
            (28, 92, passage_panel.width - 28, 350),
            translation,
            BODY_FONT,
            max_size=20,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    note_rect = (24, 376, 346, 572)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias records the two images, Alcamenes' authorship, and the statue's exceptional reputation. The Ilissos setting is plausible, but the exact sanctuary, architecture, planting, Herm form, and lost statue pose are reconstructed.",
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
            (36, 604, 334, 640),
            "ATHENS · ILISSOS · THE GARDENS",
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
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.49)),
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (692, 40, 1158, 98)
    paste_with_shadow(
        page,
        make_label(
            "APHRODITE IN THE GARDENS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=21,
            min_size=12,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACROPOLIS", (440, 100, 562, 142), (522, 164)),
        ("OLYMPIEION", (526, 250, 662, 292), (664, 310)),
        ("ILISSOS", (612, 390, 710, 432), (724, 416)),
        ("SQUARE HERM-LIKE IMAGE", (438, 502, 664, 546), (612, 424)),
        ("ALCAMENES' CULT STATUE", (1050, 168, 1308, 212), (1176, 344)),
        ("TEMPLE OF APHRODITE", (1032, 514, 1270, 558), (1260, 290)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (676, 612, 1328, 654)
    paste_with_shadow(
        page,
        make_label(
            "THE GARDENS · TWO DISTINCT IMAGES · EXACT FORMS RECONSTRUCTED",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=10,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_locator_panel(records), (28, 700))
    paste_with_shadow(page, make_herm_panel(records), (462, 700))
    paste_with_shadow(page, make_workshop_panel(records), (896, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/19/1.png"],
        "evidence_boundary": "Recorded objects and authorship are separated from the conjectural Ilissos placement and reconstructed forms.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the Aphrodite sanctuary in the Gardens."},
            {"path": str(LOCATOR_ART), "description": "Generated textured reconstruction of Roman-period southeast Athens and the Ilissos."},
            {"path": str(HERM_ART), "description": "Generated object study of the square Herm-like Heavenly Aphrodite."},
            {"path": str(WORKSHOP_ART), "description": "Generated workshop reconstruction of Alcamenes and the fully draped cult statue."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_19_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/19/2.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
