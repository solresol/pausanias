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
    INK,
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


PASSAGE_ID = "1.9.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_9_3"
MAIN_ART = ASSET_DIR / "main_thebes_surrender.png"
STATUES_ART = ASSET_DIR / "athens_ptolemy_berenice_statues.png"


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
    image = ImageEnhance.Color(image).enhance(0.95)
    image = ImageEnhance.Sharpness(image).enhance(1.035)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.04)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


def crop_to_fill(
    path: Path,
    size: tuple[int, int],
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=centering)


def make_compact_callout(
    text: str,
    size: tuple[int, int],
    name: str,
    records: list[FitRecord],
    *,
    max_size: int = 16,
    min_size: int = 9,
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
            spacing_ratio=0.13,
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
            "EGYPT, BOEOTIA, ATHENS",
            TITLE_FONT,
            max_size=17,
            min_size=9,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 230)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 25).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#766b48", white="#f1d9a5")
    sea_noise = Image.effect_noise(land.size, 17).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#4d737b", white="#a5b6a8")
    mask = Image.new("L", land.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 104), (64, 92), (128, 110), (180, 96), (236, 116), (318, 102), (318, 156), (0, 156)], fill=232)
    mdraw.polygon([(26, 88), (70, 74), (116, 88), (74, 112)], fill=226)
    mdraw.ellipse((206, 54, 258, 94), fill=222)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "ALEXANDRIA": (map_rect[0] + 88, map_rect[1] + 126),
        "THEBES": (map_rect[0] + 214, map_rect[1] + 76),
        "ATHENS": (map_rect[0] + 238, map_rect[1] + 88),
        "DELPHI": (map_rect[0] + 204, map_rect[1] + 66),
        "ORCHOMENUS": (map_rect[0] + 224, map_rect[1] + 58),
    }
    route = [points["ALEXANDRIA"], (map_rect[0] + 156, map_rect[1] + 94), points["THEBES"], points["ATHENS"]]
    draw.line(route, fill="#7b493a", width=4)
    draw.line(route, fill="#f4ead6", width=1)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("ALEXANDRIA", (50, 190, 154, 214), "locator:alexandria"),
        ("THEBES", (202, 100, 272, 124), "locator:thebes"),
        ("ATHENS", (250, 136, 320, 160), "locator:athens"),
        ("DELPHI", (114, 96, 176, 120), "locator:delphi"),
        ("ORCHOMENUS", (194, 70, 302, 94), "locator:orchomenus"),
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

    caption = "Pausanias shifts from Egyptian succession to Boeotia, then back to Athenian public honors."
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
            "FORTUNE REVERSES COURSE",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="sequence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("CLEOPATRA", "Alexander, whom she had raised up, puts her to death."),
        ("PTOLEMY", "He returns and gains Egypt for a second time."),
        ("THEBES", "A three-year revolt ends in surrender and ruin."),
        ("ATHENS", "Bronze statues honor Ptolemy and legitimate Berenice."),
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
        name_rect = (34, y + 7, 154, y + 45)
        note_rect = (166, y + 6, panel.width - 34, y + 46)
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
    for asset in [MAIN_ART, STATUES_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.50, 0.51),
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
            "PASSAGE 1.9.3",
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
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (698, 54, 1120, 116)
    paste_with_shadow(
        page,
        make_label("THEBES AFTER PTOLEMY'S RETURN", title_rect, records, font_path=TITLE_FONT, max_size=17, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("BOEOTIAN PLAIN", (520, 120, 744, 166), (688, 226), 17),
        ("THEBES", (844, 216, 1008, 262), (912, 312), 22),
        ("PTOLEMAIC FORCES", (480, 414, 746, 460), (594, 532), 17),
        ("BREACHED WALLS", (986, 404, 1218, 450), (1022, 364), 17),
        ("THREE-YEAR REVOLT", (1098, 152, 1342, 198), (1132, 266), 16),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    war_note = make_compact_callout(
        "After regaining Egypt, Ptolemy next appears in Boeotia: Thebes surrenders after a long revolt.",
        (426, 92),
        "callout:war",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(472, 648), (552, 578), (636, 512)])
    paste_with_shadow(page, war_note, (458, 642))

    ruin_note = make_compact_callout(
        "Pausanias measures Thebes' fall against its former wealth, greater than even Delphi and Orchomenus.",
        (438, 92),
        "callout:ruin",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(920, 648), (986, 532), (1040, 420)])
    paste_with_shadow(page, ruin_note, (912, 642))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    statues_crop = crop_to_fill(STATUES_ART, (420, 210), centering=(0.50, 0.50))
    statues_crop = warm_art(statues_crop, grain_strength=0.018)
    statues_panel = make_inset_panel(
        statues_crop,
        "Athens answers benefaction with bronze portraits of Ptolemy and legitimate Berenice.",
        98,
        "inset:statues-caption",
        records,
    )
    paste_with_shadow(page, statues_panel, (440, 762))
    statues_label = (512, 780, 788, 816)
    draw_leader(draw, (658, 900), (statues_label[0], statues_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("ATHENIAN BRONZE HONORS", statues_label, records, max_size=15, min_size=6),
        (statues_label[0], statues_label[1]),
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
            "graphic_book/images/1/9/1.png",
            "graphic_book/images/1/9/2.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019eb4d6-8c52-7882-ab24-ceea8bdd617e/ig_01b4b8931d1eae07016a2a33249fbc819184e70c234681b5a8.png",
                "description": "Generated raster main panel: Thebes in Boeotia after surrender, Ptolemaic forces, damaged walls, and Boeotian landscape.",
            },
            {
                "path": str(STATUES_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019eb4d6-8c52-7882-ab24-ceea8bdd617e/ig_01b4b8931d1eae07016a2a33b6cb188191ba6b95e3b356c971.png",
                "description": "Generated raster inset: Athenian bronze honor statues of Ptolemy and Berenice.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_9_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "9" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
