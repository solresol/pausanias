#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


WIDTH = 1402
HEIGHT = 1122
PASSAGE_ID = "1.2.6"

PARCHMENT = "#efd9ab"
PARCHMENT_LIGHT = "#f7e8c8"
PARCHMENT_DEEP = "#d8bb86"
INK = "#2a1e13"
RULE = "#6f5130"
ROAD = "#b8823f"
ROAD_LIGHT = "#f0deba"

TITLE_FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
BODY_FONT = "/System/Library/Fonts/Supplemental/Georgia.ttf"
DISPLAY_FONT = "/Users/gregb/Library/Fonts/EBGaramond-VariableFont_wght.ttf"


@dataclass
class FitRecord:
    name: str
    rect: tuple[int, int, int, int]
    font_path: str
    font_size: int
    text_bbox: tuple[int, int, int, int]
    text: str


def root_dir() -> Path:
    return ROOT_DIR


def load_translation() -> str:
    db_path = root_dir() / "pausanias.sqlite"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return " ".join(row[0].split())


def make_parchment(size: tuple[int, int]) -> Image.Image:
    base = Image.new("RGB", size, PARCHMENT)
    noise = Image.effect_noise(size, 14).convert("L")
    noise = ImageOps.autocontrast(noise)
    warm = ImageOps.colorize(noise, black="#cfb07a", white="#fff1d2")
    base = Image.blend(base, warm, 0.22)

    vignette = Image.new("L", size, 0)
    draw = ImageDraw.Draw(vignette)
    for inset, alpha in [(0, 140), (16, 110), (40, 70), (86, 38)]:
        draw.rectangle((inset, inset, size[0] - inset, size[1] - inset), outline=alpha, width=6)
    vignette = vignette.filter(ImageFilter.GaussianBlur(24))
    shadow = Image.new("RGB", size, "#8f7344")
    return Image.composite(shadow, base, vignette)


def panel_shadow(size: tuple[int, int], radius: int = 14) -> Image.Image:
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    draw.rounded_rectangle((10, 10, size[0] - 10, size[1] - 10), radius=18, fill=(35, 23, 11, 105))
    return shadow.filter(ImageFilter.GaussianBlur(radius))


def paste_with_shadow(canvas: Image.Image, panel: Image.Image, xy: tuple[int, int]) -> None:
    shadow = panel_shadow(panel.size)
    canvas.alpha_composite(shadow, (xy[0] - 6, xy[1] - 2))
    canvas.alpha_composite(panel, xy)


def crop_to_fill(
    path: Path,
    size: tuple[int, int],
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=centering)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return "\n".join(lines)


def fit_text_block(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    text: str,
    font_path: str,
    max_size: int,
    min_size: int,
    padding: int,
    name: str,
    spacing_ratio: float = 0.2,
) -> tuple[ImageFont.FreeTypeFont, str, tuple[int, int, int, int], FitRecord]:
    width = rect[2] - rect[0] - 2 * padding
    height = rect[3] - rect[1] - 2 * padding
    if width <= 0 or height <= 0:
        raise RuntimeError(f"{name}: invalid target rect {rect}")

    for font_size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, font_size)
        spacing = max(2, round(font_size * spacing_ratio))
        wrapped = wrap_text(draw, text, font, width)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align="left")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= width and text_h <= height:
            placed_bbox = (
                rect[0] + padding,
                rect[1] + padding,
                rect[0] + padding + text_w,
                rect[1] + padding + text_h,
            )
            record = FitRecord(
                name=name,
                rect=rect,
                font_path=font_path,
                font_size=font_size,
                text_bbox=placed_bbox,
                text=wrapped,
            )
            return font, wrapped, placed_bbox, record

    raise RuntimeError(f"{name}: text overflowed rect {rect} even at minimum size {min_size}")


def draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    text: str,
    font_path: str,
    max_size: int,
    min_size: int,
    padding: int,
    name: str,
    fill: str = INK,
    spacing_ratio: float = 0.2,
    align: str = "left",
    anchor_offset: tuple[int, int] = (0, 0),
) -> FitRecord:
    font, wrapped, bbox, record = fit_text_block(
        draw,
        rect,
        text,
        font_path,
        max_size,
        min_size,
        padding,
        name,
        spacing_ratio=spacing_ratio,
    )
    spacing = max(2, round(record.font_size * spacing_ratio))
    x = rect[0] + padding + anchor_offset[0]
    y = rect[1] + padding + anchor_offset[1]
    if align == "center":
        text_width = bbox[2] - bbox[0]
        x = rect[0] + ((rect[2] - rect[0]) - text_width) // 2
    draw.multiline_text((x, y), wrapped, font=font, fill=fill, spacing=spacing, align=align)
    return record


