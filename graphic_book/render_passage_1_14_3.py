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
from graphic_book.render_passage_1_10_1 import crop_to_fill, validate_fit_records, warm_art


PASSAGE_ID = "1.14.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_14_3"
MAIN_ART = ASSET_DIR / "main_eleusinion_dream.png"


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
    body_max_size: int = 13,
) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 64)
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
            (28, 80, panel.width - 28, panel.height - 24),
            body,
            BODY_FONT,
            max_size=body_max_size,
            min_size=9,
            padding=7,
            name=f"{name}:body",
            align="center",
            spacing_ratio=0.11,
        )
    )
    return panel


def make_traditions_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((468, 338))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 64)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "THREE POETIC TRADITIONS",
            TITLE_FONT,
            max_size=16,
            min_size=9,
            padding=6,
            name="route:title",
            align="center",
            spacing_ratio=0.06,
        )
    )
    entries = [
        ("MUSAEUS", "Triptolemus: child of Oceanus and Earth"),
        ("ORPHIC VERSES", "Dysaules: father of Eubouleus and Triptolemus"),
        ("CHOERILUS", "Triptolemus and Cercyon: brothers with different fathers"),
    ]
    for index, (place, event) in enumerate(entries):
        y0 = 82 + index * 76
        y1 = y0 + 60
        draw.rounded_rectangle((24, y0, 444, y1), radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw,
                (30, y0 + 5, 132, y1 - 5),
                place,
                DISPLAY_FONT,
                max_size=12,
                min_size=8,
                padding=4,
                name=f"traditions:source:{index}",
                align="center",
                spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (142, y0 + 5, 438, y1 - 5),
                event,
                BODY_FONT,
                max_size=11,
                min_size=8,
                padding=4,
                name=f"traditions:claim:{index}",
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

    passage_panel = framed_panel((390, 720))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.14.3",
            TITLE_FONT,
            max_size=27,
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
            (26, 96, passage_panel.width - 26, passage_panel.height - 28),
            translation,
            BODY_FONT,
            max_size=15,
            min_size=10,
            padding=8,
            name="passage:translation",
            spacing_ratio=0.11,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 24))

    art = warm_art(crop_to_fill(MAIN_ART, (930, 672), centering=(0.50, 0.50)), grain_strength=0.006)
    art_panel = framed_panel((958, 700))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 944, 686), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (424, 22))

    labels = [
        ("ATHENS: THE ACROPOLIS", (448, 48, 704, 94), (616, 252)),
        ("THE ELEUSINION", (1124, 48, 1352, 94), (1104, 168)),
        ("PAUSANIAS", (770, 620, 956, 670), (942, 514)),
        ("A DREAM FORBIDS DISCLOSURE", (1032, 620, 1354, 670), (1178, 382)),
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

    common_panel = make_text_panel(
        (390, 338),
        "THE COMMON THREAD",
        "The parentage of Triptolemus changes from poet to poet. What remains constant is the agricultural gift: after Kore's fate is revealed, Demeter grants the knowledge of sowing grain.",
        "common",
        records,
    )
    paste_with_shadow(page, common_panel, (28, 760))

    paste_with_shadow(page, make_traditions_panel(records), (424, 760))

    limit_panel = make_text_panel(
        (470, 338),
        "THE SACRED LIMIT",
        "Pausanias intended to describe the Athenian Eleusinion fully, but a vision in his dreams stopped him. He turns away from the sanctuary's restricted matters and records only what he judges proper for everyone to know.",
        "limit",
        records,
        body_max_size=12,
    )
    paste_with_shadow(page, limit_panel, (912, 760))

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
        "continuity_reference_pages": ["graphic_book/images/1/14/2.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f85d6-d00a-70a2-b958-f9571dae05d1/exec-19001c91-e206-4d6a-9130-9199b8469683.png",
                "description": "Generated nocturnal reconstruction of Pausanias halted by a sacred dream at the Athenian Eleusinion, with the Acropolis providing geographic orientation.",
            }
        ],
    }
    report_path = root_dir() / "tmp/passage_1_14_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/14/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
