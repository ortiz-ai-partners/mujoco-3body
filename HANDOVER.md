# MuJoCo 3体連携 — 引継ぎ文書

**日付**: 2026-10-27
**プロジェクト**: 松尾研 Physical AI 応用1 最終課題（締切 2026-11-02）
**Notion**: https://www.notion.so/4065e0de2f3281ae9f5aee87b7f2348a

---

## 0b. 2026-10-28 追記（アイランドマスター）— BZ 禁止、カニの押し上げで 3/3、支配人 v2

**決定（ゆうころ 10/28 未明）**：ブルドーザーがパッカンを扱うのは禁止（首を持ち上げると破損の恐れ）。手助けはカニが担う。take4／take5 の結末（フォークで押し倒す）は最終動画に使えない。

**事実：3/3 が実験で成立**（`v7_test_crab_push.py --seated --crest --face-crab --crab-vx 0.3`、物理のみ）：座ったパッカンが**カニの方を向く**（背中を坂へ）と、押されている間の傾きが 6〜12°（坂の上を向いて座ると 40° 後傾して縁で転倒）。天面到達 62.1 s → カニが 0.6 m 下がる → 自力起立 69.2 s → 天面で 1 回つまずく（1.8 s で自力復帰）→ 下り坂を歩いて **86.6 s に北側の床（y +2.20）**。動画 `out\v7_crab_push_cross.mp4`。

**支配人 v2（カニが手助け）**：`crab_help.py`（スキル生成器 WAIT／SEAT／PUSH／BACK_OFF／STANDUP／WALK_ON、観測 45 次元、固定ルール）＋ `manager2_env.py`（gymnasium 環境、開始状態 6 種、コース監視 4 cm、吹き出し付き録画）＋ `manager2_train.py`（PPO／評価／デモ）。`v7_full.py --ending crab`（take 6）は同じスキルを呼ぶ：施工→戯れ→BZ 走破→パッカン挫折→跳跳が越える→パッカンが呼ぶ→跳跳がコースの東側を回って戻る（固定）→**支配人が判断**（吹き出し）→渡り切り→跳跳が回り込んで応援ダンス、BZ はフォークで万歳（固定）。`--manager rule|ppo`。v1（`manager_env.py`、BZ の行動）は凍結。

**10/28 未明に分かった罠**：
- 押す線を x=1.22（パッカンの坂レーン、西端から 24 cm）にするとカニの左足が縁に乗って押しが止まる／天面でつまずいた後に西へ歩いて 0.44 m 落ちる → 押す線・歩く線はコース中央 x=1.45（`crab_help.LANE_X`）。
- **坂の入口で座ったパッカンが転ぶ**：座席が入口の 35 cm 手前だと、平地を滑らされる間に座り姿勢が崩れて入口で 20/20 転倒（速度・向き・横ずれ・接触ゲート・カニの待機姿勢・徐行・前傾指令・入口手前の止まり直しを変えても同じ）。入口の 13〜15 cm 手前に座らせると 3/3 登り切る → `crab_help.SEAT_Y = −2.13`、SEAT は座席へ 7 cm 以内に歩いて座らせる。通し台本でもパッカンは入口の 10 cm 手前（y −2.10）に座るので一致。
- 天面の 2 枚の継ぎ目でパッカンがつまずく（0.2 でも 0.3 でも、6 シードで 0.3 が 4/6、0.2 が 3/6）。転倒後に velstand が起きられない回がある（深掘り未着手）。
- カニは押し上げ後、線に沿って真っ直ぐ下がる（`reverse_command`）。横に動かすと西の縁から落ちる。WALK_ON の間カニは動かない。
- 学習用の配置でカニを坂の上に書き込むときは斜面に合わせて傾けて 3 cm 上から落とす（水平に置くと前足が斜面にめり込み、ソルバーが 2 体を 1 m 飛ばす）。

