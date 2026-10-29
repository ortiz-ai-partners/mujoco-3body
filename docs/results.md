# 結果：支配人 AI の同一シード評価と提出動画の記録

本文書は、支配人 AI（失敗したときの次の一手を選ぶ自作 AI）の評価結果の全表と、提出動画の本編と比較用の動画で支配人 AI が打った手の時刻をまとめた結果集である。
設計は [docs/manager_ai.md](manager_ai.md)、考察は [docs/insights.md](insights.md)、動画の読み方は [docs/video_guide.md](video_guide.md)、用語の対応表は [docs/glossary.md](glossary.md) にある。
ファイル名に含まれる番号（`out/3body_arena_v7_take51.mp4` など）は固有名としてそのまま引用し、各版の設定と系譜の台帳は [docs/devlog/takes.md](devlog/takes.md) にある。

数値はすべて `out/manager_runs/` の評価ファイルと `out/v7_full_report_*.json` から転記し、各表の直下に出所と再生成コマンドを添えた。
コマンドはリポジトリルートで `python …` として実行する。評価は 1 方策 30 話で約 26〜32 分（各 `eval_summary.json` の `mean_wall_s` × 30）、学習は 1〜4.5 時間かかる（所要時間は各表に併記）。

## 読み方

### 指標の定義

| 指標 | 意味 | 出所（eval JSON のキー） |
|---|---|---|
| 渡り切り | パッカンが峠を越えて北側の床に立った話の数 | `success` |
| 天面到達 | 天面（峠の上）に一度でも到達した話の割合 | `landed` |
| 無駄な手/話 | 結果が `nothing`（何も起きなかった）で終わった手の 1 話あたりの数 | `results` の `nothing` の数 |
| 転倒/話 | パッカンが転んだ回数の 1 話あたりの平均 | `falls` |
| 手数、中央時間 | 1 話の手の数の平均、渡った話のシミュレーション時間の中央値 | `steps`、`sim_s` |
| 平均リターン | 報酬 v2.1 の合計の 1 話あたりの平均（項は表の下） | `return` |

`eval_summary.json` は `manager2_env.py` の `summarize()` が書き、比較表 `comparison_v4.md` は `manager2_report.py` の `metrics()` が同じ話ごとの記録（`eval_<policy>.json`）から作る。
報酬 v2.1 の項（`manager2_env.py` の `REWARD` と `step()`）：渡り切り +10、経過時間 −0.03/s、天面への初到達 +3、転倒 −1（1 手で最大 2 回）、時間切れ −5、コース破損 −10、
報酬上の無駄な手 −1、パッカンが転んでおらず渡り切ってもいない時の `WAIT` −0.5。
報酬上の無駄な手は、座っている相手への `SEAT`、`PUSH`・`BACK_OFF`・`STANDUP`・`WALK_ON` が `nothing` で終わった手、`stalled`・`slipped` で終わった手で、v2.2 は `still_down` を加える。
指標の「無駄な手/話」は `nothing` だけを数える（`manager2_report.py` の `wasted_per_episode`）。

### 方式名と run ディレクトリ

| 方式名 | 内容 | 既製／自作 | 評価 v4 の run | 学習の run |
|---|---|---|---|---|
| 固定ルール | `crab_help.rule_action`、条件分岐のみ | 自作、学習なし | `baselines_v4` | なし |
| PPO v2.2 | SB3 PPO、報酬 v2.2 で PPO 中規模から継続学習 | 自作、学習あり | `ppo2_v22_v4` | `ppo2_v22` |
| Q 表 | 表形式 Q 学習、状態キー 7 要素 | 自作、学習あり | `tabq2_small_v4` | `tabq2_small` |
| PPO 中規模 | SB3 PPO、報酬 v2.1、12,000 決定 | 自作、学習あり | `ppo2_medium2_v4` | `ppo2_medium2` |
| ランダム | 6 手から一様に選ぶ | 比較用 | `baselines_v4` | なし |

「中規模」「小規模」は PPO の学習量の呼び名で、PPO 中規模＝12,000 決定（`ppo2_medium2`）、PPO 小規模＝3,000 決定（`ppo2_small`、評価は付録 B だけ）。
run ディレクトリはすべて `out/manager_runs/<run>/` 以下。
評価の出力は `eval_<policy>.json`（話ごと）と `eval_summary.json`（集計）、`eval_decisions.jsonl`（手ごと）。

### 手・結果・開始場面の名前

支配人の 6 手はコードの識別子で書く（`crab_help.py` の `ACTIONS`）：`WAIT`（様子を見る）、`SEAT`（座らせる）、`PUSH`（跳跳が押し上げる）、
`BACK_OFF`（跳跳が少し離れる）、`STANDUP`（立たせる）、`WALK_ON`（見送る）。
手の結果は 13 種（`crab_help.py` の `RESULT_SLOTS`）で、本文書に出るのは `seated`・`pushed_up`・`cleared`・`standing`・`crossed`（成功）、`walked`（歩き出したが渡り切る前に転倒）、
`stalled`・`slipped`・`fell`（押しの失敗）、`still_down`（転んだ相手が起きない）、`nothing`（何も起きない）、`waited`。

開始場面は 7 種（`manager2_env.py` の `SCENARIOS`）：`toe_seated_ok`（坂の足元で正しい向きに座る）、`toe_seated_wrong`（足元で別の向きに座る）、`toe_standing`（足元で立つ）、
`toe_fallen`（足元で転倒）、`deck_seated`（天面で座る）、`deck_fallen`（天面で転倒）、`ramp_fallen`（坂の途中で転倒）。
跳跳の初期位置は `behind`（後ろ）、`beside`（横）、`touching`（密着）の 3 種。

## 評価 v4（新コース・30 シード・エピソード独立）

### 評価の条件

- コース：峠の継ぎ目の設計値 1 cm（`../physical-ai-course-builder/slope_assembly.py` の `INSTALLATION_GAP = 0.01`、commit ea5b4e7）。提出動画と同じコース。
- シード：5000〜5029 の 30 話。同じシードは全方式で同じ開始場面と同じ跳跳の初期位置になる
  （各 `eval_*.json` の `scenario`・`crab` がシードごとに 5 方式で一致することを確認した）。
- 開始場面の抽選結果：`toe_seated_ok` 6、`toe_seated_wrong` 8、`toe_standing` 6、`toe_fallen` 3、`deck_seated` 7。跳跳の初期位置は `behind` 17、`beside` 6、`touching` 7。
  `ramp_fallen` は既定の重みが 0 のため出ない。`deck_fallen` は重み 0.05 で、シード 5000〜5029 の抽選では 0 話だった（`manager2_env.py` の `SCENARIOS`）。どちらも評価されていない。
