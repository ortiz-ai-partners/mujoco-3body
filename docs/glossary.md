# 用語対応表（呼び名｜正式名｜英語｜コード識別子）

本リポジトリの文書・動画の字幕・コードで使う呼び名を 1 か所に集める。読者向け文書は「呼び名」の列の語に統一し、コード識別子は英語のまま等幅で書く。
出所の列は、その名前が定義されているファイルを示す。「本書の訳」とある日本語は、コードに日本語名がなく本書が与えた説明語である。

## 1. 機体と AI

| 呼び名 | 正式名・製作元 | 英語 | コード識別子 | 出所 |
|---|---|---|---|---|
| パッカン | Microduck（Pollen Robotics）。既製の機体モデル | Microduck, "Pakkan" | `MD`、`md-`（プレフィックス）、`duck`、`Duck` | `v6_common.py` `MD_XML`、`v6_robots.py`、`v7_full.py` |
| 跳跳 | Jumper（KingKong Robotics）。既製の機体モデル | Jumper, "Chōchō" (nickname "Cho-san") | `JP`、`jp-`、`crab`、`Crab` | `v6_common.py` `JP_XML`、`v7_full.py`、`crab_help.py` |
| ブルドーザー | 自作 physical-ai-course-builder のフォーク付き車体。ルール制御 | bulldozer | `BZ`、body `dozer`、自由関節 `base` | `v6_common.py` `BZ_XML`、`scene_fork_tracks.xml` |
| 支配人 AI | 失敗したときの次の一手を選ぶ方策。自作、PPO と表形式 Q は学習、本番は推論（固定ルールは学習なし）。観測 46 次元、6 手 | manager AI | `manager`、`OBS_DIM`、`--manager {rule,ppo,tabq}` | `crab_help.py`、`manager2_*.py`、`v7_full.py` |
| 気分ネット | 跳跳の表情を決める小さな MLP（53-32-32-5）。自作、学習して本番は推論 | mood net | `MoodAI`、`MOOD_NET = "mood_net"`、`--face-ai mood` | `crab_face.py`、`analysis/mood_train.py` |
| 公式ポリシー | 提供元が配布した ONNX 5 本（Microduck 2、Jumper 3）。既製、推論のみ、改変なし | official policy | `velstand`、`alpha_sitstand`、`locomotion`、`jump`、`dance_crab` | `policies/microduck/manifest.json`、`v7_policies.py` |

コード識別子 `crab` と、愛称「ちょーさん」（英語 Cho-san）は跳跳（Jumper）を指す。跳跳は「ちょうちょう」（Chōchō）と読み、「ちょーさん」はその呼び名である。
「ちょーさん」は支配人のセリフ（「ちょーさん、そっと押し上げてあげて」、英語の行は `LINES_EN` で “Cho-san, give it a gentle push up.”）と自己紹介のカード（`intro.py` の `CARDS`）で使う。
以前の 2:47 版と比較用の動画の吹き出しでは「カニさん」と呼んでいた。本文では跳跳と書く。
`duck` はパッカン。`MD`／`JP`／`BZ` は 3 体の省略形で、観測や報告 JSON のキー（`three_crossed` の `bz`／`crab`／`duck`）にも現れる。

## 2. コースと場所

座標は world 座標（m）で、y が北、x が東。y の値はレーン（x = 1.45）の上での位置を示す。

