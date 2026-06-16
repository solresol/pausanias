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


PASSAGE_ID = "1.10.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_10_1"
MAIN_ART = ASSET_DIR / "main_lysimachus_war_council.png"
DEMETRIUS_ART = ASSET_DIR / "demetrius_macedonian_throne.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.02) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.95)
    image = ImageEnhance.Sharpness(image).enhance(1.025)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.045)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


def crop_to_fill(
    path: Path,
    size: tuple[int, int],
    centering: tuple[float, float] = (0.5, 0.5),
    source_box: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if source_box is not None:
        image = image.crop(source_box)
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=centering)


def make_compact_callout(
    text: str,
    size: tuple[int, int],
    name: str,
    records: list[FitRecord],
    *,
    max_size: int = 15,
    min_size: int = 8,
) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=max_size,
            min_size=min_size,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((378, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THRACE AND MACEDONIA",
            TITLE_FONT,
            max_size=17,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 230)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 31).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#77663e", white="#efd7a0")
    sea_noise = Image.effect_noise(land.size, 17).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#486e77", white="#a9b9ad")
    mask = Image.new("L", land.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (138, 0), (126, 48), (96, 88), (34, 118), (0, 156)], fill=226)
    mdraw.polygon([(112, 16), (318, 6), (318, 110), (236, 98), (174, 118), (128, 78)], fill=230)
    mdraw.polygon([(86, 128), (168, 106), (258, 120), (318, 108), (318, 156), (0, 156)], fill=220)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "THRACE": (map_rect[0] + 236, map_rect[1] + 74),
        "AMPHIPOLIS": (map_rect[0] + 150, map_rect[1] + 96),
        "PELLA": (map_rect[0] + 92, map_rect[1] + 110),
        "ANTIGONID": (map_rect[0] + 258, map_rect[1] + 34),
    }
    frontier = [points["THRACE"], points["AMPHIPOLIS"], points["PELLA"]]
    antigonid = [points["ANTIGONID"], points["AMPHIPOLIS"], points["PELLA"]]
    draw.line(frontier, fill="#7b493a", width=4)
    draw.line(frontier, fill="#f4ead6", width=1)
    draw.line(antigonid, fill="#4d5f5d", width=3)
    draw.line((map_rect[0] + 36, map_rect[1] + 128, map_rect[0] + 292, map_rect[1] + 122), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("MACEDONIA", (38, 152, 140, 176), "locator:macedonia"),
        ("PELLA", (58, 188, 118, 212), "locator:pella"),
        ("AMPHIPOLIS", (124, 164, 230, 188), "locator:amphipolis"),
        ("THRACE", (220, 132, 292, 156), "locator:thrace"),
        ("AEGEAN", (166, 202, 238, 226), "locator:aegean"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=8,
                min_size=5,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.04,
            )
        )

    caption = "The crisis turns on the border between Lysimachus' Thrace and the Macedon seized by Demetrius."
    records.append(
        draw_fitted_text(
            draw,
            (22, 262, panel.width - 22, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="locator:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def make_sequence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "WHY LYSIMACHUS MOVES",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="sequence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("FRIENDSHIP", "Macedon had remained friendly under Aridaeus and Cassander."),
        ("SUCCESSION", "Cassander's sons gave way to Demetrius' ambition."),
        ("USURPATION", "Demetrius killed Alexander and seized the kingdom."),
        ("FIRST STRIKE", "Lysimachus expected attack and chose to begin the war."),
    ]
    y = 78
    for idx, (name, note) in enumerate(rows):
        row_rect = (24, y, panel.width - 24, y + 52)
        draw.rounded_rectangle(
            row_rect,
            radius=9,
            fill="#f3dfb4" if idx % 2 == 0 else "#f7e8c8",
            outline="#b8945a",
            width=1,
        )
        name_rect = (34, y + 7, 160, y + 45)
        note_rect = (174, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"sequence:name:{idx}",
                align="center",
                spacing_ratio=0.05,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                note_rect,
                note,
                BODY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"sequence:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, DEMETRIUS_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.53, 0.48),
    )
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 726)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.10.1",
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
            max_size=19,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (604, 54, 1224, 116)
    paste_with_shadow(
        page,
        make_label("LYSIMACHUS STRIKES FIRST", title_rect, records, font_path=TITLE_FONT, max_size=24, min_size=10),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("LYSIMACHUS' COUNCIL", (486, 140, 800, 186), (704, 384), 17),
        ("NEWS FROM MACEDONIA", (456, 536, 812, 582), (548, 332), 15),
        ("FRONTIER LANDSCAPE", (878, 122, 1190, 168), (924, 268), 17),
        ("TABLE MAP", (1010, 498, 1214, 544), (890, 470), 20),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    expectation_note = make_compact_callout(
        "Demetrius' appetite for power makes Lysimachus expect the next attack.",
        (420, 88),
        "callout:expectation",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(466, 648), (610, 594), (704, 384)])
    paste_with_shadow(page, expectation_note, (462, 642))

    first_strike_note = make_compact_callout(
        "The passage explains the logic of preemption: Lysimachus chooses to open the war himself.",
        (458, 90),
        "callout:first-strike",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(910, 648), (1040, 596), (890, 470)])
    paste_with_shadow(page, first_strike_note, (898, 642))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    demetrius_crop = crop_to_fill(DEMETRIUS_ART, (420, 210), centering=(0.54, 0.50))
    demetrius_crop = warm_art(demetrius_crop, grain_strength=0.018)
    demetrius_panel = make_inset_panel(
        demetrius_crop,
        "Demetrius, son of Antigonus, came into Macedonia and seized the throne after murdering Alexander, son of Cassander.",
        98,
        "inset:demetrius-caption",
        records,
    )
    paste_with_shadow(page, demetrius_panel, (440, 762))
    demetrius_label = (510, 780, 814, 816)
    draw_leader(draw, (710, 900), (demetrius_label[0], demetrius_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("DEMETRIUS SEIZES MACEDON", demetrius_label, records, max_size=14, min_size=6),
        (demetrius_label[0], demetrius_label[1]),
    )

    sequence_panel = make_sequence_panel(records)
    paste_with_shadow(page, sequence_panel, (904, 758))

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
            "graphic_book/images/1/9/8.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ed197-af7c-7930-aae5-8ac947dd34ea/ig_042c8863865126c3016a318fb64fdc8191b3b2cf47d362b4f1.png",
                "description": "Generated raster source; final page crops a Hellenistic war-council scene with Lysimachus, a messenger, and a table map toward Macedonia.",
            },
            {
                "path": str(DEMETRIUS_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ed197-af7c-7930-aae5-8ac947dd34ea/ig_042c8863865126c3016a31905ce0448191a3ddb89b79e62d51.png",
                "description": "Generated raster scenic inset showing Demetrius taking the Macedonian throne without gore or nudity.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_10_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "10" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
