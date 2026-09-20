#!/usr/bin/env python3
"""Render the 2026-09-21 replacement candidate for passage 1.16.3."""
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

from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block  # noqa: E402
from graphic_book.render_passage_1_10_1 import validate_fit_records  # noqa: E402

ASSETS = ROOT / "graphic_book/assets/generated/1_16_3"
RUN = "20260920T181257Z"


def load_translation() -> str:
    """Load the exact local SQLite translation."""
    with sqlite3.connect(ROOT / "pausanias.sqlite") as conn:
        row = conn.execute(
            "SELECT english_translation FROM translations WHERE passage_id = ?",
            ("1.16.3",),
        ).fetchone()
    if not row:
        raise RuntimeError("Missing translation for 1.16.3")
    return row[0]


def split_translation(passage: str) -> tuple[str, str]:
    """Split at the move from restitution to foundation."""
    marker = "It was also Seleucus"
    index = passage.index(marker)
    return passage[:index].rstrip(), passage[index:]


def render(output: Path | None, preflight: bool = False) -> None:
    """Validate layout and optionally render a non-canonical candidate."""
    passage = load_translation()
    prose_1, prose_2 = split_translation(passage)
    page = Image.new("RGB", (1800, 1500), "#f3eee2")
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []

    art_specs = (
        ("rev_20260920_seleucia.png", (24, 110, 1180, 850)),
        ("rev_20260920_apollo.png", (1210, 110, 1776, 455)),
        ("rev_20260920_babylon.png", (1210, 505, 1776, 850)),
    )
    if not preflight:
        for filename, rect in art_specs:
            source = ASSETS / filename
            if not source.exists():
                raise RuntimeError(f"Missing revision component: {source}")
            x0, y0, x1, y1 = rect
            fitted = ImageOps.fit(
                Image.open(source).convert("RGB"),
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
            draw.rectangle(rect, fill="#eee3cb")
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
        records.append(FitRecord(name, rect, record.font_path, record.font_size, actual, wrapped))

    text("passage-id", (24, 15, 390, 82), "PASSAGE 1.16.3", 31, 31, title=True)
    text(
        "title",
        (420, 15, 1776, 82),
        "SELEUCUS: RESTITUTION, FOUNDATION, PRESERVATION",
        37,
        31,
        title=True,
    )
    text("seleucia-label", (40, 126, 430, 184), "SELEUCIA · THE TIGRIS", 25, 23, title=True, box=True)
    text("apollo-label", (1226, 126, 1760, 184), "BRANCHIDAE · IONIA", 25, 23, title=True, box=True)
    text("babylon-label", (1226, 521, 1760, 579), "BABYLON · THE SANCTUARY OF BEL", 25, 23, title=True, box=True)
    text(
        "seleucia-caption",
        (24, 860, 1180, 945),
        "A new capital beside the Tigris receives Babylonian households; the scene is illustrative, not a recovered city plan.",
        27,
        24,
    )
    text(
        "side-caption",
        (1210, 860, 1776, 945),
        "Apollo restored at Branchidae; Babylon's older sacred community preserved.",
        25,
        23,
    )
    text("reading-1", (24, 965, 870, 1028), "1 · JUSTICE AND RESTITUTION", 27, 25, title=True)
    text("reading-2", (930, 965, 1776, 1028), "2 · FOUNDATION AND PRESERVATION", 27, 25, title=True)
    text("translation-1", (24, 1035, 870, 1476), prose_1, 33, 29)
    text("translation-2", (930, 1035, 1776, 1476), prose_2, 33, 29)

    validate_fit_records(records)
    reconstructed = " ".join(
        " ".join(record.text.split())
        for record in records
        if record.name.startswith("translation-")
    )
    assert reconstructed == " ".join(passage.split())

    report = {
        "passage_id": "1.16.3",
        "replacement_run": RUN,
        "preflight": preflight,
        "translation_matches_sqlite": True,
        "text_blocks_checked": len(records),
        "fit_records": [asdict(record) for record in records],
    }
    (ROOT / "tmp").mkdir(exist_ok=True)
    (ROOT / "tmp/passage_1_16_3_replacement_layout_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "fit_records"}))
    print("Font sizes:", [(record.name, record.font_size) for record in records])

    if not preflight:
        if output is None:
            raise RuntimeError("Replacement rendering requires explicit --output")
        if output.resolve() == (ROOT / "graphic_book/images/1/16/3.png").resolve():
            raise RuntimeError("Refusing to render directly over the canonical original")
        if output.exists():
            raise RuntimeError(f"Refusing to overwrite existing candidate: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        page.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preflight)
