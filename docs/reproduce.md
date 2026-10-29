# 再現手順

本文書は、提出動画・ヘッドレス検証・支配人 AI の学習と評価・気分ネット・図を手元で作り直す手順をまとめる。
コマンドはすべて本リポジトリのルートで `python …` と打つ（`python` は §1 の仮想環境の Python 3.10）。
所要時間は作者の環境（Windows 11、CPU のみ、GPU なし）での目安で、数値の出所はファイル名とキー名で併記する。
3 体の呼び名は、ブルドーザー（BZ、自作 course-builder）、パッカン（Microduck, Pollen Robotics）、跳跳（Jumper, KingKong Robotics）で統一する。

## 1. 環境

Python 3.10 で仮想環境を作り、torch の CPU 版を先に入れてから `requirements.txt` を入れる。
検証した版は Python 3.10.6（Windows 11）で、他の OS は未検証（§5.5）。

```
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell。Linux/macOS では source .venv/bin/activate
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

`requirements.txt` の版は、提出動画・評価表・学習済みモデルを作った環境の `pip freeze` と同じ値である。
torch はその環境で `torch.__version__` が `2.14.1+cpu`（CPU 版の配布元から入れた版）で、先に入れておけば `requirements.txt` の `torch==2.14.1` はこれで満たされる。

| パッケージ | 版 | 使う場所 |
|---|---|---|
| mujoco | 3.11.0 | 全スクリプト。`MjSpec.attach` で 3 体を結合（`v6_robots.py`）、`mujoco.Renderer` でオフスクリーン描画（`v7_full.py`）。報告 JSON の `mujoco` キーと一致 |
| numpy | 2.2.6 | 全スクリプト |
| onnxruntime | 1.23.2 | `v7_policies.py`：公式 ONNX 5 本（パッカン 2 本、跳跳 3 本）の推論。1 セッション 1 スレッド（`_session`） |
| torch | 2.14.1（CPU 版） | 気分ネットの学習と推論（`analysis/mood_train.py`、`crab_face.py`）、Stable-Baselines3 の内部 |
| stable-baselines3 | 2.9.2 | 支配人 AI の PPO（`manager2_train.py`）、学習データ収集で PPO を読む（`analysis/mood_data.py`） |
| gymnasium | 1.0.0 | 学習環境 `manager2_env.py`。1.1 系は Python 3.10.6 で import に失敗するため 1.0.0 に固定（`docs/devlog/HANDOVER.md`） |
| imageio／imageio-ffmpeg | 2.38.0／0.6.0 | 動画の書き出し（`v6_common.py` の `Video`、libx264）と音声の合成（`v7_full.py` が imageio-ffmpeg 同梱の ffmpeg を呼ぶ） |
| Pillow | 12.3.0 | 字幕・顔モニター・表情の描画（`v6_common.py` の `Captioner`、`crab_face.py`） |
| glfw | 2.10.2 | 隣接の `physical-ai-course-builder/app.py` が import する。表示される窓は開かない |

torch は CPU 版で足りる。学習（PPO・表形式 Q・気分ネット）も本番の推論もすべて CPU で行った（`manager2_train.py`・`crab_face.py` は `device="cpu"` を明示）。
システムに ffmpeg を入れる必要はない。`analysis/grab_frames.py`（動画から静止画を切り出す補助）だけは、imageio の pyav プラグイン（`av`）か
OpenCV（`cv2`）のどちらかを追加で要する。

## 2. 隣接リポジトリの配置

本リポジトリは、親ディレクトリに並ぶ 3 つのリポジトリをファイルパスで読む。`v6_common.py` の `BASE` が親ディレクトリ（`Path(__file__).resolve().parent.parent`）で、
`COURSE_BUILDER`／`BZ_XML`／`MD_XML`／`JP_XML` と `v7_policies.py` の `JP_BUNDLE` がその下を指す。
本リポジトリ自身のディレクトリ名は任意（clone の既定名は `mujoco-3body`）だが、隣の 3 つの名前は下のとおりでなければならない。

```
<親ディレクトリ>/
├── mujoco_3body/                      本リポジトリ（名前は任意）
├── physical-ai-course-builder/        ブルドーザー：舞台 XML と施工・走行のルール制御（自作）
├── microduck_rl/                      パッカンの MJCF モデル（Pollen Robotics）
└── jumper/                            跳跳の MJCF モデル（KingKong Robotics）
    └── out/bundle_example/jumper/     公式バンドル：ONNX 3 本・契約 JSON・参照軌道（jumper リポジトリに同梱、§2.1）
