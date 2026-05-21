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


PASSAGE_ID = "1.5.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_5_3"
MAIN_SOURCE = ASSET_DIR / "source_Kakiaskala03.jpg"
HEROES_ART = root_dir() / "graphic_book/assets/generated/1_5_2/main_eponymous_heroes.png"


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


def warm_art(image: Image.Image, *, grain_strength: float = 0.032) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = ImageEnhance.Color(image).enhance(0.82)
    image = ImageEnhance.Sharpness(image).enhance(1.12)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.10)

    edges = image.filter(ImageFilter.FIND_EDGES).convert("L")
    edges = ImageOps.autocontrast(edges)
    edge_rgb = ImageOps.colorize(edges, black="#2c2117", white="#d8bf88")
    image = Image.blend(image, edge_rgb, 0.035)

    grain = Image.effect_noise(image.size, 7).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8f6a3d", white="#fff1cf")
    return Image.blend(image, grain_rgb, grain_strength)


def crop_image_to_fill(image: Image.Image, size: tuple[int, int], centering: tuple[float, float]) -> Image.Image:
    return ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=centering)


def make_coast_art(size: tuple[int, int]) -> Image.Image:
    if not MAIN_SOURCE.exists():
        raise RuntimeError(f"Missing sourced coast image: {MAIN_SOURCE}")
    source = Image.open(MAIN_SOURCE).convert("RGB")
    # Favor the cliff, sea, and coastal rock so the panel reads as landscape, not modern infrastructure.
    art = crop_image_to_fill(source, size, centering=(0.56, 0.54))
    return warm_art(art, grain_strength=0.026)


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
    panel = framed_panel((382, 306))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "LINEAGE AND EXILE",
            TITLE_FONT,
            max_size=20,
            min_size=13,
            padding=6,
            name="route:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 74, panel.width - 28, 190)
    texture = Image.open(MAIN_SOURCE).convert("RGB").resize((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]))
    texture = warm_art(texture.filter(ImageFilter.GaussianBlur(1.4)), grain_strength=0.04)
    tint = Image.new("RGB", texture.size, "#ecd9b2")
    texture = Image.blend(texture, tint, 0.48)
    panel.paste(texture, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    athens = (92, 146)
    megara = (238, 126)
    euboea = (294, 96)
    tomb = (292, 156)
    draw.line([athens, megara, tomb], fill="#7d5430", width=5, joint="curve")
    draw.line([megara, euboea], fill="#9d6a3a", width=3)
    for point, color in [(athens, "#3f5f72"), (megara, "#7d5430"), (euboea, "#56715a"), (tomb, "#8c3d2e")]:
        draw.ellipse((point[0] - 8, point[1] - 8, point[0] + 8, point[1] + 8), fill=color, outline="#f5e3ba", width=2)

    label_specs = [
        ("ATHENS", (50, 98, 130, 124), "route:athens"),
        ("MEGARA", (204, 82, 282, 108), "route:megara"),
        ("EUBOEA", (280, 58, 354, 84), "route:euboea"),
        ("SEA-TOMB", (250, 164, 354, 190), "route:tomb"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=8, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=13,
                min_size=8,
                padding=3,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = (
        "Pausanias keeps both statue-honor and genealogy uncertain: two Cecrops figures, "
        "two Pandions, Euboean migration, and exile to Megara."
    )
    records.append(
        draw_fitted_text(
            draw,
            (24, 204, panel.width - 24, panel.height - 18),
            caption,
            BODY_FONT,
            max_size=16,
            min_size=11,
            padding=6,
            name="route:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_lineage_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 220))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 52)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "STATUES NAMED, HONOR UNCLEAR",
            TITLE_FONT,
            max_size=18,
            min_size=11,
            padding=5,
            name="lineage:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    items = [
        "Cecrops I: first king, son-in-law of Actaeus",
        "Cecrops II: linked to Euboea",
        "Pandion I: son of Erichthonius",
        "Pandion II: expelled; died in Megara",
    ]
    y = 68
    for idx, item in enumerate(items, start=1):
        draw.ellipse((24, y + 4, 36, y + 16), fill="#7d5430", outline="#f0d492", width=1)
        records.append(
            draw_fitted_text(
                draw,
                (46, y - 4, panel.width - 20, y + 27),
                item,
                BODY_FONT,
                max_size=14,
                min_size=10,
                padding=2,
                name=f"lineage:item:{idx}",
                spacing_ratio=0.09,
            )
        )
        y += 35
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not HEROES_ART.exists():
        raise RuntimeError(f"Missing continuity art asset: {HEROES_ART}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 650)
    main_art = make_coast_art((main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]))
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
            "PASSAGE 1.5.3",
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
            min_size=12,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.16,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (650, 54, 1216, 118)
    paste_with_shadow(
        page,
        make_label("PANDION AT MEGARA", title_rect, records, font_path=TITLE_FONT, max_size=26, min_size=14),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("MEGARID COAST", (1014, 142, 1270, 194), (1110, 278)),
        ("ATHENA AETHYIA ROCK", (512, 430, 838, 482), (704, 472)),
        ("PANDION'S SEA-TOMB", (840, 512, 1162, 566), (894, 542)),
        ("SKIRONIAN ROCKS", (520, 168, 792, 220), (662, 326)),
        ("ATHENS-MEGARA ROUTE", (958, 296, 1276, 348), (1030, 374)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=22, min_size=11), (rect[0], rect[1]))

    lineage = make_lineage_panel(records)
    paste_with_shadow(page, lineage, (32, 748))

    note = make_compact_callout(
        "The passage turns a statue row into a problem of memory: which Cecrops, which Pandion, and where the exiled king belongs.",
        (374, 118),
        "callout:memory-problem",
        records,
    )
    paste_with_shadow(page, note, (32, 988))
    draw_polyline_leader(draw, [(406, 1042), (536, 942), (710, 474)])

    heroes_art = warm_art(crop_to_fill(HEROES_ART, (418, 246), centering=(0.48, 0.52)))
    heroes_panel = make_inset_panel(
        heroes_art,
        "The eponymous-hero monument remains the Athenian starting point; Pausanias now questions which ancestral figures the statues honor.",
        104,
        "caption:heroes",
        records,
    )
    paste_with_shadow(page, heroes_panel, (434, 714))
    paste_with_shadow(page, make_label("EPONYMOUS HEROES", (524, 734, 772, 782), records, max_size=20, min_size=11), (524, 734))
    draw_leader(draw, (648, 812), (648, 780))

    route_key = make_route_key(records)
    paste_with_shadow(page, route_key, (948, 714))
    paste_with_shadow(page, make_label("ATHENS TO MEGARA", (1004, 734, 1290, 782), records, max_size=19, min_size=11), (1004, 734))
    draw_leader(draw, (1146, 812), (1146, 780))

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
                "path": str(MAIN_SOURCE),
                "description": "Kakiaskala03.jpg, Kakia Skalla / Skironian Rocks near Megara, Wikimedia Commons CC0",
            },
            {
                "path": str(HEROES_ART),
                "description": "Local generated continuity art from passage 1.5.2",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_5_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "5" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
