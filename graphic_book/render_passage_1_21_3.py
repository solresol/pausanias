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


PASSAGE_ID = "1.21.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_21_3"
MAIN_ART = ASSET_DIR / "main_south_slope.png"
NIOBID_ART = ASSET_DIR / "niobid_cave_art.png"
SIPYLUS_ART = ASSET_DIR / "sipylus_near_far.png"


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


def make_vertical_key(records: list[FitRecord]) -> Image.Image:
    key = framed_panel((338, 108))
    draw = ImageDraw.Draw(key)
    draw.line((34, 78, 304, 28), fill="#795734", width=4)
    points = [(42, 76), (126, 60), (214, 44), (296, 29)]
    for point in points:
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#76502c",
            outline="#f4deb0",
            width=2,
        )
    labels = [
        ("THEATRE", (4, 74, 104, 104)),
        ("CAVE", (92, 58, 166, 88)),
        ("WALL", (168, 40, 246, 70)),
        ("ACROPOLIS", (226, 4, 334, 34)),
    ]
    for text, rect in labels:
        key.alpha_composite(
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=7, min_size=7),
            rect[:2],
        )
    return key


def make_niobid_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(NIOBID_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "Inside the cave, Pausanias saw an image of Apollo and Artemis attacking Niobe's children.",
        58,
        "niobid:caption",
        records,
    )
    add_panel_label(panel, records, "APOLLO", (18, 20, 142, 62), (124, 118), max_size=8)
    add_panel_label(panel, records, "ARTEMIS", (492, 20, 616, 62), (516, 118), max_size=8)
    add_panel_label(panel, records, "NIOBE'S CHILDREN", (210, 194, 424, 238), (318, 142), max_size=8)
    return panel


def make_sipylus_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(SIPYLUS_ART, (634, 280), centering=(0.50, 0.50)), grain_strength=0.004)
    panel = make_inset_panel(
        art,
        "At Mount Sipylus the same formation is mere rock nearby, yet from farther away suggests a bowed, weeping woman.",
        58,
        "sipylus:caption",
        records,
    )
    add_panel_label(panel, records, "NEAR · ROCK AND CLIFF", (18, 20, 220, 62), (188, 138), max_size=8)
    add_panel_label(panel, records, "FAR · BOWED FORM", (402, 20, 616, 62), (490, 112), max_size=8)
    location_rect = (218, 198, 418, 238)
    panel.alpha_composite(
        make_label(
            "LYDIA · MOUNT SIPYLUS",
            location_rect,
            records,
            font_path=TITLE_FONT,
            max_size=7,
            min_size=6,
        ),
        location_rect[:2],
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, NIOBID_ART, SIPYLUS_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.21.3",
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
            (28, 88, passage_panel.width - 28, 402),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=5,
            name="passage:translation",
            spacing_ratio=0.065,
        )
    )
    note_rect = (24, 414, 354, 524)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias supplies the relative positions, monuments, cave image, and near/far observation. Architecture, ornament scale, costumes, lighting, and viewpoints are reconstructed.",
            BODY_FONT,
            max_size=11,
            min_size=8,
            padding=8,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.06,
        )
    )
    passage_panel.alpha_composite(make_vertical_key(records), (20, 534))
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(crop_to_fill(MAIN_ART, (932, 622), centering=(0.50, 0.50)), grain_strength=0.004)
    art_panel = framed_panel((960, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 946, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (414, 22))

    heading_rect = (626, 40, 1162, 98)
    paste_with_shadow(
        page,
        make_label(
            "THE ACROPOLIS SOUTH SLOPE",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=14,
            min_size=9,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("SOUTHERN WALL", (438, 118, 640, 166), (782, 150), 8),
        ("GILDED GORGON · AEGIS", (1088, 174, 1346, 222), (1115, 112), 8),
        ("TRIPOD", (704, 202, 844, 248), (865, 242), 9),
        ("ROCK CAVE", (718, 386, 884, 434), (891, 356), 9),
        ("THEATRE OF DIONYSUS", (1082, 536, 1346, 584), (1188, 500), 8),
    ]
    for text, rect, point, max_size in callouts:
        add_page_label(page, draw, records, text, rect, point, max_size=max_size)

    sequence_rect = (638, 612, 1150, 658)
    paste_with_shadow(
        page,
        make_label(
            "THEATRE · CAVE AND TRIPOD · SOUTHERN WALL · ACROPOLIS",
            sequence_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        sequence_rect[:2],
    )

    paste_with_shadow(page, make_niobid_panel(records), (28, 700))
    paste_with_shadow(page, make_sipylus_panel(records), (718, 700))

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
        "continuity_reference_pages": ["graphic_book/images/1/21/2.png"],
        "evidence_boundary": "Pausanias supplies relative positions, monuments, the cave image subject, and his near/far observation. Exact architecture, scale, decoration technique, clothing, activity, lighting, vegetation, and viewpoints are reconstructed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated south-slope reconstruction with theatre, cave, tripod, Southern Wall, and gilded Gorgon in aegis.",
            },
            {
                "path": str(NIOBID_ART),
                "description": "Generated non-graphic cave artwork with fully clothed Apollo, Artemis, and Niobids.",
            },
            {
                "path": str(SIPYLUS_ART),
                "description": "Generated and revised Mount Sipylus near/far landscape study.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_21_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/21/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
