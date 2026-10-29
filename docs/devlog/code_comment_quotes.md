# コードのコメント・docstring・help の置換記録

本書は、読者向けに書き直したコードのコメント・docstring・argparse help について、置換前の原文を保存する開発記録である。
対象はリポジトリ直下の `*.py`、`analysis/*.py`、`archive/*.py`。コードの動作に関わる行は変えていない（唯一の例外は後述の `RUNS` の相対パス化）。
原文の呼び名・日付・引用はそのまま写してあり、読者向け文書の文体規則の対象外である。

## 置換の方針

置換は次の規則で行った。番号は本書の表の読み方のためのもので、コード側には印を付けていない。

| 規則 | 原文の型 | 置換後 |
|---|---|---|
| 1 | ハンドル名つきの指示（「ゆうころ 10/28 昼: 『…』」型） | 「requirement:」「design decision:」で始まる仕様文（何をするか・既定値） |
| 2 | 日付・時間帯（10/27、10/28 noon、01:40 など） | 削除。必要なら「debug run」「smoke test」「earlier render」と場面だけ残す |
| 3 | take 番号（take 5、takes 9-33 など） | 条件名（「the push ending」「the first form of the procession finale」「an earlier render」） |
| 4 | 開発環境の呼び方（`<jumper venv python>`） | `python`（リポジトリルートで実行、archive/ は `python archive/…`） |
| 5 | 移動したファイルへの参照（`HANDOVER.md`、`v7_test_fork.py`） | 移動先のパス（`docs/devlog/HANDOVER.md`、`archive/v7_test_fork.py`） |
| 6 | 作品名・社内ツール名（"Island Master"、Notion） | 「the manager AI」「the v6 plan」 |
| 7 | 事実の誤記 | `crab_help.py` の観測次元 45 → 46、`archive/manager_env.py` の 32 → 35（どちらも `OBS_DIM` の内訳を併記）、`v7_test_face.py` の表情の数 7 → 11（`crab_face.EXPRESSIONS`）と顔モニターの位置 左下 → 右上（`Captioner.draw`） |
| 8 | 配布されないファイルへの参照（`jumper/out/` の下の自作の道具） | パスを書かず、由来だけを残す（「an earlier face-display tool by the same author」） |

コード側で動作に関わる変更は 1 か所の型だけである：`analysis/after_push_fail.py` と `analysis/fallen_value.py` の `RUNS` を、
ローカルの絶対パスから `Path(__file__).resolve().parents[1] / "out" / "manager_runs"` に直した（同じディレクトリを指す）。
また `v6_robots.py` の先頭 docstring に、v6 時代の記述であり、v7 は `build_arena()` と補助関数だけを使い、`v7_full.official_md_servos()` で XML の公式サーボ値に戻して外力なしで動く旨の注記を足した。
`v6_phase4_full.py` の先頭 docstring には、演出の補助（外力）つきの v6 版であり、提出の筋書き `v7_full.py` はここから `ArenaSim` と `PHASE_TEXT` だけを import して外力を使わない旨の注記を足した。

## 置換しなかったもの

- 動画に描き込まれる文字列：タイトル「支配人AI〈アイランドマスター〉…」（`manager2_env.py:160`、`v7_full.py:745`、`v7_test_face.py:55`、`archive/manager_env.py:182`）、
  `crab_help.py` の定型セリフ `LINES`（8 本）、出来事ログの文言。提出動画と同じ描画を保つため、表示文字列は変えていない。
- `v6_common.py:45-47` の Windows フォント候補のパス：フォント探索のコードであり、OS 依存の注記は `docs/reproduce.md` に置く。
- `v7_full.py` の `--build-speed`（help と実装）：別の作業で追加された行で、本書の表には含めない。
  該当は `v7_full.py:470-475`（help）、`479-481`（引数の検査）、`522`（標本化の数え）、`846`（右下の倍率表示）、`1685-1689`（フレームの間引き）。
  help の参照先だけは直した：毎フレームの forward が物理の経路に入る話は `docs/devlog/HANDOVER.md` の §0b（ジャンプカットの罠）にあるため、「section 4」を「section 0b」にした。
- ファイル名の中の take 番号（`--tag` の例 `_take51`、`out/v7_full_report_take51.json`）：固有名として残す。
- `archive/*.py` の `sys.path.insert(...)`・`BASE`・`OUT_DIR` の行（`# archive/:` の注記つき）と、それに伴って足した `import sys`・`from pathlib import Path`：
  archive/ への移動に伴う別作業のコード変更で、本書の表には含めない。

## 検証

- 対象ファイル全部を `python -m py_compile` に通し、`python v7_full.py --help` と `python manager2_report.py --help` が終了コード 0 で通ることを確認した。
- `git diff -U0 -- "*.py"` を読み、変更行が文字列・コメント・docstring・help（と上記 `RUNS` 2 行、`--build-speed` の別作業分）だけであることを確認した。
- 同じことを構文木でも確かめた：変更前（index）と変更後の各ファイルを `ast` で読み、docstring と `help=` の値を除いて比べると、
  差が出るのは `RUNS` の 2 ファイル、archive/ の `sys.path`・`BASE`・`OUT_DIR` の行、`v7_full.py` の `--build-speed` の行だけだった。
- 表の全行について、「原文」が diff の削除行と、「置換後」が追加行と 1 文字ずつ一致することをスクリプトで照合した（行頭の空白は除く）。
- 残存チェック：`grep` で「ゆうころ」「島」「オルティス」「ファーブル」「ヴェルティ」「おるてぃーず」「Notion」「D:\\」「HANDOVER.md（docs/devlog/ 以外）」「<jumper venv python>」、
  日付（10/27 など）・時間帯（noon、morning など）・take 番号（ファイル名の中を除く）が `*.py`・`analysis/*.py`・`archive/*.py` に残っていないことを確認した。

## 表の読み方

- 「file:行」は置換後（現在の作業ツリー）の行番号。複数行の塊は「開始-終了」。
- 原文・置換後は行頭の空白を省き、複数行は `<br>` で区切った。`<`・`>`・`|` はそのまま表示するために置き換えてある。
- 原文は 1 文字も直していない（誤記・英日混在もそのまま）。原文を省かずに写すため、表の行は読者向け文書の 1 行 200 字の目安を超える。
- 置換後の文言も作業時点のもので、その後に別の作業で変わった行は現在のコードが正となる。


