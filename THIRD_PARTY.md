# 第三者資産とライセンス

本リポジトリのコード・文書・学習済みモデル・評価の生成物は MIT ライセンスで公開する（`LICENSE`、Copyright (c) 2026 ortiz-ai-partners）。
ただし第三者資産（`policies/microduck/` に同梱する公式 ONNX と `manifest.json` ほか、下の一覧）は除き、それぞれの配布元の条件に従う。
第三者のコードから書き写した転記部分は、転記元の Apache-2.0 の条件にも従う。

本作はパッカン（Microduck, Pollen Robotics）、跳跳（Jumper, KingKong Robotics）、ブルドーザー（BZ、自作 course-builder）と、公式 ONNX ポリシー 5 本を 1 つの MuJoCo ワールドで動かす。
この文書は、そこで使う第三者資産の出典・版・ライセンス・本作での使い方・同梱の有無と、AI の使用をまとめる。
動画と静止画は CC BY-NC-SA 4.0 で扱う。理由と範囲は「本リポジトリで作成したもの」の節に書く。

## 読み方

- 「同梱」は本リポジトリに実体ファイルを含むかを指す。同梱しない資産は隣接リポジトリとして親ディレクトリに並べて読む（配置は `docs/reproduce.md`）。
- 使い方の列の先頭に区分を付ける。既製＝第三者が配布したものをそのまま使う、自作＝本プロジェクトで作成、転記＝第三者のコードの一部を本リポジトリのコードに書き写した。
- commit は各隣接リポジトリで `git log -1` が示す値。本作が読むコードとシーン（MJCF・メッシュ・ONNX・契約 JSON・import するモジュール）に未 commit の変更はない（`git status` で確認）。
- 出所として引く隣接リポジトリの文書（README など）も、上の commit の版を指す。
- Apache-2.0 の本文は http://www.apache.org/licenses/LICENSE-2.0 にある（各隣接リポジトリの `LICENSE` も同じ本文）。

## 一覧

| 名称 | 出典 | 版 | ライセンス | 本作での使い方 | 同梱 |
|---|---|---|---|---|---|
| Microduck 公式 ONNX `velstand`・`alpha_sitstand`（Pollen Robotics） | Hugging Face `pollen-robotics/microduck-policies` | export 2026-10-12・2026-10-01 | 配布元の表示は未確認（下の節） | 既製。推論のみ、改変なし | あり |
| Microduck 公式 ONNX `alpha_walking`・`alpha_stand` | 同上 | `manifest.json` に学習元の記載なし | 配布元の表示は未確認（下の節） | 既製。未使用 | あり |
| `policies/microduck/manifest.json` | 同上 | 取得時のまま | 配布元の表示は未確認（下の節） | 既製。版情報の参照のみ、改変なし | あり |
| Microduck の MJCF（`microduck_rl`） | https://github.com/pollen-robotics/microduck_rl | commit b02fdea | Apache-2.0 | 既製。MJCF を読み込むのみ、改変なし | なし |
| Microduck の 3D メッシュ（`assets/*.stl`） | 同上 | 同上 | CC BY-NC-SA 4.0 | 既製。描画のみ（動画と図に映る） | なし |
| Microduck の観測契約（`scripts/infer_policy.py`） | 同上 | 同上 | Apache-2.0 | 転記。`v7_policies.py` に書き写した | 転記部分のみ |
| Jumper の MJCF とメッシュ（KingKong Robotics） | https://github.com/KingKongRobotics/jumper | commit 61d0652 | Apache-2.0 | 既製。MJCF を読み込むのみ、改変なし | なし |
| Jumper 公式 ONNX `locomotion`・`jump`・`dance_crab` と契約 JSON | 同上 `out/bundle_example/jumper/` | 同上（初版 004afda から不変） | Apache-2.0 | 既製。推論のみ、改変なし | なし |
| Jumper の観測契約と定数（`obs.rs`・`trajectory.rs`・`constants.py`） | 同上 | 同上 | Apache-2.0 | 転記。`v7_policies.py`・`v6_robots.py` に書き写した | 転記部分のみ |
| physical-ai-course-builder（ブルドーザー） | https://github.com/ortiz-ai-partners/physical-ai-course-builder | commit ea5b4e7 | MIT | 自作（同じ作者の別リポジトリ）。import して使う | なし |
| rsplan（course-builder が同梱） | https://github.com/builtrobotics/rsplan | commit 47b3ab5 | MIT | 既製。本作の実行経路からは呼ばれない | なし |
| Python パッケージ 10 本と Python 本体 | 下の「Python パッケージ」 | `requirements.txt` | 各ライセンス | 既製。pip で導入 | なし |

