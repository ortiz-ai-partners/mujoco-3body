from PIL import Image,ImageDraw,ImageFont,ImageOps
import math
from pathlib import Path
from functools import lru_cache
ROOT=Path(__file__).resolve().parent
@lru_cache(None)
def getfont(size,bold=False):
 return ImageFont.truetype(str(ROOT.parent / "fonts" / ("BIZUDPGothic-Bold.ttf" if bold else "BIZUDPGothic-Regular.ttf")),size*2)
TEXT_RUNS=[]
W,H=3600,2400
im=Image.new('RGB',(W*2,H*2),'#f5f8fc')
class ScaledDraw:
 def __init__(self,image):self.raw=ImageDraw.Draw(image)
 def coords(self,xy):
  return [tuple(v*2 for v in p) for p in xy] if isinstance(xy[0],(tuple,list)) else tuple(v*2 for v in xy)
 def __getattr__(self,name):
  def call(xy,*args,**kw):
   for k in ('width','radius'):
    if k in kw:kw[k]*=2
   return getattr(self.raw,name)(self.coords(xy),*args,**kw)
  return call
 def textbbox(self,xy,*args,**kw):return tuple(v/2 for v in self.raw.textbbox(self.coords(xy),*args,**kw))
 def text(self,xy,text,font,fill,**kw):
  if '⇆' not in text:return self.raw.text(self.coords(xy),text,font=font,fill=fill,**kw)
  # BIZ UDPGothic has ⇄ but no U+21C6. Mirror its own glyph;
  # no fallback font and no changed wording.
  before,after=text.split('⇆');x,y=self.coords(xy)
  self.raw.text((x,y),before,font=font,fill=fill,**kw)
  advance=font.getlength(before);w=round(font.getlength('⇄'));h=font.size*2
  tile=Image.new('RGBA',(w,h));td=ImageDraw.Draw(tile)
  # use a common ascender baseline to preserve the surrounding text alignment
  td.text((0,0),'⇄',font=font,fill=fill,anchor='la')
  offset=font.getbbox(text.replace('⇆','⇄'))[1]
  im.paste(ImageOps.mirror(tile),(round(x+advance),round(y-offset)),ImageOps.mirror(tile))
  self.raw.text((x+advance+w,y),after,font=font,fill=fill,**kw)
d=ScaledDraw(im)
font=str(ROOT.parent / 'fonts/BIZUDPGothic-Regular.ttf')
def t(x,y,s,size=30,c='#24344b'):
 ft=getfont(size,size>=34); d.text((x,y),s,font=ft,fill=c,anchor='lt')
 TEXT_RUNS.append((x,y,s,size,d.textbbox((x,y),s,font=ft,anchor='lt')))
def box(x,y,w,h,title,color,fill):
 d.rounded_rectangle((x,y,x+w,y+h),radius=26,fill=fill,outline=color,width=3);t(x+25,y+15,title,40,color)
def lines(x,y,arr,size=30,gap=46):
 for s in arr:t(x,y,s,size);y+=gap
 return y
def arrow(points,label='',lx=0,ly=0,col='#4f6e97',dash=False):
 for a,b in zip(points,points[1:]):
  if dash:
   dist=math.dist(a,b)
   for k in range(0,int(dist),22):
    p=[a[i]+(b[i]-a[i])*k/dist for i in (0,1)];q=[a[i]+(b[i]-a[i])*min(k+12,dist)/dist for i in (0,1)];d.line((tuple(p),tuple(q)),fill=col,width=5)
  else:d.line((a,b),fill=col,width=5)
 a,b=points[-2:];ang=math.atan2(b[1]-a[1],b[0]-a[0]);d.polygon([b,(b[0]-20*math.cos(ang-.45),b[1]-20*math.sin(ang-.45)),(b[0]-20*math.cos(ang+.45),b[1]-20*math.sin(ang+.45))],fill=col)
 if label:
  f=getfont(29);bb=d.textbbox((lx,ly),label,font=f);d.rectangle((bb[0]-8,bb[1]-4,bb[2]+8,bb[3]+4),fill='#f5f8fc');t(lx,ly,label,29,col)