## リポジトリ直下と analysis/ の置換

### analysis/after_push_fail.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/after_push_fail.py:19 | RUNS = Path(r"D:\IslandMaster\mujoco_3body\out\manager_runs") | RUNS = Path(__file__).resolve().parents[1] / "out" / "manager_runs" |

### analysis/face_check.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/face_check.py:16 | # the jump-cut notes (takes 34-) are about the video, not the physics: left out of the comparison | # the jump-cut notes are about the video, not the physics: left out of the comparison |

### analysis/face_sheet.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/face_sheet.py:1-2 | """The 11 faces as they appear in the video, with their names and the situations that bring them out (report figure 6,<br>ゆうころ 10/28 夜).  Renders each expression through the face camera at twice the monitor's size and lays them out in | """The 11 faces as they appear in the video, with their names and the situations that bring them out (report<br>figure 6).  Renders each expression through the face camera at twice the monitor's size and lays them out in |

### analysis/face_value.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/face_value.py:1 | """Is the PPO v2.2 critic's V(s) a usable mood for the crab?  (crab_face.MoodAI, ゆうころ 10/28 夜) | """Is the PPO v2.2 critic's V(s) a usable mood for the crab?  (crab_face.MoodAI; the first design, not adopted) |

### analysis/fallen_value.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/fallen_value.py:13 | RUNS = Path(r"D:\IslandMaster\mujoco_3body\out\manager_runs") | RUNS = Path(__file__).resolve().parents[1] / "out" / "manager_runs" |

### analysis/mood_data.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/mood_data.py:1 | """Training data for the crab's mood net (crab_face.MoodAI, ゆうころ 10/28 夜「本物の推論で 2 つの AI」). | """Training data for the crab's mood net (crab_face.MoodAI; requirement: two AIs doing real inference in the video). |

### analysis/mood_train.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| analysis/mood_train.py:2-3 | end - p_success / p_stall / p_fall / p_nothing - and whether the duck gets across (crab_face.MoodAI; ゆうころ<br>10/28 夜「本物の推論で 2 つの AI」「複数の確率と計測値から表情を組み立てる」). | end - p_success / p_stall / p_fall / p_nothing - and whether the duck gets across (crab_face.MoodAI; requirement:<br>two AIs doing real inference in the video, the face composed from several probabilities and measured values). |

