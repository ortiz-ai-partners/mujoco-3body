# 提出動画の見方：動画時刻・sim 時刻・場面・機体・制御の対応表

本書は提出動画 `out/3body_arena_v7_take51.mp4`（1280×720、30 fps、長さ 2:47＝167.0 s）を読み解くための対応表である。
画面の大きさとフレームレートは `v6_common.py` の `VIDEO_W`／`VIDEO_H`／`VIDEO_FPS`、長さは `out/v7_full_report_take51.json` の `video_silent.seconds`。
動画は 1 本の連続した MuJoCo 3.11.0 シミュレーション（sim 404.22 s、同 JSON の `mujoco`、`sim_seconds`）の記録で、省略（ジャンプカット）はなく、外力もテレポートもない。
時刻は二つの時計で示す。動画時刻は m:ss.s、シミュレーション時刻は「sim 秒」と書く。
すべての時刻の出所は同じ報告 JSON の `events[].video_t`・`events[].t`、`manager.decisions`、`face.log` で、次のコマンドで同じ表が出る。

```
python analysis/timeline_times.py out/v7_full_report_take51.json
```

登場するのはブルドーザー（BZ、自作 course-builder の規則制御）、パッカン（Microduck, Pollen Robotics）、跳跳（Jumper, KingKong Robotics）の 3 体と、
失敗したときの次の一手を選ぶ「支配人 AI」、跳跳の表情を推論する「気分ネット」の 2 つの自作 AI である。呼び名の対応は `docs/glossary.md`。
動画には Microduck の 3D モデル（メッシュは CC BY-NC-SA 4.0、`microduck_rl` の `LICENSE-MODELS.md`）の外観が映るため、
動画は CC BY-NC-SA 4.0 の条件で扱う（帰属：Pollen Robotics、microduck_rl）。リポジトリのコードは MIT（`LICENSE`、詳細は `THIRD_PARTY.md`）。

## 1. 画面の読み方

### 速度区間

| 動画時刻 | sim 秒 | 速度 | 映るもの |
|---|---|---|---|
| 0:00.0〜0:44.1 | 0.0〜176.4 | ×4 | 施工：BZ が坂 2 枚を置き場から運んで峠を組む。省略なし |
| 0:44.1〜2:29.1 | 176.4〜386.3 | ×2 | BZ の走破、パッカンの挑戦と座り込み、跳跳の越境、支配人 AI の 5 手、3 体が輪に並ぶまで |
| 2:29.1〜2:47.0 | 386.3〜404.2 | ×1 | 輪の万歳（公式ダンス 12.4 s＋ポーズ 3 s）と、END のあとに物理を 2.5 s 回し続ける終幕 |

出所：`analysis/timeline_times.py` の speed segments（`events` の `t` と `video_t` の比）。
速度の定義は `v7_full.py` の `SPEED`（`BUILD` から `CELEBRATE` まで 2.0、`END` 1.0）、`SPEED_DANCE`（1.0、輪のダンス開始で切替）、
施工だけを 4 倍にする `--build-speed 4`（仕組みは本節の最後）。ダンス 12.4 s とポーズ 3 s は `CHEER_DANCE_S`・`CHEER_HOLD_S`、
終幕の 2.5 s は `main()` 末尾の書き出しループ（`2.5 / CONTROL_DT` 回）。右下の時計が常に現在の倍率を示すので、見ている区間の速度は画面で確認できる。

### 画面の 5 つの要素

- 左上の字幕：題 1 行＋本文 2 行（`v7_full.py` `caption()`）。題は段階ごとに替わり（施工、峠の走破、坂に挑む、跳跳の登坂、仲間を呼ぶ、戻る、
  支配人 AI が次の一手を選ぶ、万歳）、先頭の「v7」は筋書きの版名である。本文は各機体のいまの動作と計測値（高さ、傾き、接触の有無、押し上げ回数）を出す。
- 吹き出し（救助中の字幕 1 行目）：支配人 AI の手が走っている間は「支配人（固定ルール）：「定型セリフ」 n 手目 ACTION」、
  手と手の間は「支配人（固定ルール）：（観察中） 直前の結果 …」。セリフは `crab_help.py` `LINES` の定型文で、画面上では跳跳を「カニさん」と呼ぶ（コード識別子 `crab`）。
