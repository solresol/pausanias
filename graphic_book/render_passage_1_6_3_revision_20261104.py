#!/usr/bin/env python3
"""Render a guarded funeral above two exact ordered English fields, outside canon."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_6_3/revisions/20261104'
ART_RECT = (48, 240, 2352, 1340)
BODY_RECTS = ((48, 1590, 1174, 2260), (1226, 1590, 2352, 2260))
ORIGINAL_SHA256 = '2ac6547a48d0256d33cbab1858fcad2eecfdd0722339989905375a4ba855b5af'
CAPTION = (
    'Guarded custody near Memphis: an interpretive funeral scene. Figures, wagon '
    'and landscape are conjectural; no exact route is reconstructed.'
)


def render(output: Path | None, preflight: bool = False) -> None:
    """Require exact source reassembly, common readable type and padded bounds."""
    snapshot_path()
    passage = load_translation('1.6.3')
    marker = ' Perdiccas, for outward appearance,'
    first, second = passage.split(marker, 1)
    chunks = (first, marker[1:] + second)
    if ' '.join(chunks) != passage:
        raise RuntimeError('English chunks do not rejoin byte-for-byte')
    page = Image.new('RGB', (2400, 2300), '#ecebe3')
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
            raise RuntimeError(name + ': actual glyphs escape padded target')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (42, 24, 680, 120), 'PASSAGE 1.6.3', 44, 38, True)
    measure('title', (740, 24, 2358, 120), 'A ROYAL BURIAL, A CONTESTED KINGDOM', 58, 38, True)
    measure('orientation', (42, 134, 2358, 214),
            "MEMPHIS, EGYPT | ALEXANDER'S BODY IN PTOLEMY'S CUSTODY", 36, 30, True)
    measure('interpretive-caption', (48, 1358, 2352, 1466), CAPTION, 34, 28)
    measure('reading-heading-1', (48, 1490, 1174, 1580),
            '1  PTOLEMY TAKES CONTROL', 36, 30, True)
    measure('reading-heading-2', (1226, 1490, 2352, 1580),
            "2  PERDICCAS'S CAMPAIGN", 36, 30, True)
    common_size = min(fit_text_block(draw, rect, text, BODY_FONT, 50, 42, 20,
                                   'body-preflight', .25)[3].font_size
                      for rect, text in zip(BODY_RECTS, chunks))
    for index, (rect, text) in enumerate(zip(BODY_RECTS, chunks), 1):
        measure('translation-' + str(index), rect, text, common_size, common_size)
    validate_fit_records(records)
    rendered = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(rendered.split()) != ' '.join(passage.split()):
        raise RuntimeError('Rendered English is missing or out of order')
    report = {
        'passage_id': '1.6.3', 'kind': 'replacement', 'preflight': preflight,
        'canvas': [2400, 2300], 'art_rectangle': ART_RECT,
        'translation_rectangles': BODY_RECTS, 'reading_order': 'numbered left then right',
        'translation_exact': passage, 'source_chunks': chunks,
        'translation_characters': len(passage), 'translation_words': len(passage.split()),
        'translation_utf8_sha256': hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export': True, 'source_chunks_reassemble_exactly': True,
        'original_catalogue_sha256': ORIGINAL_SHA256, 'minimum_body_font_size': 42,
        'body_font_size': common_size, 'padding': 20, 'text_blocks_checked': len(records),
        'fit_records': [asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'layout_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('fit_records', 'translation_exact', 'source_chunks')}))
    if preflight:
        return
    if output is None:
        raise RuntimeError('An explicit noncanonical output path is required')
    if output.resolve().is_relative_to((ROOT / 'graphic_book/images').resolve()):
        raise RuntimeError('Replacement must remain outside the canonical tree')
    if output.exists():
        raise RuntimeError('Refusing to overwrite ' + str(output))
    with Image.open(ASSETS / 'guarded_funeral.png') as source:
        art = ImageOps.fit(source.convert('RGB'),
                           (ART_RECT[2]-ART_RECT[0], ART_RECT[3]-ART_RECT[1]),
                           method=Image.Resampling.LANCZOS)
    page.paste(art, ART_RECT[:2])
    draw.rectangle(ART_RECT, outline='#8b9898', width=2)
    draw.line((42, 232, 2358, 232), fill='#a2abaa', width=2)
    draw.line((1200, 1490, 1200, 2260), fill='#c2c4bb', width=2)
    for xy, text, font, spacing in placements:
        draw.multiline_text(xy, text, font=font, spacing=spacing, fill='#2d383c')
    output.parent.mkdir(parents=True, exist_ok=True)
    page.save(output)
    print('Saved', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    render(args.output, args.preflight)