**通し検証（take 6、ヘッドレス、2026-10-28 早朝、`--ending crab --manager rule`）の時系列**：施工 0〜197 s（成功、4/4 面、上昇 0.44 m）→ 坂への挑戦と座り込み 197〜229 s → 跳跳の登坂・完走 229〜259 s → 呼ぶ 262 s → 跳跳がコースの東側を回って戻る 267〜282 s → **支配人（固定ルール）**：SEAT 282〜294 s（座席 (1.39, −2.06) に座り直す）→ PUSH 294〜371 s（天面 (1.62, −0.41) まで押し上げ）→ BACK_OFF 371〜373 s → STANDUP 373〜379 s → WALK_ON 379〜392 s → **パッカン渡り切り 391.8 s（y +1.95）＝3 体とも渡った** → 跳跳が坂を後ろ向きに降りて東側を回り込み、応援ダンス 411 s、BZ はフォーク万歳 → END 423 s。コースの移動なし。判断は 5 手、無駄な手なし。

**描画版 take 6（`out\3body_arena_v7_take6.mp4`、3:46、6775 フレーム、27.7 MB、音声付き；Notion 用 `3body_arena_v7_take6.notion.mp4` 4.6 MB）の時系列**：施工完了 185 s → 座り込み 217 s → 跳跳 越えて BZ の後ろへ 243 s → 呼ぶ 246 s → 跳跳が戻る 251〜265 s → 支配人：SEAT 265〜278 s → PUSH 278〜331 s（坂の途中 y −1.79 で止まる＝stalled）→ BACK_OFF → SEAT 333〜351 s（立って座席へ戻り座り直す）→ PUSH「もう一回いこう」351〜412 s（天面到達）→ BACK_OFF → STANDUP 414〜419 s → WALK_ON 419〜433 s → **渡り切り 433 s** → 跳跳が坂を後ろ向きに降りて回り込み、応援ダンス 452 s、BZ フォーク万歳 → END 464 s。8 手、再試行 1 回、コース部品の移動 0。ヘッドレス版と出来事の順序は同じで、押しが 1 回止まった点だけ違う（描画時は毎フレーム mj_forward を挟むので物理が bit 一致しない：既知の罠）。

**描画版 take 7（`out\3body_arena_v7_take7.mp4`、3:23、6081 フレーム、音声付き；`--manager tabq --run tabq2_small`＝学習済み Q 表が支配人）**：施工〜戻りは take 6 と同じ（265.5 s に支配人へ）→ STANDUP → WALK_ON（坂に向かって歩いて止まる＝学習の癖）→ SEAT → PUSH（天面 364 s）→ BACK_OFF → STANDUP → STANDUP（無駄）→ WALK_ON → **渡り切り 386.5 s** → 応援ダンス 406 s → END 418 s。8 手、コース移動 0。固定ルール版（take 6）と並べて「固定ルール／学習済み方策」の両方を提出素材にできる。

**支配人の学習結果（2026-10-28 早朝、30 シード同一評価）**：固定ルール 25/30 渡り切り／ランダム 9/30／PPO 小（3k 決定、54 分）0/30（WALK_ON に固着）／**表形式 Q（120 エピソード、2 時間）23/30**。2×2 で表形式 Q の失敗 7 本のうち判断の失敗は 1、他はスキル側（天面の継ぎ目での転倒から起きられない等）。詳細と信頼度表は `MANAGER_DESIGN.md` §7.5〜7.6、`out\manager_runs\comparison_v2.md`。PPO 中規模 `ppo2_medium2`（12k 決定、報酬 v2.1）は 05:00 頃完了予定 → `manager2_train.py eval --run ppo2_medium2 --episodes 30` で評価し、`manager2_report.py --runs ppo2_medium2 baselines_v2 tabq2_small` で表を更新する。

## 0. 2026-10-27 追記（アイランドマスター）— v7「物理のみ」版の現状

