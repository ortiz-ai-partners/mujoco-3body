# -*- coding: utf-8 -*-
"""
marimba（最終版 v4）-- 提出動画（講座 OP の後、自己紹介 15.1 s＋本編＋講座 ED）用 BGM。

v4：本編を学習済み PPO の支配人（take 58、155.5 s）に替えた。押し上げの後の手が違う（離れるを省く）ので、押し上げ成功〜進ませる・
渡り切り・万歳・終わりの合図を take 58 の時刻へ写し、天面を歩く G を 14 拍 -> 12 拍に書き直した（テンポは約 118 BPM のまま）。
環境変数 BGM_MAIN=take57 で固定ルール版（試作 4 まで）の BGM を out/music/bgm_marimba_take57.wav に書く。

v3（10/29 ゆうころの指定）：
  ・曲は OP から自己紹介に切り替わる瞬間に始まる。0.0–15.1 s は自己紹介のための新しい前奏（約 119 BPM、
    2 拍の弱起＋7 小節。カードのチャイム（C–E–C）が鳴る 7.6／8.9／10.2 s は C と Am の小節に置いた）。
  ・本編は take 56（= take 55 の時刻、物理は take 51 と同じ）。15.1 s＋本編の動画時刻で鳴る。
    take 51 からの違い：呼ぶ〜戻る（CALL・RETURN）とゴール前の集合（CELEBRATE）が 4 倍速になり約半分の長さ。
    E（呼ぶ）は 16 拍→10 拍、H（集合）は 17 拍→8.5 拍に書き直した。ほかの区間は時刻をずらしただけ（W()）。
  ・BGM の音量は一定：場面ごとの強弱の自動化と、声の「間」（POCKET）を外した（曲の中の強弱＝打鍵の強さはそのまま）。
  ・最後の G 和音（171.4 s）は本編の終わり（172.4 s）を越えて講座 ED に響かせ、175.0 s までに消す。

以下は v2（take 51 の 167.0 s 版）の説明。時刻は take 51 の動画時刻。

marimba -- 3 体ロボット動画（全長 167.0 s）用 BGM。木琴・マリンバ風の柔らかい打鍵を軸にした完全オリジナル合成。

numpy / scipy だけで合成する（既存の曲・音源・サンプルは不使用、乱数は seed 固定で決定的）。
引数なしで実行すると、out/music/bgm_marimba.wav（44,100 Hz / stereo / 16 bit、提出版の本編 take 58 に合わせた 173.6 s）を書く。
環境変数 BGM_DIAG=1 で楽器ごとの区間 RMS も表示する。

調  ：F major（施工〜3 体渡り切り）→ 集合の終わりで D7 を経て、万歳のダンスは G major（一段上げて明るく）
拍  ：区間ごとに「拍→秒」の地図を作り、合図の時刻にちょうど拍が来るようにしている（TM クラス）

  動画時刻 (s)    合図                          曲の中身
  --------------  ----------------------------  -----------------------------------------------------
  0.0 – 44.1      施工（4 倍速）                 120 BPM・22 小節。マリンバの 16 分刻み＋ピチカートベース
                                                 ＋シェイカー＋柔らかいキック。前奏 2 小節 → 主題 A（8 小節）
                                                 → 主題 B（8 小節、裏拍の和音とパッドを足す）→ つなぎ 4 小節
  44.1 – 54.0     BZ が峠を渡り切る・パッカン追う  121 BPM・5 小節。刻みを 8 分に減らし、歩く旋律、最後に 16 分で駆け上がり
  54.0            星 1（BZ 渡り切り）              チャイム 4 音（F 和音の分散）＋ヴィブラフォン＋低音
  54.0 – 68.2     パッカン挑戦・跳跳の応援ダンス    約 80 BPM。和音は変わり目だけ、間を作る。応援はピチカートの跳ね
     54.1–60.2    1 回目の挑戦                   登る動機（D–E–F–G–A の上行）
     60.2         後ずさり（困り）                下行して止まる動機、Gm に 6 度の問いかけ
     62.4         もう一度                       1 段高い上行（F–G–A–Bb–C、Bb→C）
     65.4         また登れない                   借用の Bbm でため息の下行
     68.2         座り込む                       Fadd9 へ（iv→I の温かい終止、暗くしすぎない）
  70.3 – 78.9     跳跳が登る・75.4 天面でジャンプ  約 118 BPM。上行ベース Bb–C–D–Eb–E に乗って 16 分の分散和音が昇る、
                                                 75.4 で F 和音＋32 分のグリッサンド、天面を跳ねる旋律
  78.9            星 2（跳跳 渡り切り）            チャイム 3 音＋F 和音
  78.9 – 88.2     仲間を呼ぶ・跳跳が回って戻る      約 103 BPM の静かな間。呼び声の 2 音（C–A）とこだま、歩くベース
  88.2 – 133.5    救助
     88.2         座らせる（支配人 AI が手を選ぶ） 120 BPM、考える 8 分の動機（保続音＋上の音が動く）
     94.2         押し上げ開始                   約 108 BPM。層 1：ベースの踏ん張り型＋柔らかいキック
     100.9        一瞬止まる                     1 拍だけ打鍵・打楽器を休む（パッドのみ）→ 再開で層 2：裏拍の和音
     109.9        一瞬止まる                     1 拍休む → 層 3：シェイカー＋救助の旋律（1 小節ずつ高く積み上がる）
     ~118         （汗の力仕事）                  16 分の刻みを追加、キックを毎拍に
     127.6–129.8  （最後のひと押し）              Csus4→C のロールで引っぱる
     129.8        押し上げ成功（ほっ）            F へ解決、ロール和音＋チャイム、刻みを止めて息をつく
     130.7        立たせる                       上行の分散和音 C–F–A–C–F
     133.5        「そのまま進んで」               ベースのピックアップ → 歩くベース
  133.5 – 140.6   天面を歩いて下り坂を降りる       約 118 BPM。主題 A の頭＋ウォーキングベース、16 分で駆け上がり
  140.6           3 体とも渡り切り（最大の山場）    全員で F 和音、チャイムのきらめき 10 音、低音
  140.6 – 149.1   ゴール前に集まる                余韻（F→Bb の柔らかい分散）→ 期待（Am7→D7sus4→D7、8 分で高める）
                                                 148.6 から 16 分のピックアップ G–A–B–C
  149.1 – 164.5   輪になって万歳（等速）           約 125 BPM・8 小節。G major で主題 A を再現（オクターブ下で重ねる）、
                                                 16 分刻み＋裏拍の和音＋跳ねるベース＋シェイカー＋キック
  164.5           場面の終わり                   G 和音で締める
  164.5 – 167.0   フェードアウト                 余弦で 166.8 s までに消し、166.8 以降は完全な無音

楽器の作り方（すべて加算合成）
  マリンバ    減衰する正弦の基音＋4 倍・9.6 倍の倍音（2–5 kHz に入る倍音はさらに半分）、共鳴管のうなり、
              4 ms の柔らかい立ち上がり。減衰時間は音高で変える
  ピチカート  倍音 1–8（2.2 kHz まで）、高い倍音ほど早く消える、撥弦の短いピッチ落ち
  シェイカー  5.5–11 kHz の帯域ノイズ、6 ms の柔らかい立ち上がり、ごく小さく
  キック      107→47 Hz に落ちる正弦、柔らかく
  パッド      3 声デチューン（±7 cent）の加算波（1.5 kHz まで）、ゆっくり立ち上がり／離す（場面の継ぎ目のクロスフェード）
  ヴィブラフォン／チャイム  星ときらめき用。基音中心、トレモロ
仕上げ：合成残響（220–4200 Hz の帯域）、38 Hz ハイパス、100 Hz 以下 −3 dB のシェルフ、
        2.5 kHz −4 dB・4.0 kHz −5 dB のディップ、13 kHz ローパス、場面ごとの音量の自動化、声の「間」、
        RMS −20 dBFS に正規化、先読みリミッターでピーク −1.3 dBFS 以下、TPDF ディザで 16 bit 化。

v2（検証の指摘への対応）
  声の「間」  ロボットの声（take51）の句 52 個の時刻表 VOICE_PHRASES を持ち、句の下だけ BGM を −4.5 dB 下げる
              （句の 0.06 s 前から 0.06 s で下げ、句の後 0.3 s で戻す、余弦）。曲が合図で打つ 44.1・129.8・140.6・
              149.1 は下げない、88.2 は半分。環境変数 BGM_POCKET_DB=0 で「間」なし（別テイクの声のとき）。
  場面の強弱  声の多い施工を −2.5 dB、万歳を −0.5 dB（それでも最も大きい区間）、声のほとんど無い押し上げの
              前半〜中盤を +1.2 dB。44.1 は施工の終わりより 1.5 dB 上げて入る、70.3 は 68.2→70.0 で −4 dB まで
              沈めてから −2.5 dB へ段を付け、柔らかいキックを 1 打足す。
  シェイカー  坂の場面（54–68 s）は 0.3→0.13（約 −7 dB）。
"""
import os
import sys
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d, uniform_filter1d

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SR = 44100
INTRO = 15.1                              # 自己紹介の長さ：本編の 0 s は曲の 15.1 s
ED = 2.97                                 # 講座の ED カード（最後の和音をここまで響かせる）
# 本編ごとの長さと、take 51 の動画時刻 -> 本編の動画時刻の対応点（両テイクの出来事の時刻を突き合わせたもの。
# 押し上げまでは物理も判断も同じで、違うのは 4 倍速の区間と、押し上げの後の手）
MAINS = {
    # 固定ルールの支配人（5 手：座らせる・押し上げる・離れる・立たせる・進ませる）、提出動画の試作 3〜4
    "take57": dict(length=157.3, map=[(0.0, 0.0), (78.9, 78.9), (88.2, 84.27), (140.6, 136.67), (149.1, 140.93),
                                      (164.5, 156.3), (167.0, 158.8)]),
    # 学習済み PPO の支配人（4 手：離れるを省く）、提出版
    "take58": dict(length=155.5, map=[(0.0, 0.0), (78.9, 78.9), (88.2, 84.27), (129.8, 125.9), (133.5, 128.7),
                                      (140.6, 134.8), (149.1, 139.07), (164.5, 154.43), (167.0, 156.93)]),
}
MAIN = os.environ.get("BGM_MAIN", "take58")   # どの本編に合わせるか（環境変数で切り替え）
DUR = float(np.ceil((INTRO + MAINS[MAIN]["length"] + ED) * 10 - 1e-6) / 10)   # 自己紹介＋本編＋ED を覆う（take 58 は 173.6 s）
N = int(round(DUR * 44100))
# take 51 の動画時刻 -> take 56 の動画時刻（両テイクの出来事の時刻を突き合わせた対応点、物理は同じ）
_MAP51 = MAINS[MAIN]["map"]


