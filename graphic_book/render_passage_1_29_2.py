#!/usr/bin/env python3
"""Pair the Academy approach's sanctuaries with ordered, exact English."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_2'
ART_RECTS = ((48, 252, 1468, 1448), (1290, 1640, 2552, 2400))
BODY_RECTS = ((1530, 354, 2552, 1450), (48, 1740, 1216, 2490))
MINIMUM_BODY = 46
PADDING = 24


def render(output: Path, preflight: bool = False) -> None:
    """Measure every glyph before loading art; fail on overflow or lost English."""
    snapshot_path()
    passage = load_translation('1.29.2')
    first, boundary, rest = passage.partition(' In my opinion')
    if not boundary:
        raise RuntimeError('Expected exported sentence boundary missing')
    chunks = (first, boundary[1:] + rest)
    if ' '.join(chunks) != passage:
        raise RuntimeError('Exact source substring reassembly failed')
    page = Image.new('RGB', (2600, 2700), '#f0eee5')
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

    measure('passage-id', (32, 20, 730, 120), 'PASSAGE 1.29.2', 46, 40, True)
    measure('title', (790, 20, 2568, 120), 'ON THE ROAD TO THE ACADEMY', 58, 44, True)
    measure('orientation', (32, 138, 2568, 226),
            'ATHENS | APPROACH TO THE ACADEMY | SANCTUARIES OUTSIDE THE CITY', 34, 30, True)
    measure('reading-heading-1', (1530, 252, 2552, 342),
            '1  THE SACRED ENCLOSURE', 39, 32, True)
    measure('reading-heading-2', (48, 1640, 1216, 1730),
            '2  EPITHETS AND A TEMPLE', 39, 32, True)
    size = 56
    while size >= MINIMUM_BODY:
        try:
            for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
                fit_text_block(draw, rect, text, BODY_FONT, size, size, PADDING,
                               f'translation-{i+1}', .25)
            break
        except RuntimeError:
            size -= 1
    if size < MINIMUM_BODY:
        raise RuntimeError('Complete English cannot fit at the readable minimum')
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f'translation-{i+1}', rect, text, size, size)
    measure('artemis-caption', (48, 1464, 1468, 1590),
            'Artemis: imagined wooden images of Ariste and Kalliste within an enclosure.', 34, 30)
    measure('dionysus-caption', (1290, 2416, 2552, 2524),
            'The small temple for the yearly visit of Dionysus Eleuthereus.', 34, 30)
    measure('interpretive-note', (48, 2552, 2552, 2680),
            'Separate interpretive scenes, not a surveyed view. Image forms, precinct, temple, dress and placement are conjectural; the annual transfer is not depicted.', 34, 30)
    validate_fit_records(records)
    wrapped = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Exact English lost words or original order')
    report = {
        'passage_id': '1.29.2', 'preflight': preflight, 'canvas': [2600, 2700],
        'art_rectangles': ART_RECTS, 'translation_rectangles': BODY_RECTS,
        'reading_order': '1: upper right, then 2: lower left; each top-to-bottom',
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
    for rect, filename in zip(ART_RECTS, ('artemis_enclosure.png', 'dionysus_temple.png'), strict=True):
        with Image.open(ASSETS / filename) as source:
            art = ImageOps.fit(source.convert('RGB'),
                               (rect[2]-rect[0], rect[3]-rect[1]),
                               method=Image.Resampling.LANCZOS)
        page.paste(art, rect[:2])
        draw.rectangle(rect, outline='#929486', width=2)
    draw.line((32, 236, 2568, 236), fill='#b5b3a5', width=2)
    draw.line((48, 1612, 2552, 1612), fill='#b5b3a5', width=2)
    draw.line((48, 2540, 2552, 2540), fill='#b5b3a5', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#303c31')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/29/2.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
