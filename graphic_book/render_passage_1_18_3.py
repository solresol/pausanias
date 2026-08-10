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
from graphic_book.render_passage_1_10_1 import crop_to_fill, validate_fit_records, warm_art


PASSAGE_ID = "1.18.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_18_3"
MAIN_ART = ASSET_DIR / "main_prytaneion.png"
REINSCRIBED_ART = ASSET_DIR / "reinscribed_statues.png"
AUTOLYKOS_ART = ASSET_DIR / "autolykos.png"
MAP_ART = ASSET_DIR / "central_athens_relief.png"


def load_translation() -> str:
    """Load the exact English translation from the requested local database."""
    with sqlite3.connect(root_dir() / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return row[0]


def leader_endpoint(
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
) -> tuple[int, int]:
    """Return the nearest suitable label edge for a semantic leader."""
    if rect[0] <= point[0] <= rect[2]:
        return (point[0], rect[1] if point[1] < rect[1] else rect[3])
    return (
        rect[0] if point[0] < rect[0] else rect[2],
        (rect[1] + rect[3]) // 2,
    )


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
    """Draw a measured label and semantic leader inside an inset."""
    draw = ImageDraw.Draw(panel)
    draw_leader(draw, point, leader_endpoint(rect, point))
    panel.alpha_composite(
        make_label(
            text,
            rect,
            records,
            font_path=TITLE_FONT,
            max_size=max_size,
            min_size=min_size,
        ),
        rect[:2],
    )


def make_reinscribed_panel(records: list[FitRecord]) -> Image.Image:
    """Build the altered-honorific-inscriptions inset."""
    art = warm_art(
        crop_to_fill(REINSCRIBED_ART, (390, 280), centering=(0.50, 0.56)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Old honorific statues survived, but their names were recut for new identities.",
        58,
        "reinscribed:caption",
        records,
    )
    add_panel_label(panel, records, "MILTIADES", (12, 30, 134, 68), (132, 144))
    add_panel_label(panel, records, "THEMISTOCLES", (258, 30, 414, 68), (288, 142))
    add_panel_label(panel, records, "RECUT INSCRIPTION", (128, 202, 300, 240), (186, 172))
    return panel


def make_autolykos_panel(records: list[FitRecord]) -> Image.Image:
    """Build the Autolykos honorific-statue inset."""
    art = warm_art(
        crop_to_fill(AUTOLYKOS_ART, (390, 280), centering=(0.55, 0.48)),
        grain_strength=0.004,
    )
    panel = make_inset_panel(
        art,
        "Autolykos, celebrated pancratiast, stood among the Prytaneion's civic honours.",
        58,
        "autolykos:caption",
        records,
    )
    add_panel_label(panel, records, "AUTOLYKOS", (262, 30, 414, 68), (270, 112))
    add_panel_label(panel, records, "PANCRATION WRAPS", (12, 202, 180, 240), (276, 184))
    return panel


def make_map_panel(records: list[FitRecord]) -> Image.Image:
    """Build the textured Athens orientation inset."""
    art = warm_art(
        crop_to_fill(MAP_ART, (438, 280), centering=(0.50, 0.52)),
        grain_strength=0.003,
    ).convert("RGBA")
    draw = ImageDraw.Draw(art)
    acropolis = (326, 82)
    agora = (232, 146)
    prytaneion_zone = (330, 190)
    civic_axis = [prytaneion_zone, (290, 174), agora]
    draw.line(civic_axis, fill="#f5dfad", width=7)
    draw.line(civic_axis, fill=RULE, width=2)
    for point in (acropolis, agora, prytaneion_zone):
        draw.ellipse(
            (point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
            fill="#e7bd63",
            outline=RULE,
            width=2,
        )
    panel = make_inset_panel(
        art,
        "Central Athens: the Prytaneion marker is a broad reconstructed zone, not a fixed footprint.",
        58,
        "map:caption",
        records,
    )
    add_panel_label(panel, records, "ACROPOLIS", (278, 30, 414, 68), acropolis)
    add_panel_label(panel, records, "AGORA", (12, 202, 126, 240), agora)
    add_panel_label(panel, records, "PRYTANEION ZONE", (246, 202, 430, 240), prytaneion_zone, max_size=8)
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    """Render, measure, validate, and save the illustrated passage page."""
    translation = load_translation()
    for asset in (MAIN_ART, REINSCRIBED_ART, AUTOLYKOS_ART, MAP_ART):
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    passage_panel = framed_panel((370, 650))
    passage_draw = ImageDraw.Draw(passage_panel)
    title_rect = (18, 14, passage_panel.width - 18, 74)
    passage_draw.rounded_rectangle(title_rect, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            title_rect,
            "PASSAGE 1.18.3",
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
            (28, 92, passage_panel.width - 28, 410),
            translation,
            BODY_FONT,
            max_size=20,
            min_size=12,
            padding=6,
            name="passage:translation",
            spacing_ratio=0.09,
        )
    )
    note_rect = (24, 430, 346, 586)
    passage_draw.rounded_rectangle(note_rect, radius=12, fill="#f0ddb5", outline="#a57a44", width=2)
    records.append(
        draw_fitted_text(
            passage_draw,
            note_rect,
            "The Prytaneion joined sacred fire, written law, and civic commemoration. Its plan, the placement of objects, the statues' appearance, and the precise location shown here are informed reconstructions rather than recovered arrangements.",
            BODY_FONT,
            max_size=12,
            min_size=8,
            padding=10,
            name="passage:evidence-note",
            align="center",
            spacing_ratio=0.08,
        )
    )
    records.append(
        draw_fitted_text(
            passage_draw,
            (38, 606, 332, 640),
            "ATHENS · PRYTANEION",
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
        grain_strength=0.004,
    )
    art_panel = framed_panel((968, 650))
    art_panel.paste(art, (14, 14))
    ImageDraw.Draw(art_panel).rectangle((14, 14, 954, 636), outline=RULE, width=2)
    paste_with_shadow(page, art_panel, (406, 22))

    heading_rect = (676, 40, 1124, 98)
    paste_with_shadow(
        page,
        make_label(
        "THE CIVIC HEARTH",
            heading_rect,
            records,
            font_path=TITLE_FONT,
            max_size=20,
            min_size=11,
        ),
        heading_rect[:2],
    )

    callouts = [
        ("SOLON'S WRITTEN LAWS", (438, 130, 650, 174), (600, 286)),
        ("HESTIA", (676, 118, 814, 162), (804, 310)),
        ("PEACE", (1012, 118, 1150, 162), (964, 304)),
        ("HONORIFIC GALLERY", (1144, 284, 1330, 328), (1196, 310)),
        ("PERPETUAL HEARTH", (712, 538, 900, 582), (918, 498)),
    ]
    for text, rect, point in callouts:
        draw_leader(draw, point, leader_endpoint(rect, point))
        paste_with_shadow(
            page,
            make_label(text, rect, records, font_path=TITLE_FONT, max_size=9, min_size=7),
            rect[:2],
        )

    orientation_rect = (660, 612, 1338, 654)
    paste_with_shadow(
        page,
        make_label(
            "LAW, SACRED FIRE, AND CIVIC MEMORY SHARED ONE INSTITUTION",
            orientation_rect,
            records,
            font_path=BODY_FONT,
            max_size=9,
            min_size=7,
        ),
        orientation_rect[:2],
    )

    paste_with_shadow(page, make_reinscribed_panel(records), (28, 700))
    paste_with_shadow(page, make_autolykos_panel(records), (462, 700))
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
            record.font_size for record in records if record.name == "passage:translation"
        ),
        "translation_matches_sqlite": translation == load_translation(),
        "fit_records": [asdict(record) for record in records],
        "page_plan": str(ASSET_DIR / "page_plan.md"),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "continuity_reference_pages": ["graphic_book/images/1/18/2.png"],
        "evidence_boundary": "The Prytaneion plan, object placement, statue appearances, and locator zone are reconstructed; the map does not claim a recovered footprint.",
        "sources": [
            {"path": str(MAIN_ART), "description": "Generated reconstruction of the Athenian Prytaneion interior."},
            {"path": str(REINSCRIBED_ART), "description": "Generated reconstruction of Roman-period statue re-inscription."},
            {"path": str(AUTOLYKOS_ART), "description": "Generated honorific-statue study of Autolykos."},
            {"path": str(MAP_ART), "description": "Generated textured central-Athens relief used only as a subordinate locator."},
        ],
    }
    report_path = root_dir() / "tmp/passage_1_18_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output = root_dir() / "graphic_book/images/1/18/3.png"
    print(json.dumps(render_page(output), indent=2))


if __name__ == "__main__":
    main()
