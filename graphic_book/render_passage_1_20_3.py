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


PASSAGE_ID = "1.20.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_20_3"
MAIN_ART = ASSET_DIR / "main_theatre_sanctuary.png"
HEPHAESTUS_ART = ASSET_DIR / "hephaestus_return.png"
ARIADNE_ART = ASSET_DIR / "ariadne_naxos.png"


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


def make_hephaestus_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(HEPHAESTUS_ART, (634, 280), centering=(0.50, 0.46)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Dionysus returns trusted Hephaestus to Olympus, where Hera waits bound to the golden throne.",
        58,
        "hephaestus:caption",
        records,
    )
    add_panel_label(panel, records, "DIONYSUS", (20, 24, 158, 68), (174, 120), max_size=9)
    add_panel_label(panel, records, "HEPHAESTUS", (212, 190, 380, 234), (292, 132), max_size=9)
    add_panel_label(panel, records, "HERA", (500, 24, 610, 68), (510, 118), max_size=10)
    return panel


def make_ariadne_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(ARIADNE_ART, (634, 280), centering=(0.50, 0.30)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "On Naxos, Ariadne sleeps as Theseus sails away and Dionysus approaches.",
        58,
        "ariadne:caption",
        records,
    )
    add_panel_label(panel, records, "ARIADNE", (20, 190, 158, 234), (174, 170), max_size=9)
    add_panel_label(panel, records, "THESEUS' SHIP", (208, 24, 398, 68), (284, 98), max_size=8)
    add_panel_label(panel, records, "DIONYSUS", (490, 24, 610, 68), (470, 126), max_size=9)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, HEPHAESTUS_ART, ARIADNE_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(draw_fitted_text(
        passage_draw, title_rect, "PASSAGE 1.20.3", TITLE_FONT,
        max_size=27, min_size=18, padding=10, name="passage:title", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (28, 88, passage_panel.width - 28, 492), translation, BODY_FONT,
        max_size=17, min_size=11, padding=6, name="passage:translation", spacing_ratio=0.07,
    ))
    note_rect = (24, 504, 354, 592)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(draw_fitted_text(
        passage_draw, note_rect,
        "Pausanias also names painted punishments of Pentheus and Lycurgus. Architecture, placement, dress, and viewpoint are reconstructed.",
        BODY_FONT, max_size=11, min_size=8, padding=9, name="passage:evidence-note", align="center", spacing_ratio=0.07,
    ))
    records.append(draw_fitted_text(
        passage_draw, (34, 606, 344, 638), "THEATRE PRECINCT · SOUTH SLOPE", TITLE_FONT,
        max_size=9, min_size=7, padding=4, name="passage:orientation", align="center", spacing_ratio=0.04,
    ))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (688, 40, 1120, 98)
    paste_with_shadow(page, make_label(
        "THE SANCTUARY BESIDE THE THEATRE", heading_rect, records,
        font_path=TITLE_FONT, max_size=16, min_size=10,
    ), heading_rect[:2])

    callouts = [
        ("THEATRE OF DIONYSUS", (442, 120, 676, 166), (492, 408), 9),
        ("PAINTED STOA", (442, 522, 620, 568), (594, 424), 9),
        ("DIONYSUS ELEUTHEREUS", (670, 150, 918, 196), (826, 348), 8),
        ("ALCAMENES' IVORY-AND-GOLD IMAGE", (1038, 150, 1334, 204), (1132, 370), 8),
        ("SANCTUARY ENCLOSURE", (1080, 520, 1338, 566), (1290, 448), 9),
        ("ACROPOLIS", (650, 570, 796, 614), (730, 96), 10),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    route_rect = (808, 594, 1340, 644)
    route = make_label(
        "THEATRE OF DIONYSUS · SOUTH SLOPE · ACROPOLIS",
        route_rect, records, font_path=BODY_FONT, max_size=10, min_size=8,
    )
    paste_with_shadow(page, route, route_rect[:2])

    paste_with_shadow(page, make_hephaestus_panel(records), (28, 700))
    paste_with_shadow(page, make_ariadne_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/20/2.png"],
        "evidence_boundary": "Pausanias supplies the sanctuary beside the theatre, two temples and two images, Alcamenes and the ivory-and-gold material, and the subjects of the paintings; architecture, placement, clothing, processional detail, and viewpoint are reconstructed.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated south-slope reconstruction with theatre, sanctuary enclosure, two temples, two fully draped Dionysus images, and painted stoa."},
            {"path": str(HEPHAESTUS_ART), "description": "Generated fully clothed myth scene of Dionysus returning Hephaestus to Hera's golden throne."},
            {"path": str(ARIADNE_ART), "description": "Generated fully clothed Naxos scene joining sleeping Ariadne, Theseus' departing ship, and Dionysus' arrival."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_20_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/20/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