def framed_panel(
    size: tuple[int, int],
    fill: str = PARCHMENT_LIGHT,
    border: str = RULE,
    inner: bool = True,
) -> Image.Image:
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=18, fill=fill, outline=border, width=3)
    if inner and size[0] > 26 and size[1] > 26:
        draw.rounded_rectangle((9, 9, size[0] - 10, size[1] - 10), radius=14, outline="#b8945a", width=1)
    return panel


def make_inset_panel(art: Image.Image, caption: str, caption_height: int, name: str, records: list[FitRecord]) -> Image.Image:
    border = 18
    panel = framed_panel((art.width + 2 * border, art.height + caption_height + 2 * border + 8))
    draw = ImageDraw.Draw(panel)
    art_xy = (border, border)
    panel.paste(art, art_xy)
    draw.rectangle((art_xy[0], art_xy[1], art_xy[0] + art.width, art_xy[1] + art.height), outline=RULE, width=2)
    caption_rect = (
        border + 10,
        border + art.height + 16,
        panel.width - border - 10,
        panel.height - border - 10,
    )
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            caption,
            BODY_FONT,
            max_size=18,
            min_size=13,
            padding=6,
            name=name,
            align="center",
            spacing_ratio=0.16,
        )
    )
    return panel


def make_label(
    text: str,
    rect: tuple[int, int, int, int],
    records: list[FitRecord],
    font_path: str = DISPLAY_FONT,
    max_size: int = 29,
    min_size: int = 14,
) -> Image.Image:
    size = (rect[2] - rect[0], rect[3] - rect[1])
    label = framed_panel(size, fill="#f5e3ba", inner=False)
    draw = ImageDraw.Draw(label)
    records.append(
        draw_fitted_text(
            draw,
            (8, 5, size[0] - 8, size[1] - 5),
            text,
            font_path,
            max_size=max_size,
            min_size=min_size,
            padding=4,
            name=f"label:{text}",
            align="center",
            spacing_ratio=0.06,
        )
    )
    return label


def make_note_panel(
    text: str,
    size: tuple[int, int],
    name: str,
    records: list[FitRecord],
) -> Image.Image:
    panel = framed_panel(size)
    draw = ImageDraw.Draw(panel)
    records.append(
        draw_fitted_text(
            draw,
            (14, 10, size[0] - 14, size[1] - 10),
            text,
            BODY_FONT,
            max_size=18,
            min_size=13,
            padding=4,
            name=name,
            align="center",
            spacing_ratio=0.16,
        )
    )
    return panel


def draw_leader(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((start, end), fill=RULE, width=3)
    draw.ellipse((start[0] - 5, start[1] - 5, start[0] + 5, start[1] + 5), fill=RULE)


def draw_polyline_leader(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]]) -> None:
    if len(points) < 2:
        return
    draw.line(points, fill=RULE, width=3)
    start = points[0]
    draw.ellipse((start[0] - 5, start[1] - 5, start[0] + 5, start[1] + 5), fill=RULE)