- 右上の顔モニター（240×120、`crab_face.py` `PIP_W`／`PIP_H`）：跳跳の表示板を、板の 0.30 m 前に置いた顔カメラ（`CAM_DIST`）で写した絵。
  上段に「決め手の値」（その表情を選んだ規則が根拠にした数値、`FaceDriver.title_label`）。絵の下は、救助中（sim 264.6〜369.4 s、`stage == "RESCUE"`）だけ
  4 本の棒「成・止・転・空」と「AI：成功xx 止xx 転xx 空xx｜渡れるxx」（気分ネットの 5 出力、`bars`・`ai_label`）、
  それ以外は計測値「力 x.x  接触 n 秒  止まっている」（`measured_label`）。最下行は「顔の名前：理由」（`label`）。
- 右下の時計：「sim 264.6 s   x2」。sim は物理の経過秒、x は再生倍率。施工中は `clock.speed × build_write_every` で x4 と表示される（`v7_full.py` `render_frame` の footer）。
- 左下の注記：省略があるときだけ「≫ 省略（sim a→b s）：…」を 3 秒出す（`v6_common.py` `draw` の `notice`）。提出版は `--no-cuts` なので一度も出ない。

カメラは段階ごとに自動で構図を変える（`render_frame` の `cam.aim`）：施工は BZ とコース中心の間を見る俯瞰（仰角 −38°）、
坂の挑戦・登坂・救助（押し上げ）は方位 15° の横から 2 体の間を見る（坂の挑戦はパッカン寄りの 0.6:0.4、登坂の後半は跳跳だけ）。
輪は南から 3 体の重心を見る（方位 92°）。
音はパッカンと跳跳の電子的な鳴き声で、`v7_full.py` `Chirps` が動画時刻（`add(video_t, …)`）に置いて合成した効果音（`MASTER_GAIN` 0.45）であり、物理には関係しない。

### 決め手の値の例

顔モニター上段の文は `crab_face.py` `FaceDriver.choose` が規則ごとに組む。提出版で出る形は次のとおり。

| 場面 | 上段の文の形 | 根拠 |
|---|---|---|
| 施工中・待機 | 戯れ・待機（固定プログラム）、傾き n° | 規則 17 |
| パッカンの挑戦を応援 | パッカン 坂に挑む、進み +n cm/2 秒（登っている） | 規則 7、停滞窓 `STALL_S` 2 s |
| 登れない | パッカン 坂に挑む、足踏み n 秒（進み +0 cm/2 秒） | 規則 6 |
| 救助の各手 | SEAT 成功 80%（にっこり 4%／困り 5%） | 規則 12〜14、手ごとの線は `out/manager_runs/mood_net/meta.json` の `thr_smile_by_skill`・`thr_trouble_by_skill` |
| 押し上げ中 | 力 0.7/0.7  接触 3s/5  進み +5cm ／ AI 止＋転 1%/40  転 1%/30 | 規則 8〜10、力 1.0＝接触力 10 N（`PUSH_FORCE_REF`） |
| 渡り切り | 計測：パッカンが北の床で立位（y +1.95） | 規則 3 |

### 4 倍速の実装：物理は 2 倍速の版と同一

フレームの標本化は `FrameClock`（`v6_common.py`）が行い、`speed / fps` sim 秒ごとに 1 枚を取る。
施工中は `SPEED["BUILD"] = 2.0` なので 2/30 sim 秒ごとに標本を取り、動画 1 秒に sim 2 秒が入る。
標本のたびに `render_frame()` が `sim.tracks.update()` と `mj_forward()` を呼ぶので、標本の間隔は物理の経路の一部である
（描かない標本でも `write=False` で同じ呼び出しをする。`v7_full.py` `render_frame` の docstring）。

`--build-speed 4` は標本の間隔を変えない。`build_write_every = 4 / 2 = 2` として、施工中は標本 2 枚に 1 枚だけを動画に書く（`v7_full.py` `main()` の書き出し分岐）。
書かれたフレームの間隔は sim 4/30 秒になるので再生は 4 倍速、物理の経路は 2 倍速の版と同一になる。`--build-speed` は 2 かその整数倍に限る（argparse で検査）。
検証：提出版と省略版 `out/v7_full_report_take46.json` の `state_digest`（最終状態の qpos＋qvel の sha256）は一致（先頭 678fd3cae2ca）、
`sim_seconds` 404.22 と支配人 5 手の `t` も同一であることを `analysis/timeline_times.py --compare` で確認した。

対照として、標本の間隔そのものを 4/30 秒に変えた試作版（`out/v7_full_report_take50.json`、`state_digest` 先頭 768e78f7）は経路が変わった。
3 体とも渡り切り、支配人は同じ 5 手だが、押し上げの所要は 71.3 s から 56.1 s（`manager.decisions[1].duration_s`）に、長さは 2:40（`video_silent.seconds` 160.2）になった。
描画の都合が物理に触れた例として記録に残し、提出版には標本の間隔を保つ実装を採った。

