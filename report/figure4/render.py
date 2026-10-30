"""Face-rule decision chart. Pillow + bundled BIZ UDPGothic fonts only.
Run: python -m pip install Pillow; python render.py
"""
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont
import math
ROOT=Path(__file__).resolve().parent
W,H,S=3200,4000,2
im=Image.new('RGB',(W*S,H*S),'white');d=ImageDraw.Draw(im)
INK='#23354c';EDGE='#315b88';QF='#e0f1fc';LABEL='#fff0c4';GRAY='#737b87'
RUNS=[];FACES=[]
@lru_cache(None)
def font(n,b=False):return ImageFont.truetype(str(ROOT.parent/'fonts'/('BIZUDPGothic-Bold.ttf' if b else 'BIZUDPGothic-Regular.ttf')),n*S)
def text(x,y,ss,n=32,b=False,c=INK,center=True,bg=False):
 if isinstance(ss,str):ss=[ss]
 gap=n+12
 for j,s in enumerate(ss):
  ft=font(n,b);xx=x*S-ft.getlength(s)/2 if center else x*S;yy=(y+j*gap)*S
  bb=d.textbbox((xx,yy),s,font=ft,anchor='lt')
  assert min(bb[:2])>=0 and bb[2]<=W*S and bb[3]<=H*S,(s,bb)
  if bg:d.rounded_rectangle((bb[0]-10,bb[1]-7,bb[2]+10,bb[3]+7),radius=8,fill=LABEL)
  d.text((xx,yy),s,font=ft,fill=c,anchor='lt');RUNS.append((s,n,b))
def path(pts,arrow=True,color=INK):
 pp=[(x*S,y*S) for x,y in pts];d.line(pp,fill=color,width=3*S)
 if arrow:
  a,b=pts[-2:];ang=math.atan2(b[1]-a[1],b[0]-a[0]);r=17
  d.polygon([(b[0]*S,b[1]*S),((b[0]-r*math.cos(ang-.45))*S,(b[1]-r*math.sin(ang-.45))*S),((b[0]-r*math.cos(ang+.45))*S,(b[1]-r*math.sin(ang+.45))*S)],fill=color)
def rounded(cx,cy,w,h,fill,edge=EDGE,stroke=3):d.rounded_rectangle(((cx-w/2)*S,(cy-h/2)*S,(cx+w/2)*S,(cy+h/2)*S),radius=18*S,fill=fill,outline=edge,width=stroke*S)
def diamond(cx,cy,w,h,ss):
 pts=[(cx,cy-h/2),(cx+w/2,cy),(cx,cy+h/2),(cx-w/2,cy)]
 d.polygon([(x*S,y*S) for x,y in pts],fill=QF);path(pts+[pts[0]],False,EDGE)
 if isinstance(ss,str):ss=[ss]
 text(cx,cy-(len(ss)*54-12)/2,ss,42,True)
PALETTE={'ぐるぐる':('#f9c8dc','#a53c67'),'ガーン':('#fff0bd','#a07833'),'にっこり':('#f8c6da','#ab3e68'),'キラキラ':('#bceff0','#337f89'),'ほっ':('#d4f7bd','#53844c'),'困り':('#ddcdf9','#7353a0'),'真剣':('#c7def8','#437eb0'),'まる目':('#c4f5df','#4a8d7b'),'困り汗':('#dbc7f5','#75519c'),'＞＜汗':('#c6eff0','#387e8b'),'＞＜':('#d3ddfc','#6179b1')}
def face(cx,cy,name,num,w=390):
 fill,edge=PALETTE[name];rounded(cx,cy,w,116,fill,edge)
 text(cx,cy-29,name,42,True)
 text(cx+w/2-25,cy+20,str(num),30,False,GRAY)
 FACES.append((name,num))
def down(y1,y2,label='いいえ'):
 path([(1600,y1),(1600,y2)])
 if label:text(1695,(y1+y2)/2-18,label,32,bg=True)