### crab_face.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| crab_face.py:3-7 | ゆうころ 10/28 夕〜夜:「カニの表情を AI 管理できたりする？」→ a table keyed by the manager's action (takes 30-37)<br>→「本物の推論で 2 つの AI を走らせるように」→ a mood net beside the manager (takes 38-41)<br>→「複数の確率と計測値から表情を組み立てるものを精密に設計したい」→ this version (take 42-): the face is composed from<br>the mood net's four outcome probabilities and the crossing estimate, and from measured effort, contact, progress<br>and events, by the priority rules below.  The monitor shows the values that decide the face. | Design history: the first version chose the face from a table keyed by the manager's action; the second ran a mood<br>net beside the manager (requirement: two AIs doing real inference in the video); this version (requirement: compose<br>the expression precisely from several probabilities and measured values) builds the face from the mood net's four<br>outcome probabilities and the crossing estimate, and from measured effort, contact, progress and events, by the<br>priority rules below.  The monitor shows the values that decide the face. |
| crab_face.py:9 | What is official and what is ours | What is official and what this project adds |
| crab_face.py:13-15 | * This module is the island's.  The screen derives from jumper/out/face_tools/face_display.py (10/11, the lesson<br>videos); the pictures are drawn with PIL; the sparkle borrows the official animation's four-pointed star. | * This module is the project's own work.  The screen derives from an earlier face-display tool by the same author<br>(made for lesson videos, not distributed); the pictures are drawn with PIL; the sparkle borrows the official<br>animation's four-pointed star. |
| crab_face.py:81 | HOLD = 0.5                          # s a face stays at least (ゆうころ: 0.5 秒以上保つ) | HOLD = 0.5                          # s a face stays at least (requirement: a face is held at least 0.5 s) |
| crab_face.py:89 | PUSH_SWEAT_S = 5.0                  # s of pushing in contact after which the face sweats (ゆうころ) | PUSH_SWEAT_S = 5.0                  # s of pushing in contact after which the face sweats (requirement) |
| crab_face.py:91 | # see HANDOVER; the duck weighs about 15 N) | # see docs/devlog/HANDOVER.md; the duck weighs about 15 N) |
| crab_face.py:444 | fourth item is what the monitor's top line shows (ゆうころ: every change of face names the values behind it).""" | fourth item is what the monitor's top line shows (requirement: every change of face names the values behind it).""" |

### crab_help.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| crab_help.py:4-5 | ゆうころ (2026-10-28): the bulldozer must not handle the duck (lifting by the neck could break it);<br>the crab helps instead - "a beautiful friendship".  Experiment v7_test_crab_push.py (same night): | Requirement: the bulldozer must not handle the duck (lifting it by the neck could break it); the<br>crab helps instead.  Experiment v7_test_crab_push.py: |
| crab_help.py:42 | # the west side and dropped 0.44 m (headless take-6 test, 10/28) | # the west side and dropped 0.44 m (headless test of an early render) |
| crab_help.py:48 | # before it, the duck toppled at the lip in 20/20 pushes on 10/28 (its seated | # before it, the duck toppled at the lip in 20/20 pushes (its seated |
| crab_help.py:52 | # the two deck pieces (4 cm gap at y +0.02..+0.06) was tried on 10/28: the crab | # the two deck pieces (4 cm gap at y +0.02..+0.06) was tried: the crab |
| crab_help.py:59 | # 6-seed sweep 10/28, 0.2 m/s crossed 3/6, 0.3 m/s 4/6) | # 6-seed sweep: 0.2 m/s crossed 3/6, 0.3 m/s 4/6) |
| crab_help.py:156-158 | """Seated on the line anywhere from the seat to just past the ramp's lip: close enough for a push.  (Take 13,<br>10/28: re-seated 2 cm outside SEAT_TOL at y -2.01, the rule asked for SEAT seven more times - the skill reports<br>'seated' wherever the duck sits down - until the time ran out.)""" | """Seated on the line anywhere from the seat to just past the ramp's lip: close enough for a push.  (In one<br>render the duck re-seated 2 cm outside SEAT_TOL at y -2.01 and the rule asked for SEAT seven more times - the<br>skill reports 'seated' wherever the duck sits down - until the time ran out.)""" |
| crab_help.py:255 | # tips at the ramp's toe (debug 10/28, seed 1000), so the re-seat aims tighter than the 4.6 deg before. | # tips at the ramp's toe (debug run, seed 1000), so the re-seat aims tighter than the 4.6 deg before. |
| crab_help.py:290 | c.loco.set_command(0, 0, 0)                          # (a nudge of the fallen duck was tried on 10/28 noon and | c.loco.set_command(0, 0, 0)                          # (a nudge of the fallen duck was tried and |
| crab_help.py:312 | # the lane while the duck sat 3 cm off it drifted the duck sideways and tipped it at the toe (debug 10/28) | # the lane while the duck sat 3 cm off it drifted the duck sideways and tipped it at the toe (debug run) |
| crab_help.py:337 | # speed beyond 0.4 rad of bearing error) and the push stalls (smoke 10/28, seeds 1000/1002). | # speed beyond 0.4 rad of bearing error) and the push stalls (smoke tests, seeds 1000/1002). |
| crab_help.py:363 | # (experiment 10/28, off by default: a stop-and-re-approach at the lip did not save a push that had | # (experiment, off by default: a stop-and-re-approach at the lip did not save a push that had |
| crab_help.py:379 | # toppled the seated duck on the landing in another, 10/28; the push ends at the landing's edge) | # toppled the seated duck on the landing in another; the push ends at the landing's edge) |
| crab_help.py:382 | # pieces stand 4 cm apart there (raycast 10/28: floor at y +0.02..+0.06) and a walking duck's foot | # pieces stand 4 cm apart there (raycast: floor at y +0.02..+0.06) and a walking duck's foot |
| crab_help.py:412 | """NOT IN USE - an experiment of 10/28 noon (ゆうころ「固定ルール、カニを近くに伴走させようか」), kept as a record. | """NOT IN USE - an experiment (idea: the crab escorts the duck closely and nudges it when it falls), kept as a record. |
| crab_help.py:554-555 | """45 floats.  `book` carries the bookkeeping: last_result, last_action, pushes, t0_episode, course_damage,<br>course_tolerance.""" | """46 floats (OBS_DIM = 3 + 2 + 4 + 2 + 6 stages + 7 + 13 results + 6 actions + 3).  `book` carries the<br>bookkeeping: last_result, last_action, pushes, t0_episode, course_damage, course_tolerance.""" |
| crab_help.py:621-622 | RULE_NEAR_LIP = True               # the 10/28 noon addition to the rule (take 13); False reproduces the morning's rule<br># (baselines_v2) for a like-for-like check of the evaluation environment | RULE_NEAR_LIP = True               # a later addition to the rule (push a duck seated anywhere up to the lip); False<br># reproduces the earlier rule (baselines_v2) for a like-for-like check of the environment |

### manager2_env.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| manager2_env.py:4 | ゆうころ (2026-10-27/28): the manager AI ("Island Master") decides what to do next when things do not | Requirement: the manager AI decides what to do next when things do not |
| manager2_env.py:46 | # (10/28 01:40: "wasted" now also covers a skill that ends stalled / slipped - reward v2.1; ppo2_small and | # (reward v2.1: "wasted" also covers a skill that ends stalled / slipped; ppo2_small and |
| manager2_env.py:48 | # reward v2.2 (10/28 08:30, after take 8 and the ppo2_medium2 evaluation): a SEAT / STANDUP that ends "still_down" | # reward v2.2 (after the ppo2_medium2 evaluation): a SEAT / STANDUP that ends "still_down" |
| manager2_env.py:51-53 | #  so PPO never learned to make room first (BACK_OFF after a fall 3/10 in the eval, flat through 4.9k decisions of<br>#  continued training).  Training-only: the shared-seed evaluations keep v2.1 so their returns stay comparable. | #  so PPO never learned to make room first (BACK_OFF after a fall 3/10 in the eval; still 13/52 at the 4.9k-decision<br>#  check of the continued training ppo2_medium3, docs/devlog/MANAGER_DESIGN.md section 7.7, stopped at +7.5k).<br>#  Training-only: the shared-seed evaluations keep v2.1 so their returns stay comparable. |
| manager2_env.py:59-60 | # ramp_fallen (10/28 08:30): the duck lying on the up-ramp with the crab against it from below - the state a push<br># that toppled it leaves behind (take 8, 3:05).  The placed toe_fallen + touching start did not reproduce it: there | # ramp_fallen: the duck lying on the up-ramp with the crab against it from below - the state a push<br># that toppled it leaves behind (seen in an early render).  The placed toe_fallen + touching start did not reproduce it: there |
| manager2_env.py:223 | # a full MjData reset first (10/28 noon): restoring only qpos/qvel/ctrl/act left the solver's warm start and | # a full MjData reset first: restoring only qpos/qvel/ctrl/act left the solver's warm start and |
| manager2_env.py:305 | # robots a metre (debug 10/28: duck fallen on the far ramp, crab on the floor beside the course) | # robots a metre (debug run: duck fallen on the far ramp, crab on the floor beside the course) |
| manager2_env.py:312 | # every push then toppled the duck at the ramp's lip (sweeps 10/28: 0/14 vs the experiment's 2/2) | # every push then toppled the duck at the ramp's lip (sweeps: 0/14 vs the experiment's 2/2) |
| manager2_env.py:390 | # run of 10/28 repeated it 24 times at -0.9 each (time only) | # run (before v2.1) repeated it 24 times at -0.9 each (time only) |

### manager2_report.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| manager2_report.py:3 | &lt;jumper venv python&gt; manager2_report.py --runs ppo2_small baselines_v2 tabq2_small | python manager2_report.py --runs ppo2_small baselines_v2 tabq2_small |

### manager2_tabq.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| manager2_tabq.py:3-4 | &lt;jumper venv python&gt; manager2_tabq.py train --episodes 120 --run tabq2_small<br>&lt;jumper venv python&gt; manager2_tabq.py eval  --run tabq2_small --episodes 30 --seed0 5000 | python manager2_tabq.py train --episodes 120 --run tabq2_small<br>python manager2_tabq.py eval  --run tabq2_small --episodes 30 --seed0 5000 |

### manager2_train.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| manager2_train.py:3-5 | &lt;jumper venv python&gt; manager2_train.py train --envs 12 --steps 3000 --run ppo2_small<br>&lt;jumper venv python&gt; manager2_train.py eval  --run ppo2_small --episodes 30<br>&lt;jumper venv python&gt; manager2_train.py demo  --run ppo2_small --policy ppo --seed 5003 | python manager2_train.py train --envs 12 --steps 3000 --run ppo2_small<br>python manager2_train.py eval  --run ppo2_small --episodes 30<br>python manager2_train.py demo  --run ppo2_small --policy ppo --seed 5003 |
| manager2_train.py:66-67 | # (10/28: ppo2_medium3 was stopped at 4.9k of 12k decisions and its weights were lost - until here the<br># model was only saved at the end; intermediate policies can now also be evaluated) | # (the continued-training run ppo2_medium3 was interrupted part-way and its weights were lost - until here<br># the model was only saved at the end; intermediate policies can now also be evaluated) |
| manager2_train.py:137 | crab_help.RULE_NEAR_LIP = False                    # the morning's rule, for a like-for-like check | crab_help.RULE_NEAR_LIP = False                    # the earlier rule (baselines_v2), for a like-for-like check |

### v6_common.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v6_common.py:3-5 | v1-v5 tried the whole scenario in one script; v6 follows HANDOVER.md section 8<br>and builds the video in phases that each export their own MP4. | v1-v5 tried the whole scenario in one script; v6 follows docs/devlog/HANDOVER.md section 8<br>and builds the video in phases that each export their own MP4.  v7_full.py (the submitted<br>story) and the learning environment import the helpers from here. |
| v6_common.py:91 | same row as the caption box (ゆうころ 10/28 夜: 「一番上の文字情報の枠と同じ列に、二段じゃなく一段で」).  The | same row as the caption box (requirement: one row together with the caption box, not a second row).  The |
| v6_common.py:261 | # ── Built-stage snapshot (Notion phase A0) ─────────────────────────────── | # ── Built-stage snapshot (phase A0 of the v6 plan) ────────────────────── |

### v6_phase4_full.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v6_phase4_full.py:3-5 | （追加のみ、原文なし） | Note: this is the v6 version with demo aids (external forces).  The submitted story is v7_full.py,<br>which imports only ArenaSim and PHASE_TEXT from here and uses no external force.<br>（空行） |
| v6_phase4_full.py:7 | MD wanders in the free area beyond the course (ゆうころ: 「作っている最中もうろちょろ」). | MD wanders in the free area beyond the course (requirement: it wanders while the course is built). |
| v6_phase4_full.py:9 | quacking (「がーがー言いながら後をついていって」). | quacking (requirement: it follows BZ while quacking). |

### v6_robots.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v6_robots.py:3-8 | Honesty notes for the report<br>---------------------------- | Note: the notes below describe the v6 phases (Phase 2 / 3 are in archive/).  v7 (v7_full.py, manager2_env.py) uses only<br>build_arena() and the helpers from here; it restores the XML's official Microduck servo values with<br>v7_full.official_md_servos() and applies no external force (MicroduckCtrl / JumperCtrl are v6-only).<br>（空行）<br>Honesty notes for the report (v6)<br>--------------------------------- |
| v6_robots.py:42 | # ── Microduck: idealised servo gains for the demo ──────────────────────── | # ── Microduck: idealised servo gains for the v6 demo (v7 restores the XML values, see official_md_servos) ── |

### v7_full.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_full.py:8 | Stages (ゆうころ 10/27 夜の筋書き) | Stages (the story, in order) |
| v7_full.py:16-27 | LIFT       BZ drives back around the course with JP trailing it, and JP goes round to the duck's<br>south side and cheers it with the official dance policy while BZ works the fork:<br>--ending push  (take 5) from the duck's side, fork at 6 cm: tips the seated duck over,<br>velstand gets it back on its feet by itself. | RETURN     (--ending crab, the default) JP comes back round the east side of the course to the lane<br>behind the seated duck.  BZ never touches the duck.<br>RESCUE     the manager AI (--manager rule / ppo / tabq) picks the next skill from crab_help.py -<br>WAIT / SEAT / PUSH / BACK_OFF / STANDUP / WALK_ON - until the duck stands on the floor<br>north of the course; the mood net (--face-ai mood) drives JP's face monitor.<br>CELEBRATE  the three gather at the goal (--finale circle: a circle facing the centre, BZ pumps its<br>fork, MD squats and shakes its head, JP dances and holds its claws up).<br>LIFT       (--ending push / lift only: early endings, kept as options) BZ drives back around the<br>course with JP trailing it, and JP goes round to the duck's south side and cheers it with<br>the official dance policy while BZ works the fork:<br>--ending push  from the duck's side, fork at 6 cm: tips the seated duck over, velstand<br>gets it back on its feet by itself. |
| v7_full.py:30-31 | with both tines under its hips - a 2 cm window (see HANDOVER.md), so<br>whether it lifts, shoves or misses is decided by the physics of the take. | with both tines under its hips - a 2 cm window (see docs/devlog/HANDOVER.md),<br>so whether it lifts, shoves or misses is decided by the physics of the render. |
| v7_full.py:33-35 | &lt;jumper venv python&gt; v7_full.py --test            # no render<br>&lt;jumper venv python&gt; v7_full.py --preview DIR     # stills<br>&lt;jumper venv python&gt; v7_full.py                   # -&gt; out/3body_arena_v7.mp4 (+ chirps) | python v7_full.py --test            # no render<br>python v7_full.py --preview DIR     # stills<br>python v7_full.py                   # -&gt; out/3body_arena_v7.mp4 (+ chirps) |
| v7_full.py:78-81 | # video speed per stage.  ゆうころ 10/28 昼: the submission rules allow up to 2x (3x would need the organisers' OK), so<br># nothing above 2x any more (takes 6-10 ran the construction at 4x); the celebration's dance itself plays at 1x | # video speed per stage.  Requirement: the submission rules cap the playback speed (2x when the story was planned,<br># later raised to 8x), so the story from the ramp attempt on plays at 2x and the celebration's dance at 1x.  The<br># construction alone can be shown faster with --build-speed (a multiple of 2, together with --no-cuts; the submitted<br># video uses 4): frames are still sampled at 2x and only every n-th one is written, so the physics path is unchanged |
| v7_full.py:90-91 | # ── the goal celebration (ゆうころ 10/28 朝: 「坂を降り始めたらカニも後を追いかけて、ゴールで BZ もアームを上げて、<br>#    パッカンもパタパタして、カニも腕を上げるダンス」) ── | # ── the goal celebration (requirement: once the duck starts down the far ramp the crab follows it, and at the goal<br>#    BZ raises its fork, the duck flaps and the crab dances with its arms up) ── |
| v7_full.py:100 | # ── jump cuts (ゆうころ 10/28 夕: the submission must be 1-3 min including titles, at most 2x; the story is 3:30 at 2x, | # ── jump cuts (requirement when they were made: 1-3 min including titles, at most 2x; the story is 3:30 at 2x, |
| v7_full.py:103 | #    sim clock jumps.  Default on; --no-cuts for the full record, --cut START:END:LABEL for others) ── | #    sim clock jumps.  Default on; --no-cuts for the full record (used by the submitted video), --cut for others) ── |
| v7_full.py:107-110 | # ── the circle (ゆうころ 10/28 昼: 「みんなで顔を合わせようか、円になって中央を向き、ブルドーザーはアームを上下、アヒルは<br>#    手がなかったので屈伸しながら首を振る」) ──<br># ── the crab cheers the duck's ramp attempts (ゆうころ 10/28 昼: 「カニ、ぱっかんがチャレンジしているとき万歳で踊って応援してほしい」) ── | # ── the circle (requirement: the three face each other in a circle round a centre; BZ pumps its fork up and down,<br>#    the duck, having no arms, squats while shaking its head, the crab dances) ──<br># ── the crab cheers the duck's ramp attempts (requirement: while the duck tries the ramp, the crab dances with its<br>#    claws up to cheer it on) ── |
| v7_full.py:160-162 | pump_floor: the lowest the fork goes while pumping.  0.2 m when BZ's back is to the others (takes 9-33); 0.38 m<br>once BZ has turned round to face them (take 37-, ゆうころ 10/28 夕): the duck then stands under the raised tines,<br>0.9 m in front, and its head is 0.23 m high.""" | pump_floor: the lowest the fork goes while pumping.  0.2 m when BZ's back is to the others (the first form of the<br>procession finale); 0.38 m once BZ has turned round to face them (design decision: BZ faces the others at the<br>goal): the duck then stands under the raised tines, 0.9 m in front, and its head is 0.23 m high.""" |
| v7_full.py:221 | MASTER_GAIN = 0.45          # ゆうころ: 音は小さめで | MASTER_GAIN = 0.45          # requirement: the voices stay quiet |
| v7_full.py:429 | ap.add_argument("--tag", default="", help="suffix for the output names, e.g. _take5 (keeps earlier takes)") | ap.add_argument("--tag", default="", help="suffix for the output names, e.g. _take51 (earlier outputs are kept)") |
| v7_full.py:431-435 | help="push: take 5 - BZ comes at the seated duck's side, the fork tips it over, it gets up by itself; "<br>"lift: the duck turns its back and BZ docks behind it to scoop it up (a 2 cm window - see HANDOVER); "<br>"crab (take 6, ゆうころ 10/28: BZ must not handle the duck): the crab comes back and the manager AI "<br>"chooses the skills (crab_help.py) that get the duck across - seat, push, back off, stand, walk") | help="crab (default; requirement: BZ must not handle the duck): the crab comes back and the manager AI "<br>"chooses the skills (crab_help.py) that get the duck across - seat, push, back off, stand, walk; "<br>"push (early ending, kept): BZ comes at the seated duck's side, the fork tips it over, it gets up "<br>"by itself; lift (early ending, kept): the duck turns its back and BZ docks behind it to scoop it "<br>"up (a 2 cm window, see docs/devlog/HANDOVER.md)") |
| v7_full.py:441 | help="circle (ゆうころ 10/28 昼, take 11-): the crab follows the duck down, BZ drives up and turns round, the three " | help="circle (default): the crab follows the duck down, BZ drives up and turns round, the three " |
| v7_full.py:443-444 | "procession (take 9/10): the crab follows the duck down and the three cheer where the duck stopped; "<br>"around (take 6/7): the crab backs down the up-ramp and walks round the course to the duck") | "procession: the crab follows the duck down and the three cheer where the duck stopped; "<br>"around: the crab backs down the up-ramp and walks round the course to the duck") |
| v7_full.py:446-449 | help="seconds added to where the crab's cheer dance starts in its recording (CHEER_DANCE_START). The only "<br>"purpose is to change the physics path of a rendered take: the rendered physics is deterministic "<br>"for given code, so a learned manager that fails on one path (take 17: the Q table re-seats "<br>"instead of backing off after a stalled push) can be tried on another. Say which jitter a take used") | help="seconds added to where the crab's cheer dance starts in its recording (CHEER_DANCE_START), default 0. "<br>"The only purpose is to change the physics path of a render: the physics is deterministic for given "<br>"code, so a learned manager that fails on one path can be tried on another. Record the jitter a "<br>"render used") |
| v7_full.py:451 | help="switch off the pre-positioning (ゆうころ 10/28 昼): by default an idle robot already walks to where its " | help="switch off the pre-positioning: by default an idle robot already walks to where its " |
| v7_full.py:456-459 | help="no face on the crab's display panel.  By default (ゆうころ 10/28 夕) the crab's expression is chosen from "<br>"the manager's action and its result (crab_face.py's table) and shown in the face monitor, an inset at "<br>"the bottom-left.  Render-only: the physics path is the same with and without it "<br>"(--test, out/v7_full_report_facecheck_{A,B}.json)") | help="no face on the crab's display panel.  By default the crab's expression is composed by crab_face.py "<br>"from the mood net's inference and measured values (--face-ai) and shown in the face monitor, an "<br>"inset beside the caption.  Render-only: the physics path is the same with and without it "<br>"(--test, out/v7_full_report_facecheck_{A,B}.json, analysis/face_check.py)") |
| v7_full.py:461-464 | help="mood (ゆうころ 10/28 夜, take 38-): a second AI beside the manager - the mood net, out/manager_runs/mood_net - "<br>"infers every control step of the rescue whether the running move will end well, and its mood "<br>"(confident / neutral / worried) colours the crab's face; critic: the PPO v2.2 critic's V(s) instead "<br>"(the first attempt, a record); table: the expression table alone (takes 30-37)") | help="mood (default): a second AI beside the manager - the mood net, out/manager_runs/mood_net - "<br>"infers every control step of the rescue how the running move will end, and its outputs "<br>"together with measured values choose the crab's face; critic: the PPO v2.2 critic's V(s) instead "<br>"(the first design, kept as a record); table: the expression table alone (the earliest version)") |
| v7_full.py:651 | (The procession's BZ kept its back to the others in takes 9-33: ゆうころ 10/28 夕「後ろ向いてるよ」.)""" | (Design decision: in its first form the procession finale left BZ with its back to the others; it now turns.)""" |
| v7_full.py:774 | version skipped them and the construction took 4 s longer: the story then failed, take 34 first attempt).""" | version skipped them and the construction took 4 s longer: the story then failed).""" |
| v7_full.py:811 | # right, both in profile facing the centre (take 14's view from the east put the duck far behind the fork) | # right, both in profile facing the centre (a view from the east put the duck far behind the fork) |
| v7_full.py:831 | else:                                                       # take 5's shot, from the south-east | else:                                                       # the push ending's shot, from the south-east |
| v7_full.py:983 | # only once the duck has passed on its way to the ramp (take 13: their paths crossed, the duck fell twice) | # only once the duck has passed on its way to the ramp (in an earlier render their paths crossed and the duck fell twice) |
| v7_full.py:1015 | # pre-positioning (ゆうころ 10/28 昼): once the duck gives up, the crab walks to the foot of its lane and | # pre-positioning (design decision, see --no-prestage): once the duck gives up, the crab walks to the foot of its lane and |
| v7_full.py:1098 | # (x 1.50) once over the crest - takes 11/12 (10/28 noon) drifted to x 1.90 on the landing after the jump | # (x 1.50) once over the crest - earlier renders drifted to x 1.90 on the landing after the jump |
| v7_full.py:1114 | # (take 11: the straight way back from (2.33, -0.10) pressed it against the deck's side for 60 s) | # (in an earlier render the straight way back from (2.33, -0.10) pressed it against the deck's side for 60 s) |
| v7_full.py:1125 | climb["jumps"] = 1                                # the one showcase jump at the crest (ゆうころ) | climb["jumps"] = 1                                # the one showcase jump at the crest (requirement: one jump, shown) |
| v7_full.py:1181 | # pre-positioning (ゆうころ 10/28 昼): the crab starts back while the duck is still calling, and its route | # pre-positioning (design decision, see --no-prestage): the crab starts back while the duck is still calling, and its route |
| v7_full.py:1425 | # behind it: v7_test_fork.py lifts the seated duck cleanly only with both tines under its hips | # behind it: archive/v7_test_fork.py lifts the seated duck cleanly only with both tines under its hips |
| v7_full.py:1427-1428 | # hooks it at best and the set-down tips it.  ゆうころ 10/27: being lifted is the heart-warming ending. | # hooks it at best and the set-down tips it.  Design history: the lift was the first intended ending; it is<br># kept as an option but not used, because BZ must not handle the duck (--ending crab is the default). |
| v7_full.py:1476 | else:                                                   # "push" (take 5): at the seated duck's right side, from the east | else:                                                   # "push" ending: at the seated duck's right side, from the east |
| v7_full.py:1483 | # the crab comes back with BZ and cheers the duck with a dance (ゆうころ 10/27 深夜): | # the crab comes back with BZ and cheers the duck with a dance (lift / push endings): |
| v7_full.py:1549-1550 | # "push" ending (take 5): fork held ~6 cm up while sliding in from the side.  At floor level the<br># tines shove the seated duck along (v7_test_fork.py: pushed 0.3 m, no tip); at 6 cm they catch it | # "push" ending: fork held ~6 cm up while sliding in from the side.  At floor level the<br># tines shove the seated duck along (archive/v7_test_fork.py: pushed 0.3 m, no tip); at 6 cm they catch it |
| v7_full.py:1560 | # v7_test_fork.py from straight behind: both tines slide under the hips and lift the duck when | # archive/v7_test_fork.py from straight behind: both tines slide under the hips and lift the duck when |
| v7_full.py:1592 | sim.command(0.0, 0.0, 0.6 if gentle else 1.0)           # lift: gently to 0.30 m; push: to the top (take 5) | sim.command(0.0, 0.0, 0.6 if gentle else 1.0)           # lift: gently to 0.30 m; push: to the top |
| v7_full.py:1619 | sim.command(-0.25, 0.0, 0.0)                        # take 5 | sim.command(-0.25, 0.0, 0.0)                        # push ending |
| v7_full.py:1646 | # the course must survive the rescue (ゆうころ): report any part nudged beyond course-builder's 4 cm | # the course must survive the rescue (requirement): report any part nudged beyond course-builder's 4 cm |

