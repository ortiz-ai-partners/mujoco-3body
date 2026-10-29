# archive/ — 採用しなかった設計と旧世代のスクリプト

本番のコード（`v7_full.py`、`manager2_*.py`、`crab_*.py`、`analysis/`）から import されない 12 本を保存している。
提出物の動作と再現手順には関係しない。開発の経緯を、コードと生成物で確かめられる形で残すためのフォルダである。
読者向けの説明は [../README.md](../README.md) と [../docs/](../docs/)、
経緯の原文は開発記録 [../docs/devlog/HANDOVER.md](../docs/devlog/HANDOVER.md) と [../docs/devlog/MANAGER_DESIGN.md](../docs/devlog/MANAGER_DESIGN.md) にある。

機体の呼び名は本文と同じ：ブルドーザー（BZ、自作 course-builder）、パッカン（Microduck, Pollen Robotics）、跳跳（Jumper, KingKong Robotics）。
コード中の識別子 `duck` はパッカン、`crab` は跳跳を指す。

## 採用しなかった理由（1 行ずつ）

- 外力版 v6 Phase 2〜3：姿勢と移動を胴体への外力（`xfrc_applied`）に頼り、各機体は自分のアクチュエータだけで動くという原則に反する。
- 支配人 v1：BZ のフォークでパッカンを扱う場面が前提で、安全上の設計判断でその手を禁止したため凍結した。
- フォーク持ち上げ：通しでは BZ の寄せの精度が持ち上げの窓に届かず、BZ がパッカンに触れる結末そのものも同じ設計判断で廃止した。
- 旧世代の描画 v3〜v5：跳跳の推進とパッカンの沈み込み防止を外力に頼り、v5 では坂も施工せずに静的な形状で置いた。施工を course-builder に任せる v6 に移行した。
- 初期の骨組み：3 体の結合（`MjSpec.attach`）と制御周期の試験。手順は `v6_robots.build_arena()` と本番の制御周期に引き継いだ。
- 失敗集動画：物理の事実を確かめるための確認用の収録。事実は本編の筋書きの前提になったが、動画は本編に使っていない。

## 位置づけ

- import されない：ルート直下と `analysis/` の全 `.py` の import 文を照合し、この 12 本を import するものが無いことを確認した（grep）。
  archive/ の中では、`manager_train.py` と `manager_tabq.py` が同じフォルダの `manager_env.py` を import するだけである。
- 保守しない：本番コードの変更に合わせて直さない。動かなくなっても、提出物と再現手順には影響しない。
- 残す理由：本番の 2 つの原則「外力・テレポートなし」「BZ はパッカンに触れない」が、試したうえで捨てた結果であることを示すため。

### ルートに残した旧名のファイル

- `v6_phase4_full.py`：`main()` は外力版 v6 の通し台本（`MicroduckCtrl`／`JumperCtrl` を使う）だが、ルートに置いた。
  `ArenaSim` と `PHASE_TEXT` を `v7_full.py` が、`ArenaSim` を `manager2_env.py` が import する現役のライブラリだからである。
  本番が使うのはこの 2 つだけで、`ArenaSim.command()` は BZ の `ctrl` を書くだけで外力を加えない。
- `v6_phase1_build.py`（舞台 `out/v6_stage_built.xml` を書く）と `v7_progress_video.py`（`official_md_servos` を `v7_test_collision.py` などが import）も、現役の依存先なのでルートにある。
- `xfrc_applied` に書き込むコードは、`v6_robots.py` の `MicroduckCtrl`／`JumperCtrl` と、archive/ の `render_3body*.py` にだけある。
  前者を呼ぶのは archive/ の v6 Phase 2〜3 と `v6_phase4_full.py` の `main()` で、ルート直下の他の `.py` と `analysis/` には `xfrc_applied` の記述が無い（grep で確認）。

## 動かし方

ルートから `python archive/<name>.py` で動く。動作に関わる変更はパスの解決だけで、次の 2 点である。

