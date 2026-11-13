#!/usr/bin/env python3
"""Frame a conjectural tomb-road portrait with exact, ordered prose wings."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_3'
CANVAS = (3000, 2460)
ART_RECT = (810, 280, 2190, 2200)
BODY_RECTS = ((50, 602, 750, 1880), (2250, 462, 2950, 2110))
MINIMUM_BODY = 48
PADDING = 24


def render(output: Path, preflight: bool = False) -> None:
    """Measure all text before reading art and reject any lost or clipped glyph."""
    snapshot_path()
    passage = load_translation('1.29.3')
    first, boundary, rest = passage.partition(' for it was he')
    if not boundary:
        raise RuntimeError('Expected exported clause boundary missing')
    chunks = (first, boundary[1:] + rest)
    if ' '.join(chunks) != passage:
        raise RuntimeError('Exact source substring reassembly failed')
    page = Image.new('RGB', CANVAS, '#efede4')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, PADDING, name, .25,
        )
        spacing = max(2, round(fit.font_size * .25))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + PADDING - bbox[0], rect[1] + PADDING - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + PADDING or actual[1] < rect[1] + PADDING
                or actual[2] > rect[2] - PADDING or actual[3] > rect[3] - PADDING):
            raise RuntimeError(name + ': glyphs overflow padded rectangle')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (32, 20, 760, 130), 'PASSAGE 1.29.3', 52, 42, True)
    measure('title', (800, 20, 2968, 130), 'THRASYBULUS AND RECONCILIATION', 66, 52, True)
    measure('orientation', (32, 146, 2968, 246),
            'ATHENS | THE TOMBS ON THE APPROACH TO THE ACADEMY | AN INTERPRETIVE VIEW', 38, 32, True)
    measure('reading-heading-1', (50, 450, 750, 570), '1  THE FIRST TOMB', 43, 34, True)
    measure('reading-heading-2', (2250, 310, 2950, 430), '2  THE RECONCILER', 43, 34, True)
    size = 57
    while size >= MINIMUM_BODY:
        try:
            for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
                fit_text_block(draw, rect, text, BODY_FONT, size, size, PADDING,
                               f'translation-{i+1}', .25)
            break
        except RuntimeError:
            size -= 1
    if size < MINIMUM_BODY:
        raise RuntimeError('Full English cannot fit at the readable minimum')
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f'translation-{i+1}', rect, text, size, size)
    measure('art-caption', (810, 2216, 2190, 2368),
            'An imagined monument for Thrasybulus beside the tomb-lined Academy approach.', 36, 32)
    measure('interpretive-note', (50, 2374, 2950, 2454),
            'Monument form, road, other tombs, dress and placement are conjectural; no surviving tomb or exact site is identified.', 30, 27)
    validate_fit_records(records)
    wrapped = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('English lost words or original order')
    report = {
        'passage_id': '1.29.3', 'preflight': preflight, 'canvas': CANVAS,
        'art_rectangle': ART_RECT, 'translation_rectangles': BODY_RECTS,
        'reading_order': '1: left wing top-to-bottom, then 2: right wing top-to-bottom',
        'translation_exact': passage, 'translation_chunks': chunks,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': MINIMUM_BODY,
        'body_font_size': size, 'padding': PADDING,
        'text_blocks_checked': len(records), 'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('fit_records', 'translation_exact', 'translation_chunks')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'thrasybulus_tomb.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#91948d', width=3)
    draw.line((32, 258, 2968, 258), fill='#b4b0a5', width=2)
    draw.line((50, 2358, 750, 2358), fill='#b4b0a5', width=2)
    draw.line((2250, 2358, 2950, 2358), fill='#b4b0a5', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#333c43')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/29/3.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
