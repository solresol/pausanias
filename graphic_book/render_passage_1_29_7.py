#!/usr/bin/env python3
"""An immersive public-grave scene around a lower-right reading island."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_7'
CANVAS = (3200, 3000)
ART_RECT = (56, 280, 3144, 2750)
READING_ISLAND = (1450, 1210, 3144, 2750)
BODY_RECT = (1490, 1370, 3104, 2680)
PADDING = 26
MINIMUM_BODY = 50


def render(output: Path, preflight: bool = False) -> None:
    """Fit all exact local type first, then composite one generated raster."""
    snapshot_path()
    passage = load_translation('1.29.7')
    page = Image.new('RGB', CANVAS, '#f1efe9')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, PADDING, name, .25,
        )
        spacing = max(2, round(fit.font_size * .25))
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + PADDING - box[0], rect[1] + PADDING - box[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + PADDING or actual[1] < rect[1] + PADDING
                or actual[2] > rect[2] - PADDING or actual[3] > rect[3] - PADDING):
            raise RuntimeError(name + ': actual glyph bounds overflow padded rectangle')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (32, 20, 850, 134), 'PASSAGE 1.29.7', 58, 48, True)
    measure('title', (940, 20, 3168, 134), 'NAMES IN PUBLIC MEMORY', 76, 58, True)
    measure('orientation', (32, 148, 3168, 246),
            'ATHENS | ACADEMY ROAD | THE PUBLIC WAR GRAVES', 46, 36, True)
    measure('reading-heading', (1490, 1250, 3104, 1350),
            "PAUSANIAS'S ACCOUNT", 48, 38, True)
    measure('translation', BODY_RECT, passage, 58, MINIMUM_BODY)
    measure('art-caption', (56, 2780, 3144, 2960),
            'An imagined public memorial beside the Academy road. Monument forms, visitors, '
            'dress and placement are conjectural; no surviving tomb or individual is identified, '
            'and the reported inscriptions are not reconstructed.', 43, 36)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == 'translation')
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('The full English passage lost wording or original order')
    report = {
        'passage_id': '1.29.7', 'preflight': preflight, 'canvas': CANVAS,
        'art_rectangle': ART_RECT, 'reading_island': READING_ISLAND,
        'translation_rectangle': BODY_RECT,
        'reading_order': 'one uninterrupted lower-right English field',
        'translation_exact': passage, 'translation_characters': len(passage),
        'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': MINIMUM_BODY,
        'body_font_size': next(r.font_size for r in records if r.name == 'translation'),
        'padding': PADDING, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('fit_records', 'translation_exact')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'public_memorial.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#8f9698', width=3)
    draw.rectangle(READING_ISLAND, fill='#f1efe9')
    draw.line((1450, 1210, 3144, 1210), fill='#8f9698', width=3)
    draw.line((1450, 1210, 1450, 2750), fill='#8f9698', width=3)
    draw.line((56, 260, 3144, 260), fill='#b6b6ae', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#303c42')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/29/7.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
