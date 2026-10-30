"""Render the submitted video's timeline with BIZ UDPGothic only.
Run: python -m pip install Pillow; python render.py
All horizontal positions on BOTH ribbons use the same linear 0–177 s scale.
"""
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import json
ROOT=Path(__file__).resolve().parent
SCALE=2
W,H=3600,1800
im=Image.new('RGB',(W*SCALE,H*SCALE),'white')
d=ImageDraw.Draw(im)
INK='#24344b'; MUTED='#60728a'; GOLD='#ae8442'; GREEN='#2f7f69'
BZ='#d9b471'; BIRD='#88bed2'; CRAB='#b6a0ce'; AI='#85c2ad'; ALL='#dea8b7'; GRAY='#d6dbe2'
LEFT,RIGHT=80,3520
BAND_HEIGHT=56
MIN_FONT=28
assert MIN_FONT>=BAND_HEIGHT/2
RUNS=[]
@lru_cache(None)
def font(size,bold=False):
 return ImageFont.truetype(str(ROOT.parent/'fonts'/('BIZUDPGothic-Bold.ttf' if bold else 'BIZUDPGothic-Regular.ttf')),size*SCALE)
def text(x,y,s,size=32,color=INK,bold=False,center=False):
 ft=font(size,bold)
 px=x*SCALE-ft.getlength(s)/2 if center else x*SCALE
 py=y*SCALE
 d.text((px,py),s,font=ft,fill=color,anchor='lt')
 bb=d.textbbox((px,py),s,font=ft,anchor='lt')
 assert bb[0]>=0 and bb[1]>=0 and bb[2]<=W*SCALE and bb[3]<=H*SCALE,(s,bb)
 assert size>=MIN_FONT
 RUNS.append({'text':s,'size':size,'bold':bold,'bbox':list(bb)})
def line(points,color=INK,width=2):d.line([(round(x*SCALE),round(y*SCALE)) for x,y in points],fill=color,width=width*SCALE)
def rect(x,y,w,h,color):d.rectangle((round(x*SCALE),round(y*SCALE),round((x+w)*SCALE),round((y+h)*SCALE)),fill=color)
def X(seconds):return LEFT+(RIGHT-LEFT)*seconds/177

def tm(s):return f'{s//60}:{s%60:02d}'
text(80,65,'提出動画の構成（2:57、×4／×2／×1、省略なし）',60,bold=True)
text(3100,80,'★ ＝ 渡り切り',36)
# Speed brackets: deliberately absent before 0:18 and after 2:54.
speeds=[(18,62,'×4'),(62,98,'×2'),(98,102,'×4'),(102,153,'×2'),(153,157,'×4'),(157,174,'×1')]
for a,b,label in speeds:
 xa,xb=X(a)+4,X(b)-4
 line([(xa,250),(xa,274),(xb,274),(xb,250)])
 text((xa+xb)/2,205,label,38,center=True)
# Three completion marks, exactly at the supplied video timestamps.
for s,label in [(72,'1:12 BZ'),(97,'1:37 跳跳'),(153,'2:33 パッカン')]:
 xx=X(s)
 text(xx,398,label,36,color=GOLD,center=True)
 text(xx,452,'★',48,color=GOLD,center=True)
 line([(xx,510),(xx,620)],GOLD,2)
# Main ribbon.
scenes=[(0,3,'OP',GRAY),(3,18,'自己紹介',GRAY),(18,62,'施工',BZ),(62,72,'BZ が渡る',BZ),(72,88,'坂挑戦',BIRD),(88,97,'登坂',CRAB),(97,102,'呼ぶ・戻る',None),(102,153,'救助',AI),(153,157,'集合',ALL),(157,174,'万歳',ALL),(174,177,'ED',GRAY)]
MAIN_Y=620
external={'OP':(X(1.5),547),'呼ぶ・戻る':(X(99.5)+48,542),'集合':(X(155)+25,542),'ED':(X(175.5),547)}
for a,b,label,color in scenes:
 xa,xb=X(a),X(b);mid=(xa+xb)/2
 if color is None:
  rect(xa,MAIN_Y,(xb-xa)/2,BAND_HEIGHT,BIRD);rect(mid,MAIN_Y,(xb-xa)/2,BAND_HEIGHT,CRAB)
 else:rect(xa,MAIN_Y,xb-xa,BAND_HEIGHT,color)
 line([(xa,MAIN_Y),(xa,MAIN_Y+BAND_HEIGHT)],'white',3)
 if label in external:
  tx,ty=external[label]
  line([(mid,MAIN_Y),(mid,ty+49),(tx,ty+49)],INK,2)
  text(tx,ty,label,34,center=True)
 else:text(mid,MAIN_Y+10,label,36,center=True)
