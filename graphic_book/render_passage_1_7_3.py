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


PASSAGE_ID = "1.7.3"
ASSET_DIR = root_dir() / "graphic_book/assets/generated/1_7_3"
MAIN_ART = ASSET_DIR / "main_eastern_mediterranean_campaign.png"
COUNCIL_ART = ASSET_DIR / "magas_apame_antiochus_council.png"
ARSINOITE_ART = ASSET_DIR / "arsinoite_nome.png"


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
    image = ImageEnhance.Color(image).enhance(0.94)
    image = ImageEnhance.Sharpness(image).enhance(1.04)
    wash = Image.new("RGB", image.size, "#dfbd82")
    image = Image.blend(image, wash, 0.035)
    grain = Image.effect_noise(image.size, 6).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8e693d", white="#fff1ce")
    return Image.blend(image, grain_rgb, grain_strength)


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
            min_size=9,
            padding=5,
            name=name,
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def make_locator_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((374, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=9, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "EASTERN THEATRE",
            TITLE_FONT,
            max_size=17,
            min_size=10,
            padding=6,
            name="locator:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (30, 72, panel.width - 30, 236)
    base = crop_to_fill(MAIN_ART, (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]), centering=(0.50, 0.48))
    base = warm_art(base.filter(ImageFilter.GaussianBlur(1.2)), grain_strength=0.05)
    base = Image.blend(base, Image.new("RGB", base.size, "#ead7ad"), 0.32)
    panel.paste(base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=14, outline="#9a7444", width=2)

    points = {
        "CYRENE": (88, 184),
        "ANTIOCH": (250, 102),
        "CYPRUS": (190, 154),
        "EGYPT": (260, 200),
        "ATHENS": (106, 114),
    }
    draw.line([points["ANTIOCH"], points["EGYPT"]], fill="#7f4e35", width=4)
    draw.line([points["CYRENE"], points["ANTIOCH"]], fill="#6b5735", width=3)
    draw.line([points["CYPRUS"], points["EGYPT"]], fill="#365c75", width=3)
    draw.line([points["EGYPT"], points["ATHENS"]], fill="#526b73", width=2)
    for name, color in [
        ("CYRENE", "#7f4e35"),
        ("ANTIOCH", "#7b493a"),
        ("CYPRUS", "#365c75"),
        ("EGYPT", "#7b493a"),
        ("ATHENS", "#526b73"),
    ]:
        x, y = points[name]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#f5e3ba", width=2)

    for text, rect, name in [
        ("CYRENE", (52, 190, 130, 214), "locator:cyrene"),
        ("ANTIOCH", (216, 80, 306, 104), "locator:antioch"),
        ("CYPRUS", (160, 158, 238, 182), "locator:cyprus"),
        ("EGYPT", (232, 204, 302, 228), "locator:egypt"),
        ("ATHENS", (70, 86, 148, 110), "locator:athens"),
    ]:
        draw.rounded_rectangle(rect, radius=7, fill="#f5e3ba", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=9,
                min_size=6,
                padding=2,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption = "Magas draws Antiochus toward Egypt; Ptolemy answers by spreading war through Antiochus' own territories."
    records.append(
        draw_fitted_text(
            draw,
            (22, 248, panel.width - 22, panel.height - 14),
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


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    for asset in [MAIN_ART, COUNCIL_ART, ARSINOITE_ART]:
        if not asset.exists():
            raise RuntimeError(f"Missing generated art asset: {asset}")

    records: list[FitRecord] = []
    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (424, 36, 1374, 642)
    main_art = crop_to_fill(MAIN_ART, (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]), centering=(0.50, 0.50))
    main_art = warm_art(main_art)
    main_panel = framed_panel((main_art.width + 28, main_art.height + 28), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (14, 14))
    ImageDraw.Draw(main_panel).rectangle((14, 14, 14 + main_art.width, 14 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 14, main_rect[1] - 14))

    left_panel_rect = (32, 36, 406, 706)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 72)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.7.3",
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
            max_size=17,
            min_size=9,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.12,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    draw = ImageDraw.Draw(page)
    title_rect = (628, 56, 1186, 118)
    paste_with_shadow(
        page,
        make_label("ANTIOCHUS HELD BACK", title_rect, records, font_path=TITLE_FONT, max_size=22, min_size=12),
        (title_rect[0], title_rect[1]),
    )

    label_specs = [
        ("ANTIOCH'S TERRITORIES", (946, 164, 1262, 212), (1064, 338)),
        ("RAIDED COAST", (500, 420, 722, 468), (518, 522)),
        ("PTOLEMAIC FLEETS", (576, 548, 842, 596), (648, 534)),
        ("CYPRUS", (724, 288, 872, 336), (770, 358)),
        ("EGYPT BLOCKED", (1054, 478, 1304, 526), (1142, 524)),
        ("ATHENIAN NAVAL AID", (514, 176, 798, 224), (608, 252)),
    ]
    for text, rect, point in label_specs:
        draw_leader(draw, point, (rect[0], rect[1] + (rect[3] - rect[1]) // 2))
        paste_with_shadow(page, make_label(text, rect, records, max_size=16, min_size=8), (rect[0], rect[1]))

    dispersed_note = make_compact_callout(
        "Ptolemy does not meet Antiochus in a single set battle; he disperses the danger across the coast.",
        (402, 96),
        "callout:dispersed-war",
        records,
    )
    draw_polyline_leader(draw, [(750, 654), (704, 600), (648, 534)])
    paste_with_shadow(page, dispersed_note, (520, 648))

    campaign_note = make_compact_callout(
        "Antiochus prepares to invade, but the campaign against Egypt never begins.",
        (386, 96),
        "callout:campaign-never-begins",
        records,
    )
    draw_polyline_leader(draw, [(1110, 654), (1132, 584), (1142, 524)])
    paste_with_shadow(page, campaign_note, (976, 648))

    locator = make_locator_key(records)
    paste_with_shadow(page, locator, (32, 748))

    council_art = warm_art(crop_to_fill(COUNCIL_ART, (420, 218), centering=(0.50, 0.50)), grain_strength=0.02)
    council_panel = make_inset_panel(
        council_art,
        "Magas and Apame draw Antiochus away from Seleucus' treaty with Ptolemy.",
        78,
        "inset:council-caption",
        records,
    )
    paste_with_shadow(page, council_panel, (430, 760))
    council_label = (542, 780, 790, 816)
    draw_leader(draw, (642, 884), (council_label[0], council_label[1] + 18))
    paste_with_shadow(page, make_label("PALACE COUNCIL", council_label, records, max_size=13, min_size=7), (council_label[0], council_label[1]))

    arsinoite_art = warm_art(crop_to_fill(ARSINOITE_ART, (404, 218), centering=(0.50, 0.50)), grain_strength=0.02)
    arsinoite_panel = make_inset_panel(
        arsinoite_art,
        "Pausanias closes with Arsinoe: her name remains attached to an Egyptian district.",
        78,
        "inset:arsinoite-caption",
        records,
    )
    paste_with_shadow(page, arsinoite_panel, (918, 760))
    arsinoite_label = (1032, 780, 1212, 816)
    draw_leader(draw, (1104, 884), (arsinoite_label[0], arsinoite_label[1] + 18))
    paste_with_shadow(page, make_label("ARSINOITE NOME", arsinoite_label, records, max_size=13, min_size=7), (arsinoite_label[0], arsinoite_label[1]))

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
            "graphic_book/images/1/7/2.png",
        ],
        "sources": [
            {
                "path": str(MAIN_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e897e-9297-7d11-87ab-c7948ef14a32/ig_0445492d07fbadd7016a1f1a90fd948191a62dbb2120cf932a.png",
                "description": "Generated raster main panel: eastern Mediterranean campaign theatre with Ptolemaic fleets, coastal raids, Antiochus' territories, Cyprus, and Egypt.",
            },
            {
                "path": str(COUNCIL_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e897e-9297-7d11-87ab-c7948ef14a32/ig_0445492d07fbadd7016a1f1bacb48c8191b1a11085c8d4fa51.png",
                "description": "Generated raster inset: Magas and Apame before Antiochus in a palace council.",
            },
            {
                "path": str(ARSINOITE_ART),
                "source_image": "/Users/gregb/.codex/generated_images/019e897e-9297-7d11-87ab-c7948ef14a32/ig_0445492d07fbadd7016a1f1c48d57c8191939b57ad35c2e669.png",
                "description": "Generated raster inset: Arsinoite nome canal-side district study in Ptolemaic Egypt.",
            },
        ],
    }
    report_path = root_dir() / "tmp" / "passage_1_7_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "7" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
