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

from PIL import Image, ImageDraw

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
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    make_compact_callout,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.13.5"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_5"
MAIN_ART = ASSET_DIR / "main_leuctra.png"
LOCATOR_ART = ASSET_DIR / "greece_relief.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def draw_map_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    index: int,
) -> None:
    draw = ImageDraw.Draw(panel)
    endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
    if rect[0] <= point[0] <= rect[2]:
        endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
    draw_leader(draw, point, endpoint)
    draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill="#754332")
    draw.rounded_rectangle(rect, radius=6, fill="#f4dfb2", outline="#8d693f", width=1)
    records.append(
        draw_fitted_text(
            draw,
            rect,
            text,
            DISPLAY_FONT,
            max_size=8,
            min_size=6,
            padding=3,
            name=f"locator:label:{index}",
            align="center",
            spacing_ratio=0.04,
        )
    )


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((408, 332))
    draw = ImageDraw.Draw(panel)
    title = (18, 14, panel.width - 18, 56)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "THREE TESTS OF SPARTAN ARMS",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    rect = (22, 70, panel.width - 22, 236)
    art = warm_art(
        crop_to_fill(LOCATOR_ART, (rect[2] - rect[0], rect[3] - rect[1]), centering=(0.49, 0.50)),
        grain_strength=0.012,
    )
    panel.paste(art, rect[:2])
    draw.rounded_rectangle(rect, radius=12, outline="#8d693f", width=2)

    # Points are measured against the generated oblique relief crop.
    draw_map_label(panel, records, "SPHACTERIA", (28, 177, 112, 200), (94, 183), 0)
    draw_map_label(panel, records, "SPARTA", (206, 200, 272, 223), (238, 195), 1)
    draw_map_label(panel, records, "LEUCTRA", (264, 111, 335, 134), (284, 142), 2)
    draw_map_label(panel, records, "THERMOPYLAE", (287, 76, 382, 99), (323, 112), 3)

    records.append(
        draw_fitted_text(
            draw,
            (24, 248, panel.width - 24, panel.height - 14),
            "Thermopylae and Sphacteria were explained away; Leuctra ended the claim that Spartan infantry had never been beaten.",
            BODY_FONT,
            max_size=11,
            min_size=8,
            padding=5,
            name="locator:caption",
            align="center",
            spacing_ratio=0.08,
        )
    )
    return panel