### v7_policies.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_policies.py:273 | # Forward jump (ゆうころ 10/27): sweep every foot backward with the hip yaw J0 while | # Forward jump (this project's addition to the official jump): sweep every foot backward with the hip yaw J0 while |

### v7_progress_video.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_progress_video.py:8 | &lt;jumper venv python&gt; v7_progress_video.py   -&gt; out/v7_progress_physics_only.mp4 | python v7_progress_video.py   -&gt; out/v7_progress_physics_only.mp4 |

### v7_test_bz_drive.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_bz_drive.py:3 | &lt;jumper venv python&gt; v7_test_bz_drive.py          # forward with the fork low / high, then a turn on the spot | python v7_test_bz_drive.py          # forward with the fork low / high, then a turn on the spot |
| v7_test_bz_drive.py:45 | # (10/28 noon) from its post (1.55, 3.07) facing north BZ cannot drive on: with the fork raised its tines reach 1.38 m, | # from its post (1.55, 3.07) facing north BZ cannot drive on: with the fork raised its tines reach 1.38 m, |

### v7_test_cheer.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_cheer.py:1 | """Goal celebration test (ゆうころ 10/28 朝): the three at the goal after the crossing - BZ's fork up, the duck | """Goal celebration test: the three at the goal after the crossing - BZ's fork up, the duck |
| v7_test_cheer.py:5-6 | &lt;jumper venv python&gt; v7_test_cheer.py --video out\\v7_cheer_test.mp4     # the 13 s celebration, recorded<br>&lt;jumper venv python&gt; v7_test_cheer.py --dance-only --seconds 16         # the dance alone: claw heights, arm pose at the top | python v7_test_cheer.py --video out/v7_cheer_test.mp4     # the 13 s celebration, recorded<br>python v7_test_cheer.py --dance-only --seconds 16         # the dance alone: claw heights, arm pose at the top |
| v7_test_cheer.py:28 | ap.add_argument("--circle", action="store_true", help="the circle celebration (ゆうころ 10/28 昼): BZ pumps the fork, the duck squats") | ap.add_argument("--circle", action="store_true", help="the circle celebration: BZ pumps the fork, the duck squats, the crab dances") |
| v7_test_cheer.py:41 | # where take 6 left them: BZ parked north of the course facing north, the duck on the floor just past the far | # the positions after a crossing: BZ parked north of the course facing north, the duck on the floor just past the far |

