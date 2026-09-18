#!/usr/bin/env python3
"""Render 1.23.4 as a central sculptural portrait with flanking prose."""
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
ASSETS = ROOT / 'graphic_book/assets/generated/1_23_4'

def render(output: Path, preflight=False):
    with sqlite3.connect(ROOT / 'pausanias.sqlite') as conn:
        passage = conn.execute('SELECT english_translation FROM translations WHERE passage_id=?', ('1.23.4',)).fetchone()[0]
    page = Image.new('RGB', (1800,1600), '#f5f0e5')
    draw = ImageDraw.Draw(page)
    records = []
    if not preflight:
        for filename, rect in [('hygieiai.png',(510,130,1290,1500))]:
            x0,y0,x1,y1=rect
            page.paste(ImageOps.fit(Image.open(ASSETS/filename).convert('RGB'),(x1-x0,y1-y0),method=Image.Resampling.LANCZOS),(x0,y0))
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
    first, second = passage.split('Nor did archery', 1)
    second = 'Nor did archery' + second
    text('passage-id',(24,20,430,85),'PASSAGE 1.23.4',30,30,True)
    text('title',(510,20,1776,85),'ARROWS AND THE GODDESSES OF HEALTH',37,30,True)
    text('heading-1',(24,170,480,280),'1 · THE ARROWS',29,27,True)
    text('translation-1',(24,290,480,1300),first,32,29)
    text('heading-2',(1320,390,1776,495),'2 · THE NEIGHBOURING IMAGES',29,27,True)
    text('translation-2',(1320,510,1776,1480),second,32,29)
    text('orientation',(24,1380,480,1550),'ATHENS · ACROPOLIS\nNear the statue of Diitrephes',28,25,True)
    text('caption',(510,1510,1290,1585),'Hygieia and Athena Hygieia',28,26,True)
    validate_fit_records(records)
    reconstructed=' '.join(' '.join(r.text.split()) for r in records if r.name.startswith('translation-'))
    assert reconstructed == ' '.join(passage.split())
    report={'passage_id':'1.23.4','preflight':preflight,'translation_matches_sqlite':True,'text_blocks_checked':len(records),'fit_records':[asdict(r) for r in records]}
    (ROOT/'tmp').mkdir(exist_ok=True)
    (ROOT/'tmp/passage_1_23_4_layout_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='fit_records'}))
    print('Font sizes:',[(r.name,r.font_size) for r in records])
    if not preflight:
        if output.exists(): raise RuntimeError('Refusing to overwrite accepted page')
        output.parent.mkdir(parents=True,exist_ok=True)
        page.save(output)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'graphic_book/images/1/23/4.png')
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    render(args.output,args.preflight)
