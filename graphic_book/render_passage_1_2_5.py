#!/usr/bin/env python3

from __future__ import annotations

import json
import math
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
PASSAGE_ID = "1.2.5"

PARCHMENT = "#efd9ab"
PARCHMENT_LIGHT = "#f7e8c8"
PARCHMENT_DEEP = "#d8bb86"
INK = "#2a1e13"
RULE = "#6f5130"
SEA = "#4d7c95"
ROAD = "#b8823f"
ROAD_LIGHT = "#f0deba"
WALL = "#8c6a3f"
BRONZE = "#7b7655"

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


def draw_dashed_route(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    dash: int = 14,
    gap: int = 10,
    fill: str = "#f7f0e2",
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


def make_locator_map(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((396, 334))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "INNER KERAMEIKOS",
            TITLE_FONT,
            max_size=25,
            min_size=16,
            padding=8,
            name="map:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 70, panel.width - 22, 246)
    draw.rounded_rectangle(map_rect, radius=16, fill="#efe0ba", outline="#aa8651", width=2)

    wall_points = [
        (map_rect[0] + 54, map_rect[1] + 28),
        (map_rect[0] + 46, map_rect[1] + 76),
        (map_rect[0] + 42, map_rect[1] + 152),
    ]
    draw.line(wall_points, fill=WALL, width=10)
    draw.line([(p[0] + 8, p[1] + 8) for p in wall_points], fill="#ccb07a", width=2)

    dipylon_gate = (map_rect[0] + 30, map_rect[1] + 54, map_rect[0] + 66, map_rect[1] + 86)
    sacred_gate = (map_rect[0] + 28, map_rect[1] + 134, map_rect[0] + 64, map_rect[1] + 166)
    draw.rounded_rectangle(dipylon_gate, radius=6, fill="#b68c55", outline=RULE, width=2)
    draw.rounded_rectangle(sacred_gate, radius=6, fill="#b68c55", outline=RULE, width=2)

    stoa = (map_rect[0] + 108, map_rect[1] + 52, map_rect[0] + 252, map_rect[1] + 78)
    gymnasium = (map_rect[0] + 126, map_rect[1] + 92, map_rect[0] + 252, map_rect[1] + 166)
    polytion = (map_rect[0] + 268, map_rect[1] + 86, map_rect[0] + 316, map_rect[1] + 128)
    dionysus = (map_rect[0] + 264, map_rect[1] + 136, map_rect[0] + 314, map_rect[1] + 176)
    acropolis = [(map_rect[0] + 298, map_rect[1] + 34), (map_rect[0] + 332, map_rect[1] + 8), (map_rect[0] + 348, map_rect[1] + 40)]

    for rect in [stoa, gymnasium, polytion, dionysus]:
        draw.rounded_rectangle(rect, radius=6, fill="#cfb07a", outline=RULE, width=2)
    draw.polygon(acropolis, fill="#a77e49", outline=RULE)
    draw.line((acropolis[0][0], acropolis[1][1], acropolis[2][0], acropolis[1][1]), fill="#d8bb86", width=2)

    panathenaic = [(dipylon_gate[2], dipylon_gate[1] + 8), (map_rect[0] + 134, map_rect[1] + 86), (map_rect[0] + 270, map_rect[1] + 110)]
    sacred_way = [(sacred_gate[2], sacred_gate[1] + 12), (map_rect[0] + 122, map_rect[1] + 154), (map_rect[0] + 258, map_rect[1] + 160)]
    draw.line(panathenaic, fill=ROAD, width=10)
    draw.line(sacred_way, fill=ROAD, width=8)
    draw.line(panathenaic, fill=ROAD_LIGHT, width=3)
    draw.line(sacred_way, fill=ROAD_LIGHT, width=2)

    for x, y in [(170, 64), (186, 64), (202, 64), (186, 120), (202, 120), (218, 120)]:
        draw.ellipse((map_rect[0] + x - 3, map_rect[1] + y - 3, map_rect[0] + x + 3, map_rect[1] + y + 3), fill=BRONZE)

    label_specs = [
        ("DIPYLON", (map_rect[0] + 2, map_rect[1] + 42, map_rect[0] + 78, map_rect[1] + 72), "map:dipylon"),
        ("SACRED GATE", (map_rect[0] + 0, map_rect[1] + 166, map_rect[0] + 94, map_rect[1] + 198), "map:sacred"),
        ("STOA", (map_rect[0] + 128, map_rect[1] + 18, map_rect[0] + 210, map_rect[1] + 46), "map:stoa"),
        ("GYMNASIUM", (map_rect[0] + 126, map_rect[1] + 144, map_rect[0] + 236, map_rect[1] + 170), "map:gymnasium"),
        ("POLYTION", (map_rect[0] + 246, map_rect[1] + 50, map_rect[0] + 334, map_rect[1] + 78), "map:polytion"),
        ("DIONYSUS", (map_rect[0] + 254, map_rect[1] + 140, map_rect[0] + 338, map_rect[1] + 166), "map:dionysus"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=8, fill="#f6e7c0", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=14,
                min_size=8,
                padding=4,
                name=name,
                align="center",
                spacing_ratio=0.05,
            )
        )

    caption_rect = (18, 254, panel.width - 18, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "Locator map: just beyond the north-west gates, the stoa, Hermes gymnasium, Polytion house, and Dionysus precinct formed a tightly packed civic-and-cult quarter.",
            BODY_FONT,
            max_size=15,
            min_size=11,
            padding=6,
            name="map:caption",
            align="center",
            spacing_ratio=0.14,
        )
    )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")

    main_rect = (454, 44, 1372, 692)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_5/main_inner_kerameikos.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.56, 0.46),
    )
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle((13, 13, 13 + main_art.width, 13 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 614)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.2.5",
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
            max_size=22,
            min_size=14,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (634, 42, 1166, 118)
    title_panel = make_label("THE STOAS OF DIONYSUS", title_rect, records, font_path=TITLE_FONT)
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    locator_panel = make_locator_map(records)
    locator_xy = (34, 740)

    akratos_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_5/akratos_wallface.png",
        (420, 216),
        centering=(0.5, 0.48),
    )
    akratos_panel = make_inset_panel(
        akratos_art,
        "In the Dionysus precinct Pausanias notes Akratos, a daemon of the god's retinue, represented only by a face set into the wall.",
        118,
        "caption:akratos",
        records,
    )
    akratos_xy = (470, 742)

    amphictyon_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_5/amphictyon_dionysus.png",
        (388, 232),
        centering=(0.5, 0.48),
    )
    amphictyon_panel = make_inset_panel(
        amphictyon_art,
        "A nearby building held clay figures of Amphictyon entertaining Dionysus and the other gods: mythic kingship recast as civic cult memory.",
        108,
        "caption:amphictyon",
        records,
    )
    amphictyon_xy = (964, 734)

    labels = [
        ("ACROPOLIS", (1048, 114, 1278, 166)),
        ("STOA OF GODS", (802, 286, 1080, 338)),
        ("GYMNASIUM OF HERMES", (556, 398, 908, 452)),
        ("HOUSE OF POLYTION", (980, 462, 1308, 514)),
        ("DIONYSUS PRECINCT", (988, 344, 1304, 396)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect in labels:
        label = make_label(text, rect, records, max_size=25, min_size=13)
        label_panels.append((label, (rect[0], rect[1])))

    overview_panel = make_note_panel(
        "The portico, Hermes gymnasium, and Polytion house turned this corner of the inner Kerameikos into a civic threshold densely packed with shrines.",
        (346, 104),
        "callout:overview",
        records,
    )
    overview_xy = (978, 414)

    cult_panel = make_note_panel(
        "Here the Dionysus called Melpomenos shared company with Athena Paionia, Zeus, Mnemosyne, the Muses, Apollo, and the daemon Akratos.",
        (338, 96),
        "callout:cult",
        records,
    )
    cult_xy = (990, 530)

    pegasus_panel = make_note_panel(
        "Pausanias closes with Pegasus of Eleutherae, remembered as the figure who brought the god to Athens under Delphic prompting from old Icaria.",
        (392, 96),
        "callout:pegasus",
        records,
    )
    pegasus_xy = (934, 636)

    draw = ImageDraw.Draw(page)
    draw_dashed_route(draw, (1120, 374), (1158, 164), dash=16, gap=11, width=4)
    draw_dashed_route(draw, (720, 430), (1120, 470), dash=12, gap=9, width=3)
    draw_polyline_leader(draw, [(944, 310), (944, 450), (978, 450)])
    draw_polyline_leader(draw, [(1132, 370), (1160, 370), (1160, 578), (990, 578)])
    draw_polyline_leader(draw, [(1112, 488), (1112, 680), (934, 680)])
    draw_leader(draw, (1098, 360), (akratos_xy[0] + akratos_panel.width // 2, akratos_xy[1]))
    draw_leader(draw, (1078, 484), (amphictyon_xy[0], amphictyon_xy[1] + 152))
    draw_leader(draw, (598, 434), (locator_xy[0] + locator_panel.width, locator_xy[1] + 66))

    paste_with_shadow(page, locator_panel, locator_xy)
    paste_with_shadow(page, akratos_panel, akratos_xy)
    paste_with_shadow(page, amphictyon_panel, amphictyon_xy)
    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, overview_panel, overview_xy)
    paste_with_shadow(page, cult_panel, cult_xy)
    paste_with_shadow(page, pegasus_panel, pegasus_xy)

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_2_5_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "2" / "5.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