- 方策は決定的（PPO は `deterministic=True`、`manager2_train.py`）。1 話は最長 240 s、コースの部品が 4 cm 動いたら失敗（`manager2_env.py` の `COURSE_TOLERANCE`）。
- 評価の報酬は全方式 v2.1（`eval` に報酬の引数はなく `manager2_env.py` の既定値）。報酬 v2.2 は PPO v2.2 の学習だけに使った。
- エピソードは `Scene.reset()` の中で `mj_resetData` を呼んで独立させてある（`manager2_env.py`）。独立していなかった評価 v2 は付録 B。

図：`report/results_managers_ortiz.png`。左上が渡り切り（濃い棒）と天面到達（薄い棒）、右上が固定ルールとの同一シード 2×2、
下段が手数・転倒の平均と旧コースとの対比。数値は本文書の表と同じで、出所は `out/manager_runs/comparison_v4.md` と `comparison_v3b.md`。

![支配人 AI の比較（評価 v4）](../report/results_managers_ortiz.png)

### 総合表

| 方式 | 渡り切り | 天面到達 | 無駄な手/話 | 転倒/話 | 学習コスト |
|---|---|---|---|---|---|
| 固定ルール | 29/30（97%） | 100% | 0.07 | 0.33 | なし |
| PPO v2.2 | 26/30（87%） | 97% | 0.60 | 1.03 | 4 h 28 min（継続分、累計 8 h 41 min） |
| Q 表 | 25/30（83%） | 97% | 5.17 | 0.73 | 1 h 59 min |
| PPO 中規模 | 23/30（77%） | 83% | 0.47 | 0.87 | 4 h 13 min |
| ランダム | 14/30（47%） | 73% | 8.20 | 1.53 | なし |

コース破損は全方式 0 話。学習コストは CPU の実時間で、出所は学習コストの節。

| 方式 | 中央時間 s | 平均リターン | 手数/話 | 押し上げ/話 | 評価の実時間/話 |
|---|---|---|---|---|---|
| 固定ルール | 90 | +8.56 | 6.9 | 1.00 | 52.0 s |
| PPO v2.2 | 83 | +5.50 | 8.8 | 1.10 | 53.5 s |
| Q 表 | 102 | −0.93 | 13.6 | 1.23 | 60.5 s |
| PPO 中規模 | 79 | +3.40 | 7.6 | 1.10 | 60.2 s |
| ランダム | 158 | −14.98 | 23.7 | 2.67 | 63.8 s |

出所：`out/manager_runs/comparison_v4.md`（総合表の行）と各 run の `eval_summary.json`
（`crossing_rate`、`landing_rate`、`median_time_to_cross_s`、`mean_return`、`mean_steps`、`mean_falls`、`mean_pushes`、`mean_wall_s`、`course_damaged`）。

再生成（各 run の実行時の引数はログに残っていないため argparse から再構成。1 方策あたり約 26〜32 分で、`baselines_v4` は 2 方策で約 1 時間）：

```
python manager2_train.py eval --run baselines_v4 --policies rule random --episodes 30 --seed0 5000
python manager2_tabq.py eval --run tabq2_small --episodes 30 --seed0 5000 --out tabq2_small_v4
python manager2_train.py eval --run ppo2_medium2 --policies ppo --episodes 30 --seed0 5000 --out ppo2_medium2_v4
python manager2_train.py eval --run ppo2_v22 --policies ppo --episodes 30 --seed0 5000 --out ppo2_v22_v4
python manager2_report.py --runs baselines_v4 tabq2_small_v4 ppo2_medium2_v4 ppo2_v22_v4 --name comparison_v4
```

読み方の注意：30 話の評価なので 29/30 と 26/30 の差は小さく、順位の大枠（固定ルール ≥ PPO v2.2 ≥ Q 表 ≥ PPO 中規模 ≫ ランダム）以上の主張はしない。`deck_fallen`・`ramp_fallen` は評価に出ていない。

### 開始場面ごとの渡り切り（渡った数／出た数）

| 場面 | 固定ルール | PPO v2.2 | Q 表 | PPO 中規模 | ランダム |
|---|---|---|---|---|---|
| `toe_seated_ok` | 6/6 | 6/6 | 4/6 | 5/6 | 4/6 |
| `toe_seated_wrong` | 7/8 | 6/8 | 7/8 | 4/8 | 1/8 |
| `toe_standing` | 6/6 | 4/6 | 5/6 | 4/6 | 1/6 |
| `toe_fallen` | 3/3 | 3/3 | 2/3 | 3/3 | 2/3 |
| `deck_seated` | 7/7 | 7/7 | 7/7 | 7/7 | 6/7 |

出所：`out/manager_runs/comparison_v4.md`「開始場面ごとの渡り切り」、各 `eval_summary.json` の `by_scenario`。再生成は総合表と同じコマンド。

### 手の使用回数（30 話の合計）

| 手 | 固定ルール | PPO v2.2 | Q 表 | PPO 中規模 | ランダム |
|---|---|---|---|---|---|
| `WAIT` | 56 | 122 | 32 | 3 | 120 |
| `SEAT` | 26 | 23 | 45 | 114 | 115 |
| `PUSH` | 30 | 33 | 79 | 34 | 113 |
| `BACK_OFF` | 36 | 26 | 73 | 2 | 116 |
| `STANDUP` | 30 | 29 | 74 | 36 | 119 |
| `WALK_ON` | 30 | 32 | 104 | 38 | 129 |

出所：`out/manager_runs/comparison_v4.md`「行動の使用回数」、各 `eval_summary.json` の `action_counts`。再生成は総合表と同じコマンド。

### 手ごとの結末（スキルの信頼度）

各手が何回呼ばれ、何回ねらいどおりに終わったか。固定ルールは「正しい状態でだけ呼ぶ」ので、その成功率が各スキルの実力の目安になる。

| 手 | 固定ルール | PPO v2.2 | Q 表 | PPO 中規模 | ランダム |
|---|---|---|---|---|---|
| `PUSH` → `pushed_up` | 22/30（`fell` 5、`stalled` 3） | 21/33 | 24/79（`nothing` 42） | 17/34（`stalled` 9） | 19/113 |
| `SEAT` → `seated` | 24/26 | 22/23 | 31/45（`still_down` 10） | 17/114（`still_down` 96） | 47/115 |
| `BACK_OFF` → `cleared` | 35/36 | 9/26（`nothing` 17） | 25/73（`nothing` 44） | 2/2 | 48/116 |
| `STANDUP` → `standing` | 30/30 | 29/29 | 50/74 | 25/36（`still_down` 11） | 40/119 |
| `WALK_ON` → `crossed` | 28/30（`walked` 2） | 27/32（`walked` 3） | 25/104（`nothing` 49） | 23/38（`nothing` 12） | 13/129 |