def W(t51):
    """take 51 の動画時刻 -> この曲の時刻（自己紹介 15.1 s を足す）。E・H 以外の区間では傾き 1（ずらすだけ）。"""
    return INTRO + float(np.interp(t51, [a for a, _ in _MAP51], [b for _, b in _MAP51]))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "music",                      # 提出動画の BGM（assemble.py --bgm に渡す）
                   "bgm_marimba.wav" if MAIN == "take58" else f"bgm_marimba_{MAIN}.wav")
SEED = 20261029
rng = np.random.default_rng(SEED)        # 作曲側の揺らぎ（タイミング・強さ）
rng2 = np.random.default_rng(SEED + 7)   # 合成側のノイズ・位相
K60 = np.log(1000.0)                     # -60 dB までの減衰係数

# ---------------------------------------------------------------- 音名
_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def m(x):
    """'Bb4' -> 70。int はそのまま。"""
    if isinstance(x, (int, np.integer)):
        return int(x)
    s = x.strip()
    pc = _PC[s[0]]
    i = 1
    while i < len(s) and s[i] in '#b':
        pc += 1 if s[i] == '#' else -1
        i += 1
    return 12 * (int(s[i:]) + 1) + pc


def hz(mi):
    return 440.0 * 2.0 ** ((mi - 69) / 12.0)


def panlaw(p):
    a = (float(np.clip(p, -1.0, 1.0)) + 1.0) * np.pi / 4.0
    return np.cos(a), np.sin(a)


# ---------------------------------------------------------------- 和音（ベース, 跳ねる音, 刻み 4 音, 中域 3 音, パッド）
def _chord(bass, b2, osti, mid, padv):
    return dict(b=m(bass), b2=m(b2), b8=m(bass) + 12,
                osti=[m(n) for n in osti], mid=[m(n) for n in mid], pad=[m(n) for n in padv])


CH = {
    'F':      _chord('F2', 'C3', ['F3', 'C4', 'F4', 'A4'], ['A3', 'C4', 'F4'], ['F3', 'A3', 'C4']),
    'C/E':    _chord('E2', 'G2', ['E3', 'C4', 'E4', 'G4'], ['G3', 'C4', 'E4'], ['E3', 'G3', 'C4']),
    'C':      _chord('C2', 'G2', ['G3', 'C4', 'E4', 'G4'], ['G3', 'C4', 'E4'], ['C3', 'E3', 'G3']),
    'Dm':     _chord('D2', 'A2', ['D3', 'A3', 'D4', 'F4'], ['A3', 'D4', 'F4'], ['D3', 'F3', 'A3']),
    'Bb':     _chord('Bb1', 'F2', ['F3', 'Bb3', 'D4', 'F4'], ['Bb3', 'D4', 'F4'], ['Bb2', 'D3', 'F3']),
    'F/A':    _chord('A1', 'C2', ['F3', 'C4', 'F4', 'A4'], ['A3', 'C4', 'F4'], ['A2', 'C3', 'F3']),
    'Am':     _chord('A1', 'E2', ['E3', 'A3', 'C4', 'E4'], ['A3', 'C4', 'E4'], ['A2', 'C3', 'E3']),
    'Gm':     _chord('G2', 'D3', ['G3', 'D4', 'G4', 'Bb4'], ['Bb3', 'D4', 'G4'], ['G2', 'Bb2', 'D3']),
    'Eb':     _chord('Eb2', 'Bb2', ['G3', 'Bb3', 'Eb4', 'G4'], ['G3', 'Bb3', 'Eb4'], ['Eb3', 'G3', 'Bb3']),
    'Bbm':    _chord('Bb1', 'F2', ['F3', 'Bb3', 'Db4', 'F4'], ['Bb3', 'Db4', 'F4'], ['Bb2', 'Db3', 'F3']),
    'Fadd9':  _chord('F2', 'C3', ['F3', 'C4', 'G4', 'A4'], ['A3', 'C4', 'G4'], ['F3', 'A3', 'C4', 'G4']),
    'Dm7':    _chord('D2', 'A2', ['D3', 'A3', 'C4', 'F4'], ['A3', 'C4', 'F4'], ['D3', 'F3', 'A3', 'C4']),
    'Gm7':    _chord('G2', 'D3', ['G3', 'D4', 'F4', 'Bb4'], ['Bb3', 'D4', 'F4'], ['G2', 'Bb2', 'D3', 'F3']),
    'C7':     _chord('C2', 'G2', ['G3', 'Bb3', 'C4', 'E4'], ['G3', 'Bb3', 'E4'], ['C3', 'E3', 'G3', 'Bb3']),
    'Csus4':  _chord('C2', 'G2', ['G3', 'C4', 'F4', 'G4'], ['G3', 'C4', 'F4'], ['C3', 'F3', 'G3']),
    'Bbmaj7': _chord('Bb1', 'F2', ['F3', 'A3', 'D4', 'F4'], ['A3', 'D4', 'F4'], ['Bb2', 'D3', 'F3', 'A3']),
    'Am7':    _chord('A1', 'E2', ['E3', 'G3', 'C4', 'E4'], ['G3', 'C4', 'E4'], ['A2', 'C3', 'E3', 'G3']),
    'D7sus4': _chord('D2', 'A2', ['D3', 'A3', 'C4', 'G4'], ['A3', 'C4', 'G4'], ['D3', 'G3', 'A3', 'C4']),
    'D7':     _chord('D2', 'A2', ['D3', 'A3', 'C4', 'F#4'], ['A3', 'C4', 'F#4'], ['D3', 'F#3', 'A3', 'C4']),
    'D':      _chord('D2', 'A2', ['D3', 'A3', 'D4', 'F#4'], ['A3', 'D4', 'F#4'], ['D3', 'F#3', 'A3']),
    'G':      _chord('G2', 'D3', ['G3', 'D4', 'G4', 'B4'], ['B3', 'D4', 'G4'], ['G2', 'B2', 'D3']),
    'D/F#':   _chord('F#2', 'A2', ['F#3', 'D4', 'F#4', 'A4'], ['A3', 'D4', 'F#4'], ['F#2', 'A2', 'D3']),
    'Em':     _chord('E2', 'B2', ['E3', 'B3', 'E4', 'G4'], ['G3', 'B3', 'E4'], ['E3', 'G3', 'B3']),
    'G/B':    _chord('B1', 'G2', ['G3', 'D4', 'G4', 'B4'], ['B3', 'D4', 'G4'], ['B2', 'D3', 'G3']),
}


class TM:
    """拍 -> 秒。合図の時刻を拍の錨にして区分線形に写す（区間ごとのテンポ地図）。"""

    def __init__(self, anchors, warp=True):
        """warp=True：錨は take 51 の動画時刻、出力は W() でこの曲の時刻へ。warp=False：錨がそのままこの曲の時刻。"""
        self.b = np.array([a[0] for a in anchors], float)
        self.t = np.array([(W(a[1]) if warp else a[1]) for a in anchors], float)

    def __call__(self, beat):
        b, t = self.b, self.t
        if beat <= b[0]:
            return float(t[0] + (beat - b[0]) * (t[1] - t[0]) / (b[1] - b[0]))
        if beat >= b[-1]:
            return float(t[-1] + (beat - b[-1]) * (t[-1] - t[-2]) / (b[-1] - b[-2]))
        return float(np.interp(beat, b, t))


def chord_at(prog, b):
    s = prog[0][1]
    for bs, sym in prog:
        if bs <= b + 1e-9:
            s = sym
        else:
            break
    return s


# ---------------------------------------------------------------- 音符イベント
EV = []


def _tj(t, jit):
    if jit > 0:
        t += float(np.clip(rng.normal(0.0, jit), -2.5 * jit, 2.5 * jit))
    return max(0.0, t)


def _vj(v, s=0.05):
    return max(0.02, v * (1.0 + float(np.clip(rng.normal(0.0, s), -0.12, 0.12))))


def _val(v, b):
    return v(b) if callable(v) else v


def mar(t, note, vel, pan=0.0, dec=1.0, send=0.22, jit=0.004):
    EV.append(('mar', _tj(t, jit), dict(midi=m(note), vel=_vj(vel), pan=pan, dec=dec, send=send)))


def bas(t, note, vel, dec=0.8, pan=0.0, send=0.07, jit=0.003):
    EV.append(('bass', _tj(t, jit), dict(midi=m(note), vel=_vj(vel, 0.04), pan=pan, dec=dec, send=send)))


def kick(t, vel, send=0.03):
    EV.append(('kick', max(0.0, t), dict(vel=_vj(vel, 0.03), pan=0.0, send=send)))


def shk(t, vel, pan=0.35, send=0.12, jit=0.003):
    EV.append(('shk', _tj(t, jit), dict(vel=_vj(vel, 0.08), pan=pan, send=send)))


def pad(t, dur, notes, vel, att=0.8, rel=1.2, send=0.35):
    for n in notes:
        EV.append(('pad', max(0.0, t), dict(midi=m(n), vel=vel, dur=dur, att=att, rel=rel, send=send)))