| 呼び名 | 意味 | 英語 | コード識別子・値 | 出所 |
|---|---|---|---|---|
| 坂の入口／足元 | 上り坂の下端 | toe (of the up-ramp) | `TOE_Y = -2.0`、段階 `toe` | `crab_help.py` `TOE_Y`、`STAGES` |
| 上り坂 | 16.3° の斜面（0.44 / 1.505） | up-ramp | 段階 `ramp_up`、`SLOPE` | `crab_help.py`、`manager2_env.py` `SLOPE` |
| 峠 | 上り坂の上端（天面の縁） | crest | `CREST_Y = -0.495` | `crab_help.py` `CREST_Y` |
| 天面 | 2 枚の坂の平らな上面（高さ 0.44 m） | deck, landing | 段階 `deck`、`course_z = 0.44` | `crab_help.py` `STAGES`、`course_z()` |
| 継ぎ目 | 天面 2 枚の間（設計値 1 cm、旧コースは 5 cm） | seam, joint gap | `INSTALLATION_GAP = 0.01`（course-builder） | `../physical-ai-course-builder/slope_assembly.py` `INSTALLATION_GAP` |
| 下り坂 | 天面の北側の斜面 | down-ramp | 段階 `ramp_down`、`DECK_N_Y = 0.548` | `crab_help.py` `DECK_N_Y`、`STAGES` |
| 下り坂の出口 | 下り坂の下端 | far toe | `DOWN_TOE_Y = 2.05` | `crab_help.py` `DOWN_TOE_Y` |
| 北側の床 | 下り坂を降りた先の床（ゴール側） | the floor north of the course | 段階 `north` | `crab_help.py` `Helpers.stage()` |
| 横 | コースの脇の床（レーンから 0.5 m 超、または面より 10 cm 低い） | beside the course | 段階 `beside` | `crab_help.py` `Helpers.stage()` |
| レーン | 押す線・歩く線。コース中央 x = 1.45 | lane | `LANE_X = 1.45` | `crab_help.py` `LANE_X` |
| 座席 | 押し上げのために座る位置。入口の 13 cm 手前 | seat | `SEAT_Y = TOE_Y - 0.13`、`SEAT_TOL = 0.12` | `crab_help.py` `SEAT_Y`、`SEAT_TOL` |
| 相手を向く | 座ったパッカンが南（跳跳の側）を向くこと | facing the crab | `FACE_SOUTH`、`FACING_TOL = 15°` | `crab_help.py` `FACE_SOUTH`、`FACING_TOL` |

動画の RAMP 段の字幕と報告 JSON の出来事の文言は、坂の入口を「y=-1.86」と表示する（`v7_full.py` に書き込まれた文字列）。
斜面の上面の下端は舞台 XML でも y ≈ −2.00 m で、本書の位置は `TOE_Y` に従う（`docs/physics_integration.md` の 9 節）。

## 3. 支配人 AI の 6 手（行動）

| 呼び名 | 定型の吹き出し | 英語 | コード識別子 | 出所 |
|---|---|---|---|---|
| 様子を見る（待つ） | 「ちょっと待とう」 | WAIT: everybody holds 4 s | `WAIT` (0) | `crab_help.py` `ACTIONS`、`LINES`、`bubble_line()` |
| 座らせる | 「パッカン、ちょーさんの方を向いて座って」 | SEAT: walk to the seat, face south, sit | `SEAT` (1) | 同上 |
| 押しに行く（押し上げ） | 「ちょーさん、そっと押し上げてあげて」（2 回目以降は「もう一回いこう。…」） | PUSH: the crab pushes at 0.3 m/s to the landing | `PUSH` (2)、`PUSH_RETRY` | 同上 |
| 少し離れる | 「ちょーさん、少し離れて」 | BACK_OFF: reverse until 0.6 m clear | `BACK_OFF` (3) | 同上 |
| 立たせる | 「パッカン、立てる？」 | STANDUP: sitstand flag 0, or wait for recovery | `STANDUP` (4) | 同上 |
| 見送る（進ませる） | 「パッカン、そのまま進んで」 | WALK_ON: walk north along the lane | `WALK_ON` (5) | 同上 |

括弧の数字は `ACTIONS` の添字。日本語の動詞形（座らせる・押しに行く・少し離れる・立たせる・見送る・様子を見る）は `crab_face.py` の `SKILL_JA` と同じで、
顔モニターの表示にも使う。「無駄な手」の定義は 11 節の表にある。