## 2. 出来事の対応表

制御の列の読み方。公式 ONNX は推論のみで改変していない。「固定プログラム」は先回りや輪の位置取りなど、上の制御器に目標（速度指令・向き）を与える自作の手順である。

| 制御 | 中身 | 既製／自作 | 推論／学習 |
|---|---|---|---|
| 規則制御（BZ） | course-builder の `SlopeAssembly`／`Transport`／`Navigator` | 自作 | AI 推論なし |
| velstand／alpha_sitstand（パッカン） | Pollen Robotics 公式 ONNX（`policies/microduck/`、観測 61、50 Hz） | 既製 | 推論のみ |
| locomotion／jump／dance_crab（跳跳） | KingKong Robotics 公式 ONNX（公式バンドル `../jumper/out/bundle_example/jumper/`、観測 415／167／209） | 既製 | 推論のみ |
| 支配人 AI | 観測 46 次元・6 手（`crab_help.py` `OBS_DIM`、`ACTIONS`）。提出版は固定ルール `rule_action` | 自作 | 推論（PPO 版・Q 表版は学習済み） |
| 気分ネット | 53-32-32-5 の MLP（`out/manager_runs/mood_net/`）。顔だけに使い物理を変えない | 自作 | 推論（学習済み） |
| 固定プログラム | 戯れ、先回り、回り込み、輪の位置取り、応援の合図 | 自作 | AI 推論なし |

公式ポリシーの版：velstand は microduck_rl commit 3750776・checkpoint 2749（export 2026-10-12）、alpha_sitstand は commit 77ffadf・checkpoint 2250（export 2026-10-01）で、
出所は `policies/microduck/manifest.json`（`policies[].training`）。この 2 本の ONNX のライセンス表示は配布元で確認できていない（`THIRD_PARTY.md`）。
学習コード microduck_rl は Apache-2.0。跳跳の 3 本は jumper リポジトリが git 追跡で同梱する公式バンドル（Apache-2.0）。ライセンスと取得手順の全文は `THIRD_PARTY.md`。
公式ポリシーの動き（登坂、ジャンプ、ダンス）は公式の成果であり、本プロジェクトは目標を与えて呼び出す（前方ジャンプの股関節ヨーの関節目標だけを重ねる）。

