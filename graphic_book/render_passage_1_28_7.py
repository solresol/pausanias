#!/usr/bin/env python3
"""Render a conjectural tomb study between two ordered English reading bands."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_28_7'
ART_RECT = (48, 500, 2352, 1730)
FIRST_RECT = (64, 326, 2336, 474)
REST_RECT = (64, 1950, 2336, 2358)
CAPTION = (
    'A conjectural tomb study in the Semnai enclosure. The monument and setting '
    'are imagined; no surviving tomb is identified.'
)


def render(output: Path, preflight: bool = False) -> None:
    """Measure every padded glyph rectangle and preserve exact English order."""
    snapshot_path()
    passage = load_translation('1.28.7')
    split = passage.index('. ') + 1
    first, rest = passage[:split], passage[split + 1:]
    if first + ' ' + rest != passage:
        raise RuntimeError('The two reading fields must rejoin byte-for-byte')
    page = Image.new('RGB', (2400, 2400), '#f1eee5')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 20, name, .24,
        )
        spacing = max(2, round(fit.font_size * .24))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 20 - bbox[0], rect[1] + 20 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 20 or actual[1] < rect[1] + 20
                or actual[2] > rect[2] - 20 or actual[3] > rect[3] - 20):
            raise RuntimeError(name + ': glyphs overflow padded target')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (42, 24, 680, 120), 'PASSAGE 1.28.7', 44, 38, True)
    measure('title', (730, 24, 2358, 120), 'OEDIPUS: A DISPUTED TOMB', 64, 46, True)
    measure('orientation', (42, 134, 2358, 214),
            'ATHENS | THE SEMNAI ENCLOSURE, NEAR THE AREOPAGUS', 36, 30, True)
    measure('first-heading', (64, 238, 2336, 314), '1  THE MEMORIAL', 36, 30, True)
    measure('english-1', FIRST_RECT, first, 56, 46)
    measure('interpretive-caption', (48, 1750, 2352, 1858), CAPTION, 34, 28)
    measure('second-heading', (64, 1866, 2336, 1940),
            '2  PAUSANIAS WEIGHS THE ACCOUNTS', 36, 30, True)
    measure('english-2', REST_RECT, rest, 56, 46)
    validate_fit_records(records)
    normalized = ' '.join(' '.join(r.text.split()) for r in records if r.name.startswith('english-'))
    if normalized != ' '.join(passage.split()):
        raise RuntimeError('Full English must remain in its original order')
    report = {
        'passage_id': '1.28.7', 'preflight': preflight, 'canvas': [2400, 2400],
        'art_rectangle': ART_RECT, 'translation_rectangles': [FIRST_RECT, REST_RECT],
        'reading_order': '1 above the image, then 2 below; split after the first sentence',
        'translation_exact': passage, 'translation_characters': len(passage),
        'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'split_rejoins_byte_identically': True,
        'minimum_body_font_size': 46,
        'body_font_sizes': [r.font_size for r in records if r.name.startswith('english-')],
        'padding': 20, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('fit_records', 'translation_exact')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'tomb_study.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#a29a80', width=2)
    draw.line((42, 226, 2358, 226), fill='#a8a18e', width=2)
    draw.line((64, 1864, 2336, 1864), fill='#b7b09d', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#343b34')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/28/7.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