定型の吹き出しは `LINES` に 8 本ある：6 手の 6 本と、2 回目以降の押しに使う `PUSH_RETRY`、転んだパッカンに `PUSH` を選んだときの `NUDGE`
（「ちょーさん、そっと押してずらしてあげて」）。どれを出すかは `crab_help.bubble_line()` が決める。
`NUDGE` は吹き出しの名前で、7 番目の手ではない。押してずらす実験のスキル `skill_nudge` は `SKILLS` に含まれず、本番でも評価でも使わない（`crab_help.py` の docstring）。
転んだパッカンへの `PUSH` は通常の `skill_push` が実行され、何もせずに終わる。

## 4. 13 の結果（手がどう終わったか）

| コード識別子 | 日本語 | 英語の意味 | 出所 |
|---|---|---|---|
| `none` | なし（開始時） | no previous result | `crab_help.py` `RESULT_SLOTS` |
| `waited` | 待った | WAIT ran its course | 本書の訳 |
| `seated` | 座った | the duck sat down | 本書の訳 |
| `pushed_up` | 押し上げた（天面に乗った） | pushed onto the landing | 本書の訳 |
| `fell` | 転んだ | the duck fell | `crab_face.py` `RESULT_JA` |
| `stalled` | 動かない（止まった） | no progress | 同上 |
| `slipped` | 滑った | slid back | 同上 |
| `cleared` | 離れた | the crab is clear | 本書の訳 |
| `standing` | 立った | the duck is standing | 本書の訳 |
| `still_down` | 起きない | the duck stayed down | `crab_face.py` `RESULT_JA` |
| `crossed` | 渡り切った | crossed to the north floor | 本書の訳 |
| `walked` | 歩いた（渡り切る前に止まった） | walked on but did not cross | 本書の訳 |
| `nothing` | 変化なし（空振り） | nothing happened | `crab_face.py` `RESULT_JA` |

## 5. 進行段階（パッカンがどこにいるか、6 種）

| コード識別子 | 日本語 | 英語 | 出所 |
|---|---|---|---|
| `toe` | 坂の入口（足元） | at the up-ramp's toe | `crab_help.py` `STAGES`、`Helpers.stage()` |
| `ramp_up` | 上り坂の途中 | on the up-ramp | 同上 |
| `deck` | 天面 | on the landing | 同上 |
| `ramp_down` | 下り坂 | on the down-ramp | 同上 |
| `north` | 北側の床 | on the far floor | 同上 |
| `beside` | コースの横 | off the side of the course | 同上 |

## 6. 開始場面（学習環境の 7 種）

| コード識別子 | 日本語 | 英語 | 既定の重み | 出所 |
|---|---|---|---|---|
| `toe_seated_ok` | 足元・正座（座席で相手を向いて座っている） | seated at the seat, facing the crab | 0.30 | `manager2_env.py` `SCENARIOS` |
| `toe_seated_wrong` | 別向き（座席で別の向きに座っている） | seated, facing the wrong way | 0.20 | 同上 |
| `toe_standing` | 立ち（足元で立っている） | standing at the toe | 0.20 | 同上 |
| `toe_fallen` | 足元で転倒 | fallen at the toe | 0.10 | 同上 |
| `deck_seated` | 天面で座り | seated on the landing | 0.15 | 同上 |
| `deck_fallen` | 天面で転倒 | fallen on the landing | 0.05 | 同上 |
| `ramp_fallen` | 坂の途中で転倒（跳跳が密着） | fallen on the up-ramp, crab against it | 0.0（継続学習で 0.20） | 同上、`out/manager_runs/ppo2_v22/train_summary.json` `draw_tables` |

既定の重みは `SCENARIOS` の値で、同一シード評価はこの表で場面を引く。PPO v2.2 の継続学習だけは `draw_tables` の配分（`ramp_fallen` 0.20、`toe_seated_ok` 0.20 など）に変えた。
跳跳の初期配置は `behind`（後ろ）／`beside`（横）／`touching`（密着）の 3 種（`manager2_env.py` `CRAB_SPOTS_TOE`／`CRAB_SPOTS_DECK`／`CRAB_SPOTS_RAMP`）。
評価表（`out/manager_runs/comparison_v4.md`）の場面名は英語の識別子で書かれている。

## 7. 気分ネットの出力と跳跳の表情