```

| ディレクトリ | 取得先（github.com/） | commit | 本リポジトリが読むもの | 定数 |
|---|---|---|---|---|
| `../physical-ai-course-builder/` | ortiz-ai-partners/physical-ai-course-builder | `ea5b4e7` | `scene_fork_tracks.xml`、モジュール `app`・`slope_assembly`・`tracks`・`navigation` | `COURSE_BUILDER`、`BZ_XML` |
| `../microduck_rl/` | pollen-robotics/microduck_rl | `b02fdea4` | `src/mjlab_microduck/robot/microduck/scene.xml` | `MD_XML` |
| `../jumper/` | KingKongRobotics/jumper | `61d0652` | `assets/jumper/jumper.xml`、`out/bundle_example/jumper/`（§2.1） | `JP_XML`、`JP_BUNDLE` |

定数は `JP_BUNDLE` だけが `v7_policies.py`、他は `v6_common.py` にある。

親ディレクトリで次を実行すると、上の配置と commit がそろう（1 行目は本リポジトリ）。

```
git clone https://github.com/ortiz-ai-partners/mujoco-3body.git
git clone https://github.com/ortiz-ai-partners/physical-ai-course-builder.git
git -C physical-ai-course-builder checkout ea5b4e7
git clone https://github.com/pollen-robotics/microduck_rl.git
git -C microduck_rl checkout b02fdea4
git clone https://github.com/KingKongRobotics/jumper.git
git -C jumper checkout 61d0652
```

course-builder のモジュールは `v6_common.course_builder()` が sys.path に `COURSE_BUILDER` を足して import する。
course-builder の commit `ea5b4e7` は峠の継ぎ目を 0.05 m から 0.01 m にした版で、評価 v4 と提出動画はこの版で作った。
別の commit では施工結果が変わり、§4 の照合値（最終状態の sha256 など）は一致しない。
跳跳の `tasks/jumper/common/constants.py`（基準姿勢 `JP_HOME`）と `deploy/fsm/src/obs.rs`（観測の契約）は、
`v6_robots.py`・`v7_policies.py` に転記した元ファイルで、実行時には読まない。

### 2.1 跳跳の公式バンドル

`v7_policies.py` は `../jumper/out/bundle_example/jumper/` から次の 8 ファイルを読む。このディレクトリは jumper リポジトリ自体に git 追跡で含まれている
（commit `61d0652` で `git ls-files out/bundle_example/jumper` が 55 ファイルを返す）ので、§2 の clone と checkout だけで揃い、生成の手順は要らない。
本リポジトリには同梱しない。

| ファイル | 役割 | 読む場所 | SHA-256（先頭 12 桁） |
|---|---|---|---|
| `locomotion.json` | 歩行ポリシーの契約（観測 415、200 Hz） | `JumperLocomotion` | `6204effa319e` |
| `models/locomotion.onnx` | 歩行ポリシー | `JumperLocomotion` | `a6e0864c425d` |
| `jump.json` | ジャンプの契約（観測 167、200 Hz） | `JumperJump` | `0e257faaac9a` |
| `models/jump.onnx` | ジャンプのポリシー | `JumperJump` | `1822601bd4c3` |
| `high_jump_flat.trajectory.json` | ジャンプの参照軌道（`jump.json` が名指す） | `JumperJump` | `c05e862dc910` |
| `dance_crab.json` | ダンスの契約（観測 209、50 Hz） | `JumperDance` | `de7df810b8bc` |
| `models/dance_crab.onnx` | ダンスのポリシー | `JumperDance` | `2723a684d471` |
| `demo.motion.trajectory.json` | ダンスの参照軌道（`dance_crab.json` が名指す） | `JumperDance` | `130ef0c90369` |

観測次元と制御周期は各契約 JSON の `observation.dim` と `control.control_dt`（0.005 s＝200 Hz、0.02 s＝50 Hz）。
SHA-256 はバンドル自身の `bundle.json`（`files`）の値で、同じ `bundle.json` の `built_from` に各ポリシーの出自が記録されている
（locomotion は `tasks/jumper/posture/out/example`、jump は `tasks/jumper/jump/out/example`、dance_crab は `tasks/jumper/dance/out/example` の export）。
Windows で `core.autocrlf=true` のまま clone すると JSON が CRLF 改行で取り出され、JSON 5 本の SHA-256 は上の値と一致しない（ONNX 3 本は一致する）。
読み込みには影響しない。ハッシュで照合するときは `git clone -c core.autocrlf=false` で取り出す。

バンドルを作り直す必要は通常ない。作り直すときは同リポジトリの `deploy/BUNDLE.md` に従う（`python scripts/deploy.py --bundle out/bundle_example` で
`out/bundle_example/jumper/` に書かれる）。本リポジトリが読むのは上の 8 ファイルだけなので、別のバンドルからこの 8 ファイルを同じ相対パスに置いても動く。

## 3. 同梱物と非同梱物

| 物 | 場所 | 出所 | 同梱 |
|---|---|---|---|
| パッカンの公式 ONNX 4 本と `manifest.json` | `policies/microduck/` | 既製（Pollen Robotics、HF pollen-robotics/microduck-policies） | 同梱。使うのは `velstand`・`alpha_sitstand` の 2 本（`v7_full.py` の `POLICY_DIR`） |
| 跳跳の公式 ONNX 3 本・契約・参照軌道 | `../jumper/out/bundle_example/jumper/` | 既製（KingKong Robotics、jumper リポジトリに同梱） | 非同梱（§2.1） |
| 3 体の MJCF モデルと舞台 XML | 隣接 3 リポジトリ | 自作（BZ）／既製（パッカン・跳跳） | 非同梱（§2） |
| 施工済みの舞台 XML | `out/v6_stage_built.xml` | 自作（`v6_phase1_build.py` の成果物） | 同梱。学習環境と単体実験の舞台。`out/v6_stage_built_gap5cm.xml` は旧コース（継ぎ目 5 cm） |
| 学習済みの支配人 AI | `out/manager_runs/{ppo2_medium2,ppo2_v22,ppo2_small}/ppo_manager.zip`、`tabq2_small/tabq.json` | 自作・学習済み | 同梱。PPO の途中チェックポイント `ckpt_*.zip` は非同梱 |
| 支配人 AI の学習記録 | `{ppo2_medium2,ppo2_v22,ppo2_small}/` の `train_curve.json`・`train_summary.json`、`tabq2_small/train_curve.json` | 自作 | 同梱 |
| 決定ごとの学習記録 | `{ppo2_medium2,ppo2_medium3}/train_env*.jsonl`（v2）、`{ppo_small,ppo_smoke2,ppo_smoke3}/train_env*.jsonl`（v1） | 自作 | 同梱。支配人 v2 の記録は ppo2_medium2・ppo2_medium3 の 2 run 分 |
| 気分ネット | `out/manager_runs/mood_net/mood_net.pt`、`meta.json`、`report.md` | 自作・学習済み | 同梱 |
| 気分ネットの学習データ | `out/manager_runs/mood_data.npz`、`mood_data_episodes.json` | 自作（`analysis/mood_data.py` の成果物） | 同梱 |
| 評価 JSON と比較表 | `out/manager_runs/{baselines_v4,ppo2_v22_v4,ppo2_medium2_v4,tabq2_small_v4}/`、`comparison_v4.md` | 自作 | 同梱 |
| 提出動画と比較用の 3 本（mp4） | `out/3body_arena_v7_take51.mp4`〜`out/3body_arena_v7_take54.mp4`（§4.1） | 自作 | 同梱。それ以前の版の所在は `docs/devlog/takes.md` |
| 報告 JSON と描画ログ | `out/v7_full_report_take46.json`〜`out/v7_full_report_take54.json`（§4.1・§4.2）、`out/v7_take51render.log` | 自作 | 同梱 |

既製の資産の出典・ライセンスは `THIRD_PARTY.md` にまとめる。

## 4. コマンド

表の列は「コマンド｜所要時間の目安｜出力｜照合先の数値」。「報告 JSON」は `out/v7_full_report<tag>.json` を指し、
照合に使うキーは `sim_seconds`（シミュレーション秒）、`video_silent.seconds`（動画の長さ）、`manager.decisions`（支配人の手）、`state_digest`（最終状態 qpos+qvel の sha256）。
digest は先頭 12 桁で示す。動画の長さの m:ss は `video_silent.frames` を 30 fps で秒に直して四捨五入した値で、括弧内に `video_silent.seconds` を添える。
報告 JSON にはコマンド行そのものは記録されないため、コマンドは argparse の定義と報告 JSON の内容（`manager.policy`、`ending`、`cuts`、`face.mood_ai`）から組み立てた。
報告 JSON の `video.path`・`video_silent.path` は描画した環境の絶対パスで、照合には使わない。

表のコマンドは同梱の生成物を作ったときの引数で、同じ `--tag`・`--run`・`--out`・`--name` で実行すると同梱のファイルを上書きする。
同梱物と比べるときは別名を付ける（例：`--tag _rerun51`、`--run ppo2_v22_rerun`、`--out baselines_v4_rerun`、`--name mood_data_rerun`）。
別名で作った学習済みモデルは、`v7_full.py` の `--run`（支配人）と `--mood-net`（気分ネット）でそのまま指定できる。

### 4.1 提出動画の描画（施工 4 倍速、省略なし）

`--ending crab`、`--manager rule`、`--finale circle`、`--face-ai mood`、`--mood-net mood_net` は既定値なので省略できる。
`--build-speed 4` は施工区間の動画速度を 4 倍にし、`--no-cuts` は既定の省略 2 か所を外す。右下に sim 時計と x4／x2／x1 が常に出る。
`--build-speed` は 2（既定、`SPEED["BUILD"]`）かその整数倍だけを受け付け（`v7_full.py` の `ap.error`）、2 より大きい値は `--no-cuts` と組み合わせる（`--help`）。
フレームは 2 倍速のまま標本化し、4 倍では 1 枚おきに書く（§5.3）。描画は音声の合成まで含めて 1 本あたり約 5〜8 分
（`out/v7_take51render.log` は標準出力を保存したログで、wall 列は sim 400 s 時点で 290 s。その後に動画の閉じと音声の合成が続く）。

出力は `out/3body_arena_v7<tag>.mp4`（音声付き）と報告 JSON で、§4.2 も同じ。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python v7_full.py --tag _take51 --build-speed 4 --no-cuts` | 約 5〜8 分 | mp4＋報告 JSON | 提出版（固定ルール）。sim 404.22 s、2:47（167.0 s）、5 手、digest `678fd3cae2ca` |
| `python v7_full.py --manager ppo --run ppo2_v22 --tag _take52 --build-speed 4 --no-cuts` | 約 5〜8 分 | mp4＋報告 JSON | PPO 版。sim 400.6 s、2:45（165.2 s）、4 手、digest `aafa49e7a869` |
| `python v7_full.py --manager tabq --run tabq2_small --jitter 0.4 --tag _take53 --build-speed 4 --no-cuts` | 約 5〜8 分 | mp4＋報告 JSON | Q 表版。sim 402.9 s、2:46（166.3 s）、8 手、digest `f53de6e45af7` |
| `python v7_full.py --finale procession --tag _take54 --build-speed 4 --no-cuts` | 約 5〜8 分 | mp4＋報告 JSON | 追走版（固定ルール）。sim 397.72 s、2:44（163.7 s）、5 手、digest `be8fb01e8f90` |

