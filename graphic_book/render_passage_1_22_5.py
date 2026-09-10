#!/usr/bin/env python3
"""Render 1.22.5 in two alternating narrative rows with measured exact text."""
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
ASSETS = ROOT / 'graphic_book/assets/generated/1_22_5'

def render(output: Path, preflight=False):
    with sqlite3.connect(ROOT / 'pausanias.sqlite') as conn:
        passage = conn.execute('SELECT english_translation FROM translations WHERE passage_id=?', ('1.22.5',)).fetchone()[0]
    split = passage.index('However,')
    parts = [passage[:split].rstrip(), passage[split:]]
    assert ' '.join(parts) == passage
    page = Image.new('RGB', (1600,1280), '#f5f0e5')
    draw = ImageDraw.Draw(page)
    records = []
    if not preflight:
        for filename, rect in [('returning-ship.png',(24,104,956,662)),('aegeus.png',(732,718,1576,1218))]:
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
    text('passage-id',(24,15,400,78),'PASSAGE 1.22.5',29,29,True)
    text('title',(490,15,1576,78),'THE SAILS THAT WERE NOT CHANGED',34,30,True)
    text('first-heading',(990,110,1576,178),'1 · THE PROMISED SIGNAL',26,24,True)
    text('translation-1',(990,192,1576,642),parts[0],28,25)
    text('ship-caption',(24,665,956,712),'Returning from Crete: the black sail remains aloft.',22,20)
    text('second-heading',(24,740,698,806),'2 · AEGEUS WATCHES',26,24,True)
    text('translation-2',(24,820,698,1164),parts[1],28,25)
    text('orientation',(24,1168,698,1228),'ATHENS · THE RETURN FROM CRETE',22,20,True)
    text('boundary',(24,1230,1576,1278),'Mythic narrative illustrated; ship, dress and viewpoint are interpretive. Aegeus is shown before his fatal act.',19,18)
    draw.line((24,720,698,720),fill='#627d7a',width=2)
    validate_fit_records(records)
    reconstructed=' '.join(' '.join(r.text.split()) for r in records if r.name.startswith('translation-'))
    assert reconstructed == ' '.join(passage.split())
    report={'passage_id':'1.22.5','preflight':preflight,'translation_matches_sqlite':True,'text_blocks_checked':len(records),'fit_records':[asdict(r) for r in records]}
    (ROOT/'tmp').mkdir(exist_ok=True)
    (ROOT/'tmp/passage_1_22_5_layout_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='fit_records'}))
    print('Font sizes:',[(r.name,r.font_size) for r in records])
    if not preflight:
        if output.exists(): raise RuntimeError('Refusing to overwrite accepted page')
        output.parent.mkdir(parents=True,exist_ok=True)
        page.save(output)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'graphic_book/images/1/22/5.png')
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    render(args.output,args.preflight)
