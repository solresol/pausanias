#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import random
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
    INK,
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
    make_note_panel,
    make_parchment,
    paste_with_shadow,
    root_dir,
)


PASSAGE_ID = "1.4.1"
SEA_DEEP = "#2f6275"
SEA_LIGHT = "#719eaa"
LAND = "#d5bc83"
LAND_LIGHT = "#ead9ad"
LAND_DARK = "#8d7346"
ROUTE = "#8b3f28"
ROUTE_LIGHT = "#e5c07b"
FOREST = "#586f45"
MOUNTAIN = "#7c6542"


def load_translation() -> str:
    db_path = root_dir() / "pausanias.sqlite"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            (PASSAGE_ID,),
        ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"Missing translation for passage {PASSAGE_ID}")
    return "\n\n".join(" ".join(p.split()) for p in row[0].split("\n\n"))


def validate_fit_records(records: list[FitRecord]) -> None:
    for record in records:
        rx0, ry0, rx1, ry1 = record.rect
        bx0, by0, bx1, by1 = record.text_bbox
        if bx0 < rx0 or by0 < ry0 or bx1 > rx1 or by1 > ry1:
            raise RuntimeError(f"{record.name}: measured text bbox escapes target rect")


def warm_finish(image: Image.Image, contrast: float = 1.04, color: float = 0.94) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(color)
    overlay = Image.new("RGB", image.size, "#ecd0a0")
    image = Image.blend(image, overlay, 0.08)
    grain = Image.effect_noise(image.size, 9).convert("L")
    grain = ImageOps.autocontrast(grain)
    grain_rgb = ImageOps.colorize(grain, black="#c29c66", white="#fff0ce")
    return Image.blend(image, grain_rgb, 0.08)


def draw_scribble_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: str,
    width: int,
    jitter: int,
    passes: int,
    rng: random.Random,
) -> None:
    for _ in range(passes):
        shifted = [(x + rng.randint(-jitter, jitter), y + rng.randint(-jitter, jitter)) for x, y in points]
        draw.line(shifted, fill=fill, width=width, joint="curve")