手の列（`manager.decisions`）：提出版と追走版は SEAT→PUSH→BACK_OFF→STANDUP→WALK_ON で時刻も同一、PPO 版は SEAT→PUSH→STANDUP→WALK_ON、
Q 表版は STANDUP→WALK_ON→SEAT→PUSH→BACK_OFF→STANDUP→STANDUP→WALK_ON。`manager.policy` は順に「固定ルール」「PPO 方策（ppo2_v22）」「学習済み Q 表（tabq2_small）」「固定ルール」。
4 本とも `three_crossed` は bz・crab・duck すべて true、`course_disturbed` は空（コース部品の移動なし）、`mujoco` は 3.11.0、
`face.mood_ai.inferences`（気分ネットの推論回数）は 5236／5050／5239／5236。

Q 表版の `--jitter 0.4` は応援ダンスの開始位置（`CHEER_DANCE_START`）をずらす引数で、台本と支配人を変えずに経路だけを変える（§5.4）。
この値は報告 JSON には記録されないので、`--help` の説明どおり、使った値をここに書き残す。

描き直した版が同梱の版と同じ経路かは、§4.8 の `timeline_times.py --compare` で確かめる
（例：`python analysis/timeline_times.py out/v7_full_report_rerun51.json --compare out/v7_full_report_take51.json` の末尾が `state_digest equal: True`）。

### 4.2 2 倍速・省略 2 か所の版（記録）

同じ 4 本を、施工も 2 倍速で描き、BZ が空荷で戻る 2 区間を省略した版。省略は sim 22→54 s（動画 0:11.0）と sim 110→172 s（動画 0:39.1）で、
`DEFAULT_CUTS` と報告 JSON の `cuts`、`events` の「JUMP CUT」行（`video_t`）に残る。物理の経路は §4.1 と同一で、`state_digest` が一致する（§5.3）。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python v7_full.py --tag _take46` | 約 5〜8 分 | mp4＋報告 JSON | sim 404.22 s、2:44（164.1 s）、`cuts` 2 件、digest `678fd3cae2ca`（提出版と同一） |
| `python v7_full.py --manager ppo --run ppo2_v22 --tag _take47` | 約 5〜8 分 | mp4＋報告 JSON | sim 400.6 s、2:42（162.3 s）、digest `aafa49e7a869`（PPO 版と同一） |
| `python v7_full.py --manager tabq --run tabq2_small --jitter 0.4 --tag _take48` | 約 5〜8 分 | mp4＋報告 JSON | sim 402.9 s、2:43（163.5 s）、digest `f53de6e45af7`（Q 表版と同一） |
| `python v7_full.py --finale procession --tag _take49` | 約 5〜8 分 | mp4＋報告 JSON | sim 397.72 s、2:41（160.8 s）、digest `be8fb01e8f90`（追走版と同一） |

4 組の一致は `timeline_times.py` で確かめた。§4.1 と §4.2 の表の同じ行どうし（提出版、PPO 版、Q 表版、追走版の 4 組）の報告 JSON を
`--compare` で比べ、4 組とも `state_digest equal: True` になる（例は §4.8 の 2 行目）。

`out/v7_full_report_take50.json` は 4 倍速の最初の実装（フレームの標本周期を変えた版）の記録で、digest `768e78f7ce4f`、sim 390.66 s、2:40（160.2 s）と経路が変わっている
（3 体渡り切り・5 手は同じ）。現行コードでは同じ経路は出ないので、記録としてだけ残す。

### 4.3 ヘッドレス検証と A/B

`--test` は描画なしで物理と支配人の判断だけを回し、報告 JSON を書く（動画は書かない）。顔なし（`--no-face`）・顔あり（表情は表だけ、`--face-ai table`）・
顔あり＋気分ネット（既定）を比べ、描画専用の顔と気分ネットが物理を変えないことを確認する。
`--until <STAGE>`（BUILD／FOLLOW_IN／RAMP／CLIMB／CALL／RETURN／RESCUE／CELEBRATE／END）で途中終了、`--preview DIR` で 15 s ごとの静止画、
`--max-sim`（既定 520）で打ち切り秒を変えられる。ヘッドレス 1 本の所要は約 1.5 分（`out/v7_facecheck_A.log` の wall 列は sim 380 s 時点で 80 s）。

同梱の 3 本（`facecheck_A`・`facecheck_B`・`moodcheck_C`）の比較は、計算なしで数秒で確かめられる。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python analysis/face_check.py out/v7_full_report_facecheck_A.json out/v7_full_report_facecheck_B.json` | 数秒 | 標準出力 | A（顔なし）と B（顔あり）：8 項目 same、ngeom 290→291、終了コード 0 |
| `python analysis/face_check.py out/v7_full_report_facecheck_A.json out/v7_full_report_moodcheck_C.json` | 数秒 | 標準出力 | C（気分ネットあり）：digest・判断は same、出来事 1 件の文言差、終了コード 1 |
| `python analysis/timeline_times.py out/v7_full_report_facecheck_A.json --compare out/v7_full_report_moodcheck_C.json` | 数秒 | 標準出力 | 同じ A と C の組で末尾が `state_digest equal: True  (c083a03c2625 / c083a03c2625)`、終了コード 0 |