### v7_test_collision.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_collision.py:6 | &lt;jumper venv python&gt; v7_test_collision.py [--sweep 1.2] [--jump-dist 0.55] [--preview DIR] | python v7_test_collision.py [--sweep 1.2] [--jump-dist 0.55] [--preview DIR] |

### v7_test_crab_push.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_crab_push.py:1-2 | """Can the crab push the duck up the 16-degree ramp?  (ゆうころ 10/28: the crab helps instead of the bulldozer -<br>"a beautiful friendship"; the bulldozer must not handle the duck, lifting by the neck could break it.) | """Can the crab push the duck up the 16-degree ramp?  (Requirement: the bulldozer must not handle the duck -<br>lifting it by the neck could break it - so the crab helps instead.) |
| v7_test_crab_push.py:4 | &lt;jumper venv python&gt; v7_test_crab_push.py [--crab-vx 0.3 0.5] [--seconds 60] [--video out/v7_crab_push.mp4] | python v7_test_crab_push.py [--crab-vx 0.3 0.5] [--seconds 60] [--video out/v7_crab_push.mp4] |
| v7_test_crab_push.py:81 | if seated:                                            # ゆうころ: the seated duck is pushed (low centre of mass) | if seated:                                            # design decision: the seated duck is pushed (low centre of mass) |
| v7_test_crab_push.py:193 | # there let it topple (run 10/28 01:xx, fell at y -0.82); keep the push steady until the landing | # there let it topple (one run fell at y -0.82); keep the push steady until the landing |