def triangle_mountain(draw: ImageDraw.ImageDraw, x: int, y: int, scale: int, shade: str = MOUNTAIN) -> None:
    left = (x - scale, y + scale)
    top = (x, y - scale)
    right = (x + scale, y + scale)
    draw.polygon([left, top, right], fill="#b49a69", outline=shade)
    draw.polygon([top, right, (x + scale // 5, y + scale)], fill="#8d744a")
    draw.line((x - scale // 2, y + scale // 2, x, y - scale, x + scale // 2, y + scale // 2), fill="#ead8a8", width=1)


def draw_waves(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], rng: random.Random, color: str = "#d8eee8") -> None:
    x0, y0, x1, y1 = rect
    for _ in range(150):
        x = rng.randint(x0, x1)
        y = rng.randint(y0, y1)
        length = rng.randint(16, 52)
        amp = rng.randint(2, 5)
        pts = []
        for i in range(0, length, 6):
            pts.append((x + i, y + int(math.sin(i / 6) * amp)))
        draw.line(pts, fill=color, width=1)


def make_outer_europe_atlas(size: tuple[int, int]) -> Image.Image:
    rng = random.Random(141)
    w, h = size
    source_path = root_dir() / "graphic_book" / "assets" / "generated" / "1_4_1" / "europe_1000_source.jpg"
    if source_path.exists():
        source = Image.open(source_path).convert("RGB")
        atlas = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS, centering=(0.50, 0.52))
        atlas = ImageEnhance.Contrast(atlas).enhance(1.10)
        atlas = ImageEnhance.Color(atlas).enhance(0.88)
        atlas = ImageEnhance.Sharpness(atlas).enhance(1.05)
        wash = Image.new("RGB", size, "#e8c88f")
        atlas = Image.blend(atlas, wash, 0.16)
        draw = ImageDraw.Draw(atlas)

        # Coordinates are hand-placed over the cropped antique Europe map.
        route = [(304, 358), (398, 380), (518, 420), (616, 486), (704, 546), (772, 564)]
        draw_scribble_polyline(draw, route, "#552317", 13, 2, 2, rng)
        draw_scribble_polyline(draw, route, ROUTE, 8, 1, 2, rng)
        draw_scribble_polyline(draw, route, ROUTE_LIGHT, 3, 1, 1, rng)
        for idx, (x, y) in enumerate(route[1:], start=1):
            px, py = route[idx - 1]
            angle = math.atan2(y - py, x - px)
            left = (int(x - 18 * math.cos(angle) + 8 * math.sin(angle)), int(y - 18 * math.sin(angle) - 8 * math.cos(angle)))
            right = (int(x - 18 * math.cos(angle) - 8 * math.sin(angle)), int(y - 18 * math.sin(angle) + 8 * math.cos(angle)))
            draw.polygon([(x, y), left, right], fill=ROUTE_LIGHT, outline="#552317")

        rhine = [(392, 236), (388, 284), (396, 328), (430, 372)]
        draw_scribble_polyline(draw, rhine, "#2d7280", 8, 1, 2, rng)
        draw_scribble_polyline(draw, rhine, "#e6f2e8", 3, 1, 1, rng)
        danube = [(470, 374), (548, 392), (634, 426), (730, 438)]
        draw_scribble_polyline(draw, danube, "#2d7280", 6, 1, 2, rng)
        draw_scribble_polyline(draw, danube, "#e6f2e8", 2, 1, 1, rng)

        for off in range(0, 94, 18):
            draw.arc((56 + off, 216, 116 + off, 254), 190, 350, fill="#f1efda", width=2)
        beast_x, beast_y = 120, 302
        draw.arc((beast_x - 34, beast_y - 18, beast_x + 34, beast_y + 18), 190, 350, fill="#efe9c7", width=5)
        draw.polygon(
            [(beast_x + 36, beast_y), (beast_x + 58, beast_y - 14), (beast_x + 54, beast_y + 14)],
            fill="#efe9c7",
            outline="#6f5130",
        )

        for _ in range(90):
            x = rng.randint(24, w - 24)
            y = rng.randint(30, h - 28)
            if rng.random() < 0.65:
                draw.line((x, y, x + rng.randint(8, 28), y + rng.randint(-2, 3)), fill=(125, 86, 44), width=1)
            else:
                draw.ellipse((x, y, x + 2, y + 2), fill=(68, 92, 58))

        vignette = Image.new("L", size, 0)
        vdraw = ImageDraw.Draw(vignette)
        for inset, alpha in [(0, 118), (18, 78), (42, 38)]:
            vdraw.rectangle((inset, inset, w - inset, h - inset), outline=alpha, width=12)
        vignette = vignette.filter(ImageFilter.GaussianBlur(18))
        edge = Image.new("RGB", size, "#8a6335")
        atlas = Image.composite(edge, atlas, vignette)
        return warm_finish(atlas, contrast=1.03, color=0.90)

    base = Image.new("RGB", size, SEA_DEEP)
    draw = ImageDraw.Draw(base)

    for y in range(h):
        blend = y / h
        color = (
            int(38 + 36 * blend),
            int(83 + 38 * blend),
            int(101 + 24 * blend),
        )
        draw.line((0, y, w, y), fill=color)
    draw_waves(draw, (0, 0, w, h), rng, color="#c9ded8")

    land_poly = [
        (210, 20), (370, 34), (548, 70), (715, 118), (850, 178), (914, 292),
        (862, 374), (766, 420), (794, 505), (868, 620), (682, 628),
        (574, 574), (470, 544), (354, 486), (286, 392), (204, 318), (158, 214),
    ]
    draw.polygon(land_poly, fill=LAND, outline="#6b5030")

    britain = [(132, 86), (184, 72), (228, 126), (208, 210), (146, 238), (104, 176)]
    northern_isles = [(248, 38), (284, 46), (280, 82), (236, 78)]
    iberia = [(186, 336), (310, 360), (356, 484), (278, 584), (154, 548), (118, 430)]
    italy = [(540, 430), (598, 470), (624, 552), (596, 622), (550, 556), (506, 476)]
    greece = [(706, 484), (786, 498), (846, 554), (802, 634), (718, 606), (682, 536)]
    asia_minor = [(838, 442), (918, 454), (918, 628), (844, 610), (802, 548)]
    for poly in [britain, northern_isles, iberia, italy, greece, asia_minor]:
        draw.polygon(poly, fill=LAND, outline="#6b5030")

    texture = Image.effect_noise(size, 18).convert("L")
    texture = ImageOps.autocontrast(texture)
    color_texture = ImageOps.colorize(texture, black="#9a8051", white="#f4dfaa")
    mask = Image.new("L", size, 0)
    mdraw = ImageDraw.Draw(mask)
    for poly in [land_poly, britain, northern_isles, iberia, italy, greece, asia_minor]:
        mdraw.polygon(poly, fill=170)
    base = Image.composite(Image.blend(base, color_texture, 0.30), base, mask)
    draw = ImageDraw.Draw(base)

    for _ in range(420):
        x = rng.randint(180, 900)
        y = rng.randint(40, 626)
        if rng.random() < 0.55:
            draw.ellipse((x, y, x + rng.randint(1, 3), y + rng.randint(1, 3)), fill=rng.choice([FOREST, "#6f7b45", "#9b824d"]))
        else:
            draw.line((x, y, x + rng.randint(6, 22), y + rng.randint(-4, 5)), fill="#b39761", width=1)

    for x, y, scale in [
        (418, 344, 20), (454, 350, 18), (492, 356, 23), (528, 366, 20),
        (566, 380, 22), (610, 390, 20), (656, 404, 17), (706, 420, 16),
        (604, 470, 15), (640, 502, 18), (684, 522, 16), (742, 538, 13),
    ]:
        triangle_mountain(draw, x, y, scale)

    rhine = [(406, 134), (430, 198), (452, 258), (444, 318), (470, 366), (516, 396)]
    danube = [(520, 372), (590, 380), (648, 402), (710, 420), (780, 428)]
    eridanos = [(392, 118), (416, 174), (438, 236), (430, 294)]
    draw_scribble_polyline(draw, rhine, "#4e8791", 7, 2, 3, rng)
    draw_scribble_polyline(draw, rhine, "#d5f0e6", 2, 1, 2, rng)
    draw_scribble_polyline(draw, danube, "#4e8791", 6, 2, 2, rng)
    draw_scribble_polyline(draw, danube, "#d5f0e6", 2, 1, 2, rng)
    draw_scribble_polyline(draw, eridanos, "#417783", 4, 1, 2, rng)

    route = [(378, 210), (454, 318), (548, 418), (646, 468), (728, 518), (804, 564)]
    draw_scribble_polyline(draw, route, "#5b2418", 9, 2, 2, rng)
    draw_scribble_polyline(draw, route, ROUTE, 5, 1, 2, rng)
    for idx, (x, y) in enumerate(route[1:], start=1):
        px, py = route[idx - 1]
        angle = math.atan2(y - py, x - px)
        tip = (x, y)
        left = (int(x - 18 * math.cos(angle) + 8 * math.sin(angle)), int(y - 18 * math.sin(angle) - 8 * math.cos(angle)))
        right = (int(x - 18 * math.cos(angle) - 8 * math.sin(angle)), int(y - 18 * math.sin(angle) + 8 * math.cos(angle)))
        draw.polygon([tip, left, right], fill=ROUTE_LIGHT, outline="#5b2418")

    for cx, cy, label in [(96, 292, "tide"), (70, 396, "beast"), (824, 634, "gate")]:
        if label == "beast":
            draw.arc((cx - 32, cy - 16, cx + 32, cy + 18), 195, 350, fill="#d9dfc7", width=4)
            draw.polygon([(cx + 34, cy), (cx + 50, cy - 12), (cx + 48, cy + 12)], fill="#d9dfc7", outline="#6f5130")
        elif label == "tide":
            for off in range(0, 72, 16):
                draw.arc((cx - 28 + off, cy - 14, cx + 28 + off, cy + 14), 190, 350, fill="#e8f1dc", width=2)
        else:
            draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill="#f1d59b", outline="#5b2418", width=2)

    coast = Image.new("RGBA", size, (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(coast)
    for poly in [land_poly, britain, northern_isles, iberia, italy, greece, asia_minor]:
        cdraw.line(poly + [poly[0]], fill=(229, 213, 168, 150), width=5, joint="curve")
        cdraw.line(poly + [poly[0]], fill=(82, 57, 31, 160), width=2, joint="curve")
    base = Image.alpha_composite(base.convert("RGBA"), coast).convert("RGB")

    vignette = Image.new("L", size, 0)
    vdraw = ImageDraw.Draw(vignette)
    for inset, alpha in [(0, 112), (18, 74), (42, 38)]:
        vdraw.rectangle((inset, inset, w - inset, h - inset), outline=alpha, width=12)
    vignette = vignette.filter(ImageFilter.GaussianBlur(20))
    edge = Image.new("RGB", size, "#8a6335")
    base = Image.composite(edge, base, vignette)
    return warm_finish(base, contrast=1.06, color=0.9)


def make_tidal_shore_art(size: tuple[int, int]) -> Image.Image:
    source_path = root_dir() / "graphic_book" / "assets" / "generated" / "1_4_1" / "seashore_source.jpg"
    if not source_path.exists():
        raise RuntimeError(f"Missing sourced scenic art: {source_path}")
    source = Image.open(source_path).convert("RGB")
    art = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS, centering=(0.52, 0.56))
    art = ImageEnhance.Contrast(art).enhance(1.08)
    art = ImageEnhance.Color(art).enhance(0.86)
    art = ImageEnhance.Sharpness(art).enhance(1.08)
    return warm_finish(art, contrast=1.04, color=0.88)


def make_eridanos_art(size: tuple[int, int]) -> Image.Image:
    source_path = root_dir() / "graphic_book" / "assets" / "generated" / "1_4_1" / "eridanos_heliades_generated.png"
    if not source_path.exists():
        raise RuntimeError(f"Missing generated Eridanos scenic art: {source_path}")
    source = Image.open(source_path).convert("RGB")
    art = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS, centering=(0.47, 0.52))
    art = ImageEnhance.Contrast(art).enhance(1.04)
    art = ImageEnhance.Color(art).enhance(0.90)
    art = ImageEnhance.Sharpness(art).enhance(1.08)
    return warm_finish(art, contrast=1.03, color=0.90)


def make_route_key(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((384, 214))
    draw = ImageDraw.Draw(panel)
    title_rect = (18, 14, panel.width - 18, 52)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "INVASION ROUTE",
            TITLE_FONT,
            max_size=21,
            min_size=14,
            padding=6,
            name="route-key:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (18, 62, panel.width - 18, panel.height - 18)
    source_path = root_dir() / "graphic_book" / "assets" / "generated" / "1_4_1" / "europe_1000_source.jpg"
    if not source_path.exists():
        raise RuntimeError(f"Missing sourced route-map art: {source_path}")
    source = Image.open(source_path).convert("RGB")
    map_crop = source.crop((470, 720, 1810, 1220))
    map_art = ImageOps.fit(
        map_crop,
        (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]),
        method=Image.Resampling.LANCZOS,
        centering=(0.55, 0.55),
    )
    map_art = ImageEnhance.Contrast(map_art).enhance(1.12)
    map_art = ImageEnhance.Color(map_art).enhance(0.82)
    map_art = Image.blend(map_art, Image.new("RGB", map_art.size, "#ead2a0"), 0.13)
    panel.paste(map_art, (map_rect[0], map_rect[1]))
    draw.rectangle(map_rect, outline=RULE, width=2)

    route = [(64, 122), (132, 112), (210, 122), (286, 118), (342, 142)]
    draw.line(route, fill="#552317", width=10, joint="curve")
    draw.line(route, fill=ROUTE, width=6, joint="curve")
    draw.line(route, fill=ROUTE_LIGHT, width=2, joint="curve")
    for idx, (x, y) in enumerate(route[1:], start=1):
        px, py = route[idx - 1]
        angle = math.atan2(y - py, x - px)
        left = (int(x - 14 * math.cos(angle) + 6 * math.sin(angle)), int(y - 14 * math.sin(angle) - 6 * math.cos(angle)))
        right = (int(x - 14 * math.cos(angle) - 6 * math.sin(angle)), int(y - 14 * math.sin(angle) + 6 * math.cos(angle)))
        draw.polygon([(x, y), left, right], fill=ROUTE_LIGHT, outline="#552317")
    for x, y in route:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=ROUTE, outline="#4b2419")

    labels = [
        ("ILLYRIA", (28, 152, 112, 180)),
        ("MACEDONIA", (132, 74, 250, 102)),
        ("THESSALY", (214, 146, 316, 174)),
        ("THERMOPYLAE", (238, 178, 370, 204)),
    ]
    for text, rect in labels:
        draw.rounded_rectangle(rect, radius=7, fill="#f4e0b2", outline="#b8945a", width=1)
        records.append(
            draw_fitted_text(
                draw,
                rect,
                text,
                DISPLAY_FONT,
                max_size=13,
                min_size=8,
                padding=4,
                name=f"route-key:{text}",
                align="center",
                spacing_ratio=0.04,
            )
        )
    return panel


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    main_rect = (454, 42, 1372, 682)
    main_art = make_outer_europe_atlas((main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]))
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle((13, 13, 13 + main_art.width, 13 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 1088)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.4.1",
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
            (24, 92, left_panel.width - 24, left_panel.height - 24),
            translation,
            BODY_FONT,
            max_size=18,
            min_size=12,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.17,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (650, 42, 1184, 118)
    title_panel = make_label("GALATAI AT EUROPE'S EDGE", title_rect, records, font_path=TITLE_FONT, max_size=26, min_size=15)

    label_specs = [
        ("OUTER SEA", (508, 156, 712, 210), (126, 302)),
        ("GALATAI / KELTOI", (716, 208, 1000, 262), (304, 358)),
        ("ERIDANOS / RHINE", (812, 312, 1108, 364), (392, 284)),
        ("IONIAN SEA", (1018, 574, 1244, 626), (624, 524)),
        ("THERMOPYLAE", (1134, 646, 1354, 698), (772, 564)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect, _ in label_specs:
        label_panels.append((make_label(text, rect, records, max_size=24, min_size=12), (rect[0], rect[1])))

    sea_note = make_note_panel(
        "Pausanias places the Galatai beside a vast unnavigable sea of tides and strange beasts.",
        (356, 94),
        "callout:outer-sea",
        records,
    )
    sea_note_xy = (982, 138)

    eridanos_note = make_note_panel(
        "The river Eridanos carries the myth of Phaethon's sisters into this northern geography.",
        (360, 96),
        "callout:eridanos",
        records,
    )
    eridanos_note_xy = (976, 392)

    invasion_note = make_note_panel(
        "The same passage turns from ethnography to invasion: Illyria, Macedonia, Thessaly, then the pass.",
        (428, 104),
        "callout:invasion",
        records,
    )
    invasion_note_xy = (476, 590)

    shore_panel = make_inset_panel(
        make_tidal_shore_art((408, 220)),
        "At the edge of Europe, the outer sea is defined by tide, distance, and marvels rather than a navigable route.",
        102,
        "caption:tidal-shore",
        records,
    )
    shore_xy = (468, 746)

    eridanos_panel = make_inset_panel(
        make_eridanos_art((396, 220)),
        "On the Eridanos, Pausanias preserves the story of Helios' daughters mourning Phaethon.",
        102,
        "caption:eridanos",
        records,
    )
    eridanos_xy = (936, 746)

    route_key = make_route_key(records)
    route_key_xy = (964, 490)

    # Leaders are drawn before panels and labels so they tuck behind the framed cards.
    draw_polyline_leader(draw, [(982, 184), (900, 184), (main_rect[0] + 126, main_rect[1] + 302)])
    draw_polyline_leader(draw, [(976, 438), (884, 438), (main_rect[0] + 392, main_rect[1] + 284)])
    draw_polyline_leader(draw, [(682, 590), (760, 552), (main_rect[0] + 704, main_rect[1] + 546)])
    draw_leader(draw, (main_rect[0] + 126, main_rect[1] + 302), (shore_xy[0] + 120, shore_xy[1]))
    draw_leader(draw, (main_rect[0] + 392, main_rect[1] + 284), (eridanos_xy[0] + 120, eridanos_xy[1]))
    draw_leader(draw, (main_rect[0] + 772, main_rect[1] + 564), (route_key_xy[0] + route_key.width - 48, route_key_xy[1] + route_key.height))

    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))
    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, sea_note, sea_note_xy)
    paste_with_shadow(page, eridanos_note, eridanos_note_xy)
    paste_with_shadow(page, invasion_note, invasion_note_xy)
    paste_with_shadow(page, route_key, route_key_xy)
    paste_with_shadow(page, shore_panel, shore_xy)
    paste_with_shadow(page, eridanos_panel, eridanos_xy)

    add_border(draw)
    validate_fit_records(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "approved_reference_pages": [
            "graphic_book/images/1/1/4.png",
            "graphic_book/images/1/1/5.png",
        ],
        "text_blocks_checked": len(records),
        "minimum_font_size_used": min(record.font_size for record in records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_4_1_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "4" / "1.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
