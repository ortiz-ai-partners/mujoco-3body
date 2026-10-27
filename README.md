# MuJoCo 3体連携 — ブルドーザー × パッカン（Microduck）× 跳跳（Jumper）

松尾研 Physical AI 応用1 最終課題（締切 2026-11-02）の 3 体連携動画。
**1 つの MuJoCo 3.11 ワールドで 3 台を同時に物理シミュレーションし、外力・テレポートなしで、各機体が自分のアクチュエータだけで動く**ことを原則にしている（v7 以降）。

- 🚜 ブルドーザー（BZ）：[physical-ai-course-builder](https://github.com/ortiz-ai-partners/physical-ai-course-builder) のルール制御（`SlopeAssembly` / `Transport` / `Navigator`）そのまま。坂 2 個を施工し、峠を走破する。
- 🐦 パッカン（Microduck）：pollen-robotics の公式 ONNX ポリシー（`velstand`：立位・歩行・転倒からの自力起立、`alpha_sitstand`：座る⇄立つ、首操作）。XML の公式サーボ値。
- 🦀 跳跳（Jumper）：公式バンドルの `locomotion` / `jump` / `dance_crab` ポリシー（`deploy/fsm/src/obs.rs` の契約を転記）。前方ジャンプは公式 jump に股関節ヨーの後方掃きを重ねたもの（関節目標のみ）。

## 筋書き（v4、2026-10-27）

施工中はパッカンと跳跳が空き地で戯れる → BZ が峠を渡り始めるとパッカンが後を追う → 16° の坂に 2 回挑んで座り込む（公式ポリシーでは登れない：事実） → 跳跳が横を通って坂を登り、天面で引っかかったら前方ジャンプ、峠を越える → パッカンが BZ を呼ぶ → BZ がコースを回って戻り、跳跳がついて戻って応援ダンス → BZ がフォークで持ち上げを試みる → パッカンは velstand で自力で立ち上がる。

## 動かし方

実行環境は `D:\IslandMaster\jumper\.venv`（Python 3.10、mujoco 3.11.0、onnxruntime 1.23.2、imageio）。隣に `physical-ai-course-builder/`、`jumper/`（公式バンドル `out/bundle_example/jumper/`）、`microduck_rl/` が必要（`v6_common.py` の `BASE` 直下）。

```powershell
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --test              # ヘッドレス検証（出来事のログ）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_full.py --tag _take6       # 描画 → out\3body_arena_v7_take6.mp4（音声付き）
& "D:\IslandMaster\jumper\.venv\Scripts\python.exe" v7_test_dance.py --video out\v7_dance_test.mp4
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
| `out/` | 動画・レポート（`3body_arena_v7_take4.mp4` = 押し倒し結末、`take5` = 戯れ＋応援ダンス版、`*.notion.mp4` = 圧縮版） |

Notion「MuJoCo 3体連携」ページに検証結果を逐次記録している。
