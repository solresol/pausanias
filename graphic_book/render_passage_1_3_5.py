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

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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


PASSAGE_ID = "1.3.5"


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


def validate_fit_records(records: list[FitRecord]) -> None:
    for record in records:
        rx0, ry0, rx1, ry1 = record.rect
        bx0, by0, bx1, by1 = record.text_bbox
        if bx0 < rx0 or by0 < ry0 or bx1 > rx1 or by1 > ry1:
            raise RuntimeError(f"{record.name}: measured text bbox escapes target rect")


def warm_art(image: Image.Image, contrast: float = 1.05, color: float = 0.96) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(color)
    overlay = Image.new("RGB", image.size, "#efd4a2")
    return Image.blend(image, overlay, 0.08)


def make_civic_locator_map(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((396, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "CIVIC PRECINCT",
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

    acropolis = [(map_rect[0] + 262, map_rect[1] + 16), (map_rect[0] + 336, map_rect[1] + 34), (map_rect[0] + 304, map_rect[1] + 74)]
    agora_floor = (map_rect[0] + 38, map_rect[1] + 72, map_rect[0] + 246, map_rect[1] + 148)
    metroon = (map_rect[0] + 72, map_rect[1] + 46, map_rect[0] + 158, map_rect[1] + 82)
    council = (map_rect[0] + 148, map_rect[1] + 86, map_rect[0] + 246, map_rect[1] + 128)
    tholos = (map_rect[0] + 76, map_rect[1] + 116, map_rect[0] + 124, map_rect[1] + 164)
    road = [
        (map_rect[0] + 24, map_rect[1] + 152),
        (map_rect[0] + 118, map_rect[1] + 132),
        (map_rect[0] + 232, map_rect[1] + 104),
        (map_rect[0] + 328, map_rect[1] + 88),
    ]

    draw.line(road, fill=ROAD, width=15)
    draw.line(road, fill=ROAD_LIGHT, width=5)
    draw.rounded_rectangle(agora_floor, radius=12, fill="#dfc28b", outline=RULE, width=2)
    draw.rounded_rectangle(metroon, radius=8, fill=CITY, outline=RULE, width=2)
    draw.rounded_rectangle(council, radius=8, fill="#c7a068", outline=RULE, width=2)
    draw.ellipse(tholos, fill="#d6b170", outline=RULE, width=2)
    draw.polygon(acropolis, fill="#a77e49", outline=RULE)
    draw.line((acropolis[0][0] + 8, acropolis[1][1], acropolis[1][0] - 8, acropolis[1][1]), fill="#e6c98e", width=3)

    for x, y in [(168, 106), (190, 108), (212, 106)]:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=BRONZE)

    label_specs = [
        ("METROON", (72, 84, 168, 110), "map:metroon"),
        ("COUNCIL", (170, 142, 264, 168), "map:council"),
        ("THOLOS", (76, 188, 152, 214), "map:tholos"),
        ("AGORA", (154, 188, 248, 214), "map:agora"),
        ("ACROPOLIS", (262, 112, 372, 138), "map:acropolis"),
        ("WEST ROAD", (238, 170, 350, 196), "map:west-road"),
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
            "Pausanias moves through the west Agora from the Mother sanctuary to the Council Chamber.",
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


def make_statue_study(records: list[FitRecord]) -> Image.Image:
    art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_2/main_northwest_agora.png",
        (438, 238),
        centering=(0.64, 0.62),
    )
    art = warm_art(art, contrast=1.08)
    return make_inset_panel(
        art,
        "Inside the Council Chamber Pausanias notes Zeus Boulaios, Apollo, and Demos.",
        92,
        "caption:statue-study",
        records,
    )


def make_thermopylae_panel(records: list[FitRecord]) -> Image.Image:
    art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_4/main_mantineia_cavalry.png",
        (364, 214),
        centering=(0.58, 0.42),
    )
    art = warm_art(art, contrast=1.04, color=0.9)
    art = ImageEnhance.Brightness(art).enhance(0.96)
    tablet = Image.new("RGBA", (art.width, art.height), (0, 0, 0, 0))
    tablet.alpha_composite(art.convert("RGBA"))
    vignette = Image.new("L", art.size, 0)
    vdraw = ImageDraw.Draw(vignette)
    for inset, alpha in [(0, 92), (14, 54), (32, 24)]:
        vdraw.rectangle((inset, inset, art.width - inset, art.height - inset), outline=alpha, width=8)
    vignette = vignette.filter(ImageFilter.GaussianBlur(16))
    edge = Image.new("RGBA", art.size, (91, 54, 26, 0))
    edge.putalpha(vignette)
    tablet = Image.alpha_composite(tablet, edge).convert("RGB")
    return make_inset_panel(
        tablet,
        "Olbiades painted Callippos leading Athenians at Thermopylae against the Galatian invasion.",
        108,
        "caption:thermopylae",
        records,
    )


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (454, 44, 1372, 660)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_2/main_northwest_agora.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.54),
    )
    main_art = warm_art(main_art, contrast=1.06)
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle(
        (13, 13, 13 + main_art.width, 13 + main_art.height),
        outline=RULE,
        width=2,
    )
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 642)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.3.5",
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

    title_rect = (568, 42, 1228, 118)
    title_panel = make_label(
        "MOTHER OF THE GODS AND THE COUNCIL",
        title_rect,
        records,
        font_path=TITLE_FONT,
        max_size=25,
        min_size=14,
    )
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    labels = [
        ("MOTHER SANCTUARY", (512, 160, 810, 212), (704, 280)),
        ("COUNCIL CHAMBER", (944, 188, 1246, 240), (1032, 330)),
        ("STATUES INSIDE", (998, 506, 1240, 558), (1024, 464)),
        ("ATHENIAN AGORA", (616, 584, 866, 636), (810, 528)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int], tuple[int, int]]] = []
    for text, rect, target in labels:
        label = make_label(text, rect, records, max_size=22, min_size=12)
        label_panels.append((label, (rect[0], rect[1]), target))

    locator_panel = make_civic_locator_map(records)
    locator_xy = (34, 738)

    statue_panel = make_statue_study(records)
    statue_xy = (468, 728)

    thermopylae_panel = make_thermopylae_panel(records)
    thermopylae_xy = (950, 728)

    council_note_panel = make_note_panel(
        "The Five Hundred advised Athens for the year; Pausanias ties the building to cult images and civic personifications.",
        (392, 112),
        "callout:council-role",
        records,
    )
    council_note_xy = (512, 650)

    painting_note_panel = make_note_panel(
        "The named painters turn this civic precinct into a gallery of Athenian law and public memory.",
        (390, 90),
        "callout:painters",
        records,
    )
    painting_note_xy = (952, 620)

    draw = ImageDraw.Draw(page)
    for _label, xy, target in label_panels:
        draw_leader(draw, target, (xy[0], xy[1] + 26))
    draw_polyline_leader(draw, [(760, 650), (760, 688), (council_note_xy[0] + 70, council_note_xy[1])])
    draw_polyline_leader(draw, [(1062, 558), (1062, 600), (painting_note_xy[0] + 74, painting_note_xy[1])])
    draw_leader(draw, (locator_xy[0] + locator_panel.width, locator_xy[1] + 128), (584, 604))
    draw_leader(draw, (statue_xy[0] + 220, statue_xy[1]), (1050, 482))
    draw_leader(draw, (thermopylae_xy[0] + 96, thermopylae_xy[1]), (painting_note_xy[0] + 218, painting_note_xy[1] + 90))

    paste_with_shadow(page, locator_panel, locator_xy)
    paste_with_shadow(page, statue_panel, statue_xy)
    paste_with_shadow(page, thermopylae_panel, thermopylae_xy)
    paste_with_shadow(page, council_note_panel, council_note_xy)
    paste_with_shadow(page, painting_note_panel, painting_note_xy)
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
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_3_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "3" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
