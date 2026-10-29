# 技術ノート：3 体を 1 つの MuJoCo ワールドに統合する

本ノートは、ブルドーザー（BZ、自作 physical-ai-course-builder）、パッカン（Microduck, Pollen Robotics）、跳跳（Jumper, KingKong Robotics）の
3 つの MJCF モデルを 1 つの MuJoCo 3.11.0 ワールドに結合し、公式 ONNX ポリシー 5 本（Microduck 2 本、Jumper 3 本）を推論のみで動かすための実装上の要点をまとめる。
数値には出所（ファイル名と関数・定数名、JSON のキー）を併記する。開発中の経緯は [docs/devlog/HANDOVER.md](devlog/HANDOVER.md) に原文のまま残してある。

読む順の目安：全体像は [README.md](../README.md)、支配人 AI は [docs/manager_ai.md](manager_ai.md)、表情と気分ネットは [docs/mood_net_and_faces.md](mood_net_and_faces.md)、再現は [docs/reproduce.md](reproduce.md)。
用語の対応は [docs/glossary.md](glossary.md)、外部資産の版とライセンスは [THIRD_PARTY.md](../THIRD_PARTY.md)。

## 1. 構成の全体

| 機体 | MJCF の出典（版） | 結合方法 | アクチュエータ | 動かしているもの |
|---|---|---|---|---|
| ブルドーザー（BZ） | 自作 course-builder のシーン（commit `483dbf9`） | 土台（接頭辞なし） | シーンのまま：速度 4 本 `drive_*`、フォークの位置 1 本 `blade_lift` | ルール制御（`SlopeAssembly`／`Navigator`）、AI なし |
| パッカン（MD） | `microduck_rl` の `scene.xml`（既製、commit `b02fdea`） | `MjSpec.attach(prefix="md-")` | XML の位置サーボ 14 本（kp 0.55、±0.96 N·m） | 公式 ONNX 2 本（推論のみ） |
| 跳跳（JP） | `jumper` の `jumper.xml`（既製、commit `61d0652`） | `MjSpec.attach(prefix="jp-")` | 結合時に追加した位置サーボ 22 本（kp 10、kd 0.5、±1.7464 N·m） | 公式 ONNX 3 本（推論のみ） |

ファイルの場所は `v6_common.py` の定数が示す。`BZ_XML` は `../physical-ai-course-builder/scene_fork_tracks.xml`、
`MD_XML` は `../microduck_rl/src/mjlab_microduck/robot/microduck/scene.xml`、`JP_XML` は `../jumper/assets/jumper/jumper.xml` で、3 つの隣接リポジトリは `BASE`（本リポジトリの親）の下に並べる。
commit は各リポジトリで `git log -1` が示す値（`THIRD_PARTY.md` の一覧と同じ）。
結合後のアクチュエータは BZ 5、パッカン 14、跳跳 22 の計 41 本（`model.nu`）、質量は パッカン 0.74 kg、跳跳 2.54 kg（接頭辞ごとの `body_mass` の合計）。
どちらも本ノート執筆時に `build_arena()` でコンパイルして確かめた値である。

結合は `v6_robots.py` の `build_arena()` が行う。土台 XML は course-builder の `slope_assembly.assembly_xml()` が坂の部材を加えたもので、
`v7_full.py` の `main()` が `build_arena(xml, md_pose=MD_START, jp_pose=JP_PARK, timestep=args.dt_build, face=args.face)` で読み込み、
直後に `official_md_servos(model)` でパッカンのサーボを公式値に戻してから台本を始める（6 節）。

物理ソルバーの設定は土台シーンの `<option>`（`timestep 0.005`、`integrator implicitfast`、`cone elliptic`、`iterations 60`、`scene_fork_tracks.xml` 3 行目）を引き継ぎ、
`build_arena()` は `spec.option.timestep` だけを書き換える。子シーンの `<option>` は取り込まれず、親の値が残る。
MuJoCo 3.11 はこの食い違いを結合時に警告する（`jumper.xml` の `timestep 0.001` に対し「Attach conflict … keeping parent value」）。

外力・テレポートは本番の台本では使わない（`v7_full.py` 冒頭の docstring の原則）。学習環境と単体テストの開始配置だけが例外で、6 節に書く。

## 2. MjSpec.attach の要点

MuJoCo 3.11 の `MjSpec.attach(child, prefix=…, frame=…)` は、子モデルの body 木と asset を接頭辞付きの名前で親に取り込む。
3 つの別々のリポジトリの MJCF を合わせるときに実際に問題になった点を、対処と出所つきで挙げる。

### 2-1. 接頭辞と名前空間

- 土台（BZ のシーン）の名前は無印（`dozer`、`up_1`、`down_1`、`block_1`、`block_2`、`floor`）。パッカンは `md-`、跳跳は `jp-` が付く。
  `build_arena()` が `worldbody` にフレーム `md_origin`／`jp_origin` を足し、`spec.attach(child, prefix=…, frame=f)` で結合する。
- 以後のコードは名前の先頭で機体を見分ける。`v6_robots._prefixed(model, objtype, "md-")` が関節・アクチュエータの一覧を返す。
- 自由関節の名前も変わる：BZ は `base`、パッカンは `md-trunk_base_freejoint`、跳跳は `jp-floating_base`（`manager2_env.Scene.__init__` が名前の先頭で 3 体を判別する）。
  坂 2 枚と箱 2 個も自由物体で（`up_1_free`、`down_1_free`、箱の 2 本は無名）、床に固定されていない。
  押し上げなどで坂がずれれば、それも物理の結果として現れる（学習環境はずれが 4 cm を超えると失敗とする、`manager2_env.COURSE_TOLERANCE`）。
- キーフレームも接頭辞付きになる（パッカンの `md-INIT`／`md-STAND`／`md-SIT`／`md-FOLD`）。`reset_md()` は `md-STAND` を名前で引く。

