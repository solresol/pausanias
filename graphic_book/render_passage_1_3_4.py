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
    BRONZE,
    CITY,
    CITY_LIGHT,
    DISPLAY_FONT,
    FitRecord,
    HEIGHT,
    INK,
    PARCHMENT_DEEP,
    ROAD,
    ROAD_LIGHT,
    RULE,
    TITLE_FONT,
    WALL,
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


PASSAGE_ID = "1.3.4"


def load_translation() -> str:
    db_path = root_dir() / "pausanias.sqlite"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_war_context_map(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((396, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "WAR CONTEXT",
            TITLE_FONT,
            max_size=24,
            min_size=16,
            padding=8,
            name="map:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 70, panel.width - 22, 238)
    draw.rounded_rectangle(map_rect, radius=16, fill="#efe0ba", outline="#aa8651", width=2)

    # Stylized mainland Greece and Peloponnese, kept deliberately secondary.
    mainland = [
        (map_rect[0] + 210, map_rect[1] + 12),
        (map_rect[0] + 304, map_rect[1] + 20),
        (map_rect[0] + 328, map_rect[1] + 62),
        (map_rect[0] + 292, map_rect[1] + 104),
        (map_rect[0] + 224, map_rect[1] + 100),
        (map_rect[0] + 184, map_rect[1] + 66),
    ]
    peloponnese = [
        (map_rect[0] + 82, map_rect[1] + 98),
        (map_rect[0] + 160, map_rect[1] + 80),
        (map_rect[0] + 218, map_rect[1] + 118),
        (map_rect[0] + 206, map_rect[1] + 156),
        (map_rect[0] + 146, map_rect[1] + 148),
        (map_rect[0] + 108, map_rect[1] + 166),
        (map_rect[0] + 56, map_rect[1] + 142),
    ]
    euboea = [
        (map_rect[0] + 306, map_rect[1] + 72),
        (map_rect[0] + 342, map_rect[1] + 82),
        (map_rect[0] + 330, map_rect[1] + 142),
        (map_rect[0] + 296, map_rect[1] + 124),
    ]
    for shape in (mainland, peloponnese, euboea):
        draw.polygon(shape, fill="#d2b272", outline=RULE)

    pts = {
        "Athens": (map_rect[0] + 256, map_rect[1] + 110),
        "Leuctra": (map_rect[0] + 236, map_rect[1] + 72),
        "Mantineia": (map_rect[0] + 144, map_rect[1] + 118),
        "Thermopylae": (map_rect[0] + 292, map_rect[1] + 34),
    }
    draw.line([pts["Athens"], pts["Leuctra"], pts["Mantineia"]], fill=ROAD, width=6)
    draw.line([pts["Athens"], pts["Leuctra"], pts["Mantineia"]], fill=ROAD_LIGHT, width=2)
    draw.line([pts["Athens"], pts["Thermopylae"]], fill="#a66f42", width=3)

    for name, (x, y) in pts.items():
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=BRONZE, outline=RULE, width=1)

    label_specs = [
        ("ATHENS", (238, 166, 330, 192), "map:athens"),
        ("LEUCTRA", (198, 112, 300, 138), "map:leuctra"),
        ("MANTINEIA", (78, 174, 194, 200), "map:mantineia"),
        ("THERMOPYLAE", (258, 82, 372, 108), "map:thermopylae"),
        ("BOEOTIA", (206, 140, 292, 164), "map:boeotia"),
        ("ARCADIA", (74, 214, 164, 238), "map:arcadia"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=7, fill=CITY_LIGHT, outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=13,
                min_size=8,
                padding=4,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption_rect = (18, 256, panel.width - 18, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "The Athenian Agora painting remembered a Peloponnesian cavalry fight near Mantineia after Leuctra.",
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


def validate_fit_records(records: list[FitRecord]) -> None:
    for record in records:
        rx0, ry0, rx1, ry1 = record.rect
        bx0, by0, bx1, by1 = record.text_bbox
        if bx0 < rx0 or by0 < ry0 or bx1 > rx1 or by1 > ry1:
            raise RuntimeError(f"{record.name}: measured text bbox escapes target rect")


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (454, 44, 1372, 670)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_4/main_mantineia_cavalry.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.51, 0.52),
    )
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle(
        (13, 13, 13 + main_art.width, 13 + main_art.height),
        outline=RULE,
        width=2,
    )
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 650)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.3.4",
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
            max_size=20,
            min_size=13,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (576, 42, 1208, 118)
    title_panel = make_label(
        "MANTINEIA IN THE ATHENIAN AGORA",
        title_rect,
        records,
        font_path=TITLE_FONT,
        max_size=26,
        min_size=14,
    )
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    labels = [
        ("EUPHRANOR'S PAINTING", (494, 156, 816, 210), (694, 226)),
        ("GRYLUS", (622, 432, 792, 484), (704, 446)),
        ("EPAMINONDAS", (1052, 386, 1288, 438), (1122, 428)),
        ("MANTINEIA", (994, 600, 1190, 652), (930, 560)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int], tuple[int, int]]] = []
    for text, rect, target in labels:
        label = make_label(text, rect, records, max_size=23, min_size=12)
        label_panels.append((label, (rect[0], rect[1]), target))

    war_panel = make_war_context_map(records)
    war_xy = (34, 746)

    apollo_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_4/apollo_patroos_alexikakos.png",
        (420, 214),
        centering=(0.72, 0.74),
    )
    apollo_panel = make_inset_panel(
        apollo_art,
        "Near Euphranor's paintings stood Apollo Patroos and Apollo Alexikakos, credited with turning away the plague.",
        108,
        "caption:apollo",
        records,
    )
    apollo_xy = (468, 734)

    battle_note_panel = make_note_panel(
        "Pausanias reads the Agora wall painting as history: Athenian aid, Theban power, and named commanders held in public memory.",
        (380, 112),
        "callout:battle-memory",
        records,
    )
    battle_note_xy = (940, 724)

    apollo_note_panel = make_note_panel(
        "Patroos means paternal; Alexikakos means averter of evil.",
        (370, 82),
        "callout:apollo-names",
        records,
    )
    apollo_note_xy = (952, 900)

    draw = ImageDraw.Draw(page)
    for _label, xy, target in label_panels:
        draw_leader(draw, target, (xy[0], xy[1] + 26))
    draw_polyline_leader(draw, [(1120, 438), (1120, 698), (battle_note_xy[0] + 90, battle_note_xy[1])])
    draw_polyline_leader(draw, [(690, 770), (770, 700), (920, 700), (battle_note_xy[0], battle_note_xy[1] + 44)])
    draw_leader(draw, (war_xy[0] + war_panel.width, war_xy[1] + 124), (820, 598))
    draw_leader(draw, (apollo_xy[0] + apollo_panel.width, apollo_xy[1] + 112), (apollo_note_xy[0], apollo_note_xy[1] + 40))

    paste_with_shadow(page, war_panel, war_xy)
    paste_with_shadow(page, apollo_panel, apollo_xy)
    paste_with_shadow(page, battle_note_panel, battle_note_xy)
    paste_with_shadow(page, apollo_note_panel, apollo_note_xy)
    for label, xy, _target in label_panels:
        paste_with_shadow(page, label, xy)

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_3_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "3" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
