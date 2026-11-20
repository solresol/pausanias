#!/usr/bin/env python3
"""A broad departure scene between two numbered full-width English fields."""
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

ASSETS = ROOT / 'graphic_book/assets/generated/1_29_8'
CANVAS = (2800, 3060)
ART_RECT = (56, 850, 2744, 2300)
PADDING = 26
MINIMUM_BODY = 50


def render(output: Path, preflight: bool = False) -> None:
    """Measure every glyph before compositing the commissioned raster."""
    snapshot_path()
    passage = load_translation('1.29.8')
    split = passage.index('On account of this revolt,')
    parts = (passage[:split].rstrip(), passage[split:])
    if ' '.join(parts) != passage:
        raise RuntimeError('Source substrings do not reassemble byte-identically')
    page = Image.new('RGB', CANVAS, '#f2eee4')
    draw = ImageDraw.Draw(page)
    records: list[FitRecord] = []
    placements = []

    def measure(name, rect, text, maximum, minimum, heading=False):
        font, wrapped, _, fit = fit_text_block(
            draw, rect, text, TITLE_FONT if heading else BODY_FONT,
            maximum, minimum, PADDING, name, .25,
        )
        spacing = max(2, round(fit.font_size * .25))
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing)
        xy = (rect[0] + PADDING - box[0], rect[1] + PADDING - box[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=spacing)
        if (actual[0] < rect[0]+PADDING or actual[1] < rect[1]+PADDING
                or actual[2] > rect[2]-PADDING or actual[3] > rect[3]-PADDING):
            raise RuntimeError(name + ': actual glyph bounds overflow padded rectangle')
        records.append(FitRecord(name, rect, fit.font_path, fit.font_size, actual, wrapped))
        placements.append((xy, wrapped, font, spacing))

    measure('passage-id', (32,20,850,132), 'PASSAGE 1.29.8', 58,48,True)
    measure('title', (900,20,2768,132), 'THE AID SPARTA REFUSED', 70,54,True)
    measure('orientation', (32,146,2768,246),
            "SPARTA | CIMON'S ATHENIAN CONTINGENT", 46,36,True)
    measure('reading-heading-1', (56,272,2744,370),
            '1 | ALLIANCE, EARTHQUAKE AND REVOLT', 46,38,True)
    measure('translation-1', (56,386,2744,810), parts[0], 62,MINIMUM_BODY)
    measure('reading-heading-2', (56,2330,2744,2428),
            '2 | ASSISTANCE DISMISSED', 46,38,True)
    measure('translation-2', (56,2440,2744,2820), parts[1],62,MINIMUM_BODY)
    measure('art-caption', (56,2840,2744,3040),
            'An imagined departure of the Athenian force from Sparta. The setting, equipment '
            'and figures are conjectural; no named individual, precise route or surviving site '
            'is identified. Ithome is a separate place of refuge, not the mountain shown.', 41,36)
    validate_fit_records(records)
    wrapped = ' '.join(r.text for r in records if r.name.startswith('translation-'))
    if ' '.join(wrapped.split()) != ' '.join(passage.split()):
        raise RuntimeError('The English passage lost words, punctuation or original order')
    report = {
        'passage_id':'1.29.8','preflight':preflight,'canvas':CANVAS,
        'art_rectangle':ART_RECT,'reading_order':'upper numbered English 1, then lower English 2',
        'translation_exact':passage,'translation_parts':parts,
        'translation_characters':len(passage),'translation_words':len(passage.split()),
        'translation_utf8_sha256':hashlib.sha256(passage.encode()).hexdigest(),
        'translation_matches_export':True,'substring_reassembly_byte_exact':True,
        'minimum_body_font_size':MINIMUM_BODY,'padding':PADDING,
        'body_font_sizes':[r.font_size for r in records if r.name.startswith('translation-')],
        'text_blocks_checked':len(records),'fit_records':[asdict(r) for r in records],
    }
    ASSETS.mkdir(parents=True,exist_ok=True)
    (ASSETS/'layout_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('fit_records','translation_exact','translation_parts')}))
    if preflight:
        return
    if output.exists():
        raise RuntimeError('Refusing to overwrite '+str(output))
    with Image.open(ASSETS/'athenian_departure.png') as source:
        art=ImageOps.fit(source.convert('RGB'),
                        (ART_RECT[2]-ART_RECT[0],ART_RECT[3]-ART_RECT[1]),
                        method=Image.Resampling.LANCZOS)
    page.paste(art,ART_RECT[:2])
    draw.rectangle(ART_RECT,outline='#8b8775',width=3)
    draw.line((56,260,2744,260),fill='#b8b09b',width=2)
    draw.line((56,2830,2744,2830),fill='#b8b09b',width=2)
    for xy,text,font,spacing in placements:
        draw.multiline_text(xy,text,font=font,spacing=spacing,fill='#343c32')
    output.parent.mkdir(parents=True,exist_ok=True)
    page.save(output)
    print('Saved',output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'graphic_book/images/1/29/8.png')
    args=parser.parse_args()
    render(args.output,args.preflight)
