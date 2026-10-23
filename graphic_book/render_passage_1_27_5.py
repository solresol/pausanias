#!/usr/bin/env python3
"""Render Tolmides's coastal campaign with the complete exported translation."""
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
ASSETS = ROOT / 'graphic_book/assets/generated/1_27_5'
RECTS = ((30,188,650,700),(690,188,1310,700),(1350,188,1970,700))
def render(output: Path, preflight: bool=False) -> None:
    snapshot_path()
    passage = load_translation('1.27.5')
    a=passage.index('After making a landing')
    b=passage.index('Then he invaded Boeotia')
    chunks=[passage[:a].rstrip(),passage[a:b].rstrip(),passage[b:]]
    if ' '.join(chunks)!=passage: raise RuntimeError('Exact translation split failed')
    page=Image.new('RGB',(2000,1800),'#eeeae1'); draw=ImageDraw.Draw(page); records=[]
    for size in range(42,32,-1):
        try:
            for rect,text in zip(RECTS,chunks): fit_text_block(draw,rect,text,BODY_FONT,size,size,14,'preflight',.16)
        except RuntimeError: continue
        break
    else: raise RuntimeError('Complete translation cannot fit at minimum 33px')
    def block(name,rect,text,maximum,minimum,heading=False):
        font,wrapped,_,fit=fit_text_block(draw,rect,text,TITLE_FONT if heading else BODY_FONT,maximum,minimum,14,name,.16)
        spacing=max(2,round(fit.font_size*.16)); bounds=draw.multiline_textbbox((0,0),wrapped,font=font,spacing=spacing)
        xy=(rect[0]+14-bounds[0],rect[1]+14-bounds[1]); actual=draw.multiline_textbbox(xy,wrapped,font=font,spacing=spacing)
        if actual[0]<rect[0]+14 or actual[1]<rect[1]+14 or actual[2]>rect[2]-14 or actual[3]>rect[3]-14: raise RuntimeError(name+' glyph overflow')
        draw.multiline_text(xy,wrapped,font=font,spacing=spacing,fill='#28363b'); records.append(FitRecord(name,rect,fit.font_path,fit.font_size,actual,wrapped))
    block('passage-id',(30,15,430,83),'PASSAGE 1.27.5',34,30,True)
    block('title',(465,15,1970,83),'TOLMIDES: COASTAL VICTORIES, INLAND DEFEAT',39,32,True)
    block('orientation',(30,91,1970,145),'ATHENS, ACROPOLIS: STATUES AND MEMORY  |  BELOW: GYTHIUM, LACONIAN COAST',27,24,True)
    for i,(rect,text,label) in enumerate(zip(RECTS,chunks,['1  STATUES AND THE FLEET','2  SICYON AND THE COLONISTS','3  THE BOEOTIAN DEFEAT']),1):
        block('section-'+str(i),(rect[0],146,rect[2],192),label,25,22,True)
        block('translation-'+str(i),rect,text,size,size)
    block('caption',(30,1708,1970,1780),'Gythium’s dockyards burn during Tolmides’s naval campaign. Interpretive reconstruction; the later defeat at Haliartus is recounted above.',28,25)
    validate_fit_records(records)
    if ' '.join(' '.join(r.text.split()) for r in records if r.name.startswith('translation-'))!=' '.join(passage.split()): raise RuntimeError('Rendered translation mismatch')
    report={'passage_id':'1.27.5','preflight':preflight,'translation_characters':len(passage),'translation_utf8_sha256':hashlib.sha256(passage.encode()).hexdigest(),'translation_matches_export':True,'body_font_size':size,'minimum_body_font_size':33,'padding':14,'canvas':[2000,1800],'reading_order':'three upper columns, left to right','text_blocks_checked':len(records),'fit_records':[asdict(r) for r in records]}
    ASSETS.mkdir(parents=True,exist_ok=True); (ASSETS/'layout_report.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps({k:v for k,v in report.items() if k!='fit_records'}))
    if preflight:return
    if output.exists(): raise RuntimeError('Refusing to overwrite '+str(output))
    with Image.open(ASSETS/'gythium.png') as source: art=ImageOps.fit(source.convert('RGB'),(1940,960),method=Image.Resampling.LANCZOS)
    page.paste(art,(30,734)); draw.rectangle((29,733,1970,1694),outline='#6c7778',width=2)
    draw.line((30,139,1970,139),fill='#9aa3a1',width=2)
    output.parent.mkdir(parents=True,exist_ok=True); page.save(output); print('Saved',output)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--preflight',action='store_true'); p.add_argument('--output',type=Path,default=ROOT/'graphic_book/images/1/27/5.png'); args=p.parse_args(); render(args.output,args.preflight)
