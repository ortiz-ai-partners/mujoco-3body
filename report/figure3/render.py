"""Render the mood-network pipeline using BIZ UDPGothic Regular/Bold only.
Run: python -m pip install Pillow; python render.py
"""
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
W,H=4400,2475
im=Image.new('RGB',(W,H),'#f5f8fc');d=ImageDraw.Draw(im)
INK='#24344b';MUTED='#60728a';BLUE='#466ab2';GREEN='#388d82';PURPLE='#8862af';GOLD='#ba8740'
RUNS=[]
@lru_cache(None)
def font(n,bold=False):return ImageFont.truetype(str(ROOT.parent/'fonts'/('BIZUDPGothic-Bold.ttf' if bold else 'BIZUDPGothic-Regular.ttf')),n)
def t(x,y,s,n=32,c=INK,bold=False,center=False):
 ft=font(n,bold)
 if center:x-=ft.getlength(s)/2
 bb=d.textbbox((x,y),s,font=ft,anchor='lt')
 assert bb[0]>=0 and bb[2]<=W and bb[1]>=0 and bb[3]<=H,(s,bb)
 d.text((x,y),s,font=ft,fill=c,anchor='lt');RUNS.append((s,n,bold,bb))
def lines(x,y,ss,n=32,gap=48,c=INK,bold=False):
 for s in ss:t(x,y,s,n,c,bold);y+=gap
 return y
def box(x,y,w,h,fill='#ffffff',edge='#d1ddeb',stroke=3,r=22):d.rounded_rectangle((x,y,x+w,y+h),r,fill=fill,outline=edge,width=stroke)
def arrow(x,y,x2,c=MUTED):
 d.line((x,y,x2-15,y),fill=c,width=7);d.polygon([(x2,y),(x2-26,y-15),(x2-26,y+15)],fill=c)
def heading(x,y,s,c):t(x,y,s,36,c,True)
t(65,35,'気分ネットの学習データと学習の流れ',66,bold=True)
t(70,130,'シミュレーションで集めた「手の途中の状態」から、手の結末と渡り切りを予測する',35,MUTED)
xs=[65,1150,2235,3320];colors=[BLUE,GREEN,PURPLE,GOLD];fills=['#edf3ff','#eef9f6','#f4effb','#fff7e8'];titles=['学習環境で走らせる','0.1 秒ごとに記録','学習・モデル選択','本番で使う']
for i,x in enumerate(xs):
 box(x,230,1015,1500,fills[i],colors[i]);d.ellipse((x+30,265,x+100,335),fill=colors[i]);t(x+65,278,str(i+1),40,'white',True,True);t(x+120,275,titles[i],41,colors[i],True)
 if i<3:arrow(x+1025,970,x+1075)
# 1. Collection scenarios.
x=xs[0]+35
heading(x,405,'学習用の世界',BLUE)
lines(x,465,['本番と同じコース。','開始状態だけを配置して始める。'],34,53)
box(x,620,945,245,'#ffffff','#bfd0e8')
lines(x+25,650,['固定ルール：2 シード','PPO：2 シード','ランダム：1 シード'],35,65)
heading(x,930,'開始場面は 7 種類',BLUE)
lines(x,1000,['足元：座り／別向き／立ち／転倒','天面：座り／転倒','坂の途中：転倒'],33,66)
box(x,1280,945,185,'#ffffff','#bfd0e8')
t(x+472,1310,'（2 ＋ 2 ＋ 1）× 7',42,BLUE,False,True);t(x+472,1380,'＝ 35 試行',52,BLUE,True,True)
lines(x,1580,['多様な開始場面と支配人を組み合わせ、','うまくいく手・失敗する手を集める。'],31,50,MUTED)
# 2. Inputs and labels.
x=xs[1]+35
heading(x,405,'各スキルの最中に記録',GREEN)
box(x,480,945,285,'#ffffff','#b6d9ce')
lines(x+25,510,['支配人の観測：46 次元','＋ いまの手：6 種の one-hot','＋ その手を始めてからの秒数：1'],33,57)
t(x+472,695,'＝ 53 個の数値',43,GREEN,True,True)
heading(x,825,'正解①：その手の結末',GREEN)
lines(x,885,['手が終わったら、その手の全サンプルに','成功／止まる／転ばせる／空振り','のいずれかを付ける'],31,50)
heading(x,1090,'正解②：その試行の渡り切り',GREEN)
lines(x,1150,['その試行でパッカンが渡り切ったかを、','その試行の全サンプルに付ける'],31,50)
box(x,1350,945,180,'#ffffff','#b6d9ce')
t(x+472,1380,'47,952 サンプル',47,GREEN,True,True);t(x+472,1455,'収集時間：23 分',34,INK,False,True)
t(x,1630,'入力は手の途中、正解は実行後の結果。',31,MUTED)
# 3. Train, select, and evaluate.
x=xs[2]+35
heading(x,385,'小さな MLP（tanh）',PURPLE)
for i,value in enumerate(['53','32','32','5']):
 xx=x+10+i*235;box(xx,445,180,100,'#ffffff','#cfb9e3',r=16);t(xx+90,467,value,45,PURPLE,False,True)
 if i<3:arrow(xx+190,496,xx+223,PURPLE)