t(65,30,'MuJoCo 3 体連携と 2 つの AI ― 全体の仕組み',65)
t(70,120,'制御・物理のループ ／ 結果予測と表情描画の経路',32,'#60728a')
box(70,200,2250,660,'AI 1　支配人 AI ｜ 3 種を比較','#466ab2','#edf3ff')
lines(100,280,['入力：観測 46 次元 ― パッカンの位置・向き・姿勢・傾き、跳跳の位置・接触、', '　　　直前の手と結果、押し上げ回数、経過時間','出力：WAIT / SEAT / PUSH / BACK_OFF / STANDUP / WALK_ON ＋ 吹き出しの定型セリフ'],31,45)
for x in (805,1550):d.line((x,440,x,825),fill='#bfcee5',width=2)
t(100,445,'固定ルール ｜ 学習なし',34,'#466ab2')
lines(100,505,['手書きの if-then 判断表','座っているか・跳跳の方を向いているか','密着しているか・どの段階か','→ 次の一手'],28,46)
t(835,445,'表形式 Q 学習 ｜ Q 表',34,'#466ab2')
lines(835,505,['状態 ＝ 直前の結果 × 姿勢 × 進行段階','× 南向きか × 座席か × 密着か','× 押し上げ回数 ／ 行動 6 種','120 試行・2 時間、ε-greedy で学習','状態 × 行動の価値を表で学ぶ'],28,46)
t(1580,445,'PPO ｜ SB3・actor-critic',34,'#466ab2')
lines(1580,505,['行動 MLP：46 → 64 → 64 → 6','価値 MLP：46 → 64 → 64 → 1','tanh・行動出力は 6 手の確率','12 並列 × 12,000 決定（約 4 時間）','を 2 回：中規模 → 報酬 v2.2 で継続','方策勾配による強化学習'],28,46)
box(2440,200,1090,850,'AI 2　気分ネット ｜ 教師あり学習','#8862af','#f4effb')
lines(2470,280,['入力：同じ観測 ＋ いまの手 ＋ 経過時間','53 → 32 → 32 → 5 の MLP（tanh）','出力①：4 クラスの softmax','（成功 / 止まる / 転ばせる / 空振り）','出力②：sigmoid → 渡れる確率','損失：交差エントロピー ＋ BCE','Adam、600 エポック中 450 エポック目を採用、約 3,000 パラメータ','学習環境で固定ルール・PPO・ランダムを実行','0.1 秒ごとに記録：47,952 サンプル（35 試行）','試行単位で 1/4 を検証用に分割','4 分類の正解率：0.76（独立テスト、※）','PyTorch / CPU、学習 3.5 秒','（スクリプト全体で約 1 分）'],30,56)
box(70,1000,2250,660,'MuJoCo 3.11 の 1 つのワールド','#388d82','#eef9f6')
t(100,1070,'物理は 1 つ ／ 通し実行中は外力なし・テレポートなし',33,'#388d82')
for x in (805,1550):d.line((x,1160,x,1615),fill='#b3dacf',width=2)
# Small pictograms, drawn as vectors for dependable print rendering.
def icon(x,y,kind):
 if kind=='bz':
  d.rounded_rectangle((x,y+35,x+108,y+70),radius=16,fill='#aa8546');d.rectangle((x+18,y+5,x+65,y+45),fill='#e7b958');d.rectangle((x+33,y+12,x+58,y+32),fill='#f5f8fc');d.line((x+100,y+45,x+127,y+20),fill='#aa8546',width=8);d.rectangle((x+123,y+13,x+138,y+67),fill='#c79843')
 elif kind=='bird':
  d.ellipse((x+10,y+24,x+90,y+74),fill='#71a6c7');d.ellipse((x+62,y,x+108,y+46),fill='#71a6c7');d.polygon([(x+104,y+20),(x+135,y+30),(x+104,y+36)],fill='#e8b24d');d.ellipse((x+89,y+13,x+95,y+19),fill='#24344b')
 else:
  d.ellipse((x+25,y+20,x+105,y+70),fill='#ca7b82')
  for yy in (30,48,65):
   d.line((x+30,y+yy,x+5,y+yy+12),fill='#ca7b82',width=6);d.line((x+100,y+yy,x+130,y+yy+12),fill='#ca7b82',width=6)
  for xx in (47,80):d.ellipse((x+xx,y+10,x+xx+12,y+26),fill='#24344b')