出所：各 `eval_*.json` の `actions` と `results` の組を数えたもの。再生成：

```
python analysis/skill_stats.py out/manager_runs/baselines_v4/eval_rule.json out/manager_runs/baselines_v4/eval_random.json
python analysis/skill_stats.py out/manager_runs/ppo2_v22_v4/eval_ppo.json out/manager_runs/tabq2_small_v4/eval_tabq.json out/manager_runs/ppo2_medium2_v4/eval_ppo.json
```

読み：押し上げは正しい状態で呼んでも 22/30（73%、評価 v4・固定ルール）で、残りは入口でのつまずきや坂の途中での停止＝スキルの精度の限界。固定ルールはその後を `BACK_OFF` → `SEAT` → `PUSH` のやり直しで埋めて天面到達 100% にしている。
PPO 中規模の `SEAT` 114 回のうち 96 回は転んだ相手に呼んで `still_down`、Q 表の `nothing` の多さは未訪問の状態で Q 値が同点になり手を無作為に選ぶ表形式の弱点で、どちらも渡り切りより無駄な手の列に出ている。

### 固定ルールとの同一シード 2×2

同じシードで固定ルールと比べ、失敗を「判断の失敗（ルールは渡った）」と「スキルの失敗（両方失敗）」に分ける。

| 方式 | 両方渡った | ルールだけ渡った | 方策だけ渡った | 両方失敗 |
|---|---|---|---|---|
| PPO v2.2 | 25 | 4 | 1 | 0 |
| Q 表 | 24 | 5 | 1 | 0 |
| PPO 中規模 | 22 | 7 | 1 | 0 |
| ランダム | 14 | 15 | 0 | 1 |

出所：`out/manager_runs/comparison_v4.md`「失敗の帰属」。各 `eval_*.json` の `seed` と `success` をシードごとに突き合わせて同じ値になることを確認した。再生成は総合表の `manager2_report.py` の行。

「方策だけ渡った」1 話は 3 方式ともシード 5021（固定ルール唯一の失敗）で、ランダムの「両方失敗」も 5021。同じシードでも手順が違えば物理の経路が変わるので、2×2 は帰属の第一近似であり、型の確定は次節の決定ログで行う。

### 失敗した押しの直後の手

押し（`PUSH`）が `stalled`・`slipped`・`fell` で終わった直後に何を選んだか。設計上の正解は、密着したままでは相手が起きられないので `BACK_OFF` で離れること。

| 方式 | 失敗した押し | 直後に `BACK_OFF` | 転倒（`fell`）直後に `BACK_OFF` | 転倒直後のその他 |
|---|---|---|---|---|
| 固定ルール | 8 | 8/8 | 5/5 | なし |
| PPO v2.2 | 12 | 9/12 | 8/8 | なし（停止後に `PUSH` 2、`STANDUP` 1） |
| Q 表 | 13 | 4/13 | 4/7 | `STANDUP` 1、`SEAT` 1、`WALK_ON` 1 |
| PPO 中規模 | 16 | 2/16 | 2/7 | `SEAT` 3、`STANDUP` 1、`PUSH` 1 |
| ランダム | 61 | 12/61 | 9/30 | `SEAT` 5、`WALK_ON` 5、`STANDUP` 4、`WAIT` 4、`PUSH` 1、話の終わり 2 |

出所：各 run の `eval_decisions.jsonl`（`baselines_v4` は 1 ファイルに 60 話が続き、`episode` 1〜30 が固定ルール、31〜60 がランダム。各 `eval_*.json` の `actions` と一致することを確認した）。
規則は `analysis/after_push_fail.py` と同じで、`PUSH` が `stalled`・`slipped`・`fell` で終わった行について、同じ話の次の行の `action` を数える。
同スクリプトの `eval` モードは評価 v2 の run を固定で読むため、評価 v4 の値は再計算スクリプトなしの集計である。
評価 v2 の同じ集計（`docs/devlog/MANAGER_DESIGN.md` §7.7）では、固定ルールが失敗した押し 13 回の直後すべてで `BACK_OFF`（13/13）、
PPO 中規模は失敗した押し 13 回のうち転倒 10 回の直後に限って `BACK_OFF` 3/10 だった。

### 失敗の型（シード名つき）

各方式の失敗した話を、決定ログ（`eval_*.json` の `actions`・`results`）で型に分けた。失敗はスキルの精度、判断の誤り、行動集合の不足のどれかとして書く。

固定ルール 1 話（5021、`toe_seated_wrong`）：`SEAT` → `PUSH` → `BACK_OFF` → `STANDUP` まで成功し、`WALK_ON` が `walked`（渡り切る前に下り坂側で転倒）で終わった。転んだ相手が自力で起きられず、固定ルールは密着していない転倒には `WAIT` しか持たないため 33 回待って時間切れ（242 s）。
これは判断の誤りではなく、行動集合に「離れた位置で転んだ相手を助ける手」がない設計の不足である。

PPO v2.2 4 話：3 話（5003・5011・5026）は固定ルールと同じ型で、`WALK_ON` の後に転倒し `WAIT`（5003 は 26 回、5026 は 35 回）や空振りの `BACK_OFF`（5011 は `nothing` 17 回）で時間切れ。
1 話（5029）は `PUSH` が `stalled`・`stalled` と続き、`BACK_OFF` を挟んだ 3 回目の `PUSH` が `fell` で終わり、離れた後は足元で転んだ相手を 43 回 `WAIT` した。
転んだ相手への `SEAT`／`STANDUP`（`still_down`）は 30 話を通じて 0 回で、報酬 v2.2 で塞いだ判断の穴は評価でも閉じている。代わりに `WAIT` が 122 回（すべて失敗 4 話の中）に集まった。

Q 表 5 話：4 話（5009・5015・5017・5024）は天面到達後や下り坂での転倒から起きられず、`WAIT`・`SEAT`・`WALK_ON`・`BACK_OFF` を繰り返して時間切れ（5009 は 102 手、`nothing` 92 回）。
1 話（5014、`toe_standing`・密着）は足元で `WALK_ON` と `PUSH` の空振りを繰り返した（`nothing` 23 回）。
`nothing` の多さは未訪問の状態で Q 値が同点になる表形式の弱点＝判断の誤りだが、渡り切りを落とした主因は転倒後の行動集合の不足で固定ルールと共通。