### 2-2. 自由関節の qpos はワールド座標

`attach` に `frame` を渡しても、自由関節の `qpos[0:3]` と四元数はワールド座標で解釈される。フレームからの相対ではない。
そのため各機体の初期姿勢は機体ごとの reset 関数が直接ワールド座標を書く（`v6_robots.reset_md`／`reset_jp`）。
パッカンは `md-STAND` キーフレームの関節角と `ctrl` だけを `model.key_qpos`／`model.key_ctrl` から読み、位置は引数の `(x, y, yaw)` と高さ `MD_STAND_Z + 0.004`（0.124 m）から作る。
跳跳は `JP_HOME` の関節角と高さ `JP_STAND_Z + 0.005`（0.11147 m）を書き、`ctrl` にも `JP_HOME` を入れる。どちらも `v6_robots.py` の定数である。

### 2-3. 床の重なり（Z-fighting）と照明

- パッカンのシーンは自分の床 `floor`（`scene.xml` の `worldbody`）を持ち込み、`md-floor` として土台の床と同じ高さに重なってちらつく。
  コンパイル後に `geom_contype`／`geom_conaffinity` を 0、`geom_rgba` を透明にして無効化する（`build_arena()`）。跳跳の `jumper.xml` には床がない。
- 子シーンの照明が足されると床が白飛びする（開発記録 `docs/devlog/HANDOVER.md`）ので、土台の 1 灯（0 番、`pos -3 -3 7`）だけを残し、1 番以降を `light_active = 0` にする（同）。
  結合後の照明は 2 灯で、消すのはパッカンの `scene.xml` が持ち込む 1 灯である。`jumper.xml` は照明を持たない。
- 跳跳の衝突メッシュは `class="collision"` で `group="1"`（`jumper.xml`）なので、描画時は `MjvOption.geomgroup[1] = 0` で隠す（`v7_full.main()`）。物理には影響しない。

### 2-4. `mj_resetDataKeyframe` は使わない

`mj_resetDataKeyframe()` はモデル全体の `qpos`／`qvel`／`ctrl` をキーフレームで上書きするので、1 体を戻すと残り 2 体も巻き込まれる。
本リポジトリは機体ごとの reset 関数（2-2 節）を使い、キーフレームは該当関節の値だけを読む。
`mj_resetDataKeyframe` を呼ぶのは単体の読み込みテスト（`test_load_microduck.py`）と初期の結合テスト（`archive/build_3body_arena.py`、`archive/run_3body.py`）だけである。
機体ごとの reset に切り替えたのは `archive/render_3body.py` で、同ファイルの docstring にその理由が残る。

学習環境はエピソードの始めに `mj_resetData()` で `MjData` 全体を初期化し、初期化直後に保存した全体の `qpos`／`qvel`／`ctrl`／`act` を書き戻す（`manager2_env.Scene.reset`、`self.init`）。
`qpos` などだけを戻す初版はソルバーのウォームスタートを前のエピソードから持ち越し、同じシードでも直前に走ったエピソードによって結果が変わった（同メソッドのコメント）。
評価 v3 以降はこの直しでエピソードが独立している。8 節の「`mj_forward` も経路の一部」と同じ根の問題である。

### 2-5. MjSpec の material と texture

MjSpec では `material.texture = "name"` は使えず（MuJoCo 3.11 で `AttributeError`）、`material.textures[role] = "name"` と役割つきで書く。
表情の板の材質は `crab_face.add_face()` が `mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = tex.name` で 11 枚の texture（`jp-face_tex_<表情>`）を
11 の material（`jp-face_mat_<表情>`）に割り当て、表情の切り替えは `crab_face.FaceDriver` が `model.geom_matid` を書き換えて行う。
開発記録と `archive/render_3body.py` にある `textures[0]` は添字で書いた初期の形で、添字 0 は `mjTEXROLE_USER`（値 0）にあたる。色の texture の役割は `mjTEXROLE_RGB`（値 1）なので、現行コードは役割名で書く。

### 2-6. 跳跳にアクチュエータを足す

`jumper.xml` には `<actuator>` がなく、実機側のランタイムが制御する設計になっている。結合時に `build_arena()` が `JP_HOME` の 22 関節へ位置アクチュエータを追加する
（`spec.add_actuator()`、`mjTRN_JOINT`、`mjGAIN_FIXED` の `gainprm[0] = JP_KP`、`mjBIAS_AFFINE` の `biasprm[1] = -JP_KP`、`biasprm[2] = -JP_KD`、`forcerange ±JP_EFFORT`）。
ゲインは公式バンドルの契約と同じ kp 10／kd 0.5／`effort_limit` 1.7464 N·m（`locomotion.json` の `control`、`v6_robots.py` の `JP_KP`／`JP_KD`／`JP_EFFORT`）。
`JP_HOME` は `jumper` の `tasks/jumper/common/constants.py` の `HOME` の転記で、22 値は 3 契約（`locomotion.json`・`jump.json`・`dance_crab.json`）の `default_joint_pos` と一致する。
立位の高さ `JP_STAND_Z` 0.10647 m は同ファイルの `STAND_Z` と契約の `base_height` に一致する（いずれも本ノート執筆時に 22 関節すべてを照合）。

`locomotion` と `jump` の契約は `LF_J4_joint`／`RF_J4_joint` を `unactuated_joints`（0 rad に固定）と定め、行動は残り 20 関節である（ONNX の出力 20）。
`dance_crab` だけは `unactuated_joints` が空で、22 関節すべてに行動を出す（出力 22）。本リポジトリは J4 の 2 関節にも同じ PD アクチュエータを付け、
`locomotion`／`jump` の間は目標 0 rad（既定姿勢の値）で保持する。剛体拘束ではなく PD 保持なので、接触時にわずかに動き得る。
契約の注記は「固定しないと足の接触形状が変わる」とするので、これは実機との差として残る（9 節）。

