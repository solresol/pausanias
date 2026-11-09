#!/usr/bin/env python3
"""A street-level pursuit between two ordered English fields, outside canon."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_13_7/revisions/20261109'
ART_RECT = (48, 680, 2352, 1730)
BODY_RECTS = ((64, 324, 2336, 650), (64, 2034, 2336, 2356))
ORIGINAL_SHA256 = '56be8926568f5b096650845ff16b7b8c161139d1c864272706652562e995e82e'
CAPTION = (
    'Pursuit into Argos: the victorious formation loses order inside the city. '
    'Figures, dress, gate and street are conjectural; no precise entrance, '
    'individual portrait or episode of the later fighting is identified.'
)


def render(output: Path | None, preflight: bool = False) -> None:
    """Fit the complete export and require an explicitly noncanonical candidate."""
    snapshot_path()
    passage = load_translation('1.13.7')
    split = passage.index('As Antigonus was preparing')
    parts = [passage[:split], passage[split:]]
    if ''.join(parts) != passage:
        raise RuntimeError('Source changed at split')
    page = Image.new('RGB', (2400, 2400), '#eeede7')
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
            raise RuntimeError(name + ': actual glyph overflow')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (40, 24, 720, 124), 'PASSAGE 1.13.7', 44, 38, True)
    measure('title', (790, 24, 2360, 124), 'VICTORY BECOMES DISORDER', 58, 44, True)
    measure('orientation', (40, 140, 2360, 222),
            'ARGOS | PELOPONNESE | PYRRHUS AND ANTIGONUS', 34, 28, True)
    measure('heading-1', (64, 246, 2336, 318),
            '1  ANTIGONUS MOVES SOUTH', 34, 30, True)
    measure('interpretive-caption', (48, 1750, 2352, 1900), CAPTION, 32, 28)
    measure('heading-2', (64, 1936, 2336, 2010),
            '2  PURSUIT INTO ARGOS', 34, 30, True)
    common_size = min(fit_text_block(draw, rect, text, BODY_FONT, 54, 46, 20,
                                   'body-preflight', .26)[3].font_size
                      for rect, text in zip(BODY_RECTS, parts))
    for n, (rect, text) in enumerate(zip(BODY_RECTS, parts), 1):
        measure('translation-' + str(n), rect, text, common_size, common_size)
    validate_fit_records(records)
    wrapped = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('English wording/order changed')
    report = {
        'passage_id': '1.13.7', 'kind': 'replacement', 'preflight': preflight,
        'canvas': [2400, 2400], 'art_rectangle': ART_RECT,
        'translation_rectangles': BODY_RECTS, 'reading_order': 'upper 1 then lower 2',
        'translation_exact': passage, 'translation_parts_exact': parts,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'original_catalogue_sha256': ORIGINAL_SHA256,
        'minimum_body_font_size': 46, 'body_font_size': common_size,
        'padding': 20, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('fit_records','translation_exact','translation_parts_exact')}))
    if preflight:
        return
    if output is None or output.resolve().is_relative_to((ROOT / 'graphic_book/images').resolve()):
        raise RuntimeError('Explicit output outside canonical page tree required')
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'argos_pursuit.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#82908d', width=2)
    for y in (236, 1920):
        draw.line((64, y, 2336, y), fill='#a7afa9', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#293b3e')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    render(args.output, args.preflight)
