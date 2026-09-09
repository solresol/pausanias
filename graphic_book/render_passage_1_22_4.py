#!/usr/bin/env python3
"""Render 1.22.4: a broad architectural approach above two text columns."""
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
ASSETS = ROOT / 'graphic_book/assets/generated/1_22_4'

def render(output: Path, preflight=False):
    with sqlite3.connect(ROOT / 'pausanias.sqlite') as conn:
        passage = conn.execute('SELECT english_translation FROM translations WHERE passage_id=?', ('1.22.4',)).fetchone()[0]
    split = passage.index('As for the statues')
    parts = [passage[:split].rstrip(), passage[split:]]
    assert ' '.join(parts) == passage
    page = Image.new('RGB', (1600,1280), '#f5f0e5')
    draw = ImageDraw.Draw(page)
    records = []
    if not preflight:
        page.paste(ImageOps.fit(Image.open(ASSETS/'propylaia.png').convert('RGB'), (1552,820), method=Image.Resampling.LANCZOS), (24,90))
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
    text('passage-id',(24,15,390,78),'PASSAGE 1.22.4',29,29,True)
    text('title',(430,15,1576,78),'THE ENTRANCE TO THE ACROPOLIS',34,30,True)
    text('orientation',(820,108,1555,164),'ATHENS · WESTERN APPROACH · LOOKING EAST',21,20,True,box=True)
    text('propylaia-label',(490,836,850,895),'PROPYLAIA · ENTRANCE',21,20,True,box=True)
    text('nike-label',(1100,836,1550,895),'TEMPLE OF WINGLESS VICTORY',20,19,True,box=True)
    text('translation-1',(36,930,780,1204),parts[0],26,23)
    text('translation-2',(810,930,1564,1204),parts[1],26,23)
    draw.line((795,946,795,1185),fill='#b4bab7',width=1)
    text('boundary',(36,1211,1564,1267),'Illustrative reconstruction. Horsemen remain unidentified; Aegeus’ death is reported as a tradition, not pictured.',20,18)
    validate_fit_records(records)
    reconstructed=' '.join(' '.join(r.text.split()) for r in records if r.name.startswith('translation-'))
    assert reconstructed == ' '.join(passage.split())
    report={'passage_id':'1.22.4','preflight':preflight,'translation_matches_sqlite':True,'text_blocks_checked':len(records),'fit_records':[asdict(r) for r in records]}
    (ROOT/'tmp').mkdir(exist_ok=True)
    (ROOT/'tmp/passage_1_22_4_layout_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='fit_records'}))
    print('Font sizes:',[(r.name,r.font_size) for r in records])
    if not preflight:
        if output.exists(): raise RuntimeError('Refusing to overwrite accepted page')
        output.parent.mkdir(parents=True,exist_ok=True)
        page.save(output)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'graphic_book/images/1/22/4.png')
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    render(args.output,args.preflight)
