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


PASSAGE_ID = "1.8.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_8_4"
MAIN_ART = ASSET_DIR / "main_agora_ares_sanctuary.png"
TEMPLE_SOURCE = ASSET_DIR / "source_temple_of_ares.jpg"
ALTAR_SOURCE = ASSET_DIR / "source_ares_altar.jpg"
FRIEZE_SOURCE = ASSET_DIR / "source_ares_frieze.jpg"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.022) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Sharpness(image).enhance(1.035)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.045)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


def crop_fraction(path: Path, box: tuple[float, float, float, float], size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    w, h = image.size
    crop_box = (
        round(box[0] * w),
        round(box[1] * h),
        round(box[2] * w),
        round(box[3] * h),
    )
    cropped = image.crop(crop_box)
    return ImageOps.fit(cropped, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def make_compact_callout(text: str, size: tuple[int, int], name: str, records: list[FitRecord]) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=16,
            min_size=10,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_locator(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 338))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ARES IN THE AGORA",
            TITLE_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 238)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.46, 0.52))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.25)), grain_strength=0.052)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.34)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "ACROPOLIS": (92, 102),
        "AGORA": (174, 162),
        "ARES": (226, 152),
        "DEMOSTHENES": (140, 188),
    }
    draw.line([points["ACROPOLIS"], points["AGORA"], points["ARES"]], fill="#7b493a", width=3)
    draw.line([points["DEMOSTHENES"], points["ARES"]], fill="#526b73", width=2)
    for name, color in [
        ("ACROPOLIS", "#6a5a39"),
        ("AGORA", "#3f5f72"),
        ("ARES", "#7b493a"),
        ("DEMOSTHENES", "#7f4e35"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    label_specs = [
        ("ACROPOLIS", (48, 78, 152, 102), "locator:acropolis"),
        ("AGORA", (136, 168, 214, 192), "locator:agora"),
        ("ARES", (214, 124, 286, 148), "locator:ares"),
        ("DEMOSTHENES", (82, 202, 210, 226), "locator:demosthenes"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=10,
                min_size=6,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "The sanctuary stands near Demosthenes' statue in the public memory landscape of the Agora."
    records.append(
        draw_fitted_text(
            draw,
            (22, 252, panel.width - 22, panel.height - 14),
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


def make_statue_list_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((398, 336))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 66)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "THE STATUE CATALOGUE",
            TITLE_FONT,
            max_size=17,
            min_size=10,
            padding=6,
            name="catalogue:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            draw,
            (34, 88, panel.width - 34, 166),
            "Inside and beside the sanctuary: Ares, Athena, Enyo, and two images of Aphrodite.",
            BODY_FONT,
            max_size=16,
            min_size=10,
            padding=7,
            name="catalogue:divine-images",
            align="center",
            spacing_ratio=0.14,
        )
    )
    records.append(
        draw_fitted_text(
            draw,
            (34, 184, panel.width - 34, 260),
            "Around the temple: Heracles, Theseus, Apollo binding his hair, Calades, and Pindar.",
            BODY_FONT,
            max_size=16,
            min_size=10,
            padding=7,
            name="catalogue:surrounding-statues",
            align="center",
            spacing_ratio=0.14,
        )
    )
    records.append(
        draw_fitted_text(
            draw,
            (34, 278, panel.width - 34, panel.height - 22),
            "The passage reads like a walked inventory of civic memory.",
            BODY_FONT,
            max_size=15,
            min_size=9,
            padding=5,
            name="catalogue:interpretive-note",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, TEMPLE_SOURCE, ALTAR_SOURCE, FRIEZE_SOURCE]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated/source art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 642)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 706)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.8.4",
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
            max_size=18,
            min_size=10,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (586, 54, 1228, 116)
    paste_with_shadow(
        page,
        make_label("SANCTUARY OF ARES", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ACROPOLIS", (476, 142, 672, 190), (586, 202), 16),
        ("ATHENIAN AGORA", (630, 398, 904, 446), (734, 504), 15),
        ("ARES PRECINCT", (1004, 164, 1258, 212), (1134, 302), 15),
        ("ALTAR AND TEMPLE AXIS", (548, 524, 884, 572), (708, 566), 14),
        ("STATUES AROUND THE TEMPLE", (894, 470, 1288, 518), (1064, 456), 13),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    sculptor_note = make_compact_callout(
        "Pausanias names the makers: Alcamenes for Ares, Locros of Paros for Athena, and Praxiteles' sons for Enyo.",
        (500, 94),
        "callout:sculptors",
        records,
    )
    draw_polyline_leader(draw, [(874, 648), (930, 590), (1064, 456)])
    paste_with_shadow(page, sculptor_note, (430, 648))

    memory_note = make_compact_callout(
        "The shrine gathers divine images, heroes, a lawgiver, and Pindar into one Agora precinct.",
        (438, 94),
        "callout:civic-memory",
        records,
    )
    draw_polyline_leader(draw, [(1198, 648), (1174, 586), (1134, 302)])
    paste_with_shadow(page, memory_note, (934, 648))

    locator = make_locator(records)
    paste_with_shadow(page, locator, (32, 748))

    altar_art = crop_fraction(ALTAR_SOURCE, (0.02, 0.03, 0.98, 0.82), (430, 218))
    altar_art = warm_art(altar_art, grain_strength=0.018)
    altar_panel = make_inset_panel(
        altar_art,
        "The archaeological altar remains anchor the sanctuary within the Agora's actual terrain.",
        92,
        "inset:altar-caption",
        records,
    )
    paste_with_shadow(page, altar_panel, (430, 752))
    altar_label = (540, 772, 816, 808)
    draw_leader(draw, (660, 864), (altar_label[0], altar_label[1] + 18))
    paste_with_shadow(page, make_label("ALTAR OF ARES REMAINS", altar_label, records, max_size=12, min_size=6), (altar_label[0], altar_label[1]))

    frieze_art = crop_fraction(FRIEZE_SOURCE, (0.00, 0.00, 1.00, 0.84), (360, 154))
    frieze_art = warm_art(frieze_art, grain_strength=0.018)
    frieze_panel = make_inset_panel(
        frieze_art,
        "Temple fragments evoke the sculptural programme Pausanias catalogues by artist and subject.",
        94,
        "inset:frieze-caption",
        records,
    )
    paste_with_shadow(page, frieze_panel, (966, 752))

    credit_panel = framed_panel((888, 42))
    credit_draw = ImageDraw.Draw(credit_panel)
    records.append(
        draw_fitted_text(
            credit_draw,
            (12, 7, credit_panel.width - 12, credit_panel.height - 7),
            "Source photos: Dennis G. Jarvis; George E. Koronaios; Giovanni Dall'Orto / Wikimedia Commons.",
            BODY_FONT,
            max_size=10,
            min_size=7,
            padding=3,
            name="source:credits",
            align="center",
            spacing_ratio=0.05,
        )
    )
    paste_with_shadow(page, credit_panel, (450, 1070))

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
            "graphic_book/images/1/8/3.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e9e18-34f0-7a30-9d26-b0fb815e6585/ig_0dd1cf1224ef4b32016a246262e5688191862a3778fbf1115f.png",
                "description": "Generated raster main panel: Athenian Agora temple precinct with Acropolis orientation.",
            },
            {
                "path": str(TEMPLE_SOURCE),
                "source_url": "https://commons.wikimedia.org/wiki/File:Greece-0258_(2215096821).jpg",
                "description": "Wikimedia Commons Temple of Ares source photo by Dennis G. Jarvis, CC BY-SA 2.0.",
            },
            {
                "path": str(ALTAR_SOURCE),
                "source_url": "https://commons.wikimedia.org/wiki/File:Remains_of_the_Altar_of_Ares_in_Ancient_Agora_of_Athens_on_March_23,_2021.jpg",
                "description": "Wikimedia Commons Altar of Ares source photo by George E. Koronaios, CC BY-SA 4.0.",
            },
            {
                "path": str(FRIEZE_SOURCE),
                "source_url": "https://commons.wikimedia.org/wiki/File:3377_-_Athens_-_Sto%C3%A0_of_Attalus_-_Fragments_from_a_freize_-_Photo_by_Giovanni_Dall%27Orto,_Nov_9_2009.jpg",
                "description": "Wikimedia Commons Ares temple fragment source photo by Giovanni Dall'Orto.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_8_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "8" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