def vibe(t, notes, vel, dur, pan=0.0, send=0.3, spread=0.012):
    k = len(notes)
    for i, n in enumerate(notes):
        p = pan + 0.3 * (i - (k - 1) / 2.0) / max(1, k)
        EV.append(('vibe', max(0.0, t + i * spread), dict(midi=m(n), vel=_vj(vel, 0.03), dur=dur, pan=p, send=send)))


def chime(t, note, vel, pan=0.0, send=0.4):
    EV.append(('chime', max(0.0, t), dict(midi=m(note), vel=vel, pan=pan, send=send)))


# ---------------------------------------------------------------- 書き方の道具
OST16 = [0, 2, 1, 2, 3, 2, 1, 2, 0, 2, 1, 2, 3, 1, 2, 1]
OST8 = [0, 2, 1, 3, 0, 2, 1, 3]
PAT_A = [(0, 'b', 0.9), (1.5, 'b2', 0.55), (2, 'b', 0.75), (3, 'b8', 0.6), (3.5, 'b2', 0.5)]
PAT_B = [(0, 'b', 0.85), (1, 'b2', 0.55), (2, 'b8', 0.6), (3, 'b2', 0.55)]
PAT_H = [(0, 'b', 0.85), (1.5, 'b', 0.5), (2, 'b2', 0.68), (3, 'b', 0.58), (3.5, 'b8', 0.45)]
PAT_D = [(0, 'b', 0.9), (1, 'b2', 0.55), (1.5, 'b8', 0.5), (2, 'b', 0.75), (3, 'b2', 0.55), (3.5, 'b8', 0.5)]


def _frac(b):
    return (b + 1e-7) % 1.0


def ostinato(tm, prog, b0, b1, sub=4, pattern=OST16, vel=0.5, pan=-0.28, dec=0.42, skip=None):
    k = 0
    while True:
        b = b0 + k / sub
        if b >= b1 - 1e-9:
            break
        if not (skip and skip(b)):
            notes = CH[chord_at(prog, b)]['osti']
            fr = _frac(b)
            acc = 1.0 if fr < 1e-5 else (0.82 if abs(fr - 0.5) < 1e-5 else 0.66)
            mar(tm(b), notes[pattern[k % len(pattern)]], _val(vel, b) * acc, pan, dec, send=0.18, jit=0.003)
        k += 1


def shaker(tm, b0, b1, sub=4, vel=0.5, pat=None, pan=0.35, skip=None):
    if pat is None:
        pat = (1.0, 0.4, 0.7, 0.45) if sub == 4 else (0.55, 1.0)
    k = 0
    while True:
        b = b0 + k / sub
        if b >= b1 - 1e-9:
            break
        if not (skip and skip(b)):
            shk(tm(b), _val(vel, b) * pat[k % len(pat)], pan)
        k += 1


def bassline(tm, prog, b0, b1, pat, vel=1.0, dec=0.7, skip=None):
    bar = b0
    while bar < b1 - 1e-9:
        for off, which, v in pat:
            b = bar + off
            if b >= b1 - 1e-9 or (skip and skip(b)):
                continue
            bas(tm(b), CH[chord_at(prog, b)][which], v * _val(vel, b), dec=dec)
        bar += 4


def offchords(tm, prog, b0, b1, vel, pan=0.3, dec=0.35, skip=None):
    b = b0 + 0.5
    while b < b1 - 1e-9:
        if not (skip and skip(b)):
            for j, n in enumerate(CH[chord_at(prog, b)]['mid']):
                mar(tm(b) + 0.007 * j, n, _val(vel, b) * (1.0 - 0.08 * j), pan, dec, send=0.2, jit=0.002)
        b += 1.0


def pads(tm, prog, b0, b1, vel, att=0.8, rel=0.8, ov=0.2):
    """和音ごとのパッド。次の和音の立ち上がりと前の和音の離しが重なる＝クロスフェード。"""
    for i, (bs, sym) in enumerate(prog):
        be = prog[i + 1][0] if i + 1 < len(prog) else b1
        s, e = max(bs, b0), min(be, b1)
        if e <= s + 1e-9:
            continue
        t0, t1 = tm(s), tm(e)
        dur = t1 - t0 + ov
        pad(t0, dur, CH[sym]['pad'], _val(vel, s), att=min(att, 0.45 * dur), rel=rel)


def melody(tm, b0, bars, vel, pan=0.1, dec=1.0, tr=0, send=0.22):
    for i, bar in enumerate(bars):
        for bb, du, n in bar:
            b = b0 + 4 * i + bb
            acc = 1.0 if abs(bb - round(bb)) < 1e-6 else 0.9
            mar(tm(b), m(n) + tr, _val(vel, b) * acc, pan, dec * (1.25 if du >= 1.5 else 1.0), send)


def roll(t0, t1, notes, v0, v1, rate=14.0, pan=0.1, dec=0.6):
    n = max(1, int((t1 - t0) * rate))
    for k in range(n):
        v = v0 + (v1 - v0) * k / max(1, n - 1)
        mar(t0 + k / rate, notes[k % len(notes)], v, pan + (0.12 if k % 2 else -0.12), dec, send=0.25, jit=0.004)


def roll_chord(t, notes, vel, spread=0.02, dec=1.4, pan=0.0):
    k = len(notes)
    for i, n in enumerate(notes):
        mar(t + i * spread, n, vel * (1.0 - 0.025 * i), pan + 0.4 * (i / max(1, k - 1) - 0.5), dec, send=0.28, jit=0.001)


def star(t, chimes, vibes, bass_note, vel=0.8, spread=0.045, vdur=2.5):
    k = len(chimes)
    for i, n in enumerate(chimes):
        chime(t + i * spread, n, vel * (0.9 + 0.1 * i / max(1, k - 1)), pan=-0.4 + 0.8 * i / max(1, k - 1))
    vibe(t, vibes, 0.55 * vel, vdur)
    bas(t, bass_note, 0.85 * vel, dec=1.4)


def tones_from(start, pcs, n):
    out, x = [], m(start)
    while len(out) < n:
        if x % 12 in pcs:
            out.append(x)
        x += 1
    return out


# ---------------------------------------------------------------- 旋律（すべてこの曲のための書き下ろし）
# (拍, 長さ[拍], 音)
MEL_A = [  # 主題 A：F | C/E | Dm | Bb | F/A | Bb | C | C
    [(0, .5, 'C5'), (.5, .5, 'D5'), (1, 1, 'F5'), (2, .5, 'E5'), (2.5, .5, 'F5'), (3, 1, 'G5')],
    [(0, 1.5, 'E5'), (1.5, .5, 'D5'), (2, 1, 'C5'), (3, 1, 'G4')],
    [(0, .5, 'A4'), (.5, .5, 'D5'), (1, 1, 'F5'), (2, .5, 'E5'), (2.5, .5, 'D5'), (3, 1, 'A5')],
    [(0, 1.5, 'G5'), (1.5, .5, 'F5'), (2, 2, 'D5')],
    [(0, .5, 'C5'), (.5, .5, 'F5'), (1, 1, 'A5'), (2, .5, 'G5'), (2.5, .5, 'F5'), (3, 1, 'C6')],
    [(0, 1, 'Bb5'), (1, .5, 'A5'), (1.5, .5, 'G5'), (2, 1, 'F5'), (3, 1, 'D5')],
    [(0, .5, 'E5'), (.5, .5, 'F5'), (1, 1, 'G5'), (2, .5, 'C5'), (2.5, .5, 'D5'), (3, 1, 'E5')],
    [(0, 1, 'E5'), (1, .5, 'D5'), (1.5, .5, 'E5'), (2, 2, 'G5')],
]
MEL_B = [  # 主題 B：Bb | C | Am | Dm | Gm | C | F | F
    [(0, .5, 'D5'), (.5, .5, 'F5'), (1, 1, 'Bb5'), (2, .5, 'A5'), (2.5, .5, 'G5'), (3, 1, 'F5')],
    [(0, .5, 'E5'), (.5, .5, 'G5'), (1, 1, 'C6'), (2, .5, 'Bb5'), (2.5, .5, 'G5'), (3, 1, 'E5')],
    [(0, 1.5, 'A5'), (1.5, .5, 'G5'), (2, 1, 'E5'), (3, 1, 'C5')],
    [(0, .5, 'D5'), (.5, .5, 'E5'), (1, 1, 'F5'), (2, 1, 'A5'), (3, 1, 'F5')],
    [(0, .5, 'G5'), (.5, .5, 'A5'), (1, 1, 'Bb5'), (2, 1, 'G5'), (3, 1, 'D5')],
    [(0, .5, 'E5'), (.5, .5, 'F5'), (1, 1, 'G5'), (2, 1, 'Bb5'), (3, .5, 'A5'), (3.5, .5, 'G5')],
    [(0, 1.5, 'A5'), (1.5, .5, 'G5'), (2, 1, 'F5'), (3, 1, 'C5')],
    [(0, 2, 'F5')],
]
MEL_T = [  # つなぎ：Bb | C | Dm | C
    [(0, 1, 'D5'), (1, .5, 'C5'), (1.5, .5, 'D5'), (2, 2, 'F5')],
    [(0, 1, 'E5'), (1, .5, 'D5'), (1.5, .5, 'E5'), (2, 2, 'G5')],
    [(0, 1, 'F5'), (1, .5, 'E5'), (1.5, .5, 'D5'), (2, 2, 'A4')],
    [(0, 1, 'G4'), (1, .5, 'A4'), (1.5, .5, 'Bb4'), (2, 1, 'C5'), (3, 1, 'E5')],
]
MEL_BR = [  # 峠を渡る：F | Dm | Bb | C | C(駆け上がりは別)
    [(0, 1, 'A4'), (1, 1, 'C5'), (2, 1.5, 'F5'), (3.5, .5, 'E5')],
    [(0, 1, 'D5'), (1, 1, 'F5'), (2, 2, 'A5')],
    [(0, 1, 'G5'), (1, .5, 'F5'), (1.5, .5, 'D5'), (2, 1, 'Bb4'), (3, 1, 'D5')],
    [(0, 1, 'C5'), (1, 1, 'E5'), (2, 2, 'G5')],
    [(0, 1, 'E5'), (1, .5, 'F5'), (1.5, .5, 'G5')],
]
MEL_R = [  # 救助：Dm | Bb | F | C | Dm | Bb | Gm | C  （1 小節目は 1 拍休んでから）
    [(1, .5, 'A4'), (1.5, .5, 'G4'), (2, 1, 'A4'), (3, 1, 'D5')],
    [(0, 1.5, 'D5'), (1.5, .5, 'C5'), (2, 1, 'D5'), (3, 1, 'F5')],
    [(0, 1.5, 'F5'), (1.5, .5, 'E5'), (2, 1, 'F5'), (3, 1, 'A5')],
    [(0, 2, 'G5'), (2, 1, 'E5'), (3, 1, 'C5')],
    [(0, 1.5, 'D5'), (1.5, .5, 'E5'), (2, 1, 'F5'), (3, 1, 'A5')],
    [(0, 1.5, 'Bb5'), (1.5, .5, 'A5'), (2, 1, 'G5'), (3, 1, 'F5')],
    [(0, 1.5, 'G5'), (1.5, .5, 'A5'), (2, 1, 'Bb5'), (3, .5, 'A5'), (3.5, .5, 'Bb5')],
    [(0, 2, 'C6'), (2, 1, 'Bb5'), (3, 1, 'G5')],
]
MEL_W = [  # 天面を歩く：F | Bb | Gm7 | (C7 の駆け上がりは別)
    [(0, .5, 'C5'), (.5, .5, 'D5'), (1, 1, 'F5'), (2, .5, 'E5'), (2.5, .5, 'F5'), (3, 1, 'G5')],
    [(0, .5, 'D5'), (.5, .5, 'F5'), (1, 1, 'Bb5'), (2, .5, 'A5'), (2.5, .5, 'G5'), (3, 1, 'F5')],
    [(0, 1, 'D5'), (1, .5, 'F5'), (1.5, .5, 'G5'), (2, 1, 'Bb5'), (3, .5, 'A5'), (3.5, .5, 'G5')],
]
# 万歳：主題 A を G major へ（+2）、8 小節目だけ終止へ向けて書き換え
MEL_DANCE = [[(bb, du, m(n) + 2) for bb, du, n in bar] for bar in MEL_A[:7]] + [
    [(0, 1, 'F#5'), (1, .5, 'E5'), (1.5, .5, 'F#5'), (2, 1, 'A5'),
     (3, .25, 'C6'), (3.25, .25, 'B5'), (3.5, .25, 'A5'), (3.75, .25, 'F#5')],
]