### 2-7. 描画専用の板と顔カメラ

跳跳の表示板 `jp-display_module_link` に、`contype 0`／`conaffinity 0`／`density 0`／`group 2` のメッシュ geom `jp-face_screen` と顔カメラ `jp-face_cam` を `MjSpec` で足す
（`crab_face.add_face()`、カメラは板の 0.30 m 前、`CAM_DIST`）。板は `density 0` で質量を持たず（体積のない面なので慣性の計算は `mjMESH_INERTIA_SHELL`）、
接触もしないので物理の経路は変わらない。
検証：顔なし（`out/v7_full_report_facecheck_A.json`）と顔あり（`…_facecheck_B.json`）のヘッドレス通しで最終状態のダイジェストが一致し（`c083a03c…`）、
`ngeom` だけ 290→291 である（`analysis/face_check.py`、8 節の表）。

## 3. 公式ポリシーの観測契約（転記）

公式ポリシー 5 本は ONNX を改変せず推論のみで使う。観測の並びと行動の変換は公式の実装から本リポジトリの `v7_policies.py` に転記した。転記元と範囲を先に示す。

| ポリシー（既製・推論のみ） | 提供元・版 | 入力→出力 | 転記元（観測の並び） | 本リポジトリの実装（転記） |
|---|---|---|---|---|
| Microduck `velstand.onnx` | Pollen Robotics、`microduck_rl` commit 3750776、checkpoint 2749、export 2026-10-12 | 61→14 | `scripts/infer_policy.py`（`--new-cmd-obs`、`--no-bam` の経路） | `MicroduckPolicy` |
| Microduck `alpha_sitstand.onnx` | 同、commit 77ffadf、checkpoint 2250、export 2026-10-01 | 61→14 | 同上（観測は共通、指令スロットに姿勢フラグ） | `MicroduckPolicy`（`flag`／`twist[0]`） |
| Jumper `locomotion.onnx` | KingKong Robotics、公式バンドル、checkpoint `jumper.posture/…/model_74800` | 415→20 | `locomotion.json` の `observation.terms`、`deploy/fsm/src/obs.rs` | `JumperLocomotion` |
| Jumper `jump.onnx` | 同、checkpoint `jump/…/model_3100` | 167→20 | `jump.json` の `terms` と `reference`、参照軌道 `high_jump_flat.trajectory.json` | `JumperJump` |
| Jumper `dance_crab.onnx` | 同、checkpoint `jumper.dance/…/model_2300` | 209→22 | `dance_crab.json` の `terms`、`obs.rs` と `trajectory.rs` | `JumperDance` |

入力→出力は各 ONNX の入出力の形で、本ノート執筆時に onnxruntime で読んで確かめた。
Microduck の版は `policies/microduck/manifest.json` の `policies[].training`、Jumper の版は各契約 JSON の `_checkpoint` から転記した。
`obs.rs` から転記した範囲は `projected_gravity` の式（`v7_policies.projected_gravity`）、履歴付き観測の環の組み方、
参照軌道の索引（終端で固定し巻き戻さない、`root_quat` は最近傍のフレーム、`trajectory.rs`）である。

Jumper の 3 契約の `deploy_notes` は「`target = action × action_scale + default_joint_pos`、ONNX に観測の正規化を内蔵、生の観測を入れる」と定める。
`locomotion` と `dance_crab` はそのとおりに実装した（`action_scale` 0.25 は各 JSON、クリップは `joint_limits`）。
`jump` は `reference.residual_action: true` に従い、基線を `default_joint_pos` ではなく記録の指令列 `q_cmd` にした残差である（3-3 節）。

ONNX の置き場所：Microduck は Hugging Face の `pollen-robotics/microduck-policies` から取得した ONNX 4 本と `manifest.json` を本リポジトリの `policies/microduck/` に同梱する。
使うのは 2 本で、`alpha_walking.onnx`／`alpha_stand.onnx` は読み込まない（`v7_full.Duck.__init__`、ライセンスと未使用の扱いは `THIRD_PARTY.md`）。
Jumper のバンドルは `jumper` リポジトリ自体が git 追跡で同梱する `out/bundle_example/jumper/` を `v7_policies.JP_BUNDLE` が隣のディレクトリから読み、本リポジトリには複製しない。

### 3-1. Microduck `velstand`／`alpha_sitstand`：61 次元、50 Hz

| 区分 | 次元 | 内容（`MicroduckPolicy.observe`／`command`） |
|---|---|---|
| gyro | 3 | `md-imu_ang_vel` センサ |
| projected_gravity | 3 | 機体座標での重力方向（`obs.rs` と同じ式、`v7_policies.projected_gravity`） |
| joint_pos − default | 14 | 14 関節の角度から既定姿勢 `MD_DEFAULT_POSE` を引いたもの |
| joint_vel | 14 | 14 関節の角速度 |
| last_action | 14 | 直前の推論出力 |
| command | 13 | twist 3（vx, vy, yaw rate）＋首 4（neck_pitch, head_pitch, head_yaw, head_roll）＋胴体 6 |

行動は 14 次元で、`target = default + a × action_scale` を XML の位置アクチュエータにそのまま渡す（`MicroduckPolicy.step`）。
`action_scale` は 1.0（`MicroduckPolicy` と `infer_policy.py --action-scale` の既定値。`manifest.json` が別の値を持つのは使わない roller 系だけ）。
`manifest.json` の `obs_len 61`／`action_len 14`／`robot.control_hz 50` と一致し、制御周期は `MD_CONTROL_DT = 0.02 s`（`v7_policies.py`）。

重力方向は `infer_policy.py` が四元数の逆回転で求める量と同じもので、本リポジトリは Jumper と共通の `obs.rs` の式で計算する。
`MicroduckPolicy` は ONNX の入力が 51 次元なら旧形式（指令 3 次元）に切り替わるが、使う 2 本はどちらも 61 次元である。
`alpha_sitstand` は同じ観測で、指令の `twist.vx` スロットに姿勢フラグ（座る 1.0、立つ 0.0）を入れる契約である（`manifest.json` の `command.encoding: posture_flag`、`ramp_s 2.0`、`unwind_s 1.0`）。