**方針転換**：v6 Phase 2〜3（`v6_robots.py` の仮想ハーネス／誘導力＝`xfrc_applied` の外力）はゆうころの指摘で却下。以後、各機体は自分のアクチュエータだけで動かし、公式の立ち方・ポリシーを使う。v6 Phase 1 の施工（course-builder そのまま）だけが外力なしで有効。

**実行環境**：`D:\IslandMaster\jumper\.venv\Scripts\python.exe`（Python 3.10.6、mujoco 3.11.0、onnxruntime 1.23.2、imageio、PIL）。`mujoco_3body\.venv` には onnxruntime が無い。

| ファイル | 役割 |
|---|---|
| `v6_common.py` | 動画書き出し・字幕（Meiryo）・カメラ・施工済みステージ XML 保存 |
| `v6_robots.py` | `build_arena()`（MjSpec.attach、照明/床の整理、JP に kp10/kd0.5 の position actuator を追加）。`MicroduckCtrl`/`JumperCtrl` は**外力版なので使わない** |
| `v6_phase1_build.py` | BZ 単体施工の 4 倍速動画 → `out\v6_phase1_build.mp4`、`out\v6_stage_built.xml`（施工済み独立シーン、Notion A0） |
| `v7_policies.py` | 公式ポリシーの観測転記：`JumperLocomotion`（415 次元、200 Hz、`deploy/fsm/src/obs.rs` 準拠）、`JumperJump`（参照軌道残差、kp 20、`SWEEP_*` で前方ジャンプ）、`JumperDance`（`dance_crab.json` の 209 次元、50 Hz、参照 `demo.motion.trajectory.json` 235.7 s、HOME 相対の ref_*、ref_tilt_error＝参照の重力方向−機体の重力方向）、`MicroduckPolicy`（`infer_policy.py` の 61 次元、`--no-bam` 経路） |
| `v7_test_*.py` | 単体検証（歩行・ジャンプ・前方ジャンプ・velstand・sitstand・衝突・首の到達範囲・ダンス `v7_test_dance.py --video`） |
| `v7_progress_video.py` / `v7_failures_video.py` | 進捗動画 `out\v7_progress_physics_only.mp4`、失敗集 `out\v7_failures_physics_only.mp4` |
| `v7_full.py` | 通し台本 v4（施工中はパッカンと跳跳が戯れる→BZ 走破→パッカンが坂に 2 回挑んで座り込む→跳跳が坂を越える→BZ を呼ぶ→跳跳が BZ について戻り、BZ がフォークで持ち上げを試みる横で応援ダンス→パッカン自力起立）→ `out\3body_arena_v7{tag}.mp4`（チャープ音声付き）。`--tag _take5` のように版を分ける。`--test` はヘッドレス、`--until RAMP` で途中終了 |
| `out\3body_arena_v7_take4.mp4` | 再描画 #4（ゆうころ「フォークで持ち上げようとしたとこ、傑作」）。結末の BZ とパッカンの動きはこの版で固定 |
| `policies\microduck\` | HF `pollen-robotics/microduck-policies` から取得（ゆうころ許可）：velstand / alpha_sitstand / alpha_walking / alpha_stand / manifest.json |

**検証済みの事実**（外力なし）：
- 跳跳 locomotion：立位 z 0.105〜0.112、指令 0.3 → 実速 0.28 m/s、旋回可。jump：高さ 13.6 cm（公式値 14 cm と一致）。股関節ヨー J0 の後方掃き（ゆうころ案）で前方ジャンプ 8〜39 cm（掃き 0.3〜1.2 rad）、着地直立。
- パッカン velstand（XML サーボ kp 0.55）：立位 z 0.116；歩行は指令 0.3 m/s で実速 0.10 m/s（0.15 では歩き出さない）；仰向け・横倒しから 3 秒で自力起立；首の指令に追従。頭を前下に出すのは首だけではほぼ無理（1〜3 cm）→ sitstand で座ってのぞき込む。
- 接触：跳跳の飛びつきでパッカンは 21〜45° 傾いても大抵は転ばない（条件により転ぶこともある：v7_full テスト #1 では 91° 転倒）。0.8 m/s の体当たりなら転倒。カニは転ばない。転倒後、カニが密着したままだと起き上がれない → カニを後ずさりさせる。
- パッカンは 16° の坂を登れない（入口で足踏み）→ 台本では 15 秒挑んでから脇を回る。
- 施工中の物理刻みは検証済みの 0.005（0.002 だと TO_START でタイムアウト）。施工完了後に 0.001（跳跳の契約）へ切替。3体同居でも施工タイムラインは Phase 1 と完全一致（TO_START まで。以降は下記）。
- 跳跳 dance（公式 `dance_crab`、`models/dance_crab.onnx`）：素の MuJoCo で 30 s 踊って転倒なし（傾き ≤7°、横滑り 9 cm @dt 0.001／22 cm @dt 0.005）。参照 demo.motion は最初の 5 s が静かで、以降は大きく動く。クリップ `out\v7_dance_test.mp4`。
- 戯れ（施工中、テスト #11）：跳跳の jump は dt 0.005 でも 11 回すべて安定。ただし倒れたパッカンの横で跳跳が跳び続けると起き上がりに 16〜27 s（単体では 0.3〜3 s）→ 跳ぶ距離 0.95 m、うろうろ中 0.6 m 以内は停止、転倒中は 1.1 m 離れて待つ。パッカンが歩いて跳跳の脚に当たっても転ぶ（#12、見学位置への道の途中）→ `CRAB_WATCH` をパッカンの道から外す。
- **course-builder の TO_START 復路の罠（#12 で再現、決定論的）**：角の経由点 (−1,−3.2) で BZ が南を向くと、上げたフォークの爪先（1.38 m 前、z 0.5）が `scene_fork_tracks.xml` の南壁（box pos 0 −4.6 0.3、内面 y=−4.5）まで 8 cm。他の 2 体が居るだけのソルバーの数値差で BZ の軌跡が十数 cm ずれ、`fork_right` が壁に触れて Navigator の `fast_empty` 検査「Empty transfer touched course geometry.」で施工中断（単独・#7・#10・#11 は曲がるのが一瞬早くて通っていた）。v7_full.py は TO_START になった瞬間に同じ設定の Navigator を角 y=−3.0 で差し替える（course-builder 本体は無変更）。ファーブル／course-builder 側への申し送り事項。

**筋書き v4（ゆうころ 10/27 深夜確定、物理の結果を取り込んだもの）**：施工（跳跳は最初からパッカンと空き地で戯れる：近づく→ぴょん→うろうろ→ひと休み、声はランダム・小さめ、カニにも声）→ BZ 走破、パッカンが坂の入口へ → 坂に 1 回挑む → 後ずさり → もう 1 回 → やっぱり無理で座り込む（sitstand）→ 座った直後に首を振りながら「ぐわぁぁ？」2 秒 → 跳跳が見学位置から歩いて来て、座ったパッカンの横を通って坂を登る（天面で引っかかったら前方ジャンプ 1 回、それでも駄目なら最高速 0.8）→ 峠を完走して BZ の後ろへ → パッカンがきょろきょろ → BZ を呼ぶ → 跳跳は BZ の旋回圏から脇へ → BZ がコースの東側を回って戻る（跳跳が 1.7 m 後ろについて戻る）→ BZ が到着して向きを合わせる間に跳跳は BZ の東側を回り込んでパッカンの南 1.1 m へ → **BZ がフォークで持ち上げを試みる（座ったパッカンを押し倒す→BZ が下がる→パッカンが velstand で自力起立；この 2 台の動きは #4 のまま固定）横で跳跳が応援ダンス（公式 dance）** → 立ったパッカンが踊るカニの方を向く → END。わざとぶつけない。失敗集 `out\v7_failures_physics_only.mp4`（A 坂で足踏み／B 跳跳の登坂と縁での足踏み／C 飛びつき）はゆうころへ送付済み。「学習させた AI を使う」ミッションは保留（後で相談）。

**通し検証 #7（10/27 夜）の時系列**：施工 0〜197 s → 坂への挑戦と座り込み 197〜225 s → 跳跳の登坂・ジャンプ・完走 229〜260 s → 呼ぶ 263 s → BZ 回り込み到着 293 s → フォークが座ったパッカンを押し倒す 313 s（持ち上げは空振り）→ BZ が下がった直後にパッカンが velstand で自力起立 336 s → END 342 s。最終動画は `out\3body_arena_v7.mp4`（`3body_arena_v7_silent.mp4` ＋ `3body_arena_v7_chirps.wav` を ffmpeg で合成）、時系列は `out\v7_full_report.json`。

**通し検証 #15（10/27 深夜、筋書き v4）の時系列**：施工 0〜197 s（戯れ中のパッカン転倒 0）→ 坂への挑戦と座り込み 197〜229 s → 跳跳：入口 235.9 s、天面 244.0 s、天面で引っかかって前方ジャンプ 252.1 s、越えて BZ の後ろへ 259.0 s → 呼ぶ 262 s → BZ 回り込み 267〜292.5 s（跳跳が 1.7 m 後ろについて戻る）→ 跳跳が BZ の東側を回り込んでパッカンの南へ、応援ダンス開始 309.1 s → フォーク 6 cm で差し込み → 押し倒し 329.3 s（傾き 65°）→ 1.2 s で自力起立 → フォーク下降で再転倒 334.0 s → 4.3 s で自力起立 → うれしい声 339.8 s → END 344.8 s。再描画 #5（`--tag _take5`）→ `out\3body_arena_v7_take5.mp4`（2 分 22 秒、4263 フレーム、21.9 MB、音声付き）、Notion 用 `3body_arena_v7_take5.notion.mp4`（9.2 MB）、時系列 `out\v7_full_report_take5.json`。描画版の時系列：施工 185 s → 座り込み 213 s → 跳跳 天面 232 s・前方ジャンプ 235 s・BZ の後ろへ 243 s → BZ 回り込み 251〜276 s → 応援ダンス 293 s → 押し倒し 313 s → 自力起立 1.3 s／6.8 s → END 328 s。**罠**：描画時は毎フレーム `mj_forward` を挟むのでヘッドレスと物理が bit 単位では一致しない（施工完了 185.0 s vs 196.9 s、ソルバーのウォームスタートがずれる）。出来事の順序と結果は同じだったが、時刻をヘッドレスの数字で語らないこと。無印の `3body_arena_v7.mp4` は #4 のまま。

**フォーク実験**（`v7_test_fork.py`、BZ をパッカンの東 1.9 m に置いてテスト専用に姿勢を書き込む）：床の高さの爪は座ったパッカンを押して滑らせるだけ（0.3 m、転ばない）、6 cm の爪は中心 ±5 cm なら押し倒す（傾き 92°、12.8 s で自力起立）、0.1 m ずれると爪に乗って z 0.425 まで持ち上がってから落ちる、0.2 m なら外れる。→ 台本は差し込み時にフォークを 6 cm に保ち、狙いを ±0.03 rad（20 s 打ち切り）。

**持ち上げ結末の試行（10/27 深夜、`--ending lift`、#16〜#21）**：ゆうころ「持ち上げられるならその方がほんわかする」→ パッカンが CALL 中に立って坂に背を向けて座り直し、BZ が真後ろ 3.2 m に来てライン追従→精密狙い→這い寄りで爪を腰の下に差し込む設計。フォーク実験（`v7_test_fork.py --from south`）では BZ の中心線がパッカンの左 1.5〜3 cm・平行なら両爪が腰の下に入って z 0.22 m まで持ち上がり、そのまま降ろして自力で立てた（3 回/3 回）。しかし通しでは BZ の寄せ残差が 5〜12 cm・4〜5° で、結果は「斜めに持ち上がる ×2（#19 は降ろした後に転んで 2.1 s で自力起立、#17 はフォークに引っかかって起きられず）／押し倒して自力起立 ×1／爪が外れて何も起きず ×2」。立ったパッカンは爪の間隔 13 cm より細く、中央なら爪が素通り、4 cm ずれると脚を蹴って倒す。**→ 方針転換（ゆうころ）：この「失敗したとき次にどうするか」を支配人 AI〈アイランドマスター〉の判断として学習させる最終課題に。設計は `MANAGER_DESIGN.md`（Notion 子ページにも同内容）。** take5 の結末は `--ending push` で再現（タグ `take5`）。

**支配人 AI（10/27 深夜〜）**：`manager_env.py`（LIFT 場面を gymnasium 環境に。行動＝既存スキル WAIT／DOCK／LIFT／PUSH_SIDE／STANDUP／CLEAR、観測 32 次元、報酬・決定ログ・ルール固定／ランダム基準）、`manager_train.py`（SB3 PPO、8 並列、同一シード評価）。実行は jumper venv（sb3 2.9.2、**gymnasium は 1.0.0 に固定**：1.1 は Python 3.10.6 の typing バグで import 不可）。学習時はリセットで姿勢を書き込む（動画では不可）。block_2 (4,−3) に BZ を重ねると弾け飛ぶので再抽選。設計と比較は `MANAGER_DESIGN.md`。

**Navigator の罠**：経由点同士が 0.35 m しか離れていないと BZ（全長 1.4 m）は旋回半径の都合で到着できず円を描き続ける。「東側を南下 → 目標の真東 1.9 m」の 2 点にし、向きはその場旋回（`aim`）で合わせる。

**罠**：子シーンの照明を `light_active=0` で消さないと床が白飛び。JP の衝突メッシュは geomgroup 1 を非表示。ポリシーの切替（velstand⇄sitstand、locomotion⇄jump）は `reset()` と PD ゲイン切替（jump は kp 20）を忘れずに。履歴付き観測（跳跳）はストライド 4・5 フレーム・古い順。

## 1. ゴール

BZ(ブルドーザー) がコースを作る → MD(パッカン/Microduck) が歩く → JP(跳跳/Jumper) がジャンプで接近 → 接触 → MD転倒 → 復帰、を1本の動画にする。
提出用の素材としてレンダリング動画 (MP4) を生成する。

---

## 2. ファイル構成

### スクリプト (`D:\IslandMaster\mujoco_3body\`)

| ファイル | 役割 |
|---|---|
| `build_3body_arena.py` | 最初の3体合体テスト（MjSpec.attach検証用） |
| `run_3body.py` | MjViewer表示版（レンダリングなし） |
| `test_load_bulldozer.py` | BZ XML単体ロードテスト |
| `test_load_microduck.py` | MD XML単体ロードテスト |
| **`render_3body.py`** | v3レンダリング — 空arenaにBZ/MD/JP attach |
| **`render_3body_v4.py`** | v4 — BZのscene_fork_tracks.xmlをベースarenaに変更 |
| **`render_3body_v5.py`** | v5 — v4 + 坂道パーツ追加（未完成、BZが詰まる） |

### 動画 (`D:\IslandMaster\mujoco_3body\out\`)

| ファイル | 内容 | 状態 |
|---|---|---|
| `3body_arena_v1.mp4` (15MB) | 初版。床チカチカ、MD潰れる、JP静止 | 記録 |
| `3body_arena_v2.mp4` (2KB) | 床修正、JPまだ逃げる | 記録 |
| `3body_arena_v3.mp4` (2KB) | JP到達、MD安定化 | 記録 |
| `3body_arena.mp4` | = v3のコピー | 同上 |
| `3body_arena_v4.mp4` (1.2MB) | BZステージベース。BZ前進＋JP到達。坂なし | **v4 OK** |
| `3body_arena_v5.mp4` (1.4MB) | 坂道追加だがBZ詰まり＋JP制御不安定 | 未完成 |

### Python環境

```
D:\IslandMaster\mujoco_3body\.venv\Scripts\python.exe
  mujoco==3.11.0, imageio==2.38.0
  Python 3.10系
