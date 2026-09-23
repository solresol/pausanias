#!/usr/bin/env python3
"""Render 1.23.10 as a central civic portrait with opposed prose."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_23_10"


def render(output: Path, preflight: bool = False) -> None:
    """Render the page, or validate its deterministic text geometry."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            ("1.23.10",),
        ).fetchone()[0]

    page = Image.new("RGB", (1800, 1600), "#f1ede3")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    art_rect = (520, 138, 1280, 1460)
    if not preflight:
        image = Image.open(ASSETS / "phormio_settlement.png").convert("RGB")
        fitted = ImageOps.fit(
            image,
            (art_rect[2] - art_rect[0], art_rect[3] - art_rect[1]),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
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
        fill: str = "#26363d",
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

    first, second = passage.split("When the Athenians elected", 1)
    second = "When the Athenians elected" + second
    text("passage-id", (24, 15, 415, 82), "PASSAGE 1.23.10", 31, 29, title=True)
    text(
        "title",
        (445, 15, 1776, 82),
        "PHORMIO: PRIVATE DEBT, PUBLIC COMMAND",
        40,
        32,
        title=True,
    )
    text(
        "heading-1",
        (24, 170, 485, 285),
        "1 · WITHDRAWAL TO PAIANIA",
        28,
        25,
        title=True,
    )
    text("translation-1", (24, 300, 485, 1185), first, 34, 29)
    text(
        "left-orientation",
        (24, 1240, 485, 1425),
        "PAIANIA · ATTICA\nRetirement from public life under debt",
        27,
        24,
        title=True,
    )
    text(
        "heading-2",
        (1315, 270, 1776, 385),
        "2 · THE COMMAND AND THE DEBTS",
        28,
        25,
        title=True,
    )
    text("translation-2", (1315, 400, 1776, 1335), second, 34, 29)
    text(
        "right-orientation",
        (1315, 1390, 1776, 1555),
        "ATHENS · NAVAL COMMAND\nThe fleet waits while the civic obstacle is removed",
        27,
        24,
        title=True,
    )
    text(
        "caption",
        (520, 1468, 1280, 1588),
        "An interpretive civic view of the Athenians settling Phormio's debts.",
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
        "passage_id": "1.23.10",
        "preflight": preflight,
        "translation_matches_sqlite": True,
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_23_10_layout_report.json").write_text(
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
        default=ROOT / "graphic_book/images/1/23/10.png",
    )
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