## Microduck（Pollen Robotics）

### 公式 ONNX ポリシー（`policies/microduck/`）

出典は Hugging Face の `pollen-robotics/microduck-policies`（https://huggingface.co/pollen-robotics/microduck-policies ）。
`velstand.onnx` がこの Hub の公式セットの版 v8 に当たることは `../microduck_rl/docs/velstand_policy.md` に記載がある。
同梱は ONNX 4 本と `manifest.json` の 5 ファイル。`manifest.json` は公式セット 10 本を列挙する第三者ファイルで、改変せずに置く（同梱しない 6 本の記述もそのまま残る）。

| ファイル | 本作 | 学習元（`manifest.json` の `policies[].training`） | SHA-256（先頭 16 桁） |
|---|---|---|---|
| `velstand.onnx` | 使用：歩行・立位・転倒からの起立 | commit 3750776、branch improve_standup_velstand、checkpoint 2749、export 2026-10-12 | `2fc7f8ee6acd7d0d` |
| `alpha_sitstand.onnx` | 使用：座る・立つ | commit 77ffadf、branch sitstand_no_fall_back、checkpoint 2250、export 2026-10-01 | `a6f102d9fd655782` |
| `alpha_walking.onnx` | 未使用 | 記載なし | `e36332d383997d51` |
| `alpha_stand.onnx` | 未使用 | 記載なし | `1569268713e40dee` |
| `manifest.json` | 版情報の参照のみ | — | `8ca3664ad87b852d` |

全桁は `sha256sum policies/microduck/*` で確かめられる。ONNX 4 本はいずれも入力 61 次元・出力 14 次元で（ONNX のグラフ、`manifest.json` の `obs_len`・`action_len`）、制御は 50 Hz（同 `robot.control_hz`）。
使用する 2 本は `v7_full.py` の `Duck.__init__` が開く（`POLICY_DIR`）。歩行・起立・座り込みの出来は提供元のポリシーの成果であり、本作はそれに指令を与えて呼び分ける。
アクチュエータは MJCF の公式サーボ値のまま使う（`robot_groundcontact.xml` の `chosen_actuator`：kp 0.55、±0.96 N·m。`v7_full.official_md_servos`）。

`alpha_walking.onnx` と `alpha_stand.onnx` は、`../microduck_rl/docs/velstand_policy.md` の Lineage 表で、`velstand` の学習の歩行と起立の教師として名前が挙がる旧ポリシーである。
本番の台本と学習環境はこの 2 本を読み込まない（コード中に参照なし）。単体試験 `v7_test_microduck.py` は `--policy` で任意のファイルを選べるが、既定は `velstand.onnx`。
取得時のセットの整合を保つため削除せず、ここで未使用と明記する。

ライセンス：配布元（Hugging Face `pollen-robotics/microduck-policies`）のライセンス表示は確認できていない。
`manifest.json` にライセンスの項目はなく、学習コードの `microduck_rl` は Apache-2.0。
本リポジトリでの同梱は配布元の表示に従い、表示が無い場合は同梱をやめて取得手順に置き換える。

### MJCF モデルと 3D メッシュ（`microduck_rl`）

出典は https://github.com/pollen-robotics/microduck_rl 、使用 commit b02fdea。
読み込むのは `src/mjlab_microduck/robot/microduck/scene.xml`（`robot_groundcontact.xml` を include、`v6_common.MD_XML`）。
`MjSpec.attach` で接頭辞 `md-` を付けて 1 ワールドに結合する（`v6_robots.build_arena`）。ファイルは改変せず、同梱しない。

