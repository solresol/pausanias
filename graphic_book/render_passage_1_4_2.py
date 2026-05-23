#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pausanias_db import connect

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from graphic_book.render_passage_1_3_2 import (
    BODY_FONT,
    DISPLAY_FONT,
    FitRecord,
    HEIGHT,
    INK,
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
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.4.2"


def load_translation() -> str:
    with connect() as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = %s",
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
    image = ImageEnhance.Contrast(image).enhance(1.07)
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    overlay = Image.new("RGB", image.size, "#edcf9a")
    image = Image.blend(image, overlay, 0.10)
    grain = Image.effect_noise(image.size, 7).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#ba8f55", white="#fff0cb")
    return Image.blend(image, grain_rgb, 0.05)


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((404, 330))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THERMOPYLAE NARROWS",
            TITLE_FONT,
            max_size=23,
            min_size=15,
            padding=8,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 72, panel.width - 22, 238)
    x0, y0, x1, y1 = map_rect
    art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_4_2/main_thermopylae_pass.png",
        (x1 - x0, y1 - y0),
        centering=(0.55, 0.46),
    )
    art = warm_art(art)
    veil = Image.new("RGB", art.size, "#efd9ab")
    art = Image.blend(art, veil, 0.10)
    panel.paste(art, (x0, y0))
    draw.rounded_rectangle(map_rect, radius=16, outline="#7b5a32", width=3)
    draw.rounded_rectangle((x0 + 5, y0 + 5, x1 - 5, y1 - 5), radius=12, outline="#d9bf86", width=1)

    hidden_path = [(x0 + 34, y0 + 54), (x0 + 118, y0 + 36), (x0 + 214, y0 + 52), (x0 + 320, y0 + 92)]
    draw.line(hidden_path, fill="#4c2118", width=7, joint="curve")
    draw.line(hidden_path, fill="#e1b85f", width=3, joint="curve")
    greek_line = [(x0 + 86, y0 + 124), (x0 + 158, y0 + 112), (x0 + 238, y0 + 106)]
    draw.line(greek_line, fill="#213f45", width=8, joint="curve")
    draw.line(greek_line, fill="#f2e6c9", width=3, joint="curve")
    draw.ellipse((x0 + 204, y0 + 56, x0 + 218, y0 + 70), fill="#e1b85f", outline="#4c2118", width=2)

    label_specs = [
        ("MOUNT OETA", (34, 86, 162, 112), "locator:oeta"),
        ("HIDDEN PATH", (70, 122, 198, 148), "locator:path"),
        ("PHOCIANS", (184, 94, 290, 120), "locator:phocians"),
        ("PASS", (130, 184, 210, 210), "locator:pass"),
        ("LAMIAN GULF", (250, 180, 382, 206), "locator:gulf"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=7, fill="#f4e0b4", outline="#b8945a", width=1)
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

    caption_rect = (20, 256, panel.width - 20, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "The Greek line held the coastal narrows until the Celts found the old mountain track.",
            BODY_FONT,
            max_size=16,
            min_size=11,
            padding=6,
            name="locator:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (16, 12, size[0] - 16, size[1] - 12),
            text,
            BODY_FONT,
            max_size=20,
            min_size=12,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.16,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []
    art_path = root_dir() / "graphic_book/assets/generated/1_4_2/main_thermopylae_pass.png"
    if not art_path.exists():
        raise RuntimeError(f"Missing generated art asset: {art_path}")

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    main_rect = (424, 42, 1372, 696)
    main_art = crop_to_fill(art_path, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.52))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 398, 706)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.4.2",
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
            max_size=25,
            min_size=14,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    greek_line = (610, 556)
    hidden_track = (944, 212)
    phocian_post = (790, 246)
    gulf = (1160, 510)
    oeta = (700, 158)

    draw.line([(620, 558), (704, 544), (778, 538)], fill="#2f4f54", width=10)
    draw.line([(620, 558), (704, 544), (778, 538)], fill="#f2e6c9", width=4)
    draw.line([(626, 186), (758, 166), (890, 196), (1012, 248)], fill="#572019", width=9, joint="curve")
    draw.line([(626, 186), (758, 166), (890, 196), (1012, 248)], fill="#e4bd65", width=4, joint="curve")
    draw.ellipse((phocian_post[0] - 9, phocian_post[1] - 9, phocian_post[0] + 9, phocian_post[1] + 9), fill="#e4bd65", outline="#572019", width=2)

    title_rect = (604, 54, 1088, 116)
    paste_with_shadow(page, make_label("THERMOPYLAE FLANKING PATH", title_rect, records, font_path=TITLE_FONT), (title_rect[0], title_rect[1]))

    labels = [
        ("MOUNT OETA", (520, 144, 740, 196), oeta),
        ("HIDDEN PATH", (902, 198, 1144, 250), hidden_track),
        ("PHOCIAN POST", (730, 266, 968, 318), phocian_post),
        ("GREEK DEFENSE", (542, 574, 822, 628), greek_line),
        ("LAMIAN GULF", (1080, 518, 1320, 572), gulf),
    ]
    for text, rect, point in labels:
        paste_with_shadow(page, make_label(text, rect, records), (rect[0], rect[1]))
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))

    locator = make_locator_panel(records)
    locator_xy = (40, 746)
    paste_with_shadow(page, locator, locator_xy)

    callouts = [
        (
            "Kallippos led the Athenians out with the remaining Greeks, despite the exhaustion left by the Macedonian wars.",
            (498, 760, 862, 884),
            (640, 548),
            "callout:kallippos",
        ),
        (
            "Pausanias explicitly recalls Ephialtes: the Celts used the same hidden path once shown to the Medes.",
            (896, 742, 1318, 864),
            (944, 212),
            "callout:ephialtes",
        ),
        (
            "The Phocians posted on the heights were overcome, opening the flank over Mount Oeta.",
            (720, 934, 1186, 1046),
            (790, 246),
            "callout:phocians",
        ),
    ]
    for text, rect, point, name in callouts:
        panel = make_callout(text, (rect[2] - rect[0], rect[3] - rect[1]), name, records)
        paste_with_shadow(page, panel, (rect[0], rect[1]))
        draw_polyline_leader(draw, [point, (rect[0] + 18, rect[1] + (rect[3] - rect[1]) // 2)])

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
    report_path = root_dir() / "tmp" / "passage_1_4_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "4" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