### 3-2. Jumper `locomotion`：415 次元、200 Hz

| 項 | 次元 | 履歴 | 内容（`locomotion.json` の `observation.terms`） |
|---|---|---|---|
| base_ang_vel | 3 | 1 | `jp-imu_ang_vel` センサ |
| projected_gravity | 3 | 1 | 機体座標の重力方向 |
| joint_pos | 100 | 5 フレーム、ストライド 4 | 20 関節の角度 − 既定姿勢 |
| joint_vel | 100 | 5、4 | 20 関節の角速度 |
| actions | 100 | 5、4 | 直前の行動 |
| velocity_commands | 3 | 1 | vx, vy, yaw rate |
| joint_torque | 100 | 5、4 | `actuator_force` |
| gait_phase | 2 | 1 | sin／cos（指令が `command_threshold` 未満なら 0） |
| posture_command | 4 | 1 | twist, pitch, roll, height − `neutral_height` |

履歴付きの項は「ストライド 4 で 5 フレーム、古い順」である。契約の注記どおり、`stride × (length − 1) + 1 = 17` フレームの環を保ち 4 つおきに取り出す
（`JumperLocomotion.observe` の `deque`）。1 推論ごとに 1 フレームずらす実装では形だけ合って中身が違う窓になる。
制御周期 `control_dt 0.005`（200 Hz）、PD kp 10／kd 0.5、`sim_dt 0.001`、`decimation 5`、方策ネット [512, 256, 128, 64] ELU（`locomotion.json` の `control`／`network`）。
行動は J4 を除く 20 関節で、`target = default + 0.25 × a` を `joint_limits` でクリップする（`JumperLocomotion.step`）。

### 3-3. Jumper `jump`：167 次元、200 Hz、kp 20

観測は base_ang_vel 3＋projected_gravity 3＋joint_pos 20＋joint_vel 20＋actions 20＋jump_phase 1＋ref_future 100（先読み 5 点 × 20 関節）で 167 次元（`jump.json` の `terms`）。
行動は記録済みの高跳び `high_jump_flat.trajectory.json` の指令列 `q_cmd` を基線にした残差で、`reference.residual_action: true`（`JumperJump.baseline`／`step`）。
時間の定数は `t_go 0.3 s`、`span 1.172 s`、`duration 1.472 s`、記録 250 Hz、先読み 0.01／0.02／0.04／0.08／0.16 s（`jump.json` の `reference`）。
PD は kp 20／kd 0.5、契約の `sim_dt 0.0025`・`decimation 2`、方策ネット [512, 256, 128] ELU（`jump.json` の `control`／`network`）。
記録の `q_cmd` は J4 を 0 rad に保つ（本ノート執筆時に全 295 行を確認）。

前方ジャンプは本プロジェクトで作成した工夫で、公式 `jump` の関節目標に股関節ヨー `J0` の後方掃きを重ねるだけである。
左脚 3 本は +、右脚 3 本は − の符号（`JumperJump.SWEEP_SIGN`）、ジャンプ位相 0.26→0.38 で立ち上げ、0.44→0.56 で戻す（`SWEEP_PHASES`、`sweep_gain`）。
本番の掃き量は 1.0 rad（`v7_full.py` の `Crab.sweep`）。外力は使わない。
掃き量 0.3〜1.2 rad で前方 8〜39 cm、掃きなしの公式ジャンプの高さ 13.6 cm という値は開発記録（`docs/devlog/HANDOVER.md`）の計測である。
`python v7_test_jump.py`（高さ）と `python v7_test_jump_forward.py`（掃き量 0／0.3／0.6／0.9／1.2 rad の前方距離）で再計算できるが、本ノートでは再実行していない。

### 3-4. Jumper `dance_crab`：209 次元、50 Hz

観測は clip_phase 2＋ref_joint_pos 22＋ref_joint_vel 22＋ref_future 66（先読み 0.04／0.1／0.2 s）＋ref_tilt_error 3＋base_ang_vel 3＋projected_gravity 3
＋joint_pos 22＋joint_vel 22＋actions 22＋joint_torque 22 で 209 次元（`dance_crab.json` の `terms`）。参照は `demo.motion.trajectory.json`（50 Hz、11,784 フレーム、235.68 s）。

`ref_joint_pos`／`ref_future` は既定姿勢からの差、`ref_joint_vel` は既定姿勢を引かない記録の値そのまま、
`ref_tilt_error` は参照の重力方向から機体の重力方向を引いたもの（`JumperDance.observe`）。
残差ではなく `target = HOME + 0.25 × action`（`residual_action: false`）で、J4 を含む 22 関節に出す（記録は J4 を ±0.26 rad まで動かす）。
制御周期 0.02 s、kp 10／kd 0.5、契約の `sim_dt 0.005`・`decimation 4`（`dance_crab.json` の `control`）。応援ダンスは記録の 8.0 s から始める（`v7_full.py` の `CHEER_DANCE_START`）。

## 4. ポリシー切替：reset と PD ゲイン

ポリシーを切り替えるときは、履歴と直前行動を持つ観測を作り直し、契約どおりの PD ゲインに戻す必要がある。忘れると前のポリシーの履歴を次のポリシーが読む。

