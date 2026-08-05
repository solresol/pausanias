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
    FitRecord,
    HEIGHT,
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
    validate_fit_records,
    warm_art,
)


PASSAGE_ID = "1.17.4"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_17_4"
MAIN_ART = ASSET_DIR / "main_cichyrus.png"
BATTLE_ART = ASSET_DIR / "battle_collapse.png"
APPROACH_ART = ASSET_DIR / "cichyrus_approach.png"
MAP_ART = ASSET_DIR / "epirus_relief.png"


def load_translation() -> str:
    """Load the exact English translation from the requested local database."""
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def leader_endpoint(
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
) -> tuple[int, int]:
    """Return a nearby label edge for a semantic leader."""
    endpoint = (
        rect[0] if point[0] < rect[0] else rect[2],
        (rect[1] + rect[3]) // 2,
    )
    if rect[0] <= point[0] <= rect[2]:
        endpoint = (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return endpoint


def add_panel_label(
    panel: Image.Image,
    records: list[FitRecord],
    text: str,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
    *,
    max_size: int = 9,
    min_size: int = 7,
) -> None:
    """Draw a fitted label and semantic leader inside an inset."""
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    label = make_label(
        text,
        rect,
        records,
        font_path=TITLE_FONT,
        max_size=max_size,
        min_size=min_size,
    )
    panel.alpha_composite(label, rect[:2])


def make_battle_panel(records: list[FitRecord]) -> Image.Image:
    """Build the failed-expedition battle inset."""
    art = warm_art(
        crop_to_fill(BATTLE_ART, (390, 280), centering=(0.50, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "A Thesprotian counterattack breaks the invading column in the river valley.",
        58,
        "battle:caption",
        records,
    )
    add_panel_label(panel, records, "THESPROTIAN ADVANCE", (12, 30, 176, 68), (132, 126))
    add_panel_label(panel, records, "RETREAT", (298, 202, 414, 240), (304, 184))
    return panel


def make_approach_panel(records: list[FitRecord]) -> Image.Image:
    """Build the reconstructed settlement approach inset."""
    art = warm_art(
        crop_to_fill(APPROACH_ART, (390, 280), centering=(0.52, 0.50)),
        grain_strength=0.006,
    )
    panel = make_inset_panel(
        art,
        "Cichyrus is reconstructed as a defended hill settlement above the Acheron plain.",
        58,
        "approach:caption",
        records,
    )
    add_panel_label(panel, records, "CICHYRUS", (276, 30, 414, 68), (292, 100))
    add_panel_label(panel, records, "RIVER PLAIN", (12, 202, 142, 240), (104, 172))
    add_panel_label(panel, records, "GATE ROAD", (264, 202, 414, 240), (312, 186))
    return panel


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build a rich, subordinate regional orientation inset."""
    art = warm_art(
        crop_to_fill(MAP_ART, (438, 280), centering=(0.50, 0.50)),
        grain_strength=0.004,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    athens = (352, 202)
    cichyrus = (116, 82)
    route = [athens, (306, 178), (258, 152), (208, 126), (160, 100), cichyrus]
    draw.line(route, fill="#f6e2ad", width=6)
    draw.line(route, fill=RULE, width=2)
    for point in (athens, cichyrus):
        draw.ellipse(
            (point[0] - 6, point[1] - 6, point[0] + 6, point[1] + 6),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "The failed expedition runs from Attica toward Thesprotia in north-west Greece.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "THESPROTIA", (12, 30, 132, 68), (134, 100))
    add_panel_label(panel, records, "CICHYRUS", (12, 202, 124, 240), (134, 100))
    add_panel_label(panel, records, "ATHENS", (350, 202, 462, 240), (370, 220))
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, BATTLE_ART, APPROACH_ART, MAP_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(
        title_rect,
        radius=12,
        fill="#ead2a0",
        outline=RULE,
        width=2,
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.17.4",
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
            (28, 92, passage_panel.width - 28, 432),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=11,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.10,
        )
    )

    note_rect = (24, 454, 346, 586)
    passage_draw.rounded_rectangle(
        note_rect,
        radius=12,
        fill="#f0ddb5",
        outline="#a57a44",
        width=2,
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "Pausanias calls this the most credible of several contradictory accounts. The court and fortification shown here are a reconstruction, not an excavated plan.",
            BODY_FONT,
            max_size=12,
            min_size=9,
            padding=10,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.09,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (38, 604, 332, 640),
            "THESPROTIA · CICHYRUS / EPHYRA",
            TITLE_FONT,
            max_size=10,
            min_size=7,
            padding=4,
            name="passage:orientation",
            align="center",
            spacing_ratio=0.04,
        )
    )
    paste_with_shadow(page, passage_panel, (28, 22))

    art = warm_art(
        crop_to_fill(MAIN_ART, (940, 622), centering=(0.50, 0.50)),
        grain_strength=0.005,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (714, 40, 1080, 98)
    paste_with_shadow(
        page,
        make_label(
            "CAPTURED AT CICHYRUS",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=20,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("THESEUS", (448, 126, 590, 170), (796, 336)),
        ("PIRITHOUS", (448, 438, 616, 482), (942, 350)),
        ("THESPROTIAN KING", (1120, 126, 1334, 170), (1192, 218)),
        ("BOUND WRISTS", (1058, 438, 1260, 482), (860, 430)),
        ("FORTIFIED GATE", (1100, 548, 1308, 592), (1020, 114)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(
                text,
                rect,
                records,
                font_path=TITLE_FONT,
                max_size=10,
                min_size=7,
            ),
            rect[:2],
        )

    orientation_rect = (706, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "THE FAILED EXPEDITION ENDS IN CAPTURE BEFORE THE THESPROTIAN KING",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_battle_panel(records), (28, 700))
    paste_with_shadow(page, make_approach_panel(records), (462, 700))
    paste_with_shadow(page, make_map_panel(records), (896, 700))

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)
    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "translation_font_size": next(
            record.font_size
            for record in records
            if record.name == "passage:translation"
        ),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/17/3.png"],
        "evidence_boundary": "The royal court, fortification, garments, and battle arrangement are reconstructed; no excavated plan is claimed.",
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd316-4d0a-7431-b880-fbb79df0a341/exec-7109ac5b-942c-4923-a7d8-492c0b6caf4c.png",
                "description": "Generated reconstruction of Theseus and Pirithous captive before the Thesprotian king at Cichyrus.",
            },
            {
                "path": str(BATTLE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd316-4d0a-7431-b880-fbb79df0a341/exec-f71ac21e-6305-408b-8b29-c16398a7bce6.png",
                "description": "Generated reconstruction of the Thesprotian counterattack and invading army's collapse.",
            },
            {
                "path": str(APPROACH_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd316-4d0a-7431-b880-fbb79df0a341/exec-dc589aa1-c3e4-469d-b1ca-6780591da24c.png",
                "description": "Generated landscape reconstruction of a fortified Cichyrus above the Acheron plain.",
            },
            {
                "path": str(MAP_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019fd316-4d0a-7431-b880-fbb79df0a341/exec-18834564-ad70-4bf8-b97b-bf4571f18236.png",
                "description": "Generated textured Greek relief base used only as a subordinate orientation inset.",
            },
        ],
    }
    report_path = root_dir() / "tmp/passage_1_17_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/17/4.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