A と B の組は最後の行が `VERDICT: identical physics path` になる。A と C の組は `VERDICT: THE PATHS DIFFER` になるが、
差は出来事の文言 1 件（`BZ faces south: the circle is complete` と `BZ faces south, toward the goal: …`）だけで、digest は同じ `c083a03c2625` である。
`face_check.py` は文言も含めて出来事を比べるので、この組では終了コード 1 になる。

ヘッドレスを新しく回すときは、同梱のファイルを上書きしない別名の tag を使う。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python v7_full.py --test --no-face --tag _rerunA` | 約 1.5 分 | `out/v7_full_report_rerunA.json` | 同梱の `facecheck_A`：sim 385.6 s、`events` 64、5 手、`ngeom` 290、digest `c083a03c2625` |
| `python v7_full.py --test --face-ai table --tag _rerunB` | 約 1.5 分 | `out/v7_full_report_rerunB.json` | 同梱の `facecheck_B`：同じ sim・events・手・digest、`ngeom` 291（表示板 1 枚） |
| `python v7_full.py --test --tag _rerunC` | 約 1.5 分 | `out/v7_full_report_rerunC.json` | 同梱の `moodcheck_C`：同じ digest、`face.mood_ai.inferences` 4518 |
| 下の digest 一覧 | 数秒 | 標準出力 | 同梱 6 本（`facecheck_A`・`_B`、`moodcheck_B`〜`_E`）と新しい 3 本がすべて `c083a03c2625` |
| `python analysis/timeline_times.py out/v7_full_report_rerunC.json --compare out/v7_full_report_moodcheck_C.json` | 数秒 | 標準出力 | 末尾が `state_digest equal: True`（新しい C と同梱の C の digest がともに `c083a03c2625` のとき） |

digest 一覧は、ヘッドレスの報告 JSON の `state_digest` を並べて印字する 1 行である。`timeline_times.py` の表は、ヘッドレスでは動画時刻の列がすべて 0:00.0 になる。

```
python -c "import json,glob;[print(p,json.load(open(p,encoding='utf-8'))['state_digest'][:12]) for g in ('*check_?','rerun?') for p in sorted(glob.glob('out/v7_full_report_%s.json'%g))]"
```

同梱の `facecheck_B`・`moodcheck_B`・`moodcheck_C` は、表情ログ（`face.log`）の行が 3 要素だった時期の報告である（`facecheck_A` は顔なしで、`face.log` が null）。
現行コードの `crab_face.py` は行に規則番号と計測値を足して 5 要素で書く（`FaceDriver` の `self.log.append`）。
そのため新しく作った報告を `analysis/face_check.py` に渡すと、8 項目の same／DIFFERS と ngeom の行を印字した後、表情ログの一覧で
値の展開に失敗して止まる（ValueError、終了コード 1、`VERDICT` 行は出ない）。印字済みの 8 項目か、上の digest の一覧で判定する。

`analysis/timeline_times.py` は表情ログの形を問わない。顔なしの報告（A、`face.log` が null）では表情ログの節を `face log: none` と印字し、
3 要素の報告では規則番号を省いて印字する。同梱のヘッドレス報告 4 組（A と B、B と C、C と D、E と D）で終了コード 0 と `state_digest equal: True` を確認した。
`moodcheck_D` と `moodcheck_E` は、気分ネットありで 5 要素の表情ログを持つ同梱の報告で、digest は `c083a03c2625`。

ヘッドレス（sim 385.6 s）と描画版（sim 404.22 s）は時刻が一致しない。これは描画のたびに `mj_forward` を呼ぶことによるもので、§5.3 に書く。

### 4.4 支配人 AI の学習

学習環境は `manager2_env.py`（1 ステップ＝1 スキル、開始場面 7 種、舞台は `out/v6_stage_built.xml`）。学習の seed は `train_summary.json` に残らないため、
下の seed は開発時のコマンドの写し（`docs/devlog/README_development.md`「動かし方」）による。
PPO の学習は `--envs` 個の並列プロセス（`SubprocVecEnv`）を使う。`--envs` を下げると、実時間が延びるうえ、1 回の更新に集める決定数
（`--envs`×`--rollout`）が変わるので学習結果も同じにはならない。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python manager2_env.py --episodes 2 --policy rule` | 約 2 分 | `out/manager2_smoke.jsonl` | 煙試験。2 話の判断ログが書かれる（seed は `--seed0` 既定 1000 から） |
| `python manager2_train.py train --run ppo2_medium2 --envs 12 --steps 12000 --rollout 48 --seed 1` | 約 4 h 13 min | run のディレクトリ | 792 話、学習中成功率 0.677（`train_summary.json`） |
| `python manager2_train.py train --run ppo2_v22 --init-from ppo2_medium2 --reward v2.2 --envs 12 --steps 12000 --seed 3 <W>` | 約 4 h 28 min | 同上 | 766 話、0.658、`draw_tables` ほかが一致 |
| `python manager2_tabq.py train --run tabq2_small --episodes 120` | 約 2 h | 同上 | 314 状態（`tabq.json` のキー数）、α 0.2・γ 0.95・ε 0.3→0.05（既定値） |

run のディレクトリは `out/manager_runs/<run>/`。所要時間は PPO が `train_summary.json` の `wall_s`（15154.2 s、16105.2 s）、
Q 表が `train_curve.json` 末尾の `wall_s`（7166.2 s、単一プロセス）。ppo2_v22 の `train_summary.json` は `init_from`・`reward`・`draw_tables`・`rollout`（48）を記録する。

出力ファイルは、PPO が `ppo_manager.zip`、`ckpt_*.zip`（`--ckpt-every` 既定 2000 決定ごと）、`ppo_manager_latest.zip`、`train_curve.json`、`train_summary.json`、`train_env*.jsonl`。
Q 表が `tabq.json`、`train_curve.json`、`train_decisions.jsonl`。
継続学習（`--init-from`）は保存済みモデルを `PPO.load` で読むので、`--rollout` は読み込んだモデルの値（48）を引き継ぐ。
`--reward v2.2` は学習時だけの報酬の変更で、評価は v2.1 のまま（`manager2_train.py` の `train()`、`--reward` の help）。
`<W>` は次の 2 引数で、値は引用符で囲んで渡す（開始場面の重みと、足元場面での跳跳の配置の重み。`ppo2_v22/train_summary.json` の `draw_tables` と同じ値）。

```
<W> = --scenario-weights "toe_seated_ok=0.20,toe_seated_wrong=0.15,toe_standing=0.15,toe_fallen=0.10,deck_seated=0.15,deck_fallen=0.05,ramp_fallen=0.20"
      --crab-toe-weights "behind=0.5,beside=0.2,touching=0.3"
```

### 4.5 評価と比較表