```

実行例:
```powershell
& "D:\IslandMaster\mujoco_3body\.venv\Scripts\python.exe" render_3body_v5.py
```

---

## 3. ロボットXMLパス

| ロボット | XML | 備考 |
|---|---|---|
| BZ (ブルドーザー) | `D:\IslandMaster\physical-ai-course-builder\scene_fork_tracks.xml` | フォーク＋キャタピラ版。blocks 4個、ball 1個含む |
| MD (パッカン) | `D:\IslandMaster\microduck_rl\src\mjlab_microduck\robot\microduck\scene.xml` | STANDキーフレームあり |
| JP (跳跳) | `D:\IslandMaster\jumper\assets\jumper\jumper.xml` | actuatorなし（実行時に追加が必要） |

---

## 4. MjSpec.attach の要点（痛い目にあった知見）

### 4-1. プレフィックスと名前空間
- `arena.attach(child_spec, prefix="md-", frame=frame)` で全名前にprefixが付く
- BZをベースarenaにした場合、BZの名前はプレフィックスなし（`dozer`, `drive_lf`等）
- MD/JPは `md-`, `jp-` プレフィックス付き

### 4-2. freejoint qpos はワールド座標
- freejoint qpos[0:3] は**常にワールド座標**、frameからの相対ではない
- MDのSTANDキーフレーム復元時は `kf[0:3] += MD_FRAME_POS` で配置オフセットを加算
- JPも同様: `data.qpos[adr+0] = JP_FRAME_POS[0]` で世界座標を直接指定

### 4-3. 床のZ-fighting
- 各子シーンが自分のfloor geomを持ち込む → arenaの床と重なってチカチカする
- 解決: コンパイル後に子の床を無効化
  ```python
  gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "md-floor")
  model.geom_contype[gid] = 0
  model.geom_conaffinity[gid] = 0
  model.geom_rgba[gid] = [0, 0, 0, 0]
  ```

### 4-4. mj_resetDataKeyframe は全ロボットを巻き込む
- `mj_resetDataKeyframe()` はモデル全体のqpos/qvel/ctrlをリセットする
- 個別ロボットの復元は per-robot reset関数を自作する必要がある

### 4-5. MjSpec material texture
- `mat.texture = "name"` は AttributeError
- 正しくは `mat.textures[0] = "name"` (MjStringVec)

### 4-6. JP (Jumper) にはactuatorがない
- jumper.xmlは `<actuator>` セクションなし（mjrl-labが実行時追加する設計）
- 手動で position actuator を追加する必要あり:
  ```python
  for jname in JP_JOINTS:
      act = arena.add_actuator()
      act.name = f"jp-{jname}"
      act.target = f"jp-{jname}"
      act.trntype = mujoco.mjtTrn.mjTRN_JOINT
      act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
      act.gainprm[0] = 50.0
      act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
      act.biasprm[1] = -50.0
      act.biasprm[2] = -0.5
  ```

---

## 5. コントローラ設計の現状

### BZ (BulldozerCtrl)
- velocity actuator: `drive_lf/lr/rf/rr` (kv=8, ctrlrange [-8,8])
- position actuator: `blade_lift` (kp=1200, range [0, 0.5])
- 前進速度 5 rad/s → 停止はx座標 or 時間ベース

### MD (MicroduckCtrl)
- STANDキーフレームのctrlをベースに、hip_pitch/kneeをsin波で揺らして歩行表現
- **stand-assist**: `xfrc_applied[body][2] = (target_z - z) * 200.0` で沈み防止
- implicitfastインテグレータでMDが沈む問題あり（Euler前提のモデル）

### JP (JumperCtrl)
- 脚グループ: LM, RM, LR, RR (後脚), LF, RF (前脚/腕)
- ジャンプ: 周期0.5s、推進0.14s、残りはtuck
- **移動は xfrc_applied 外力依存** — 関節gaitだけでは推進力が足りない
  - ジャンプ中: Z=25N(上), X=-20N(前進)
  - 滑走中: X=-8N * dist
- **ブレーキ問題**: dist < 0.5 で `20*dist` のバネ力だが、まだMDを通り越す
- y方向の横ずれ補正: `-jp_y * 3.0`

---

## 6. 残っている課題

### 最優先（提出動画に必要）
1. **BZがblock_1に衝突して止まる**: v4/v5共通。blocks をBZ進路から物理的にどかすか、collision無効化するか、BZの初期位置を変えるか
2. **JPのオーバーシュート**: MDの位置で止まらず通過する。バネ＋ダンパ制御の調整か、距離ベースの力上限が必要
3. **MDの沈み**: implicitfast vs Euler問題。xfrc_applied assist でしのいでいるが不安定（z=0.06~0.11を行き来）

### 坂道統合（v5）
4. **坂道パーツの配置**: `slope_parts.py` の `add_slope()` がmesh頂点ベースの正確な坂を生成。v5ではMjSpec boxで近似したが見栄えが劣る
5. **推奨**: `slope_assembly.py::assembly_xml()` でElementTreeベースのXMLを生成→一時ファイル保存→MjSpec.from_fileで読み込みが最も忠実
6. 坂道をBZ進路（y=0）に配置すると衝突。y=±2以上に離すか、コース全体を90度回転してx軸方向にする

### 演出
7. **カメラワーク**: 現状はゆっくり回転する俯瞰カメラ。固定カットや追尾カメラのほうが見栄えするかも
8. **シナリオ分割**: BZのコース施工→MDの走行→JPの接近、を明確なフェーズにして長めの動画にする
9. **ゆうころの要望**: 「カニが逃げるのおもしろい」「くねくねパーツも？」

---

## 7. BZコース施工システム（Notion設計書より）

Notionページ: https://www.notion.so/3f35e0de2f3281dbabfec38aecafe183

- **パーツ**: blocks 4個（44cm高）、up-slope、down-slope（天面44cm共通規格）
- **施工フロー**: AI計画 → BZフォークで運搬・設置 → 走行テスト
- **実績**: 「こもれびの小さな峠」（坂2個、166秒）
- **slope_assembly.py**: `assembly_xml(scene_path)` で坂道入りXMLを生成
- **GitHub**: https://github.com/ortiz-ai-partners/physical-ai-course-builder

---

## 8. 推奨する進め方

ゆうころの提案どおり、段階的に組み立てるのが良い:

1. **BZ単体で施工動画** — `slope_assembly.py` の既存コードでBZが坂を設置する動画を作る（これは physical-ai-course-builder 側で既に動く）
2. **そのステージにMDを追加** — 施工完了後のXML（または assembly_xml() 出力）にMD attachして歩かせる
3. **JPを追加** — MD動画にJPを足してジャンプ接近シーン
4. **動画つなぎ** — 3ステップを順に録画して連結するか、1スクリプトでフェーズ制御

**ポイント**: 1本のスクリプトで全部やろうとすると複雑化する（今回のv1-v5の轍）。段階ごとに動画を確認してから次へ進むほうが確実。

---

## 9. 鉄則（ゆうころの指示）

- **中間成果物は消さない** — v1〜v5の動画とスクリプトはすべて残す
- **作業したらNotion追記** — MuJoCo 3体連携ページ（上記）に進捗を書く
- **「運」「確率」で報告しない** — 失敗は技術的に分析する（コーチの運動の見方）