- パッカン `velstand` ⇄ `alpha_sitstand`：`Duck.use()` が新しいポリシーの `reset()` を呼び、`last_action` だけ引き継ぐ（`v7_full.py`）。両者は同じ観測契約なので PD は変えない。
- 跳跳 `→ JUMP`：`Crab.set_mode("JUMP")` が `jump.reset(sweep=…)` と `set_pd_gains(kp 20, kd 0.5)` を行う。`→ DANCE`：`dance.reset(t_start=…)` と kp 10／kd 0.5。
  それ以外のモードへ移るときは、元が `JUMP`／`HOLD`／`DANCE`／`FREEZE` なら `loco.reset()` と kp 10／kd 0.5 に戻す
  （`v7_full.py` の `Crab.set_mode`、`set_pd_gains` は `v7_policies.py`）。`WALK`⇄`IDLE` の間は `locomotion` の履歴をそのまま使い続ける。
- `FREEZE` は最後の関節目標を保持するだけで推論しない（万歳の決めポーズ、`Crab.step`）。`HOLD` は既定姿勢を目標にする（`JumperLocomotion.hold_home`）。
- 学習環境のエピソード開始でも `loco.reset()` と kp 10／kd 0.5 を書く（`manager2_env.Scene.reset`）。

## 5. 制御周期と時間刻み

台本の外側ループは `CONTROL_DT = 0.02 s`（`v7_full.py`）。その中で物理を `substeps = round(CONTROL_DT / dt)` 回進め、
パッカンは `md_every = round(MD_CONTROL_DT / dt)` ステップごと（0.02 s）、跳跳は `jp_every = max(1, round(0.005 / dt))` ステップごと（0.005 s）に推論する（`v7_full.main()` の物理ループ）。
ダンスは 200 Hz の `Crab.step()` の中で `dance_every = 4` 回に 1 回だけ推論する（`Crab.__init__`）。

時間刻みは 2 段階である。施工中は `--dt-build 0.005`、施工完了の瞬間に `--dt-action 0.001` へ切り替える（`model.opt.timestep = args.dt_action`、既定値は `v7_full.main()` の argparse）。
提出動画の本編では sim 196.08 s（本編 0:54.0、提出動画 1:12.1）に `physics step -> 0.001` の出来事が記録されている（`out/v7_full_report_take61.json` の `events`）。
0.005 は course-builder が施工を検証した刻み（`scene_fork_tracks.xml` の `<option>`）で、0.001 は Jumper の契約 `sim_dt`（`locomotion.json`）である。
施工を 0.002 で回すと復路 `TO_START` で時間切れになったという記述は開発記録（`docs/devlog/HANDOVER.md`）にあり、再計算スクリプトはない。

刻み 0.005 の間も跳跳は毎物理ステップ（200 Hz）推論する（`jp_every = 1`）。パッカンは 4 ステップに 1 回（50 Hz）で、`manifest.json` の `control_hz 50` と同じになる。

| ポリシー | 契約の制御周期 | 契約の `sim_dt` | 本作の時間刻み |
|---|---|---|---|
| Microduck `velstand`／`alpha_sitstand` | 0.02 s（50 Hz、`manifest.json`） | 記載なし | 施工中 0.005、以後 0.001 |
| Jumper `locomotion` | 0.005 s（200 Hz） | 0.001（`decimation 5`） | 施工中 0.005、以後 0.001 |
| Jumper `jump` | 0.005 s（200 Hz） | 0.0025（`decimation 2`） | 施工中 0.005、以後 0.001 |
| Jumper `dance_crab` | 0.02 s（50 Hz） | 0.005（`decimation 4`） | 0.001（踊るのは切り替えの後） |

制御周期はどのポリシーも契約どおりに守る。物理の刻みは 3 体で 1 つしか持てないため、坂の場面は最も細かい `locomotion` の 0.001 にそろえた。
施工中（刻み 0.005）の跳跳は東側の空き地で歩いて跳ねる戯れだけで（本編で `WALK` 10 回・`JUMP` 9 回）、坂を登るのは刻みを 0.001 に切り替えた後である
（`out/v7_full_report_take61.json` の `jp_events` と `events`）。戯れの間は `locomotion` と `jump` が契約より粗い刻みで動き、
坂の場面の `jump` と `dance_crab` は契約より細かい刻みで動く。この差が動きに与える影響は、契約の刻みどおりの場合と比べておらず確かめていない。

## 6. 外力なしの原則の実装

原則：各機体は自分のアクチュエータだけで動き、`xfrc_applied` も位置の書き込みも使わない（`v7_full.py` 冒頭の docstring）。実装上の要点は 3 つ。

1. パッカンのサーボは XML の公式値に戻す。`build_arena()` は旧世代の理想化ゲイン（`MD_KP 8.0`／`MD_KV 0.3`／`MD_FORCE 5.0`、`v6_robots.py`）を一度書くが、
   直後に `v7_full.official_md_servos()` が全 14 本へ kp 0.55、kv 0、`forcerange ±0.96 N·m` を書く（呼び出しは `v7_full.main()` と `manager2_env.Scene.__init__`）。
   この値は `microduck_rl` の MJCF のクラス `chosen_actuator`（`kp="0.55" kv="0.0" forcerange="-0.96 0.96"`）と同じである。
   `scene.xml` が include する `robot_groundcontact.xml` がこのクラスを定義し（`joints_properties.xml` と同じ値）、14 関節と 14 本の位置アクチュエータがすべてこのクラスを使う。
2. `xfrc_applied` を書くコードは `v6_robots.py` の `MicroduckCtrl`／`JumperCtrl`（旧世代の仮想ハーネス）と `archive/` にだけ残り、本番の台本・学習環境・ポリシーからは呼ばれない。
   `v6_robots.py` 冒頭の docstring は旧世代の注記を保存したもので、現行（外力なし・公式サーボ値）との違いを冒頭の段落で断っている。
3. 位置の書き込み（テレポート）は学習環境の開始配置（`manager2_env.Scene.teleport`／`Scene.reset`、docstring に training-only と明記、BZ の待機位置 `BZ_PARK` を含む）と、
   単体テストと途中経過の動画の開始配置に限る。後者は `teleport()` などで開始位置を書く `v7_test_bz_drive.py`、`v7_test_cheer.py`、`v7_test_nudge.py` と、
   パッカンを仰向けなどの転倒姿勢に置く初期条件の `v7_test_microduck.py`（`lie_down()`）、`v7_progress_video.py` である。開始配置のあとは物理だけで動く。
   提出動画の台本（`v7_full.py`）は t = 0 の前に `build_arena()` が初期姿勢を書くだけで、以後は `qpos` に一度も書き込まない。