# ---------------------------------------------------------------- 作曲本体
def build():
    # ===== 0 自己紹介 0.0–15.1（v3 で追加）：約 119 BPM、2 拍の弱起＋7 小節。30 拍目が施工の頭（F） =====
    # 拍 -> 秒：0.503 s。はじめまして（0.3 s〜）・講座の最終課題の説明（2.7 s〜）・仲間の紹介（7.2 s〜、カード 7.6／8.9／10.2 s）・
    # わたしの仕事（11.6 s〜）・暗転（14.5–15.1 s）。カードのチャイムは C6・E6・C7 なので、その小節は C と Am。
    t0 = TM([(0, 0.0), (30, INTRO)], warp=False)
    prog0 = [(0, 'F'), (6, 'Dm'), (10, 'Bb'), (14, 'C'), (18, 'Am'), (22, 'Bb'), (26, 'C'), (28, 'C7')]
    for i, n in enumerate(['C4', 'F4', 'A4', 'C5']):                  # 「はじめまして」：上行の 4 音
        mar(t0(0.1 + 0.5 * i), n, 0.34 + 0.04 * i, pan=-0.2 + 0.13 * i, dec=1.0)
    vibe(t0(2), ['F4', 'A4', 'C5'], 0.24, dur=2.2)
    pads(t0, prog0, 0, 30, vel=lambda b: 0.24 + 0.1 * b / 30, att=1.0, rel=1.0)
    ostinato(t0, prog0, 2, 30, sub=2, pattern=OST8, vel=lambda b: 0.24 + 0.14 * (b - 2) / 28, pan=-0.28, dec=0.5)
    bassline(t0, prog0, 6, 28, PAT_B, vel=lambda b: 0.5 + 0.2 * (b - 6) / 22, dec=0.6)
    shaker(t0, 14, 30, sub=2, vel=lambda b: 0.16 + 0.14 * (b - 14) / 16)
    for b in (14, 18, 22, 26):
        kick(t0(b), 0.2)
    for b in (14, 18):                                                  # 紹介のカードの小節：ヴィブラフォンを高めに
        vibe(t0(b), [n + 12 for n in CH[chord_at(prog0, b)]['mid']], 0.18, dur=1.6)
    bas(t0(28), 'C2', 0.5, dec=0.5)                                     # 施工へのピックアップ
    bas(t0(29), 'E2', 0.5, dec=0.45)
    bas(t0(29.5), 'G2', 0.52, dec=0.45)

    # ===== A 0.0–44.1 施工（4 倍速）：120 BPM, 22 小節 =====
    tA = TM([(0, 0.0), (88, 44.1)])
    symsA = ['F', 'F',
             'F', 'C/E', 'Dm', 'Bb', 'F/A', 'Bb', 'C', 'C',
             'Bb', 'C', 'Am', 'Dm', 'Gm', 'C', 'F', 'F',
             'Bb', 'C', 'Dm', 'C']
    progA = [(4 * i, s) for i, s in enumerate(symsA)]

    def vA(b):
        if b < 8:
            return 0.62
        if b < 72:
            return 0.46
        if b < 84:
            return 0.52
        return 0.52 - 0.14 * (b - 84) / 4.0
    ostinato(tA, progA, 0, 88, sub=4, vel=vA, pan=-0.28, dec=0.42)
    shaker(tA, 4, 88, sub=4, vel=lambda b: 0.5 if b < 84 else 0.5 - 0.2 * (b - 84) / 4)
    bassline(tA, progA, 8, 88, PAT_A, vel=0.95, dec=0.7)
    for b in range(8, 72, 2):
        kick(tA(b), 0.36 if b % 4 == 0 else 0.26)
    melody(tA, 8, MEL_A, vel=0.9, pan=0.1)
    melody(tA, 40, MEL_B, vel=0.88, pan=0.1)
    melody(tA, 72, MEL_T, vel=0.62, pan=0.15)
    offchords(tA, progA, 40, 72, vel=0.34)
    pads(tA, progA, 40, 88, vel=0.3, att=0.6, rel=1.0)

    # ===== B 44.1–54.0 BZ が渡り切る・パッカン追う：5 小節 =====
    tB = TM([(0, 44.1), (20, 54.0)])
    progB = [(0, 'F'), (4, 'Dm'), (8, 'Bb'), (12, 'C'), (16, 'C')]
    ostinato(tB, progB, 0, 18, sub=2, pattern=OST8, vel=lambda b: 0.55 if b < 16 else 0.45, pan=-0.28, dec=0.5)
    bassline(tB, progB, 0, 18, PAT_B, vel=0.85, dec=0.65)
    shaker(tB, 0, 20, sub=2, vel=0.45)
    for b in range(0, 18, 2):
        kick(tB(b), 0.28)
    melody(tB, 0, MEL_BR, vel=0.85)
    for i, n in enumerate(['C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'Bb5', 'C6']):
        mar(tB(18 + 0.25 * i), n, 0.48 + 0.04 * i, pan=0.1, dec=0.6)
    pads(tB, progB, 0, 20, vel=0.28, att=0.6, rel=1.0)
    # 54.0 星 1
    star(W(54.0), ['F5', 'A5', 'C6', 'F6'], ['F4', 'A4', 'C5'], 'F2', vel=0.8, vdur=3.0)

    # ===== C 54.0–70.3 パッカン挑戦・跳跳の応援：約 80 BPM =====
    tC = TM([(0, 54.0), (8, 60.2), (11, 62.4), (15, 65.4), (19, 68.2), (22, 70.3)])
    progC = [(0, 'F'), (4, 'Dm'), (8, 'Gm'), (11, 'Bb'), (13, 'C'), (15, 'Bbm'), (19, 'Fadd9')]
    pads(tC, progC, 0.3, 22.4, vel=0.5, att=1.0, rel=1.0, ov=0.3)
    for b, sym in progC[1:]:
        for i, n in enumerate(CH[sym]['mid']):
            mar(tC(b) + 0.055 * i, n, 0.4 - 0.03 * i, pan=0.25, dec=1.1)
    motif = [(4, 'D4', .62), (4.5, 'E4', .58), (5, 'F4', .62), (5.5, 'G4', .66), (6, 'A4', .72),     # 1 回目の挑戦
             (8, 'G4', .6), (8.5, 'F4', .52), (9, 'D4', .5), (10.5, 'E4', .36),                  # 60.2 後ずさり
             (11, 'F4', .6), (11.5, 'G4', .62), (12, 'A4', .66), (12.5, 'Bb4', .7), (13, 'C5', .76),  # 62.4 もう一度
             (15, 'Db5', .6), (15.5, 'C5', .54), (16, 'Bb4', .52), (17, 'F4', .46),              # 65.4 登れない
             (19.5, 'A4', .34), (20.5, 'G4', .3)]                                               # 68.2 座り込む
    for b, n, v in motif:
        mar(tC(b), n, v, pan=0.05, dec=1.25)
    # 跳跳の応援（跳ねるピチカート）
    for lo, hi, step, v in ((1, 8, 0.5, 0.36), (8, 11, 1.0, 0.26), (11, 15, 0.5, 0.36), (15, 19, 1.0, 0.24)):
        k = 0
        b = lo
        while b < hi - 1e-9:
            ch = CH[chord_at(progC, b)]
            bas(tC(b), ch['b8'] if k % 2 else ch['b'], v * (0.85 if k % 2 else 1.0), dec=0.35)
            k += 1
            b = lo + k * step
    # v2：坂の場面は高い音が少ないのでシェイカーが浮く -> 約 -7 dB（0.3 -> 0.13）
    shaker(tC, 1, 8, sub=2, vel=0.13)
    shaker(tC, 11, 15, sub=2, vel=0.13)
    bas(tC(19), 'F2', 0.5, dec=1.4)
    mar(tC(19), 'F3', 0.38, pan=-0.1, dec=1.3)
    vibe(tC(19), ['A4', 'C5', 'G5'], 0.32, dur=2.0)
    bas(tC(21), 'F2', 0.38, dec=0.4)
    bas(tC(21.5), 'A2', 0.44, dec=0.4)

    # ===== D 70.3–78.9 跳跳が登る・75.4 ジャンプ =====
    tD = TM([(0, 70.3), (10, 75.4), (17, 78.9)])
    progD = [(0, 'Bb'), (2, 'C'), (4, 'Dm'), (6, 'Eb'), (8, 'C/E'), (10, 'F'), (12, 'Bb'), (14, 'C7'), (17, 'F')]
    bases = ['Bb3', 'C4', 'D4', 'Eb4', 'E4']
    for k in range(5):
        sym = progD[k][1]
        pcs = set(n % 12 for n in CH[sym]['osti'])
        tones = tones_from(bases[k], pcs, 5)
        seq = tones[0:4] + tones[1:5]
        for i in range(8 if k < 4 else 6):
            b = 2 * k + 0.25 * i
            mar(tD(b), seq[i], (0.42 + 0.36 * b / 10.0) * (1.0 if i % 4 == 0 else 0.84), pan=-0.15 + 0.06 * k, dec=0.5)
        ch = CH[sym]
        bas(tD(2 * k), ch['b'], 0.7 + 0.05 * k, dec=0.7)
        bas(tD(2 * k + 1), ch['b'], 0.5, dec=0.5)
        bas(tD(2 * k + 1.5), ch['b8'], 0.45, dec=0.4)
    for i, n in enumerate(['C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'Bb5', 'C6']):
        mar(tD(9.5 + 0.0625 * i), n, 0.45 + 0.045 * i, pan=0.1, dec=0.45, jit=0.002)
    kick(tD(0), 0.3)        # v2：70.3 の「登り始め」に柔らかい一打
    kick(tD(2), 0.22)
    for b in range(4, 10):
        kick(tD(b), 0.22 + 0.035 * (b - 4))
    shaker(tD, 2, 10, sub=4, vel=lambda b: 0.25 + 0.35 * (b - 2) / 8)
    pads(tD, progD[:5], 0, 10, vel=lambda b: 0.38 + 0.02 * b, att=0.4, rel=0.6)
    # 75.4 ジャンプ
    T = tD(10)
    roll_chord(T, ['F3', 'C4', 'F4', 'A4', 'C5', 'F5'], 0.6, spread=0.018, dec=1.6)
    chime(T + 0.03, 'C6', 0.52, pan=-0.3)
    chime(T + 0.08, 'F6', 0.48, pan=0.3)
    vibe(T, ['A4', 'C5', 'F5'], 0.42, dur=1.2)
    bas(T, 'F2', 0.8, dec=1.3)
    kick(T, 0.4)
    # 天面を跳ねる旋律
    melD = [(10, 'A5', .85), (11, 'G5', .78), (11.5, 'F5', .74),
            (12, 'D5', .78), (12.5, 'F5', .74), (13, 'Bb5', .82),
            (14, 'A5', .78), (14.5, 'G5', .74), (15, 'E5', .76), (15.5, 'G5', .74),
            (16, 'G5', .76), (16.5, 'E5', .72)]
    for b, n, v in melD:
        mar(tD(b), n, v, pan=0.1, dec=1.0)
    ostinato(tD, progD, 11, 17, sub=2, pattern=OST8, vel=0.45, pan=-0.28, dec=0.5)
    for b in np.arange(11, 17, 1.0):
        ch = CH[chord_at(progD, b)]
        bas(tD(b), ch['b'] if int(b) % 2 == 0 else ch['b2'], 0.65, dec=0.55)
        bas(tD(b + 0.5), ch['b8'], 0.42, dec=0.35)
    for b in (12, 14, 16):
        kick(tD(b), 0.36)
    shaker(tD, 10.5, 17, sub=4, vel=0.5)
    pads(tD, progD[5:], 10, 17, vel=0.5, att=0.3, rel=0.8)
    # 78.9 星 2
    star(W(78.9), ['A5', 'C6', 'F6'], ['F4', 'A4', 'C5'], 'F2', vel=0.8, vdur=3.0)
    mar(W(78.9), 'F5', 0.78, pan=0.1, dec=1.4)

    # ===== E 呼ぶ・跳跳が戻る：v3 では 4 倍速で 5.37 s（take 51 の 9.3 s）。16 拍 -> 10 拍（約 112 BPM） =====
    # 呼び声 C–A とこだま（パッカンが呼ぶ 80.4 s の少し前）、戻り（RETURN 81.6 s）から歩くベースで救助の Dm へ。
    tE = TM([(0, W(78.9)), (10, W(88.2))], warp=False)
    progE = [(0, 'F'), (2, 'Dm7'), (5, 'Bbmaj7'), (8, 'C7')]
    pads(tE, progE, 0.5, 10.3, vel=0.42, att=1.0, rel=1.0, ov=0.3)
    calls = [(2, 'C5', .58, -.3), (2.5, 'A4', .54, -.3), (3.5, 'C5', .36, .35), (4, 'A4', .32, .35)]
    for b, n, v, p in calls:
        mar(tE(b), n, v, pan=p, dec=1.2)
    walk = [(5, 'Bb1'), (6, 'D2'), (7, 'F2'), (7.5, 'A2'), (8, 'C2'), (8.5, 'E2'), (9, 'G2'), (9.5, 'Bb2')]
    for b, n in walk:
        bas(tE(b), n, 0.55, dec=0.55)
    for k, b in enumerate(np.arange(5, 10, 0.5)):
        mid = CH[chord_at(progE, b)]['mid']
        mar(tE(b), mid[[0, 1, 2, 1][k % 4]] + 12, 0.28 + 0.1 * (b - 5) / 5, pan=0.3, dec=0.6)
    vibe(tE(5), ['A4', 'D5', 'F5'], 0.3, dur=tE(8) - tE(5))
    vibe(tE(8), ['G4', 'Bb4', 'E5'], 0.32, dur=tE(10) - tE(8))
    shaker(tE, 8, 10, sub=2, vel=lambda b: 0.18 + 0.15 * (b - 8) / 2)

    # ===== F 88.2–133.5 救助 =====
    tF = TM([(0, 88.2), (12, 94.2), (24, 100.9), (40, 109.9), (76, 129.8)])
    progF = [(0, 'Dm'), (4, 'Bb'), (8, 'C'),
             (12, 'Dm'), (16, 'Bb'), (20, 'C'),
             (24, 'Dm'), (28, 'Bb'), (32, 'F'), (36, 'C'),
             (40, 'Dm'), (44, 'Bb'), (48, 'F'), (52, 'C'), (56, 'Dm'), (60, 'Bb'), (64, 'Gm'), (68, 'C'),
             (72, 'Csus4'), (74, 'C')]

    def paused(b):
        return (24 - 1e-9 <= b < 25 - 1e-9) or (40 - 1e-9 <= b < 41 - 1e-9)

    # 88.2 座らせる：支配人 AI が考える 8 分の動機
    THINK = {'Dm': ['A4', 'D5', 'A4', 'E5', 'A4', 'F5', 'A4', 'E5'],
             'Bb': ['F4', 'Bb4', 'F4', 'C5', 'F4', 'D5', 'F4', 'C5'],
             'C': ['G4', 'C5', 'G4', 'D5', 'G4', 'E5', 'G4', 'D5']}
    for b in np.arange(0, 24, 0.5):
        seq = THINK[chord_at(progF, b)]
        i = int(round((b % 4) * 2))
        v = (0.46 if i % 2 else 0.36) * (1.0 if b < 12 else 0.75)
        mar(tF(b), seq[i], v, pan=-0.2, dec=0.65)
    vibe(tF(0), ['A4', 'D5', 'F5'], 0.3, dur=2.5)
    bas(tF(0), 'D2', 0.55, dec=1.4)
    mar(tF(0), 'D3', 0.42, pan=-0.1, dec=1.2)
    pads(tF, progF[:-2], 0, 72, vel=lambda b: 0.38 + 0.24 * max(0.0, b - 12) / 60, att=0.8, rel=1.0)
    pads(tF, progF[-2:], 72, 76, vel=0.62, att=0.5, rel=0.8)
    # 94.2 押し上げ開始：層 1 ベースの踏ん張り＋キック
    bassline(tF, progF, 12, 72, PAT_H, vel=lambda b: 0.8 + 0.2 * (b - 12) / 60, dec=0.7, skip=paused)
    for i, b in enumerate(np.arange(72, 76, 0.5)):
        bas(tF(b), 'C2', 0.55 + 0.05 * i, dec=0.5)
    for b in np.arange(12, 76, 1.0):
        if paused(b):
            continue
        if b < 64:
            if b % 2 == 0:
                kick(tF(b), 0.34 + 0.1 * (b - 12) / 52)
        else:
            kick(tF(b), 0.42 + 0.08 * (b - 64) / 12)
    kick(tF(75.5), 0.4)
    # 100.9 / 109.9 の一瞬の停止から「よいしょ」と再開
    for b, v in ((25, 0.8), (41, 0.85)):
        bas(tF(b), 'D2', v, dec=0.6)
        kick(tF(b), 0.42)
    # 層 2：裏拍の和音（100.9 から）
    offchords(tF, progF, 24, 72, vel=lambda b: 0.3 + 0.12 * (b - 24) / 48, skip=paused)
    # 層 3：シェイカー＋救助の旋律（109.9 から）
    shaker(tF, 41, 76, sub=4, vel=lambda b: 0.32 + 0.36 * (b - 41) / 35)
    melody(tF, 40, MEL_R, vel=lambda b: 0.72 + 0.16 * (b - 40) / 32, pan=0.1)
    # 汗の力仕事：16 分の刻み（~118 s から）
    ostinato(tF, progF, 56, 72, sub=4, vel=lambda b: 0.3 + 0.16 * (b - 56) / 16, pan=-0.3, dec=0.4)
    # 最後のひと押し：Csus4→C のロール
    roll(tF(72), tF(74), ['G4', 'C5', 'F5'], 0.3, 0.55)
    roll(tF(74), tF(76) - 0.04, ['G4', 'C5', 'E5'], 0.55, 0.75)
    # 129.8 押し上げ成功（ほっ）
    T = W(129.8)
    roll_chord(T, ['F3', 'C4', 'F4', 'A4', 'C5'], 0.72, spread=0.03, dec=1.6)
    roll(T + 0.15, T + 1.3, ['A4', 'C5', 'F5'], 0.4, 0.12, rate=12, dec=0.8)
    chime(T + 0.05, 'A5', 0.5, pan=-0.3)
    chime(T + 0.12, 'C6', 0.48, pan=0.0)
    chime(T + 0.2, 'F6', 0.45, pan=0.3)
    vibe(T, ['F4', 'A4', 'C5'], 0.4, dur=2.8)
    bas(T, 'F2', 0.8, dec=1.6)
    kick(T, 0.32)
    pad(T, 2.6, CH['F']['pad'], 0.55, att=0.25, rel=1.5)
    # 130.7 立たせる
    for i, n in enumerate(['C4', 'F4', 'A4', 'C5', 'F5']):
        mar(W(130.7) + 0.12 * i, n, 0.5 + 0.04 * i, pan=-0.3 + 0.15 * i, dec=1.0)
    # 133.5「そのまま進んで」へのピックアップ
    pad(W(132.0), 1.6, CH['C7']['pad'], 0.4, att=0.6, rel=0.6)
    bas(W(133.0), 'C2', 0.45, dec=0.5)
    bas(W(133.25), 'E2', 0.5, dec=0.5)

    # ===== G 133.5–140.6 天面を歩いて下る =====
    if W(140.6) - W(133.5) > 6.6:           # 固定ルールの本編（7.1 s）：14 拍
        tG = TM([(0, 133.5), (14, 140.6)])
        progG = [(0, 'F'), (4, 'Bb'), (8, 'Gm7'), (12, 'C7')]
        walkG = ['F2', 'A2', 'C3', 'A2', 'Bb1', 'D2', 'F2', 'D2', 'G2', 'A2', 'Bb2', 'B2', 'C3', 'Bb2']
        for i, n in enumerate(walkG):
            bas(tG(i), n, 0.7 + 0.015 * i, dec=0.55)
        melody(tG, 0, MEL_W, vel=0.82)
        for i, n in enumerate(['G4', 'A4', 'Bb4', 'C5', 'D5', 'E5', 'F5', 'G5']):
            mar(tG(12 + 0.25 * i), n, 0.5 + 0.045 * i, pan=0.1, dec=0.5)
        ostinato(tG, progG, 0, 12, sub=2, pattern=OST8, vel=lambda b: 0.4 + 0.15 * b / 12, pan=-0.28, dec=0.5)
        shaker(tG, 0, 8, sub=2, vel=0.45)
        shaker(tG, 8, 14, sub=4, vel=lambda b: 0.45 + 0.25 * (b - 8) / 6)
        for b, v in ((0, .35), (2, .35), (4, .35), (6, .35), (8, .38), (10, .38), (12, .45), (13, .45), (13.5, .4)):
            kick(tG(b), v)
        pads(tG, progG, 0, 14, vel=0.48, att=0.5, rel=0.8)
    else:                                    # PPO の本編（6.1 s）：12 拍にして同じ約 118 BPM を保つ
        tG = TM([(0, 133.5), (12, 140.6)])
        progG = [(0, 'F'), (4, 'Bb'), (8, 'Gm7'), (10, 'C7')]
        walkG = ['F2', 'A2', 'C3', 'A2', 'Bb1', 'D2', 'F2', 'D2', 'G2', 'Bb2', 'C3', 'Bb2']
        for i, n in enumerate(walkG):
            bas(tG(i), n, 0.7 + 0.018 * i, dec=0.55)
        melody(tG, 0, MEL_W[:2] + [[x for x in MEL_W[2] if x[0] < 2]], vel=0.82)
        for i, n in enumerate(['G4', 'A4', 'Bb4', 'C5', 'D5', 'E5', 'F5', 'G5']):
            mar(tG(10 + 0.25 * i), n, 0.5 + 0.045 * i, pan=0.1, dec=0.5)
        ostinato(tG, progG, 0, 10, sub=2, pattern=OST8, vel=lambda b: 0.4 + 0.15 * b / 10, pan=-0.28, dec=0.5)
        shaker(tG, 0, 6, sub=2, vel=0.45)
        shaker(tG, 6, 12, sub=4, vel=lambda b: 0.45 + 0.25 * (b - 6) / 6)
        for b, v in ((0, .35), (2, .35), (4, .35), (6, .38), (8, .38), (10, .45), (11, .45), (11.5, .4)):
            kick(tG(b), v)
        pads(tG, progG, 0, 12, vel=0.48, att=0.5, rel=0.8)

    # ===== H 3 体渡り切り（最大の山場）-> 集合：v3 では 4 倍速で 4.26 s（take 51 の 8.5 s）。17 拍 -> 8.5 拍（約 120 BPM） =====
    tH = TM([(0, W(140.6)), (8.5, W(149.1))], warp=False)
    progH = [(0, 'F'), (3, 'Am7'), (5, 'D7sus4'), (6, 'D7')]
    T = W(140.6)
    roll_chord(T, ['C3', 'F3', 'A3', 'C4', 'F4', 'A4', 'C5'], 0.62, spread=0.016, dec=1.8)
    mar(T, 'A5', 0.9, pan=0.1, dec=1.4)
    sparkle = ['F5', 'A5', 'C6', 'F6', 'A6', 'F6', 'C6', 'A5', 'C6', 'F6']
    for i, n in enumerate(sparkle):
        chime(T + 0.06 + 0.11 * i, n, 0.55 - 0.025 * i, pan=(-0.5 if i % 2 else 0.5))
    vibe(T, ['F4', 'A4', 'C5', 'F5'], 0.5, dur=2.6)
    bas(T, 'F2', 0.85, dec=1.8)
    kick(T, 0.42)
    pad(T, tH(3) - T + 0.2, CH['F']['pad'], 0.62, att=0.2, rel=1.0)
    pads(tH, progH[1:], 3, 8.5, vel=lambda b: 0.5 + 0.08 * (b - 3) / 5.5, att=0.5, rel=0.6, ov=0.05)
    for k, b in enumerate(np.arange(1, 5, 0.5)):                       # 余韻：柔らかい分散
        mid = CH[chord_at(progH, b)]['mid']
        mar(tH(b), mid[[0, 1, 2, 1][k % 4]] + 12, 0.3 if b < 3 else 0.34, pan=-0.2, dec=0.8)
    bas(tH(3), 'A1', 0.65, dec=1.0)
    bas(tH(4), 'A1', 0.55, dec=0.8)
    bas(tH(4.5), 'E2', 0.45, dec=0.6)
    shaker(tH, 4, 8, sub=4, vel=lambda b: 0.2 + 0.35 * (b - 4) / 4)
    for i, b in enumerate(np.arange(5, 7.5, 0.5)):                     # 期待：D7sus4 -> D7 を 8 分で高める
        for j, n in enumerate(CH[chord_at(progH, b)]['mid']):
            mar(tH(b) + 0.006 * j, n, 0.34 + 0.05 * i, pan=0.25, dec=0.4)
        bas(tH(b), 'D2', 0.45 + 0.05 * i, dec=0.45)
    for b, v in ((6, .35), (6.5, .38), (7, .42)):
        kick(tH(b), v)
    for i, n in enumerate(['G4', 'A4', 'B4', 'C5']):                   # 万歳へのピックアップ
        mar(tH(7.5 + 0.25 * i), n, 0.6 + 0.06 * i, pan=0.1, dec=0.5)

    # ===== I 149.1–164.5 輪になって万歳（等速）：G major, 8 小節 =====
    tI = TM([(0, 149.1), (32, 164.5)])
    progI = [(0, 'G'), (4, 'D/F#'), (8, 'Em'), (12, 'C'), (16, 'G/B'), (20, 'C'), (24, 'D'), (28, 'D7')]
    melody(tI, 0, MEL_DANCE, vel=0.9, pan=0.1, dec=1.0)
    melody(tI, 0, MEL_DANCE, vel=0.4, pan=-0.15, dec=0.8, tr=-12)
    ostinato(tI, progI, 0, 32, sub=4, vel=0.38, pan=-0.3, dec=0.4)
    offchords(tI, progI, 0, 32, vel=0.36)
    bassline(tI, progI, 0, 32, PAT_D, vel=0.95, dec=0.6)
    shaker(tI, 0, 32, sub=4, vel=0.6)
    for b in range(0, 32, 2):
        kick(tI(b), 0.42)
    pads(tI, progI, 0, 32, vel=0.42, att=0.4, rel=0.6)
    for b in range(0, 32, 4):
        vibe(tI(b), [n + 12 for n in CH[chord_at(progI, b)]['mid']], 0.24, dur=0.9)
    # 164.5 締めの G
    T = W(164.5)
    roll_chord(T, ['D3', 'G3', 'B3', 'D4', 'G4'], 0.62, spread=0.02, dec=1.8)
    mar(T, 'G5', 0.75, pan=0.1, dec=1.5)
    chime(T + 0.04, 'G5', 0.5, pan=-0.3)
    chime(T + 0.09, 'B5', 0.48, pan=0.0)
    chime(T + 0.14, 'D6', 0.46, pan=0.3)
    vibe(T, ['G4', 'B4', 'D5'], 0.45, dur=2.2)
    bas(T, 'G2', 0.8, dec=1.5)
    kick(T, 0.38)
    pad(T, 0.8, CH['G']['pad'], 0.5, att=0.15, rel=1.3)


# ---------------------------------------------------------------- 楽器の合成
_cache = {}


def _att(y, sec):
    n = min(len(y), max(2, int(sec * SR)))
    y[:n] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)


def _tail(y, sec=0.012):
    n = min(len(y), int(sec * SR))
    y[-n:] *= np.linspace(1.0, 0.0, n)


def w_mar(midi, bright, dec):
    key = ('mar', midi, bright, dec)
    y = _cache.get(key)
    if y is not None:
        return y
    f = hz(midi)
    T = float(np.clip(1.5 * (262.0 / f) ** 0.6, 0.22, 3.0)) * dec
    L = int(SR * T * 1.02) + 64
    t = np.arange(L) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-K60 * t / T)
    y += 0.16 * np.sin(2 * np.pi * f * 1.0021 * t + 0.7) * np.exp(-K60 * t / (0.85 * T))   # 共鳴管のうなり
    for r, a, tf in ((3.97, 0.11, 0.22), (9.6, 0.025, 0.07)):
        fr = f * r
        if fr > 11000.0:
            continue
        g = a * bright * (0.5 if 1800.0 < fr < 5500.0 else 1.0)
        y += g * np.sin(2 * np.pi * fr * t + 0.3) * np.exp(-K60 * t / (T * tf))
    _att(y, 0.004)
    _tail(y)
    y /= np.max(np.abs(y))
    _cache[key] = y
    return y


def w_bass(midi, dec):
    key = ('bass', midi, dec)
    y = _cache.get(key)
    if y is not None:
        return y
    f = hz(midi)
    T0 = 1.1 * dec
    L = int(SR * T0 * 1.02) + 64
    t = np.arange(L) / SR
    ph = 2 * np.pi * f * (t + 0.015 * 0.03 * (1.0 - np.exp(-t / 0.03)))   # 撥弦の短いピッチ落ち
    y = np.zeros(L)
    for n in range(1, 9):
        fn = n * f
        if fn > 2200.0:
            break
        a = n ** -1.1 / (1.0 + (fn / 650.0) ** 2)
        y += a * np.sin(n * ph) * np.exp(-K60 * t / (T0 / (1.0 + 0.7 * (n - 1))))
    y *= 0.7 + 0.3 * np.exp(-t / 0.09)
    _att(y, 0.005)
    _tail(y)
    y /= np.max(np.abs(y))
    _cache[key] = y
    return y


def w_kick():
    y = _cache.get('kick')
    if y is not None:
        return y
    L = int(0.5 * SR)
    t = np.arange(L) / SR
    y = np.sin(2 * np.pi * (47.0 * t + 60.0 * 0.03 * (1.0 - np.exp(-t / 0.03)))) * np.exp(-t / 0.16)
    _att(y, 0.003)
    _tail(y, 0.02)
    y /= np.max(np.abs(y))
    _cache['kick'] = y
    return y


_SHN = []


def w_shk():
    if not _SHN:
        sos = signal.butter(4, [5500.0, 11000.0], btype='bandpass', fs=SR, output='sos')
        z = signal.sosfilt(sos, rng2.standard_normal(4 * SR))
        _SHN.append(z / np.std(z))
    z = _SHN[0]
    L = int(0.14 * SR)
    o = int(rng2.integers(0, len(z) - L))
    t = np.arange(L) / SR
    y = z[o:o + L] * (1.0 - np.exp(-t / 0.006)) * np.exp(-t / 0.03)
    _tail(y, 0.01)
    return y * 0.35


def w_chime(midi):
    key = ('chime', midi)
    y = _cache.get(key)
    if y is not None:
        return y
    f = hz(midi)
    T = 2.6 * (880.0 / f) ** 0.35
    L = int(SR * T) + 64
    t = np.arange(L) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-K60 * t / T)
    y += 0.05 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-K60 * t / (0.35 * T))
    y *= 1.0 + 0.04 * np.sin(2 * np.pi * 4.5 * t)
    _att(y, 0.007)
    _tail(y)
    y /= np.max(np.abs(y))
    _cache[key] = y
    return y