### v7_test_crest.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_crest.py:3 | &lt;jumper venv python&gt; v7_test_crest.py [--sweep 1.0] | python v7_test_crest.py [--sweep 1.0] |

### v7_test_dance.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_dance.py:3 | &lt;jumper venv python&gt; v7_test_dance.py [--seconds 30] [--start 0] [--dt 0.001] [--name dance_crab] | python v7_test_dance.py [--seconds 30] [--start 0] [--dt 0.001] [--name dance_crab] |

### v7_test_face.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_face.py:1-2 | """Smoke test of the crab's face (crab_face.py): the seven expressions on the display panel, seen from in front of the<br>crab by a story-style camera and by the face monitor (the inset at the bottom-left).  No physics is stepped. | """Smoke test of the crab's face (crab_face.py): the 11 expressions (crab_face.EXPRESSIONS) on the display panel, seen<br>from the front by a story-style camera and by the face monitor (top-right, beside the caption).  No physics is stepped. |
| v7_test_face.py:54 | # the story's widest caption (RESCUE), so the monitor goes below it; the smoke test also shows a jump-cut notice | # the story's widest caption (RESCUE) beside the monitor; the smoke test also shows a jump-cut notice |

### v7_test_fall_recovery.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_fall_recovery.py:7 | &lt;jumper venv python&gt; v7_test_fall_recovery.py | python v7_test_fall_recovery.py |