| 動画時刻 | sim 秒 | 場面 | 動いている機体 | 制御 | 既製／自作 |
|---|---|---|---|---|---|
| 0:00.0 | 0.0 | 上り坂を置き場から運んで設置（UP） | BZ | 規則制御（Transport） | 自作 |
| 0:00〜0:26 | 0〜106 | 施工の間、パッカンと跳跳は遊び場で戯れる。跳跳は近づいて跳び、離れて休むのを繰り返す（`v7_full.py` `play`、`jp_events` の `JUMP` は sim 0〜98 s に 9 回、おおむね 12〜14 s おき） | パッカン、跳跳 | velstand／locomotion＋jump（目標は固定プログラム） | 既製／自作 |
| 0:04.1 | 16.3 | フォークを上げ（RAISE_UP）、空荷で下り坂の置き場へ（TO_DOWN、17.9） | BZ | 規則制御（Navigator） | 自作 |
| 0:14.4 | 57.5 | レーン位置合わせ、向き合わせ（65.8）、後退（75.6）、フォークを下げる（79.1） | BZ | 規則制御 | 自作 |
| 0:20.2 | 80.8 | 下り坂を運んで設置（DOWN）、フォークを上げる（RAISE_DOWN、104.4） | BZ | 規則制御（Transport） | 自作 |
| 0:26.5 | 106.1 | 空荷でスタート地点へ回る（TO_START）。パッカンは待機場所へ、跳跳は見物位置へ | BZ、パッカン、跳跳 | 規則制御／velstand／locomotion | 自作／既製 |
| 0:44.1 | 176.4 | 完成した峠を走破（CROSS）。ここから ×2 | BZ | 規則制御（Navigator） | 自作 |
| 0:54.0 | 196.1 | 施工完了：坂 2 枚、4/4 面を走破、上昇 0.440 m（BZ 渡り切り）。物理刻み 0.005→0.001 s | BZ | 規則制御 | 自作 |
| 0:54.1 | 196.5 | パッカンが 16.3° の坂（`manager2_env.py` `SLOPE`、画面の字幕では 16°）に挑む（1 回目）。跳跳は坂の南東で応援ダンス | パッカン、跳跳 | velstand／dance_crab | 既製 |
| 1:01.1 | 210.5 | 入口で足踏みし、いったん後ずさり（y=−1.99、入口 y=−1.86） | パッカン | velstand | 既製 |
| 1:02.4 | 213.0 | もう一回挑む（2 回目） | パッカン | velstand | 既製 |
| 1:07.9 | 224.0 | 登れない（y=−2.00）。跳跳は自分のレーンの足元へ先回り | パッカン、跳跳 | velstand／locomotion（固定プログラム） | 既製／自作 |
| 1:08.2 | 224.6 | 諦めて座り込む。首を振って鳴く（226.1） | パッカン | alpha_sitstand | 既製 |
| 1:10.3 | 228.9 | 跳跳が座ったパッカンの横を通り、坂を登る | 跳跳 | locomotion | 既製 |
| 1:14.0 | 236.1 | 峠に乗る（z=0.50）。縁に引っかかって止まり、前方ジャンプ（1:15.4、239.0） | 跳跳 | jump＋股関節ヨーの関節目標（外力なし） | 既製＋自作 |
| 1:16.0 | 240.2 | 着地（y=−0.45、z=0.54）、天面を越える（242.8） | 跳跳 | locomotion | 既製 |
| 1:18.9 | 245.9 | 跳跳が渡り切り、BZ の後ろで止まる（z=0.11） | 跳跳 | locomotion | 既製 |
| 1:20.4 | 248.9 | パッカンが仲間を呼ぶ（CALL）。跳跳は東側を回って座席の後ろへ戻り始める（250.5） | パッカン、跳跳 | velstand の旋回／locomotion（固定プログラム） | 既製／自作 |
| 1:22.9 | 254.0 | 跳跳がコースの東側を回って戻る（RETURN）。BZ は動かない | 跳跳 | locomotion | 既製 |
| 1:28.2 | 264.6 | 支配人 AI が引き継ぐ（RESCUE）。1 手目 SEAT：パッカンが跳跳の方を向いて座る | パッカン | 支配人 AI → SEAT（velstand の旋回＋alpha_sitstand） | 自作 AI＋既製 |
| 1:34.2 | 276.5 | 結果 seated。2 手目 PUSH：跳跳が座ったパッカンを坂の上へ押す | 跳跳 | 支配人 AI → PUSH（locomotion 0.3 m/s） | 自作 AI＋既製 |
| 1:38.0〜2:09.8 | 284.2〜347.9 | 押し上げ中。顔は ＞＜、＞＜汗、困り汗を行き来する | 跳跳、パッカン | PUSH 継続、気分ネットが 0.02 s ごとに推論 | 自作 AI＋既製 |
| 2:09.8 | 347.9 | 結果 pushed_up（天面 z=0.50）。3 手目 BACK_OFF：跳跳がパッカンから 0.6 m 離れるまで下がる（距離 0.25→0.64 m、`crab_help.py` `skill_back_off` の `clearance`） | 跳跳 | 支配人 AI → BACK_OFF（locomotion） | 自作 AI＋既製 |
| 2:10.7 | 349.6 | 結果 cleared。4 手目 STANDUP：パッカンが天面で立つ | パッカン | 支配人 AI → STANDUP（alpha_sitstand → velstand） | 自作 AI＋既製 |
| 2:13.5 | 355.2 | 結果 standing。5 手目 WALK_ON。跳跳が 0.61 m 後ろにつき、BZ はフォークを上げてその場で向き直る | 3 体 | WALK_ON（velstand 0.3 m/s）／locomotion／規則制御 | 自作 AI＋既製／自作 |
| 2:19.1 | 366.3 | BZ が南（ゴール）を向き終え、その場で 2 体を待つ | BZ | 規則制御 | 自作 |
| 2:20.6 | 369.4 | 結果 crossed：パッカンが北の床へ（y=+1.95、z=0.15）。3 体とも渡り切り | パッカン | velstand | 既製 |
| 2:20.6〜2:27.8 | 369.4〜383.8 | 跳跳が天面で一度止まり（371.4）、下り坂を降り（375.2）、パッカンと跳跳が輪の位置に着く（383.8） | パッカン、跳跳 | velstand／locomotion（固定プログラム） | 既製／自作 |
| 2:29.1 | 386.3 | 輪の万歳：BZ はフォーク上下、パッカンは屈伸と首振り、跳跳は腕を上げてダンス。ここから ×1 | 3 体 | 規則制御／alpha_sitstand＋velstand／dance_crab | 自作／既製 |
| 2:44.5 | 401.7 | END。終幕の 2.5 s を足して 2:47.0 で終わる | — | — | — |

