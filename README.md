# MuJoCo 3体連携 — ブルドーザー × パッカン（Microduck）× 跳跳（Jumper）

松尾研 Physical AI 応用1 最終課題（締切 2026-11-02）の 3 体連携動画。
**1 つの MuJoCo 3.11 ワールドで 3 台を同時に物理シミュレーションし、外力・テレポートなしで、各機体が自分のアクチュエータだけで動く**ことを原則にしている（v7 以降）。

- 🚜 ブルドーザー（BZ）：[physical-ai-course-builder](https://github.com/ortiz-ai-partners/physical-ai-course-builder) のルール制御（`SlopeAssembly` / `Transport` / `Navigator`）そのまま。坂 2 個を施工し、峠を走破する。
- 🐦 パッカン（Microduck）：pollen-robotics の公式 ONNX ポリシー（`velstand`：立位・歩行・転倒からの自力起立、`alpha_sitstand`：座る⇄立つ、首操作）。XML の公式サーボ値。
- 🦀 跳跳（Jumper）：公式バンドルの `locomotion` / `jump` / `dance_crab` ポリシー（`deploy/fsm/src/obs.rs` の契約を転記）。前方ジャンプは公式 jump に股関節ヨーの後方掃きを重ねたもの（関節目標のみ）。

## 筋書き（v5 = take 6、2026-10-28）— 支配人AI〈アイランドマスター〉が次の一手を選ぶ

施工中はパッカンと跳跳が空き地で戯れる → BZ が峠を渡り始めるとパッカンが後を追い、跳跳は坂の足元の脇へ来る → 16° の坂に 2 回挑んで座り込む（公式ポリシーでは登れない：事実）、**その間、跳跳は横でハサミを上げる公式ダンスで応援**（10/28 昼） → 跳跳が横を通って坂を登り、天面で引っかかったら前方ジャンプ、峠を越える → パッカンが仲間を呼ぶ → 跳跳がコースの東側を回って座席の後ろへ戻る（固定プログラム、呼ばれている途中で帰り始める＝事前移動） → **ここから支配人AIが判断**（吹き出しに定型セリフ）：「パッカン、カニさんの方を向いて座って」→「カニさん、そっと押し上げてあげて」（座ったパッカンを跳跳が 0.3 m/s で坂の上まで押す）→「カニさん、少し離れて」→「パッカン、立てる？」→「パッカン、そのまま進んで」（天面を歩いて下り坂を降りる）→ パッカンが天面を歩き出すと跳跳が 0.8 m 後ろについて峠を越え、下り坂を降りる → **3 体ともコースを渡った** → **ゴールで輪になって万歳**（固定、ゆうころ 10/28 昼の案＝`--finale circle`、take 13 以降）：BZ はパッカンが天面を歩く間にフォークを上げてその場で向きを変え、パッカンと跳跳は坂の出口の北を回って BZ の前の半円に着き、全員が中央を向く → BZ はフォークを上げ下げ、パッカンは手がないので屈伸（sitstand）しながら首を振り、跳跳は公式ダンスで腕を上げて最後は両腕を上げたまま。take 9／10 の結末（渡った所で三人そろって万歳）は `--finale procession`、take 6／7 の結末（跳跳が東側を回り込み、離れた所でダンス）は `--finale around` で残してある。動画の速度はすべて 2 倍以下（提出の規則）、万歳のダンスは等速。

**跳跳の表情（ゆうころ 10/28 夕、take 30 以降）**：支配人の行動と結果から表情表で選ぶ（`crab_face.py`）— 戯れ・待機はまる目、持ち場へ・坂登りは真剣、押し上げ中は ＞＜、押しに失敗した直後の手は ＞＜＋汗、応援・祝賀ダンスはにっこり、パッカンが渡り切ったらキラキラ、転倒はぐるぐる。実機の跳跳には丸い目のディスプレイが 2 つあり、公式リポジトリは dance 用の目アニメ（開く・まばたき・半目・キラキラ、動画）を同梱している（状態で表情を切り替える API はない）。顔は表示パネルに貼った描画専用の板で、画面左下の「顔モニター」（顔カメラの小窓）に映す。物理は不変：顔あり／なしのヘッドレス A/B で最終状態のダイジェスト・出来事・判断がすべて一致（`analysis/face_check.py`）。学習はしない（表情に報酬がない）。

ブルドーザーはパッカンに触れない（ゆうころ 10/28：首を持ち上げると破損の恐れ）。v4（take 5）の結末「BZ のフォークが押し倒す→自力起立」は `--ending push` で残してある。

### 支配人AI（最終課題の核）

「うまくいかなかったとき、次にどうするか」を選ぶ部分だけを学習する。各機体の動作は既存コード（公式ポリシー＋ルール制御、物理のみ）。

| ファイル | 内容 |
|---|---|
| `crab_help.py` | スキル（生成器）WAIT／SEAT／PUSH／BACK_OFF／STANDUP／WALK_ON、観測 45 次元、固定ルール。学習環境と通し動画が共用 |
| `manager2_env.py` | gymnasium 環境：1 ステップ＝1 スキル、開始状態 7 種（足元で座り／別の向き／立ち／転倒、天面で座り／転倒、坂の途中で転倒＋カニ密着＝押しに失敗した後の状態）、報酬 v2.1／v2.2（v2.2 は転んだ相手への無駄な SEAT／STANDUP も −1、学習用のみ）、コース監視（4 cm で破損＝失敗）、吹き出し付き録画 |
| `manager2_train.py` | SB3 PPO（MLP 64×64、12 並列）の学習（継続学習 `--init-from`、開始分布と報酬版の指定、2,000 決定ごとのチェックポイント）／同一シード評価（PPO・固定ルール・ランダム）／デモ動画 |
| `manager2_tabq.py` | 表形式 Q 学習（比較基準）：状態キー＝直前の結果 × 姿勢 × 進行段階 × 南向き × 座席 × 密着 × 押し上げ回数 |
| `manager2_report.py` | 同一シード評価の比較表・場面別・行動回数・固定ルールとの 2×2（判断の失敗とスキルの失敗を分ける）→ `out\manager_runs\comparison_v2.md` |
| `analysis/` | 学習記録・評価ログの分析スクリプト（失敗した押しの直後の手 `after_push_fail.py`、転倒状態の収益 `fallen_value.py`、分位ごとの行動分布 `train_stats.py`／`fallen_stats.py`、スキル信頼度、失敗の型、動画の静止画取り出し、顔の有無で物理が同じことの確認 `face_check.py`）。設計メモ §7.5b〜7.8 の表の出どころ |
| `manager_env.py` ほか `manager_*.py` | v1（BZ がフォークで扱う版）。BZ 禁止で凍結、履歴 |
| `MANAGER_DESIGN.md` | 設計メモ v1〜v1.4（事実・実験・比較。§7 が v2 の結果） |

同一シード評価（30 シード 5000〜5029、決定的方策、開始場面は乱数）。**評価 v4（10/28 午後、新コース＝峠の隙間 1 cm、エピソード独立、`out\manager_runs\comparison_v4.md`、設計メモ §7.15）**。旧コース（隙間 5 cm）の評価 v3（`comparison_v3b.md`）と朝の値（持ち越しあり、`comparison_v2.md`）は括弧：

| 支配人 | 学習 | 渡り切り | 天面到達 | 無駄な手／話 | 通し台本（take） |
|---|---|---|---|---|---|
| 固定ルール（near_lip） | なし | **29/30**（旧コース v3 23/30、朝 25/30） | 100% | 0.07 | **新コース（峠の隙間 1 cm）：take 30 輪の万歳・take 33 追走（顔付き、5 手、転倒 0、提出候補。顔なしの take 24／25 と物理が同一）**。旧コース：take 16／18（同じ結末）、take 9、take 6 |
| 表形式 Q `tabq2_small` | 120 話、2 h | **25/30**（旧コース v3 24/30、朝 23/30） | 97% | 5.17 | **新コース：take 32 輪の万歳（顔付き、8 手、転倒 0、`--jitter 0.4`、提出候補。顔なしの take 28 と物理が同一；0.8 の take 29 も成功、0 の take 26 は下り坂の転倒で失敗）**。旧コース：take 20（jitter 0.4）、take 10、take 7 |
| PPO 小 `ppo2_small` | 3k 決定、54 min | （朝 0/30、v3／v4 未実施） | 27% | 61.9 | — （WALK_ON に固着） |
| PPO 中 `ppo2_medium2` | 12k 決定、4 h 13 min | **23/30**（旧コース v3 16/30、朝 19/30）、渡った回は最速 79 s | 83% | 0.47 | 失敗 7 本中 5 本は転んだ相手への SEAT 連打（判断の穴、設計メモ §7.15）。take 8（旧コース）：ヘッドレスは 4 手で渡り切り（BACK_OFF を省く）、描画版は失敗（止まった押しの後に STANDUP、転倒・密着で SEAT 連打） |
| PPO 中（継続）`ppo2_medium3` | +4.9k 決定で中断（同じ報酬、足元の転倒・密着の開始を増量） | — | | | 学習中の成功率は 80% で横ばい、転倒直後の BACK_OFF は 13/52。置いた転倒は「押しに失敗して挟まった」状態を再現せず（SEAT のままでも 9/13 成功）。重みは未保存、ログのみ |
| PPO 中（継続、報酬 v2.2）`ppo2_v22` | +12k 決定、転んだ相手への無駄手に −1、坂の途中で転倒＋密着の開始 20%、4 h 28 min | **26/30**（旧コース v3 16/30：押しが効かないと「下がる→押す」の堂々巡りで手数上限） | 97% | 0.60 | 転んだ相手への SEAT／STANDUP 連打 0 本（報酬 v2.2 の狙いどおり）。**新コース：take 31 輪の万歳（顔付き、4 手、転倒 0、ずらしなし、提出候補。顔なしの take 27 と物理が同一）**。旧コース：take 23（4 手、jitter 0.8）、take 22（押しに失敗→自分で離れる→再押し、7 手、jitter 0.4） |
| ランダム | なし | 14/30（旧コース v3 9/30） | 73% | 8.20 | — |

評価 v4 の 2×2（固定ルールとの同一シード）：PPO v2.2 — 両方渡った 25／ルールだけ 4／方策だけ 1／両方失敗 0。Q 表 — 24／5／1／0。PPO 中 — 22／7／1／0。ランダム — 14／15／0／1。残る失敗は下り坂（足元）で転んだ相手に打つ手がない型が中心（固定ルールの 1 本もこれ）、PPO 中だけ「転んだ相手に SEAT 連打」の穴が残り、PPO v2.2 はそれを埋めた（設計メモ §7.15）。旧コース（評価 v3）の 2×2：Q 表 — 両方渡った 19／ルールだけ 4／Q 表だけ 5／両方失敗 2。PPO 中 — 13／10／3／4。固定ルールの失敗 7 本のうち 6 本は天面の継ぎ目や押し上げ中に転んだ相手を待ち続ける型（転んだ相手に働きかける手が行動にない＝スキル側の上限）。朝の評価ではエピソード間でソルバーの状態が持ち越されていた（設計メモ §7.10）。

失敗の帰属：固定ルールとの同一シード 2×2 で「ルールは渡ったが方策は失敗」＝判断の失敗、「両方失敗」＝スキルの失敗（天面の継ぎ目での転倒など）。押し上げスキルは正しい状態で呼んでも 63% なので、「やり直しの判断」が支配人の仕事になる。その要は「押しに失敗したらカニが下がる」（ゆうころ 10/28 朝）：固定ルールは失敗した押しの後 13/13 で下がる（take 6 の 2:20）。PPO 中は転倒直後 3/10 で、報酬 v2.1 では転んだ相手への無駄な SEAT／STANDUP が時間しか引かれず学ぶ圧力がなかった → 報酬 v2.2 と「坂の途中で転倒＋密着」の開始場面で継続学習（`ppo2_v22`）。

## 動かし方

実行環境は `D:\IslandMaster\jumper\.venv`（Python 3.10、mujoco 3.11.0、onnxruntime 1.23.2、imageio）。隣に `physical-ai-course-builder/`、`jumper/`（公式バンドル `out/bundle_example/jumper/`）、`microduck_rl/` が必要（`v6_common.py` の `BASE` 直下）。

```powershell
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --test --ending crab              # ヘッドレス検証（出来事のログ）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager rule --tag _take6   # 描画 → out\3body_arena_v7_take6.mp4（音声付き）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_crab_push.py --seated --crest --face-crab --crab-vx 0.3 --video out\v7_crab_push_cross.mp4   # 押し上げ実験
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_env.py --episodes 2 --policy rule   # 学習環境の煙試験
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_train.py train --envs 12 --steps 12000 --rollout 48 --seed 1 --run ppo2_medium2   # PPO 中規模（約 4 時間）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_train.py eval --run ppo2_medium2 --episodes 30 --policies ppo --seed0 5000       # 30 シード評価
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_train.py train --envs 12 --steps 12000 --seed 3 --run ppo2_v22 --init-from ppo2_medium2 --reward v2.2 --scenario-weights "toe_seated_ok=0.20,toe_seated_wrong=0.15,toe_standing=0.15,toe_fallen=0.10,deck_seated=0.15,deck_fallen=0.05,ramp_fallen=0.20" --crab-toe-weights "behind=0.5,beside=0.2,touching=0.3"   # 継続学習（報酬 v2.2、約 4 時間）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_env.py --episodes 1 --policy rule --scenario ramp_fallen --crab touching --reward v2.2 --video out\manager2_smoke_ramp_fallen_rule.mp4   # 新しい開始場面の煙試験（動画付き）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_tabq.py train --episodes 120 --run tabq2_small                                   # 表形式 Q（約 2 時間）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" manager2_report.py --runs ppo2_small ppo2_medium2 baselines_v2 tabq2_small                # 比較表と 2×2
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager tabq --run tabq2_small --tag _take7                    # 学習済み Q 表が支配人
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager ppo --run ppo2_medium2 --tag _take8                    # 学習済み PPO が支配人
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager rule --finale procession --tag _take9                  # take 9 の結末（跳跳が追走、ゴールで三人の万歳）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager rule --tag _take13                                     # 既定：輪の万歳・応援ダンス・事前移動・2 倍速上限（--no-prestage で先回りなし）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_cheer.py --circle --video out\v7_cheer_circle_test1.mp4                            # 輪の万歳の単体テスト
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_bz_drive.py                                                                        # BZ の前進・旋回・フォーク上下の単体テスト
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_cheer.py --video out\v7_cheer_test3.mp4                                           # ゴールの万歳の単体テスト（配置は手置き）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_face.py                                                                            # 跳跳の顔の単体テスト（7 表情 → out\face_test\）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --test --no-face --tag _facecheck_A; python v7_full.py --test --tag _facecheck_B; python analysis\face_check.py out\v7_full_report_facecheck_A.json out\v7_full_report_facecheck_B.json   # 顔の有無で物理が同じことの確認
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --ending crab --manager rule --tag _take30                                     # take 24 の顔付き（既定で顔あり、--no-face で無し）
```

| ファイル | 内容 |
|---|---|
| `v7_full.py` | 通し台本（1 つの連続シミュレーション）。`--tag` で版を分ける |
| `v7_policies.py` | 公式ポリシーの観測転記：`JumperLocomotion` / `JumperJump` / `JumperDance` / `MicroduckPolicy` |
| `v7_test_*.py` | 単体検証（歩行・ジャンプ・前方ジャンプ・velstand・sitstand・衝突・首・ダンス・フォーク、ゴールの万歳 `v7_test_cheer.py`、BZ の前進・旋回 `v7_test_bz_drive.py`、跳跳の顔 `v7_test_face.py`） |
| `crab_face.py` | 跳跳の表情：表示パネルの描画専用スクリーン（7 表情の絵、`MjSpec` で追加）、顔カメラ、支配人の行動と結果から表情を選ぶ表情表（`FaceDriver`）。10/11 のレッスン動画の顔（`jumper/out/face_tools/face_display.py`）が元 |
| `v6_common.py` / `v6_robots.py` | 動画・字幕・カメラ、`MjSpec.attach` による 3 体アリーナ |
| `v6_phase1_build.py` | BZ 単体施工 → `out\v6_stage_built.xml`（施工済みの独立シーン） |
| `render_3body*.py`, `v6_phase2/3/4_*.py` | v1〜v6 の記録（v6 Phase 2〜3 は外力あり：採用せず、履歴として残置） |
| `HANDOVER.md` | 引継ぎ文書（事実・罠・時系列） |
| `out/` | 動画・レポート（**新コース（峠の隙間 1 cm、take 24 以降）：`take24`/`take25` = 固定ルール（輪／追走）、`take27` = PPO v2.2（輪）、`take28` = Q 表（輪）**；旧コース：`take16`/`take18` = 固定ルール、`take20` = Q 表、`take22`/`take23` = PPO v2.2、`take14` = 最初の全部入り成功版、`take11`〜`take13`・`take15`/`17`/`19`/`21`/`26` = 失敗版、`take9` = 追走の結末（施工 4 倍速）、`take10` = 学習済み Q 表で同じ結末、`take6` = 固定ルールで 3/3（旧結末）、`take7` = 学習済み Q 表（旧結末）、`take8` = 学習済み PPO（失敗）、`take4`/`take5` = 旧々結末（押し倒し）、`manager2_demo_*.mp4` = 学習環境のデモ、`v7_cheer_test*.mp4` = 万歳の単体テスト、`face_test\` = 顔の単体テスト、`v7_full_report_facecheck_{A,B}.json` = 顔の有無の A/B（物理同一）、`*.notion.mp4` = 圧縮版）。`out\manager_runs\<run>\` に学習ログ・評価 JSON・方策 |

Notion「MuJoCo 3体連携」ページに検証結果を逐次記録している。