ライセンスは 2 層ある。MJCF（`.xml`）と設定（`.json`）は Apache-2.0（同リポジトリ `LICENSE`、Copyright 2026 Pollen Robotics）。
`src/mjlab_microduck/robot/microduck/assets/*.stl` の 3D メッシュは CC BY-NC-SA 4.0（同 `LICENSE-MODELS.md`）。
メッシュは描画にだけ使い、提出動画と報告書の図に Microduck の外観が映る。メッシュの実体は再配布しない。
帰属表示：Microduck 3D model by Pollen Robotics（https://github.com/pollen-robotics/microduck_rl ）、CC BY-NC-SA 4.0（https://creativecommons.org/licenses/by-nc-sa/4.0/ ）、メッシュは改変なし。

### 観測契約の転記（`scripts/infer_policy.py`）

`v7_policies.MicroduckPolicy` は `microduck_rl/scripts/infer_policy.py` の観測の並びを MuJoCo 直接の Python に書き写した。
並びは gyro 3、projected_gravity 3、関節位置と既定姿勢の差 14、関節速度 14、前回の行動 14、指令 3 または 13 で、61 次元の版は指令 13 次元（`MicroduckPolicy.command`）。
既定姿勢（`infer_policy.py` の `DEFAULT_POSE` → `v7_policies.MD_DEFAULT_POSE`）と行動の変換（target = default + action × scale）も同じ元から書き写した。
転記元は Apache-2.0（`microduck_rl` の `LICENSE`、Copyright 2026 Pollen Robotics。本文は http://www.apache.org/licenses/LICENSE-2.0 ）。
帰属表示をこの節で行い、転記部分はこの条件に従う。`infer_policy.py` のファイル自体は含まない。

## Jumper（KingKong Robotics）

### MJCF・メッシュ・公式ポリシーバンドル（`jumper`）

出典は https://github.com/KingKongRobotics/jumper 、使用 commit 61d0652。ライセンスは Apache-2.0（同リポジトリ `LICENSE`・`NOTICE`）。
同リポジトリの `NOTICE` の冒頭は次の 2 行で、Apache-2.0 の求めに従いここに写す：「Jumper / Copyright 2026 KingKong Robotics.」「Licensed under the Apache License, Version 2.0 (see LICENSE).」
`NOTICE` が挙げる第三者部分（`rl/mjlab/`、`rl/rsl_rl/`、MuJoCo Menagerie のロボットなど）は本作では使わない。

MJCF は `assets/jumper/jumper.xml`（`v6_common.JP_XML`）で、メッシュは同じ階層の `meshes/` と `urdf/jumper/meshes/visual/` にある。接頭辞 `jp-` を付けて結合する。
ファイルは改変しない。位置アクチュエータの追加は本リポジトリ側で行う（`v6_robots.build_arena`）。同梱しない。

公式ポリシーは同リポジトリが git で配布する例示バンドル `out/bundle_example/jumper/` から読む（`v7_policies.JP_BUNDLE`）。
バンドルは 55 ファイルで、初版 commit 004afda から変更がない（`git log -- out/bundle_example/jumper`）。使うのは次の 3 組。

| モード | 契約 JSON と ONNX | 参照軌道 | 入力→出力 | 制御 | チェックポイント（`_checkpoint`） |
|---|---|---|---|---|---|
| locomotion | `locomotion.json`、`models/locomotion.onnx` | なし | 415 → 20 | 200 Hz、kp 10 / kd 0.5 | jumper.posture `model_74800` |
| jump | `jump.json`、`models/jump.onnx` | `high_jump_flat.trajectory.json` | 167 → 20 | 200 Hz、kp 20 / kd 0.5 | jump `model_3100` |
| dance_crab | `dance_crab.json`、`models/dance_crab.onnx` | `demo.motion.trajectory.json` | 209 → 22 | 50 Hz、kp 10 / kd 0.5 | jumper.dance `model_2300` |