跳跳は結合時に追加した PD アクチュエータ（2-6 節）だけで歩き、跳び、押す。座ったパッカンを押し上げる力は接触から生まれる。
本編の報告 JSON（`out/v7_full_report_take61.json`、PUSH の区間は固定ルール版・以前の 2:47 版と同じ値）の `face.effort_series`（1 秒ごとの標本、3 列目がパッカンへの接触力）を PUSH の区間 sim 276.5〜347.9 s で集計すると、
71 点の中央値 6.8 N、90 パーセンタイル 11.7 N である（本ノート執筆時に集計）。表情の基準値 `crab_face.PUSH_FORCE_REF` 10 N は、
開発記録のヘッドレスの較正（中央値 6.4 N、90 パーセンタイル 10.2 N、`docs/devlog/HANDOVER.md`）から決めた値である。
パッカンの重さは 7.2 N（0.74 kg、1 節）で、16.3° の坂に沿った成分は 2.0 N にとどまる。残りは座ったまま坂を滑らせる摩擦に使われていると考える。

## 7. course-builder との境界

ブルドーザー側は自作リポジトリ physical-ai-course-builder（commit `483dbf9`、峠の継ぎ目 `INSTALLATION_GAP` 0.01 m）をそのまま使い、本体は変更しない。
`v6_common.course_builder()` が隣のディレクトリ `COURSE_BUILDER`（`../physical-ai-course-builder`）を `sys.path` に加え、
`app`（`Simulation`）、`slope_assembly`（`assembly_xml`／`SlopeAssembly`）、`tracks`（`TrackAnimation`）を import する。
`ArenaSim`（`v6_phase4_full.py`）が `Simulation` 互換の薄いラッパ（`observe`／`command`／`lift_target`／`tracks`）で、`SlopeAssembly` は結合後の `model`／`data` の上でそのまま動く。

- 舞台 XML：`assembly_xml(scene_fork_tracks.xml)` が坂 2 枚と箱を加えた XML を返し、`build_arena()` がこれを土台にする。
  施工が終わった配置は `v6_common.built_stage_xml()` で各部材の `pos`／`quat` に書き戻し、`out/v6_stage_built.xml` として保存する（`v6_phase1_build.py`）。
  学習環境（`manager2_env.STAGE_XML`）と単体実験はこの保存済み舞台を読む。
- 履帯：`tracks.TrackAnimation.update()` は描画用の装飾ジオメトリ（`class="decor"`）を動かすだけで、接触はしない。車体は 4 輪（`drive_lf`／`drive_lr`／`drive_rf`／`drive_rr`）で接地する。
- 施工結果：`Placed 2 slopes; crossed 4/4 surfaces; rise 0.440 m`（`out/v7_full_report_take61.json` の `construction.reason`）。
  各部材は 0.21 m 持ち上げて約 2.98 m 運ぶ（同 `construction.parts[].lift_m`／`carry_m`）。

### 7-1. Navigator の差し替え（復路の壁）

course-builder の復路 `TO_START` は経由点 `[[-1, .75], [-1, -3.2], [target_x, -3.2]]` で角を回る（`slope_assembly.py` の `SlopeAssembly.action`）。
BZ は角 `(-1, -3.2)` へ向けて南に走り、経由点に近づくと次の経由点へ向きを変え始める（`navigation.py` の到達判定）。
そのため上げたフォークの爪先（車体前方 1.38 m）が壁に届くことはないが、南壁の内面 `y = -4.5`（`scene_fork_tracks.xml` の箱 `pos 0 -4.6 0.3`、半厚 0.1）との余裕は 8 cm しかない。
爪先の 1.38 m は `v7_test_bz_drive.py` の計測、8 cm は開発記録（`docs/devlog/HANDOVER.md`）の値で、`v7_full.py` の `TO_START` 差し替え箇所と `CIRCLE_BZ` の注記にもある。

単独の施工では通るが、3 体同居ではソルバーの数値差で BZ の軌跡が十数 cm ずれ、`fork_right` が壁に触れて `fast_empty` の接触検査
（`navigation.py` の `Empty transfer touched course geometry.`）が施工を中断した。

対処：台本は `TO_START` に入った瞬間に同じ設定の `Navigator` を角 `y = -3.0` で差し替える（`v7_full.main()`：`Navigator(sim, [[-1, .75], [-1, -3.0], [target_x, -3.0]], fast_empty=…)`）。
course-builder 本体は無変更である。本編では sim 106.06 s（本編 0:26.5、提出動画 0:44.6）に `TO_START route: corner at y=-3.0` の出来事が残る（`out/v7_full_report_take61.json` の `events`）。
施工後に BZ が自分で移動する場面では `Navigator(sim, waypoints, allow_reverse=True)` を使い、後退を許す（`v7_full.make_navigator`）。

### 7-2. 施工中の制約

course-builder は空荷の走行中に車体が何かに触れると施工を中断する。そのため施工中はパッカンと跳跳を作業範囲の外（東側の空き地）に置き、BZ の進路に入れない
（`v7_full.py` の `WANDER_ZONE`、`JP_PARK`、`CRAB_WATCH`）。事前移動や応援の位置も BZ の走路と経由点を避けて決めている（`CHEER_SPOT`、`ASIDE_SPOT` の注記）。

## 8. 描画と物理：毎フレームの `mj_forward` は経路の一部

描画版は 1 フレームごとに `sim.tracks.update()` と `mujoco.mj_forward()` を呼ぶ（`v7_full.py` の `render_frame()`）。
`mj_forward` はソルバーのウォームスタートなど `MjData` の中身を更新するので、同じコードでもヘッドレス版（`--test`）と描画版の軌道は bit 単位では一致しない。