def add_border(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((10, 10, WIDTH - 10, HEIGHT - 10), outline=RULE, width=3)
    draw.rectangle((24, 24, WIDTH - 24, HEIGHT - 24), outline="#9d7d4e", width=1)


def make_succession_panel(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((396, 352))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "ROYAL SUCCESSION",
            TITLE_FONT,
            max_size=24,
            min_size=16,
            padding=8,
            name="succession:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    box_specs = [
        ("ACTAEUS", "First ruler of the land later called Attica.", (28, 76, 176, 148)),
        ("CECROPS", "Succeeds through marriage; Erysichthon dies before inheriting.", (216, 76, 368, 156)),
        ("CRANAUS", "Rises after Cecrops and becomes pre-eminent among Athenians.", (28, 176, 176, 252)),
        ("AMPHICTYON", "Cranaus' son-in-law seizes the kingdom by revolt.", (216, 182, 368, 258)),
        ("ERICHTHONIUS", "Earth-born king who expels Amphictyon.", (92, 272, 304, 340)),
    ]
    for title, text, rect in box_specs:
        draw.rounded_rectangle(rect, radius=12, fill="#f5e7c4", outline="#a78454", width=2)
        band = (rect[0] + 8, rect[1] + 6, rect[2] - 8, rect[1] + 28)
        draw.rounded_rectangle(band, radius=8, fill="#ead2a0", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                band,
                title,
                DISPLAY_FONT,
                max_size=17,
                min_size=10,
                padding=4,
                name=f"succession:{title}:title",
                align="center",
                spacing_ratio=0.05,
            )
        )
        records.append(
            draw_fitted_text(
                draw,
                (rect[0] + 10, rect[1] + 32, rect[2] - 10, rect[3] - 8),
                text,
                BODY_FONT,
                max_size=13,
                min_size=9,
                padding=3,
                name=f"succession:{title}:body",
                align="center",
                spacing_ratio=0.12,
            )
        )

    arrow_points = [
        ((176, 112), (216, 112)),
        ((292, 156), (292, 186)),
        ((216, 228), (176, 228)),
        ((102, 252), (136, 280)),
        ((304, 290), (258, 254)),
    ]
    for start, end in arrow_points:
        draw.line((start, end), fill=ROAD, width=8)
        draw.line((start, end), fill=ROAD_LIGHT, width=3)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if dx == 0 and dy == 0:
            continue
        if abs(dx) > abs(dy):
            direction = 1 if dx > 0 else -1
            tip = end
            wing1 = (tip[0] - 10 * direction, tip[1] - 6)
            wing2 = (tip[0] - 10 * direction, tip[1] + 6)
        else:
            direction = 1 if dy > 0 else -1
            tip = end
            wing1 = (tip[0] - 6, tip[1] - 10 * direction)
            wing2 = (tip[0] + 6, tip[1] - 10 * direction)
        draw.polygon([tip, wing1, wing2], fill=ROAD)

    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (454, 44, 1372, 684)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_6/main_attica_panorama.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.48, 0.5),
    )
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle((13, 13, 13 + main_art.width, 13 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 620)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.2.6",
            TITLE_FONT,
            max_size=31,
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
            max_size=21,
            min_size=13,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (620, 42, 1182, 118)
    title_panel = make_label("FROM ACTAEA TO ATTICA", title_rect, records, font_path=TITLE_FONT, max_size=29, min_size=16)
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    labels = [
        ("ACROPOLIS", (482, 92, 710, 144)),
        ("ATHENS", (510, 472, 684, 522)),
        ("ATTICA", (1020, 92, 1232, 144)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect in labels:
        label = make_label(text, rect, records, max_size=25, min_size=13)
        label_panels.append((label, (rect[0], rect[1])))

    origin_panel = make_note_panel(
        "Actaeus ruled first; Cecrops followed through marriage into the royal house, but Erysichthon died before he could inherit.",
        (350, 94),
        "callout:origin",
        records,
    )
    origin_xy = (930, 182)

    name_panel = make_note_panel(
        "Cranaus' daughter Atthis gives the land its later name Attica, replacing the older name Actaea.",
        (316, 92),
        "callout:name",
        records,
    )
    name_xy = (972, 312)

    revolt_panel = make_note_panel(
        "Amphictyon overthrows Cranaus, yet is himself expelled when Erichthonius and his allies rise against him.",
        (350, 92),
        "callout:revolt",
        records,
    )
    revolt_xy = (922, 438)

    succession_panel = make_succession_panel(records)
    succession_xy = (34, 742)

    atthis_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_6/atthis_cranaus.png",
        (420, 188),
        centering=(0.5, 0.5),
    )
    atthis_panel = make_inset_panel(
        atthis_art,
        "Cranaus and Atthis personify the name-change at the center of the passage: from Actaea to Attica.",
        104,
        "caption:atthis",
        records,
    )
    atthis_xy = (470, 742)

    erichthonius_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_6/erichthonius_birth.png",
        (388, 188),
        centering=(0.5, 0.45),
    )
    erichthonius_panel = make_inset_panel(
        erichthonius_art,
        "Pausanias ends with Erichthonius as a child of Hephaestus and Earth: autochthony turned into dynastic legitimacy.",
        104,
        "caption:erichthonius",
        records,
    )
    erichthonius_xy = (958, 742)

    draw = ImageDraw.Draw(page)
    draw_polyline_leader(draw, [(930, 228), (850, 228), (850, 497), (684, 497)])
    draw_polyline_leader(draw, [(972, 356), (910, 356), (910, 118), (1020, 118)])
    draw_polyline_leader(draw, [(922, 484), (882, 484), (882, 742), (742, 742)])
    draw_leader(draw, (1110, 404), (atthis_xy[0] + atthis_panel.width // 2, atthis_xy[1]))
    draw_leader(draw, (1052, 530), (erichthonius_xy[0], erichthonius_xy[1] + 124))

    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, origin_panel, origin_xy)
    paste_with_shadow(page, name_panel, name_xy)
    paste_with_shadow(page, revolt_panel, revolt_xy)
    paste_with_shadow(page, succession_panel, succession_xy)
    paste_with_shadow(page, atthis_panel, atthis_xy)
    paste_with_shadow(page, erichthonius_panel, erichthonius_xy)

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_2_6_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "2" / "6.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