| 呼び名 | 意味 | 英語 | コード識別子 | 出所 |
|---|---|---|---|---|
| 成功 | いま走っている手がうまく終わる | success | `p_success` | `crab_face.py` docstring、`analysis/mood_train.py`、`meta.json` `outputs` |
| 止まる | 止まる、または滑る | stall / slip | `p_stall` | 同上 |
| 転ばせる | パッカンが転ぶ | fall | `p_fall` | 同上 |
| 空振り | 何も起きない、起きない | nothing / stays down | `p_nothing` | 同上 |
| 渡れる | 最後には渡り切る | gets across | `p_cross` | 同上 |
| にっこりの線／困りの線 | 検証用に取り置いたデータから決めた `p_success` のしきい値（全体値 0.34／0.287、手ごとの値あり） | smile line / trouble line | `thr_smile`／`thr_trouble`、`*_by_skill` | `out/manager_runs/mood_net/meta.json` |

表情は 11 種で、識別子と日本語は `crab_face.py` の `EXPRESSIONS`／`JA` のとおり。

| コード識別子 | 日本語 | 英語 | コード識別子 | 日本語 | 英語 |
|---|---|---|---|---|---|
| `neutral` | まる目 | neutral | `sparkle` | キラキラ | sparkle |
| `serious` | 真剣 | serious | `troubled` | 困り | troubled |
| `spiral` | ぐるぐる | dizzy spiral | `troubled_sweat` | 困り汗 | troubled, sweating |
| `cross` | ＞＜ | strained | `relief` | ほっ | relief |
| `sweat` | ＞＜汗 | strained, sweating | `shock` | ガーン | shock |
| `happy` | にっこり | happy | | | |

「顔モニター」は画面右上の小窓（240×120、`PIP_W`／`PIP_H`）で、顔カメラ（`jp-face_cam`）が板を写したものと「決め手の値」を出す。

## 8. 動画の段階と機体のモード

台本（`v7_full.py`）の段階は 9 つ。報告 JSON の `events` に `stage -> …` として記録される。

| コード識別子 | 日本語 | 英語 |
|---|---|---|
| `BUILD` | 施工（BZ が坂 2 枚を運んで峠を組む） | construction |
| `FOLLOW_IN` | BZ が峠を渡り、パッカンが坂へ向かう | BZ crosses, the duck follows in |
| `RAMP` | パッカンが坂に挑み、座り込む | the duck's ramp attempts |
| `CLIMB` | 跳跳が坂を登り、ジャンプして越える | the crab climbs and jumps over |
| `CALL` | パッカンがブルドーザーを呼び、跳跳が BZ の旋回範囲から出る | the duck calls BZ |
| `RETURN` | 跳跳が東側を回って座席の後ろへ戻る | the crab returns |
| `RESCUE` | 支配人 AI が手を選ぶ | the rescue (the manager decides) |
| `CELEBRATE` | 3 体が集まり、輪になって万歳 | the celebration |
| `END` | 終了 | end |

このほか `LIFT` があるが、旧い結末（`--ending push`／`lift`）でだけ使い、本編の台本（既定の `--ending crab`）には現れない。

パッカンのモード（`v7_full.py` `MD_TEXT`）：`STAND` 立位、`WALK` 歩行、`BACK` 後ずさり、`FALLEN` 転倒→自力で起き上がり中、`SIT` お座り、
`CALL` ブルドーザーを呼ぶ、`TURN` 向きを変える、`WALK_ON` レーンを北へ歩く、`CHEER` パタパタ（旋回＋首振り）。
跳跳のモード（`v7_full.py` `Crab.set_mode`）：`HOLD` 既定姿勢で待つ、`WALK` 歩く（`locomotion`）、`IDLE` 止まる、`JUMP` 跳ぶ（`jump`）、`DANCE` 踊る（`dance_crab`）、`FREEZE` 最後の姿勢を保つ。

坂挑戦の段階（`crab_face.py` `RAMP_JA`）：`try1` 坂に挑む、`try2` もう一回、`back` 後ずさり、`handover` 諦める、`sit` 座り込む。