1. 12 本すべてに次の 1 行を足した。位置はモジュール docstring と `from __future__` の後、標準ライブラリの import の直後で、サードパーティとリポジトリ内の import より前である。

   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
   ```

   `import sys` が無かった 7 本には同じ箇所に足し、そのうち `v7_failures_video.py` と `v7_test_fork.py` には `from pathlib import Path` も足した。
2. v6 より前の 5 本（`render_3body.py`、`render_3body_v4.py`、`render_3body_v5.py`、`run_3body.py`、`build_3body_arena.py`）は、自分の位置から隣接リポジトリを探す。
   そこで `BASE` を `parents[2]` に、`render_3body*.py` の 3 本は `OUT_DIR` も `parents[1] / "out"` に直した（どちらも行末に `# archive/:` の注記）。

このほか、docstring とコメントの開発中の呼び名・日付・実行例を読者向けに置き換えた。動作は変えておらず、置換前の原文は `../docs/devlog/code_comment_quotes.md` にある。
`v6_phase2_md_walk.py` と `v6_phase3_jp_contact.py` の docstring の実行例は移動前の `python v6_phase…` のままなので、`python archive/v6_phase…` と読み替える。

### 前提

- 本番と同じく、隣接リポジトリ 3 つ（`../physical-ai-course-builder`、`../microduck_rl`、`../jumper`）と公式 ONNX が要る。手順は `../docs/reproduce.md`。
- 舞台を読む 5 本（`v6_phase2_md_walk.py`、`v6_phase3_jp_contact.py`、`manager_env.py`、`v7_test_fork.py`、`v7_failures_video.py`）は `out/v6_stage_built.xml` を読む。
  この XML は `python v6_phase1_build.py` の成果物で、リポジトリで追跡している。`manager_train.py` と `manager_tabq.py` も `manager_env.py` を通じて同じ舞台を読む。
- 引数を持たない 6 本（`render_3body*.py` の 3 本、`run_3body.py`、`build_3body_arena.py`、`v7_failures_video.py`）は、実行するとそのまま描画か実験が走る。
- 生成物は `out/` 直下か `out/manager_runs/` に書き、同名の既存ファイルを上書きする。
- 舞台を読むスクリプトの生成物は、舞台を新コース（峠の継ぎ目 1 cm）に変える前に作ったものである。
  現在の `out/v6_stage_built.xml` は新コースなので、再実行の数値が記録と一致するかは確かめていない。旧コースの舞台は `out/v6_stage_built_gap5cm.xml` に残る。

### 確認した事項

- 12 本すべてが `python -m py_compile` を通る。
- argparse を持つ 6 本（`manager_env.py`、`manager_train.py`、`manager_tabq.py`、`v6_phase2_md_walk.py`、`v6_phase3_jp_contact.py`、`v7_test_fork.py`）は、`--help` が終了コード 0 で返る。
  どれもモジュール先頭の import（ルート直下の `v6_common.py`、`v7_full.py` など）を通ったうえで、1 秒未満で返った。
- 引数を持たない 6 本は `main()` を走らせずに import だけ行い、`BASE`・`OUT_DIR` と XML のパスが移動前と同じ場所を指し、実在することを確かめた。
- 描画・学習・評価そのものは、移動後に再実行していない。

## 一覧

