#!/usr/bin/env python3
"""Render 1.23.9 as staggered prose, statue, tomb-road, and prose blocks."""
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

ASSETS = ROOT / "graphic_book/assets/generated/1_23_9"


def render(output: Path, preflight: bool = False) -> None:
    """Render the page, or validate its deterministic text geometry."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        passage = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            ("1.23.9",),
        ).fetchone()[0]

    page = Image.new("RGB", (1800, 1600), "#f2eee4")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    art = [
        ("epicharinos.png", (800, 125, 1776, 735)),
        ("melitid_gate.png", (24, 840, 1050, 1510)),
    ]
    if not preflight:
        for filename, rect in art:
            image = Image.open(ASSETS / filename).convert("RGB")
            fitted = ImageOps.fit(
                image,
                (rect[2] - rect[0], rect[3] - rect[1]),
                method=Image.Resampling.LANCZOS,
            )
            page.paste(fitted, (rect[0], rect[1]))

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

    first, second = passage.split("There is also", 1)
    second = "There is also" + second
    text("passage-id", (24, 15, 410, 82), "PASSAGE 1.23.9", 31, 31, title=True)
    text(
        "title",
        (440, 15, 1776, 82),
        "THE RUNNER, THE DECREE AND THE TOMB",
        40,
        34,
        title=True,
    )
    text(
        "heading-1",
        (24, 145, 760, 210),
        "1 · EPICHARINOS IN BRONZE",
        29,
        26,
        title=True,
    )
    text("translation-1", (24, 225, 760, 690), first, 34, 29)
    text(
        "runner-orientation",
        (800, 745, 1776, 790),
        "ATHENS · THE ACROPOLIS · BEYOND THE BRONZE HORSE",
        27,
        24,
        title=True,
    )
    text(
        "runner-caption",
        (800, 785, 1776, 836),
        "An interpretive study of Kritias' statue of the hoplitodromos Epicharinos.",
        27,
        23,
    )
    text(
        "tomb-orientation",
        (24, 1512, 1050, 1555),
        "ATHENS · NEAR THE MELITID GATE",
        27,
        24,
        title=True,
    )
    text(
        "tomb-caption",
        (24, 1552, 1050, 1600),
        "Pausanias locates Thucydides' tomb not far from the gate.",
        27,
        23,
    )
    text(
        "heading-2",
        (1090, 840, 1776, 905),
        "2 · OINOBIOS AND THUCYDIDES",
        29,
        26,
        title=True,
    )
    text("translation-2", (1090, 920, 1776, 1515), second, 34, 29)

    validate_fit_records(records)
    reconstructed = " ".join(
        " ".join(record.text.split())
        for record in records
        if record.name.startswith("translation-")
    )
    assert reconstructed == " ".join(passage.split())

    report = {
        "passage_id": "1.23.9",
        "preflight": preflight,
        "translation_matches_sqlite": True,
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_23_9_layout_report.json").write_text(
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
        default=ROOT / "graphic_book/images/1/23/9.png",
    )
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
