#!/usr/bin/env python3
"""Render the Areopagus stones beside one measured continuous reading field."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_28_5'
ART_RECT = (966, 254, 2358, 2122)
BODY_RECT = (64, 390, 896, 2000)
CAPTION = (
    "The litigants' rough stones on the Areopagus: an interpretive view. "
    "Forms, spacing and ancient setting are conjectural; no surviving stones are identified."
)


def render(output: Path, preflight: bool = False) -> None:
    """Validate exact source order and padded actual glyph bounds before save."""
    snapshot_path()
    passage = load_translation('1.28.5')
    page = Image.new('RGB', (2400, 2300), '#eeeae0')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, 20, name, .25,
        )
        spacing = max(2, round(fit.font_size * .25))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + 20 - bbox[0], rect[1] + 20 - bbox[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0] + 20 or actual[1] < rect[1] + 20
                or actual[2] > rect[2] - 20 or actual[3] > rect[3] - 20):
            raise RuntimeError(name + ': actual glyphs overflow padded target')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing, heading))

    measure('passage-id', (42, 24, 680, 120), 'PASSAGE 1.28.5', 44, 38, True)
    measure('title', (740, 24, 2358, 120), 'THE STONES OF THE AREOPAGUS', 64, 44, True)
    measure('orientation', (42, 134, 2358, 214),
            'ATHENS  |  AREOPAGUS, SOUTH OF THE AGORA', 36, 30, True)
    measure('reading-heading', (64, 278, 896, 360), "PAUSANIAS'S ACCOUNT", 37, 30, True)
    measure('translation', BODY_RECT, passage, 54, 44)
    measure('interpretive-caption', (42, 2160, 2358, 2280), CAPTION, 34, 28)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == 'translation')
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Complete exported English must remain in source order')
    report = {
        'passage_id': '1.28.5', 'preflight': preflight, 'canvas': [2400, 2300],
        'art_rectangle': ART_RECT, 'translation_rectangle': BODY_RECT,
        'reading_order': 'one continuous left English field, top to bottom',
        'translation_exact': passage,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': 44,
        'body_font_size': next(r.font_size for r in records if r.name == 'translation'),
        'padding': 20, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('fit_records','translation_exact')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'areopagus_stones.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#94887e', width=2)
    draw.line((42, 232, 2358, 232), fill='#b7a69c', width=2)
    draw.line((936, 254, 936, 2122), fill='#c8bdb2', width=2)
    for xy, text, font, spacing, heading in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing,
                            fill='#39363b' if heading else '#383438')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/28/5.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
