#!/usr/bin/env python3
"""Render 1.3.4 in a monumental painted wall over three prose columns with measured exact text."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw, ImageOps
from graphic_book.render_passage_1_3_2 import BODY_FONT, TITLE_FONT, FitRecord, fit_text_block
from graphic_book.render_passage_1_10_1 import validate_fit_records
ASSETS = ROOT / 'graphic_book/assets/generated/1_3_4'

def render(output: Path, preflight=False):
    with sqlite3.connect(ROOT / 'pausanias.sqlite') as conn:
        passage = conn.execute('SELECT english_translation FROM translations WHERE passage_id=?', ('1.3.4',)).fetchone()[0]
    words = passage.split(' ')
    # Preserve exact lexical order while balancing three measured columns.
    cut1,cut2=len(words)//3,2*len(words)//3
    parts=[' '.join(words[:cut1]),' '.join(words[cut1:cut2]),' '.join(words[cut2:])]
    assert ' '.join(parts) == passage
    page = Image.new('RGB', (1800,1440), '#f5f0e5')
    draw = ImageDraw.Draw(page)
    records=[]
    if not preflight:
        page.paste(ImageOps.fit(Image.open(ASSETS/'revision-20260911-mantineia.png').convert('RGB'),(1752,820),method=Image.Resampling.LANCZOS),(24,100))
    def text(name, rect, content, size, minimum, title=False, fill='#23333b', box=False):
        if box:
            draw.rectangle(rect, fill='#f5f0e5')
        font, wrapped, _, record = fit_text_block(draw,rect,content,TITLE_FONT if title else BODY_FONT,size,minimum,12,name,spacing_ratio=.18)
        spacing=max(2,round(record.font_size*.18))
        raw=draw.multiline_textbbox((0,0),wrapped,font=font,spacing=spacing)
        xy=(rect[0]+12-raw[0],rect[1]+12-raw[1])
        actual=draw.multiline_textbbox(xy,wrapped,font=font,spacing=spacing)
        if actual[0]<rect[0]+12 or actual[1]<rect[1]+12 or actual[2]>rect[2]-12 or actual[3]>rect[3]-12:
            raise RuntimeError(f'{name}: overflow')
        draw.multiline_text(xy,wrapped,font=font,spacing=spacing,fill=fill)
        records.append(FitRecord(name,rect,record.font_path,record.font_size,actual,wrapped))
    text('passage-id',(24,18,430,82),'PASSAGE 1.3.4',30,28,True)
    text('title',(490,18,1776,82),'MANTINEIA REMEMBERED IN ATHENS',36,32,True)
    text('orientation',(24,932,1776,992),'ATHENIAN AGORA · EUPHRANOR’S PAINTING OF THE CAVALRY ENGAGEMENT NEAR MANTINEIA',23,22,True)
    for i,rect in enumerate([(30,1008,587,1356),(622,1008,1179,1356),(1214,1008,1771,1356)]):
        text(f'translation-{i+1}',rect,parts[i],26,24)
    for x in [604,1196]:draw.line((x,1020,x,1340),fill='#a5aba8',width=1)
    text('boundary',(24,1370,1776,1425),'Interpretive reconstruction of a lost painting; figures and pictorial arrangement are not claimed as Euphranor’s original.',21,19)
    validate_fit_records(records)
    reconstructed=' '.join(' '.join(r.text.split()) for r in records if r.name.startswith('translation-'))
    assert reconstructed == ' '.join(passage.split())
    report={'passage_id':'1.3.4','preflight':preflight,'translation_matches_sqlite':True,'text_blocks_checked':len(records),'fit_records':[asdict(r) for r in records]}
    (ROOT/'tmp').mkdir(exist_ok=True)
    (ROOT/'tmp/passage_1_3_4_revision_layout_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='fit_records'}))
    print('Font sizes:',[(r.name,r.font_size) for r in records])
    if not preflight:
        if output.exists(): raise RuntimeError('Refusing to overwrite any existing page; promotion is separate')
        output.parent.mkdir(parents=True,exist_ok=True)
        page.save(output)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    render(args.output,args.preflight)
