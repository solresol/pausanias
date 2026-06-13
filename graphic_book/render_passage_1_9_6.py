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


PASSAGE_ID = "1.9.6"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_9_6"
MAIN_ART = ASSET_DIR / "main_danube_getae_campaign.png"
PEACE_ART = ASSET_DIR / "dromichaetes_peace_inset.png"


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
            "DANUBE FRONTIER",
            TITLE_FONT,
            max_size=18,
            min_size=9,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 230)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 29).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#766b43", white="#efd7a0")
    water_noise = Image.effect_noise(land.size, 17).convert("L")
    water = ImageOps.colorize(ImageOps.autocontrast(water_noise), black="#486e77", white="#a7b8ad")
    mask = Image.new("L", land.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 110), (58, 102), (118, 116), (180, 98), (256, 114), (318, 104), (318, 156), (0, 156)], fill=230)
    mdraw.polygon([(128, 38), (218, 44), (318, 70), (318, 112), (236, 98), (168, 84)], fill=226)
    base = Image.composite(land, water, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "MACEDON": (map_rect[0] + 98, map_rect[1] + 124),
        "THRACE": (map_rect[0] + 180, map_rect[1] + 106),
        "DANUBE": (map_rect[0] + 224, map_rect[1] + 78),
        "GETAE": (map_rect[0] + 262, map_rect[1] + 48),
    }
    route = [points["MACEDON"], points["THRACE"], points["DANUBE"], points["GETAE"]]
    draw.line(route, fill="#7b493a", width=4)
    draw.line(route, fill="#f4ead6", width=1)
    draw.line((map_rect[0] + 134, map_rect[1] + 88, map_rect[0] + 292, map_rect[1] + 48), fill="#496b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("MACEDON", (56, 188, 146, 212), "locator:macedon"),
        ("THRACE", (152, 170, 226, 194), "locator:thrace"),
        ("DANUBE", (184, 104, 266, 128), "locator:danube"),
        ("GETAE", (250, 82, 326, 106), "locator:getae"),
        ("BEYOND THE RIVER", (168, 138, 338, 162), "locator:beyond"),
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

    caption = "The campaign crosses from Lysimachus' Thracian sphere toward Getic power beyond the Danube."
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


def make_consequence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "CAPTIVITY, TREATY, MARRIAGE",
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
        ("DANGER", "Lysimachus narrowly escapes a stronger Getic enemy."),
        ("AGATHOCLES", "His son is captured during the northern campaign."),
        ("DROMICHAETES", "Peace follows necessity and frontier loss."),
        ("LYSANDRA", "Agathocles later marries Ptolemy's daughter."),
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
        name_rect = (34, y + 7, 158, y + 45)
        note_rect = (170, y + 6, panel.width - 34, y + 46)
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
    for asset in [MAIN_ART, PEACE_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.54, 0.48),
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
            "PASSAGE 1.9.6",
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
            max_size=17,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (656, 54, 1174, 116)
    paste_with_shadow(
        page,
        make_label("LYSIMACHUS AT THE DANUBE", title_rect, records, font_path=TITLE_FONT, max_size=27, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("LYSIMACHUS' CAMP", (468, 142, 716, 188), (596, 378), 20),
        ("DANUBE FRONTIER", (712, 246, 980, 292), (820, 292), 21),
        ("GETIC STRONGHOLD", (1036, 138, 1326, 184), (1188, 252), 20),
        ("DROMICHAETES' PEOPLE", (954, 444, 1324, 490), (1118, 396), 17),
        ("RIVER CROSSING", (620, 500, 844, 546), (744, 452), 19),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    treaty_note = make_compact_callout(
        "Repeated setbacks forced peace: lands beyond the Danube passed to Dromichaetes.",
        (420, 88),
        "callout:treaty",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(468, 648), (618, 590), (730, 452)])
    paste_with_shadow(page, treaty_note, (462, 642))

    variant_note = make_compact_callout(
        "Pausanias preserves rival accounts: Agathocles was captured, or Lysimachus himself was released through his son.",
        (458, 92),
        "callout:variant",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(910, 650), (1038, 580), (1154, 388)])
    paste_with_shadow(page, variant_note, (898, 642))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    peace_crop = crop_to_fill(PEACE_ART, (420, 210), centering=(0.52, 0.50))
    peace_crop = warm_art(peace_crop, grain_strength=0.018)
    peace_panel = make_inset_panel(
        peace_crop,
        "Negotiation replaces battle: captivity, necessity, and marriage reorder the frontier.",
        98,
        "inset:peace-caption",
        records,
    )
    paste_with_shadow(page, peace_panel, (440, 762))
    peace_label = (510, 780, 790, 816)
    draw_leader(draw, (660, 900), (peace_label[0], peace_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("PEACE WITH DROMICHAETES", peace_label, records, max_size=15, min_size=6),
        (peace_label[0], peace_label[1]),
    )

    sequence_panel = make_consequence_panel(records)
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
            "graphic_book/images/1/9/5.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ec224-d783-7821-8d40-8a11cdb3f41a/ig_078003db2f0cb793016a2d9b30bdcc81918f4b6d01adf149b0.png",
                "description": "Generated raster source; final page crops a wide Danube-frontier campaign tableau with the river and Getic stronghold visible.",
            },
            {
                "path": str(PEACE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ec224-d783-7821-8d40-8a11cdb3f41a/ig_078003db2f0cb793016a2d9be117888191a845509399e362b5.png",
                "description": "Generated raster scenic inset showing the non-gory peace/captivity negotiation with Dromichaetes.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_9_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "9" / "6.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
