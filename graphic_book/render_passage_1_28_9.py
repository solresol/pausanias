#!/usr/bin/env python3
"""Render the mistaken Phalerum landfall above the full exported English."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_28_9'
ART_RECT = (48, 244, 2352, 1468)
BODY_RECT = (64, 1760, 2336, 2440)
CAPTION = (
    'Phalerum, on the coast of Attica: the Argives make an unrecognized landfall '
    'in Pausanias\'s reported story. Shoreline, ships, dress and figures are '
    'conjectural. The later attack and accidental death are not depicted.'
)


def render(output: Path, preflight: bool = False) -> None:
    """Fit exact text before art and refuse any padded glyph overflow."""
    snapshot_path()
    passage = load_translation('1.28.9')
    page = Image.new('RGB', (2400, 2480), '#eeeee8')
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
            raise RuntimeError(name + ': glyphs overflow padded target')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (40, 24, 690, 124), 'PASSAGE 1.28.9', 44, 38, True)
    measure('title', (716, 24, 2360, 124), 'LANDFALL IN THE DARK', 64, 46, True)
    measure('orientation', (40, 140, 2360, 218),
            'PHALERUM | ATTIC COAST | A DISPUTED HOMECOMING', 34, 28, True)
    measure('interpretive-caption', (48, 1488, 2352, 1652), CAPTION, 34, 30)
    measure('reading-heading', (64, 1668, 2336, 1748),
            "PAUSANIAS'S ACCOUNT", 36, 30, True)
    measure('translation', BODY_RECT, passage, 54, 46)
    validate_fit_records(records)
    wrapped = next(r.text for r in records if r.name == 'translation')
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('Full exported English must remain in original order')
    report = {
        'passage_id': '1.28.9', 'preflight': preflight, 'canvas': [2400, 2480],
        'art_rectangle': ART_RECT, 'translation_rectangle': BODY_RECT,
        'reading_order': 'one continuous lower English field, top to bottom',
        'translation_exact': passage,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'minimum_body_font_size': 46,
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
    with Image.open(ASSETS / 'phalerum.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#77838a', width=2)
    draw.line((40, 238, 2360, 238), fill='#a6b0b1', width=2)
    draw.line((64, 1658, 2336, 1658), fill='#a6b0b1', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#27363d')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'graphic_book/images/1/28/9.png')
    args = parser.parse_args()
    render(args.output, args.preflight)