PPO 中規模 7 話：5 話（5000・5002・5011・5029・5018）は押しで転ばせた相手に密着したまま `SEAT` を連打して `still_down`（5000・5002・5011・5029 は 18〜24 回、5018 は 5 回のあと `PUSH` が `stalled` 5 回）。
残り 2 話（5003・5026）は `walked` の後に `STANDUP`／`SEAT`（`still_down`）と `WALK_ON`／`WAIT` の交互。

前者 5 話は判断の誤りである。手順が分かれる直前までは各手の時刻と所要時間が方式間で一致し（各 `eval_decisions.jsonl` の `t`・`duration_s`）、同じ状態から別の手を選んでいる。
固定ルールは同じシードで、押しが失敗した直後（5000・5002・5011 は `fell`、5029 は `stalled`）に `BACK_OFF` を選んで渡った（5018 は押しが 1 回で成功）。
5018 では PPO v2.2 が PPO 中規模と同じ転倒の直後に `BACK_OFF` を選んで渡った。
転んだ相手への `SEAT` 連打は報酬 v2.2 で消えた（PPO v2.2 の `still_down` 0 回）。ただし 5011・5029 は PPO v2.2 でも別の型（`walked` や `fell` の後の `WAIT`）で失敗する。

ランダム 16 話（5000・5002・5003・5011・5014・5015・5017・5018・5020・5021・5022・5024・5026・5027・5028・5029）：手を一様に選ぶため型はなく、1 話あたり `nothing` 6〜18 回、転倒 0〜6 回。
天面到達 73%（22/30）の内訳は、天面から始まる 7 話、一様に選んだ手の中で `PUSH` が `pushed_up` で終わった 14 話、押しの途中で天面に上がって転んだ 1 話（5003）である（`eval_random.json` の `landed`・`actions`・`results`）。

再生成（失敗した話の一覧）：`python analysis/failures.py out/manager_runs/<run>/eval_<policy>.json`。

## 学習コストと学習曲線

### 学習コスト

| 方式（run） | モデル | 学習量 | 実時間（CPU） | 学習中の成功率 | 出所 |
|---|---|---|---|---|---|
| Q 表（`tabq2_small`） | 状態キー 7 要素、学習後 314 状態 | 120 話、ε 0.3→0.05 | 1 h 59 min（7,166 s） | 0.725 | `tabq2_small/train.log` 末尾、`tabq.json` |
| PPO 小規模（`ppo2_small`） | MLP [64,64]、12 並列、rollout 24 | 3,000 決定、118 話 | 54 min（3,216 s） | 0.381 | `ppo2_small/train_summary.json` |
| PPO 中規模（`ppo2_medium2`） | MLP [64,64]、12 並列、rollout 48 | 12,000 決定、792 話 | 4 h 13 min（15,154 s） | 0.677 | `ppo2_medium2/train_summary.json` |
| PPO v2.2（`ppo2_v22`） | PPO 中規模から継続、報酬 v2.2、`ramp_fallen` 0.20 | +12,000 決定、766 話 | 4 h 28 min（16,105 s） | 0.658 | `ppo2_v22/train_summary.json` |
| 継続学習（`ppo2_medium3`、中断） | PPO 中規模から継続、報酬 v2.1、転倒側の開始分布 | +7,536 決定（12,108→19,644）、740 話 | 3 h 1 min（10,876 s） | 0.790（585/740） | `ppo2_medium3/train_curve.json` |

run はすべて `out/manager_runs/` 以下。PPO の設定は `manager2_train.py`（lr 3e-4、γ 0.99、GAE 0.95、6 epoch、clip 0.2、ent_coef 0.02）、Q 表は `manager2_tabq.py`（α 0.2、γ 0.95）。学習中の成功率は探索込み（PPO は方策の分布から手を引く、Q 表は ε-greedy）。
PPO v2.2 の累計は 15,154 + 16,105 = 31,259 s（8 h 41 min）。`ppo2_medium3` は重みを保存する前に止めたので評価には使っていない（学習記録のみ）。固定ルールとランダムに学習コストはない。

再生成（学習。シードは学習記録に残っていないため `docs/reproduce.md` の値）：

```
python manager2_tabq.py train --episodes 120 --run tabq2_small
python manager2_train.py train --envs 12 --steps 12000 --rollout 48 --seed 1 --run ppo2_medium2
python manager2_train.py train --envs 12 --steps 12000 --rollout 48 --seed 3 --run ppo2_v22 --init-from ppo2_medium2 --reward v2.2 --scenario-weights <A> --crab-toe-weights <B>
```

`<A>` は `toe_seated_ok=0.20,toe_seated_wrong=0.15,toe_standing=0.15,toe_fallen=0.10,deck_seated=0.15,deck_fallen=0.05,ramp_fallen=0.20`、
`<B>` は `behind=0.5,beside=0.2,touching=0.3`（引用符で囲んで 1 引数にする）。

開始分布の重みは `ppo2_v22/train_summary.json` の `draw_tables` と一致する。

### 学習曲線の要約（学習中の渡り切り、5 分位）

| run | 第 1 分位 | 第 2 分位 | 第 3 分位 | 第 4 分位 | 第 5 分位 |
|---|---|---|---|---|---|
| Q 表 `tabq2_small`（24 話ごと） | 12/24 | 17/24 | 19/24 | 19/24 | 20/24 |
| PPO 小規模 `ppo2_small`（23 話ごと） | 7/23 | 11/23 | 8/23 | 9/23 | 10/26 |
| PPO 中規模 `ppo2_medium2`（158 話ごと） | 81/158 | 92/158 | 119/158 | 115/158 | 129/160 |
| PPO v2.2 `ppo2_v22`（153 話ごと） | 107/153 | 90/153 | 97/153 | 120/153 | 90/154 |
| 継続学習 `ppo2_medium3`（148 話ごと） | 119/148 | 116/148 | 115/148 | 112/148 | 123/148 |

出所：各 run の `train_curve.json`（1 話 1 行、`success`）。再生成：`python analysis/curve.py out/manager_runs/<run>/train_curve.json`。

読み：PPO 小規模は 3,000 決定では上昇が見えず（7/23 → 10/26）、評価 v2 では 0/30 だった（付録 B）。PPO 中規模は 4 倍の予算（rollout も 24→48）で 51% → 81% に上がった。
PPO v2.2 の曲線が平らに見えるのは、開始分布に `ramp_fallen`（坂の途中で転倒、0.20）と密着 0.3 を入れた難しい分布で学習したためと考える。PPO 中規模の曲線と直接は比べられない。学習中の値は探索込みなので、方式の比較は評価 v4（決定的方策）で行う。

## 提出動画の手と時刻

### 本編と比較用の動画の対応