出所：`events` の全 62 行（本表は要約）。座標は world 座標で、y は南から北へ正、コースの中心線は x=1.45（`crab_help.py` `LANE_X`）。
施工の工程名（UP, TO_DOWN, CROSS など）は course-builder の `SlopeAssembly.phase` で、字幕には日本語で出る（`v6_phase4_full.py` `PHASE_TEXT`）。
支配人 AI の手の名前（SEAT など）は `crab_help.py` `ACTIONS`、結果の名前（seated など）は `RESULT_SLOTS` のとおり。

## 3. 支配人 AI の 5 手

提出版の支配人は固定ルール（`crab_help.py` `rule_action`）で、観測 46 次元から 6 手のうち 1 つを選ぶ。
1 手＝1 スキルで、スキルが結果を返すまで次の判断はしない。5 手すべてが狙った結果で終わり、転倒 0、コース破損なし（`course_disturbed` は空）。

| 手 | 動画時刻（sim 秒） | 定型セリフ | 結果（動画時刻） | 所要 sim 秒（動画秒） |
|---|---|---|---|---|
| 1 `SEAT` | 1:28.2（264.6） | パッカン、カニさんの方を向いて座って | `seated`（1:34.2） | 11.9（6.0） |
| 2 `PUSH` | 1:34.2（276.5） | カニさん、そっと押し上げてあげて | `pushed_up`（2:09.8、天面 z=0.50） | 71.3（35.7） |
| 3 `BACK_OFF` | 2:09.8（347.9） | カニさん、少し離れて | `cleared`（2:10.7） | 1.7（0.9） |
| 4 `STANDUP` | 2:10.7（349.6） | パッカン、立てる？ | `standing`（2:13.5） | 5.5（2.8） |
| 5 `WALK_ON` | 2:13.5（355.2） | パッカン、そのまま進んで | `crossed`（2:20.6、y=+1.95） | 14.2（7.1） |

出所：`manager.decisions[].t`・`video_t`・`bubble`・`result`・`duration_s`。動画秒は ×2 区間なので sim 秒の半分。
定型セリフは `crab_help.py` `LINES` の 8 本（6 手それぞれの文と、2 回目以降の押しに使う `PUSH_RETRY`、転んだ相手を押してずらす `NUDGE`。選び方は `bubble_line`）。
提出版で画面に出たのは上の 5 本で、`WAIT`・`PUSH_RETRY`・`NUDGE` は出ていない。

判断時の観測の要点（`manager.decisions[].duck`、`stage`、`crab_dist`、`last_result`）：
1 手目はパッカンが座席付近に座り（SIT／toe）、跳跳は 0.99 m 離れて非接触、直前の結果なし。2 手目は結果 `seated` を受けて同じ位置から押しに入る。
3 手目は天面（deck）で跳跳が 0.25 m まで密着しているので離れさせ、4 手目は 0.64 m 離れたのを見て立たせ、5 手目は立位（STAND／deck）を見て歩かせる。
PUSH の条件は「座っている、かつ跳跳の方を向いている、かつ座席か坂の上か縁の近くにいる」（`rule_action`）。
この版の筋では 2 手目の時点でパッカンが座席に座り直しているため、押し上げは 1 回で天面に届いた。他の方式の手順との違いは第 5 節。

## 4. 跳跳の表情ログ

表情は 11 種から 17 本の優先規則で決まる（`crab_face.py` 冒頭の docstring。上から順に最初に当たった規則が勝つ）。
提出版の `face.log` は 26 行で、使われた顔は 9 種（ぐるぐる＝転倒とガーン＝相手の転倒は、転倒がなかったので出ない）。
気分ネットは救助の間、制御周期 0.02 s（`v7_full.py` `CONTROL_DT`）ごとに推論し、計 5,236 回（`face.mood_ai.inferences`）。「成功 80%」などの値はその出力 p(成功) である。

