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
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.6.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_5"
MAIN_ART = ASSET_DIR / "main_antigonus_eastern_mediterranean.png"


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


def validate_fit_records(records: list[FitRecord]) -> None:
    for record in records:
        rx0, ry0, rx1, ry1 = record.rect
        bx0, by0, bx1, by1 = record.text_bbox
        if bx0 < rx0 or by0 < ry0 or bx1 > rx1 or by1 > ry1:
            raise RuntimeError(f"{record.name}: measured text bbox escapes target rect")


def warm_art(image: Image.Image, *, grain_strength: float = 0.025) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.90)
    image = ImageEnhance.Sharpness(image).enhance(1.04)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.04)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


def make_compact_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=18,
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_campaign_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 304))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "EASTERN MEDITERRANEAN TURN",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="campaign-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 206)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.55, 0.68))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.5)), grain_strength=0.045)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.48)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "LIBYA": (90, 166),
        "EGYPT": (142, 178),
        "SYRIA": (235, 128),
        "PHOENICIA": (218, 148),
        "HELLESPONT": (186, 96),
        "BATTLE": (254, 164),
    }
    for a, b, color in [
        ("LIBYA", "EGYPT", "#5c6480"),
        ("EGYPT", "SYRIA", "#7d5432"),
        ("SYRIA", "PHOENICIA", "#7d5432"),
        ("PHOENICIA", "HELLESPONT", "#7b493a"),
        ("BATTLE", "EGYPT", "#445d77"),
    ]:
        draw.line([points[a], points[b]], fill=color, width=3)

    for name, color in [
        ("LIBYA", "#5c6480"),
        ("EGYPT", "#365c75"),
        ("SYRIA", "#8a6c31"),
        ("PHOENICIA", "#8a6c31"),
        ("HELLESPONT", "#7b493a"),
        ("BATTLE", "#7b493a"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("LIBYA", (58, 178, 122, 200), "campaign-key:libya"),
        ("EGYPT", (110, 194, 178, 216), "campaign-key:egypt"),
        ("SYRIA", (216, 104, 276, 126), "campaign-key:syria"),
        ("PHOENICIA", (176, 146, 270, 168), "campaign-key:phoenicia"),
        ("HELLESPONT", (142, 74, 244, 96), "campaign-key:hellespont"),
        ("DEFEAT", (246, 174, 318, 196), "campaign-key:defeat"),
    ]:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "Ptolemy's Libyan diversion opens the Levant; Demetrius' setback pulls Antigonus back from the Hellespont."
    records.append(
        draw_fitted_text(
            draw,
            (24, 218, panel.width - 24, panel.height - 12),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="campaign-key:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not MAIN_ART.exists():
        raise RuntimeError(f"Missing generated art asset: {MAIN_ART}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.52, 0.52))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 738)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.6.5",
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
            max_size=19,
            min_size=11,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.14,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (612, 56, 1198, 118)
    paste_with_shadow(
        page,
        make_label("ANTIGONUS' COUNTERMOVE", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ANTIGONUS", (512, 274, 666, 326), (612, 380)),
        ("DEMETRIUS", (808, 222, 986, 274), (860, 410)),
        ("LIBYA / CYRENE", (526, 542, 744, 594), (636, 560)),
        ("EGYPT", (916, 548, 1042, 600), (994, 594)),
        ("SYRIA", (1068, 492, 1188, 544), (1052, 518)),
        ("PHOENICIA", (1168, 568, 1350, 620), (1122, 564)),
        ("HELLESPONT", (1008, 152, 1206, 204), (930, 306)),
        ("PTOLEMY WITHDRAWS", (702, 610, 956, 646), (994, 594)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=18, min_size=8), (rect[0], rect[1]))

    campaign_key = make_campaign_key(records)
    paste_with_shadow(page, campaign_key, (32, 756))

    levante_note = make_compact_callout(
        "Ptolemy's march into Libya gives Antigonus the opening to seize Syria and Phoenicia quickly.",
        (424, 116),
        "callout:levant",
        records,
    )
    paste_with_shadow(page, levante_note, (444, 706))
    draw_polyline_leader(draw, [(656, 706), (760, 648), (1052, 518)])

    demetrius_note = make_compact_callout(
        "Demetrius holds part of the captured territory, even after defeat, by ambushing a small Egyptian force.",
        (424, 116),
        "callout:demetrius",
        records,
    )
    paste_with_shadow(page, demetrius_note, (898, 706))
    draw_polyline_leader(draw, [(1110, 706), (1100, 652), (860, 410)])

    withdrawal_note = make_compact_callout(
        "Antigonus' return changes the balance: Ptolemy declines battle and retreats to Egypt.",
        (424, 104),
        "callout:withdrawal",
        records,
    )
    paste_with_shadow(page, withdrawal_note, (468, 852))
    draw_polyline_leader(draw, [(680, 852), (792, 798), (994, 594)])

    hellespont_note = make_compact_callout(
        "The Hellespont is the interrupted northern objective; the southern crisis pulls the army back before the crossing.",
        (424, 104),
        "callout:hellespont",
        records,
    )
    paste_with_shadow(page, hellespont_note, (918, 852))
    draw_polyline_leader(draw, [(1130, 852), (1164, 650), (930, 306)])

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
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Hellenistic campaign room with an eastern Mediterranean map-table for Antigonus, Demetrius, and Ptolemy's movements.",
            }
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
