#!/usr/bin/env python3
"""Render 1.21.7 from generated art and measured, exact local typography."""
from __future__ import annotations
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw, ImageFont, ImageOps
from graphic_book.render_passage_1_3_2 import (
    BODY_FONT, TITLE_FONT, FitRecord, make_parchment, framed_panel,
    paste_with_shadow, fit_text_block, add_border, draw_leader,
)
from graphic_book.render_passage_1_10_1 import validate_fit_records

ASSETS = ROOT / 'graphic_book/assets/generated/1_21_7'
PASSAGE_ID = '1.21.7'


def render():
    """Fail before saving if any measured text escapes its padded rectangle."""
    with sqlite3.connect(ROOT / 'pausanias.sqlite') as conn:
        translation = conn.execute('SELECT english_translation FROM translations WHERE passage_id=?', (PASSAGE_ID,)).fetchone()[0]
    records = []
    page = make_parchment((1402, 1122)).convert('RGBA')
    draw = ImageDraw.Draw(page)

    def text(rect, content, size=20, minimum=16, title=False, box=False, name='text'):
        if box:
            panel = framed_panel((rect[2]-rect[0], rect[3]-rect[1]))
            paste_with_shadow(page, panel, rect[:2])
        font, wrapped, _, record = fit_text_block(draw, rect, content, TITLE_FONT if title else BODY_FONT, size, minimum, 12, name, spacing_ratio=.14)
        # Correct for font ascenders: verify the actual draw coordinates and bbox.
        raw = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=max(2,round(record.font_size*.14)))
        xy = (rect[0]+12-raw[0], rect[1]+12-raw[1])
        actual = draw.multiline_textbbox(xy, wrapped, font=font, spacing=max(2,round(record.font_size*.14)))
        if actual[2] > rect[2]-12 or actual[3] > rect[3]-12:
            raise RuntimeError(f'{name}: actual text overflow')
        draw.multiline_text(xy, wrapped, font=font, spacing=max(2,round(record.font_size*.14)), fill='#2a1e13')
        records.append(FitRecord(name,rect,record.font_path,record.font_size,actual,wrapped))

    paste_with_shadow(page, framed_panel((378,650)), (28,24))
    text((44,40,390,100),'PASSAGE 1.21.7',26,22,True,True,'passage-id')
    text((44,112,390,442),translation,21,16,name='translation')
    text((44,462,390,560),'GRYNEIUM • AEOLIS\nCoastal western Asia Minor, across the Aegean from Greece.',18,16,box=True,name='orientation')
    text((44,572,390,658),'Reconstruction: architecture, grove planting and corselet construction are illustrative.',15,12,name='boundary')
    paste_with_shadow(page,framed_panel((960,650)),(414,24))
    main = ImageOps.fit(Image.open(ASSETS/'sanctuary.png').convert('RGB'),(932,622),method=Image.Resampling.LANCZOS)
    page.paste(main,(428,38))
    text((768,50,1176,106),'LINEN OFFERED TO APOLLO',22,18,True,True,'main-title')
    for label,rect,point,start in [
        ('LINEN CORSELET',(444,566,688,624),(578,357),(565,566)),
        ("APOLLO’S SANCTUARY",(1060,572,1346,630),(1202,350),(1202,572)),
        ('THE SACRED GROVE',(886,144,1170,194),(1067,261),(1028,194)),
    ]:
        draw_leader(draw,point,start)
        text(rect,label,18,16,True,True,label)
    studies=Image.open(ASSETS/'material_studies.png').convert('RGB')
    for i,(heading,caption,note) in enumerate([
        ('IRON CAN PIERCE', 'Pausanias says iron weapons can penetrate linen corselets when driven with force.', 'Material study: a spear point through woven linen.'),
        ('TEETH ENTANGLED', 'For hunting, he says linen catches even the teeth of lions and leopards.', 'Illustration of his account: a lion grips loose linen.'),
    ]):
        x=28+i*690
        paste_with_shadow(page,framed_panel((656,392)),(x,702))
        half=studies.crop((i*studies.width//2,0,(i+1)*studies.width//2,studies.height))
        art=ImageOps.fit(half,(336,350),method=Image.Resampling.LANCZOS)
        page.paste(art,(x+16,718))
        text((x+364,720,x+642,782),heading,20,17,True,name=f'inset-{i}-title')
        text((x+364,798,x+642,954),caption,21,17,name=f'inset-{i}-caption')
        text((x+364,974,x+642,1076),note,16,14,name=f'inset-{i}-note')
    add_border(draw)
    validate_fit_records(records)
    output=ROOT/'graphic_book/images/1/21/7.png'
    if output.exists():
        raise RuntimeError('Refusing to overwrite an accepted page')
    output.parent.mkdir(parents=True,exist_ok=True)
    report={'passage_id':PASSAGE_ID,'text_blocks_checked':len(records),'translation_matches_sqlite':' '.join(next(r.text for r in records if r.name=='translation').split())==' '.join(translation.split()),'fit_records':[asdict(r) for r in records]}
    (ROOT/'tmp').mkdir(exist_ok=True)
    (ROOT/'tmp/passage_1_21_7_layout_report.json').write_text(json.dumps(report,indent=2))
    page.convert('RGB').save(output)
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    render()
