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


PASSAGE_ID = "1.13.9"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_13_9"
MAIN_ART = ASSET_DIR / "main_three_aeacids.png"
COURT_ART = ASSET_DIR / "court_historian.png"


def load_translation() -> str:
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_aeacid_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((378, 330))
    draw = ImageDraw.Draw(panel)
    title = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw, title, "THE THREE AEACIDS", TITLE_FONT,
            max_size=16, min_size=9, padding=6,
            name="aeacids:title", align="center", spacing_ratio=0.06,
        )
    )
    entries = [
        ("ACHILLES", "Son of Peleus | Troy | Paris and Apollo"),
        ("NEOPTOLEMUS", "Son of Achilles; also called Pyrrhus | Delphi | Pythian oracle"),
        ("PYRRHUS OF EPIRUS", "Aeacid king | Argos | Argive account and Demeter"),
    ]
    for index, (name, note) in enumerate(entries):
        y0 = 72 + index * 78
        y1 = y0 + 66
        draw.ellipse((22, y0 + 12, 62, y0 + 52), fill="#d2ad70", outline="#795331", width=2)
        records.append(
            draw_fitted_text(
                draw, (22, y0 + 12, 62, y0 + 52), str(index + 1), TITLE_FONT,
                max_size=15, min_size=9, padding=8,
                name=f"aeacids:number:{index}", align="center", spacing_ratio=0.04,
            )
        )
        draw.rounded_rectangle((72, y0, 354, y1), radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw, (80, y0 + 4, 346, y0 + 28), name, DISPLAY_FONT,
                max_size=10, min_size=7, padding=2,
                name=f"aeacids:name:{index}", align="center", spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw, (82, y0 + 29, 344, y1 - 4), note, BODY_FONT,
                max_size=9, min_size=7, padding=3,
                name=f"aeacids:note:{index}", align="center", spacing_ratio=0.05,
            )
        )
    return panel


def make_court_panel(records: list[FitRecord]) -> Image.Image:
    art = warm_art(crop_to_fill(COURT_ART, (464, 222), centering=(0.50, 0.53)), grain_strength=0.012)
    panel = make_inset_panel(
        art,
        "Hieronymus wrote close to Antigonus: Pausanias warns that royal proximity bends the record toward praise.",
        76,
        "court:caption",
        records,
    )
    draw = ImageDraw.Draw(panel)
    labels = [
        ("COURT HISTORIAN", (26, 28, 154, 56), (160, 124)),
        ("ROYAL PATRON", (328, 36, 454, 64), (360, 104)),
        ("CAMPAIGN RECORD", (232, 174, 382, 202), (296, 174)),
    ]
    for text, rect, point in labels:
        endpoint = (rect[0] if point[0] < rect[0] else rect[2], (rect[1] + rect[3]) // 2)
        if rect[0] <= point[0] <= rect[2]:
            endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
        draw_leader(draw, point, endpoint)
        panel.alpha_composite(
            make_label(text, rect, records, font_path=BODY_FONT, max_size=8, min_size=6),
            rect[:2],
        )
    return panel


def make_historiography_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((420, 330))
    draw = ImageDraw.Draw(panel)
    title = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw, title, "WHO CONTROLS THE RECORD?", TITLE_FONT,
            max_size=15, min_size=8, padding=6,
            name="history:title", align="center", spacing_ratio=0.06,
        )
    )
    entries = [
        ("ARGOS & LYCEAS", "Local memory preserves divine intervention and the death site."),
        ("HIERONYMUS", "A king's associate writes what pleases Antigonus."),
        ("PHILISTUS", "Hope of return to Syracuse concealed Dionysius's impiety."),
        ("PAUSANIAS", "Conflicting accounts reveal the pressure of patronage."),
    ]
    for index, (heading, note) in enumerate(entries):
        y0 = 70 + index * 60
        y1 = y0 + 50
        draw.rounded_rectangle((22, y0, 398, y1), radius=8, fill="#f4dfb2", outline="#9c7443", width=2)
        records.append(
            draw_fitted_text(
                draw, (28, y0 + 3, 148, y1 - 3), heading, DISPLAY_FONT,
                max_size=9, min_size=6, padding=3,
                name=f"history:heading:{index}", align="center", spacing_ratio=0.04,
            )
        )
        records.append(
            draw_fitted_text(
                draw, (154, y0 + 3, 392, y1 - 3), note, BODY_FONT,
                max_size=9, min_size=7, padding=3,
                name=f"history:note:{index}", align="center", spacing_ratio=0.05,
            )
        )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in (MAIN_ART, COURT_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    left = framed_panel((378, 706))
    left_draw = ImageDraw.Draw(left)
    title_band = (18, 14, left.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw, title_band, "PASSAGE 1.13.9", TITLE_FONT,
            max_size=29, min_size=18, padding=10,
            name="panel:title", align="center", spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            left_draw, (24, 92, left.width - 24, left.height - 24), translation, BODY_FONT,
            max_size=15, min_size=8, padding=8,
            name="panel:translation", spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left, (32, 36))

    main_rect = (430, 36, 1374, 628)
    art = warm_art(crop_to_fill(MAIN_ART, (944, 592), centering=(0.50, 0.50)), grain_strength=0.010)
    main_panel = framed_panel((972, 620), fill=PARCHMENT_DEEP)
    main_panel.paste(art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 958, 606), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (416, 22))

    location_labels = [
        ("TROY", (500, 52, 650, 94)),
        ("DELPHI", (792, 52, 972, 94)),
        ("ARGOS", (1122, 52, 1290, 94)),
        ("ACHILLES", (502, 558, 660, 604)),
        ("NEOPTOLEMUS — PYRRHUS", (704, 552, 1020, 608)),
        ("PYRRHUS OF EPIRUS", (1062, 552, 1354, 608)),
    ]
    for text, rect in location_labels:
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=15, min_size=8),
            rect[:2],
        )

    callouts = [
        ("Paris's arrow and Apollo's agency place Achilles's death under divine intervention.", (430, 646), (300, 82), "callout:troy"),
        ("At Delphi the Pythian oracle foretold the death of Achilles's son Neoptolemus.", (752, 646), (300, 82), "callout:delphi"),
        ("At Argos Pyrrhus of Epirus was buried where Argive memory placed Demeter's act.", (1074, 646), (300, 82), "callout:argos"),
    ]
    for text, xy, size, name in callouts:
        paste_with_shadow(page, make_compact_callout(text, size, name, records, max_size=12), xy)

    paste_with_shadow(page, make_aeacid_panel(records), (32, 780))
    paste_with_shadow(page, make_court_panel(records), (416, 780))
    paste_with_shadow(page, make_historiography_panel(records), (950, 780))
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
        "continuity_reference_pages": ["graphic_book/images/1/13/8.png"],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f7663-f94a-7f13-8cbd-434f41a5bceb/exec-01874143-2e09-4ebc-8299-8a9348055a50.png",
                "description": "Generated triptych of the three Aeacid deaths at Troy, Delphi, and Argos.",
            },
            {
                "path": str(COURT_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019f7663-f94a-7f13-8cbd-434f41a5bceb/exec-b2032f20-6ac9-408e-82d7-c0e494e3d2a1.png",
                "description": "Generated reconstruction of a Hellenistic historian writing under royal observation.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_13_9_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/13/9.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