def w_vibe(midi, dur):
    dur = round(float(dur), 1)
    key = ('vibe', midi, dur)
    y = _cache.get(key)
    if y is not None:
        return y
    f = hz(midi)
    T = 4.0 * (440.0 / f) ** 0.4
    L = int(SR * (min(dur, T) + 0.35)) + 64
    t = np.arange(L) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-K60 * t / T)
    y += 0.04 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-K60 * t / (0.15 * T))
    y *= 1.0 - 0.25 * (0.5 - 0.5 * np.cos(2 * np.pi * 5.0 * t))     # モーターのトレモロ
    y *= np.where(t > dur, np.exp(-(t - dur) / 0.07), 1.0)          # ダンパー
    _att(y, 0.006)
    _tail(y)
    y /= np.max(np.abs(y))
    _cache[key] = y
    return y


def w_pad(midi, dur, att, rel):
    f = hz(midi)
    L = int(SR * (dur + rel)) + 64
    t = np.arange(L) / SR
    env = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / max(att, 0.02), 0.0, 1.0))
    env *= 0.5 + 0.5 * np.cos(np.pi * np.clip((t - dur) / rel, 0.0, 1.0))
    env *= 1.0 + 0.06 * np.sin(2 * np.pi * 0.17 * t + rng2.uniform(0, 2 * np.pi))
    yl = np.zeros(L)
    yr = np.zeros(L)
    for det, pl in ((-7.0, -0.7), (0.0, 0.0), (7.0, 0.7)):
        fd = f * 2.0 ** (det / 1200.0)
        v = np.zeros(L)
        for n in range(1, 7):
            if n * fd > 1500.0:
                break
            v += n ** -1.5 * np.sin(2 * np.pi * n * fd * t + rng2.uniform(0, 2 * np.pi))
        gl, gr = panlaw(pl)
        yl += gl * v
        yr += gr * v
    return yl * env, yr * env