## 9. 施工の工程（course-builder、11 段階）

`v6_phase4_full.py` の `PHASE_TEXT` による日本語。英語は course-builder の識別子そのもの（`slope_assembly.py` `SlopeAssembly.phase`）。

| コード識別子 | 日本語 | コード識別子 | 日本語 |
|---|---|---|---|
| `UP` | 上り坂を運搬・設置 | `LOWER` | フォークを下げる |
| `RAISE_UP` | フォークを上げる | `DOWN` | 下り坂を運搬・設置 |
| `TO_DOWN` | 空荷で下り坂の置き場へ | `RAISE_DOWN` | フォークを上げる |
| `PRECISE_LANE` | レーン位置合わせ | `TO_START` | スタート地点へ移動 |
| `ALIGN` | 向きを合わせる | `CROSS` | 完成した峠を走破 |
| `RETREAT_FOR_ALIGNMENT` | 後退して差し込み準備 | | |

「空荷」は部材を持たずに走ること。`fast_empty` は空荷の直進を速くする Navigator の設定で、車体が何かに触れると施工を中断する。

## 10. 物理・描画・検証の用語

| 呼び名 | 意味 | 英語 | コード識別子・出所 |
|---|---|---|---|
| 外力なし | `xfrc_applied` と位置の書き込みを使わず、各機体が自分のアクチュエータだけで動く | physics only, no external forces | `v7_full.py` 冒頭の docstring |
| 推論のみ | 公式 ONNX を改変せず、観測を作って出力を関節目標に変換するだけ | inference only | `v7_policies.py` |
| 観測契約 | ポリシーが期待する観測の並び・次元・周期・PD ゲイン | observation contract | `locomotion.json` ほか、`docs/physics_integration.md` |
| 転記 | 公式の実装から観測の組み立てを書き写したこと | transcribed | `v7_policies.py` の docstring |
| プレフィックス | 結合時に子モデルの名前に付く接頭辞 | prefix | `md-`、`jp-`（`v6_robots.py`） |
| 舞台 XML | 施工済みの配置を書き戻した独立シーン | built stage | `out/v6_stage_built.xml` |
| ヘッドレス | 描画せずに物理と判断だけ回す実行 | headless | `v7_full.py --test` |
| 最終状態ダイジェスト | 終了時の `qpos`＋`qvel` の sha256。同じ経路なら一致 | final-state digest | `state_digest`（`v7_full.main()` 末尾、報告 JSON のキー） |
| A/B | 顔あり／なしなど 2 条件のヘッドレス通しを比べ、物理が同じことを確かめる手順 | A/B check | `analysis/face_check.py`、`analysis/timeline_times.py --compare` |
| 決定的 | 同じコード・同じ設定・同じ版なら同じ経路になる性質。設定を変えずに経路だけを変えるダイヤルが `--jitter` | deterministic | `v7_full.py` |
| ジャンプカット（省略） | 物理は走り続け、フレームだけ書かない区間 | jump cut | `DEFAULT_CUTS`、`--no-cuts`、`--cut` |
| sim 時計 | 画面右下の「sim … s」。シミュレーション時刻 | sim clock | `render_frame` の footer |
| 倍速 | 動画時刻に対するシミュレーション時刻の比（x4／x2／x1）。×4 は 2 倍速で標本化したフレームを 1 枚おきに書くだけで、物理を変えない | playback speed | `SPEED`、`SPEED_DANCE`、`--build-speed`、`--speedup`、報告 JSON の `settings.write_every` |
| 動画時刻／sim 時刻 | 動画の m:ss と「sim 404 s」。両方を添えて書く。提出動画の時刻は本編の時刻＋18.14 s | video time / sim time | `events` の `video_t`／`t` |
| 提出動画／本編 | 提出動画は講座の OP カード＋自己紹介＋本編＋講座の ED カードを結合した 2:58.4 の動画。本編はその 0:18.1 からの 1 本の連続シミュレーションの記録（2:37.3） | submitted video / main video | `assemble.py`、`out/3body_arena_v7_take57.mp4` |
| 自己紹介 | 本編の前の 15.1 s。支配人 AI が丸い顔と打ち込みの文字で名乗り、3 体をカードで紹介する。物理は進めない描画のみ | self-introduction | `intro.py`、`out/intro.mp4` |
| 講座の OP／ED カード | 提出動画の最初と最後に付ける講座の素材（3.04 s／2.97 s）。リポジトリに含まない | the course's opening / end card | `assemble.py --op`／`--ed` |
| 支配人の帯 | 支配人 AI が手を選ぶたびに画面下 1/5 に出る帯。支配人の丸い顔とセリフを 1 秒 15 文字で打ち込み（チャイムと打鍵音つき）、日本語が出そろうと英語の行を出す。描画のみ | the manager's band | `v7_full.py` `band_frame()`・`BAND_CPS`、`v6_common.Captioner._band`、`crab_help.LINES_EN`、`--no-band`、`settings.band` |
| 声の音量と振り分け | パッカンの鳴き声は 1/3、跳跳は 1/2 の音量。鳴いた機体の画面上の位置で左右に振る（定電力のパン、幅 0.8）。音声のみ | voice levels and panning | `Chirps.DUCK_GAIN`／`CRAB_GAIN`／`PAN_WIDTH`、`v6_common.screen_xy`、`settings.voice_pan` |
| BGM | 提出動画の背景音楽。numpy/scipy の加算合成だけで作る自作のマリンバ曲（既存の曲・音源・サンプルは不使用、seed 固定）。OP カードの終わりから一定の音量（−16 dB）で鳴る | background music | `music/marimba_bgm.py`、`out/music/bgm_marimba.wav`、`assemble.py --bgm` |
| 時間刻み | 物理の 1 ステップ。施工中 0.005 s、以後 0.001 s | physics timestep | `--dt-build`、`--dt-action` |
| 制御周期 | 推論の間隔。パッカン 0.02 s、跳跳 0.005 s（ダンス 0.02 s） | control period | `MD_CONTROL_DT`、`control_dt` |