def add_tree_box(
    draw: ImageDraw.ImageDraw,
    records: list[FitRecord],
    name: str,
    note: str,
    rect: tuple[int, int, int, int],
    index: int,
) -> None:
    draw.rounded_rectangle(rect, radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
    records.append(
        draw_fitted_text(
            draw,
            (rect[0] + 4, rect[1] + 3, rect[2] - 4, rect[1] + 23),
            name,
            DISPLAY_FONT,
            max_size=9,
            min_size=6,
            padding=1,
            name=f"succession:name:{index}",
            align="center",
            spacing_ratio=0.04,
        )
    )
    records.append(
        draw_fitted_text(
            draw,
            (rect[0] + 5, rect[1] + 22, rect[2] - 5, rect[3] - 3),
            note,
            BODY_FONT,
            max_size=9,
            min_size=7,
            padding=1,
            name=f"succession:note:{index}",
            align="center",
            spacing_ratio=0.05,
        )
    )


def make_succession_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 332))
    draw = ImageDraw.Draw(panel)
    title = (24, 16, panel.width - 24, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "A CONTESTED SUCCESSION",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="succession:title",
            align="center",
            spacing_ratio=0.06,
        )
    )

    cleomenes = (136, 72, 316, 116)
    acrotatus = (28, 152, 204, 198)
    cleonymus = (248, 152, 424, 198)
    areus = (28, 236, 204, 282)
    draw.line((226, 116, 226, 132), fill="#815b36", width=3)
    draw.line((116, 132, 336, 132), fill="#815b36", width=3)
    draw.line((116, 132, 116, 152), fill="#815b36", width=3)
    draw.line((336, 132, 336, 152), fill="#815b36", width=3)
    draw.line((116, 198, 116, 236), fill="#815b36", width=3)
    draw.polygon([(110, 228), (122, 228), (116, 236)], fill="#815b36")

    boxes = [
        ("CLEOMENES", "king of Sparta", cleomenes),
        ("ACROTATUS", "elder son; died first", acrotatus),
        ("CLEONYMUS", "younger son; claimed throne", cleonymus),
        ("AREUS", "Acrotatus' son; rival claimant", areus),
    ]
    for index, (name, note, rect) in enumerate(boxes):
        add_tree_box(draw, records, name, note, rect, index)
    records.append(
        draw_fitted_text(
            draw,
            (224, 224, 428, 294),
            "Cleonymus answered Areus' succession by bringing Pyrrhus into Laconia.",
            BODY_FONT,
            max_size=10,
            min_size=7,
            padding=5,
            name="succession:result",
            align="center",
            spacing_ratio=0.07,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, LOCATOR_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    main_rect = (430, 36, 1374, 628)
    art = warm_art(
        crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.52)),
        grain_strength=0.012,
    )
    main_panel = framed_panel((art.width + 28, art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + art.width, 14 + art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left = framed_panel((378, 706))
    left_draw = ImageDraw.Draw(left)
    title_band = (18, 14, left.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.13.5",
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
            (24, 92, left.width - 24, left.height - 24),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left, (32, 36))

    title_rect = (634, 54, 1260, 116)
    paste_with_shadow(
        page,
        make_label("THE DAY SPARTA'S CLAIM BROKE", title_rect, records, font_path=TITLE_FONT, max_size=20, min_size=10),
        title_rect[:2],
    )
    labels = [
        ("THEBAN DEEP COLUMN", (470, 318, 666, 362), (694, 500)),
        ("SPARTAN RIGHT", (1128, 382, 1302, 426), (1110, 510)),
        ("LEUCTRA", (824, 286, 942, 330), (844, 342)),
        ("MOUNT CITHAERON", (472, 170, 660, 214), (576, 246)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=BODY_FONT, max_size=11, min_size=7),
            rect[:2],
        )

    note1 = make_compact_callout(
        "Leuctra, 371 BCE: the massed Theban left broke the elite Spartan right.",
        (440, 86),
        "callout:leuctra",
        records,
        max_size=13,
    )
    draw_polyline_leader(draw, [(448, 652), (582, 592), (704, 518)])
    paste_with_shadow(page, note1, (448, 642))
    note2 = make_compact_callout(
        "For Pausanias, this was the defeat Spartan explanations could no longer dismiss.",
        (448, 86),
        "callout:claim",
        records,
        max_size=13,
    )
    draw_polyline_leader(draw, [(904, 652), (1040, 592), (1120, 526)])
    paste_with_shadow(page, note2, (904, 642))

    paste_with_shadow(page, make_locator_panel(records), (32, 780))

    spartans_crop = warm_art(
        crop_to_fill(MAIN_ART, (420, 202), source_box=(780, 420, 1536, 1050), centering=(0.50, 0.54)),
        grain_strength=0.014,
    )
    inset = make_inset_panel(
        spartans_crop,
        "Sparta remembered Thermopylae as victory and Sphacteria as stratagem; Leuctra left no such refuge.",
        92,
        "inset:spartan-caption",
        records,
    )
    paste_with_shadow(page, inset, (450, 780))
    inset_label = (532, 800, 792, 836)
    draw_leader(draw, (662, 914), (inset_label[0], inset_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("A DEFEAT THEY COULD NOT DISCOUNT", inset_label, records, font_path=BODY_FONT, max_size=10, min_size=7),
        inset_label[:2],
    )

    paste_with_shadow(page, make_succession_panel(records), (904, 780))
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
        "continuity_reference_pages": ["graphic_book/images/1/13/4.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f61c9-b2f9-7bc2-9bcc-8e541c40a395/exec-84f6d4ec-e88e-445b-a4e4-1146ff669f9d.png",
                "description": "Generated raster reconstruction of the Battle of Leuctra.",
            },
            {
                "path": str(LOCATOR_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f61c9-b2f9-7bc2-9bcc-8e541c40a395/exec-27a37ad7-43ef-489b-af08-447af8c07bad.png",
                "description": "Generated raster relief base for the battle-site locator.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_13_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/13/5.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