GAIN = dict(mar=0.30, bass=0.42, kick=0.40, shk=0.20, pad=0.030, vibe=0.12, chime=0.12)


def render(diag=False):
    Lb = np.zeros(N)
    Rb = np.zeros(N)
    S = np.zeros(N)
    stems = {} if diag else None
    order = sorted(range(len(EV)), key=lambda i: (EV[i][0], EV[i][1], i))
    for i in order:
        kind, t, p = EV[i]
        i0 = int(round(t * SR))
        if i0 >= N:
            continue
        g = GAIN[kind]
        if kind == 'pad':
            yl, yr = w_pad(p['midi'], p['dur'], p['att'], p['rel'])
            n = min(len(yl), N - i0)
            a = g * p['vel']
            Lb[i0:i0 + n] += a * yl[:n]
            Rb[i0:i0 + n] += a * yr[:n]
            S[i0:i0 + n] += p['send'] * a * 0.7 * (yl[:n] + yr[:n])
            if diag:
                stems.setdefault(kind, np.zeros(N, np.float32))[i0:i0 + n] += a * 0.7 * (yl[:n] + yr[:n])
            continue
        if kind == 'mar':
            v = p['vel']
            y = w_mar(p['midi'], round(min(1.0, 0.35 + 0.65 * v), 1), round(p['dec'] * 20) / 20)
        elif kind == 'bass':
            y = w_bass(p['midi'], round(p['dec'] * 20) / 20)
        elif kind == 'kick':
            y = w_kick()
        elif kind == 'shk':
            y = w_shk()
        elif kind == 'chime':
            y = w_chime(p['midi'])
        else:
            y = w_vibe(p['midi'], p['dur'])
        n = min(len(y), N - i0)
        s = (g * p['vel']) * y[:n]
        gl, gr = panlaw(p['pan'])
        Lb[i0:i0 + n] += gl * s
        Rb[i0:i0 + n] += gr * s
        S[i0:i0 + n] += p['send'] * s
        if diag:
            stems.setdefault(kind, np.zeros(N, np.float32))[i0:i0 + n] += s
    return Lb, Rb, S, stems


