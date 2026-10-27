# MuJoCo 3体連携 — ブルドーザー × パッカン（Microduck）× 跳跳（Jumper）

松尾研 Physical AI 応用1 最終課題（締切 2026-11-02）の 3 体連携動画。
**1 つの MuJoCo 3.11 ワールドで 3 台を同時に物理シミュレーションし、外力・テレポートなしで、各機体が自分のアクチュエータだけで動く**ことを原則にしている（v7 以降）。

- 🚜 ブルドーザー（BZ）：[physical-ai-course-builder](https://github.com/ortiz-ai-partners/physical-ai-course-builder) のルール制御（`SlopeAssembly` / `Transport` / `Navigator`）そのまま。坂 2 個を施工し、峠を走破する。
- 🐦 パッカン（Microduck）：pollen-robotics の公式 ONNX ポリシー（`velstand`：立位・歩行・転倒からの自力起立、`alpha_sitstand`：座る⇄立つ、首操作）。XML の公式サーボ値。
- 🦀 跳跳（Jumper）：公式バンドルの `locomotion` / `jump` / `dance_crab` ポリシー（`deploy/fsm/src/obs.rs` の契約を転記）。前方ジャンプは公式 jump に股関節ヨーの後方掃きを重ねたもの（関節目標のみ）。

## 筋書き（v5 = take 6、2026-10-28）— 支配人AI〈アイランドマスター〉が次の一手を選ぶ

施工中はパッカンと跳跳が空き地で戯れる → BZ が峠を渡り始めるとパッカンが後を追う → 16° の坂に 2 回挑んで座り込む（公式ポリシーでは登れない：事実） → 跳跳が横を通って坂を登り、天面で引っかかったら前方ジャンプ、峠を越える → パッカンが仲間を呼ぶ → 跳跳がコースの東側を回って戻る（固定プログラム） → **ここから支配人AIが判断**（吹き出しに定型セリフ）：「パッカン、カニさんの方を向いて座って」→「カニさん、そっと押し上げてあげて」（座ったパッカンを跳跳が 0.3 m/s で坂の上まで押す）→「カニさん、少し離れて」→「パッカン、立てる？」→「パッカン、そのまま進んで」（天面を歩いて下り坂を降りる）→ **3 体ともコースを渡った** → 跳跳が回り込んで応援ダンス、BZ はフォークで万歳（固定）。

ブルドーザーはパッカンに触れない（ゆうころ 10/28：首を持ち上げると破損の恐れ）。v4（take 5）の結末「BZ のフォークが押し倒す→自力起立」は `--ending push` で残してある。

### 支配人AI（最終課題の核）

「うまくいかなかったとき、次にどうするか」を選ぶ部分だけを学習する。各機体の動作は既存コード（公式ポリシー＋ルール制御、物理のみ）。

| ファイル | 内容 |
|---|---|
| `crab_help.py` | スキル（生成器）WAIT／SEAT／PUSH／BACK_OFF／STANDUP／WALK_ON、観測 45 次元、固定ルール。学習環境と通し動画が共用 |
| `manager2_env.py` | gymnasium 環境：1 ステップ＝1 スキル、開始状態 6 種（足元で座り／別の向き／立ち／転倒、天面で座り／転倒）、コース監視（4 cm で破損＝失敗）、吹き出し付き録画 |
| `manager2_train.py` | SB3 PPO（MLP 64×64、12 並列）の学習／同一シード評価（PPO・固定ルール・ランダム）／デモ動画 |
| `manager2_tabq.py` | 表形式 Q 学習（比較基準）：状態キー＝直前の結果 × 姿勢 × 進行段階 × 南向き × 座席 × 密着 × 押し上げ回数 |
| `manager2_report.py` | 同一シード評価の比較表・場面別・行動回数・固定ルールとの 2×2（判断の失敗とスキルの失敗を分ける）→ `out\manager_runs\comparison_v2.md` |
| `manager_env.py` ほか `manager_*.py` | v1（BZ がフォークで扱う版）。BZ 禁止で凍結、履歴 |
| `MANAGER_DESIGN.md` | 設計メモ v1〜v1.4（事実・実験・比較。§7 が v2 の結果） |

同一シード評価（30 シード 5000〜5029、決定的方策、開始場面は乱数）：

| 支配人 | 学習 | 渡り切り | 天面到達 | 無駄な手／話 | 通し台本（take） |
|---|---|---|---|---|---|
| 固定ルール | なし | 25/30 | 97% | 0.13 | take 6：5 手（描画版 8 手、押し直し 1 回） |
| 表形式 Q `tabq2_small` | 120 話、2 h | 23/30 | 93% | 13.97 | take 7：8 手 |
| PPO 小 `ppo2_small` | 3k 決定、54 min | 0/30 | 27% | 61.9 | — （WALK_ON に固着） |
| PPO 中 `ppo2_medium2` | 12k 決定、4 h 13 min | （評価中） | | | take 8：ヘッドレスは 4 手で渡り切り（BACK_OFF を省く）、描画版は失敗（止まった押しの後に STANDUP、転倒・密着で SEAT 連打） |
| PPO 中（継続）`ppo2_medium3` | +12k 決定、転倒・密着の開始を増量 | （学習中） | | | take 9 予定 |
| ランダム | なし | 9/30 | 80% | 8.4 | — |

失敗の帰属：固定ルールとの同一シード 2×2 で「ルールは渡ったが方策は失敗」＝判断の失敗、「両方失敗」＝スキルの失敗（天面の継ぎ目での転倒など）。押し上げスキルは正しい状態で呼んでも 63% なので、「やり直しの判断」が支配人の仕事になる。

## 動かし方

実行環境は `D:\IslandMaster\jumper\.venv`（Python 3.10、mujoco 3.11.0、onnxruntime 1.23.2、imageio）。隣に `physical-ai-course-builder/`、`jumper/`（公式バンドル `out/bundle_example/jumper/`）、`microduck_rl/` が必要（`v6_common.py` の `BASE` 直下）。

```powershell
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --test --ending crab              # ヘッドレス検証（出来事のログ）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager rule --tag _take6   # 描画 → out\3body_arena_v7_take6.mp4（音声付き）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_crab_push.py --seated --crest --face-crab --crab-vx 0.3 --video out\v7_crab_push_cross.mp4   # 押し上げ実験
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_env.py --episodes 2 --policy rule   # 学習環境の煙試験
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_train.py train --envs 12 --steps 12000 --rollout 48 --seed 1 --run ppo2_medium2   # PPO 中規模（約 4 時間）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_train.py eval --run ppo2_medium2 --episodes 30 --policies ppo --seed0 5000       # 30 シード評価
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_tabq.py train --episodes 120 --run tabq2_small                                   # 表形式 Q（約 2 時間）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_report.py --runs ppo2_small ppo2_medium2 baselines_v2 tabq2_small                # 比較表と 2×2
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager tabq --run tabq2_small --tag _take7                    # 学習済み Q 表が支配人
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager ppo --run ppo2_medium2 --tag _take8                    # 学習済み PPO が支配人
```

| ファイル | 内容 |
|---|---|
| `v7_full.py` | 通し台本（1 つの連続シミュレーション）。`--tag` で版を分ける |
| `v7_policies.py` | 公式ポリシーの観測転記：`JumperLocomotion` / `JumperJump` / `JumperDance` / `MicroduckPolicy` |
| `v7_test_*.py` | 単体検証（歩行・ジャンプ・前方ジャンプ・velstand・sitstand・衝突・首・ダンス・フォーク） |
| `v6_common.py` / `v6_robots.py` | 動画・字幕・カメラ、`MjSpec.attach` による 3 体アリーナ |
| `v6_phase1_build.py` | BZ 単体施工 → `out\v6_stage_built.xml`（施工済みの独立シーン） |
| `render_3body*.py`, `v6_phase2/3/4_*.py` | v1〜v6 の記録（v6 Phase 2〜3 は外力あり：採用せず、履歴として残置） |
| `HANDOVER.md` | 引継ぎ文書（事実・罠・時系列） |
| `out/` | 動画・レポート（`3body_arena_v7_take6.mp4` = 固定ルール支配人で 3/3、`take7` = 学習済み Q 表、`take8` = 学習済み PPO、`take4`/`take5` = 旧結末（押し倒し）、`manager2_demo_*.mp4` = 学習環境のデモ、`*.notion.mp4` = 圧縮版）。`out\manager_runs\<run>\` に学習ログ・評価 JSON・方策 |

Notion「MuJoCo 3体連携」ページに検証結果を逐次記録している。