| ファイル | 分類 | 何をするか | 生成物（`out/`） |
|---|---|---|---|
| `v6_phase2_md_walk.py` | 外力版（不採用） | 施工済みの舞台で、パッカンをスクリプト歩容と仮想ハーネス（胴体への外力）で歩かせる | `v6_phase2_md_walk.mp4`、`v6_phase2_report.json` |
| `v6_phase3_jp_contact.py` | 外力版（不採用） | 跳跳が誘導力で近づいて接触し、転んだパッカンをハーネスで引き起こす | `v6_phase3_jp_contact.mp4`、`v6_phase3_report.json` |
| `manager_env.py` | 支配人 v1（凍結） | BZ がフォークで助ける場面の gymnasium 環境。単体では固定ルール／ランダムの煙試験 | `manager_smoke*.jsonl`、`--video` 指定時は mp4 |
| `manager_train.py` | 支配人 v1（凍結） | v1 環境での PPO の学習・同一シード評価・デモ | `manager_runs/` の `ppo_smoke2`・`ppo_smoke3`・`ppo_small`・`baselines`・`baselines2`・`baselines_final` |
| `manager_tabq.py` | 支配人 v1（凍結） | v1 環境での表形式 Q 学習 | 無し（実行記録は残っていない） |
| `v7_test_fork.py` | 不採用の結末 | BZ のフォークで座ったパッカンを持ち上げる／押し倒す単体実験 | 無し（標準出力に JSON） |
| `render_3body.py` | 旧世代の描画 v3 | 自前の床に 3 体を結合して 10 s 描画 | `3body_arena.mp4`（追跡しない。同じ内容の `3body_arena_v3.mp4` を追跡） |
| `render_3body_v4.py` | 旧世代の描画 v4 | course-builder の `scene_fork_tracks.xml` を土台に 10 s 描画 | `3body_arena_v4.mp4` |
| `render_3body_v5.py` | 旧世代の描画 v5 | v4 に坂 2 枚を静的な形状で置いて 10 s 描画（未完成） | `3body_arena_v5.mp4` |
| `build_3body_arena.py` | 初期の骨組み | `MjSpec.attach` で 3 つの MJCF を 1 ワールドに結合する最初の試験 | 無し（標準出力） |
| `run_3body.py` | 初期の骨組み | 物理 500 Hz・制御 50 Hz で 3 体に別々の制御器を持たせる骨組み（描画なし、sim 8 s） | 無し（標準出力） |
| `v7_failures_video.py` | 失敗集動画 | 外力なしで確かめた 3 つの事実を 1 本に収める | `v7_failures_physics_only.mp4` |

## 詳細：事実・原因・対処

### 外力版 v6 Phase 2〜3

- 事実：`v6_phase2_md_walk.py` の歩行はスクリプト歩容で、姿勢は `v6_robots.py` の `MicroduckCtrl` が胴体に力とトルク（`xfrc_applied`）を加えて保つ（仮想ハーネス）。
- 事実：`v6_phase3_jp_contact.py` は跳跳の接近を `JumperCtrl` の誘導力で、転倒後の復帰をハーネスの引き起こしで行い、物理のままなのは接触だけだった。
  接触 sim 10.74 s、転倒 sim 11.04 s、引き起こし開始 sim 12.54 s（`out/v6_phase3_report.json` の `md_events` の `HIT`・`FALLEN`・`RECOVER`）。
- 原因：演出に要る動きを外力で補う設計の不足。外力で動かした映像は、その機体が自分の力で何をできるかを示さない。
- 対処：本番はパッカンを公式 velstand ポリシーと XML の公式サーボ値（`v7_full.py` の `official_md_servos()`）で、跳跳を公式 locomotion で動かす。
  転倒からの復帰も、外力の引き起こしではなく velstand の自力起立にした。

### 支配人 v1（BZ がフォークで扱う版）

- 中身：`manager_env.py` は、座ったパッカンのところへ BZ が来て助ける場面を gymnasium 環境にしたもの。1 ステップ＝1 スキル。
  6 手 `WAIT`／`DOCK`／`LIFT`／`PUSH_SIDE`／`STANDUP`／`CLEAR`（`ACTIONS`）、直前の結果 8 種（`RESULT_SLOTS`）、観測 35 次元（`OBS_DIM` = 16 + 3 + 8 + 6 + 2）。
  設計メモ（§4.1）と初版の docstring の「32 次元」は旧記述で、コードは 33→34→35 と改訂された（`../docs/devlog/README.md` 訂正表 13）。docstring は 35 に直してある。
- 到達点：座席を坂の縁から 0.65 m 離し（`DUCK_SEAT`）、降ろしを足が床に着いた時点で止める最終環境で、固定ルールの煙試験 8 シードは持ち上げ 8/8・復帰 8/8・コースの移動 0 だった。
  出所は開発記録 `../docs/devlog/MANAGER_DESIGN.md` §4.5 の集計で、再計算スクリプトは無い。
  決定ログ `out/manager_smoke10.jsonl`・`manager_smoke11.jsonl` の 8 話（各 4 話）とも数は一致する。
  ただし smoke10 には降ろし高さ `set_down_height` の記録が無く（smoke11 は全行にある）、最終環境の版かは確かめていない。