# ---------------------------------------------------------------- 仕上げ
def reverb(S):
    L = int(2.3 * SR)
    t = np.arange(L) / SR
    sos = signal.butter(2, [220.0, 4200.0], btype='bandpass', fs=SR, output='sos')
    pre = int(0.02 * SR)
    out = []
    for _ in range(2):
        ir = signal.sosfilt(sos, rng2.standard_normal(L) * np.exp(-K60 * t / 1.8))
        _att(ir, 0.004)
        _tail(ir, 0.05)
        ir = np.concatenate([np.zeros(pre), ir])
        ir /= np.sqrt(np.sum(ir ** 2))
        out.append(signal.fftconvolve(S, ir)[:N])
    return out


def peq(x, f0, gdb, Q):
    A = 10.0 ** (gdb / 40.0)
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    b = np.array([1 + al * A, -2 * c, 1 - al * A])
    a = np.array([1 + al / A, -2 * c, 1 - al / A])
    return signal.lfilter(b / a[0], a / a[0], x, axis=0)


def lowshelf(x, f0, gdb):
    A = 10.0 ** (gdb / 40.0)
    w0 = 2 * np.pi * f0 / SR
    c = np.cos(w0)
    al = np.sin(w0) / 2 * np.sqrt(2.0)
    sA = 2 * np.sqrt(A) * al
    b = np.array([A * ((A + 1) - (A - 1) * c + sA), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sA)])
    a = np.array([(A + 1) + (A - 1) * c + sA, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sA])
    return signal.lfilter(b / a[0], a / a[0], x, axis=0)


