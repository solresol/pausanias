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


PASSAGE_ID = "1.15.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_15_2"
MAIN_ART = ASSET_DIR / "main_stoa.png"
AMAZON_ART = ASSET_DIR / "amazon_battle.png"
CASSANDRA_ART = ASSET_DIR / "cassandra_council.png"
ROUTE_ART = ASSET_DIR / "eastern_route.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_amazon_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(AMAZON_ART, (504, 278), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "At Athens, Theseus and the Athenians meet the Amazons in ordered battle.",
        88,
        "amazon:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("ATHENIANS", (22, 22, 154, 62), (178, 142)),
        ("THESEUS", (170, 226, 284, 266), (246, 164)),
        ("AMAZONS", (384, 22, 518, 62), (408, 150)),
        ("ATHENS", (260, 22, 360, 62), (300, 95)),
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


def make_cassandra_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(
        crop_to_fill(CASSANDRA_ART, (454, 278), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "After Ilium falls, the kings assemble over Ajax's outrage against Cassandra.",
        88,
        "cassandra:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("CASSANDRA", (18, 224, 152, 264), (116, 136)),
        ("ATHENA", (18, 22, 122, 62), (82, 96)),
        ("THE KINGS", (184, 22, 310, 62), (252, 138)),
        ("AJAX", (366, 224, 470, 264), (374, 142)),
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
    return panel


def make_route_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((300, 402))
    draw = ImageDraw.Draw(panel)
    art = warm_art(
        crop_to_fill(ROUTE_ART, (264, 250), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel.paste(art, (18, 18))
    draw.rectangle((18, 18, 282, 268), outline=RULE, width=2)

    route_points = [(64, 218), (146, 136), (238, 78)]
    draw.line(route_points, fill="#f6e7bd", width=6, joint="curve")
    draw.line(route_points, fill="#7d4c28", width=3, joint="curve")
    for point in route_points:
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#7d4c28",
            outline="#f6e7bd",
            width=2,
        )

    labels = [
        ("ATHENS", (24, 218, 108, 254), route_points[0]),
        ("TROY", (104, 112, 184, 148), route_points[1]),
        ("THEMISCYRA", (178, 48, 278, 86), route_points[2]),
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
                max_size=8,
                min_size=6,
            ),
            rect[:2],
        )

    records.append(
        draw_fitted_text(
            draw,
            (26, 280, panel.width - 26, panel.height - 18),
            "THE AMAZON SEQUENCE\nThemiscyra captured · Athens attacked · Troy defended",
            BODY_FONT,
            max_size=13,
            min_size=9,
            padding=7,
            name="route:caption",
            align="center",
            spacing_ratio=0.10,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, AMAZON_ART, CASSANDRA_ART, ROUTE_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 648))
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
            "PASSAGE 1.15.2",
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
            (26, 94, passage_panel.width - 26, passage_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 620), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    art_panel = framed_panel((968, 648))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 634), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (650, 42, 1160, 98)
    paste_with_shadow(
        page,
        make_label(
            "PAINTINGS IN THE STOA",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=19,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("AMAZONS & ATHENIANS", (432, 116, 666, 160), (760, 316)),
        ("THESEUS", (462, 548, 596, 592), (690, 384)),
        ("THE FALL OF ILIUM", (1110, 116, 1350, 160), (1090, 324)),
        ("CASSANDRA & ATHENA", (1110, 500, 1352, 544), (1160, 348)),
        ("AJAX ACCUSED", (1184, 574, 1348, 618), (1260, 390)),
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
                max_size=11,
                min_size=7,
            ),
            rect[:2],
        )

    paste_with_shadow(page, make_amazon_panel(records), (28, 692))
    paste_with_shadow(page, make_route_panel(records), (580, 692))
    paste_with_shadow(page, make_cassandra_panel(records), (892, 692))

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
        "continuity_reference_pages": ["graphic_book/images/1/15/1.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa4bd-319c-7ee2-96af-363d54ce61b9/call_myHO2GVGKeFtxT3dvkIriZSF.png",
                "description": "Generated reconstruction of the Stoa interior and its adjacent Amazon and Troy paintings.",
            },
            {
                "path": str(AMAZON_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa4bd-319c-7ee2-96af-363d54ce61b9/call_7WTQvp8WlPeu5QFptOq7KMAI.png",
                "description": "Generated Theseus and Amazon battle tableau outside Athens.",
            },
            {
                "path": str(CASSANDRA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa4bd-319c-7ee2-96af-363d54ce61b9/call_sySrN9iDbCaY3Ub62JcvbrjY.png",
                "description": "Generated post-sack council tableau with Cassandra, Athena, Ajax, and the Greek kings.",
            },
            {
                "path": str(ROUTE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fa4bd-319c-7ee2-96af-363d54ce61b9/call_s8GYf0nr1NdLlw1P8DgfR893.png",
                "description": "Generated eastern Mediterranean relief atlas beneath locally rendered route and labels.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_15_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/15/2.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
