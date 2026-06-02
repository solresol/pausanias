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


PASSAGE_ID = "1.7.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_7_2"
MAIN_ART = ASSET_DIR / "main_egyptian_entrance_defense.png"
MARMARIDAE_ART = ASSET_DIR / "marmaridae_revolt_cyrene.png"
GALATIAN_ART = ASSET_DIR / "galatian_nile_island.png"


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
    image = ImageEnhance.Contrast(image).enhance(1.05)
    image = ImageEnhance.Color(image).enhance(0.92)
    image = ImageEnhance.Sharpness(image).enhance(1.03)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.035)
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
            max_size=16,
            min_size=9,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_locator_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 340))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "CYRENE AND EGYPT",
            TITLE_FONT,
            max_size=17,
            min_size=10,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 244)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.45, 0.50))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.4)), grain_strength=0.05)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.36)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "CYRENE": (78, 188),
        "MARMARIDAE": (72, 130),
        "EGYPT": (228, 172),
        "NILE ISLAND": (238, 212),
    }
    draw.line([points["CYRENE"], points["EGYPT"]], fill="#7f4e35", width=4)
    draw.line([points["CYRENE"], points["MARMARIDAE"]], fill="#6b5735", width=3)
    draw.line([points["EGYPT"], points["NILE ISLAND"]], fill="#365c75", width=3)
    for name, color in [
        ("CYRENE", "#7f4e35"),
        ("MARMARIDAE", "#6b5735"),
        ("EGYPT", "#7b493a"),
        ("NILE ISLAND", "#365c75"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("CYRENE", (40, 194, 118, 218), "locator:cyrene"),
        ("MARMARIDAE", (44, 102, 146, 126), "locator:marmaridae"),
        ("EGYPT", (204, 144, 276, 168), "locator:egypt"),
        ("NILE ISLAND", (184, 216, 300, 240), "locator:nile-island"),
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

    caption = "Ptolemy holds the Egyptian entrance; Magas turns back to Cyrene, while suspect Galatians are removed to a deserted river island."
    records.append(
        draw_fitted_text(
            draw,
            (22, 258, panel.width - 22, panel.height - 14),
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


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, MARMARIDAE_ART, GALATIAN_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 642)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 688)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.7.2",
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
    title_rect = (636, 56, 1172, 118)
    paste_with_shadow(
        page,
        make_label("PTOLEMY CHECKS MAGAS", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("WESTERN ROAD FROM CYRENE", (506, 164, 842, 212), (526, 292)),
        ("EGYPTIAN ENTRANCE", (760, 354, 1032, 402), (806, 408)),
        ("PTOLEMY'S DEFENSES", (1042, 478, 1306, 526), (1118, 524)),
        ("NILE WATERWAY", (668, 506, 888, 554), (734, 498)),
        ("DELTA FIELDS", (1054, 178, 1238, 226), (1110, 250)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=16, min_size=8), (rect[0], rect[1]))

    pursuit_note = make_compact_callout(
        "Ptolemy is ready to pursue, but first has to neutralize foreign mercenaries inside Egypt.",
        (392, 96),
        "callout:pursuit-blocked",
        records,
    )
    draw_polyline_leader(draw, [(786, 654), (790, 566), (734, 498)])
    paste_with_shadow(page, pursuit_note, (566, 648))

    magas_note = make_compact_callout(
        "The Marmaridae revolt pulls Magas away from the Egyptian advance and back to Cyrene.",
        (392, 96),
        "callout:magas-withdraws",
        records,
    )
    draw_polyline_leader(draw, [(1100, 654), (1000, 562), (526, 292)])
    paste_with_shadow(page, magas_note, (976, 648))

    locator = make_locator_key(records)
    paste_with_shadow(page, locator, (32, 724))

    marmaridae_art = warm_art(crop_to_fill(MARMARIDAE_ART, (420, 218), centering=(0.50, 0.50)), grain_strength=0.02)
    marmaridae_panel = make_inset_panel(
        marmaridae_art,
        "News of the Marmaridae revolt turns Magas back from the road toward Egypt.",
        78,
        "inset:marmaridae-caption",
        records,
    )
    paste_with_shadow(page, marmaridae_panel, (430, 760))
    marmaridae_label = (548, 780, 788, 816)
    draw_leader(draw, (642, 884), (marmaridae_label[0], marmaridae_label[1] + 18))
    paste_with_shadow(page, make_label("MARMARIDAE REVOLT", marmaridae_label, records, max_size=13, min_size=7), (marmaridae_label[0], marmaridae_label[1]))

    galatian_art = warm_art(crop_to_fill(GALATIAN_ART, (404, 218), centering=(0.50, 0.50)), grain_strength=0.02)
    galatian_panel = make_inset_panel(
        galatian_art,
        "Ptolemy conveys suspect Galatians by river to an isolated island.",
        78,
        "inset:galatian-caption",
        records,
    )
    paste_with_shadow(page, galatian_panel, (918, 760))
    galatian_label = (1036, 780, 1208, 816)
    draw_leader(draw, (1104, 888), (galatian_label[0], galatian_label[1] + 18))
    paste_with_shadow(page, make_label("NILE ISLAND", galatian_label, records, max_size=15, min_size=8), (galatian_label[0], galatian_label[1]))

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
            "graphic_book/images/1/7/1.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e8458-df5c-75e1-b6dd-26109f659600/ig_0638aef7a576ce49016a1dc945cae081918a3f7d95b126d72f.png",
                "description": "Generated raster main panel: western Egyptian/Nile entrance with Ptolemaic defenses and Libyan approach road.",
            },
            {
                "path": str(MARMARIDAE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e8458-df5c-75e1-b6dd-26109f659600/ig_0638aef7a576ce49016a1dc9e96d248191bfeb41f68ca8889e.png",
                "description": "Generated raster inset: Marmaridae revolt near Cyrene.",
            },
            {
                "path": str(GALATIAN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e8458-df5c-75e1-b6dd-26109f659600/ig_0638aef7a576ce49016a1dca7949948191bf0a29018ca9408c.png",
                "description": "Generated raster inset: Galatian mercenaries conveyed by river to a deserted Nile island.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_7_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "7" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
