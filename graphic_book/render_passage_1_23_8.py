#!/usr/bin/env python3
"""Render 1.23.8 as a bronze-horse panorama above two reading columns."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphic_book.render_passage_1_3_2 import (  # noqa: E402
    BODY_FONT,
    TITLE_FONT,
    FitRecord,
    fit_text_block,
)
from graphic_book.render_passage_1_10_1 import validate_fit_records  # noqa: E402

ASSETS = ROOT / "graphic_book/assets/generated/1_23_8"


def render(output: Path, preflight: bool = False) -> None:
    """Render the page, or validate its deterministic text geometry."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            ("1.23.8",),
        ).fetchone()[0]

    page = Image.new("RGB", (1800, 1500), "#f3eee2")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    art_rect = (24, 140, 1776, 1040)
    if not preflight:
        image = Image.open(ASSETS / "trojan_horse.png").convert("RGB")
        fitted = ImageOps.fit(
            image,
            (art_rect[2] - art_rect[0], art_rect[3] - art_rect[1]),
            method=Image.Resampling.LANCZOS,
        )
        page.paste(fitted, (art_rect[0], art_rect[1]))

    def text(
        name: str,
        rect: tuple[int, int, int, int],
        content: str,
        size: int,
        minimum: int,
        *,
        title: bool = False,
        fill: str = "#28343b",
    ) -> None:
        font, wrapped, _, record = fit_text_block(
            draw,
            rect,
            content,
            TITLE_FONT if title else BODY_FONT,
            size,
            minimum,
            12,
            name,
            spacing_ratio=0.18,
        )
        spacing = max(2, round(record.font_size * 0.18))
        raw = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 12 - raw[0], rect[1] + 12 - raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (
            actual[0] < rect[0] + 12
            or actual[1] < rect[1] + 12
            or actual[2] > rect[2] - 12
            or actual[3] > rect[3] - 12
        ):
            raise RuntimeError(f"{name}: overflow")
        draw.multiline_text(xy, wrapped, font=font, spacing=spacing, fill=fill)
        records.append(
            FitRecord(name, rect, record.font_path, record.font_size, actual, wrapped)
        )

    first, second = passage.split("It is told", 1)
    second = "It is told" + second
    text("passage-id", (24, 15, 410, 82), "PASSAGE 1.23.8", 31, 31, title=True)
    text(
        "title",
        (440, 15, 1776, 82),
        "THE BRONZE HORSE AND THE HIDDEN WARRIORS",
        40,
        34,
        title=True,
    )
    text(
        "orientation",
        (24, 86, 1776, 136),
        "ATHENS · THE ACROPOLIS · A BRONZE DEDICATION",
        28,
        25,
        title=True,
    )
    text(
        "art-caption",
        (24, 1048, 1776, 1112),
        "Pausanias describes the bronze work itself as showing Greek warriors peering from the horse.",
        29,
        26,
    )
    text(
        "reading-1",
        (24, 1120, 866, 1175),
        "1 · THE PURPOSE OF THE HORSE",
        28,
        25,
        title=True,
    )
    text("translation-1", (24, 1180, 866, 1476), first, 33, 29)
    text(
        "reading-2",
        (920, 1120, 1776, 1175),
        "2 · THE FIGURES IN BRONZE",
        28,
        25,
        title=True,
    )
    text("translation-2", (920, 1180, 1776, 1476), second, 33, 29)

    validate_fit_records(records)
    reconstructed = " ".join(
        " ".join(record.text.split())
        for record in records
        if record.name.startswith("translation-")
    )
    assert reconstructed == " ".join(passage.split())

    report = {
        "passage_id": "1.23.8",
        "preflight": preflight,
        "translation_matches_sqlite": True,
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_23_8_layout_report.json").write_text(
        json.dumps(report, indent=2)
    )
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    print("Font sizes:", [(record.name, record.font_size) for record in records])

    if not preflight:
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite existing output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "graphic_book/images/1/23/8.png",
    )
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
