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
    PARCHMENT_DEEP,
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    draw_fitted_text,
    draw_leader,
    draw_polyline_leader,
    framed_panel,
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    make_compact_callout,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.13.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_6"
MAIN_ART = ASSET_DIR / "main_sparta_assault.png"
LOCATOR_ART = ASSET_DIR / "laconia_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def draw_map_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    index: int,
) -> None:
    draw = ImageDraw.Draw(panel)
    endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
    if rect[0] <= point[0] <= rect[2]:
        endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
    draw_leader(draw, point, endpoint)
    draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill="#754332")
    draw.rounded_rectangle(rect, radius=6, fill="#f4dfb2", outline="#8d693f", width=1)
    records.append(
        draw_fitted_text(
            draw,
            rect,
            text,
            DISPLAY_FONT,
            max_size=8,
            min_size=6,
            padding=3,
            name=f"locator:label:{index}",
            align="center",
            spacing_ratio=0.04,
        )
    )


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((408, 332))
    draw = ImageDraw.Draw(panel)
    title = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "SPARTA IN THE EUROTAS VALLEY",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    rect = (22, 70, panel.width - 22, 236)
    art = warm_art(
        crop_to_fill(LOCATOR_ART, (rect[2] - rect[0], rect[3] - rect[1]), centering=(0.50, 0.52)),
        grain_strength=0.012,
    )
    panel.paste(art, rect[:2])
    draw.rounded_rectangle(rect, radius=12, outline="#8d693f", width=2)

    # Points are measured against the generated oblique Laconia relief crop.
    draw.line((225, 107, 205, 168), fill="#f2e1b8", width=3)
    draw.polygon([(199, 160), (211, 163), (205, 171)], fill="#f2e1b8")
    draw_map_label(panel, records, "TAYGETUS", (28, 87, 110, 110), (120, 139), 0)
    draw_map_label(panel, records, "PARNON", (300, 103, 376, 126), (286, 145), 1)
    draw_map_label(panel, records, "SPARTA", (166, 184, 234, 207), (204, 169), 2)
    draw_map_label(panel, records, "NORTH APPROACH", (170, 76, 286, 99), (225, 110), 3)

    records.append(
        draw_fitted_text(
            draw,
            (24, 248, panel.width - 24, panel.height - 14),
            "Pyrrhus descended into Laconia toward Sparta, set between Taygetus and Parnon beside the Eurotas.",
            BODY_FONT,
            max_size=11,
            min_size=8,
            padding=5,
            name="locator:caption",
            align="center",
            spacing_ratio=0.08,
        )
    )
    return panel


def make_four_shocks_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title = (24, 16, panel.width - 24, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "FOUR HOSTILE SHOCKS",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="shocks:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    entries = [
        ("1", "BOEOTIA", "Leuctra broke the old claim."),
        ("2", "ANTIPATER", "Macedonian pressure followed."),
        ("3", "DEMETRIUS", "Trenches and palisades were built."),
        ("4", "PYRRHUS", "A direct assault almost took Sparta."),
    ]
    for index, (number, heading, note) in enumerate(entries):
        y0 = 72 + index * 59
        y1 = y0 + 49
        draw.ellipse((24, y0 + 5, 62, y0 + 43), fill="#d2ad70", outline="#795331", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (24, y0 + 5, 62, y0 + 43),
                number,
                TITLE_FONT,
                max_size=15,
                min_size=9,
                padding=8,
                name=f"shocks:number:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        draw.rounded_rectangle((72, y0, 428, y1), radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (82, y0 + 3, 182, y1 - 3),
                heading,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=3,
                name=f"shocks:heading:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (190, y0 + 3, 420, y1 - 3),
                note,
                BODY_FONT,
                max_size=9,
                min_size=7,
                padding=3,
                name=f"shocks:note:{index}",
                align="center",
                spacing_ratio=0.05,
            )
        )
    return panel


def make_defensive_inset(records: list[FitRecord]) -> Image.Image:
    crop = warm_art(
        crop_to_fill(
            MAIN_ART,
            (420, 202),
            source_box=(255, 270, 1390, 735),
            centering=(0.50, 0.50),
        ),
        grain_strength=0.014,
    )
    inset = make_inset_panel(
        crop,
        "Trench, palisade, and fortified houses turned Sparta's vulnerable edge into a layered defensive line.",
        92,
        "inset:defences-caption",
        records,
    )
    draw = ImageDraw.Draw(inset)
    labels = [
        ("FORTIFIED HOUSES", (40, 30, 176, 58), (176, 86)),
        ("TIMBER PALISADE", (270, 40, 402, 68), (304, 100)),
        ("DEEP TRENCH", (160, 158, 262, 186), (242, 139)),
    ]
    for index, (text, rect, point) in enumerate(labels):
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        label = make_label(text, rect, records, font_path=BODY_FONT, max_size=8, min_size=6)
        inset.alpha_composite(label, rect[:2])
    return inset


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, LOCATOR_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    main_rect = (430, 36, 1374, 628)
    art = warm_art(
        crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50)),
        grain_strength=0.012,
    )
    main_panel = framed_panel((art.width + 28, art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + art.width, 14 + art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left = framed_panel((378, 706))
    left_draw = ImageDraw.Draw(left)
    title_band = (18, 14, left.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.13.6",
            TITLE_FONT,
            max_size=29,
            min_size=18,
            padding=10,
            name="panel:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            left_draw,
            (24, 92, left.width - 24, left.height - 24),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left, (32, 36))

    title_rect = (648, 54, 1246, 116)
    paste_with_shadow(
        page,
        make_label("PYRRHUS AT THE EDGE OF SPARTA", title_rect, records, font_path=TITLE_FONT, max_size=20, min_size=10),
        title_rect[:2],
    )
    labels = [
        ("TAYGETUS", (470, 150, 598, 194), (548, 224)),
        ("SPARTA", (1066, 230, 1176, 274), (1024, 330)),
        ("DEFENSIVE LINE", (708, 338, 884, 382), (828, 410)),
        ("EPIROTE ASSAULT", (1064, 490, 1260, 534), (1052, 550)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=11, min_size=7),
            rect[:2],
        )

    note1 = make_compact_callout(
        "Pyrrhus gained the upper hand and nearly forced a direct entry into Sparta.",
        (440, 86),
        "callout:assault",
        records,
        max_size=13,
    )
    draw_polyline_leader(draw, [(448, 652), (574, 588), (700, 478)])
    paste_with_shadow(page, note1, (448, 642))
    note2 = make_compact_callout(
        "Works raised against Demetrius gave the defenders time to prepare for siege.",
        (448, 86),
        "callout:works",
        records,
        max_size=13,
    )
    draw_polyline_leader(draw, [(904, 652), (1010, 576), (934, 411)])
    paste_with_shadow(page, note2, (904, 642))

    paste_with_shadow(page, make_locator_panel(records), (32, 780))
    paste_with_shadow(page, make_defensive_inset(records), (440, 780))
    paste_with_shadow(page, make_four_shocks_panel(records), (904, 780))
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
        "continuity_reference_pages": ["graphic_book/images/1/13/5.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f66f0-2663-7130-8cb6-d1790d93ca52/exec-3a9c13c0-839e-4915-af13-b387b4df892d.png",
                "description": "Generated raster reconstruction of Pyrrhus's assault on Sparta.",
            },
            {
                "path": str(LOCATOR_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f66f0-2663-7130-8cb6-d1790d93ca52/exec-08cbe8fb-378e-4901-a58c-20b4213685ea.png",
                "description": "Generated raster relief base for Laconia and the Eurotas valley.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_13_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/13/6.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
