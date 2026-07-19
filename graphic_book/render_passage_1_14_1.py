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
    RULE,
    TITLE_FONT,
    WIDTH,
    add_border,
    draw_fitted_text,
    draw_leader,
    framed_panel,
    make_label,
    make_parchment,
    paste_with_shadow,
    root_dir,
)
from graphic_book.render_passage_1_10_1 import (
    crop_to_fill,
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.14.1"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_14_1"
MAIN_ART = ASSET_DIR / "main_enneakrounos_agora.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_text_panel(
    size: tuple[int, int],
    title: str,
    body: str,
    name: str,
    records: list[FitRecord],
    *,
    body_max_size: int = 12,
) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 62)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            title,
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name=f"{name}:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    records.append(
        draw_fitted_text(
            draw,
            (28, 78, panel.width - 28, panel.height - 24),
            body,
            BODY_FONT,
            max_size=body_max_size,
            min_size=8,
            padding=6,
            name=f"{name}:body",
            align="center",
            spacing_ratio=0.10,
        )
    )
    return panel


def make_orientation_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((474, 326))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 62)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "PAUSANIAS'S URBAN SEQUENCE",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="orientation:title",
            align="center",
            spacing_ratio=0.05,
        )
    )
    entries = [
        ("NEARBY", "Odeion | image of Dionysus"),
        ("BELOW", "Enneakrounos | natural spring"),
        ("ABOVE", "Demeter and Kore | Triptolemus"),
    ]
    for index, (relation, subject) in enumerate(entries):
        y0 = 78 + index * 72
        y1 = y0 + 58
        draw.rounded_rectangle((26, y0, 448, y1), radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (34, y0 + 5, 132, y1 - 5),
                relation,
                DISPLAY_FONT,
                max_size=11,
                min_size=7,
                padding=4,
                name=f"orientation:relation:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (142, y0 + 5, 438, y1 - 5),
                subject,
                BODY_FONT,
                max_size=11,
                min_size=8,
                padding=4,
                name=f"orientation:subject:{index}",
                align="center",
                spacing_ratio=0.05,
            )
        )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    if not MAIN_ART.exists():
        raise RuntimeError(f"Missing generated art asset: {MAIN_ART}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((378, 708))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 72)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.14.1",
            TITLE_FONT,
            max_size=28,
            min_size=18,
            padding=10,
            name="passage:title",
            align="center",
            spacing_ratio=0.07,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (26, 94, passage_panel.width - 26, passage_panel.height - 28),
            translation,
            BODY_FONT,
            max_size=16,
            min_size=9,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, passage_panel, (32, 30))

    art = warm_art(crop_to_fill(MAIN_ART, (944, 656), centering=(0.50, 0.51)), grain_strength=0.009)
    art_panel = framed_panel((972, 684))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 958, 670), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (416, 22))

    labels = [
        ("DEMETER AND KORE", (452, 48, 692, 94), (615, 242)),
        ("TRIPTOLEMUS", (706, 48, 902, 94), (786, 250)),
        ("ODEION | DIONYSUS", (1026, 54, 1348, 100), (1136, 330)),
        ("ACROPOLIS", (1160, 138, 1342, 184), (1230, 176)),
        ("ENNEAKROUNOS", (720, 602, 970, 652), (796, 520)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=13, min_size=8),
            rect[:2],
        )

    spring_panel = make_text_panel(
        (378, 326),
        "NINE SPOUTS, ONE SPRING",
        "Wells served households across Athens. Pausanias singles out Enneakrounos because it alone was a natural spring, monumentalized by Peisistratus.",
        "spring",
        records,
        body_max_size=13,
    )
    paste_with_shadow(page, spring_panel, (32, 770))

    paste_with_shadow(page, make_orientation_panel(records), (426, 770))

    transition_panel = make_text_panel(
        (466, 326),
        "FROM EPIRUS BACK TO ATHENS",
        "The fall of Epeirote power closes the preceding history. Pausanias then resumes the traveller's route: Odeion, fountain, temples, and finally the stories of Triptolemus.",
        "transition",
        records,
        body_max_size=12,
    )
    paste_with_shadow(page, transition_panel, (918, 770))

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
        "continuity_reference_pages": ["graphic_book/images/1/13/9.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f7b89-7fc9-76f3-a88f-6b0a8c2bf7bb/exec-eba12691-2df9-430f-9c6e-807dab99f2cb.png",
                "description": "Generated reconstruction of Enneakrounos, the sanctuaries above it, the nearby Odeion, and the Athenian skyline.",
            }
        ],
    }
    report_path = root_dir() / "tmp/passage_1_14_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/14/1.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
