#!/usr/bin/env python3
"""Set the exact exported expedition account beside a Thracian storm scene."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_5'
CANVAS = (3000, 2480)
ART_RECT = (48, 252, 1760, 2240)
BODY_RECT = (1820, 450, 2952, 2150)
PADDING = 26
MINIMUM_BODY = 50


def render(output: Path, preflight: bool = False) -> None:
    """Measure all text before opening art; reject loss, reordering or overflow."""
    snapshot_path()
    passage = load_translation('1.29.5')
    page = Image.new('RGB', CANVAS, '#f0ece1')
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

    measure('passage-id', (24, 16, 820, 136), 'PASSAGE 1.29.5', 58, 48, True)
    measure('title', (1000, 16, 2976, 136), 'THE THIRD EXPEDITION', 74, 58, True)
    measure('orientation', (24, 146, 2976, 234),
            'THRACE | ATHENIAN EXPEDITION | A REPORTED STORM', 42, 34, True)
    measure('reading-heading', (1820, 318, 2952, 420),
            "PAUSANIAS'S ACCOUNT", 44, 36, True)
    measure('translation', BODY_RECT, passage, 60, MINIMUM_BODY)
    measure('art-caption', (48, 2270, 2952, 2458),
            'A conjectural view of the Athenian expedition in Thrace. The thunderstorm is a '
            'reported tradition; no commander, exact route or battlefield is identified. '
            'Terrain, equipment and staging are imagined.', 39, 34)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == 'translation')
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Full English lost wording or original order')
    report = {
        'passage_id': '1.29.5', 'preflight': preflight, 'canvas': CANVAS,
        'art_rectangle': ART_RECT, 'translation_rectangle': BODY_RECT,
        'reading_order': 'single continuous right prose field, top to bottom',
        'translation_exact': passage,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
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
    with Image.open(ASSETS / 'thracian_storm.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#8e988d', width=3)
    draw.line((48, 240, 2952, 240), fill='#b5b2a2', width=2)
    draw.line((48, 2256, 2952, 2256), fill='#b5b2a2', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#303c3b')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/29/5.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