### v7_test_head_reach.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_head_reach.py:3 | &lt;jumper venv python&gt; v7_test_head_reach.py | python v7_test_head_reach.py |

### v7_test_jump.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_jump.py:3 | &lt;jumper venv python&gt; v7_test_jump.py [--preview DIR] | python v7_test_jump.py [--preview DIR] |

### v7_test_jump_forward.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_jump_forward.py:3 | &lt;jumper venv python&gt; v7_test_jump_forward.py | python v7_test_jump_forward.py |

### v7_test_jumper.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_jumper.py:3 | &lt;jumper venv python&gt; v7_test_jumper.py [--preview DIR] | python v7_test_jumper.py [--preview DIR] |

### v7_test_microduck.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_microduck.py:3 | &lt;jumper venv python&gt; v7_test_microduck.py [--dt 0.005] [--policy velstand.onnx] [--preview DIR] | python v7_test_microduck.py [--dt 0.005] [--policy velstand.onnx] [--preview DIR] |

### v7_test_nudge.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_nudge.py:1-3 | """The nudge (PUSH on a fallen duck, ゆうころ 10/28 昼): the duck lying across the landing's seam, the crab 0.6 m behind.<br>Does velstand get it up on its own in 4 s?  If not, does the nudge move it, and does velstand get it up afterwards?<br>Built stage; the robots are placed by teleport (test only). | """The nudge (PUSH on a fallen duck; an experiment, not adopted): the duck lying across the landing's seam, the crab<br>0.6 m behind.  Does velstand get it up on its own in 4 s?  If not, does the nudge move it, and does velstand get it<br>up afterwards?  Built stage; the robots are placed by teleport (test only). |
| v7_test_nudge.py:5 | &lt;jumper venv python&gt; v7_test_nudge.py [--video out\\v7_nudge_test.mp4] | python v7_test_nudge.py [--video out/v7_nudge_test.mp4] |

### v7_test_sitstand.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| v7_test_sitstand.py:3 | &lt;jumper venv python&gt; v7_test_sitstand.py [--preview DIR] | python v7_test_sitstand.py [--preview DIR] |

## archive/ の置換

archive/ のスクリプトは import されない履歴であり、本文の規則は同じだが実行例は `python archive/…` と書いた。