提出動画（2:56.6）は講座の OP カード、自己紹介（15.1 s）、本編、講座の ED カードをつないだもので、本編は提出動画の 0:18.1（18.14 s）から始まる（`docs/video_guide.md` 第 1 節）。
本編の支配人は PPO v2.2（`ppo2_v22`）である。提出動画の支配人は学習した AI とし、評価 v4 で最良の固定ルールは、本編と同じ設定で描いた固定ルール版で示す。
本編と固定ルール版は施工を 4 倍速で省略なしに描き、以後 2 倍速、仲間を呼んで戻る区間と輪へ集まる区間は 4 倍速、ゴールの万歳は等速。画面右下に sim 時計と x4／x2／x1 を常時表示する。
以前の速度設定の比較用の動画（以前の 2:47 版を含む 4 本）は、施工 4 倍速・以後 2 倍速・万歳は等速の設定で描いた。
現在の実装では `--build-speed` と `--speedup` は 2 倍速で標本化したフレームを間引いて書き出すだけで、標本周期は変えない（`v7_full.py` の `SPEED` 直上の注記）。
このため最終状態のダイジェスト（qpos＋qvel の sha256、`state_digest`）は省略の有無と書き出しの倍速によらず一致し、下の表の「物理」列がその確認である。
顔と気分ネットの有無でダイジェストと支配人の判断が変わらないことは `analysis/face_check.py` で確かめた（`docs/mood_net_and_faces.md`）。施工 4 倍速の初版は標本周期そのものを変えたため、物理の経路が変わった（表の下）。

| 条件名 | ファイル（`out/`） | 支配人 | 手数 | 長さ | 物理（`state_digest` 先頭 8 桁） |
|---|---|---|---|---|---|
| 本編（提出、PPO・輪の万歳） | `3body_arena_v7_take58.mp4` | PPO v2.2（`ppo2_v22`） | 4 | 2:35.5 | `aafa49e7`、PPO 版と同じ |
| 固定ルール版（比較用、本編と同じ設定） | `3body_arena_v7_take57.mp4` | 固定ルール | 5 | 2:37.3 | `678fd3ca`、以前の 2:47 版と同じ |
| 以前の 2:47 版（固定ルール・輪の万歳） | `3body_arena_v7_take51.mp4` | 固定ルール | 5 | 2:47.0 | `678fd3ca`、省略版 `v7_full_report_take46.json` と同じ |
| PPO 版 | `3body_arena_v7_take52.mp4` | PPO v2.2（`ppo2_v22`） | 4 | 2:45.2 | `aafa49e7`、省略版 `v7_full_report_take47.json` と同じ |
| Q 表版 | `3body_arena_v7_take53.mp4` | Q 表（`tabq2_small`） | 8 | 2:46.3 | `f53de6e4`、省略版 `v7_full_report_take48.json` と同じ |
| 追走版（固定ルール・追走の結末） | `3body_arena_v7_take54.mp4` | 固定ルール | 5 | 2:43.7 | `be8fb01e`、省略版 `v7_full_report_take49.json` と同じ |

6 本とも 3 体が渡り切り（`three_crossed` が bz・crab・duck すべて true）、コースの部品の移動なし（`course_disturbed` が空）、MuJoCo 3.11.0（`mujoco`）。
長さは各 report JSON の音声なしの `video_silent.seconds`（フレーム数÷30：155.5、157.3、167.0、165.2、166.3、163.7 s）。音声付き MP4 は ffmpeg の Duration で本編 2:35.47、固定ルール版 2:37.30 だった。
シミュレーションの全長は `sim_seconds`（400.6、404.2、404.2、400.6、402.9、397.7 s）で、省略版と同じ値である。本編と固定ルール版は END の後に回す 2.5 s のうち 1 s だけを書き出すので（`settings.tail_write_s`）、
動画の長さはそれぞれ PPO 版・2:47 版より 9.7 s 短いが、`sim_seconds` は同じである。

省略版（`out/3body_arena_v7_take46〜49.mp4`、2 倍速＋省略 2 か所、2:44.1／2:42.3／2:43.5／2:40.8）は記録として残す。
施工 4 倍速の初版（`out/v7_full_report_take50.json`、2:40.2）は描画の標本周期が変わったことで物理の経路が変わり（`state_digest` が `768e78f7` で異なる）、
同じ 5 手で 3 体渡り切りだが提出には使わない。

出所：`out/v7_full_report_take58.json`・`take57.json` と `take51.json`〜`take54.json`（`manager.policy`、`manager.decisions`、`state_digest`、`three_crossed`、`course_disturbed`、`video_silent`、`sim_seconds`、`mujoco`）
と `out/v7_full_report_take46.json`〜`take49.json` の `state_digest`。

再生成（約 8 分／本。`--ending crab`、`--manager rule`、`--finale circle` は既定値。Q 表版の `--jitter 0.4` は省略版の記録から）：

```
python v7_full.py --manager ppo --run ppo2_v22 --tag _take58 --build-speed 4 --no-cuts --speedup CALL=4 --speedup RETURN=4 --speedup CELEBRATE=4 --tail-write 1.0
python v7_full.py --tag _take57 --build-speed 4 --no-cuts --speedup CALL=4 --speedup RETURN=4 --speedup CELEBRATE=4 --tail-write 1.0
python v7_full.py --tag _take51 --build-speed 4 --no-cuts
python v7_full.py --manager ppo --run ppo2_v22 --tag _take52 --build-speed 4 --no-cuts
python v7_full.py --manager tabq --run tabq2_small --jitter 0.4 --tag _take53 --build-speed 4 --no-cuts
python v7_full.py --finale procession --tag _take54 --build-speed 4 --no-cuts
```

### 速度区間（動画時刻）

| 条件名 | ×4 | ×2 | ×1 | 全長 |
|---|---|---|---|---|
| 本編（提出） | 0:00〜0:44.1（sim 0〜176.4 s）、1:20.4〜1:24.3（sim 248.9〜264.6 s）、2:14.8〜2:19.1（sim 365.6〜382.7 s） | 0:44.1〜1:20.4（sim 176.4〜248.9 s）、1:24.3〜2:14.8（sim 264.6〜365.6 s） | 2:19.1〜2:35.5（sim 382.7 s〜、END の後は 1 s だけ） | 2:35.5 |
| 固定ルール版 | 0:00〜0:44.1（sim 0〜176.4 s）、1:20.4〜1:24.3（sim 248.9〜264.6 s）、2:16.7〜2:20.9（sim 369.4〜386.3 s） | 0:44.1〜1:20.4（sim 176.4〜248.9 s）、1:24.3〜2:16.7（sim 264.6〜369.4 s） | 2:20.9〜2:37.3（sim 386.3 s〜、END の後は 1 s だけ） | 2:37.3 |
| 以前の 2:47 版 | 0:00〜0:44.1（sim 0〜176.4 s） | 0:44.1〜2:29.1（sim 176.4〜386.3 s） | 2:29.1〜2:47.0（sim 386.3〜404.2 s） | 2:47.0 |
| PPO 版 | 0:00〜0:44.1（sim 0〜176.4 s） | 0:44.1〜2:27.3（sim 176.4〜382.7 s） | 2:27.3〜2:45.2（sim 382.7〜400.6 s） | 2:45.2 |
| Q 表版 | 0:00〜0:44.1（sim 0〜176.4 s） | 0:44.1〜2:28.4（sim 176.4〜385.0 s） | 2:28.4〜2:46.3（sim 385.0〜402.9 s） | 2:46.3 |
| 追走版 | 0:00〜0:44.1（sim 0〜176.4 s） | 0:44.1〜2:25.8（sim 176.4〜379.8 s） | 2:25.8〜2:43.7（sim 379.8〜397.7 s） | 2:43.7 |

