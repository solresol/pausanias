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

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

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


PASSAGE_ID = "1.4.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_4_5"
MAIN_ART = ASSET_DIR / "main_asia_minor_galatian_route.png"
MIDAS_ART = ASSET_DIR / "midas_anchor_spring.png"
PESSINUS_ART = ASSET_DIR / "pessinus_agdistis_attis.png"


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


def warm_art(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Sharpness(image).enhance(1.04)
    wash = Image.new("RGB", image.size, "#e7c995")
    image = Image.blend(image, wash, 0.055)
    grain = Image.effect_noise(image.size, 5).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#a77b45", white="#fff0ca")
    return Image.blend(image, grain_rgb, 0.035)


def make_compact_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=17,
            min_size=12,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.15,
        )
    )
    return panel


def make_route_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((360, 164))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 12, panel.width - 18, 48)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "COAST TO INTERIOR",
            TITLE_FONT,
            max_size=19,
            min_size=13,
            padding=6,
            name="route-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    locator_rect = (24, 58, panel.width - 24, 116)
    locator = crop_to_fill(MAIN_ART, (locator_rect[2] - locator_rect[0], locator_rect[3] - locator_rect[1]), centering=(0.50, 0.58))
    locator = warm_art(locator)
    wash = Image.new("RGB", locator.size, "#ead2a0")
    locator = Image.blend(locator, wash, 0.12)
    panel.paste(locator, (locator_rect[0], locator_rect[1]))
    draw.rounded_rectangle(locator_rect, radius=10, outline=RULE, width=2)
    route = [
        (locator_rect[0] + 34, locator_rect[1] + 42),
        (locator_rect[0] + 104, locator_rect[1] + 34),
        (locator_rect[0] + 174, locator_rect[1] + 38),
        (locator_rect[0] + 246, locator_rect[1] + 30),
        (locator_rect[0] + 296, locator_rect[1] + 40),
    ]
    draw.line(route, fill="#4e2118", width=5, joint="curve")
    draw.line(route, fill="#e0b85e", width=2, joint="curve")
    for point in [route[0], route[-1]]:
        draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5), fill="#6f2d20", outline="#f0d492", width=1)
    records.append(
        draw_fitted_text(
            draw,
            (24, 122, panel.width - 24, panel.height - 12),
            "Coastal raids turn inland beyond the Sangarius.",
            BODY_FONT,
            max_size=13,
            min_size=10,
            padding=4,
            name="route-key:caption",
            align="center",
            spacing_ratio=0.13,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, MIDAS_ART, PESSINUS_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (432, 40, 1372, 666)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.52))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 724)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.4.5",
            TITLE_FONT,
            max_size=30,
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
            max_size=20,
            min_size=12,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.17,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (620, 54, 1186, 118)
    paste_with_shadow(
        page,
        make_label("GALATIANS DRIVEN INLAND", title_rect, records, font_path=TITLE_FONT, max_size=25, min_size=15),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("AEGEAN COAST", (456, 160, 668, 212), (512, 382)),
        ("GALATIAN LANDING", (450, 502, 732, 556), (568, 526)),
        ("PERGAMON / TEUTHRANIA", (578, 382, 930, 436), (652, 404)),
        ("SANGARIUS RIVER", (820, 296, 1096, 350), (858, 336)),
        ("ANKYRA", (1054, 246, 1188, 298), (1082, 274)),
        ("PESSINUS UNDER AGDISTIS", (1124, 430, 1352, 484), (1248, 462)),
        ("PERGAMENE PRESSURE", (928, 560, 1280, 614), (1198, 586)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=22, min_size=11), (rect[0], rect[1]))

    draw_polyline_leader(draw, [(632, 536), (744, 494), (862, 466), (1000, 436), (1110, 392)])
    draw.line([(632, 536), (744, 494), (862, 466), (1000, 436), (1110, 392)], fill="#e0b85e", width=3, joint="curve")

    route_key = make_route_key(records)
    paste_with_shadow(page, route_key, (34, 760))

    coast_callout = make_compact_callout(
        "Pausanias marks a west-to-east turn: seaborne raiding along the Asian coast gives way to inland Galatian control.",
        (364, 112),
        "callout:coast-to-interior",
        records,
    )
    paste_with_shadow(page, coast_callout, (34, 948))
    draw_polyline_leader(draw, [(404, 1002), (524, 928), (596, 558)])

    midas_art = warm_art(crop_to_fill(MIDAS_ART, (398, 214), centering=(0.46, 0.52)))
    midas_panel = make_inset_panel(
        midas_art,
        "At Ankyra, Pausanias records Midas' anchor and spring in the sanctuary of Zeus.",
        90,
        "caption:midas",
        records,
    )
    paste_with_shadow(page, midas_panel, (438, 742))
    paste_with_shadow(page, make_label("MIDAS' ANCHOR", (536, 760, 754, 808), records, max_size=22, min_size=12), (536, 760))
    draw_leader(draw, (638, 846), (610, 806))

    pessinus_art = warm_art(crop_to_fill(PESSINUS_ART, (404, 214), centering=(0.50, 0.52)))
    pessinus_panel = make_inset_panel(
        pessinus_art,
        "Pessinus lies beneath Agdistis; Pausanias adds the tomb of Attis to the Galatian inland horizon.",
        90,
        "caption:pessinus",
        records,
    )
    paste_with_shadow(page, pessinus_panel, (914, 742))
    paste_with_shadow(page, make_label("AGDISTIS AND ATTIS", (1012, 760, 1272, 808), records, max_size=22, min_size=12), (1012, 760))
    draw_leader(draw, (1164, 840), (1136, 806))

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
    }
    report_path = root_dir() / "tmp" / "passage_1_4_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "4" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
