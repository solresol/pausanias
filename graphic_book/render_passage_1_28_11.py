#!/usr/bin/env python3
"""Phreattys: one shoreline scene surrounding a lower-left reading island."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from graphic_book_corpus import load_translation, snapshot_path
from graphic_book_fonts import BODY_FONT, TITLE_FONT
from graphic_book.render_passage_1_3_2 import FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records

ASSETS = ROOT / 'graphic_book/assets/generated/1_28_11'
ART_RECT = (48, 240, 2352, 2310)
READING_PANEL = (80, 1190, 1490, 2276)
TRANSLATION_RECT = (100, 1292, 1470, 2250)
CAPTION = (
    'Phreattys, on the coast of Piraeus: an imagined defence spoken from a ship '
    'to listeners ashore. Shoreline, vessel, dress and gathering are conjectural; '
    'no precise court site or individual trial is identified.'
)


def render(output: Path, preflight: bool = False) -> None:
    """Measure all fields before drawing; refuse overflow or altered English."""
    snapshot_path()
    passage = load_translation('1.28.11')
    page = Image.new('RGB', (2400, 2580), '#f2eee6')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 24, name, .25,
        )
        spacing = max(2, round(fit.font_size * .25))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 24 - bbox[0], rect[1] + 24 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 24 or actual[1] < rect[1] + 24
                or actual[2] > rect[2] - 24 or actual[3] > rect[3] - 24):
            raise RuntimeError(name + ': glyphs overflow padded rectangle')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (32, 16, 720, 116), 'PASSAGE 1.28.11', 44, 38, True)
    measure('title', (750, 16, 2368, 116), 'A DEFENCE ACROSS THE WATER', 59, 44, True)
    measure('orientation', (32, 126, 2368, 214),
            'PIRAEUS | PHREATTYS | A SHIP AND THE LISTENING SHORE', 34, 28, True)
    measure('reading-heading', (100, 1202, 1470, 1284),
            'PAUSANIAS\u2019S ACCOUNT', 34, 30, True)
    measure('translation', TRANSLATION_RECT, passage, 52, 46)
    measure('interpretive-caption', (48, 2340, 2352, 2540), CAPTION, 34, 30)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == 'translation')
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Exact English lost words or source order')
    report = {
        'passage_id': '1.28.11', 'preflight': preflight, 'canvas': [2400, 2580],
        'art_rectangle': ART_RECT, 'reading_panel': READING_PANEL,
        'translation_rectangles': [TRANSLATION_RECT],
        'reading_order': 'one continuous top-to-bottom lower-left English field',
        'translation_exact': passage, 'translation_characters': len(passage),
        'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': 46,
        'body_font_sizes': [r.font_size for r in records if r.name == 'translation'],
        'padding': 24, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('fit_records','translation_exact')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'phreattys.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#a09a8b', width=2)
    draw.rectangle(READING_PANEL, fill='#f2eee6', outline='#a09a8b', width=2)
    draw.line((32, 222, 2368, 222), fill='#b9b1a1', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#2c383c')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/28/11.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