for x,k in [(105,'bz'),(840,'bird'),(1585,'crab')]:icon(x,1165,k)
t(260,1175,'ブルドーザー BZ',34);t(995,1175,'パッカン（Microduck）',34);t(1740,1175,'跳跳（Jumper）',34)
lines(105,1270,['ルール制御：course-builder','ニューラルネットなし','坂 2 枚を保管場所から運んで設置','→ 峠を走破'],29,53)
lines(840,1270,['公式 ONNX ポリシー ｜ 推論のみ','velstand：観測 61 次元 → 関節目標','立つ・歩く・転倒から起きる','alpha_sitstand：座る ⇆ 立つ','サーボ：XML の公式値','Pollen Robotics が強化学習で作成'],29,53)
lines(1585,1270,['公式ポリシー ｜ 推論のみ','locomotion：415 次元・200 Hz・ONNX','jump：167 次元 ／ 跳ぶ','dance_crab：209 次元 ／ 踊る','KingKong Robotics 公式バンドル'],29,53)
box(70,1800,2250,230,'スキル（固定プログラム）','#466ab2','#edf3ff')
lines(100,1880,['SEAT / PUSH / BACK_OFF / STANDUP / WALK_ON / WAIT','各スキル ＝ 公式ポリシーへの指令列（速度指令・座る／立つのフラグ）'],32,54)
box(2440,1190,1090,430,'表情の規則（17 本）','#ba8740','#fff7e8')
lines(2470,1270,['入力：気分ネットの確率 ＋ 計測値','接触力（パッカンへ）・押している時間・進み','転倒・自分の傾き','出力：11 の顔'],30,58)
box(2440,1770,1090,260,'表示パネル ＋ 顔モニター','#ba8740','#fff7e8')
lines(2470,1850,['描画のみ：物理には影響しない','顔あり／なしで最終状態が一致'],33,60)
arrow([(290,1000),(290,860)],'観測 46 次元',320,910)
arrow([(100,860),(35,860),(35,1730),(380,1730),(380,1800)],'一手',80,1690)
arrow([(1280,1800),(1280,1660)],'指令 → 公式ポリシー → 関節目標 → 物理',1370,1710)
arrow([(2320,330),(2440,330)],'同じ観測',2280,260,col='#8862af')
arrow([(2960,1050),(2960,1190)],'確率',2990,1090,col='#8862af')
arrow([(2320,1450),(2440,1450)],'計測値',2290,1380,col='#ba8740')
arrow([(2960,1620),(2960,1770)],'顔（描画のみ）',2990,1670,col='#ba8740',dash=True)
d.line((70,2090,3530,2090),fill='#c9d5e2',width=2)
def paragraph(x,y,text,width,size=27,leading=38):
 # Wrap only at visual line boundaries; preserve all supplied characters.
 line=''
 for ch in text:
  if getfont(size).getlength(line+ch)>width*2:
   t(x,y,line,size);y+=leading;line=''
  line+=ch
 if line:t(x,y,line,size);y+=leading
 return y
notes=[
'原則：通し実行中は外力なし・テレポートなし（学習・評価の各試行はリセット時に初期配置を書き込む）。学習は支配人（PPO / Q）と気分ネットの 2 か所。描画と物理は分離。',
'※ 気分ネットの正解率は、学習に使っていないシードで集め直した 35 試行での値（独立テスト）。学習時の検証データでの 0.80 は、正規化とモデル選択に同じデータを使ったため独立ではない。',
'用語　多層パーセプトロン（MLP）＝ 数値を入れて数値を出す、いちばん単純な全結合のニューラルネット。 PPO ＝ 試行錯誤の報酬から方策を学ぶ強化学習。 Q 表 ＝ 状態 × 行動の価値を表に書いて学ぶ強化学習。 教師あり学習 ＝ 正解付きのデータから当て方を学ぶ。']
y=2120
for note in notes:y=paragraph(70,y,note,3460)+12
assert y<=2395, y
# All text is drawn directly on the full canvas, without line-height clipping.
for x,y,txt,size,b in TEXT_RUNS:
 assert 0<=b[0] and b[2]<=W and 0<=b[1] and b[3]<=H,(txt,b)
for word in ['BACK_OFF','WALK_ON','alpha_sitstand','dance_crab']:
 assert any(word in r[2] for r in TEXT_RUNS)
im.save(ROOT.parent/'system_overview_ortiz.png',dpi=(300,300))
if __name__=='__main__':
 print('Created 7200 × 4800 PNG using BIZ UDPGothic Regular/Bold only.')