lines(x,580,['出力：4 クラスの softmax（結末）','＋ sigmoid 1 個（渡れる）','損失：交差エントロピー ＋ BCE','最適化：Adam ／ 約 3,000 パラメータ'],30,48)
lines(x,800,['試行単位で 1/4 を検証用に分ける。','600 エポック学習し、450 エポック目を採用。','選択指標は検証用データの','「うまく終わる手 vs 失敗」の均衡正解率。'],30,47)
box(x,1020,945,195,'#ffffff','#cfb9e3')
t(x+25,1042,'検証用データでの成績（独立ではない※）',31,PURPLE,True)
t(x+25,1100,'4 分類正解率',30);t(x+710,1090,'0.80',40,PURPLE)
t(x+25,1158,'成功 vs 失敗',30);t(x+710,1148,'0.83',40,PURPLE)
# Independent test is emphasized with a thicker border and bold figures.
box(x,1240,945,325,'#ffffff',PURPLE,stroke=7)
t(x+25,1264,'独立テスト',38,PURPLE,True)
t(x+25,1324,'（学習に使っていない 35 試行・44,230 サンプル）',28)
for yy,label,value in [(1380,'4 分類正解率','0.76'),(1440,'成功 vs 失敗','0.85'),(1500,'渡れるか','0.62')]:
 t(x+25,yy,label,31);t(x+710,yy-6,value,44,PURPLE,True)
lines(x,1615,['CPU で学習 3.5 秒','（スクリプト全体で約 1 分）'],30,45,MUTED)
# 4. Inference and thresholds.
x=xs[3]+35
heading(x,405,'救助の間、毎制御ステップで推論',GOLD)
box(x,480,945,170,'#ffffff','#e5c99b')
t(x+472,505,'0.02 秒ごと',48,GOLD,True,True);t(x+472,580,'提出動画の本編で 5,050 回',34,INK,False,True)
heading(x,715,'スキルごとに 2 本の線と比較。',GOLD)
t(x,780,'線の値は検証用データで決めた。',32)
box(x,860,945,150,'#ffffff','#e5c99b')
t(x+25,885,'にっこりの線',35,GOLD,True);t(x+25,945,'うまく終わった手の 8 割が上になる値',31)
box(x,1050,945,150,'#ffffff','#e5c99b')
t(x+25,1075,'困りの線',35,GOLD,True);t(x+25,1135,'失敗の 8 割が下になる値',31)
lines(x,1265,['新しいデータでは線の効き方が手によって','ずれた（失敗した押し上げのうち、','困りの線を下回ったのは 18%）。'],31,48)
lines(x,1460,['予測した確率を線と比べ、','計測値と合わせて表情を決める。'],32,50)
box(x,1600,945,85,'#ffffff','#e5c99b');t(x+472,1625,'→ 図「表情の規則」へ',35,GOLD,False,True)
# Lower horizontal panel.
box(65,1790,4270,460)
t(100,1820,'検証用データでのスキル別の推論の平均（独立ではない）',40,PURPLE,True)
t(100,1880,'数値は各場面における予測確率の平均（正解率ではない）。',30,MUTED)
labels=['押しが届く手','転ぶ手','立たせて立つ','起きない相手','見送りで渡る'];outs=['成功','転ばせる','成功','空振り','成功'];values=['0.99','0.92','0.99','0.62','0.99']
for i in range(5):
 xx=100+i*840;box(xx,1945,805,210,'#f7f8fc','#dbe2ed',r=16)
 t(xx+402,1968,labels[i],34,INK,True,True);t(xx+402,2025,outs[i],30,PURPLE,False,True);t(xx+402,2075,values[i],55,PURPLE,False,True)
t(100,2190,'記録（0.1 秒ごと）と本番推論（0.02 秒ごと）は周期が異なる。検証用の分割はサンプル単位ではなく、試行単位。',30,MUTED)
# Exact supplied footnotes; two visual lines.
footnote='※ 検証用データは入力の正規化とモデル選択にも使ったため、独立したテストではない。独立テストは、学習に使っていないシードで同じ作り方の 35 試行を集め直し、本番のネットを重み・正規化・線ごとそのまま採点した値。'
assert font(26).getlength(footnote)<=4260
t(70,2320,footnote,26,MUTED)
t(70,2385,'出典：学習と評価の記録。気分ネットは結果を予測し、表情の規則へ渡す。',28,MUTED)
assert not any('話' in r[0] for r in RUNS)
assert all(any(term in r[0] for r in RUNS) for term in ['one-hot','softmax','sigmoid','0.76','0.85','0.62','5,050','18%'])
im.save(ROOT.parent/'mood_net_pipeline_ortiz.png',dpi=(300,300))
if __name__=='__main__':print('Created 4400 × 2475 PNG (16:9), BIZ UDPGothic Regular/Bold only.')
