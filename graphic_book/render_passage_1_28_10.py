#!/usr/bin/env python3
"""An axe study between the two jurisdictions in the exact exported account."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_28_10'
ART_RECT = (48, 720, 2352, 1820)
TEXT_RECTS = [(64, 324, 2336, 688), (64, 2070, 2336, 2554)]
CAPTION = (
    'The axe as an object of judgment in the Prytaneion tradition. '
    'Tool, support and architectural setting are conjectural; no surviving '
    'axe or excavated court is identified. The killing and sacrifice are not depicted.'
)


def render(output: Path, preflight: bool = False) -> None:
    """Measure every field before drawing and refuse any clipped source text."""
    snapshot_path()
    passage = load_translation('1.28.10')
    split = passage.index('As for the procedure')
    parts = [passage[:split], passage[split:]]
    if ''.join(parts) != passage:
        raise RuntimeError('Translation split changed the exported source')
    page = Image.new('RGB', (2400, 2600), '#eff0e9')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 20, name, .26,
        )
        spacing = max(2, round(fit.font_size * .26))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 20 - bbox[0], rect[1] + 20 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 20 or actual[1] < rect[1] + 20
                or actual[2] > rect[2] - 20 or actual[3] > rect[3] - 20):
            raise RuntimeError(name + ': glyphs overflow padded rectangle')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (40, 24, 720, 124), 'PASSAGE 1.28.10', 44, 38, True)
    measure('title', (790, 24, 2360, 124), 'THE AXE ON TRIAL', 64, 46, True)
    measure('orientation', (40, 140, 2360, 222),
            'ATHENS | DELPHINION AND PRYTANEION | TWO KINDS OF JUDGMENT', 32, 28, True)
    measure('first-heading', (64, 246, 2336, 318),
            '1  THE DELPHINION', 34, 30, True)
    measure('translation-1', TEXT_RECTS[0], parts[0], 52, 46)
    measure('interpretive-caption', (48, 1840, 2352, 1986), CAPTION, 32, 28)
    measure('second-heading', (64, 1992, 2336, 2064),
            '2  THE PRYTANEION', 34, 30, True)
    measure('translation-2', TEXT_RECTS[1], parts[1], 52, 46)
    validate_fit_records(records)
    wrapped = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Exact English lost words or source order')
    report = {
        'passage_id': '1.28.10', 'preflight': preflight, 'canvas': [2400, 2600],
        'art_rectangle': ART_RECT, 'translation_rectangles': TEXT_RECTS,
        'reading_order': 'numbered upper field 1, then lower field 2',
        'translation_exact': passage, 'translation_parts_exact': parts,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': 46,
        'body_font_sizes': [r.font_size for r in records if r.name.startswith('translation-')],
        'padding': 20, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('fit_records','translation_exact','translation_parts_exact')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'axe_study.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#788783', width=2)
    for y in (236, 1988):
        draw.line((64, y, 2336, y), fill='#a6b0a8', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#293a37')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/28/10.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
