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


PASSAGE_ID = "1.21.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_21_1"
MAIN_ART = ASSET_DIR / "main_theatre_poets.png"
DREAM_ART = ASSET_DIR / "spartan_dream.png"
FUNERAL_ART = ASSET_DIR / "sophocles_funeral.png"
RELIEF_ART = root_dir() / "graphic_book/assets/generated/1_14_4/southern_greece_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return row[0]


def leader_endpoint(rect: tuple[int, int, int, int], point: tuple[int, int]) -> tuple[int, int]:
    if rect[0] <= point[0] <= rect[2]:
        return (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)


def add_page_label(
    page: Image.Image,
    draw: ImageDraw.ImageDraw,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    draw_leader(draw, point, leader_endpoint(rect, point))
    paste_with_shadow(
        page,
        make_label(text, rect, records, font_path=TITLE_FONT, max_size=max_size, min_size=min_size),
        rect[:2],
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
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    panel.alpha_composite(
        make_label(text, rect, records, font_path=TITLE_FONT, max_size=max_size, min_size=min_size),
        rect[:2],
    )


def make_orientation_strip(records: list[FitRecord]) -> Image.Image:
    relief = warm_art(
        crop_to_fill(RELIEF_ART, (326, 96), centering=(0.67, 0.56)),
        grain_strength=0.003,
    ).convert("RGBA")
    strip = framed_panel((338, 108))
    strip.paste(relief, (6, 6))
    draw = ImageDraw.Draw(strip)
    athens = (232, 56)
    draw.ellipse((athens[0] - 6, athens[1] - 6, athens[0] + 6, athens[1] + 6), fill="#76502c", outline="#f4deb0", width=2)
    athens_rect = (224, 14, 324, 44)
    slope_rect = (24, 66, 224, 96)
    strip.alpha_composite(
        make_label("ATHENS", athens_rect, records, font_path=TITLE_FONT, max_size=7, min_size=6),
        athens_rect[:2],
    )
    draw_leader(draw, athens, (224, 81))
    strip.alpha_composite(
        make_label("SOUTH SLOPE THEATRE", slope_rect, records, font_path=TITLE_FONT, max_size=7, min_size=6),
        slope_rect[:2],
    )
    return strip


def make_dream_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(DREAM_ART, (634, 280), centering=(0.50, 0.51)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "A Spartan commander dreamed that Dionysus ordered honours for the newly dead ‘Siren.’",
        58,
        "dream:caption",
        records,
    )
    add_panel_label(panel, records, "DIONYSUS", (18, 20, 158, 64), (238, 126), max_size=9)
    add_panel_label(panel, records, "DREAMING COMMANDER", (402, 20, 616, 64), (490, 178), max_size=8)
    add_panel_label(panel, records, "THEATRE MASK", (230, 190, 394, 234), (398, 174), max_size=8)
    add_panel_label(panel, records, "ATTICA CAMP", (18, 190, 158, 234), (108, 166), max_size=8)
    return panel


def make_funeral_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(FUNERAL_ART, (634, 280), centering=(0.50, 0.52)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "The dream was understood as Sophocles: poetry's charm was likened to a Siren.",
        58,
        "funeral:caption",
        records,
    )
    add_panel_label(panel, records, "FUNERAL HONOURS", (18, 20, 190, 64), (294, 140), max_size=8)
    add_panel_label(panel, records, "COVERED BIER", (422, 20, 616, 64), (418, 132), max_size=8)
    add_panel_label(panel, records, "LAUREL", (18, 190, 130, 234), (132, 154), max_size=8)
    add_panel_label(panel, records, "MASK AND LYRE", (414, 190, 616, 234), (340, 154), max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, DREAM_ART, FUNERAL_ART, RELIEF_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(
        passage_draw, title_rect, "PASSAGE 1.21.1", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 88, passage_panel.width - 28, 416), translation, BODY_FONT,
        max_size=18, min_size=11, padding=5, name="passage:translation", spacing_ratio=0.065,
    ))
    note_rect = (24, 426, 354, 524)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Pausanias supplies the theatre statues, named poets, invasion, dream, Dionysian command, funeral honours, and ‘new Siren’ metaphor; setting, statue order, gestures, objects, and procession are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=8, name="passage:evidence-note", align="center", spacing_ratio=0.06,
    ))
    passage_panel.alpha_composite(make_orientation_strip(records), (20, 534))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (690, 40, 1110, 98)
    paste_with_shadow(page, make_label(
        "THEATRE OF DIONYSUS · POETS IN STONE",
        heading_rect, records, font_path=TITLE_FONT, max_size=14, min_size=9,
    ), heading_rect[:2])

    callouts = [
        ("ACROPOLIS", (1168, 86, 1328, 134), (1048, 144), 9),
        ("THEATRE OF DIONYSUS", (916, 176, 1180, 224), (900, 312), 8),
        ("STAGE BUILDING", (1122, 306, 1328, 354), (1052, 362), 8),
        ("ORCHESTRA", (902, 508, 1054, 556), (880, 438), 9),
        ("MENANDER", (438, 564, 588, 612), (570, 480), 9),
        ("EURIPIDES", (676, 584, 836, 632), (846, 490), 9),
        ("SOPHOCLES", (1150, 574, 1318, 622), (1220, 486), 9),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    chronology_rect = (576, 620, 1126, 658)
    paste_with_shadow(page, make_label(
        "THEATRE · SOPHOCLES DIES · SPARTAN DREAM · FUNERAL HONOURS",
        chronology_rect, records, font_path=BODY_FONT, max_size=9, min_size=7,
    ), chronology_rect[:2])

    paste_with_shadow(page, make_dream_panel(records), (28, 700))
    paste_with_shadow(page, make_funeral_panel(records), (718, 700))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "translation_font_size": next(record.font_size for record in records if record.name == "passage:translation"),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/20/7.png"],
        "evidence_boundary": "Pausanias supplies the theatre statues, named poets, invasion, dream, Dionysian instruction, funeral honours, and new-Siren metaphor. Statue placement, theatre activity, camp setting, gestures, objects, clothing, funeral route, and dream appearance are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated Roman-period reconstruction of the Theatre of Dionysus and its poet-statue display."},
            {"path": str(DREAM_ART), "description": "Generated dream scene with the Spartan commander, fully robed Dionysus, laurel, and theatre mask."},
            {"path": str(FUNERAL_ART), "description": "Generated and twice edited non-graphic funeral honours for Sophocles, with pseudo-text removed."},
            {"path": str(RELIEF_ART), "description": "Existing generated southern-Greece relief reused as a subordinate Athens orientation strip."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_21_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/21/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
