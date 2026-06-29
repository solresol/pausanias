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
PASSAGE_ID = "1.3.2"

PARCHMENT = "#efd9ab"
PARCHMENT_LIGHT = "#f7e8c8"
PARCHMENT_DEEP = "#d8bb86"
INK = "#2a1e13"
RULE = "#6f5130"
ROAD = "#b8823f"
ROAD_LIGHT = "#f4ead6"
WALL = "#8c6a3f"
CITY = "#cfb07a"
CITY_LIGHT = "#f6e7c0"
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


def make_locator_map(records: list[FitRecord]) -> Image.Image:
    panel = framed_panel((396, 330))
    draw = ImageDraw.Draw(panel)

    title_rect = (18, 14, panel.width - 18, 58)
    draw.rounded_rectangle(title_rect, radius=10, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            draw,
            title_rect,
            "NORTH-WEST AGORA",
            TITLE_FONT,
            max_size=24,
            min_size=16,
            padding=8,
            name="map:title",
            align="center",
            spacing_ratio=0.08,
        )
    )

    map_rect = (22, 70, panel.width - 22, 240)
    map_size = (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1])
    relief = Image.effect_noise(map_size, 24).convert("L")
    relief = ImageOps.autocontrast(relief)
    map_base = ImageOps.colorize(relief, black="#c4a26c", white="#f4e5bd").convert("RGBA")
    paving = Image.new("RGBA", map_size, (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(paving)
    for x in range(-map_size[1], map_size[0], 34):
        pdraw.line((x, 0, x + map_size[1], map_size[1]), fill=(126, 94, 52, 32), width=1)
    for y in range(12, map_size[1], 28):
        pdraw.line((0, y, map_size[0], y - 18), fill=(255, 244, 213, 26), width=1)
    map_base.alpha_composite(paving)
    mask = Image.new("L", map_size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, map_size[0] - 1, map_size[1] - 1), radius=16, fill=255)
    map_base.putalpha(mask)
    panel.alpha_composite(map_base, map_rect[:2], source=(0, 0, map_size[0], map_size[1]))
    draw.rounded_rectangle(map_rect, radius=16, outline="#aa8651", width=2)

    road_band = [
        (map_rect[0] + 22, map_rect[1] + 158),
        (map_rect[0] + 96, map_rect[1] + 136),
        (map_rect[0] + 210, map_rect[1] + 116),
        (map_rect[0] + 340, map_rect[1] + 126),
    ]
    draw.line(road_band, fill=ROAD, width=18)
    draw.line(road_band, fill=ROAD_LIGHT, width=5)

    royal_stoa = (map_rect[0] + 170, map_rect[1] + 20, map_rect[0] + 336, map_rect[1] + 56)
    stoa_zeus = (map_rect[0] + 138, map_rect[1] + 154, map_rect[0] + 324, map_rect[1] + 194)
    statue_court = (map_rect[0] + 164, map_rect[1] + 76, map_rect[0] + 304, map_rect[1] + 138)
    altar = (map_rect[0] + 214, map_rect[1] + 90, map_rect[0] + 252, map_rect[1] + 124)
    acropolis = [(map_rect[0] + 44, map_rect[1] + 36), (map_rect[0] + 86, map_rect[1] + 12), (map_rect[0] + 104, map_rect[1] + 42)]

    for shape in [royal_stoa, stoa_zeus, statue_court, altar]:
        shadow = (shape[0] + 3, shape[1] + 4, shape[2] + 3, shape[3] + 4)
        draw.rounded_rectangle(shadow, radius=8, fill="#6f513044")
    draw.polygon([(x + 3, y + 4) for x, y in acropolis], fill="#6f513044")
    draw.rounded_rectangle(royal_stoa, radius=8, fill=CITY, outline=RULE, width=2)
    draw.rounded_rectangle((royal_stoa[0] + 5, royal_stoa[1] + 6, royal_stoa[2] - 5, royal_stoa[3] - 6), radius=5, outline=CITY_LIGHT, width=1)
    draw.rounded_rectangle(stoa_zeus, radius=8, fill=CITY, outline=RULE, width=2)
    draw.rounded_rectangle((stoa_zeus[0] + 5, stoa_zeus[1] + 6, stoa_zeus[2] - 5, stoa_zeus[3] - 6), radius=5, outline=CITY_LIGHT, width=1)
    draw.rounded_rectangle(statue_court, radius=10, fill="#e3c891", outline=RULE, width=2)
    draw.rounded_rectangle(altar, radius=6, fill="#c29d67", outline=RULE, width=2)
    draw.polygon(acropolis, fill="#a77e49", outline=RULE)
    draw.line((acropolis[0][0], acropolis[1][1], acropolis[2][0], acropolis[1][1]), fill="#d8bb86", width=2)

    for x, y in [(190, 98), (214, 96), (238, 98), (262, 100), (246, 118)]:
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=BRONZE)

    label_specs = [
        ("ACROPOLIS", (map_rect[0] + 18, map_rect[1] + 46, map_rect[0] + 120, map_rect[1] + 74), "map:acropolis"),
        ("ROYAL STOA", (map_rect[0] + 182, map_rect[1] - 2, map_rect[0] + 328, map_rect[1] + 24), "map:royal"),
        ("STATUE COURT", (map_rect[0] + 152, map_rect[1] + 58, map_rect[0] + 316, map_rect[1] + 84), "map:statues"),
        ("ALTAR", (map_rect[0] + 204, map_rect[1] + 126, map_rect[0] + 262, map_rect[1] + 152), "map:altar"),
        ("STOA OF ZEUS", (map_rect[0] + 168, map_rect[1] + 158, map_rect[0] + 322, map_rect[1] + 184), "map:zeus"),
        ("WESTERN ROAD", (map_rect[0] + 22, map_rect[1] + 132, map_rect[0] + 150, map_rect[1] + 160), "map:road"),
    ]
    for text, rect, name in label_specs:
        draw.rounded_rectangle(rect, radius=8, fill=CITY_LIGHT, outline="#b8945a", width=1)
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

    caption_rect = (18, 258, panel.width - 18, panel.height - 18)
    records.append(
        draw_fitted_text(
            draw,
            caption_rect,
            "Locator map: the Royal Stoa stood at the north-west Agora, beside the statue court, altar, and Stoa of Zeus.",
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

    main_rect = (454, 44, 1372, 690)
    main_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_2/main_northwest_agora.png",
        (main_rect[2] - main_rect[0], main_rect[3] - main_rect[1]),
        centering=(0.54, 0.46),
    )
    main_panel = framed_panel((main_art.width + 26, main_art.height + 26), fill=PARCHMENT_DEEP)
    main_panel.paste(main_art, (13, 13))
    ImageDraw.Draw(main_panel).rectangle((13, 13, 13 + main_art.width, 13 + main_art.height), outline=RULE, width=2)
    paste_with_shadow(page, main_panel, (main_rect[0] - 13, main_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 618)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.3.2",
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

    title_rect = (610, 42, 1208, 118)
    title_panel = make_label("STATUES BY THE ROYAL STOA", title_rect, records, font_path=TITLE_FONT, max_size=27, min_size=15)
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    locator_panel = make_locator_map(records)
    locator_xy = (34, 746)

    fleet_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_2/evagoras_triremes.png",
        (420, 214),
        centering=(0.56, 0.5),
    )
    fleet_panel = make_inset_panel(
        fleet_art,
        "Evagoras of Salamis in Cyprus, claimed as Athenian kin through Teucer and Cinyras, secured Phoenician triremes for Conon.",
        118,
        "caption:fleet",
        records,
    )
    fleet_xy = (468, 742)

    zeus_art = crop_to_fill(
        root_dir() / "graphic_book/assets/generated/1_3_2/zeus_hadrian.png",
        (388, 230),
        centering=(0.54, 0.42),
    )
    zeus_panel = make_inset_panel(
        zeus_art,
        "Pausanias groups Zeus Eleutherios and Hadrian together as figures of liberation and benefaction in the civic heart of Athens.",
        108,
        "caption:zeus",
        records,
    )
    zeus_xy = (964, 736)

    labels = [
        ("ACROPOLIS", (866, 88, 1134, 142)),
        ("ROYAL STOA", (666, 236, 926, 290)),
        ("STATUE COURT", (850, 496, 1128, 550)),
        ("STOA OF ZEUS", (1066, 368, 1328, 422)),
    ]
    label_panels: list[tuple[Image.Image, tuple[int, int]]] = []
    for text, rect in labels:
        label = make_label(text, rect, records, max_size=25, min_size=13)
        label_panels.append((label, (rect[0], rect[1])))

    conon_panel = make_note_panel(
        "Conon, Timotheus, and Evagoras marked alliance, naval recovery, and Cypriot aid in Athens' civic memory.",
        (346, 98),
        "callout:conon",
        records,
    )
    conon_xy = (972, 174)

    zeus_note_panel = make_note_panel(
        "Nearby stood Zeus Eleutherios and Hadrian: liberation and later imperial favor set side by side.",
        (350, 96),
        "callout:zeus-note",
        records,
    )
    zeus_note_xy = (970, 544)

    draw = ImageDraw.Draw(page)
    draw_polyline_leader(draw, [(972, 222), (936, 222), (936, 486), (986, 486)])
    draw_polyline_leader(draw, [(970, 592), (936, 592), (936, 454), (1132, 454)])
    draw_leader(draw, (520, 840), (666, 598))
    draw_leader(draw, (1132, 600), (1162, 544))
    draw_leader(draw, (968, 482), (fleet_xy[0] + fleet_panel.width // 2, fleet_xy[1]))
    draw_leader(draw, (1182, 594), (zeus_xy[0], zeus_xy[1] + 118))

    paste_with_shadow(page, locator_panel, locator_xy)
    paste_with_shadow(page, fleet_panel, fleet_xy)
    paste_with_shadow(page, zeus_panel, zeus_xy)
    for label, xy in label_panels:
        paste_with_shadow(page, label, xy)
    paste_with_shadow(page, conon_panel, conon_xy)
    paste_with_shadow(page, zeus_note_panel, zeus_note_xy)

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_3_2_layout_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "3" / "2.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
