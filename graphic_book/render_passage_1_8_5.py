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


PASSAGE_ID = "1.8.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_8_5"
MAIN_ART = ASSET_DIR / "main_agora_tyrannicides.png"
WORKSHOP_ART = ASSET_DIR / "sculptors_workshop.png"
RETURN_ART = ASSET_DIR / "return_procession.png"


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
    return ImageOps.fit(image.crop(crop_box), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


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


def make_route_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((378, 338))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "STATUES TAKEN AND RETURNED",
            TITLE_FONT,
            max_size=18,
            min_size=10,
            padding=6,
            name="route:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (28, 72, panel.width - 28, 232)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 22).convert("L")
    relief = ImageOps.autocontrast(relief)
    relief_rgb = ImageOps.colorize(relief, black="#8c8f71", white="#f3deaa")
    sea = Image.new("RGB", relief_rgb.size, "#7b9da0")
    mask = Image.new("L", relief_rgb.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 116), (72, 98), (122, 118), (160, 92), (210, 116), (322, 106), (322, 160), (0, 160)], fill=150)
    base = Image.composite(sea, relief_rgb, mask.filter(ImageFilter.GaussianBlur(9)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "ATHENS": (54, 152),
        "SARDIS": (126, 122),
        "SUSA": (250, 100),
        "ANTIOCH": (178, 148),
    }
    route_out = [points["ATHENS"], points["SARDIS"], points["SUSA"]]
    route_back = [points["SUSA"], points["ANTIOCH"], points["ATHENS"]]
    draw.line(route_out, fill="#7b493a", width=4)
    draw.line(route_back, fill="#365f6c", width=3)
    for x, y in route_out[1:]:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill="#7b493a")
    for x, y in route_back[1:]:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill="#365f6c")

    label_specs = [
        ("ATHENS", (44, 196, 118, 220), "route:athens"),
        ("SARDIS", (102, 84, 176, 108), "route:sardis"),
        ("PERSIA", (226, 62, 304, 86), "route:persia"),
        ("ANTIOCHUS", (150, 166, 260, 190), "route:antiochus"),
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

    caption = "Xerxes carried off the older bronzes; Antiochus later restored them to Athens."
    records.append(
        draw_fitted_text(
            draw,
            (22, 250, panel.width - 22, panel.height - 14),
            caption,
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=5,
            name="route:caption",
            align="center",
            spacing_ratio=0.12,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, WORKSHOP_ART, RETURN_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 622)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.56, 0.50))
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
            "PASSAGE 1.8.5",
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
    title_rect = (650, 54, 1038, 116)
    paste_with_shadow(
        page,
        make_label("THE TYRANNICIDES", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ACROPOLIS", (482, 132, 682, 180), (602, 148), 16),
        ("ATHENIAN AGORA", (586, 432, 854, 480), (720, 518), 15),
        ("HARMODIUS AND ARISTOGEITON", (984, 392, 1354, 440), (1128, 292), 13),
        ("SANCTUARY OF ARES NEARBY", (574, 540, 932, 588), (812, 386), 13),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    antiochus_note = make_compact_callout(
        "The monument's history turns the Agora into a memory map: seizure, absence, and restitution.",
        (438, 92),
        "callout:memory-map",
        records,
    )
    draw_polyline_leader(draw, [(930, 636), (1010, 550), (1128, 360)])
    paste_with_shadow(page, antiochus_note, (462, 634))

    sculptor_note = make_compact_callout(
        "Pausanias distinguishes Antenor's originals from later statues by Critius.",
        (414, 92),
        "callout:sculptors",
        records,
    )
    draw_polyline_leader(draw, [(956, 636), (908, 576), (812, 386)])
    paste_with_shadow(page, sculptor_note, (926, 634))

    route_panel = make_route_panel(records)
    paste_with_shadow(page, route_panel, (32, 736))

    workshop = crop_fraction(WORKSHOP_ART, (0.02, 0.04, 0.98, 0.88), (420, 220))
    workshop = warm_art(workshop, grain_strength=0.018)
    workshop_panel = make_inset_panel(
        workshop,
        "The passage preserves two sculptural moments: Antenor's originals and Critius' later group.",
        92,
        "inset:workshop-caption",
        records,
    )
    paste_with_shadow(page, workshop_panel, (440, 754))
    workshop_label = (526, 772, 776, 808)
    draw_leader(draw, (650, 864), (workshop_label[0], workshop_label[1] + 18))
    paste_with_shadow(page, make_label("ANTENOR AND CRITIUS", workshop_label, records, max_size=12, min_size=6), (workshop_label[0], workshop_label[1]))

    returned = crop_fraction(RETURN_ART, (0.00, 0.02, 1.00, 0.86), (420, 220))
    returned = warm_art(returned, grain_strength=0.018)
    return_panel = make_inset_panel(
        returned,
        "A later ruler returns the bronzes, making the statue group a civic trophy of recovery.",
        92,
        "inset:return-caption",
        records,
    )
    paste_with_shadow(page, return_panel, (936, 754))
    return_label = (1018, 772, 1288, 808)
    draw_leader(draw, (1138, 872), (return_label[0], return_label[1] + 18))
    paste_with_shadow(page, make_label("RETURNED TO ATHENS", return_label, records, max_size=12, min_size=6), (return_label[0], return_label[1]))

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
            "graphic_book/images/1/8/4.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ea33f-2602-7152-a358-0c33d5dd55b6/ig_0bac9ca00a155623016a25b238c93481918d674db05fd671d4.png",
                "description": "Generated raster main panel: Athenian Agora with Tyrannicides monument, Acropolis, and civic precinct.",
            },
            {
                "path": str(WORKSHOP_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ea33f-2602-7152-a358-0c33d5dd55b6/ig_0bac9ca00a155623016a25b2f6161c8191b2ca8d35b7b6ead4.png",
                "description": "Generated raster inset: sculptors' workshop evoking Antenor and Critius versions.",
            },
            {
                "path": str(RETURN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ea33f-2602-7152-a358-0c33d5dd55b6/ig_0bac9ca00a155623016a25b39777c481919fcd167407db19bf.png",
                "description": "Generated raster inset: return of captured civic bronzes toward Athens.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_8_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "8" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
