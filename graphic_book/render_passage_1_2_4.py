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

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


WIDTH = 1402
HEIGHT = 1122
PASSAGE_ID = "1.2.4"

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
            "KERAMEIKOS ENTRY",
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
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    locator_base = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_4/main_kerameikos_entry.png",
        map_size,
        centering=(0.44, 0.54),
    )
    locator_base = locator_base.filter(ImageFilter.GaussianBlur(1.6))
    locator_base = ImageEnhance.Color(locator_base).enhance(0.54)
    locator_base = ImageEnhance.Contrast(locator_base).enhance(0.88)
    parchment_wash = Image.new("RGB", map_size, "#ead6a8")
    locator_base = Image.blend(locator_base, parchment_wash, 0.42)
    grain = Image.effect_noise(map_size, 10).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#8f7143", white="#fff0cb")
    locator_base = Image.blend(locator_base, grain_rgb, 0.08)
    panel.paste(locator_base, (map_rect[0], map_rect[1]))
    draw.rounded_rectangle(map_rect, radius=16, outline="#aa8651", width=2)

    # River and open low ground beyond the walls.
    river = [
        (map_rect[0] + 24, map_rect[1] + 126),
        (map_rect[0] + 56, map_rect[1] + 116),
        (map_rect[0] + 94, map_rect[1] + 120),
        (map_rect[0] + 132, map_rect[1] + 102),
        (map_rect[0] + 168, map_rect[1] + 110),
        (map_rect[0] + 212, map_rect[1] + 96),
    ]
    draw.line(river, fill="#5f8795", width=8)
    draw.line(river, fill="#d4e0d2", width=2)

    # City wall segment.
    wall_points = [
        (map_rect[0] + 118, map_rect[1] + 28),
        (map_rect[0] + 98, map_rect[1] + 74),
        (map_rect[0] + 98, map_rect[1] + 152),
        (map_rect[0] + 142, map_rect[1] + 176),
    ]
    draw.line(wall_points, fill=WALL, width=11)
    draw.line([(p[0] + 8, p[1] + 8) for p in wall_points], fill="#ccb07a", width=2)

    dipylon_gate = (map_rect[0] + 90, map_rect[1] + 64, map_rect[0] + 126, map_rect[1] + 96)
    sacred_gate = (map_rect[0] + 90, map_rect[1] + 134, map_rect[0] + 126, map_rect[1] + 166)
    draw.rounded_rectangle(dipylon_gate, radius=6, fill="#b68c55", outline=RULE, width=2)
    draw.rounded_rectangle(sacred_gate, radius=6, fill="#b68c55", outline=RULE, width=2)

    pompeion = (map_rect[0] + 140, map_rect[1] + 62, map_rect[0] + 216, map_rect[1] + 112)
    demeter = (map_rect[0] + 188, map_rect[1] + 126, map_rect[0] + 244, map_rect[1] + 168)
    poseidon = (map_rect[0] + 250, map_rect[1] + 122, map_rect[0] + 286, map_rect[1] + 152)
    stoa_one = (map_rect[0] + 238, map_rect[1] + 58, map_rect[0] + 306, map_rect[1] + 78)
    stoa_two = (map_rect[0] + 248, map_rect[1] + 88, map_rect[0] + 320, map_rect[1] + 108)
    acropolis = [(map_rect[0] + 308, map_rect[1] + 182), (map_rect[0] + 344, map_rect[1] + 132), (map_rect[0] + 356, map_rect[1] + 188)]

    for rect in [pompeion, demeter, poseidon, stoa_one, stoa_two]:
        draw.rounded_rectangle(rect, radius=6, fill="#cfb07a", outline=RULE, width=2)

    draw.polygon(acropolis, fill="#a77e49", outline=RULE)
    draw.line((acropolis[0][0], acropolis[1][1], acropolis[2][0], acropolis[1][1]), fill="#d8bb86", width=2)

    panathenaic_way = [(dipylon_gate[2], dipylon_gate[1] + 8), (map_rect[0] + 234, map_rect[1] + 76), (map_rect[0] + 330, map_rect[1] + 154)]
    sacred_way = [(sacred_gate[2], sacred_gate[1] + 12), (map_rect[0] + 212, map_rect[1] + 140), (map_rect[0] + 300, map_rect[1] + 170)]
    draw.line(panathenaic_way, fill="#8f6231", width=11)
    draw.line(sacred_way, fill="#8f6231", width=9)
    draw.line(panathenaic_way, fill=ROAD_LIGHT, width=4)
    draw.line(sacred_way, fill=ROAD_LIGHT, width=3)

    for x, y in [(272, 76), (284, 76), (296, 76), (280, 106), (292, 106), (304, 106)]:
        draw.ellipse((map_rect[0] + x - 3, map_rect[1] + y - 3, map_rect[0] + x + 3, map_rect[1] + y + 3), fill=BRONZE)

    label_specs = [
        ("DIPYLON", (map_rect[0] + 16, map_rect[1] + 42, map_rect[0] + 90, map_rect[1] + 74), "map:dipylon"),
        ("SACRED GATE", (map_rect[0] + 8, map_rect[1] + 154, map_rect[0] + 98, map_rect[1] + 190), "map:sacred"),
        ("POMPEION", (map_rect[0] + 144, map_rect[1] + 24, map_rect[0] + 228, map_rect[1] + 54), "map:pompeion"),
        ("STOAS", (map_rect[0] + 254, map_rect[1] + 20, map_rect[0] + 328, map_rect[1] + 48), "map:stoas"),
        ("ACROPOLIS", (map_rect[0] + 270, map_rect[1] + 96, map_rect[0] + 352, map_rect[1] + 126), "map:acropolis"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=8, fill="#f6e7c0", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=16,
                min_size=10,
                padding=4,
                name=name,
                align="center",
                spacing_ratio=0.06,
            )
        )

    caption_rect = (18, 254, panel.width - 18, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "Locator map: the Dipylon and Sacred Gates opened toward the Panathenaic and Sacred roads, with the Pompeion and honorific stoas just inside Athens.",
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
        root_dir() / "graphic_book/assets/generated/1_2_4/main_kerameikos_entry.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.54, 0.5),
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
            "PASSAGE 1.2.4",
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

    title_rect = (612, 42, 1168, 118)
    title_panel = make_label("THE POMPEION AND THE CERAMICUS", title_rect, records, font_path=TITLE_FONT)
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    locator_panel = make_locator_map(records)
    locator_xy = (34, 740)

    demeter_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_4/demeter_sanctuary.png",
        (420, 216),
        centering=(0.52, 0.48),
    )
    demeter_panel = make_inset_panel(
        demeter_art,
        "Near the procession-building stood the Demeter sanctuary: Demeter, Kore, and torch-bearing Iacchus, with the wall inscription attributing the group to Praxiteles.",
        112,
        "caption:demeter",
        records,
    )
    demeter_xy = (472, 744)

    poseidon_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_2_4/poseidon_polybotes.png",
        (388, 232),
        centering=(0.5, 0.46),
    )
    poseidon_panel = make_inset_panel(
        poseidon_art,
        "A mounted sea-god driving his spear into Polybotes embodied myth in civic stone, though a later inscription no longer named Poseidon.",
        98,
        "caption:poseidon",
        records,
    )
    poseidon_xy = (962, 734)

    labels = [
        ("ACROPOLIS", (1048, 114, 1276, 166)),
        ("PANATHENAIC WAY", (612, 520, 962, 576)),
        ("DIPYLON GATE", (542, 246, 788, 300)),
        ("SACRED GATE", (482, 340, 720, 394)),
        ("POMPEION", (760, 236, 960, 288)),
        ("DEMETER TEMPLE", (776, 310, 1016, 362)),
        ("CERAMICUS STOAS", (1010, 362, 1318, 414)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect in labels:
        label = make_label(text, rect, records, max_size=26, min_size=13)
        label_panels.append((label, (rect[0], rect[1])))

    overview_panel = make_note_panel(
        "Just inside the north-western gates, the Pompeion staged Athens' processions before the roads split toward the Acropolis and Eleusis.",
        (340, 104),
        "callout:overview",
        records,
    )
    overview_xy = (986, 422)

    honors_panel = make_note_panel(
        "Pausanias notices the stoas and the bronze honorific portraits that turned the approach into a civic gallery.",
        (340, 94),
        "callout:honors",
        records,
    )
    honors_xy = (988, 532)

    inscription_panel = make_note_panel(
        "The Demeter sanctuary and the mounted giant-slaying statue condensed cult, craftsmanship, and myth into one dense ceremonial quarter.",
        (380, 92),
        "callout:inscription",
        records,
    )
    inscription_xy = (946, 636)

    draw = ImageDraw.Draw(page)
    draw_dashed_route(draw, (676, 286), (1148, 146), dash=16, gap=11, width=4)
    draw_dashed_route(draw, (650, 372), (1048, 556), dash=12, gap=9, width=3)
    draw_polyline_leader(draw, [(826, 262), (940, 262), (940, 468), (986, 468)])
    draw_polyline_leader(draw, [(1118, 344), (1164, 344), (1164, 578), (988, 578)])
    draw_polyline_leader(draw, [(908, 340), (908, 678), (946, 678)])
    draw_leader(draw, (896, 352), (demeter_xy[0] + demeter_panel.width // 2, demeter_xy[1]))
    draw_leader(draw, (1038, 406), (poseidon_xy[0], poseidon_xy[1] + 154))
    draw_leader(draw, (598, 290), (locator_xy[0] + locator_panel.width, locator_xy[1] + 54))

    paste_with_shadow(page, locator_panel, locator_xy)
    paste_with_shadow(page, demeter_panel, demeter_xy)
    paste_with_shadow(page, poseidon_panel, poseidon_xy)
    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, overview_panel, overview_xy)
    paste_with_shadow(page, honors_panel, honors_xy)
    paste_with_shadow(page, inscription_panel, inscription_xy)

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    validate_fit_records(records)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_2_4_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "2" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
