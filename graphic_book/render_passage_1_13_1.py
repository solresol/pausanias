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


PASSAGE_ID = "1.13.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_1"
MAIN_ART = ASSET_DIR / "main_night_crossing_ceraunia.png"
COUNCIL_ART = ASSET_DIR / "council_deception_inset.png"
LOCATOR_ART = ASSET_DIR / "adriatic_locator_base.png"


def load_translation() -> str:
    db_path = root_dir() / "pausanias.sqlite"
    if not db_path.exists():
        raise RuntimeError(f"Missing local SQLite database: {db_path}")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((392, 332))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THE NIGHT CROSSING",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 70, panel.width - 22, 236)
    art = crop_to_fill(LOCATOR_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.50, 0.52))
    art = warm_art(art, grain_strength=0.012)
    panel.paste(art, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=12, outline="#8d693f", width=2)

    tarentum = (map_rect[0] + 96, map_rect[1] + 106)
    ceraunia = (map_rect[0] + 272, map_rect[1] + 95)
    route = [tarentum, (map_rect[0] + 173, map_rect[1] + 82), ceraunia]
    draw.line(route, fill="#f5ead2", width=7)
    draw.line(route, fill="#7c4033", width=3)
    for x, y in (tarentum, ceraunia):
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#713e2e", outline="#f7e8bf", width=2)

    labels = [
        ("TARENTUM", (38, 174, 138, 200), "locator:tarentum"),
        ("ADRIATIC", (145, 114, 244, 140), "locator:adriatic"),
        ("CERAUNIAN MTS.", (236, 158, 370, 188), "locator:ceraunia"),
    ]
    for text, rect, name in labels:
        draw.rounded_rectangle(rect, radius=7, fill="#f4dfb2", outline="#9c7443", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=3,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    records.append(
        draw_fitted_text(
            draw,
            (24, 248, panel.width - 24, panel.height - 14),
            "Roman hesitation bought one night: Pyrrhus crossed from Tarentum to the mountain refuge of Ceraunia.",
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="locator:caption",
            align="center",
            spacing_ratio=0.1,
        )
    )
    return panel


def make_strategy_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title_rect = (24, 16, panel.width - 24, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "A RETREAT BUILT ON RUMOUR",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="strategy:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("DEFEAT", "The surviving fleet returns from Sicily to Tarentum."),
        ("LETTERS", "Pyrrhus asks Asian kings and Antigonus for men and money."),
        ("RUMOUR", "He suppresses their replies and announces imminent support."),
        ("ESCAPE", "Rome pauses; Pyrrhus crosses by night to Ceraunia."),
    ]
    y = 74
    for index, (heading, note) in enumerate(rows):
        row_rect = (24, y, panel.width - 24, y + 54)
        draw.rounded_rectangle(
            row_rect,
            radius=9,
            fill="#f3dfb4" if index % 2 == 0 else "#f7e8c8",
            outline="#b8945a",
            width=1,
        )
        records.append(
            draw_fitted_text(
                draw,
                (34, y + 7, 142, y + 47),
                heading,
                DISPLAY_FONT,
                max_size=10,
                min_size=6,
                padding=2,
                name=f"strategy:heading:{index}",
                align="center",
                spacing_ratio=0.05,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (154, y + 5, panel.width - 34, y + 49),
                note,
                BODY_FONT,
                max_size=12,
                min_size=8,
                padding=2,
                name=f"strategy:note:{index}",
                spacing_ratio=0.08,
            )
        )
        y += 60
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, COUNCIL_ART, LOCATOR_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art, grain_strength=0.012)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_rect = (32, 36, 410, 742)
    left_panel = framed_panel((left_rect[2] - left_rect[0], left_rect[3] - left_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.13.1",
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
            (24, 92, left_panel.width - 24, left_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_rect[0], left_rect[1]))

    title_rect = (626, 54, 1272, 116)
    paste_with_shadow(
        page,
        make_label("THE RUMOUR AND THE NIGHT CROSSING", title_rect, records, font_path=TITLE_FONT, max_size=19, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    labels = [
        ("PYRRHUS", (486, 262, 620, 306), (576, 414), 13),
        ("TARENTUM", (678, 178, 824, 222), (746, 333), 13),
        ("CERAUNIAN MOUNTAINS", (1032, 154, 1306, 202), (1162, 284), 12),
        ("SECRET LANDING", (1058, 488, 1272, 534), (1166, 424), 12),
    ]
    for text, rect, point, max_size in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], rect[1] + (rect[3] - rect[1]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=max_size, min_size=7),
            (rect[0], rect[1]),
        )

    route_note = make_compact_callout(
        "The destination is not merely overseas: the Ceraunian coast offers immediate mountain cover.",
        (440, 86),
        "callout:route",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(448, 652), (592, 600), (816, 438)])
    paste_with_shadow(page, route_note, (448, 642))

    night_note = make_compact_callout(
        "The Romans remain still just long enough for rumour to become escape.",
        (448, 86),
        "callout:night",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(904, 652), (1052, 594), (1166, 424)])
    paste_with_shadow(page, night_note, (904, 642))

    locator = make_locator(records)
    paste_with_shadow(page, locator, (32, 780))

    council_art = crop_to_fill(COUNCIL_ART, (420, 202), centering=(0.48, 0.50))
    council_art = warm_art(council_art, grain_strength=0.014)
    council = make_inset_panel(
        council_art,
        "Pyrrhus reads none of the replies; he announces support and lets the rumour travel to Rome.",
        92,
        "inset:council-caption",
        records,
    )
    paste_with_shadow(page, council, (438, 780))
    council_label = (548, 800, 776, 836)
    draw_leader(draw, (666, 910), (council_label[0], council_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("THE UNREAD REPLIES", council_label, records, font_path=BODY_FONT, max_size=12, min_size=7),
        (council_label[0], council_label[1]),
    )

    strategy = make_strategy_panel(records)
    paste_with_shadow(page, strategy, (904, 780))

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
        "continuity_reference_pages": ["graphic_book/images/1/12/5.png"],
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated main art of the secret Adriatic crossing and Ceraunian landing."},
            {"path": str(COUNCIL_ART), "description": "Generated inset art of Pyrrhus announcing support over unread letters."},
            {"path": str(LOCATOR_ART), "description": "Generated unlabeled relief-map base for the Tarentum-Ceraunia locator."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_13_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book/images/1/13/1.png"
    print(json.dumps(render_page(output_path), indent=2))


if __name__ == "__main__":
    main()