入力次元は各 JSON の `observation.dim` と ONNX のグラフ、制御は同 `control`（`control_hz`・`kp`・`kd`）。バンドルの他のファイル（claw、gesture、他のダンス、`runtime/`）は使わない。
使い方は推論のみで、重み・観測・制御周期を変えていない。歩行・ジャンプ・ダンスの出来は提供元のポリシーの成果である。
前方へのジャンプは、公式 `jump` の出力に股関節ヨー（J0）の関節目標を跳躍の位相に合わせて足す本リポジトリ側の追加である（`v7_policies.JumperJump` の `SWEEP_SIGN`・`SWEEP_PHASES`）。
足すのは関節目標だけで、外力は使わない。ONNX の改変ではない。

### 観測契約と定数の転記

`v7_policies.py` は `deploy/fsm/src/obs.rs` の観測の組み立て（`projected_gravity` ほか）と、`trajectory.rs` の参照軌道の索引（終端で止め、巻き戻さない）を Python に書き写した。
転記元は `v7_policies.py` のモジュール docstring、`projected_gravity`、`JumperDance` の docstring に記す。
`v6_robots.JP_HOME`（22 関節の HOME 姿勢）、`JP_STAND_Z`（0.10647 m）、`JP_KP`・`JP_KD`・`JP_EFFORT`（10・0.5・1.7464 N·m）は、
`tasks/jumper/common/constants.py` の `HOME`・`STAND_Z`・`STIFFNESS`・`DAMPING`・`EFFORT_LIMIT` の写しである。

転記元は Apache-2.0（`jumper` の `LICENSE`・`NOTICE`、Copyright 2026 KingKong Robotics。本文は http://www.apache.org/licenses/LICENSE-2.0 ）。
帰属表示は上に写した `NOTICE` の 2 行とこの節で行い、転記部分はこの条件に従う。Rust と Python の元ファイル自体は含まない。

### 表情ディスプレイの参考

実機の Jumper は 0.9 インチの丸型 TFT の表情ディスプレイを 2 つ備える（`../jumper/docs/HARDWARE.md`）。公式リポジトリはダンス課題の表情アニメーション 1 本を含む（`tasks/jumper/dance/media/demo.mp4`）。
本作の表情の絵は本リポジトリが Pillow で描いたもので（`crab_face.py`）、キラキラの四芒星の形だけ公式アニメーションに倣った（`crab_face._star`）。
表示板の土台は作者が以前に作った表情表示の道具で、公式リポジトリには含まれない（`crab_face.py` のモジュール docstring）。
公式リポジトリに機体の状態から表情を選ぶ API はなく、表情の選び方（気分ネットと優先規則）と表示板の取り付けは本リポジトリの設計である。

## physical-ai-course-builder（ブルドーザー）と rsplan

出典は https://github.com/ortiz-ai-partners/physical-ai-course-builder 、使用 commit ea5b4e7。
本リポジトリと同じ作者が同じ課題のために作成した自作リポジトリで、MIT（同リポジトリ `LICENSE`、Copyright (c) 2026 ortiz-ai-partners）。
本作は `sys.path` 経由で `app`（`Simulation`）、`slope_assembly`（`assembly_xml`・`SlopeAssembly`）、`tracks`、`navigation`（`Navigator`）を import する（`v6_common.course_builder`、`v7_full.py`）。
ブルドーザーの土台シーンは `scene_fork_tracks.xml`。ブルドーザー側に AI 推論はなく、実行時に LLM も動かない。同梱しない。

course-builder 単体の検証版は MuJoCo 3.3.7（同リポジトリ `requirements.txt`）で、本作は同じモジュールを MuJoCo 3.11.0 で読む。
course-builder は Built Robotics の rsplan（https://github.com/builtrobotics/rsplan 、MIT、Copyright (c) 2023 Built Robotics）を `third_party/rsplan/` に版固定で同梱する。
固定した commit は 47b3ab572a4b7ffc314dfc2aa68b8349f061fe13 で、各ファイルの Git blob SHA-1 の照合表が同 `NOTICE.md` にある。
rsplan を読み込むのは course-builder の `rs_course.py`（とその検証 `verify_rs_course.py`）だけで、本作が使う `app`・`slope_assembly`・`slope_parts`・`parts`・`transport`・`navigation`・`tracks` からは呼ばれない。