×1 の開始はゴールの万歳が始まる出来事（`events` の「the circle」または「the three cheer」）。施工の段階 `BUILD`（sim 0〜176.4 s）の ×4 は 6 本とも同じ。
×1 の終わりは動画の末尾（`video_silent.seconds`）で、最後の出来事 `stage -> END` は以前の速度設定の 4 本ではその 2.5 s 前、本編と固定ルール版では 1 s 前にある
（本編 2:34.4／sim 398.1 s、固定ルール版 2:36.3／sim 401.7 s、以前の 2:47 版 2:44.5／sim 401.7 s、PPO 版 2:42.6／sim 398.1 s、Q 表版 2:43.8／sim 400.4 s、追走版 2:41.2／sim 395.2 s）。末尾も ×1 で描かれる。

出所：各 report JSON の `events` の `t` と `video_t` から `analysis/timeline_times.py` が区間を推定したもの（同スクリプトは ×1 の区間を最後の出来事までとして出す）。
再生成：`python analysis/timeline_times.py out/v7_full_report_take58.json`（表情ログも動画時刻で出る）。

### 本編の主な出来事（提出動画｜本編｜sim 秒）

提出動画の時刻は本編の時刻に 18.14 s（講座の OP カード 3.04 s＋自己紹介 15.1 s）を足した値。

| 出来事 | 提出動画 | 本編 | sim 秒 | 動いているもの | 制御 |
|---|---|---|---|---|---|
| 施工完了、ブルドーザーが 4 面を走破して渡り切り | 1:12.1 | 0:54.0 | 196.1 | ブルドーザー | 自作ルール制御（course-builder） |
| パッカンが座り込む（2 回目の挑戦のあと） | 1:26.4 | 1:08.2 | 224.6 | パッカン | 公式 `velstand`・`alpha_sitstand`（推論） |
| 跳跳が峠で前方ジャンプ | 1:33.6 | 1:15.4 | 239.0 | 跳跳 | 公式 `jump`（推論）＋関節目標の重ね合わせ |
| 跳跳が渡り切り | 1:37.0 | 1:18.9 | 245.9 | 跳跳 | 公式 `locomotion`（推論） |
| 支配人 AI が引き継ぐ（1 手目 `SEAT`） | 1:42.4 | 1:24.3 | 264.6 | 支配人 AI | 自作、PPO v2.2（学習済み） |
| `PUSH` 開始 | 1:48.4 | 1:30.2 | 276.5 | 跳跳 | 公式 `locomotion`（推論）、支配人の手 |
| `STANDUP`、`WALK_ON` | 2:24.0、2:26.8 | 2:05.9、2:08.7 | 347.9、353.4 | パッカン | 支配人の手 |
| パッカンが渡り切り、3 体そろう | 2:32.9 | 2:14.8 | 365.6 | パッカン | 公式 `velstand`（推論） |
| 輪の万歳が始まる（以後 ×1） | 2:37.2 | 2:19.1 | 382.7 | 3 体 | 公式 `dance_crab`（推論）ほか |
| 終了 | 2:52.6 | 2:34.4 | 398.1 | — | — |

出所：`out/v7_full_report_take58.json` の `events`（`video_t`、`t`）。sim 秒は以前の速度設定の PPO 版（`out/v7_full_report_take52.json`）と全行で同じで、
PPO 版の動画時刻は跳跳の渡り切りまで本編と同じ、支配人の引き継ぎは 1:28.2、輪の万歳は 2:27.3、終了は 2:42.6 である。
固定ルール版（`out/v7_full_report_take57.json`）は支配人の 2 手目までと sim 時刻が本編と同じで、その後は `BACK_OFF` 2:05.9、`STANDUP` 2:06.8、`WALK_ON` 2:09.6、
渡り切り 2:16.7（sim 369.4 s）、輪の万歳 2:20.9（sim 386.3 s）、終了 2:36.3（sim 401.7 s）（固定ルール版の動画時刻。sim 秒は以前の 2:47 版と全行で同じ）。
以前の 2:47 版・追走版は施工から引き継ぎまで PPO 版と同じ時刻である。
Q 表版は `--jitter 0.4`（跳跳の応援ダンスの開始点を 0.4 s ずらす設定、`v7_full.py` の `CHEER_DANCE_START`）のため、跳跳のジャンプ以降の出来事が sim で 0.1 s 未満ずれる（ジャンプ 1:15.5／sim 239.1 s、渡り切り sim 246.0 s）。
支配人の引き継ぎは比較用の 4 本とも 1:28.2（sim 264.6 s）。
渡り切り・万歳・終了は次の表の下に記す。制御の列は `docs/physics_integration.md` §1（構成の全体）の「動かしているもの」に対応する。

再生成：`python analysis/timeline_times.py out/v7_full_report_take58.json`。`--compare out/v7_full_report_take52.json` を足すと、
PPO 版との出来事ごとの動画時刻のずれと `state_digest` の一致も出る（固定ルール版と 2:47 版の組は `take57.json --compare take51.json`、2:47 版と省略版の組は `take51.json --compare take46.json`）。

### 支配人 AI の手（本編と比較用の 4 本）

本編（PPO v2.2、`out/v7_full_report_take58.json` の `manager.decisions`）：

| 手 | 提出動画 | 本編 | sim 秒 | 所要 s | 結果 |
|---|---|---|---|---|---|
| 1 `SEAT` | 1:42.4 | 1:24.3 | 264.6 | 11.9 | `seated` |
| 2 `PUSH` | 1:48.4 | 1:30.2 | 276.5 | 71.3 | `pushed_up` |
| 3 `STANDUP` | 2:24.0 | 2:05.9 | 347.9 | 5.5 | `standing` |
| 4 `WALK_ON` | 2:26.8 | 2:08.7 | 353.4 | 12.2 | `crossed` |

