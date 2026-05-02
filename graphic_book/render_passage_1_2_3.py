#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pausanias_db import connect

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


WIDTH = 1402
HEIGHT = 1122
PASSAGE_ID = "1.2.3"

PARCHMENT = "#efd9ab"
PARCHMENT_LIGHT = "#f7e8c8"
PARCHMENT_DEEP = "#d8bb86"
INK = "#2a1e13"
RULE = "#6f5130"

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
    with connect() as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = %s",
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
    base = Image.composite(shadow, base, vignette)
    return base


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
    x = rect[0] + padding
    y = rect[1] + padding
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
    draw.rectangle(
        (art_xy[0], art_xy[1], art_xy[0] + art.width, art_xy[1] + art.height),
        outline=RULE,
        width=2,
    )
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
            max_size=29,
            min_size=14,
            padding=4,
            name=f"label:{text}",
            align="center",
            spacing_ratio=0.06,
        )
    )
    return label


def draw_leader(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((start, end), fill=RULE, width=3)
    draw.ellipse((start[0] - 5, start[1] - 5, start[0] + 5, start[1] + 5), fill=RULE)


def draw_polyline_leader(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]]) -> None:
    if len(points) < 2:
        return
    draw.line(points, fill=RULE, width=3)
    start = points[0]
    draw.ellipse((start[0] - 5, start[1] - 5, start[0] + 5, start[1] + 5), fill=RULE)


def draw_dashed_route(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    dash: int = 14,
    gap: int = 10,
    fill: str = "#f4ede3",
    width: int = 4,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    step = dash + gap
    ux = dx / length
    uy = dy / length
    pos = 0.0
    while pos < length:
        seg_end = min(length, pos + dash)
        x1 = start[0] + ux * pos
        y1 = start[1] + uy * pos
        x2 = start[0] + ux * seg_end
        y2 = start[1] + uy * seg_end
        draw.line((x1, y1, x2, y2), fill=fill, width=width)
        pos += step


def add_border(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((10, 10, WIDTH - 10, HEIGHT - 10), outline=RULE, width=3)
    draw.rectangle((24, 24, WIDTH - 24, HEIGHT - 24), outline="#9d7d4e", width=1)


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (454, 44, 1372, 690)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_3/main_city_gates.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.57, 0.5),
    )
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle((13, 13, 13 + main_art.width, 13 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 610)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.2.3",
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
            max_size=24,
            min_size=15,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (624, 42, 1062, 118)
    title_panel = make_label("THE CITY GATES", title_rect, records, font_path=TITLE_FONT)
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    relief_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_3/praxiteles_relief.png",
        (388, 230),
        centering=(0.48, 0.46),
    )
    relief_panel = make_inset_panel(
        relief_art,
        "Beside the gates Pausanias notes a tomb relief of a soldier and horse, carved by Praxiteles though the dead man was forgotten.",
        96,
        "caption:relief",
        records,
    )
    relief_xy = (34, 736)

    court_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_3/court_poet.png",
        (430, 206),
        centering=(0.52, 0.47),
    )
    court_panel = make_inset_panel(
        court_art,
        "Anacreon and the other examples stand for a wider pattern: poets often moved within the orbit of rulers and courts.",
        92,
        "caption:court",
        records,
    )
    court_xy = (472, 780)

    homer_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_3/homer_bard.png",
        (390, 234),
        centering=(0.5, 0.46),
    )
    homer_panel = make_inset_panel(
        homer_art,
        "Homer, Pausanias says, ranged widely and chose renown among ordinary hearers over profit from kings.",
        92,
        "caption:homer",
        records,
    )
    homer_xy = (944, 736)

    labels = [
        ("ATHENS", (980, 96, 1180, 150)),
        ("ACROPOLIS", (1018, 154, 1288, 208)),
        ("CITY GATES", (714, 236, 968, 292)),
        ("ROAD FROM PIRAEUS", (602, 514, 974, 570)),
        ("ROADSIDE TOMB", (522, 362, 790, 418)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect in labels:
        label = make_label(text, rect, records)
        label_panels.append((label, (rect[0], rect[1])))

    gates_callout_rect = (994, 396, 1328, 496)
    poets_callout_rect = (1012, 522, 1328, 618)
    relief_callout_rect = (920, 620, 1328, 714)

    gates_callout = framed_panel((gates_callout_rect[2] - gates_callout_rect[0], gates_callout_rect[3] - gates_callout_rect[1]))
    gates_callout_draw = ImageDraw.Draw(gates_callout)
    records.append(
        draw_fitted_text(
            gates_callout_draw,
            (16, 10, gates_callout.width - 16, gates_callout.height - 10),
            "The road from Piraeus tightened here at the city gates, where monuments still clustered near the entrance to Athens.",
            BODY_FONT,
            max_size=18,
            min_size=13,
            padding=4,
            name="callout:gates",
            align="center",
            spacing_ratio=0.16,
        )
    )

    poets_callout = framed_panel((poets_callout_rect[2] - poets_callout_rect[0], poets_callout_rect[3] - poets_callout_rect[1]))
    poets_callout_draw = ImageDraw.Draw(poets_callout)
    records.append(
        draw_fitted_text(
            poets_callout_draw,
            (14, 10, poets_callout.width - 14, poets_callout.height - 10),
            "The digression links poets to patrons across the Greek world, from Samos and Syracuse to later Macedonian courts.",
            BODY_FONT,
            max_size=18,
            min_size=13,
            padding=4,
            name="callout:poets",
            align="center",
            spacing_ratio=0.16,
        )
    )

    relief_callout = framed_panel((relief_callout_rect[2] - relief_callout_rect[0], relief_callout_rect[3] - relief_callout_rect[1]))
    relief_callout_draw = ImageDraw.Draw(relief_callout)
    records.append(
        draw_fitted_text(
            relief_callout_draw,
            (18, 10, relief_callout.width - 18, relief_callout.height - 10),
            "At the gate-side tomb Pausanias could name the sculptor, Praxiteles, even though the dead horseman remained unknown.",
            BODY_FONT,
            max_size=18,
            min_size=13,
            padding=4,
            name="callout:relief",
            align="center",
            spacing_ratio=0.16,
        )
    )

    # Route and leader strokes must sit below text-bearing panels so they cannot
    # run through labels, callouts, or inset captions.
    draw = ImageDraw.Draw(page)
    draw_dashed_route(draw, (736, 540), (1080, 196), dash=16, gap=10, width=4)
    draw_polyline_leader(draw, [(666, 388), (820, 388), (820, 666), (920, 666)])
    draw_polyline_leader(draw, [(844, 266), (930, 266), (930, 446), (994, 446)])
    draw_polyline_leader(draw, [(742, 542), (906, 542), (906, 570), (1012, 570)])
    draw_leader(draw, (602, 642), (relief_xy[0] + relief_panel.width, relief_xy[1] + 124))
    draw_leader(draw, (1020, 568), (court_xy[0] + court_panel.width // 2, court_xy[1]))
    draw_leader(draw, (744, 540), (homer_xy[0], homer_xy[1] + 152))

    paste_with_shadow(page, relief_panel, relief_xy)
    paste_with_shadow(page, court_panel, court_xy)
    paste_with_shadow(page, homer_panel, homer_xy)
    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, gates_callout, (gates_callout_rect[0], gates_callout_rect[1]))
    paste_with_shadow(page, poets_callout, (poets_callout_rect[0], poets_callout_rect[1]))
    paste_with_shadow(page, relief_callout, (relief_callout_rect[0], relief_callout_rect[1]))

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_2_3_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "2" / "3.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
