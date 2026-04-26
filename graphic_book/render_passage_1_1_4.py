#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


WIDTH = 1402
HEIGHT = 1122
PASSAGE_ID = "1.1.4"

PARCHMENT = "#efd9ab"
PARCHMENT_LIGHT = "#f7e8c8"
PARCHMENT_DEEP = "#d8bb86"
INK = "#2a1e13"
RULE = "#6f5130"
SEA = "#315f79"

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
    return Path(__file__).resolve().parents[1]


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


def crop_to_fill(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


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
            max_size=30,
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


def add_border(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((10, 10, WIDTH - 10, HEIGHT - 10), outline=RULE, width=3)
    draw.rectangle((24, 24, WIDTH - 24, HEIGHT - 24), outline="#9d7d4e", width=1)


def render_page(output_path: Path) -> dict[str, object]:
    translation = load_translation()
    records: list[FitRecord] = []

    page = make_parchment((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(page)

    map_rect = (454, 44, 1374, 768)
    map_art = crop_to_fill(root_dir() / "graphic_book/assets/generated/1_1_4/map.png", (map_rect[2] - map_rect[0], map_rect[3] - map_rect[1]))
    map_panel = framed_panel((map_art.width + 26, map_art.height + 26), fill=PARCHMENT_DEEP)
    map_panel.paste(map_art, (13, 13))
    ImageDraw.Draw(map_panel).rectangle((13, 13, 13 + map_art.width, 13 + map_art.height), outline=RULE, width=2)
    paste_with_shadow(page, map_panel, (map_rect[0] - 13, map_rect[1] - 13))

    left_panel_rect = (32, 36, 430, 522)
    left_panel = framed_panel((left_panel_rect[2] - left_panel_rect[0], left_panel_rect[3] - left_panel_rect[1]))
    left_draw = ImageDraw.Draw(left_panel)
    title_band = (18, 14, left_panel.width - 18, 70)
    left_draw.rounded_rectangle(title_band, radius=12, fill="#ead2a0", outline=RULE, width=2)
    records.append(
        draw_fitted_text(
            left_draw,
            title_band,
            "PASSAGE 1.1.4",
            TITLE_FONT,
            max_size=32,
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
            max_size=27,
            min_size=15,
            padding=8,
            name="panel:translation",
            spacing_ratio=0.18,
        )
    )
    paste_with_shadow(page, left_panel, (left_panel_rect[0], left_panel_rect[1]))

    title_rect = (540, 44, 902, 118)
    title_panel = make_label("MUNYCHIA AND PHALERUM", title_rect, records, font_path=TITLE_FONT)
    paste_with_shadow(page, title_panel, (title_rect[0], title_rect[1]))

    small_callout_rect = (742, 194, 986, 292)
    mid_callout_rect = (606, 774, 912, 906)
    lower_callout_rect = (518, 934, 930, 1046)

    munychia_art = crop_to_fill(root_dir() / "graphic_book/assets/generated/1_1_4/munychia.png", (348, 236))
    munychia_panel = make_inset_panel(
        munychia_art,
        "Munychia's harbor beneath the sanctuary of Artemis Munychia.",
        72,
        "caption:munychia",
        records,
    )
    munychia_xy = (988, 82)
    paste_with_shadow(page, munychia_panel, munychia_xy)

    phalerus_art = crop_to_fill(root_dir() / "graphic_book/assets/generated/1_1_4/phalerus_jason.png", (388, 224))
    phalerus_panel = make_inset_panel(
        phalerus_art,
        "Athenians said Phalerus sailed with Jason to Colchis.",
        70,
        "caption:phalerus_jason",
        records,
    )
    phalerus_xy = (34, 770)
    paste_with_shadow(page, phalerus_panel, phalerus_xy)

    phalerum_art = crop_to_fill(root_dir() / "graphic_book/assets/generated/1_1_4/phalerum.png", (404, 236))
    phalerum_panel = make_inset_panel(
        phalerum_art,
        "Phalerum's sacred shore: Demeter, Athena Sciras, Zeus, heroes, and the Hero altar.",
        80,
        "caption:phalerum_shore",
        records,
    )
    phalerum_xy = (934, 694)

    draw = ImageDraw.Draw(page)
    draw_leader(draw, (600, 372), (small_callout_rect[0], small_callout_rect[1] + 48))
    draw_leader(draw, (589, 412), (munychia_xy[0], munychia_xy[1] + 160))
    draw_leader(draw, (1118, 344), (phalerus_xy[0] + 428, phalerus_xy[1] + 92))
    draw_leader(draw, (1114, 346), (mid_callout_rect[0] + 34, mid_callout_rect[1] + 28))
    draw_leader(draw, (1116, 352), (phalerum_xy[0], phalerum_xy[1] + 122))
    draw_leader(draw, (1114, 360), (lower_callout_rect[2], lower_callout_rect[1] + 40))

    paste_with_shadow(page, phalerum_panel, phalerum_xy)

    small_callout = framed_panel((small_callout_rect[2] - small_callout_rect[0], small_callout_rect[3] - small_callout_rect[1]))
    small_draw = ImageDraw.Draw(small_callout)
    records.append(
        draw_fitted_text(
            small_draw,
            (14, 12, small_callout.width - 14, small_callout.height - 12),
            "One harbor lay at Munychia, beside the sanctuary of Artemis Munychia.",
            BODY_FONT,
            max_size=19,
            min_size=13,
            padding=4,
            name="callout:munychia",
            align="center",
            spacing_ratio=0.16,
        )
    )
    paste_with_shadow(page, small_callout, (small_callout_rect[0], small_callout_rect[1]))

    mid_callout = framed_panel((mid_callout_rect[2] - mid_callout_rect[0], mid_callout_rect[3] - mid_callout_rect[1]))
    mid_draw = ImageDraw.Draw(mid_callout)
    records.append(
        draw_fitted_text(
            mid_draw,
            (16, 12, mid_callout.width - 16, mid_callout.height - 12),
            "At Phalerum Pausanias notes Demeter, Athena Sciras, Zeus, and altars to Unknown Gods, heroes, the sons of Theseus, and Phalerus.",
            BODY_FONT,
            max_size=20,
            min_size=13,
            padding=4,
            name="callout:phalerum",
            align="center",
            spacing_ratio=0.16,
        )
    )
    paste_with_shadow(page, mid_callout, (mid_callout_rect[0], mid_callout_rect[1]))

    lower_callout = framed_panel((lower_callout_rect[2] - lower_callout_rect[0], lower_callout_rect[3] - lower_callout_rect[1]))
    lower_draw = ImageDraw.Draw(lower_callout)
    records.append(
        draw_fitted_text(
            lower_draw,
            (18, 12, lower_callout.width - 18, lower_callout.height - 12),
            "Local experts said the altar of the Hero belonged to Androgeus, son of Minos.",
            BODY_FONT,
            max_size=21,
            min_size=13,
            padding=4,
            name="callout:androgeus",
            align="center",
            spacing_ratio=0.16,
        )
    )
    paste_with_shadow(page, lower_callout, (lower_callout_rect[0], lower_callout_rect[1]))

    labels = [
        ("ATHENS", (776, 126, 956, 178)),
        ("PHALERUM", (1028, 424, 1232, 476)),
        ("MUNYCHIA", (522, 252, 724, 308)),
        ("PIRAEUS", (724, 470, 924, 528)),
        ("SARONIC GULF", (1110, 604, 1336, 666)),
    ]
    for text, rect in labels:
        label = make_label(text, rect, records)
        paste_with_shadow(page, label, (rect[0], rect[1]))

    add_border(draw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(output_path, quality=95)

    report = {
        "passage_id": PASSAGE_ID,
        "output_path": str(output_path),
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    report_path = root_dir() / "tmp" / "passage_1_1_4_layout_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    output_path = root_dir() / "graphic_book" / "images" / "1" / "1" / "4.png"
    report = render_page(output_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