## Python パッケージ

| パッケージ | 版 | ライセンス | 出典 | 本作での用途 |
|---|---|---|---|---|
| mujoco | 3.11.0 | Apache-2.0 | https://github.com/google-deepmind/mujoco | 物理、`MjSpec.attach` による結合、オフスクリーン描画（`mujoco.Renderer`） |
| onnxruntime | 1.23.2 | MIT | https://github.com/microsoft/onnxruntime | 公式 ONNX 5 本の推論（1 セッション 1 スレッド、`v7_policies._session`） |
| stable-baselines3 | 2.9.2 | MIT | https://github.com/DLR-RM/stable-baselines3 | 支配人 AI の PPO の学習と推論（`manager2_train.py`、`v7_full.py --manager ppo`） |
| torch（CPU 版） | 2.14.1 | BSD-3-Clause（注 1） | https://github.com/pytorch/pytorch | 気分ネットの学習と推論（`analysis/mood_train.py`、`crab_face.MoodAI`）、SB3 の基盤 |
| gymnasium | 1.0.0 | MIT | https://github.com/Farama-Foundation/Gymnasium | 学習環境の API（`manager2_env.py`） |
| numpy | 2.2.6 | BSD-3-Clause | https://github.com/numpy/numpy | 数値計算 |
| imageio | 2.38.0 | BSD-2-Clause | https://github.com/imageio/imageio | 動画フレームの書き出し（`v6_common.Video`、libx264） |
| imageio-ffmpeg | 0.6.0 | BSD-2-Clause（注 2） | https://github.com/imageio/imageio-ffmpeg | ffmpeg 実行ファイルの提供。音声の合成も同じ ffmpeg を別プロセスで呼ぶ（`v7_full.py`） |
| Pillow | 12.3.0 | MIT-CMU | https://github.com/python-pillow/Pillow | 字幕・顔モニター・表情の描画（`v6_common.Captioner`、`crab_face.py`） |
| glfw | 2.10.2 | MIT（注 3） | https://github.com/FlorianRhiem/pyGLFW | course-builder の `app.py` が import する。本作は窓を開かない |

版は `requirements.txt` と同じで、開発環境の pip のメタデータで確かめた。ライセンス名は各パッケージの配布メタデータ（`License-Expression`、`License`、classifier）から取った。
Python 本体は 3.10（3.10.6 で確認、PSF License）。上の 10 本が引き込む依存（cloudpickle など）は各配布物のライセンスに従う。いずれも pip で導入し、本リポジトリには同梱しない。

- 注 1：PyTorch 本体の `LICENSE` は BSD-3-Clause 形式。配布物は第三者部分を含み、配布メタデータの `License-Expression` は Apache-2.0・BSD-2-Clause・MIT などを並べた複合表記である。
- 注 2：imageio-ffmpeg が同梱する ffmpeg 7.1 の実行ファイルは `--enable-gpl --enable-version3` の構成で、FFmpeg の GPL-3.0 の条件に従う。本作はこれを別プロセスとして呼ぶだけで、リンクも再配布もしない。
- 注 3：glfw パッケージが同梱する `glfw3.dll` は GLFW 本体（zlib/libpng ライセンス）。

字幕の文字は Windows 同梱の日本語フォント（Meiryo、Yu Gothic Medium、MS Gothic のうち最初に見つかったもの、`v6_common._FONTS`）を描画時に読む。
フォントは再配布しない。見つからない環境では Pillow の既定フォントに切り替わる（`v6_common.Captioner`）。

## 本リポジトリで作成したもの