| 動画時刻 | sim 秒 | 顔 | 理由 | 規則 |
|---|---|---|---|---|
| 0:00.0 | 0.00 | まる目（neutral） | 戯れ・待機 | 17 |
| 0:54.1 | 196.46 | にっこり（happy） | パッカンを応援 | 7 |
| 1:00.2 | 208.64 | 困り（troubled） | パッカンが登れない（坂に挑む） | 6 |
| 1:02.4 | 213.00 | にっこり | パッカンを応援 | 7 |
| 1:05.4 | 219.00 | 困り | パッカンが登れない（もう一回） | 6 |
| 1:10.3 | 228.86 | 真剣（serious） | 坂を登る | 16 |
| 1:18.9 | 245.92 | まる目 | 待機 | 17 |
| 1:28.2 | 264.58 | にっこり | 座らせる、成功 80% | 13 |
| 1:34.2 | 276.52 | ほっ（relief） | うまくいった | 5 |
| 1:35.2 | 278.52 | 真剣 | 押しに行く、成功 98% | 14 |
| 1:35.5 | 279.30 | にっこり | 押しに行く、成功 99% | 13 |
| 1:38.0 | 284.22 | ＞＜（cross） | 押し上げ中 | 10 |
| 1:38.3 | 284.74 | ＞＜汗（sweat） | 押し上げ中、力 0.7 | 9 |
| 1:39.4 | 287.08 | ＞＜ | 押し上げ中 | 10 |
| 1:40.5 | 289.20 | ＞＜汗 | 押し上げ中、接触 5 秒超 | 9 |
| 1:41.0 | 290.14 | 困り汗（troubled_sweat） | 押しながら、進みが止まった | 8 |
| 1:48.5 | 305.26 | ＞＜汗 | 押し上げ中、接触 5 秒超 | 9 |
| 1:49.9 | 307.98 | 困り汗 | 押しながら、進みが止まった | 8 |
| 1:51.8 | 311.82 | ＞＜汗 | 押し上げ中、力 0.8 | 9 |
| 2:09.8 | 347.86 | ほっ | うまくいった | 5 |
| 2:11.7 | 351.62 | にっこり | 立たせる、成功 99% | 13 |
| 2:13.5 | 355.18 | ほっ | うまくいった | 5 |
| 2:14.5 | 357.18 | 真剣 | 見送る、成功 98% | 14 |
| 2:19.7 | 367.56 | にっこり | 見送る、成功 99% | 13 |
| 2:20.6 | 369.38 | キラキラ（sparkle） | パッカンが渡り切った | 3 |
| 2:29.1 | 386.34 | にっこり | 祝賀ダンス | 4 |

出所：`face.log` の各行（sim 秒、顔、理由、規則番号、計測値と推論値）。動画時刻は `analysis/timeline_times.py` が `events` の時刻を補間して出す。

読み方の補足。1:35.2 の真剣と 1:35.5 のにっこりの違いは、PUSH のにっこりの線が 0.987 と高いためである
（`meta.json` `thr_smile_by_skill.PUSH`。`face.log` の p(成功) は 278.52 s に 0.978 で線の下、279.30 s に 0.987 で線に達した）。
4 手目の STANDUP は 2:10.7 に始まるが、顔が「にっこり（立たせる 99%）」になるのは 2:11.7 である。
sim 349.6〜351.6 s の 2 秒（×2 区間なので動画では 1 秒）は、3 手目 BACK_OFF の結果 `cleared` で出し直された「ほっ」（規則 5、`RELIEF_S` 2 s）が優先する。
良い結果（`crab_face.py` `GOOD_RESULTS`）のたびに `relief_until` が延びるので、2:09.8 からの「ほっ」が続いて見え、`face.log` に新しい行は出ない。

押し上げ中の「力 0.7」は接触力 7 N（力 1.0＝10 N、`PUSH_FORCE_REF`）、「接触 5 秒超」は `PUSH_SWEAT_S`、
「進みが止まった」は押しながら 3 秒進まない状態（`PUSH_STALL_S`）で、提出版では 2 度記録された。どちらも押し上げは続き、天面に届いた。
表情の規則としきい値の全表は `docs/mood_net_and_faces.md`。

## 5. 4 本の動画と省略版との関係

提出動画のほかに、支配人 AI の方式と結末を替えた 3 本を同じ設定（施工 ×4、省略なし、以後 ×2、ダンス ×1）で描画した。
いずれも 3 体とも渡り切り（`three_crossed` すべて true）、コース破損なし（`course_disturbed` は空）。長さは各報告 JSON の `video_silent.seconds`。

| 版 | ファイル（`out/`） | 支配人 AI | 結末 | 長さ | 手数 |
|---|---|---|---|---|---|
| 提出版 | `3body_arena_v7_take51.mp4` | 固定ルール | 輪の万歳 | 2:47（167.0 s） | 5 |
| PPO 版 | `3body_arena_v7_take52.mp4` | PPO v2.2（`ppo2_v22`） | 輪の万歳 | 2:45（165.2 s） | 4 |
| Q 表版 | `3body_arena_v7_take53.mp4` | 学習済み Q 表（`tabq2_small`）、`--jitter 0.4` | 輪の万歳 | 2:46（166.3 s） | 8 |
| 追走版 | `3body_arena_v7_take54.mp4` | 固定ルール | 追走して三人そろって万歳 | 2:44（163.7 s） | 5 |