固定ルール・輪の結末の同じ台本で比べると、施工完了はどちらも sim 196.08 s だが、PUSH の決定から次の手まではヘッドレス 57.1 s（sim 276.5→333.6 s）、
描画版 71.4 s（276.5→347.9 s）と分かれる。

END はヘッドレス sim 385.6 s、描画版 sim 401.7 s である。支配人の 5 手の種類と順序（SEAT→PUSH→BACK_OFF→STANDUP→WALK_ON）は同じだが、出来事は一致しない。
ヘッドレス版はパッカンが渡り切った直後（sim 354.9 s）の sim 355.2 s に転倒し（傾き 84°）、2.2 s で自力で起き上がる。描画版にはこの転倒がない。
`events` はヘッドレス 64 件、描画版 62 件である（`out/v7_full_report_facecheck_A.json` と以前の 2:47 版の `_take51.json` の `events`・`manager.decisions`、本ノート執筆時に数字を除いて行ごとに照合。固定ルール版 `_take57.json` も同じ 62 件。PPO の本編 `_take61.json` は `BACK_OFF` の 2 行がなく 60 件）。
描画版の報告の `sim_seconds` 404.22 は、END の後に回す 2.5 s を含む（`v7_full.main()` の末尾。本編と固定ルール版はそのうち最初の 1 s だけを書き出す、`--tail-write 1.0`）。

一方、描画版同士はコードとフレームの時刻が同じなら決定的で、カメラの向きは物理に影響しない
（開発記録：カメラだけを変えて描いた 2 本で出来事の時系列が一致）。設定を変えずに経路だけを変えるダイヤルは `--jitter`（応援ダンスの開始位置をずらす秒数）である。

この性質から 2 つの設計判断が出た。

- 省略区間（ジャンプカット）でもフレームは描かずに `render_frame(write=False)` を呼び、`mj_forward` と履帯の更新だけは毎フレーム行う（`cut_at()` が区間を判定）。
  省略区間で呼び出しを省いた初版は物理の経路が変わり、施工の完了が 4 s 遅れて筋書きが成立しなかった（`render_frame` の docstring、`docs/devlog/HANDOVER.md`）。
- 施工を 4 倍速で見せる `--build-speed 4` は、フレームの標本周期を 2 倍速のまま保ち、書き出しだけ 2 枚に 1 枚にする（`build_write_every`、`sampled % build_write_every`）。
  標本周期そのものを変えた初版は別の経路になった（下表の最終行）。

### 8-1. 物理同一の確認（最終状態のダイジェスト）

報告 JSON の `state_digest` は終了時の `qpos` と `qvel` を連結した sha256 である（`v7_full.main()` の末尾）。同じ経路なら一致し、違えば一致しない。
以下は本ノート執筆時に各報告 JSON（`sim_seconds`、`state_digest`、`manager.decisions`、`video_silent.seconds`）を読み比べて確認した値である。
省略ありの版と省略なしの版で一致するのは、省略区間でも `render_frame(write=False)` が `mj_forward` を呼ぶからである。

| 比較（左／右） | 報告 JSON（`out/`） | ダイジェスト | `sim_seconds` | 手数 | 動画長 s |
|---|---|---|---|---|---|
| 顔なし／顔あり（ヘッドレス） | `v7_full_report_facecheck_A.json`／`_B.json` | 一致 `c083a03c…` | 385.6／385.6 | 5／5 | 描画なし（`ngeom` 290／291） |
| 本編（提出）／PPO 版 | `v7_full_report_take61.json`／`_take52.json` | 一致 `aafa49e7…` | 400.6／400.6 | 4／4 | 155.5／165.2 |
| 固定ルール版／以前の 2:47 版 | `v7_full_report_take57.json`／`_take51.json` | 一致 `678fd3ca…` | 404.22／404.22 | 5／5 | 157.3／167.0 |
| 以前の 2:47 版（固定ルール）／2 倍速・省略あり | `v7_full_report_take51.json`／`_take46.json` | 一致 `678fd3ca…` | 404.22／404.22 | 5／5 | 167.0／164.1 |
| PPO 版／2 倍速・省略あり | `v7_full_report_take52.json`／`_take47.json` | 一致 `aafa49e7…` | 400.6／400.6 | 4／4 | 165.2／162.3 |
| Q 表版／2 倍速・省略あり | `v7_full_report_take53.json`／`_take48.json` | 一致 `f53de6e4…` | 402.9／402.9 | 8／8 | 166.3／163.5 |
| 追走版／2 倍速・省略あり | `v7_full_report_take54.json`／`_take49.json` | 一致 `be8fb01e…` | 397.72／397.72 | 5／5 | 163.7／160.8 |
| 標本周期を変えた 4 倍速の初版／2 倍速・省略あり | `v7_full_report_take50.json`／`_take46.json` | 不一致 `768e78f7…`／`678fd3ca…` | 390.66／404.22 | 5／5 | 160.2／164.1 |

2・3 行目は、仲間を呼んで戻る区間と輪へ集まる区間も 4 倍速で書き出し（`--speedup`）、END の後の書き出しを 1 s にした本編（PPO の支配人）・固定ルール版と、以前の速度設定で描いた同じ支配人の版の組である。
本編と固定ルール版には支配人の帯、声の音量と左右の振り分けもあるが、どれも描画と音声だけなので digest は変わらない。
4〜7 行目の左は施工 4 倍速・省略なし、右は施工も 2 倍速で空荷走行 2 か所を省略した版である。最終行の初版も 3 体とも渡り切るが、別の経路である。
動画は報告 JSON と同じ番号の `out/3body_arena_v7_take61.mp4` などで、番号はファイルの固有名としてそのまま引用している。
`sim_seconds` は描画版では END の後の 2.5 s を含む（本編も 2.5 s 回し、書き出すのは最初の 1 s）。