## 11. 評価の用語

| 呼び名 | 意味 | 英語 | 出所 |
|---|---|---|---|
| 渡り切り | パッカンが北側の床で立っている（`stage == north` かつ立位） | crossed | `crab_help.py` `Helpers.crossed`、`crossing_rate`（`eval_summary.json`） |
| 天面到達 | 押し上げなどで天面に乗った | reached the landing | `landing_rate`（`eval_summary.json`） |
| 無駄な手 | 報酬 v2.1 で −1 を数える手（下の注） | wasted move | `manager2_env.py` の `step`（`wasted`）、`REWARD` |
| 転倒 | パッカンの傾きが 60° を超えた | fall | `v7_full.py` `Duck.control`、`crab_help.check_seated_fall` |
| コース破損 | 設置済み部材が 4 cm を超えて動いた（失敗、−10） | course damaged | `manager2_env.py` `COURSE_TOLERANCE = 0.04`、`REWARD["course_damaged"]` |
| 同一シード評価 | 全方式を同じ 30 シード（5000〜5029）・同じ開始場面で評価する | shared-seed evaluation | `manager2_train.py eval --seed0 5000` |
| 評価 v4 | 新コース（継ぎ目 1 cm）・エピソード独立・決定的方策での同一シード評価 | evaluation v4 | `out/manager_runs/comparison_v4.md` |
| 2×2 帰属 | 固定ルールと方策の成否を 4 象限に分け、判断の失敗とスキルの失敗を切り分ける | 2×2 attribution | 同上「失敗の帰属」 |
| 判断の失敗 | ルールは渡ったが方策は失敗した話 | decision failure | 同上 |
| スキルの失敗 | 両方失敗した話（手の実行側の限界） | skill failure | 同上 |
| 固定ルール／PPO／Q 表／ランダム | 支配人 AI の 4 方式（PPO は SB3、Q 表は表形式 Q 学習） | rule / PPO / tabular Q / random | `crab_help.rule_action`、`manager2_train.py`、`manager2_tabq.py` |
| 報酬 v2.1／v2.2 | 学習の報酬の版。v2.2 は `still_down` で終わる `SEAT`／`STANDUP` も無駄な手に数える（学習のみ、評価は v2.1） | reward v2.1 / v2.2 | `manager2_env.py` `REWARD`、`REWARD_VERSIONS` |