# Start and first four checks.
rounded(1600,95,790,100,'#e1d5f8')
text(1600,73,'毎制御ステップ（0.02 s）',42,True)
down(145,240,'')
diamond(1600,320,1000,160,'自分の傾き 50° 超？')
path([(2100,320),(2455,320)]);text(2270,268,'はい',32,bg=True);face(2680,320,'ぐるぐる',1,450)
down(400,500)
diamond(1600,590,1230,180,['パッカンが転んだ直後','1.5 s？'])
path([(2215,590),(2455,590)]);text(2320,538,'はい',32,bg=True);face(2680,590,'ガーン',2,450)
down(680,800)
diamond(1600,880,900,160,'渡り切った？')
path([(1150,880),(725,880)]);text(945,825,'ダンス中',32,bg=True);face(500,880,'にっこり',4,450)
path([(2050,880),(2455,880)]);text(2250,825,'まだダンス前',32,bg=True);face(2680,880,'キラキラ',3,450)
down(960,1080)
diamond(1600,1170,1230,180,['直前の手が成功して','2 s 以内？'])
path([(2215,1170),(2455,1170)]);text(2325,1118,'はい',32,bg=True);face(2680,1170,'ほっ',5,450)
down(1260,1430)
# Five scene branches; rescue stays on the central downward route.
diamond(1600,1510,1000,160,'いまの場面は？')
path([(1600,1590),(1600,1650)],False)
path([(350,1650),(2850,1650)],False)
branches=[(350,['パッカンの坂挑戦で、','足踏み・後ずさり・座り込み'],'困り',6),(1020,['パッカンの坂挑戦で、','登っている'],'にっこり',7),(2240,['自分の登坂'],'真剣',16),(2850,['その他','（戯れ・待機・移動）'],'まる目',17)]
for x,ss,name,num in branches:
 path([(x,1650),(x,1852)]);text(x,1700,ss,32,bg=True);face(x,1910,name,num,430)
path([(1600,1650),(1600,2070)]);text(1600,1810,'救助の場面',32,bg=True)
# Contact decision: non-contact continues directly downward to check 7.
diamond(1600,2170,1000,200,['押している','（接触中）？'])
path([(1100,2170),(500,2170),(500,2442)])
text(500,2245,['止まる＋転ぶ ≥ 40%、','または 転ぶ ≥ 30%、','または 進みなし 3 s'],32,bg=True)
face(500,2500,'困り汗',8,450)
path([(2100,2170),(2920,2170)],False)
for x,ss,name,num,w in [(2280,['力 ≥ 0.7、または','接触 5 s 超'],'＞＜汗',9,420),(2920,['それ以外'],'＞＜',10,390)]:
 path([(x,2170),(x,2442)]);text(x,2270,ss,32,bg=True);face(x,2500,name,num,w)
path([(1600,2270),(1600,2720)])
text(1600,2480,'押していない',32,bg=True)
# Previous push result.
diamond(1600,2810,1120,180,['直前の押しが止まった・','転ばせた？'])
path([(1040,2810),(500,2810),(500,2922)])
text(770,2714,['はい（成功の確率が','にっこりの線を超えるまで）'],32,bg=True)
face(500,2980,'困り',11,450)
down(2900,3110)
# Four probability/skill branches.
diamond(1600,3200,1260,180,['この手の確率 vs','スキルごとの線'])
path([(1600,3290),(1600,3330)],False)
path([(330,3330),(2690,3330)],False)
for x,ss,name,num in [(330,['困りの線以下、または','押しで転ぶ ≥ 30%'],'困り',12),(1010,['にっこりの線以上'],'にっこり',13),(1660,['線の間'],'真剣',14)]:
 path([(x,3330),(x,3582)]);text(x,3390,ss,32,bg=True);face(x,3640,name,num,430)
path([(2690,3330),(2690,3440)],False);text(2690,3360,'様子を見る手',32,bg=True)
path([(2260,3440),(3030,3440)],False)
for x,ss,name,num in [(2260,'渡れる ≥ 60%','にっこり',15),(2645,'渡れる ≤ 30%','困り',15),(3030,'その間','まる目',17)]:
 path([(x,3440),(x,3712)]);text(x,3500,ss,32,bg=True);face(x,3770,name,num,300)
# Only the supplied one-line note.
note='確率は気分ネットの出力。線は一度越えると 5 ポイント戻るまで切り替えない。顔は描画だけで、物理には影響しない。'
text(1600,3915,note,30)
assert set(n for _,n in FACES)==set(range(1,18))
assert min(n for _,n,_ in RUNS)>=.7*42
assert ('にっこり',15) in FACES and ('困り',15) in FACES and FACES[-1]==('まる目',17)
im.save(ROOT.parent/'face_rules_chart_ortiz.png',dpi=(300,300))
if __name__=='__main__':print('6400 × 8000 (4:5); all 17 rule numbers; text-only faces; vertical non-contact continuation.')