上の第三者資産と転記部分を除くコードは、すべて本プロジェクトで作成した。
学習済みの支配人 AI（`out/manager_runs/ppo2_v22/ppo_manager.zip`、`out/manager_runs/tabq2_small/tabq.json` ほか）と気分ネット（`out/manager_runs/mood_net/`）も本プロジェクトの成果物である。
評価の生成物（`out/manager_runs/*.md`、`*.json`）と報告 JSON（`out/v7_full_report_take57.json` など）も含め、MIT で公開する。
動画の効果音は `v7_full.py` の `Chirps` と `intro.py` が合成するもので、BGM は `music/marimba_bgm.py` が numpy/scipy の加算合成だけで作る自作曲である。第三者の音源・既存の曲・サンプルは使わない。提出動画の最初と最後の講座の OP／ED カード（計 6 s、音声なし）は講座が配布した素材で、本リポジトリには含めない。

動画と静止画も本プロジェクトで作成した。動画は `out/` 以下の `*.mp4` のすべてで、提出動画の本編は `out/3body_arena_v7_take57.mp4`、自己紹介は `out/intro.mp4`、
本編と物理が同一の以前の 2:47 版は `out/3body_arena_v7_take51.mp4`、PPO 版・Q 表版・追走版は `out/3body_arena_v7_take52.mp4`・`out/3body_arena_v7_take53.mp4`・`out/3body_arena_v7_take54.mp4`。
静止画は報告書の図（`report/*.png`）、差し替え前の図と元データ（`docs/devlog/figures/`）、表情の確認画像（`out/face_test/`）である。
これらの多くに Microduck（CC BY-NC-SA 4.0 のメッシュ）と Jumper（Apache-2.0）の外観が映る。
そのため動画と静止画は一律に、コードの MIT ではなく CC BY-NC-SA 4.0 の条件（帰属・非営利・継承）で扱う。帰属表示は「MJCF モデルと 3D メッシュ」の節のとおり。

## AI の使用

作品名〈アイランドマスター〉は、開発を補助した LLM の呼び名でもある。動画の中で次の一手を選ぶのは常に支配人 AI であり、LLM はシミュレーションの実行時には動かない。

### 本番で推論する AI

提出動画の中で推論しているのは次の 7 つで、すべて同じシミュレーション時間の中で動く。

| AI | 区分 | 学習 | 入力→出力・周期 | 役割 |
|---|---|---|---|---|
| Microduck `velstand` | 既製（Pollen Robotics）、推論のみ | 提供元 | 61 → 14、50 Hz | パッカンの歩行・立位・転倒からの起立 |
| Microduck `alpha_sitstand` | 既製（Pollen Robotics）、推論のみ | 提供元 | 61 → 14、50 Hz | パッカンの座り込みと起立 |
| Jumper `locomotion` | 既製（KingKong Robotics）、推論のみ | 提供元 | 415 → 20、200 Hz | 跳跳の歩行・旋回 |
| Jumper `jump` | 既製（KingKong Robotics）、推論のみ | 提供元 | 167 → 20、200 Hz | 跳跳のジャンプ（前方成分は本リポジトリ側の関節目標の追加） |
| Jumper `dance_crab` | 既製（KingKong Robotics）、推論のみ | 提供元 | 209 → 22、50 Hz | 跳跳のダンス |
| 支配人 AI | 自作 | 固定ルール版は学習なし、PPO 版・Q 表版は学習 | 46 → 6 手、前の手が終わるたびに 1 回 | 失敗したときの次の一手を選ぶ |
| 気分ネット | 自作 | 学習 | 53 → 5、救助中に支配人の手を実行している間の毎制御ステップ | 跳跳の表情の元になる 5 つの値を推論する |

支配人 AI の観測は 46 次元（`crab_help.py` の `OBS_DIM`）、手は 6 つ（同 `ACTIONS`）。提出動画は固定ルール版で（`crab_help.rule_action`）、5 手を打った（`out/v7_full_report_take57.json` の `manager.decisions`）。
気分ネットは 53-32-32-5 の MLP で（`analysis/mood_train.py` の `MoodNet`、`out/manager_runs/mood_net/meta.json` の `n_in`・`hidden`・`n_out`）、提出動画では 5,236 回推論した（同 JSON の `face.mood_ai.inferences`）。
出力は 4 つの結末の確率と「渡れる」の確率である（`crab_face.MoodAI` の `KEYS`）。ブルドーザーは規則制御で、AI 推論はない。