def master_eq(x):
    x = signal.sosfilt(signal.butter(2, 38.0, btype='highpass', fs=SR, output='sos'), x, axis=0)
    x = lowshelf(x, 100.0, -3.0)
    x = peq(x, 2500.0, -4.0, 1.1)
    x = peq(x, 4000.0, -5.0, 1.1)
    x = signal.sosfilt(signal.butter(2, 13000.0, btype='lowpass', fs=SR, output='sos'), x, axis=0)
    return x


FADE0, FADE1 = round(W(164.5) + 0.6, 3), round(DUR - 0.4, 3)   # 最後の G を講座 ED に響かせてから消す（take 57：172.0／175.0）

# 声の「間」：ロボットの声（3body_arena_v7_take51_chirps.wav）の句の時刻表 (始, 終) [s]。
# 50 ms 窓で -50 dBFS を超える所を、0.3 s 以下の隙間はつないで句にしたもの（take51 から一度だけ書き出して固定）。
# 句の 0.06 s 前から 0.06 s かけて下げ、句の終わりから 0.3 s かけて戻す（余弦）。深さは POCKET_DB。
VOICE_PHRASES = [
    (0.00, 1.55), (2.20, 4.55), (6.15, 6.65), (7.40, 7.90), (9.30, 10.65), (11.30, 11.75), (12.40, 12.70),
    (13.50, 13.80), (14.15, 15.30), (16.80, 18.05), (19.20, 19.70), (20.65, 22.40), (23.90, 25.50), (25.90, 26.40),
    (27.30, 27.80), (28.35, 28.65), (30.00, 30.95), (32.80, 33.95), (34.35, 34.80), (36.10, 36.95), (38.00, 38.85),
    (39.85, 40.20), (41.15, 41.65), (43.40, 43.80), (44.10, 44.55), (54.10, 55.10), (56.50, 57.00), (58.40, 58.90),
    (60.00, 60.45), (61.10, 61.90), (62.40, 62.85), (67.90, 68.55), (68.95, 71.10), (73.95, 75.10), (79.40, 79.90),
    (80.75, 82.85), (88.20, 88.65), (94.15, 94.45), (129.80, 130.20), (130.70, 131.20), (133.50, 133.95),
    (140.60, 140.95), (149.05, 149.40), (150.70, 150.95), (152.30, 152.65), (153.90, 154.15), (155.50, 155.85),
    (157.10, 157.70), (158.75, 159.10), (160.35, 160.95), (161.95, 162.30), (163.55, 163.85),
]
POCKET_DB = float(os.environ.get('BGM_POCKET_DB', '0'))    # v3：音量は一定（「間」なし）   # 0 にすると「間」なし（別テイクの声に使うとき）
POCKET_PRE, POCKET_ATT, POCKET_REL = 0.06, 0.06, 0.30
# 曲が合図で「打つ」所は声と一緒に鳴らす：峠へ・ほっ・最大の山場・万歳の入りは「間」を作らない（0）、
# 44.1（峠へ）も作らない、88.2（座らせる）は半分の深さ。
POCKET_AT_CUE = {44.1: 0.0, 88.2: 0.5, 129.8: 0.0, 140.6: 0.0, 149.1: 0.0}


def voice_pocket():
    """声の句の下だけ BGM を POCKET_DB 下げる係数（1 = そのまま）。区間は余弦でつなぐのでクリックは出ない。"""
    gate = np.zeros(N)
    if POCKET_DB <= 0:
        return np.ones(N)
    for a, b in VOICE_PHRASES:
        w = min([POCKET_AT_CUE[c] for c in POCKET_AT_CUE if abs(a - c) <= 0.15] + [1.0])
        if w <= 0:
            continue
        s0 = a - POCKET_PRE - POCKET_ATT
        i0, i1 = max(0, int(s0 * SR)), min(N, int((b + POCKET_REL) * SR) + 1)
        if i1 <= i0:
            continue
        t = np.arange(i0, i1) / SR
        up = 0.5 - 0.5 * np.cos(np.pi * np.clip((t - s0) / POCKET_ATT, 0.0, 1.0))
        dn = 0.5 - 0.5 * np.cos(np.pi * np.clip(1.0 - (t - b) / POCKET_REL, 0.0, 1.0))
        np.maximum(gate[i0:i1], w * np.minimum(up, dn), out=gate[i0:i1])
    return 10.0 ** (-POCKET_DB * gate / 20.0)


def automation():
    # 場面ごとの強弱 [dB]。v2：声の多い施工は -2.5、万歳は -0.5（それでも最も大きい区間のまま）、
    # 声のほとんど無い押し上げの前半〜中盤は +1.2。44.1 / 70.3 / 94.2 / 149.1 は段を付けて場面の変わり目をはっきり。
    pts = [(0.0, -14.5), (0.25, 0.0), (DUR, 0.0)]            # v3：音量は一定（頭の 0.25 s のフェードインだけ）
    tt = np.arange(N) / SR
    g = 10.0 ** (np.interp(tt, [p[0] for p in pts], [p[1] for p in pts]) / 20.0)
    g *= voice_pocket()
    u = np.clip((tt - FADE0) / (FADE1 - FADE0), 0.0, 1.0)
    g *= 0.5 + 0.5 * np.cos(np.pi * u)
    g[tt >= FADE1] = 0.0
    return g


def rms_db(x):
    return 10.0 * np.log10(np.mean(np.asarray(x, np.float64) ** 2) + 1e-30)


def limiter(x, ceil):
    a = np.max(np.abs(x), axis=1)
    w = int(0.008 * SR)
    need = np.minimum(1.0, ceil / np.maximum(a, 1e-12))
    g = minimum_filter1d(need, size=4 * w + 1)
    g = uniform_filter1d(g, size=2 * w + 1)
    return x * g[:, None]


SECTIONS = [(0.0, INTRO, '自己紹介'), (W(0.0), W(44.1), '施工'), (W(44.1), W(54.0), 'BZ渡り'), (W(54.0), W(70.3), '挑戦'),
            (W(70.3), W(78.9), '跳跳登る'), (W(78.9), W(88.2), '呼ぶ'), (W(88.2), W(94.2), '座らせる'), (W(94.2), W(129.8), '押し上げ'),
            (W(129.8), W(133.5), '成功'), (W(133.5), W(140.6), '下る'), (W(140.6), W(149.1), '集合'), (W(149.1), W(164.5), '万歳'),
            (W(164.5), DUR, '終わり')]


def main():
    t0 = time.time()
    diag = os.environ.get('BGM_DIAG') == '1'
    build()
    print(f"events: {len(EV)}")
    Lb, Rb, S, stems = render(diag)
    print(f"render: {time.time() - t0:.1f} s")
    wl, wr = reverb(S)
    WET = 0.55
    x = np.stack([Lb + WET * wl, Rb + WET * wr], axis=1)
    del Lb, Rb, S, wl, wr
    x = master_eq(x)
    x *= automation()[:, None]
    ceil = 10.0 ** (-1.3 / 20.0)
    x *= 10.0 ** ((-20.0 - rms_db(x)) / 20.0)
    a = np.max(np.abs(x), axis=1)
    over = a > ceil
    print(f"before limiter: peak {20 * np.log10(a.max()):.2f} dBFS, samples over ceiling {100 * over.mean():.3f} %")
    if diag and over.any():
        sec = np.unique(np.round(np.nonzero(over)[0] / SR, 1))
        worst = {}
        for i in np.nonzero(over)[0]:
            k = round(i / SR, 1)
            worst[k] = max(worst.get(k, 0.0), 20 * np.log10(a[i] / ceil))
        print("  over-ceiling at (s: dB over):", " ".join(f"{k}:{worst[k]:.1f}" for k in sec))
    for _ in range(6):
        x *= 10.0 ** ((-20.0 - rms_db(x)) / 20.0)
        if np.max(np.abs(x)) > ceil:
            x = limiter(x, ceil)
    x = np.clip(x, -ceil, ceil)
    iz = int(FADE1 * SR)
    d = rng2.random(x.shape) - rng2.random(x.shape)   # TPDF ディザ（±1 LSB）
    y = np.clip(np.round(x * 32767.0 + d), -32767, 32767).astype(np.int16)
    y[iz:] = 0
    assert y.shape == (N, 2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wavfile.write(OUT, SR, y)
    yf = y.astype(np.float64) / 32768.0
    pk = 20 * np.log10(np.max(np.abs(yf)) + 1e-30)
    print(f"wrote {OUT}")
    print(f"length {y.shape[0]} samples = {y.shape[0] / SR:.4f} s, peak {pk:.2f} dBFS, RMS {rms_db(yf):.2f} dBFS")
    mono = yf.mean(axis=1)
    f, P = signal.welch(mono, SR, nperseg=8192)
    for lo, hi in ((0, 200), (200, 800), (800, 2000), (2000, 5000), (5000, 22050)):
        band = P[(f >= lo) & (f < hi)].sum() / P.sum()
        print(f"  band {lo:5d}-{hi:5d} Hz energy share: {100 * band:.3f} %")
    if diag:
        env = [rms_db(yf[int(s * SR):int((s + 2) * SR)]) for s in range(0, int(DUR), 2)]
        print("  2 s RMS:", " ".join(f"{s}:{e:.0f}" for s, e in zip(range(0, int(DUR), 2), env)))
    for a, b, name in SECTIONS:
        seg = yf[int(a * SR):int(b * SR)]
        print(f"  {a:6.1f}-{b:6.1f} {name:6s} RMS {rms_db(seg):6.1f} dBFS  peak {20 * np.log10(np.max(np.abs(seg)) + 1e-30):6.1f}")
    if diag:
        for k, st in stems.items():
            row = " ".join(f"{rms_db(st[int(a * SR):int(b * SR)]):6.1f}" for a, b, _ in SECTIONS)
            print(f"  stem {k:5s} {row}")
    print(f"total {time.time() - t0:.1f} s")


if __name__ == '__main__':
    main()