評価は 30 シード（5000〜5029）を全方式で共有し、方策は決定的に動かす（PPO は `deterministic=True`、ランダム方策は `default_rng(7)`、Q 表は ε 0 で同点だけ `default_rng(1)`）。
`--out` で評価結果を学習 run とは別のディレクトリに置く（比較表の run 名 `*_v4` と一致させる）。
1 話の実時間は `eval_summary.json` の `mean_wall_s`（52.0〜63.8 s）で、1 方策 30 話は約 30 分。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python manager2_train.py eval --run baselines_v4 --policies rule random --episodes 30 --seed0 5000` | 約 1 h（2 方策） | `baselines_v4/` | 固定ルール 29/30、ランダム 14/30（`crossing_rate` 0.967／0.467） |
| `python manager2_train.py eval --run ppo2_v22 --policies ppo --episodes 30 --seed0 5000 --out ppo2_v22_v4` | 約 30 分 | `ppo2_v22_v4/` | 26/30（0.867） |
| `python manager2_train.py eval --run ppo2_medium2 --policies ppo --episodes 30 --seed0 5000 --out ppo2_medium2_v4` | 約 30 分 | `ppo2_medium2_v4/` | 23/30（0.767） |
| `python manager2_tabq.py eval --run tabq2_small --episodes 30 --seed0 5000 --out tabq2_small_v4` | 約 30 分 | `tabq2_small_v4/` | 25/30（0.833） |
| `python manager2_report.py --runs baselines_v4 tabq2_small_v4 ppo2_medium2_v4 ppo2_v22_v4 --name comparison_v4` | 数秒 | `comparison_v4.md` | 渡り切り 29／14／25／23／26（/30）と 2×2（下記） |
| `python manager2_train.py demo --run ppo2_v22 --policy ppo --seed 5003 --video out/manager2_demo_ppo.mp4` | 数分 | `out/manager2_demo_ppo.mp4` | 学習環境での 1 話を吹き出し付きで録画（照合値なし） |

出力の場所はすべて `out/manager_runs/` の下。各評価の出力は `eval_<policy>.json`、`eval_summary.json`、`eval_decisions.jsonl` で、
渡り切りの割合は `eval_summary.json` の `crossing_rate`。
比較表の 2×2（両方渡った／ルールだけ／方策だけ／両方失敗）は PPO v2.2 25/4/1/0、Q 表 24/5/1/0、PPO 中規模 22/7/1/0、ランダム 14/15/0/1（`comparison_v4.md`）。
`--rule-near-lip off` は固定ルールの PUSH 条件から near_lip を外した旧ルールで評価する（`crab_help.py` の `RULE_NEAR_LIP`、旧コースの評価 v2 と同じ条件）。
評価 v4 の比較表は `--rule-near-lip` 既定の on で作った。

### 4.6 気分ネット

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python analysis/mood_data.py --seeds 2 --policies rule ppo random --name mood_data` | 約 23 分 | `mood_data.npz` ほか | 47,952 サンプル・35 話（固定ルール 14、PPO 14、ランダム 7） |
| `python analysis/mood_train.py --data mood_data --out mood_net --epochs 600 --hidden 32 --seed 0` | 1 分以内 | `mood_net/` | `best_epoch` 450、見送り分の正解率は下記 |
| `python analysis/face_value.py --seeds 2 --policies rule ppo --name face_value` | 約 20 分（目安） | `face_value.md`・`.json` | 不採用の第 1 案（PPO 批評家 V(s)）の下調べ。25,214 サンプル・28 話 |

出力の場所はすべて `out/manager_runs/` の下。所要時間は、収集が `mood_data.log` 末尾の 1364 s、学習が学習ループ 3.5 s（`meta.json` の `train_s`）に
読み込みと書き出しを足した目安、`face_value.py` は経過時間の記録がない目安。`face_value.py` の件数の出所は `face_value.json`。

学習データの出力は `out/manager_runs/mood_data.npz` と `mood_data_episodes.json`（話ごとの方策・場面・サンプル数。方策の内訳はここから）。
`mood_data.log` は標準出力を保存したログ。`--run ppo2_v22` が既定で、PPO の話にはこの重みを使う。
気分ネットの出力は `out/manager_runs/mood_net/` の `mood_net.pt`、`meta.json`、`report.md`。
`meta.json` の `metrics` は見送り 10,772 サンプルで 4 分類（`outcome4/heldout`）0.80、成功 vs 失敗（`success_vs_not/heldout`）0.80・均衡正解率 0.83、
渡れる（`crossed/heldout`）0.672。表情の線は `thr_smile` 0.34、`thr_trouble` 0.287。

気分ネットの入出力は 53→32→32→5（`meta.json` の `n_in`、`hidden`、`n_out`）。学習は話 ID で 4 話に 1 話を見送りに回し（37,180／10,772 サンプル、`metrics` の `n`）、
見送り分の均衡正解率でエポックを選ぶ（`analysis/mood_train.py`）。
torch の乱数は `--seed` で固定するが、別の CPU・別の torch 版では学習結果の数値が小数点以下でずれることがある。

### 4.7 図の生成

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python analysis/face_sheet.py` | 数十秒 | `report/faces_sheet_ja.png` | 11 表情を 480×240 で格子に並べた図（名前と出る場面つき）。日本語フォントが必要（§5.2） |
| `python v7_test_face.py` | 数十秒 | `out/face_test/face_<expression>.png`、`faces_sheet.png` | 顔の煙試験（物理は進めない）。目視で向きと鏡像を確認 |
| `python analysis/grab_frames.py out/3body_arena_v7_take51.mp4 report/take51 54 88 94 130` | 数秒 | `report/take51_054.0s.png` の形で 1 枚ずつ | 動画の指定秒の静止画。`av` か `cv2` が必要（§1、`requirements.txt` には含めない） |

`report/` の他の図（`system_overview_ortiz.png`、`course_plan_ortiz.png`、`results_managers_ortiz.png`、`mood_net_pipeline_ortiz.png`、
`face_rules_chart_ortiz.png`、`timeline_ortiz.png`）は本プロジェクトで作成した説明図で、コードからは生成しない。載せた数値は §4.5・§4.6・§4.8 の出力と照合する。
ただし `timeline_ortiz.png` は 2 倍速＋省略 2 か所の版（§4.2、`out/v7_full_report_take46.json`）の時刻で描いた図で、省略のない提出動画（§4.1）の時刻と合わないため、
README には載せていない。提出動画の時刻は §4.8 の表を正とする。

### 4.8 時刻表（動画時刻と sim 時刻の対応）

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python analysis/timeline_times.py out/v7_full_report_take51.json` | 数秒 | 標準出力：速度区間、出来事、支配人の判断、表情ログ（動画時刻 m:ss.s と sim 秒） | 下の表の値 |
| `python analysis/timeline_times.py out/v7_full_report_take51.json --compare out/v7_full_report_take46.json` | 数秒 | 標準出力：2 本の表と時刻のずれ | 末尾に `state_digest equal: True`（digest `678fd3cae2ca`） |