顔・字幕・気分ネットは描画専用で物理を変えない。試験走行（`v7_full.py --test`）で 2 つの比較をして確かめた。
顔なしと顔あり（表情は固定の表、`--face-ai table`）では、最終状態の digest と支配人の手が一致する
（`out/v7_full_report_facecheck_A.json` と `_B.json` の `state_digest`・`manager.decisions`、`analysis/face_check.py`）。
気分ネットありの通し（`out/v7_full_report_moodcheck_C.json`、推論 4,518 回は `face.mood_ai.inferences`）も、digest・判断・モード変化が顔なしと一致する。
出来事の文言が 1 件だけ違うため、`analysis/face_check.py` はこの対で終了コード 1 を返す（`docs/mood_net_and_faces.md`）。

### 学習した AI

学習したのは支配人 AI の 2 方式と気分ネットで、いずれも CPU で学習した（`manager2_train.py` の `device="cpu"`、torch は CPU 版）。
PPO 版は Stable-Baselines3 の PPO（`MlpPolicy`、`net_arch` [64, 64]、`manager2_train.py`）。12 並列で計 12,000 決定を学習し、報酬 v2.2 でさらに 12,000 決定を続けた。
学習量の出所は `out/manager_runs/ppo2_medium2/train_summary.json` と `out/manager_runs/ppo2_v22/train_summary.json`（`envs`・`steps`・`init_from`・`reward`）。
Q 表版は本リポジトリで実装した表形式 Q 学習で（`manager2_tabq.py`）、学習環境の 120 話から学んだ（`out/manager_runs/tabq2_small/train_curve.json` の件数）。

気分ネットは PyTorch で、学習環境の 35 話・47,952 サンプルから学習した（`out/manager_runs/mood_net/meta.json` の `n_episodes`・`n_samples`）。
評価 v4（同じ 30 シード）の渡り切りは固定ルール 29/30、PPO v2.2 26/30、Q 表 25/30（`out/manager_runs/comparison_v4.md`）。
学習方式は固定ルールに届いておらず、提出動画には固定ルール版を使った。PPO 版と Q 表版は別の動画として公開する。

### 開発補助の AI

本リポジトリの設計・実装・文書は、作者が LLM（Anthropic の Claude、Claude Code）の支援を受けて作成した。
ブルドーザー側の course-builder の開発では、OpenAI の Codex の対話型セッションも使った。
坂と門の配置の計画 JSON と、施工結果を読んだ評価はそのセッションが作成した（同リポジトリ commit ea5b4e7 の `README.md` L349、
`examples/ortiz-slope-plan.json`・`examples/ortiz-gate-plan.json` の `provenance`、`examples/ortiz-slope-review.json`）。
本作はその計画 JSON を読まず、坂の配置は `slope_assembly.assembly_xml` の定数で決まる。

報告書の図のうち 6 枚（`report/*_ortiz.png`）は、本プロジェクトで書いた数値入りの依頼文をもとに、
開発補助の LLM とは別の対話型 AI が清書した（AI の名称・版は記録していない）。
`report/faces_sheet_ja.png` は `analysis/face_sheet.py` が描く。

図中の数値と規則は `crab_face.py`、`crab_help.py`、報告 JSON、`out/manager_runs/comparison_v4.md` と照合した（記録は `docs/devlog/face_rules_chart.md`）。
照合で見つかったずれは `docs/devlog/README.md` の訂正表に記す：全体図は公式ポリシー 5 本のうち 4 本分の次元だけを載せる（訂正表 14）、
気分ネットの図の「CPU 1 分」は学習ループ（3.5 s、`out/manager_runs/mood_net/meta.json` の `train_s`）でなくスクリプト全体の目安（訂正表 8）。
タイムライン図と全体図は提出版に合わせて描き直した（訂正表 6、旧図は `docs/devlog/figures/`）。

公式ポリシーが見せる歩行・ジャンプ・ダンスの出来は提供元の成果である。
本作で作成したのは、3 体の統合、失敗したときの次の一手を選ぶ支配人 AI、表情を推論する気分ネットである。
