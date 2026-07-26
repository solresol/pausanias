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
    DISPLAY_FONT,
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


PASSAGE_ID = "1.15.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_15_1"
MAIN_ART = ASSET_DIR / "main_agora.png"
LOCATOR_ART = ASSET_DIR / "argive_locator.png"
BATTLE_ART = ASSET_DIR / "oinoe_battle.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_battle_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(BATTLE_ART, (514, 278), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Oinoe: Pausanias notices the instant before collision—two disciplined lines still advancing.",
        90,
        "battle:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("ATHENIANS", (24, 24, 150, 64), (176, 166)),
        ("OPEN GROUND", (196, 226, 338, 266), (270, 188)),
        ("LACEDAEMONIANS", (330, 24, 526, 64), (398, 166)),
    ]
    for text, rect, point in labels:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        panel.alpha_composite(
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
    return panel


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((474, 410))
    draw = ImageDraw.Draw(panel)
    art = warm_art(
        crop_to_fill(LOCATOR_ART, (438, 278), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel.paste(art, (18, 18))
    draw.rectangle((18, 18, 456, 296), outline=RULE, width=2)

    route_points = [
        (402, 104),
        (302, 168),
        (212, 194),
        (112, 238),
    ]
    draw.line(route_points, fill="#f5e7bd", width=6, joint="curve")
    draw.line(route_points, fill="#7d4c28", width=3, joint="curve")
    for point in route_points:
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#7d4c28",
            outline="#f5e7bd",
            width=2,
        )
    end = route_points[-1]
    draw.polygon(
        [(end[0] - 2, end[1] - 1), (end[0] + 14, end[1] - 9), (end[0] + 8, end[1] + 8)],
        fill="#7d4c28",
        outline="#f5e7bd",
    )

    labels = [
        ("ATHENS", (354, 54, 450, 90), route_points[0]),
        ("ISTHMUS", (258, 124, 354, 160), route_points[1]),
        ("ARGOS", (174, 206, 254, 242), route_points[2]),
        ("OINOE", (30, 224, 120, 260), route_points[3]),
    ]
    for text, rect, point in labels:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        panel.alpha_composite(
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=9,
                min_size=7,
            ),
            rect[:2],
        )

    records.append(
        draw_fitted_text(
            draw,
            (30, 310, panel.width - 30, panel.height - 18),
            "From Athens to Oinoe in Argive territory—not the Attic deme of the same name.",
            BODY_FONT,
            max_size=15,
            min_size=10,
            padding=7,
            name="locator:caption",
            align="center",
            spacing_ratio=0.10,
        )
    )
    return panel


def make_reading_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((296, 410))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 66)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THREE THINGS TO SEE",
            TITLE_FONT,
            max_size=15,
            min_size=9,
            padding=7,
            name="traditions:title",
            align="center",
            spacing_ratio=0.05,
        )
    )

    entries = [
        (
            "MARKET",
            "Hermes Agoraios marks the civic space before the Painted Stoa.",
        ),
        (
            "TROPHY",
            "The gate recalls an Athenian cavalry victory over Pleistarchus.",
        ),
        (
            "PAINTING",
            "The Oinoe scene freezes combat at its opening movement.",
        ),
    ]
    for index, (name, note) in enumerate(entries):
        y0 = 78 + index * 94
        y1 = y0 + 82
        draw.rounded_rectangle(
            (20, y0, 276, y1),
            radius=9,
            fill="#f4dfb2",
            outline="#9c7443",
            width=2,
        )
        records.append(
            draw_fitted_text(
                draw,
                (28, y0 + 7, 104, y1 - 7),
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=8,
                padding=4,
                name=f"traditions:name:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (108, y0 + 7, 268, y1 - 7),
                note,
                BODY_FONT,
                max_size=9,
                min_size=8,
                padding=5,
                name=f"traditions:note:{index}",
                align="center",
                spacing_ratio=0.08,
            )
        )

    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, LOCATOR_ART, BATTLE_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 648))
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
            "PASSAGE 1.15.1",
            TITLE_FONT,
            max_size=28,
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
            (26, 96, passage_panel.width - 26, passage_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.11,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    art = warm_art(
        crop_to_fill(MAIN_ART, (944, 620), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((972, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 958, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (416, 22))

    heading_rect = (650, 42, 1150, 96)
    paste_with_shadow(
        page,
        make_label(
            "THE PAINTED STOA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=19,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("ACROPOLIS", (438, 114, 604, 158), (536, 250)),
        ("HERMES AGORAIOS", (438, 508, 632, 552), (630, 420)),
        ("STOA POIKILE", (1100, 112, 1356, 158), (1050, 286)),
        ("BATTLE PAINTINGS", (1084, 314, 1356, 360), (1010, 376)),
        ("TROPHY GATE", (1090, 570, 1290, 616), (1170, 216)),
    ]
    for text, rect, point in callouts:
        endpoint = (
            rect[0] if point[0] < rect[0] else rect[2],
            (rect[1] + rect[3]) // 2,
        )
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=12,
                min_size=8,
            ),
            rect[:2],
        )

    paste_with_shadow(page, make_battle_panel(records), (28, 692))
    paste_with_shadow(page, make_locator_panel(records), (590, 692))
    paste_with_shadow(page, make_reading_panel(records), (1076, 692))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/14/7.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9f95-ce05-74f3-95f4-e91daff83e84/call_Si7UHVNWxC6XwYYXxlfsM8kG.png",
                "description": "Generated reconstruction of the Athenian Agora, Stoa Poikile, Hermes Agoraios, trophy gate, and Acropolis.",
            },
            {
                "path": str(LOCATOR_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9f95-ce05-74f3-95f4-e91daff83e84/call_mZeO1pMefGsF3hSnX3P9MH3a.png",
                "description": "Generated southern Greece relief atlas used beneath the locally drawn Athens-to-Argive-Oinoe route.",
            },
            {
                "path": str(BATTLE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f9f95-ce05-74f3-95f4-e91daff83e84/call_N6rmtHdDSpb1alLjuC35CbSr.png",
                "description": "Generated Oinoe battle tableau showing the two formations before contact.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_15_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/15/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
