#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pausanias_db import connect

from graphic_book.render_passage_1_3_2 import (
    BODY_FONT,
    BRONZE,
    CITY,
    CITY_LIGHT,
    DISPLAY_FONT,
    FitRecord,
    HEIGHT,
    PARCHMENT_DEEP,
    ROAD,
    ROAD_LIGHT,
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    crop_to_fill,
    draw_fitted_text,
    draw_leader,
    draw_polyline_leader,
    framed_panel,
    make_inset_panel,
    make_label,
    make_note_panel,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.3.3"


def load_translation() -> str:
    with connect() as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = %s",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_locator_map(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((396, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "WEST AGORA STOAS",
            TITLE_FONT,
            max_size=24,
            min_size=16,
            padding=8,
            name="map:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 70, panel.width - 22, 240)
    draw.rounded_rectangle(map_rect, radius=16, fill="#efe0ba", outline="#aa8651", width=2)

    road_band = [
        (map_rect[0] + 24, map_rect[1] + 154),
        (map_rect[0] + 96, map_rect[1] + 136),
        (map_rect[0] + 208, map_rect[1] + 118),
        (map_rect[0] + 342, map_rect[1] + 126),
    ]
    draw.line(road_band, fill=ROAD, width=18)
    draw.line(road_band, fill=ROAD_LIGHT, width=5)

    royal_stoa = (map_rect[0] + 164, map_rect[1] + 24, map_rect[0] + 334, map_rect[1] + 60)
    stoa_zeus = (map_rect[0] + 156, map_rect[1] + 84, map_rect[0] + 324, map_rect[1] + 126)
    altar = (map_rect[0] + 170, map_rect[1] + 138, map_rect[0] + 244, map_rect[1] + 178)
    painted_wall = (map_rect[0] + 262, map_rect[1] + 82, map_rect[0] + 306, map_rect[1] + 126)
    acropolis = [(map_rect[0] + 298, map_rect[1] + 36), (map_rect[0] + 334, map_rect[1] + 12), (map_rect[0] + 350, map_rect[1] + 42)]

    draw.rounded_rectangle(royal_stoa, radius=8, fill=CITY, outline=RULE, width=2)
    draw.rounded_rectangle(stoa_zeus, radius=8, fill="#d7bb85", outline=RULE, width=2)
    draw.rounded_rectangle(altar, radius=8, fill="#c39b62", outline=RULE, width=2)
    draw.rounded_rectangle(painted_wall, radius=6, fill="#b98863", outline=RULE, width=2)
    draw.polygon(acropolis, fill="#a77e49", outline=RULE)
    draw.line((acropolis[0][0], acropolis[1][1], acropolis[2][0], acropolis[1][1]), fill="#d8bb86", width=2)

    for x, y in [(174, 98), (196, 98), (218, 98), (240, 98)]:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=BRONZE)
    for x, y in [(188, 154), (204, 154), (220, 154), (236, 154)]:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill="#f0e1bc", outline=RULE)

    label_specs = [
        ("ROYAL STOA", (map_rect[0] + 176, map_rect[1] - 2, map_rect[0] + 332, map_rect[1] + 24), "map:royal"),
        ("STOA OF ZEUS", (map_rect[0] + 164, map_rect[1] + 56, map_rect[0] + 320, map_rect[1] + 82), "map:zeus"),
        ("TWELVE GODS ALTAR", (map_rect[0] + 122, map_rect[1] + 166, map_rect[0] + 286, map_rect[1] + 194), "map:altar"),
        ("PAINTED WALL", (map_rect[0] + 250, map_rect[1] + 128, map_rect[0] + 348, map_rect[1] + 154), "map:wall"),
        ("WEST ROAD", (map_rect[0] + 24, map_rect[1] + 132, map_rect[0] + 126, map_rect[1] + 160), "map:road"),
        ("ACROPOLIS", (map_rect[0] + 252, map_rect[1] + 48, map_rect[0] + 350, map_rect[1] + 76), "map:acropolis"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=8, fill=CITY_LIGHT, outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=14,
                min_size=8,
                padding=4,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption_rect = (18, 258, panel.width - 18, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "Locator map: the Stoa of Zeus stood just behind the Royal Stoa on the west side of the Agora, beside the altar of the Twelve Gods.",
            BODY_FONT,
            max_size=15,
            min_size=11,
            padding=6,
            name="map:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (454, 44, 1372, 690)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_3/main_stoa_zeus_twelve_gods.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.56, 0.48),
    )
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle((13, 13, 13 + main_art.width, 13 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 618)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.3.3",
            TITLE_FONT,
            max_size=31,
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
            (24, 88, left_panel.width - 24, left_panel.height - 22),
            translation,
            BODY_FONT,
            max_size=22,
            min_size=14,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (562, 42, 1242, 118)
    title_panel = make_label(
        "THE STOA OF ZEUS AND THE TWELVE GODS",
        title_rect,
        records,
        font_path=TITLE_FONT,
        max_size=27,
        min_size=15,
    )
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    locator_panel = make_locator_map(records)
    locator_xy = (34, 746)

    gods_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_3/twelve_gods_portico.png",
        (420, 214),
        centering=(0.58, 0.34),
    )
    gods_panel = make_inset_panel(
        gods_art,
        "Inside the stoa a painted cycle of the Twelve Gods made divine order visible beside Athens' civic heart.",
        116,
        "caption:gods",
        records,
    )
    gods_xy = (468, 742)

    trio_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_3/theseus_democracy_demos.png",
        (388, 230),
        centering=(0.5, 0.33),
    )
    trio_panel = make_inset_panel(
        trio_art,
        "Theseus appears beside Democracy and Demos, a public image Pausanias treats as civic myth rather than literal constitutional history.",
        116,
        "caption:trio",
        records,
    )
    trio_xy = (964, 734)

    labels = [
        ("ACROPOLIS", (1022, 86, 1278, 140)),
        ("ROYAL STOA", (596, 228, 846, 282)),
        ("STOA OF ZEUS", (1006, 332, 1280, 386)),
        ("TWELVE GODS ALTAR", (720, 560, 948, 614)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect in labels:
        label = make_label(text, rect, records, max_size=24, min_size=12)
        label_panels.append((label, (rect[0], rect[1])))

    gods_note_panel = make_note_panel(
        "Within the portico Pausanias notes the painted Twelve Gods, giving the stoa both civic and sacred authority.",
        (356, 96),
        "callout:gods-note",
        records,
    )
    gods_note_xy = (968, 172)

    theseus_note_panel = make_note_panel(
        "On the opposite wall Theseus stands with Democracy and Demos; Pausanias rejects the popular claim that Theseus truly founded democratic rule.",
        (360, 114),
        "callout:theseus-note",
        records,
    )
    theseus_note_xy = (948, 486)

    draw = ImageDraw.Draw(page)
    draw_polyline_leader(draw, [(968, 220), (934, 220), (934, 418), (1108, 418)])
    draw_polyline_leader(draw, [(948, 542), (920, 542), (920, 472), (1034, 472)])
    draw_leader(draw, (582, 838), (1088, 420))
    draw_leader(draw, (1082, 734), (1022, 470))

    paste_with_shadow(page, locator_panel, locator_xy)
    paste_with_shadow(page, gods_panel, gods_xy)
    paste_with_shadow(page, trio_panel, trio_xy)
    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, gods_note_panel, gods_note_xy)
    paste_with_shadow(page, theseus_note_panel, theseus_note_xy)

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_3_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "3" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