提出版（`out/v7_full_report_take51.json`）の主な時刻。動画時刻は m:ss.s、sim 時刻は秒。速度区間は ×4 が 0:00.0〜0:44.1、×2 が 0:44.1〜2:29.1、
×1 が 2:29.1〜終端 2:47（167.0 s、`video_silent.frames` 5009 を 30 fps で秒に直した値）。
`timeline_times.py` の速度区間の表示は最終出来事 END（2:44.5）までで切れるが、動画は END の後も等速で sim 404.22 s まで続く。
表の値は `events` の `video_t`・`t` と `manager.decisions` の `video_t`・`t` から読む。

| 出来事 | 動画時刻 | sim 秒 |
|---|---|---|
| 施工完了（BZ が 4 面を走破、同時に渡り切り） | 0:54.0 | 196.08 |
| パッカンが座り込む | 1:08.2 | 224.64 |
| 跳跳が峠でジャンプ | 1:15.4 | 239.04 |
| 跳跳が渡り切る | 1:18.9 | 245.92 |
| 支配人 AI の 1 手目 SEAT | 1:28.2 | 264.58 |
| 2 手目 PUSH | 1:34.2 | 276.54 |
| 3 手目 BACK_OFF | 2:09.8 | 347.88 |
| 4 手目 STANDUP | 2:10.7 | 349.64 |
| 5 手目 WALK_ON | 2:13.5 | 355.20 |
| パッカンが渡り切る（3 体そろう） | 2:20.6 | 369.38 |
| 輪の万歳のダンス開始（等速） | 2:29.1 | 386.32 |
| END | 2:44.5 | 401.72 |

表情ログも同じコマンドで動画時刻に直して出る。たとえば顔が「にっこり（立たせる、成功 99%）」に変わるのは 2:11.7（sim 351.62）で、
4 手目 STANDUP の動画 1.0 s 後（sim 1.98 s 後）である。

他の 3 本も同じコマンドで出せる。施工完了（0:54.0｜sim 196.08）は 4 本で同じ。跳跳の渡り切りは動画 1:18.9 で 4 本とも同じだが、
sim は Q 表版だけ 246.00（`--jitter 0.4` で経路が変わったため）、他の 3 本は 245.92。違いは支配人の手から大きくなる。

| 版（報告 JSON） | 手数 | 1 手目 | パッカン渡り切り | ×1 開始 | END |
|---|---|---|---|---|---|
| PPO 版（`out/v7_full_report_take52.json`） | 4 | SEAT 1:28.2｜264.58 | 2:18.7｜365.64 | 2:27.3｜382.70 | 2:42.6｜398.10 |
| Q 表版（`out/v7_full_report_take53.json`） | 8 | STANDUP 1:28.2｜264.62 | 2:20.7｜369.54 | 2:28.4｜384.98 | 2:43.8｜400.40 |
| 追走版（`out/v7_full_report_take54.json`） | 5 | SEAT 1:28.2｜264.58 | 2:20.6｜369.38 | 2:25.8｜379.82 | 2:41.2｜395.22 |

「×1 開始」は輪の万歳（`the circle`）または追走版のゴールでの万歳（`the three cheer at the goal`）の出来事で、ここから等速になる。
追走版は輪を作らず、跳跳が後を追ってその場で万歳する結末で、支配人の 5 手の時刻は提出版と同一（`manager.decisions`）。

### 4.9 単体実験

`v7_test_*.py` は 1 つの現象を切り出して確かめる実験で、配置は姿勢の書き込み（テレポート）で置く（テスト専用。提出動画では使わない）。
舞台は `out/v6_stage_built.xml`（直接読むか、学習環境の `manager2_env.Scene` 経由）。`v7_test_face.py`（§4.7）だけは course-builder の舞台を自分で組む。
照合値の欄に数値があるのは記録が同梱されているものだけで、他は確かめる現象を書く。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python v7_test_crab_push.py --seated --crest --face-crab --crab-vx 0.3 --video out/v7_crab_push_cross.mp4` | 数分 | mp4、標準出力 | 天面到達 sim 81.4 s、北側の床へ sim 86.6 s（`out/v7_crab_push_cross.log`） |
| `python v7_test_cheer.py --circle --video out/v7_cheer_circle_test1.mp4` | 数分 | `out/v7_cheer_circle_test1.mp4` | 輪の万歳（BZ フォーク上下、パッカン屈伸、跳跳ダンス） |
| `python v7_test_bz_drive.py` | 数分 | 標準出力 | BZ の前進（フォーク低／高）と旋回 |
| `python v7_test_microduck.py --fall side` | 数分 | 標準出力、`--preview DIR` で静止画 | 公式 velstand の転倒からの起き上がり（XML 公式サーボ kp 0.55・±0.96 N·m、外力なし） |
| `python v7_test_sitstand.py` | 数分 | 標準出力 | velstand→sitstand（座る・首・立つ）→velstand の遷移 |
| `python v7_test_dance.py --seconds 30` | 数分 | 標準出力、`--video PATH` | 公式 dance_crab を 30 s 続けて転倒しないか |
| `python v7_test_jumper.py`、`python v7_test_jump.py` | 数分 | 標準出力、`--preview DIR` | 公式 locomotion の歩行、公式 jump の高さ・距離 |
| `python v7_test_jump_forward.py` | 数分 | 標準出力 | 前方ジャンプ：公式 jump の関節目標に股関節ヨーの後方掃きを重ねる（外力なし） |
| `python v7_test_collision.py --sweep 1.2 --jump-dist 0.55` | 数分 | 標準出力 | 跳跳の前方ジャンプがパッカンに当たったときの物理（`--ram` で跳ばずに歩いて当たる） |
| `python v7_test_crest.py`、`python v7_test_head_reach.py`、`python v7_test_fall_recovery.py` | 数分 | 標準出力 | 峠で腹をつく問題、首の到達範囲、起き上がれない原因の切り分け |
| `python v7_test_nudge.py --video out/v7_nudge_test1.mp4` | 数分 | `out/v7_nudge_test1.mp4` | 転んだパッカンへの小突き（採用しなかった試み） |
| `python v7_progress_video.py` | 数分 | `out/v7_progress_physics_only.mp4` | 外力なしの公式ポリシーで跳跳の歩行と前方ジャンプ、パッカンの起き上がりと首の動き |

`v7_test_crab_push.py` の行は、座って跳跳の方を向いたパッカンを跳跳が押し上げる、提出動画の救助の鍵になった実験である。
照合値はログの `landing_t`・`crossed_t`。
`v7_test_microduck.py` の `--fall` は none／side／side2／face／face2／back から選び、`--kp`・`--force` の既定値が XML 公式値（0.55、0.96）である。

### 4.10 舞台 XML と読み込み確認

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python v6_phase1_build.py` | 数分 | `out/v6_stage_built.xml`、`out/v6_phase1_build.mp4`、`out/v6_phase1_report.json` | `success` true、`surfaces_touched` 4、`vehicle_rise_m` 0.440、`seconds` 199.32 |
| `python test_load_bulldozer.py` | 数秒 | 標準出力 | course-builder の 4 シーン XML が MuJoCo 3.11 で読める |
| `python test_load_microduck.py` | 数秒 | 標準出力 | microduck_rl のシーン XML 群が読める |
| `python v6_phase4_full.py --test` | 数分 | `out/v6_phase4_report.json` | 外力による補助を使っていた前世代の通し台本（記録、下記） |

