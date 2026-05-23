#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pausanias_db import connect

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

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


PASSAGE_ID = "1.5.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_5_2"
MAIN_ART = ASSET_DIR / "main_eponymous_heroes.png"
LEOS_ART = ASSET_DIR / "leos_daughters_oracle.png"
ERECHTHEUS_ART = ASSET_DIR / "erechtheus_eleusinians.png"


def load_translation() -> str:
    with connect() as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = %s",
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


def warm_art(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Sharpness(image).enhance(1.025)
    wash = Image.new("RGB", image.size, "#e2c38c")
    image = Image.blend(image, wash, 0.055)
    grain = Image.effect_noise(image.size, 4).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#9a7244", white="#fff1ce")
    return Image.blend(image, grain_rgb, 0.026)


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


def make_lineage_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 270))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 54)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "HEROIC LINES",
            TITLE_FONT,
            max_size=21,
            min_size=14,
            padding=6,
            name="lineage:title",
            align="center",
            spacing_ratio=0.08,
        )
    )
    items = [
        "Poseidon line: Hippothoon, Aegeus",
        "Herakles line: Antiochos",
        "Salamis: Ajax son of Telamon",
        "Civic crisis: Leos and his daughters",
        "Eleusis war: Erechtheus and Immarados",
        "Theseid line: Akamas",
    ]
    y = 72
    for idx, item in enumerate(items, start=1):
        draw.ellipse((24, y + 4, 36, y + 16), fill="#7d5430", outline="#f0d492", width=1)
        records.append(
            draw_fitted_text(
                draw,
                (46, y - 4, panel.width - 20, y + 25),
                item,
                BODY_FONT,
                max_size=14,
                min_size=10,
                padding=2,
                name=f"lineage:item:{idx}",
                spacing_ratio=0.09,
            )
        )
        y += 31
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for path in [MAIN_ART, LEOS_ART, ERECHTHEUS_ART]:
        if not path.exists():
            raise RuntimeError(f"Missing generated art asset: {path}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 640)
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

    left_panel_rect = (32, 36, 406, 724)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.5.2",
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
    title_rect = (644, 54, 1208, 118)
    paste_with_shadow(
        page,
        make_label("THE EPONYMOUS HEROES", title_rect, records, font_path=TITLE_FONT, max_size=25, min_size=14),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ACROPOLIS", (1034, 146, 1214, 196), (1092, 194)),
        ("ATHENIAN AGORA", (1110, 522, 1346, 574), (1196, 548)),
        ("THOLOS", (962, 394, 1110, 444), (1018, 432)),
        ("BOULEUTERION", (1186, 374, 1360, 424), (1224, 414)),
        ("EPONYMOUS HEROES", (510, 398, 824, 452), (690, 448)),
        ("TEN TRIBES", (698, 506, 896, 556), (762, 520)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=22, min_size=11), (rect[0], rect[1]))

    lineage_key = make_lineage_key(records)
    paste_with_shadow(page, lineage_key, (32, 748))

    note = make_compact_callout(
        "The statue row makes myth, kinship, and civic memory into a public map.",
        (374, 78),
        "callout:monument-function",
        records,
    )
    paste_with_shadow(page, note, (32, 1028))
    draw_polyline_leader(draw, [(406, 1062), (504, 918), (670, 444)])

    leos_art = warm_art(crop_to_fill(LEOS_ART, (398, 222), centering=(0.48, 0.50)))
    leos_panel = make_inset_panel(
        leos_art,
        "Leos' daughters mark the oracle-driven offering for the common safety of Athens.",
        92,
        "caption:leos",
        records,
    )
    paste_with_shadow(page, leos_panel, (438, 714))
    paste_with_shadow(page, make_label("LEOS' DAUGHTERS", (528, 732, 766, 780), records, max_size=20, min_size=12), (528, 732))
    draw_leader(draw, (648, 812), (648, 778))

    erechtheus_art = warm_art(crop_to_fill(ERECHTHEUS_ART, (414, 222), centering=(0.50, 0.52)))
    erechtheus_panel = make_inset_panel(
        erechtheus_art,
        "Erechtheus defeats the Eleusinians and kills Immarados, son of Eumolpos.",
        92,
        "caption:erechtheus",
        records,
    )
    paste_with_shadow(page, erechtheus_panel, (902, 714))
    paste_with_shadow(page, make_label("ERECHTHEUS", (1026, 732, 1226, 780), records, max_size=22, min_size=12), (1026, 732))
    draw_leader(draw, (1126, 812), (1126, 778))

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
    }
    report_path = root_dir() / "tmp" / "passage_1_5_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "5" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
