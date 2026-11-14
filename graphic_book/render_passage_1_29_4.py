#!/usr/bin/env python3
"""Place the exported war-dead account around a wide Academy-road panorama."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_4'
CANVAS = (2600, 2780)
ART_RECT = (56, 730, 2544, 1960)
BODY_RECTS = ((64, 328, 2536, 690), (64, 2210, 2536, 2650))
PADDING = 24
MINIMUM_BODY = 48


def render(output: Path, preflight: bool = False) -> None:
    """Fit every glyph before reading raster art, rejecting overflow or lost text."""
    snapshot_path()
    passage = load_translation('1.29.4')
    first, boundary, rest = passage.partition(' The others lie')
    if not boundary:
        raise RuntimeError('Expected exported sentence boundary missing')
    chunks = (first, boundary[1:] + rest)
    if ' '.join(chunks) != passage:
        raise RuntimeError('Source substrings do not reassemble byte-exactly')
    page = Image.new('RGB', CANVAS, '#f2ecdf')
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
            raise RuntimeError(name + ': glyph overflow in padded rectangle')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (32, 20, 780, 130), 'PASSAGE 1.29.4', 54, 44, True)
    measure('title', (814, 20, 2568, 130), 'THE ATHENIAN WAR DEAD', 68, 52, True)
    measure('orientation', (32, 146, 2568, 234),
            'ATHENS | ROAD TO THE ACADEMY | COLLECTIVE REMEMBRANCE', 39, 32, True)
    measure('reading-heading-1', (64, 246, 2536, 322),
            '1  THE MONUMENT AND THE MARATHON EXCEPTION', 39, 34, True)
    measure('reading-heading-2', (64, 2120, 2536, 2200),
            '2  THE ROAD, THE PILLARS AND THE FIRST BURIALS', 39, 34, True)
    size = 58
    while size >= MINIMUM_BODY:
        try:
            for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
                fit_text_block(draw, rect, text, BODY_FONT, size, size, PADDING,
                               f'translation-{i+1}', .25)
            break
        except RuntimeError:
            size -= 1
    if size < MINIMUM_BODY:
        raise RuntimeError('Complete English cannot fit at readable minimum')
    for i, (rect, text) in enumerate(zip(BODY_RECTS, chunks, strict=True)):
        measure(f'translation-{i+1}', rect, text, size, size)
    measure('art-caption', (56, 1980, 2544, 2114),
            'The Academy road imagined from above: groups of grave markers beside the approach. '
            'The Marathon graves and the fighting in Thrace are not depicted.', 37, 33)
    measure('interpretive-note', (56, 2664, 2544, 2760),
            'Road, plots, pillars, visitors and landscape are conjectural; no exact grave plan, '
            'inscription or surviving monument is reconstructed.', 32, 29)
    validate_fit_records(records)
    wrapped = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Full English lost wording or original order')
    report = {
        'passage_id': '1.29.4', 'preflight': preflight, 'canvas': CANVAS,
        'art_rectangle': ART_RECT, 'translation_rectangles': BODY_RECTS,
        'reading_order': '1: upper full-width prose, then 2: lower full-width prose',
        'translation_exact': passage, 'translation_chunks': chunks,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': MINIMUM_BODY,
        'body_font_size': size, 'padding': PADDING,
        'text_blocks_checked': len(records), 'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('fit_records', 'translation_exact', 'translation_chunks')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'academy_road.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#9e967e', width=3)
    draw.line((56, 238, 2544, 238), fill='#b9ad95', width=2)
    draw.line((56, 2658, 2544, 2658), fill='#b9ad95', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#373c35')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/29/4.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
