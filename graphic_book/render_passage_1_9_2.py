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


PASSAGE_ID = "1.9.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_9_2"
MAIN_ART = ASSET_DIR / "main_alexandria_palace_harbor_coup.png"
PROCLAMATION_ART = ASSET_DIR / "alexander_arrival_proclamation.png"


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
    image = Image.blend(image, wash, 0.042)
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
            min_size=9,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.13,
        )
    )
    return panel


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((378, 338))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ALEXANDRIA AND CYPRUS",
            TITLE_FONT,
            max_size=18,
            min_size=10,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 236)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 26).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#7d7049", white="#f2dbad")
    sea_noise = Image.effect_noise(land.size, 18).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#517b82", white="#a5b6a9")
    mask = Image.new("L", land.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 118), (84, 110), (162, 134), (234, 126), (318, 150), (318, 162), (0, 162)], fill=224)
    mdraw.ellipse((226, 34, 296, 82), fill=220)
    mdraw.polygon([(210, 48), (270, 30), (304, 56), (256, 96)], fill=220)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    alexandria = (map_rect[0] + 82, map_rect[1] + 124)
    cyprus = (map_rect[0] + 252, map_rect[1] + 62)
    draw.line((alexandria, (map_rect[0] + 168, map_rect[1] + 92), cyprus), fill="#7b493a", width=4)
    draw.line((alexandria, (map_rect[0] + 168, map_rect[1] + 92), cyprus), fill="#f4ead6", width=1)
    for x, y in [alexandria, cyprus]:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("ALEXANDRIA", (46, 194, 162, 220), "locator:alexandria"),
        ("CYPRUS", (228, 104, 308, 130), "locator:cyprus"),
        ("EGYPT", (92, 244, 164, 268), "locator:egypt"),
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

    caption = "Cyprus is the lever: Alexander returns from the island as Ptolemy escapes Alexandria by sea."
    records.append(
        draw_fitted_text(
            draw,
            (22, 278, panel.width - 22, panel.height - 14),
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


def make_crisis_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 318))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 64)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "THE STAGED ACCUSATION",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="crisis:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("CLEOPATRA", "wounded loyal eunuchs, then displayed them before the people"),
        ("ACCUSATION", "she claimed Ptolemy had plotted against her and injured them"),
        ("PTOLEMY", "anticipated the Alexandrian rush and escaped aboard a ship"),
        ("ALEXANDER", "arrived from Cyprus and was proclaimed king by the crowd"),
    ]
    y = 82
    for idx, (name, note) in enumerate(rows):
        row_rect = (24, y, panel.width - 24, y + 48)
        draw.rounded_rectangle(
            row_rect,
            radius=9,
            fill="#f3dfb4" if idx % 2 == 0 else "#f7e8c8",
            outline="#b8945a",
            width=1,
        )
        name_rect = (34, y + 6, 160, y + 42)
        note_rect = (174, y + 5, panel.width - 34, y + 43)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"crisis:name:{idx}",
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
                max_size=11,
                min_size=7,
                padding=2,
                name=f"crisis:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 54
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, PROCLAMATION_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 622)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 410, 704)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.9.2",
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
            max_size=21,
            min_size=11,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.13,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (648, 54, 1148, 116)
    paste_with_shadow(
        page,
        make_label("ALEXANDRIA: FLIGHT AND PROCLAMATION", title_rect, records, font_path=TITLE_FONT, max_size=18, min_size=10),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("CLEOPATRA", (458, 116, 646, 162), (532, 244), 20),
        ("WOUNDED EUNUCHS", (548, 344, 822, 390), (636, 330), 18),
        ("ALEXANDRIANS", (728, 458, 950, 504), (810, 454), 20),
        ("PTOLEMY'S SHIP", (1078, 206, 1308, 252), (1166, 366), 18),
        ("GREAT HARBOR", (914, 112, 1128, 158), (934, 292), 20),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    accusation_note = make_compact_callout(
        "The accusation is staged through visible wounds: Cleopatra shows the attendants as proof of a plot.",
        (426, 94),
        "callout:accusation",
        records,
    )
    draw_polyline_leader(draw, [(520, 636), (532, 542), (558, 456), (602, 410)])
    paste_with_shadow(page, accusation_note, (462, 634))

    flight_note = make_compact_callout(
        "Ptolemy survives because he boards first; the mob reaches for him after his ship has become his refuge.",
        (438, 94),
        "callout:flight",
        records,
    )
    draw_polyline_leader(draw, [(918, 636), (1046, 484), (1196, 384)])
    paste_with_shadow(page, flight_note, (912, 634))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 736))

    proclamation_crop = crop_to_fill(PROCLAMATION_ART, (420, 220), centering=(0.48, 0.50))
    proclamation_crop = warm_art(proclamation_crop, grain_strength=0.018)
    proclamation_panel = make_inset_panel(
        proclamation_crop,
        "Alexander's arrival from Cyprus turns the accusation into a public proclamation.",
        92,
        "inset:proclamation-caption",
        records,
    )
    paste_with_shadow(page, proclamation_panel, (440, 754))
    proclamation_label = (508, 772, 792, 808)
    draw_leader(draw, (622, 900), (proclamation_label[0], proclamation_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("PROCLAIMED KING", proclamation_label, records, max_size=18, min_size=6),
        (proclamation_label[0], proclamation_label[1]),
    )

    crisis_panel = make_crisis_panel(records)
    paste_with_shadow(page, crisis_panel, (904, 754))

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
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019eafb1-96bd-7e80-ab1d-e8b1edae8146/ig_0d8115b8b7e5a461016a28e237d81881918a5e147bd9e66d89.png",
                "description": "Generated raster main panel: Alexandrian palace-harbor coup with Cleopatra, wounded attendants, crowd, and Ptolemy's ship.",
            },
            {
                "path": str(PROCLAMATION_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019eafb1-96bd-7e80-ab1d-e8b1edae8146/ig_0d8115b8b7e5a461016a28e306495881919bb622d231dfefbb.png",
                "description": "Generated raster inset: Alexander arriving from Cyprus and being acclaimed by Alexandrians.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_9_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "9" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