line([(RIGHT,MAIN_Y),(RIGHT,MAIN_Y+BAND_HEIGHT)],'white',3)
# Main boundary labels use the same time positions. Stagger narrow neighbors.
for s in [0,3,18,62,72,88,97,102,153,157,174,177]:
 yy=706 if s not in (3,102,157,177) else 764
 line([(X(s),MAIN_Y+BAND_HEIGHT),(X(s),yy-10)],MUTED,1)
 tx=X(s)
 if s==0:tx+=4
 if s==177:tx-=10
 text(tx,yy,tm(s),30,center=True)
# PPO's four actions: exact attachment points, separate readable callouts.
actions=[(102,1835,890,'A 1:42 座らせる'),(108,2300,1025,'B 1:48 押し上げる（動画で約 36 秒）'),(144,2750,890,'C 2:24 立たせる'),(147,3210,1025,'D 2:27 進ませる')]
for sec,tx,ty,label in actions:
 xx=X(sec);dot_y=842
 line([(xx,MAIN_Y+BAND_HEIGHT),(xx,dot_y),(tx,ty-18)],GREEN,2)
 r=6;d.ellipse(((xx-r)*SCALE,(dot_y-r)*SCALE,(xx+r)*SCALE,(dot_y+r)*SCALE),fill=GREEN)
 text(tx,ty,label,32,color=GREEN,center=True)
# Face ribbon: every cell uses X(a), X(b), never categorical/equal widths.
text(80,1190,'跳跳の顔',42,bold=True)
FACE_Y=1290
faces=[
(18,72,'まる目',['まる目'],'#d9e4f4'),
(72,88,'にっこり／困り',['にっこり／困り'],'#d7eee3'),
(88,97,'真剣',['真剣'],'#e4d9f1'),
(97,102,'まる目',['まる目'],'#d9e4f4'),
(102,112,'にっこり・ほっ',['にっこり・ほっ'],'#d7eee3'),
(112,144,'＞＜／＞＜汗／困り汗',['＞＜／＞＜汗／困り汗'],'#f4dfbd'),
(144,153,'ほっ・にっこり・真剣',['ほっ・にっこり','・真剣'],'#d7eee3'),
(153,157,'キラキラ',['キラ','キラ'],'#f5e8b4'),
(157,174,'にっこり',['にっこり'],'#f0d9df')]
for a,b,name,ss,color in faces:
 xa,xb=X(a),X(b);mid=(xa+xb)/2
 rect(xa,FACE_Y,xb-xa,BAND_HEIGHT,color)
 line([(xa,FACE_Y),(xa,FACE_Y+BAND_HEIGHT)],'white',3)
 assert ''.join(ss)==name
 for j,s in enumerate(ss):
  assert font(28).getlength(s)/SCALE <= xb-xa-5,(name,xb-xa)
  yy=FACE_Y+14 if len(ss)==1 else FACE_Y+j*28
  text(mid,yy,s,28,center=True)
 text(mid,1390,tm(a),28,center=True)
 text(mid,1450,'〜'+tm(b),28,center=True)
line([(X(174),FACE_Y),(X(174),FACE_Y+BAND_HEIGHT)],'white',3)
# Verify duration coverage, common scale, exact endpoints and minimum type size.
assert scenes[0][0]==0 and scenes[-1][1]==177
assert all(scenes[i][1]==scenes[i+1][0] for i in range(len(scenes)-1))
assert faces[0][0]==18 and faces[-1][1]==174
assert all(faces[i][1]==faces[i+1][0] for i in range(len(faces)-1))
assert abs((X(62)-X(18))/(X(153)-X(102))-44/51)<1e-12
im.save(ROOT.parent/'timeline_ortiz.png',dpi=(300,300))
if __name__=='__main__':
 print('7200 × 3600; 2:1; 11 scene cells, 9 face cells, 6 speed brackets, 3 stars, 4 action pins.')
 print('Both ribbons are proportional to video time; construction/rescue width ratio = 44/51.')