PPO 版（`out/v7_full_report_take52.json`）は SEAT → PUSH → STANDUP → WALK_ON の 4 手で、押し上げ直後に離れる手を省き、跳跳が 0.25 m に密着したまま立たせて成功した。
パッカンの渡り切りは 2:18.7（sim 365.6 s）、輪のダンス開始 2:27.3（sim 382.7 s）、END 2:42.6。

Q 表版（`out/v7_full_report_take53.json`）は STANDUP → WALK_ON（`stalled`）→ SEAT → PUSH → BACK_OFF → STANDUP → STANDUP（`nothing`）→ WALK_ON の 8 手。
まず立たせて歩かせ、入口で止まったのを見て座らせて押す手順に切り替えた。押し上げの所要は 59.0 s で、渡り切りは 2:20.7（sim 369.5 s）、ダンス開始 2:28.4。
立位の相手への 2 度目の STANDUP（結果 `nothing`、1.0 s）は判断の誤りであり、評価 v4 では結果が `nothing` の手を「無駄な手」として 1 話あたりで数える
（`manager2_report.py` の `wasted_per_episode`、`out/manager_runs/comparison_v4.md` の列で Q 表 5.17、固定ルール 0.07）。

`--jitter 0.4` は跳跳の応援ダンスを収録の 0.4 s 先から始める引数（`CHEER_DANCE_START` に加算）で、目的は物理の経路を変えることだけである。報告 JSON には記録されないので、使った値は描画コマンドに残す（argparse の help の指示）。
jitter 0 の経路（`out/v7_full_report_take26.json`）では、7 手目 WALK_ON の途中でパッカンが下り坂で転び（sim 358.3 s）、起き上がれないまま救助の上限 240 s（`--rescue-max`）で打ち切られた。
その間 Q 表は BACK_OFF（結果 `nothing`）と WAIT を 31 回選び、パッカンは渡れなかった（39 手、`three_crossed.duck` が false）。
転倒と起き上がれなかったことは歩行スキル（公式 velstand）の下り坂での精度の不足、転んだ相手を助ける手が 6 手にないことは設計の不足である（固定ルールもこの状態では WAIT を選ぶ、`rule_action`）。
jitter 0.8 の経路（`out/v7_full_report_take29.json`）は 0.4 と同じ 8 手で渡った。動画は経路を選んだ 1 本で、方式の優劣は評価 v4（`docs/results.md`）で比べる。

追走版（`out/v7_full_report_take54.json`）の 5 手と時刻は提出版と同一で、渡り切り後に輪を作らず、跳跳が後を追い、その場で三人が万歳する（2:25.8、sim 379.8 s）。

省略版との関係。同じ 4 つの設定を、施工 ×2 と 2 か所の省略（sim 22→54 s「BZ が空荷で保管場所へ戻る」、110→172 s「BZ が空荷でスタート地点へ回る」、`v7_full.py` `DEFAULT_CUTS`）で描いた
`out/3body_arena_v7_take46.mp4`〜`out/3body_arena_v7_take49.mp4`（164.1、162.3、163.5、160.8 s）が記録に残っている。省略の間も物理は走り、画面左下に注記が 3 秒出る。

物理は提出 4 本とそれぞれ同一で、`state_digest` の先頭 12 桁が一致する：提出版と `out/v7_full_report_take46.json` が 678fd3cae2ca、
PPO 版と `out/v7_full_report_take47.json` が aafa49e7a869、Q 表版と `out/v7_full_report_take48.json` が f53de6e45af7、
追走版と `out/v7_full_report_take49.json` が be8fb01e8f90。
施工より後の出来事は、提出版では省略版より動画時刻で 2.86〜2.87 s 遅い（例：1 手目 1:25.3 → 1:28.2。`analysis/timeline_times.py --compare` の shift 列）。

描画コマンド（リポジトリルート。`--ending crab`、`--manager rule`、`--finale circle`、`--face-ai mood` は既定値。報告 JSON は引数を記録しないので、設定から再構成した）：

