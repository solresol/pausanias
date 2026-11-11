#!/usr/bin/env python3
"""A Panathenaic vessel on land beneath one broad, continuous reading band."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_1'
ART_RECT = (48, 596, 2552, 2200)
TRANSLATION_RECT = (64, 254, 2536, 564)
CAPTION = (
    'Athens, near the Areopagus: an interpretive display of the Panathenaic '
    'procession ship on land. Hull, rig, wheeled support and setting are '
    'conjectural. The Delian ship mentioned for comparison is not depicted; '
    'no exact ship design or display site is claimed.'
)


def render(output: Path, preflight: bool = False) -> None:
    """Fit every block first; refuse any overflow or loss of exported English."""
    snapshot_path()
    passage = load_translation('1.29.1')
    page = Image.new('RGB', (2600, 2400), '#f2eee7')
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

    measure('passage-id', (32, 20, 720, 120), 'PASSAGE 1.29.1', 46, 40, True)
    measure('title', (810, 20, 2568, 120), 'THE PANATHENAIC SHIP', 62, 46, True)
    measure('orientation', (32, 138, 2568, 226),
            'ATHENS | NEAR THE AREOPAGUS | A VESSEL FOR THE PROCESSION', 36, 30, True)
    measure('translation', TRANSLATION_RECT, passage, 58, 50)
    measure('interpretive-caption', (48, 2220, 2552, 2376), CAPTION, 36, 30)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == 'translation')
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Exact English lost words or source order')
    report = {
        'passage_id': '1.29.1', 'preflight': preflight, 'canvas': [2600, 2400],
        'art_rectangle': ART_RECT, 'translation_rectangles': [TRANSLATION_RECT],
        'reading_order': 'one continuous full-width English field above the image',
        'translation_exact': passage, 'translation_characters': len(passage),
        'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': 50,
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
    with Image.open(ASSETS / 'procession_ship.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#9b9390', width=2)
    draw.line((32, 236, 2568, 236), fill='#b7afaa', width=2)
    draw.line((64, 578, 2536, 578), fill='#b7afaa', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#30383e')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/29/1.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