4 手すべて成功、転倒 0、パッカンの渡り切り 2:32.9（本編 2:14.8、sim 365.6 s）、万歳 2:37.2（本編 2:19.1、sim 382.7 s）、終了 2:52.6（本編 2:34.4、sim 398.1 s）。押し上げは動画で約 36 秒（2 倍速）。
固定ルールが押し上げの後に挟む `BACK_OFF` を省き、跳跳が 0.25 m 後ろに残ったまま（`touching` false）立たせた。
手・sim 時刻・所要・結果は以前の速度設定の PPO 版と同じで、PPO 版の動画時刻は下の表のとおり。

固定ルール版（本編と同じ設定、`out/v7_full_report_take57.json`）：

| 手 | 動画時刻 | sim 秒 | 所要 s | 結果 |
|---|---|---|---|---|
| 1 `SEAT` | 1:24.3 | 264.6 | 11.9 | `seated` |
| 2 `PUSH` | 1:30.2 | 276.5 | 71.3 | `pushed_up` |
| 3 `BACK_OFF` | 2:05.9 | 347.9 | 1.7 | `cleared` |
| 4 `STANDUP` | 2:06.8 | 349.6 | 5.5 | `standing` |
| 5 `WALK_ON` | 2:09.6 | 355.2 | 14.2 | `crossed` |

5 手すべて成功、転倒 0、パッカンの渡り切り 2:16.7（sim 369.4 s）、万歳 2:20.9（sim 386.3 s）、終了 2:36.3（sim 401.7 s）。
手・sim 時刻・所要・結果は以前の 2:47 版と同じで、2:47 版の動画時刻は `SEAT` 1:28.2、`PUSH` 1:34.2、`BACK_OFF` 2:09.8、`STANDUP` 2:10.7、`WALK_ON` 2:13.5。

PPO 版（PPO v2.2、`out/v7_full_report_take52.json`、本編と物理が同一）：

| 手 | 動画時刻 | sim 秒 | 所要 s | 結果 |
|---|---|---|---|---|
| 1 `SEAT` | 1:28.2 | 264.6 | 11.9 | `seated` |
| 2 `PUSH` | 1:34.2 | 276.5 | 71.3 | `pushed_up` |
| 3 `STANDUP` | 2:09.8 | 347.9 | 5.5 | `standing` |
| 4 `WALK_ON` | 2:12.6 | 353.4 | 12.2 | `crossed` |

`BACK_OFF` を省いて 4 手。渡り切り 2:18.7（sim 365.6 s）、万歳 2:27.3（sim 382.7 s）、終了 2:42.6（sim 398.1 s）。学習した方策が固定ルールより 1 手短い手順を選んだ例で、本編も同じ手順である。
評価 v4 のシード 5026（`toe_standing`）では同じ 4 手の並びの `WALK_ON` が `walked`（渡り切る前に転倒）で終わり、固定ルールは同じシードで `BACK_OFF` を挟んで渡った（失敗の型の節）。

Q 表版（`out/v7_full_report_take53.json`）：

| 手 | 動画時刻 | sim 秒 | 所要 s | 結果 |
|---|---|---|---|---|
| 1 `STANDUP` | 1:28.2 | 264.6 | 5.5 | `standing` |
| 2 `WALK_ON` | 1:31.0 | 270.2 | 11.0 | `stalled` |
| 3 `SEAT` | 1:36.5 | 281.2 | 7.4 | `seated` |
| 4 `PUSH` | 1:40.2 | 288.6 | 59.0 | `pushed_up` |
| 5 `BACK_OFF` | 2:09.8 | 347.7 | 1.7 | `cleared` |
| 6 `STANDUP` | 2:10.6 | 349.4 | 5.5 | `standing` |
| 7 `STANDUP` | 2:13.4 | 355.0 | 1.0 | `nothing` |
| 8 `WALK_ON` | 2:13.9 | 356.0 | 13.5 | `crossed` |

8 手、無駄な手 1（7 手目）。最初の 2 手は学習した Q 値どおりである。座り込んだ直後の状態（`tabq.json` のキー `none|SIT|toe|f0|s1|c0|n0`）では `STANDUP` の 0.87 が最大で、
立った後（`standing|STAND|toe|f0|s1|c0|n0`）は `WALK_ON` の 2.00 が最大。歩かせて `stalled` を見た状態では `SEAT` の 3.31 が最大になり、以後は固定ルールと同じ手順に合流した。
7 手目の `STANDUP`（`nothing`）も、天面で立った状態（`standing|STAND|deck|f0|s0|c0|n1`）で `STANDUP` 5.98 が `WALK_ON` 2.64 を上回るという学習した値の偏りで、
評価 v4 の `STANDUP` → `nothing` 16 回と同じ型である。120 話の学習では状態ごとの値がまだ安定していないためと考える（出所：`out/manager_runs/tabq2_small/tabq.json`）。
渡り切り 2:20.7（sim 369.5 s）、万歳 2:28.4（sim 385.0 s）、終了 2:43.8（sim 400.4 s）。

追走版（固定ルール、`out/v7_full_report_take54.json`）：手と時刻は以前の 2:47 版と同じ 5 手（`SEAT` 1:28.2、`PUSH` 1:34.2、`BACK_OFF` 2:09.8、`STANDUP` 2:10.7、`WALK_ON` 2:13.5）。
渡り切り 2:20.6（sim 369.4 s）のあと跳跳がパッカンを追って下り（`v7_full.py` の `--finale procession`）、ゴールで三人の万歳 2:25.8（sim 379.8 s）、終了 2:41.2（sim 395.2 s）。
ブルドーザーの位置取りは `WALK_ON` の開始（sim 355.2 s）から輪の結末の版と分かれ、最終状態のダイジェストも異なる。それでもパッカンの渡り切りまでの支配人の手と sim 時刻は固定ルール版と同じである。

気分ネット（跳跳の表情を推論する自作 AI）の本番推論回数は本編 5,050（PPO 版も同じ）、固定ルール版 5,236（以前の 2:47 版も同じ）、Q 表版 5,239、追走版 5,236（各 report JSON の `face.mood_ai.inferences`）。
表情ログは `face.log`（本編 26 行、固定ルール版 26 行、以前の 2:47 版 26 行、PPO 版 26 行、Q 表版 27 行、追走版 26 行）で、動画時刻への対応は `analysis/timeline_times.py` が出す。

出所：各 report JSON の `manager.decisions`（`action`、`t`、`video_t`、`duration_s`、`result`）と `events`。
再生成（どの版も同じ形）：`python analysis/timeline_times.py out/v7_full_report_take52.json` のように report JSON を指定する。