```
python v7_full.py --build-speed 4 --no-cuts --tag _take51
python v7_full.py --build-speed 4 --no-cuts --manager ppo --run ppo2_v22 --tag _take52
python v7_full.py --build-speed 4 --no-cuts --manager tabq --run tabq2_small --jitter 0.4 --tag _take53
python v7_full.py --build-speed 4 --no-cuts --finale procession --tag _take54
python analysis/timeline_times.py out/v7_full_report_take51.json --compare out/v7_full_report_take46.json
```

5 方式の 30 シード評価（固定ルール 29/30、PPO v2.2 26/30、Q 表 25/30、PPO 中規模 23/30、ランダム 14/30、`out/manager_runs/comparison_v4.md`）は `docs/results.md`、
支配人 AI の設計は `docs/manager_ai.md`。

## 6. English event table and YouTube subtitles

Playback speed is x4 until 0:44, x2 until 2:29 and x1 to the end (2:47); the sim clock and the speed are shown at the bottom right throughout. There are no jump cuts.
Times are from `out/v7_full_report_take51.json` (`events[].video_t`, `events[].t`). "Official" means an unmodified ONNX policy run in inference only; "own" means made in this project.
The video shows the Microduck 3D model, so the video is CC BY-NC-SA 4.0 (attribution: Pollen Robotics, microduck_rl); the code in this repository is MIT.

| Video | Sim s | Event | Robot | Control |
|---|---|---|---|---|
| 0:00 | 0 | BZ carries the up-ramp from storage and sets it; the duck and the crab play in the yard (x4) | BZ, Microduck, Jumper | own rule controller / official ONNX |
| 0:20 | 81 | BZ carries and sets the down-ramp, then drives round to the start | BZ | own rule controller (course-builder) |
| 0:44 | 176 | BZ drives over the finished pass (x2 from here) | BZ | own rule controller |
| 0:54 | 196 | Construction done: 2 ramps, 4/4 surfaces, rise 0.440 m. The duck tries the 16.3-degree ramp while the crab dances | Microduck, Jumper | velstand / dance_crab (official) |
| 1:01 | 210 | The duck stalls at the toe, backs off and tries again at 1:02 | Microduck | velstand (official) |
| 1:08 | 225 | The duck gives up and sits down | Microduck | alpha_sitstand (official) |
| 1:10 | 229 | The crab climbs the ramp; stuck at the crest, it jumps forward (1:15) and lands on the deck | Jumper | locomotion + jump (official) + own hip-yaw joint targets, no external force |
| 1:19 | 246 | The crab has crossed and stops behind BZ; at 1:20 the duck calls and the crab walks back round the east side | Jumper, Microduck | official ONNX, targets from a fixed programme (own) |
| 1:28 | 265 | The manager AI (fixed rules) takes over. Move 1 SEAT: the duck turns to face the crab and sits | manager AI, Microduck | own AI (inference) -> velstand, alpha_sitstand |
| 1:34 | 277 | Move 2 PUSH: the crab pushes the seated duck up the ramp (36 s of video, 71 s of sim); the mood net drives the face | Jumper | locomotion 0.3 m/s (official); mood net (own AI) |
| 2:10 | 348 | Move 3 BACK_OFF (the crab backs away until it is 0.6 m clear), then move 4 STANDUP at 2:10.7: the duck stands on the deck | Jumper, Microduck | locomotion / alpha_sitstand -> velstand |
| 2:14 | 355 | Move 5 WALK_ON: the duck walks across and down; the crab follows 0.6 m behind; BZ turns round | all three | velstand / locomotion / own rule controller |
| 2:21 | 369 | The duck reaches the far floor: all three have crossed | Microduck | velstand |
| 2:29 | 386 | The circle (x1): BZ pumps its fork, the duck squats and shakes its head, the crab dances with its claws up | all three | own rule controller / alpha_sitstand + velstand / dance_crab |
| 2:44 | 402 | End (the video runs to 2:47) | - | - |

An SRT file for YouTube is made from this table: each row's video time is a cue's start and the next row's start is its end (the last cue ends at 00:02:47,000).
A cue is a sequence number, a line `HH:MM:SS,mmm --> HH:MM:SS,mmm`, the text (at most 2 lines) and a blank line, saved as UTF-8.
No speed conversion is needed, because `video_t` already includes the x4/x2/x1 playback.
`python analysis/timeline_times.py out/v7_full_report_take51.json` prints the same times to 0.1 s for finer cues.
In YouTube Studio the file is added under Subtitles, Add language, Upload file, With timing. Example of the first cue:

```
1
00:00:00,000 --> 00:00:20,200
BZ carries the up-ramp from storage and sets it (x4 playback)
```