- 凍結の理由：安全上の設計判断で、BZ のフォークがパッカンを扱うことを禁止した。フォークで首を持ち上げると破損の恐れがある、という指摘による（`../docs/devlog/MANAGER_DESIGN.md` §5.1b・§6）。
  性能が足りなかったからではなく、行動集合の前提が成り立たなくなったための凍結である。
- 作り直し：本番の支配人 AI は跳跳が押し上げる場面に作り直し、観測 46 次元・6 手 `WAIT`／`SEAT`／`PUSH`／`BACK_OFF`／`STANDUP`／`WALK_ON` になった。
  出所は `crab_help.py` の `OBS_DIM`・`ACTIONS`、学習環境は `manager2_env.py`。
- `manager_train.py`：学習ログ `train_env*.jsonl`（`out/manager_runs/ppo_smoke2`・`ppo_smoke3`・`ppo_small`）と基準方策の評価（`baselines`・`baselines2`・`baselines_final`）が残る。
  方策ファイル `ppo_manager.zip` は残っていない。`ppo_smoke2`・`ppo_smoke3`・`baselines`・`baselines2` は環境を直す前の参考値である。
  `ppo_small` と `baselines_final` は凍結の時点で走っていた記録で、`baselines_final` には集計（`eval_summary.json`）が無い（同メモ §4.5）。本番は `manager2_train.py`。
- `manager_tabq.py`：実行記録は残っていない。本番は `manager2_tabq.py`。
- v1 環境のデモ動画 `out/manager_demo_rule*.mp4`（同名の `.jsonl` は決定ログ）も残る。

### フォーク持ち上げの単体実験

この節の数値のうち、出所を開発記録と書いたものは開発中の集計で、再計算スクリプトは無い。

- 実験：`v7_test_fork.py` は座ったパッカンの東 1.9 m（`--from south` では真後ろ）に BZ を置き、横ずれ `--dy`・フォーク高さ `--lift`・進入角 `--skew` を変えて、持ち上がるか・押し倒すか・押すだけかを測る。
  BZ の配置は姿勢の書き込みで、この試験の中だけで使い、動画では使わない。
- 事実（横から）：床の高さの爪は座ったパッカンを 0.3 m 押して滑らせるだけで、6 cm の爪は中心 ±5 cm なら押し倒した。傾き 92°、velstand で 12.8 s 後に自力で起きた（開発記録 `../docs/devlog/HANDOVER.md` §0）。
- 事実（後ろから）：BZ の中心線がパッカンの左 1.5〜3 cm で平行なら、3 回中 3 回、両爪が腰の下に入って z 0.22 m まで持ち上げて降ろせた（同 §0）。
  支配人 v1 の場面では、窓は左 2.5 cm 付近の 1 cm 未満、進入角は 6° までだった（開発記録 `../docs/devlog/MANAGER_DESIGN.md` §4.2）。
- 通しの結果：台本どおりに寄せると、BZ の残差は 5〜12 cm・4〜5° で窓に届かなかった（同 HANDOVER §0）。
  5 回の内訳は斜めに持ち上がる 2・押し倒す 1・爪が外れる 2 で、水平に持ち上げて降ろせた回は無い。
- 原因と対処：寄せのスキルの精度不足。合わせ直すか別の方法に切り替えるかを選ぶ問題として支配人 v1 に引き継いだが、BZ がパッカンに触れる結末そのものを上記の設計判断で廃止した。

### 旧世代の描画 v3〜v5

- `render_3body.py`（v3）：自前の床に 3 体を結合した最初の描画。跳跳は跳躍中に上向き 15 N・前向き 10 N の外力で進む。
  跳躍していない間も、パッカンとの距離に比例した引き寄せ（4 N/m、最大 4 N）と、y=0 への寄せ（3 N/m）を外力で受ける。
  パッカンは高さが 0.11 m を下回ると、差に 80 N/m を掛けた上向きの外力で沈み込みを防ぐ（どれも `xfrc_applied`）。