## 付録 A：旧コース（継ぎ目 5 cm）の評価 v3／v3b

評価 v3 は、エピソードを独立させた最初の評価で、コースは旧設計（峠の 2 枚の継ぎ目の設計値 5 cm、`INSTALLATION_GAP = 0.05`）。v3b は v3 と同じ条件に PPO v2.2 の行を足したもので、他の 4 行は v3 と同じ値である。

| 方式（run） | 渡り切り | 天面到達 | 無駄な手/話 | 転倒/話 | 2×2（両方／ルールだけ／方策だけ／両方失敗） |
|---|---|---|---|---|---|
| 固定ルール（`baselines_v3`） | 23/30（77%） | 97% | 0.00 | 0.60 | — |
| Q 表（`tabq2_small_v3`） | 24/30（80%） | 90% | 2.60 | 0.67 | 19／4／5／2 |
| PPO 中規模（`ppo2_medium2_v3`） | 16/30（53%） | 83% | 0.67 | 0.90 | 13／10／3／4 |
| PPO v2.2（`ppo2_v22_v3`） | 16/30（53%） | 90% | 14.90 | 1.00 | 13／10／3／4 |
| ランダム（`baselines_v3`） | 9/30（30%） | 70% | 9.73 | 1.33 | 8／15／1／6（コース破損 2） |

出所：`out/manager_runs/comparison_v3b.md`（`comparison_v3.md` は PPO v2.2 の行がない同内容）、各 `*_v3/eval_summary.json`。
再生成は舞台 XML を旧コース（`out/v6_stage_built_gap5cm.xml`）に差し替える必要があり、`manager2_env.py` は `out/v6_stage_built.xml`（`STAGE_XML`）を固定で読むため、
手順としては提供しない（記録のみ）。

何が違ったか：継ぎ目の幅はレイキャストで 4.0〜4.5 cm あり（`docs/devlog/MANAGER_DESIGN.md` §7.12・§7.14 の計測、再計算スクリプトなし）、
パッカンが天面を歩くと継ぎ目でつまずいて転倒し、どの支配人にも転んだ相手を助ける手がなかった。
固定ルールの失敗 7 話はすべて転倒後に `WAIT` だけで時間切れになる型で、5 話は `WALK_ON` が `walked`（5003・5006・5009・5015・5025）、
1 話は押し上げ中の `fell`（5008）、1 話は天面で `WALK_ON` が `stalled` のあと転倒（5023）。`WAIT` が 470 手中 327 手を占める（`baselines_v3/eval_rule.json`）。
PPO v2.2 は押しが効かないと `BACK_OFF` → `PUSH` を繰り返し（`BACK_OFF` 465 回、5026 で 145 回、5027 で 140 回）、無駄な手 14.90/話になった。「両方失敗」が 2〜6 話あるのは、スキルの失敗がコースの不備で起きていたことを示す。

なぜ提出の数値にしないか：継ぎ目は置き誤差ではなく course-builder の設計値だったので、設計値を 1 cm に直した（commit ea5b4e7、新コース）。提出動画は新コースで描いており、旧コースの評価は存在しない環境の成績である。
修正の効果は評価 v4 との差に出る：固定ルール 23 → 29、Q 表 24 → 25、PPO 中規模 16 → 23、PPO v2.2 16 → 26、ランダム 9 → 14、両方失敗 2〜6 → 0。環境の不備は PPO の 2 方式にいちばん厳しく出ていた（PPO v2.2 +10 話、PPO 中規模 +7 話。固定ルール +6、ランダム +5、Q 表 +1）。

## 付録 B：評価 v2（エピソード非独立）

評価 v2 は旧コースで、エピソードの独立性を確かめる前に行った最初の 30 シード評価である。

| 方式（run） | 渡り切り | 天面到達 | 無駄な手/話 | 転倒/話 | 2×2（両方／ルールだけ／方策だけ／両方失敗） |
|---|---|---|---|---|---|
| 固定ルール（`baselines_v2`、`near_lip` なし） | 25/30（83%） | 97% | 0.13 | 0.80 | — |
| Q 表（`tabq2_small`） | 23/30（77%） | 93% | 13.97 | 0.83 | 20／5／3／2 |
| PPO 中規模（`ppo2_medium2`） | 19/30（63%） | 77% | 9.97 | 1.13 | 17／8／2／3 |
| PPO 小規模（`ppo2_small`） | 0/30（0%） | 27% | 61.90 | 0.00 | 0／25／0／5 |
| ランダム（`baselines_v2`） | 9/30（30%） | 80% | 8.40 | 1.33 | 8／17／1／4（コース破損 1） |

出所：`out/manager_runs/comparison_v2.md`、各 run の `eval_summary.json`。PPO 小規模は 30 話すべてで `WALK_ON` に固着（2,375 回）し、`SEAT` と `PUSH` を 1 回ずつしか選ばなかった。

何が違ったか：(1) `Scene.reset()` が `mj_resetData` を呼んでおらず、ソルバーの状態が前の話から持ち越されたため、同じシードでも `PUSH` の所要時間が走らせるたびに変わった（修正後は一致。`docs/devlog/MANAGER_DESIGN.md` §7.10、再計算スクリプトなし）。
(2) 報酬が混在し、`ppo2_small` と `baselines_v2` は v2.0（`stalled`／`slipped` の −1 なし）、Q 表と PPO 中規模は v2.1 で、平均リターンは比較できない（`manager2_env.py` の `REWARD` 直下の注記）。
(3) 固定ルールに `near_lip` の押し条件（`crab_help.py` の `RULE_NEAR_LIP`）がまだなく、v3 以降のルールと同一ではない。

なぜ無効か：話が独立していないので、1 話を単独で再現できず、順序を変えると結果が変わる。
同じルール・同じ環境で取り直した `baselines_v21check` は 30 話とも手順が一致して 25/30 を再現したが、`near_lip` を足した `baselines_v22`（26/30）では 12 シードで手順が変わり、
この持ち越しが見つかった（各 run の `eval_summary.json` の `crossing_rate` 0.833 と 0.867、`docs/devlog/MANAGER_DESIGN.md` §7.9〜7.10）。
評価は v3 から `mj_resetData` 入りで取り直し、提出の数値は v4 だけを使う。v2 の結果は、評価の独立性を最初に確かめなかった反省の根拠として残す（`docs/insights.md`）。

再生成：現在のコードはエピソードを独立させるので v2 の値は再現できない。`--rule-near-lip off` を付けると v2 当時の固定ルールで評価できる：

```
python manager2_train.py eval --run baselines_v2 --policies rule random --episodes 30 --seed0 5000 --rule-near-lip off --out <別名>
```
