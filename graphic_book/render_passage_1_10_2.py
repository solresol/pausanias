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
from graphic_book.render_passage_1_10_1 import crop_to_fill, make_compact_callout, validate_fit_records, warm_art


PASSAGE_ID = "1.10.2"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_10_2"
MAIN_ART = ASSET_DIR / "main_amphipolis_campaign.png"
ASIA_ART = ASSET_DIR / "demetrius_asia_crossing.png"


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


def make_locator_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((388, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "EPIRUS, MACEDONIA, THRACE",
            TITLE_FONT,
            max_size=15,
            min_size=8,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 74, panel.width - 30, 230)
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    base = crop_to_fill(MAIN_ART, map_size, centering=(0.50, 0.42)).filter(ImageFilter.GaussianBlur(1.2))
    base = ImageEnhance.Contrast(base).enhance(0.78)
    base = ImageEnhance.Color(base).enhance(0.62)
    parchment_wash = Image.new("RGB", map_size, "#d9bc82")
    base = Image.blend(base, parchment_wash, 0.34)
    sea_mask = Image.new("L", map_size, 0)
    mdraw = ImageDraw.Draw(sea_mask)
    mdraw.polygon([(0, 126), (92, 112), (178, 122), (252, 112), (328, 120), (328, 156), (0, 156)], fill=140)
    sea = Image.new("RGB", map_size, "#496f78")
    base = Image.composite(sea, base, sea_mask.filter(ImageFilter.GaussianBlur(5)))
    base = warm_art(base, grain_strength=0.035)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "EPIRUS": (map_rect[0] + 56, map_rect[1] + 110),
        "PYRRHUS": (map_rect[0] + 92, map_rect[1] + 92),
        "AMPHIPOLIS": (map_rect[0] + 162, map_rect[1] + 86),
        "THRACE": (map_rect[0] + 250, map_rect[1] + 58),
        "ASIA": (map_rect[0] + 288, map_rect[1] + 128),
    }
    pyrrhus_route = [points["EPIRUS"], points["PYRRHUS"], points["AMPHIPOLIS"]]
    lysimachus_route = [points["THRACE"], points["AMPHIPOLIS"], (map_rect[0] + 130, map_rect[1] + 112)]
    asia_route = [points["AMPHIPOLIS"], (map_rect[0] + 230, map_rect[1] + 106), points["ASIA"]]
    draw.line(pyrrhus_route, fill="#4d5f5d", width=4)
    draw.line(lysimachus_route, fill="#7b493a", width=4)
    draw.line(asia_route, fill="#6e5f8a", width=3)
    draw.line((map_rect[0] + 28, map_rect[1] + 132, map_rect[0] + 306, map_rect[1] + 128), fill="#486b72", width=4)
    for x, y in points.values():
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#6a4d2d", outline="#f6e8c4", width=2)

    label_specs = [
        ("EPIRUS", (38, 178, 104, 202), "locator:epirus"),
        ("PYRRHUS", (70, 148, 148, 172), "locator:pyrrhus"),
        ("AMPHIPOLIS", (136, 138, 236, 162), "locator:amphipolis"),
        ("THRACE", (230, 116, 302, 140), "locator:thrace"),
        ("ASIA", (278, 190, 334, 214), "locator:asia"),
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

    caption = "The alliance first protects Thrace near Amphipolis, then breaks after Demetrius is overcome in Asia."
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


def make_sequence_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((452, 330))
    draw = ImageDraw.Draw(panel)
    title = (24, 18, panel.width - 24, 60)
    draw.rounded_rectangle(title, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title,
            "ALLIANCE TO VICTORY",
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
        ("AMPHIPOLIS", "Lysimachus nearly loses Thrace in the fight with Demetrius."),
        ("PYRRHUS", "Epirote support helps him retain Thrace for the moment."),
        ("ASIA", "Demetrius crosses east and is overcome by Seleucus."),
        ("MACEDONIA", "Lysimachus defeats Pyrrhus and Antigonus, claiming the kingdom."),
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
    for asset in [MAIN_ART, ASIA_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (430, 36, 1374, 628)
    main_art = crop_to_fill(
        MAIN_ART,
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.48, 0.45),
    )
    main_art = warm_art(ImageEnhance.Contrast(main_art).enhance(1.03))
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
            "PASSAGE 1.10.2",
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
            (24, 92, left_panel.width - 24, left_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=8,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (586, 54, 1248, 116)
    paste_with_shadow(
        page,
        make_label("AMPHIPOLIS AND THE BREAKING ALLIANCE", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=9),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("AMPHIPOLIS", (870, 148, 1078, 194), (1010, 270), 18),
        ("STRYMON CROSSING", (1020, 390, 1296, 436), (1032, 402), 16),
        ("THRACE HELD", (510, 154, 712, 200), (620, 380), 18),
        ("PYRRHUS' EPIROTES", (488, 548, 790, 594), (535, 454), 15),
        ("MACEDONIA CLAIMED", (1054, 548, 1336, 594), (1168, 326), 15),
    ]
    for text, rect, point, max_size in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=max_size, min_size=7), (rect[0], rect[1]))

    near_loss_note = make_compact_callout(
        "Near Amphipolis, Lysimachus comes close to losing Thrace before Pyrrhus' support steadies the campaign.",
        (450, 88),
        "callout:near-loss",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(462, 648), (620, 592), (620, 380)])
    paste_with_shadow(page, near_loss_note, (462, 642))

    victory_note = make_compact_callout(
        "Once Demetrius falls to Seleucus, the alliance breaks; Lysimachus defeats Pyrrhus and Antigonus.",
        (462, 90),
        "callout:victory",
        records,
        max_size=14,
    )
    draw_polyline_leader(draw, [(912, 648), (1102, 596), (1168, 326)])
    paste_with_shadow(page, victory_note, (898, 642))

    locator_panel = make_locator_panel(records)
    paste_with_shadow(page, locator_panel, (32, 758))

    asia_crop = crop_to_fill(ASIA_ART, (420, 198), centering=(0.66, 0.50))
    asia_crop = warm_art(asia_crop, grain_strength=0.018)
    asia_panel = make_inset_panel(
        asia_crop,
        "Demetrius crosses into Asia to fight Seleucus; after Seleucus overcomes him, Lysimachus and Pyrrhus no longer remain friends.",
        94,
        "inset:asia-caption",
        records,
    )
    paste_with_shadow(page, asia_panel, (440, 756))
    asia_label = (516, 774, 800, 810)
    draw_leader(draw, (706, 882), (asia_label[0], asia_label[1] + 18))
    paste_with_shadow(
        page,
        make_label("DEMETRIUS CROSSES TO ASIA", asia_label, records, max_size=13, min_size=6),
        (asia_label[0], asia_label[1]),
    )

    sequence_panel = make_sequence_panel(records)
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
            "graphic_book/images/1/10/1.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "graphic_book/assets/generated/1_9_6/main_danube_getae_campaign.png",
                "description": "Repo-local high-quality generated raster base reused for a river-frontier campaign scene and locally oriented as Amphipolis/Strymon.",
            },
            {
                "path": str(ASIA_ART),
                "source_image": "graphic_book/assets/generated/1_9_7/main_ephesus_harbor_refoundation.png",
                "description": "Repo-local high-quality generated raster base cropped as a scenic inset for Demetrius crossing into Asia and Seleucus' pressure.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_10_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "10" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