`v6_phase1_build.py` の引数は `--preview DIR`（動画の代わりに静止画）、`--speed`（時間短縮の倍率）、カメラの `--az-start`／`--az-end`／`--elevation`／`--distance`。
`out/v6_stage_built.xml` は同梱済みなので、学習環境と単体実験を動かすだけなら再実行は要らない。提出動画（`v7_full.py`）は舞台を自分で施工するので、この XML を読まない。
`v6_phase4_full.py` は `--test` なしなら `out/3body_arena_v6.mp4` も書く。
本番の `v7_full.py`（`ArenaSim`・`PHASE_TEXT`）と学習環境 `manager2_env.py`（`ArenaSim`）がここから import するので、ルートに置いてある。

### 4.11 archive/ の旧スクリプト

`archive/` の 12 本は採用しなかった設計と旧世代の記録で、本番コードからは import されず保守もしない（`archive/README.md`）。ルートから `python archive/<name>.py` で動く。
各ファイルは標準ライブラリの import 直後に `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` を 1 行持ち、ルート直下の `v6_common.py` などを解決する。
v6 より前の 5 本は `BASE` を `parents[2]` に、出力のある 3 本（`render_3body*.py`）は `OUT_DIR` を `parents[1]` にして、移動前と同じ場所に向けてある。
前提は本番と同じ（隣接 3 リポジトリ、`out/v6_stage_built.xml`、公式 ONNX）。生成物は `out/` 直下または `out/manager_runs/` に書き、既存の生成物を上書きする。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python archive/manager_env.py --episodes 1 --policy rule` | 数分 | `out/manager_smoke.jsonl` | 支配人 v1（BZ がフォークで扱う場面）の煙試験。観測 35 次元（`OBS_DIM`） |
| `python archive/manager_train.py train --run ppo_smoke --envs 8 --steps 1024 --rollout 32` | 数十分 | `manager_runs/ppo_smoke/` | 支配人 v1 の PPO。記録は `ppo_smoke2`・`ppo_smoke3`・`ppo_small`（方策なし） |
| `python archive/manager_tabq.py train --run tabq_smoke --episodes 300` | 数時間 | `manager_runs/tabq_smoke/` | 支配人 v1 の表形式 Q（実行記録は残っていない） |
| `python archive/v6_phase2_md_walk.py --test` | 数分 | 標準出力（計測ログ） | 外力（`xfrc_applied` の仮想ハーネス）を使った不採用版。本番の原則に反する記録 |
| `python archive/v6_phase3_jp_contact.py --test` | 数分 | 標準出力（要約 JSON） | 同上。同梱の報告（描画版）で接触 sim 10.74 s、転倒 11.04 s、引き起こし 12.54 s |
| `python archive/v7_test_fork.py --mode lift --lift 0 0.06` | 数分 | 標準出力（JSON） | BZ のフォークで座ったパッカンを持ち上げる不採用の結末の単体実験（`--mode tip` が既定） |
| `python archive/render_3body_v4.py` | 数分 | `out/3body_arena_v4.mp4` | 旧世代 v4 の 10 s 描画（`xfrc_applied` による補助あり） |

表の出力の `manager_runs/` は `out/manager_runs/`。v6 Phase 2〜3 の 2 本は `--test` なしで描くと、`out/v6_phase2_md_walk.mp4`・`out/v6_phase2_report.json`、
`out/v6_phase3_jp_contact.mp4`・`out/v6_phase3_report.json` を書く。Phase 3 の照合値は同梱の `out/v6_phase3_report.json` の `md_events`（HIT・FALLEN・RECOVER）。

argparse を持つのは `manager_env.py`・`manager_train.py`・`manager_tabq.py`・`v6_phase2_md_walk.py`・`v6_phase3_jp_contact.py`・`v7_test_fork.py` の 6 本で、
`--help` で引数を確認できる。残りの 6 本（`render_3body.py`、`render_3body_v4.py`、`render_3body_v5.py`、`build_3body_arena.py`、`run_3body.py`、
`v7_failures_video.py`）は引数なしで実行する。

### 4.12 集計スクリプト

`analysis/` の次の 7 本は、同梱の評価 JSON と学習記録を読んで表を印字するだけで、ファイルは書かない。いずれも数秒で終わる。

| コマンド | 所要時間 | 出力 | 照合先の数値 |
|---|---|---|---|
| `python analysis/skill_stats.py out/manager_runs/baselines_v4/eval_rule.json` | 数秒 | 標準出力：手ごとの結果の内訳 | PUSH n=30 のうち `pushed_up` 22・`fell` 5・`stalled` 3（評価 v4 の固定ルールで押し上げの精度 22/30） |
| `python analysis/failures.py out/manager_runs/baselines_v4/eval_rule.json` | 数秒 | 標準出力：失敗した話の一覧 | 固定ルールの失敗は 1 話（seed 5021、`toe_seated_wrong`） |
| `python analysis/curve.py out/manager_runs/tabq2_small/train_curve.json` | 数秒 | 標準出力：学習曲線の五分位 | 120 話、成功 12/24 から 20/24 |
| `python analysis/curve.py out/manager_runs/ppo2_v22/train_curve.json` | 数秒 | 同上 | 766 話（`train_summary.json` の `episodes` と一致） |
| `python analysis/train_stats.py out/manager_runs/ppo2_medium2` | 数秒 | 標準出力：行動の内訳と成功率の五分位 | 12 並列、1 並列あたり 1008 決定 |
| `python analysis/fallen_stats.py out/manager_runs/ppo2_medium2` | 数秒 | 標準出力：転んだ相手への行動の五分位 | 転倒状態での決定の内訳 |
| `python analysis/after_push_fail.py ppo2_medium2 ppo2_medium3`、`python analysis/fallen_value.py ppo2_medium2` | 数秒 | 標準出力 | 押しの失敗の直後に何を選んだか、その後の収益 |

`train_stats.py`・`fallen_stats.py`・`after_push_fail.py`・`fallen_value.py` は決定ごとの記録 `train_env*.jsonl` を読むので、支配人 v2 の記録が
同梱されている ppo2_medium2 と ppo2_medium3 に使う（§3）。`after_push_fail.py` を引数なし（既定は `eval` を含む）で動かすと、旧コースの評価の決定ログ
（`baselines_v2/eval_decisions.jsonl` など、非同梱）を読みに行って止まる。

## 5. 既知の注意

### 5.1 文字コード

argparse の `--help` は ASCII だけで書いてあり、cp932（日本語 Windows の既定）のコンソールでも文字化けしない
（argparse を持つ 27 本、`archive/` の 6 本を含む。サブコマンドを合わせた 37 通りの `--help` で非 ASCII のバイト 0、終了コード 0 を確認した）。
一方、進行表示と出来事の印字には日本語（パッカンの状態、支配人の吹き出し）が含まれる。出力をファイルやパイプに送ると、Windows ではロケールのコードページで書かれる。
英語版 Windows（cp1252）など日本語を表せないコードページでは UnicodeEncodeError で止まり、cp932 で保存したログは UTF-8 で開くと文字化けする。
環境変数 `PYTHONUTF8=1` または `PYTHONIOENCODING=utf-8` を設定して実行する。報告 JSON などファイルへの書き出しはすべて UTF-8 で行う。

### 5.2 日本語フォント

字幕・吹き出し・顔モニターの文字は `v6_common.py` の `_FONTS`（Windows のフォントフォルダの meiryo.ttc／YuGothM.ttc／msgothic.ttc）を順に探す。
見つからないときは Pillow の既定フォントに退避し、日本語は表示できない。他の OS では日本語 TrueType フォントのパスを `_FONTS` に足す。
フォントは描画だけに使うので、物理と報告 JSON には影響しない。
`analysis/face_sheet.py` は退避を持たず、`_FONTS` のどれも無いと Pillow のフォント読み込みで止まる（OSError）。

### 5.3 描画時の mj_forward は物理経路の一部

`v7_full.py` の `render_frame()` はフレームを描く前に毎回 `mujoco.mj_forward` を呼ぶ。この呼び出しはソルバーのウォームスタートを更新するので、物理の経路はフレームの刻みに依存する。
その結果、(1) ヘッドレス（`--test`、sim 385.6 s）と描画版（sim 404.22 s）は出来事の順序と結果が同じでも時刻は一致しない。
(2) 描画版どうしは、フレームの標本周期が同じなら同一になる。省略区間と 4 倍速の施工では `render_frame(write=False)` で描かずに forward だけ毎フレーム呼ぶため、
§4.1 と §4.2 の `state_digest` が一致する。(3) 標本周期を変えた最初の 4 倍速実装（`out/v7_full_report_take50.json`）は別の経路になった。
報告 JSON の時刻を語るときは、どの版の値かを添える。

### 5.4 決定性と再現の範囲

物理はコードと入力が同じなら決定的で、乱数は `v7_full.py` 内部で固定している（`default_rng(11)`、Q 表の同点の手を選ぶ乱数に `default_rng(1)`）。
台本と支配人が同じ（`--manager`・`--run`・`--ending`・`--finale` が同じ）まま経路だけを変える引数は `--jitter` である。
`--manager`・`--run`・`--ending`・`--finale`・`--no-prestage`・`--rescue-max`・`--dt-build`・`--dt-action` は台本・支配人・時間刻みそのものを変えるので、経路も変わりうる
（例：`--finale` だけが違う提出版と追走版は、支配人の 5 手と時刻までは同一で、最終状態の digest が異なる）。
描画だけの引数（`--build-speed`・`--no-cuts`・`--no-face`・`--face-ai`）は経路を変えないことを確認した（§4.2、§4.3）。

作者の環境（Windows 11、CPU のみ）では、物理の条件が同じ報告どうしで `state_digest` が一致することを確認した
（施工 2 倍速と 4 倍速の提出版の組、ヘッドレス 6 本がすべて `c083a03c2625`、§4.3）。別の機械での一致は確かめていない。
同じ MuJoCo 3.11.0、同じ course-builder commit、同じ CPU 向けビルドなら別の機械でも一致すると考える。
別の版や別の CPU では浮動小数の差で digest が一致しない可能性があり、その場合は出来事の順序・支配人の手・3 体の渡り切りで照合する。

### 5.5 実行環境

- `mujoco.Renderer` のオフスクリーン描画は Windows でだけ確認した。Linux では環境変数 `MUJOCO_GL`（egl または osmesa）の指定が必要になる場合がある。
- 起動時に `WARNING: Attach conflict when attaching 'jumper' to 'arena_v6'` と `timestep: parent has 0.005, child has 0.001, keeping parent value` が出る。
  跳跳の MJCF を結合するときの時間刻みの衝突で、舞台側の値を使う想定どおりの表示である（施工完了後に 0.001 s へ切り替える）。
- 学習と評価は長い（PPO 4 時間超、評価 1 方策 30 分）。先に §4.3 のヘッドレス検証（約 1.5 分）で環境を確かめる。
- `v7_full.py --manager ppo` の `--run` の既定値は `ppo2_small`（初期の小規模 run、同梱）で、提出動画の方策ではない。PPO 版は `--run ppo2_v22` を明示する。
- `analysis/face_check.py` は表情ログの行を 3 要素として読む。現行コードの 5 要素の報告 JSON での振る舞いと確かめ方は §4.3 のとおり。
- `v7_full.py` は音声なしの `*_silent.mp4` と `*_chirps.wav` を中間物として `out/` に残す。`.gitignore` がこの 2 種を除外する（合成後の MP4 は除外しない）。

## 6. 追跡の点検

§4 のコマンドが clone 直後に成立するために、本リポジトリに含まれていなければならないもの。

| 用途 | 必要なファイル |
|---|---|
| 提出動画の描画・ヘッドレス検証 | `policies/microduck/*.onnx`、`manifest.json`、`out/manager_runs/mood_net/mood_net.pt`・`meta.json`、PPO 版は `out/manager_runs/ppo2_v22/ppo_manager.zip`、Q 表版は `tabq2_small/tabq.json` |
| 照合（報告 JSON） | `out/v7_full_report_take46.json`〜`out/v7_full_report_take54.json`、`out/v7_full_report_facecheck_A.json`・`_B.json`、`moodcheck_B.json`〜`_E.json` |
| 照合（動画） | `out/3body_arena_v7_take51.mp4`〜`out/3body_arena_v7_take54.mp4`（提出版は §4.7 の静止画の切り出しにも使う） |
| 照合（ログ） | `out/v7_take51render.log`、`out/v7_facecheck_A.log`、`out/v7_crab_push_cross.log`、`out/manager_runs/mood_data.log` |
| 照合（スクリプト） | `analysis/timeline_times.py`（§4.1・§4.3・§4.8）、`analysis/face_check.py`（§4.3） |
| 学習環境・単体実験 | `out/v6_stage_built.xml` |
| 学習の記録 | `out/manager_runs/{ppo2_medium2,ppo2_v22}/train_summary.json`・`train_curve.json`、`tabq2_small/train_curve.json` |
| 学習の記録（続き） | `ppo2_medium2`・`ppo2_medium3`（v2）と `ppo_small`・`ppo_smoke2`・`ppo_smoke3`（v1）の `train_env*.jsonl`、`docs/devlog/README_development.md`（seed の出所） |
| 評価と比較表 | `out/manager_runs/{baselines_v4,ppo2_v22_v4,ppo2_medium2_v4,tabq2_small_v4}/eval_*.json`、`eval_summary.json`、`comparison_v4.md` |
| 気分ネットの再学習と記録 | `out/manager_runs/mood_data.npz`、`mood_data_episodes.json`、`mood_net/report.md`、`face_value.json`・`face_value.md` |
| 図 | `report/*.png` |

隣接 3 リポジトリ（§2）と跳跳の公式バンドル（§2.1、jumper リポジトリに同梱）は本リポジトリに含まれないので、clone の後に別途そろえる。