### archive/manager_env.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| archive/manager_env.py:3 | ゆうころ (2026-10-27): put a manager AI ("Island Master") that decides what to do next when the | Requirement: put a manager AI that decides what to do next when the |
| archive/manager_env.py:22 | 3 PUSH_SIDE  "別の方法にしよう — BZ、横から起こしてあげて"    take-5 method: at the duck's side, fork at | 3 PUSH_SIDE  "別の方法にしよう — BZ、横から起こしてあげて"    the push ending's method: at the duck's side, fork at |
| archive/manager_env.py:28 | Observation: 32 floats from the simulator (duck/BZ/crab pose and status, BZ's alignment to the | Observation: 35 floats (OBS_DIM = 16 + 3 + 8 results + 6 actions + 2) from the simulator (duck/BZ/crab pose and status, BZ's alignment to the |
| archive/manager_env.py:31 | Calibration facts (v7_test_fork.py and the offset sweep of 10/27): both tines go under the seated | Calibration facts (v7_test_fork.py and its offset sweep): both tines go under the seated |
| archive/manager_env.py:63 | # west = back to the east.  At -2.10 (10 cm from the edge, as in take 5) BZ's | # west = back to the east.  At -2.10 (10 cm from the edge, as in the push ending) BZ's |
| archive/manager_env.py:84 | # Reward (per decision).  The job is recovery; the lift is the outcome ゆうころ prefers, so it carries a | # Reward (per decision).  The job is recovery; the lift is the preferred outcome (requirement), so it carries a |
| archive/manager_env.py:86 | # The course is the whole point of the scene (ゆうころ: コースを壊さないようにしなきゃ): a slope part or block | # The course is the whole point of the scene (requirement: the course must not be damaged): a slope part or block |
| archive/manager_env.py:289 | # course-builder's block_2 sits at (4, -3): a BZ written on top of it explodes (debug 10/27).  Redraw. | # course-builder's block_2 sits at (4, -3): a BZ written on top of it explodes (debug run).  Redraw. |
| archive/manager_env.py:328 | """Safety stop (ゆうころ: コースを壊さない): True when the tine tips are inside, or about to enter, the | """Safety stop (requirement: the course must not be damaged): True when the tine tips are inside, or about to enter, the |
| archive/manager_env.py:339-340 | """ゆうころ: おろすときは下までおろさない、足がついたら止める - any duck foot touching the floor.""" | """Requirement: when setting the duck down, stop as soon as its feet touch the floor instead of lowering<br>the fork all the way - any duck foot touching the floor.""" |
| archive/manager_env.py:501 | # lower only until the duck's feet touch the floor (ゆうころ): set all the way down, the duck sits on | # lower only until the duck's feet touch the floor (requirement): set all the way down, the duck sits on |
| archive/manager_env.py:511 | # topple it onto the fork (smoke 10/27: 1.3 m, then stuck).  So the duck stands first: its feet | # topple it onto the fork (smoke test: 1.3 m, then stuck).  So the duck stands first: its feet |
| archive/manager_env.py:522 | # standing with a foot on a tine, the duck rides along when BZ reverses (smoke 10/27: carried | # standing with a foot on a tine, the duck rides along when BZ reverses (smoke test: carried |
| archive/manager_env.py:535 | free_t0 = self.t          # fallen onto / against the fork: tines 8 cm up, then reverse (experiment 10/27) | free_t0 = self.t          # fallen onto / against the fork: tines 8 cm up, then reverse (experiment) |
| archive/manager_env.py:567 | """Take 5's ending: come at the seated duck's right side, fork at 6 cm, tip it, back off.""" | """The push ending: come at the seated duck's right side, fork at 6 cm, tip it, back off.""" |
| archive/manager_env.py:573 | # the duck (ゆうころ: コースを壊さないようにしなきゃ; the first try from the south shoved up_1 by 9 cm). | # the duck (requirement: the course must not be damaged; the first try from the south shoved up_1 by 9 cm). |
| archive/manager_env.py:641 | # work (velstand needs clear floor) - raising the tines 8 cm and then reversing freed it (experiment 10/27) | # work (velstand needs clear floor) - raising the tines 8 cm and then reversing freed it (experiment) |

### archive/manager_tabq.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| archive/manager_tabq.py:3-4 | &lt;jumper venv python&gt; manager_tabq.py train --episodes 300 --run tabq_smoke<br>&lt;jumper venv python&gt; manager_tabq.py eval  --run tabq_smoke --episodes 20 --seed0 5000 | python archive/manager_tabq.py train --episodes 300 --run tabq_smoke<br>python archive/manager_tabq.py eval  --run tabq_smoke --episodes 20 --seed0 5000 |

### archive/manager_train.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| archive/manager_train.py:1 | """Train and evaluate the manager (Island Master) with Stable-Baselines3 PPO on ManagerEnv. | """Train and evaluate the manager AI (v1) with Stable-Baselines3 PPO on ManagerEnv. |
| archive/manager_train.py:3-4 | &lt;jumper venv python&gt; manager_train.py train --envs 8 --steps 1024 --run ppo_smoke<br>&lt;jumper venv python&gt; manager_train.py eval  --run ppo_smoke --episodes 30 | python archive/manager_train.py train --envs 8 --steps 1024 --run ppo_smoke<br>python archive/manager_train.py eval  --run ppo_smoke --episodes 30 |

### archive/v6_phase2_md_walk.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| archive/v6_phase2_md_walk.py:1 | """v6 Phase 2 - Microduck walks on the built stage (Notion phases A1 / A2 / B1). | """v6 Phase 2 - Microduck walks on the built stage (phases A1 / A2 / B1 of the v6 plan). |

### archive/v7_failures_video.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| archive/v7_failures_video.py:1 | """v7 failure footage (physics only) for ゆうころ to inspect: | """v7 failure footage (physics only), recorded for inspection: |
| archive/v7_failures_video.py:7 | &lt;jumper venv python&gt; v7_failures_video.py   -&gt; out/v7_failures_physics_only.mp4 | python archive/v7_failures_video.py   -&gt; out/v7_failures_physics_only.mp4 |

### archive/v7_test_fork.py

| file:行 | 原文 | 置換後 |
|---|---|---|
| archive/v7_test_fork.py:3 | &lt;jumper venv python&gt; v7_test_fork.py [--dy 0 0.1 0.2] [--lift 0 0.06] | python archive/v7_test_fork.py [--dy 0 0.1 0.2] [--lift 0 0.06] |
| archive/v7_test_fork.py:36 | mode 'lift': the gentle one (ゆうころ 10/27: lifting the duck is the heart-warming ending) - | mode 'lift': the gentle one (the lift was the first intended ending) - |
