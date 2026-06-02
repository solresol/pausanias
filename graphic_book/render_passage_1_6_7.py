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
    make_inset_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.6.7"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_6_7"
MAIN_ART = ASSET_DIR / "main_antigonus_ipsus.png"
CASSANDER_ART = ASSET_DIR / "cassander_betrayal.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.024) -> Image.Image:
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
            max_size=17,
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_campaign_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 388))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "FROM FAILED SIEGES TO COLLAPSE",
            TITLE_FONT,
            max_size=14,
            min_size=8,
            padding=6,
            name="campaign-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 270)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.56, 0.48))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.5)), grain_strength=0.046)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.55)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "RHODES": (94, 210),
        "EGYPT": (130, 232),
        "MACEDON": (94, 112),
        "ASIA MINOR": (232, 154),
        "COALITION": (258, 182),
    }
    draw.line([points["RHODES"], points["ASIA MINOR"], points["COALITION"]], fill="#7f4e35", width=3)
    draw.line([points["EGYPT"], points["ASIA MINOR"]], fill="#456879", width=3)
    draw.line([points["MACEDON"], points["ASIA MINOR"], points["COALITION"]], fill="#6b5735", width=3)

    for name, color in [
        ("RHODES", "#7f4e35"),
        ("EGYPT", "#365c75"),
        ("MACEDON", "#6b5735"),
        ("ASIA MINOR", "#8a6c31"),
        ("COALITION", "#7b493a"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("RHODES", (50, 194, 124, 216), "campaign-key:rhodes"),
        ("EGYPT", (98, 236, 162, 258), "campaign-key:egypt"),
        ("MACEDON", (50, 92, 134, 114), "campaign-key:macedon"),
        ("ASIA MINOR", (190, 132, 292, 154), "campaign-key:asia-minor"),
        ("COALITION", (210, 194, 310, 216), "campaign-key:coalition"),
    ]:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=8,
                min_size=6,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "Rhodes and Egypt mark the failed reach of Antigonus. The coalition then closes on him in Asia Minor."
    records.append(
        draw_fitted_text(
            draw,
            (24, 286, panel.width - 24, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=13,
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
    for asset in [MAIN_ART, CASSANDER_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.51, 0.51))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 502)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.6.7",
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
            min_size=11,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.14,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (640, 56, 1168, 118)
    paste_with_shadow(
        page,
        make_label("ANTIGONUS FALLS", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ANTIGONUS' PHALANX", (666, 486, 908, 536), (758, 510)),
        ("SELEUCUS' ELEPHANTS", (926, 326, 1194, 376), (1042, 374)),
        ("COALITION PRESSURE", (1044, 472, 1310, 522), (1158, 508)),
        ("CAVALRY FLANK", (500, 278, 694, 328), (640, 314)),
        ("ASIA MINOR", (1148, 574, 1304, 622), (1078, 578)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=17, min_size=8), (rect[0], rect[1]))

    campaign_key = make_campaign_key(records)
    paste_with_shadow(page, campaign_key, (32, 522))

    draw_polyline_leader(draw, [(626, 684), (708, 622), (758, 510)])
    draw_polyline_leader(draw, [(724, 684), (912, 630), (1042, 374)])
    collapse_note = make_compact_callout(
        "After Rhodes and Egypt, Antigonus faces Lysimachus, Cassander, and Seleucus together.",
        (398, 104),
        "callout:coalition",
        records,
    )
    paste_with_shadow(page, collapse_note, (430, 672))

    draw_polyline_leader(draw, [(1090, 684), (1184, 612), (1158, 508)])
    draw_polyline_leader(draw, [(1168, 684), (1054, 618), (758, 510)])
    death_note = make_compact_callout(
        "Pausanias makes Antigonus' death the hinge before judging the kings who overthrew him.",
        (398, 104),
        "callout:death-hinge",
        records,
    )
    paste_with_shadow(page, death_note, (882, 672))

    cassander_art = warm_art(crop_to_fill(CASSANDER_ART, (420, 190), centering=(0.48, 0.42)), grain_strength=0.02)
    cassander_panel = make_inset_panel(
        cassander_art,
        "Cassander is singled out as impious: Antigonus helped restore him to Macedon, yet Cassander joined the war against him.",
        88,
        "inset:cassander-caption",
        records,
    )
    paste_with_shadow(page, cassander_panel, (828, 778))
    cassander_label = (866, 798, 1032, 836)
    draw_leader(draw, (1010, 890), (cassander_label[0], cassander_label[1] + 19))
    paste_with_shadow(page, make_label("CASSANDER", cassander_label, records, max_size=15, min_size=8), (cassander_label[0], cassander_label[1]))

    final_note = make_compact_callout(
        "Pausanias' historical note is also a moral note: success in Macedon does not erase betrayal.",
        (344, 102),
        "callout:moral-note",
        records,
    )
    paste_with_shadow(page, final_note, (430, 902))

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
        "continuity_reference_pages": [
            "graphic_book/images/1/6/6.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "description": "Generated raster main panel: Antigonus' final defeat by the coalition in Asia Minor.",
            },
            {
                "path": str(CASSANDER_ART),
                "description": "Generated raster inset: Cassander and the moral judgment of betrayal.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_6_7_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "6" / "7.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