本編の速度区間は ×4 が本編 0:00〜0:44.1（sim 0〜176.4 s）、×2 が 0:44.1〜1:20.4（sim 176.4〜248.9 s）、×4 が 1:20.4〜1:24.3（sim 248.9〜264.6 s）、
×2 が 1:24.3〜2:14.8（sim 264.6〜365.6 s）、×4 が 2:14.8〜2:19.1（sim 365.6〜382.7 s）、×1 が 2:19.1〜2:35.5（sim 382.7 s〜）である。提出動画の時刻はこれに 18.14 s を足す。
動画時刻の区間は `python analysis/timeline_times.py out/v7_full_report_take61.json` が END（本編 2:34.4、sim 398.1 s）まで出す。
その後の等速の尾は `v7_full.main()` 末尾のループ（`range(int(2.5 / CONTROL_DT))`）が回し、`--tail-write 1.0` で最初の 1 s だけを書くので、本編の全長は 2:35.5（`video_silent.seconds` 155.5）になる。
sim の区切りは `events` の `stage -> FOLLOW_IN`（176.38 s）、`stage -> CALL`（248.94 s）、`stage -> RESCUE`（264.56 s）、`stage -> CELEBRATE`（365.64 s）、輪のダンスの開始（382.70 s）の時刻である。
固定ルール版は `stage -> CELEBRATE` が 369.38 s、輪のダンスの開始が 386.32 s で、×2 が 1:24.3〜2:16.7、×4 が 2:16.7〜2:20.9、×1 が 2:20.9〜2:37.3 になる（`out/v7_full_report_take57.json`）。
以前の 2:47 版は ×4 が 0:00〜0:44.1、×2 が 0:44.1〜2:29.1、×1 が 2:29.1〜2:47.0 で、END の後の 2.5 s をすべて書いた。

### 8-2. 検証コマンド

```
python analysis/face_check.py out/v7_full_report_facecheck_A.json out/v7_full_report_facecheck_B.json
python analysis/timeline_times.py out/v7_full_report_take61.json --compare out/v7_full_report_take52.json
python analysis/timeline_times.py out/v7_full_report_take57.json --compare out/v7_full_report_take51.json
python analysis/timeline_times.py out/v7_full_report_take51.json --compare out/v7_full_report_take46.json
```

1 行目は同梱の顔なし／顔ありのヘッドレス報告を照合し、8 項目すべて same、ngeom 290→291、`VERDICT: identical physics path`（終了コード 0）を出す。
2 行目は本編と PPO 版、3 行目は固定ルール版と以前の 2:47 版、4 行目は 4 倍速・省略なしの 2:47 版と 2 倍速・省略ありの版を比べ、いずれも末尾に `state_digest equal: True` を出す。いずれも本ノート執筆時に実行して確かめた。
ヘッドレスの報告を作り直す手順（`python v7_full.py --test --no-face --tag _rerunA` ほか、同梱ファイルを上書きしない別名の tag、各約 1.5 分）は
`docs/reproduce.md` の 4.3 節にある。現行コードが書く表情ログは 1 行 5 要素で、`face_check.py` は 3 要素として読むため、作り直した組では一覧の途中で止まる（同節）。
その場合は印字済みの 8 項目か、報告 JSON の `state_digest` を直接比べて判定する。

## 9. 残っている差と限界

- 跳跳の `LF_J4`／`RF_J4` は `locomotion`／`jump` の契約では固定関節だが、本リポジトリは PD 保持である（2-6 節）。
- 物理の刻みは 3 体で共通の 1 つで、ポリシーによっては契約の `sim_dt` と違う刻みで動く（5 節の表）。
- パッカンのサーボは XML の位置アクチュエータである。`infer_policy.py` は既定で、方策の学習に使われた BAM のサーボモデル（M6、電圧と摩擦）を通して動かし、
  `--no-bam` で XML の位置アクチュエータに切り替わる（同ファイルの argparse の help）。本リポジトリは後者の経路で、BAM も backlash も入れていない
  （`velstand` の学習タスク名は `Mjlab-VelStand-Rough-Backlash-MicroDuck`、`manifest.json` の `training.task_id`）。学習時の駆動系との差は残る。
- 公式の `velstand` はこの環境で 16.3° の坂を登れない。本編では前進の指令を 1 回目 14 s、2 回目 11 s 与えても、胴体の到達は y −1.99 m／−2.00 m である。
  これは上り坂の下端（`crab_help.TOE_Y` −2.0 m）の位置で、そこから坂を登れなかった（`out/v7_full_report_take61.json` の `events`、挑戦の秒数は `v7_full.py` の RAMP 段）。
  座り込むのはこの時間が過ぎた後の台本の動作である。
  登れない原因が上の駆動系の差か、勾配そのものかは切り分けていない。本作はこれを支配人 AI が次の一手を選ぶ場面として筋書きの核にした。
- RAMP 段の字幕と出来事の文言は坂の入口を y −1.86 m と表示する（`v7_full.py` に書き込まれた文字列）。斜面の上面の下端は y ≈ −2.00 m で、
  `TOE_Y` と一致する（`out/v6_stage_built.xml` の `up_1`：`pos` の y −0.999 に頂点の y −1.0）。−1.86 m は斜面メッシュの底面側の頂点（y −0.86）の位置にあたる。
  本ノートと `docs/glossary.md` の位置の記述は `TOE_Y` に従う。
- 描画版とヘッドレス版は経路が異なる（8 節）。数値の照合は同じ描画設定どうし、またはヘッドレスどうしで行う。
- MuJoCo 3.11.0 と course-builder commit `483dbf9`、同じバンドルと ONNX、同じ CPU 向けビルドが前提で、版が違えばダイジェストは一致しない。環境の版は `requirements.txt` と `docs/reproduce.md`。
