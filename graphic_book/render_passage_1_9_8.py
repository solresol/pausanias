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


PASSAGE_ID = "1.9.8"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_9_8"
MAIN_ART = ASSET_DIR / "main_epirote_tombs_inquiry.png"
CARDIA_ART = ASSET_DIR / "cardia_lysimacheia_inset.png"


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
    image = ImageEnhance.Color(image).enhance(0.96)
    image = ImageEnhance.Sharpness(image).enhance(1.02)
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
            "EPIRUS TO THE CHERSONESE",
            TITLE_FONT,
            max_size=16,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 76, panel.width - 30, 232)
    relief = Image.effect_noise((map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), 31).convert("L")
    relief = ImageOps.autocontrast(relief)
    land = ImageOps.colorize(relief, black="#786940", white="#efd7a0")
    sea_noise = Image.effect_noise(land.size, 18).convert("L")
    sea = ImageOps.colorize(ImageOps.autocontrast(sea_noise), black="#426a75", white="#9db8b3")
    mask = Image.new("L", land.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon([(0, 0), (126, 0), (112, 58), (74, 112), (0, 156)], fill=230)
    mdraw.polygon([(176, 22), (318, 8), (318, 86), (230, 80), (192, 58)], fill=226)
    mdraw.polygon([(196, 94), (318, 108), (318, 156), (166, 156), (142, 132)], fill=220)
    base = Image.composite(land, sea, mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.055)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 62, map_rect[1] + 116),
        "MACEDON": (map_rect[0] + 112, map_rect[1] + 72),
        "CARDIA": (map_rect[0] + 222, map_rect[1] + 88),
        "LYSIMACHEIA": (map_rect[0] + 252, map_rect[1] + 112),
    }
    route = [points["EPIRUS"], points["MACEDON"], (map_rect[0] + 172, map_rect[1] + 78), points["CARDIA"], points["LYSIMACHEIA"]]
    draw.line(route, fill="#7b493a", width=4)
    draw.line(route, fill="#f4ead6", width=1)
    draw.line((map_rect[0] + 178, map_rect[1] + 102, map_rect[0] + 304, map_rect[1] + 104), fill="#486b72", width=3)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    labels = [
        ("EPIRUS", (46, 174, 118, 198), "locator:epirus"),
        ("MACEDON", (94, 120, 182, 144), "locator:macedon"),
        ("CARDIA", (216, 130, 286, 154), "locator:cardia"),
        ("LYSIMACHEIA", (214, 184, 328, 208), "locator:lysimacheia"),
        ("AEGEAN", (144, 184, 210, 208), "locator:aegean"),
    ]
    for text, rect, name in labels:
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

    caption = "The rejected tomb story points west to Epirus, while Hieronymus' real grievance leads east to Cardia and Lysimacheia."
    records.append(
        draw_fitted_text(
            draw,
            (22, 260, panel.width - 22, panel.height - 14),
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


def make_evidence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "PAUSANIAS WEIGHS THE STORY",
            TITLE_FONT,
            max_size=14,
            min_size=8,
            padding=6,
            name="evidence:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    rows = [
        ("CHARGE", "Hieronymus says Lysimachus broke open Epirote tombs."),
        ("REBUTTAL", "Pausanias calls the tale slander, not sober history."),
        ("KINSHIP", "Aeacid ancestry links Pyrrhus and Alexander through Epirus."),
        ("GRIEVANCE", "Cardia's destruction better explains the hostile account."),
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
        name_rect = (34, y + 7, 150, y + 45)
        note_rect = (164, y + 6, panel.width - 34, y + 46)
        records.append(
            draw_fitted_text(
                draw,
                name_rect,
                name,
                DISPLAY_FONT,
                max_size=12,
                min_size=7,
                padding=2,
                name=f"evidence:name:{idx}",
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
                name=f"evidence:note:{idx}",
                spacing_ratio=0.08,
            )
        )
        y += 58
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, CARDIA_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.56, 0.50))
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
            "PASSAGE 1.9.8",
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
            (24, 88, left_panel.width - 24, left_panel.height - 22),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=7,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.08,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (622, 54, 1194, 116)
    paste_with_shadow(
        page,
        make_label("THE SLANDER OF THE TOMBS", title_rect, records, font_path=TITLE_FONT, max_size=23, min_size=10),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("INTACT EPIROTE TOMBS", (876, 138, 1214, 184), (1004, 276), 17),
        ("HIERONYMUS' CHARGE", (478, 146, 782, 192), (664, 414), 17),
        ("PAUSANIAS REJECTS IT", (494, 520, 806, 566), (626, 360), 16),
        ("AEACID ANCESTRY", (1016, 506, 1294, 552), (1110, 350), 17),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    slander_note = make_compact_callout(
        "Pausanias treats the tomb violation as hostile invention, not a reliable deed of Lysimachus.",
        (420, 88),
        "callout:slander",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(468, 648), (594, 592), (626, 360)])
    paste_with_shadow(page, slander_note, (462, 642))

    kinship_note = make_compact_callout(
        "The tombs belonged to ancestors of Pyrrhus and, through Olympias, Alexander as well.",
        (458, 88),
        "callout:kinship",
        records,
        max_size=15,
    )
    draw_polyline_leader(draw, [(910, 648), (1040, 594), (1110, 350)])
    paste_with_shadow(page, kinship_note, (898, 642))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    cardia_crop = crop_to_fill(CARDIA_ART, (420, 210), centering=(0.50, 0.52))
    cardia_crop = warm_art(cardia_crop, grain_strength=0.018)
    cardia_panel = make_inset_panel(
        cardia_crop,
        "Hieronymus of Cardia had reason to resent Lysimachus: Cardia was erased and Lysimacheia founded on the Chersonese.",
        98,
        "inset:cardia-caption",
        records,
    )
    paste_with_shadow(page, cardia_panel, (440, 762))
    cardia_label = (526, 780, 800, 816)
    draw_leader(draw, (702, 900), (cardia_label[0], cardia_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("CARDIA TO LYSIMACHEIA", cardia_label, records, max_size=14, min_size=6),
        (cardia_label[0], cardia_label[1]),
    )

    evidence_panel = make_evidence_panel(records)
    paste_with_shadow(page, evidence_panel, (904, 758))

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
            "graphic_book/images/1/9/7.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ecc72-8827-7cc0-90a3-4426c04b8566/ig_0e6afe64642382b5016a303e7422e8819188f85e3aa4ff9842.png",
                "description": "Generated raster source; final page crops an intact Epirote tomb precinct with a scholar inspecting a disputed scroll.",
            },
            {
                "path": str(CARDIA_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019ecc72-8827-7cc0-90a3-4426c04b8566/ig_0e6afe64642382b5016a303f11522c8191938a99ef56441163.png",
                "description": "Generated raster scenic inset showing Cardia's loss and Lysimacheia's foundation on the Thracian Chersonese.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_9_8_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "9" / "8.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