注：無駄な手に数えるのは次の 3 つ。`PUSH`／`BACK_OFF`／`STANDUP`／`WALK_ON` が `nothing` で終わる、どの手でも `stalled`／`slipped` で終わる、
座席で正しく座っているのに `SEAT` を呼ぶ。パッカンが転んでおらず北側の床にもいないのに `WAIT` を選ぶと、同じ `wasted` に 0.5 を足す（報酬 −0.5、`wait_idle`）。

## 12. 版の呼び名

動画と評価の版は条件名で呼ぶ。ファイル名の `takeNN` は固有名で、本文の呼び名との対応はこの表のとおり。

| 呼び名 | 条件 | 英語 | ファイル・出所 |
|---|---|---|---|
| 提出動画 | 講座の OP カード＋自己紹介＋本編＋講座の ED カード、BGM つき、2:58.4 | submitted video | `assemble.py` の出力（講座の素材を含むので同梱しない） |
| 本編（固定ルール） | 固定ルールの支配人、輪の万歳、施工・仲間を呼んで戻る区間・輪へ集まる区間は 4 倍速、省略なし、END の後は 1 s、支配人の帯つき、2:37 | main video (rule) | `out/3body_arena_v7_take57.mp4`、`out/v7_full_report_take57.json` |
| 以前の 2:47 版 | 本編と物理が同一（`state_digest` 一致）。施工 4 倍速・以後 2 倍速・省略なし、帯なし、2:47。比較の基準 | earlier 2:47 cut | `out/3body_arena_v7_take51.mp4`、`out/v7_full_report_take51.json` |
| PPO 版 | PPO v2.2（`--manager ppo --run ppo2_v22`）、以前の 2:47 版と同じ速度設定、2:45 | PPO run | `out/3body_arena_v7_take52.mp4`、`out/v7_full_report_take52.json` |
| Q 表版 | 表形式 Q（`--manager tabq --run tabq2_small --jitter 0.4`）、2:46 | tabular-Q run | `out/3body_arena_v7_take53.mp4`、`out/v7_full_report_take53.json` |
| 追走版 | 固定ルール、結末 `--finale procession`、2:44 | procession run | `out/3body_arena_v7_take54.mp4`、`out/v7_full_report_take54.json` |
| 2 倍速・省略ありの版 | 以前の 2:47 版・PPO 版・Q 表版・追走版と同じ物理で、施工も 2 倍速、空荷走行 2 か所を省略 | 2x render with jump cuts | `out/3body_arena_v7_take46.mp4`〜`out/3body_arena_v7_take49.mp4`（`state_digest` が一致） |
| 評価 v4（新コース・30 シード） | 継ぎ目 1 cm、エピソード独立、決定的方策、シード 5000〜5029 | evaluation v4 | `out/manager_runs/comparison_v4.md` |
| 旧コース（継ぎ目 5 cm） | course-builder の `INSTALLATION_GAP` を 0.05 m から 0.01 m にする前の施工（変更は commit `ea5b4e7`） | old course (5 cm seam) | 旧舞台 `out/v6_stage_built_gap5cm.xml` |
| 評価 v2（エピソード非独立） | エピソード間で `MjData` を持ち越していた時期の評価 | evaluation v2 | `out/manager_runs/comparison_v2.md` |

長さは各報告 JSON の `video_silent.seconds`（本編 157.3、以前の 2:47 版 167.0、PPO 版 165.2、Q 表版 166.3、追走版 163.7 s）、提出動画の長さは `assemble.py` の印字の `total_s`（178.41 s）。
版ごとの物理同一の確認は `docs/physics_integration.md` の 8 節。
