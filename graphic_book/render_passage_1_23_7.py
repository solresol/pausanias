#!/usr/bin/env python3
"""Render 1.23.7 as an unequal Acropolis and Brauron architectural diptych."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_23_7"


def render(output: Path, preflight: bool = False) -> None:
    """Render the page, or validate all deterministic text geometry."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            ("1.23.7",),
        ).fetchone()[0]

    page = Image.new("RGB", (1800, 1600), "#f3eee2")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    main_rect = (24, 125, 900, 1450)
    brauron_rect = (940, 820, 1776, 1450)
    if not preflight:
        for filename, rect in (
            ("acropolis_court.png", main_rect),
            ("brauron_sanctuary.png", brauron_rect),
        ):
            x0, y0, x1, y1 = rect
            image = Image.open(ASSETS / filename).convert("RGB")
            fitted = ImageOps.fit(
                image,
                (x1 - x0, y1 - y0),
                method=Image.Resampling.LANCZOS,
            )
            page.paste(fitted, (x0, y0))

    def text(
        name: str,
        rect: tuple[int, int, int, int],
        content: str,
        size: int,
        minimum: int,
        *,
        title: bool = False,
        fill: str = "#26343b",
        box: bool = False,
    ) -> None:
        if box:
            draw.rectangle(rect, fill="#f3eee2")
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

    text("passage-id", (24, 15, 410, 85), "PASSAGE 1.23.7", 31, 31, title=True)
    text(
        "title",
        (440, 15, 1776, 85),
        "BRONZE, MARBLE AND THE BRAURONIAN GODDESS",
        37,
        31,
        title=True,
    )
    text(
        "orientation-acropolis",
        (940, 125, 1776, 205),
        "ATHENS · THE ACROPOLIS · SOUTH OF THE PROPYLAIA",
        26,
        23,
        title=True,
    )
    text("translation-1", (940, 220, 1776, 690), passage, 33, 29)
    text(
        "acropolis-caption",
        (24, 1460, 900, 1576),
        "The bronze boy and Perseus stand near the city sanctuary of Artemis Brauronia; appearances and arrangement are illustrative.",
        27,
        24,
    )
    text(
        "brauron-label",
        (940, 720, 1776, 805),
        "BRAURON · EASTERN ATTICA",
        27,
        24,
        title=True,
    )
    text(
        "brauron-caption",
        (940, 1460, 1776, 1576),
        "The principal sanctuary at Brauron, where Pausanias reports the ancient wooden image.",
        27,
        24,
    )

    validate_fit_records(records)
    reconstructed = " ".join(
        " ".join(record.text.split())
        for record in records
        if record.name.startswith("translation-")
    )
    assert reconstructed == " ".join(passage.split())

    report = {
        "passage_id": "1.23.7",
        "preflight": preflight,
        "translation_matches_sqlite": True,
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_23_7_layout_report.json").write_text(
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
        default=ROOT / "graphic_book/images/1/23/7.png",
    )
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