- `render_3body_v4.py`（v4）：土台を course-builder の `scene_fork_tracks.xml` に替え、跳跳の外力を上向き 25 N・前向き 20 N に強めた。
  引き寄せも 8 N/m・最大 16 N に、パッカンの補助も目標 0.12 m・200 N/m に強めた（y=0 への寄せは 3 N/m のまま、v5 も同じ）。
  BZ がコース上の `block_1` に当たって止まる課題が残った（開発記録 `../docs/devlog/HANDOVER.md` §6、v4・v5 共通）。土台の選択は本番に残る（`v6_common.py` の `BZ_XML`）。
- `render_3body_v5.py`（v5）：坂 2 枚を施工せずに静的な形状として置き、v4 と同じ外力を使い、パッカンまで 0.5 m 以内ではばね力（20 N/m）に切り替えて跳跳の行き過ぎを抑えようとした。
  BZ の詰まりと跳跳の制御の不安定が残り、未完成のまま止めた（同 §2・§5）。
- 原因と対処：機体を外力で動かし、コースを描画側で置いた設計の不足。坂の施工を course-builder の `SlopeAssembly` に任せる `v6_phase1_build.py`（現役）に移行した。
  各機体の動きは、公式ポリシーとルール制御に置き換えた。

### 初期の骨組み

- `build_3body_arena.py`：3 つの MJCF を `MjSpec.attach` で 1 ワールドに結合する最初の試験（prefix `bz-`／`md-`／`jp-`、物体数と actuator 数を表示）。
  手順は `v6_robots.build_arena()` に引き継いだ。本番は施工済みの舞台（BZ を含む）を土台にして prefix を付けず、パッカンと跳跳に `md-`／`jp-` を付ける。
- `run_3body.py`：物理 0.002 s（`PHYSICS_DT`）・制御 0.02 s（`CONTROL_DT`、50 Hz）で、3 体に別々の制御器を持たせる骨組み（描画なし、sim 8 s）。
  制御 0.02 s の周期は本番に残り（`v7_full.py` の `CONTROL_DT`、`v7_policies.py` の `MD_CONTROL_DT`）、各機体の動かし方は公式ポリシーとルール制御に置き換えた。

### 失敗集動画

- `v7_failures_video.py`：外力なしで確かめた 3 場面を 1 本に収める。A パッカンが 16° の坂に 2 回挑んで登れず座り込む。
  B 跳跳が公式 locomotion で同じ坂を登る。C 跳跳の飛びつきで転んだパッカンが、密着されたままだと起き上がれない。
- 位置づけ：開発中の確認用の収録で、本編には使っていない。A と B は本編の筋書きの前提になった。
  C の事実は、本番の支配人 AI の手 `BACK_OFF`（跳跳が 0.6 m 離れて、パッカンが起き上がる場所を空ける。`crab_help.py` の docstring）の前提になっている。

## 本番に引き継いだこと

- 外力版から：原則「外力・テレポートなし」（例外は学習環境のリセット配置だけで、動画には出ない）。
  顔モニターや字幕などの演出は物理に触れない形に限り、顔あり／なしのヘッドレス A/B で qpos と qvel の sha256 が一致することを確かめる（`analysis/face_check.py`）。
- フォーク持ち上げから：スキルの精度が足りないときに次の一手をどう選ぶか、という支配人 AI の課題設定（`../docs/manager_ai.md`）。
- 支配人 v1 から：1 ステップ＝1 スキルの環境、同一シード評価、スキルの失敗と判断の失敗を分ける 2×2 の集計（`../docs/results.md`）。
- 失敗集から：パッカンが 16° の坂を登れない事実を隠さず、跳跳が押し上げる物語の核にしたこと。

## 考察

- 旧世代の描画は、施工から接触までを 1 本のスクリプトで一度に組もうとして、部分ごとの検証が追いつかなかった（開発記録 `../docs/devlog/HANDOVER.md` §8）。
  v6 からは施工・歩行・接触を段階に分け、各段の動画を確かめてから次へ進めた。
- v6 までは演出の動きを先に決め、足りない力を外力で補った。v7 では先に外力なしで物理の事実を測り（失敗集の A〜C）、筋書きをその事実に合わせた（同 §0）。
