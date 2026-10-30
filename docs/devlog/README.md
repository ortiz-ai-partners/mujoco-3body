# 開発記録（devlog）の索引

このディレクトリは、本リポジトリの開発中に書かれた記録を原文のまま保存する場所である。
読者向けの説明（作品の概要、設計、結果、再現手順）はリポジトリ直下の `README.md` と `docs/` にあり、
ここにある文書は「どういう経緯でその設計と数値に至ったか」を確かめるための一次資料に当たる。

## 位置づけと読むときの約束

- 原文は書き換えていない。各文書の冒頭に足した注記 3 行（と空行 1 行）と、下に書くローカルの絶対パスの置き換えだけが後からの変更で、本文の誤記もそのまま残っている。誤記と現物の値の対応は本書の「訂正表」にまとめた。
- 例外は 1 行だけ：`face_rules_chart.md` L86 の図のリンクは、ファイルを `report/` から移したときに参照先を `../../report/face_rules_chart_ortiz.png` に直し、代替文のハンドル名を外した。
- `takes.md` と `code_comment_quotes.md` は原文の保存ではなく、本リポジトリのために新たに書いた文書である（前者は各 take の報告 JSON からの再集計、後者はコードから外した原文の転記）。
- 日付と take 番号を本文に書く文書は `docs/devlog/` の中（本書、この 2 つ、原文）に限る。読者向け文書（`README.md`、`docs/`）では版を条件名で呼ぶ。
- 原文に出てくる呼び名は開発チーム内のハンドル名である。役割は 4 つ：要件と判断を出した企画者（本リポジトリの作者）、コードと文書を書いた開発補助 AI（LLM）、図版の清書を手伝った別の AI、
  隣のリポジトリ physical-ai-course-builder 側の開発補助 AI（`HANDOVER.md` L110 の申し送り先）。読者向け文書ではこれらを「要件：」「設計判断：」「本プロジェクトで作成」という役割語に置き換えた。
- 「アイランドマスター」は開発補助 AI（LLM）の呼び名で、動画の支配人 AI が自己紹介と字幕で名乗るキャラクター名はここから取った（作品名ではない）。原文の「アイランドマスター追記」は開発補助 AI による追記の意味で、動画の中で次の一手を選ぶ主体は常に「支配人 AI」である。
- コミット ID：公開リポジトリ 2 本の履歴の作者アドレスを GitHub の noreply アドレスに置き換えたとき、すべてのコミット ID が変わった（中身・日付・メッセージは同じ）。原文（HANDOVER.md、MANAGER_DESIGN.md）の ID は置き換え前のもので、course-builder の ea5b4e7 は 483dbf9、本リポジトリの e3a40dd は 94e273b、13124be は 3dabe92、1b7c1fe は 69427a9、0a9322f は 4b15858 にあたる。
- 日付・時刻・take 番号・未決の事項は作業時点のものである。提出動画の本編は take 58（`out/3body_arena_v7_take58.mp4`、PPO の支配人、物理は take 52 と同一）で、同じ設定の固定ルール版 take 57（物理は take 51 と同一）は比較用に残す。原文の多くは take 46 以前や take 51 を「提出版」と呼んでいる（訂正表 6・7）。
- 原文中のローカルの絶対パスは、公開にあたり先頭の作業フォルダ（ドライブ名から始まる部分）を `<BASE>`（`v6_common.py` の `BASE`＝隣接リポジトリを並べた親ディレクトリ）に置き換えた。`out/` の報告 JSON とログの中のパスも同じように置き換えた（置き換えたのはその部分だけ）。開発中の仮想環境名、開発中の外部の記録ページへのリンクは公開リポジトリの外を指しており、読者は辿れない。再現はリポジトリ直下で `python …` と相対パスで行う（`docs/reproduce.md`）。
- 個人の実名・所属・個人メールアドレスは原文にも載せていない（メールアドレスは GitHub の noreply のみ、`report_outline.md` L22）。

## 各文書の性格と読む順

| 文書 | 行数 | 性格 | 読む順の要点 |
|---|---|---|---|
| `README_development.md` | 102 | 旧 README の写し。開発中の作業台帳 | 最初に全体像をつかむ。見出しと数値の一部が旧値（訂正表 1・2・3・5） |
| `takes.md` | — | take 台帳（新規）。take 4〜58 の設定・結果・物理同一の系譜・採否・所在 | 版と take 番号の対応はここで引く。日付と take 番号を本文に書く新規文書 |
| `HANDOVER.md` | 304 | 次の作業者への引継ぎ文書。終盤 2 日間の決定・実験・take 毎の成否 | 上が新しい逆時刻順：§0b → §0 → §1〜9 |
| `MANAGER_DESIGN.md` | 579 | 支配人 AI の設計メモ v1〜v1.4。実験の事実と決定を含む原本 | 節番号は 0,1,2,3,6,4,5,4.5,7 の順で並ぶ。採用設計は §7 |
| `report_outline.md` | 106 | 提出レポート PDF の構成案（案 3） | 読者向け文書の章立ての元 |
| `face_rules_chart.md` | 120 | 表情 17 規則の Mermaid 図 2 枚としきい値表＋図 7 枚の作成経緯 | 図と表は読者向けに写し済み。経緯は本書「図の経緯」で要約 |
| `timeline_brief_take51.md` | 42 | タイムライン図を take 51 の時刻で作り直すための依頼文 | 時刻の出所は `out/v7_full_report_take51.json` |
| `code_comment_quotes.md` | — | コードの help・docstring・コメントの置換記録。置換前の原文（チャット引用・決定ログの括弧標識・ハンドル名）をファイルごとに転記 | 置換の方針（規則の表）→ 置換しなかったもの → 検証 → ファイルごとの表（直下・`analysis/`・`archive/`） |
| `figures/` | 2 枚 | 差し替え済みの旧図と元データ | 報告書には載せない |

行数は注記 3 行と空行を足した現在のファイルのもの（`timeline_brief_take51.md`、`takes.md`、`code_comment_quotes.md` には注記を足していない）。
以下の各節で引く行番号も現在のファイルに合わせてある。新規の `takes.md` と `code_comment_quotes.md` は追記で行がずれるため行数を載せず、節名で引く。
コードも書き直しで行がずれるため、行番号ではなく定数名・関数名で引く。

推奨する読む順は次のとおり。

1. `README_development.md`：作品の全体像、支配人 AI の 3 方式と評価表、動かし方。
2. `takes.md`：どの take がどの版か、物理が同一の系譜、失敗版の意味、提出版の時間軸。
3. `HANDOVER.md` §0b → §0 → §1〜9：終盤の決定と実験、物理のみ版の現状、初期の構成。
4. `MANAGER_DESIGN.md` §7（7.1 → 7.2 → 7.6 → 7.7 → 7.8 → 7.10 → 7.14 → 7.15 → 7.16〜7.18）→ §6 → §0〜5。
5. `report_outline.md`：レポート PDF の骨子と提出手順の点検。
6. `face_rules_chart.md`、`timeline_brief_take51.md`、`figures/`：図の原本と経緯。
7. `code_comment_quotes.md`：コードから外した原文。読者向けの help・docstring との対応を確かめるときだけ読む。

### HANDOVER.md

- §0b（L13〜）：最新の追記。ブルドーザーがパッカンを扱う結末の禁止、跳跳が座ったパッカンを押し上げる発見（実験 3/3）、支配人 v2 の学習環境、PPO と表形式 Q の学習、評価 v2 → v3 → v4、結末の変更、ジャンプカットの罠、表情表 → 気分ネット、提出候補 take 34〜49。
- §0（L84〜）：物理のみ版（外力・テレポートなし）の現状。ファイル表、実行環境、公式ポリシーで確かめた物理の事実、フォーク実験と持ち上げ結末の試行、course-builder の Navigator を差し替えた理由。
- §1〜9（L128〜）：外力版（v1〜v5）時点の旧構成。§4「MjSpec.attach の要点」は現行にも有効。§5 のコントローラは `xfrc_applied` を使う不採用版、§6 の課題は全て解決済み、§9 は開発チーム内の作業方針。
- 読むときの注意：L34 の評価 v2 はエピソードが独立していなかった版の数値（訂正表 10）。L19 の「観測 45 次元」は誤記（訂正表 1）。L122 の支配人 v1「観測 32 次元」はコードでは 35（訂正表 13）。
  L98 の `v7_full.py` の説明は、ブルドーザーがフォークでパッカンを扱う旧結末（`--ending push`／`lift`、通し台本 v4）のもの。現行の既定は `--ending crab --finale circle`（`v7_full.py` の argparse）。

### MANAGER_DESIGN.md

- v1（§0〜§5、§4.5）：ブルドーザーがフォークでパッカンを扱う案。`manager_env.py`（現在は `archive/`）の観測は原文で 32 次元、コードでは 35 次元（訂正表 13）。安全上の理由で凍結。
- v1.3（§6）：ブルドーザー禁止。跳跳がパッカンを押す予備実験（立ったパッカンは押しても倒れる、座ったパッカンは 0.3 m/s でだけ登る）。
- v1.4（§7）前半：採用設計。§7.1 発見（座ったパッカンが跳跳の方を向くと縁で倒れない）、§7.2 学習環境 v2、§7.5〜7.7 PPO 小・中・継続、§7.8 報酬 v2.2、§7.9 near_lip、§7.10 評価の独立化。
- v1.4（§7）後半：§7.11 評価 v3、§7.12 不採用の試み、§7.13 PPO v2.2、§7.14 コース v2、§7.15 評価 v4（最終結果）、§7.16 表情表、§7.17 気分ネット v1 と批評家案の不採用、§7.18 気分ネット v2 と 17 規則。
- 読むときの注意：§7.2 L263 の「観測（45）」は 46 の誤記（訂正表 1）。§7.18 L573 の「§7.16b」は存在しない節（訂正表 9）。§7.17 の正解率 0.921 は上書き済みの v1（訂正表 2）。§7.7 L385 の決定数は現物と異なる（訂正表 3）。§4 L167 の v1「観測（32 次元）」はコードでは 35（訂正表 13）。
- 条件に注意する数値：L303・L339・L345・L366 の押し上げ 63%（22/35）は旧コース・評価 v2 の値（訂正表 15）。L260 のセリフは 6 手に 1 本ずつで、実装は 8 本（訂正表 16）。

### README_development.md

- 構成：原則と 3 体（L5〜12）、筋書き（L14〜26）、支配人 AI のファイル表と比較表（L28〜57）、動かし方（L59〜87、ローカル絶対パスのコマンド 24 本）、ファイル表と take の系譜（L90〜102）。
- 読むときの注意：L14 の見出し「v5 = take 6」（訂正表 5）、L22 の気分ネットは旧版（訂正表 2）、L34 の「観測 45 次元」（訂正表 1）、L51 の「+4.9k 決定」（訂正表 3）、L86 の「1 分」（訂正表 8）。L100 の take の系譜は作業時点のもので、提出版はその後 take 51、take 57（固定ルール）を経て、最終的に本編 take 58（PPO の支配人）に変わった。
- 条件に注意する数値：L57 の「押し上げスキルは正しい状態で呼んでも 63%」は旧コース・評価 v2 の値（訂正表 15）。

### takes.md

- 内容：通し台本 `v7_full.py` が描画した全 take（4〜58）の台帳。節は「読み方（列の定義と略号）」「系譜の全体像」「物理同一の系譜（ダイジェストで確認）」「台帳 1：設定と結果」「台帳 2：採否と所在」「失敗版と変種の意味」「ヘッドレス検証の報告」「提出版 take 58 の時間軸」「固定ルール版 take 57（比較用、58 と同じ設定）の時間軸」「take 51（以前の 2:47 版）の時間軸」「以前の 2:47 版と比較用 3 本（take 51〜54）の時間軸の比較」「出所一覧」。
- 使い方：読者向け文書の条件名（本編（PPO）、固定ルール版、以前の 2:47 版、PPO 版、Q 表版、追走版、旧コース）がどの take か、その take の物理が他のどの take と同一か（`state_digest` の系譜 A〜D）を引く。
- 出所：各 take の `out/v7_full_report_take*.json`（`manager.policy`、`manager.decisions`、`three_crossed`、`sim_seconds`、`state_digest`、`cuts`）、MP4 の長さは ffmpeg の実測。
- 読むときの注意：所在（追跡／未追跡）は執筆時点の `git ls-files out/` による。公開リポジトリの最終構成で変わった場合は台帳の値より `git ls-files` を優先する。

### report_outline.md

- 内容：課題文の要件（加点 4 観点、AI の使用必須、個人情報の禁止）、決定事項（公開範囲、コミットのメールアドレスの匿名化、人名の役割語化）、本文 8 節の骨子（表紙〜動画の構成と再現）、提出手順の点検、案 1・2 からの変更。
- 読むときの注意：L14 の「案 2 で講座のものと書いたのは誤り」は、course-builder が自作であることの訂正記録（訂正表 11）。動画長 2:44 と省略 2 か所は take 46 時点の仕様（訂正表 7）。BGM・ナレーションは未決のまま残っている。
- 数の誤記：L13・L32 の「公式ポリシー 4 本」は 5 本（訂正表 14）。

### face_rules_chart.md

- L5〜80：表情の決め方の図 2 枚（入力、判定）と「しきい値の出どころ」表。17 規則の条件・順序は `crab_face.py` の docstring と、しきい値は同ファイルの定数（`P_FALL`・`P_STALL_FALL`・`EFFORT_HI`・`PUSH_SWEAT_S`・`STALL_S`・`PUSH_STALL_S`・`P_CROSS_HI` ほか）と一致する。
  スキル別の線は `out/manager_runs/mood_net/meta.json` の `thr_smile_by_skill`・`thr_trouble_by_skill`（規則 8 の停滞判定は訂正表 4）。読者向けには `docs/mood_net_and_faces.md` に写した。
- L82〜120：報告書の図 7 枚の清書・照合の経緯と図の一覧。ハンドル名と日付つきの見出しで書かれている。要約は本書「図の経緯」。
- 読むときの注意：L102 の「CPU 1 分」（訂正表 8）、L106 の「表情ログの 23 区間」（訂正表 12）、L106 の時刻は take 46 版（訂正表 6）。L90 の公式ポリシーの列挙は 4 つで `alpha_sitstand` を欠く（図には 5 本とも載る、訂正表 14）。

### timeline_brief_take51.md

- 内容：take 46 版の図と同じ体裁で時刻だけ差し替える指示。速度のかっこ（×4 0:00〜0:44、×2 0:44〜2:29、×1 2:29〜2:47）、上の帯 9 区間、跳跳の顔の帯 12 区間。
- 時刻の出所：`out/v7_full_report_take51.json`。`python analysis/timeline_times.py out/v7_full_report_take51.json` で動画時刻と sim 時刻、表情ログを再出力できる。
- 読むときの注意：時刻は秒に丸めてある。ピン C は 2:09.8（`manager.decisions[2].video_t` 129.8）、D は 2:10.7（`decisions[3].video_t` 130.7）。
  顔が「にっこり（立たせる、成功 99%）」に変わるのは 2:11.7（`face.log`）で、STANDUP の時刻とは別である。

### figures/

- `timeline_ortiz_v1_dense.png`：タイムライン図の初版（半分の大きさで保存）。帯・カード・表で同じ情報が 3 回出て読みにくかったため、帯 2 本と印だけに絞った `report/timeline_ortiz.png` に差し替えた。
- `face_rules_chart_ortiz.webp`：`report/face_rules_chart_ortiz.png` の元データ。

### code_comment_quotes.md

- 内容：読者向けに書き直したコードのコメント・docstring・argparse help について、置換前の原文をファイルごとの表に保存した記録。対象はリポジトリ直下の `*.py`、`analysis/*.py`、`archive/*.py`。
- 構成：置換の方針（規則の表：チャットの直接引用、決定ログの括弧標識、ハンドル名、日付の各型と置換後の形）→ 置換しなかったもの → 検証（`py_compile` と `--help`）→ 表の読み方 → ファイルごとの表。
- 使い方：読者向けのコードは要件を「要件：」、判断を「設計判断：」、検証を「検証：」の文に直し、help は「何をするか・既定値」だけにした。元の文言と判断の経緯は、この記録でファイルと識別子から引く。
- 読むときの注意：コードの動作に関わる行は変えていない（例外は同書に記載の `RUNS` の相対パス化）。転記は原文の保存が目的で数値の訂正は反映していないため、数値は本書の訂正表と `docs/` を優先する。

## 訂正表

原文に残る記述と現物の値の対応。行番号は注記を足した現在のファイルのもの。コードは定数名・関数名で引く。
表の中の略称：旧 README＝`README_development.md`、HANDOVER＝`HANDOVER.md`、設計メモ＝`MANAGER_DESIGN.md`、
図メモ＝`face_rules_chart.md`、構成案＝`report_outline.md`、依頼文＝`timeline_brief_take51.md`。
`meta.json`・`train_curve.json`・`comparison_*.md` は `out/manager_runs/` 以下、`take46.json` などは `out/v7_full_report_take46.json` の略。

| 番号 | 原文の記述（所在） | 現物の値 | 出所 |
|---|---|---|---|
| 1 | 支配人の観測 45 次元（旧 README L34、HANDOVER L19、設計メモ L263） | 46 次元＝3+2+4+2+段階 6+7+結果 13+手 6+3 | `crab_help.py` の `OBS_DIM`、`mood_net/meta.json` の `obs_mean`（46 要素） |
| 2 | 気分ネット 53-32-32-2、正解率 0.92（旧 README L22、HANDOVER L79、設計メモ §7.17） | 旧版（上書き済み）。現物は 53-32-32-5、見送り分で 4 分類 0.80、成功 vs 失敗 0.83（均衡）、渡れる 0.67 | `mood_net/meta.json` の `metrics`（`*/heldout`） |
| 3 | ppo2_medium3 は +4.9k（4,869）決定で中断（旧 README L51、設計メモ L385） | 12,108 → 19,644 で +7,536 決定、実時間 10,876 s（約 3 h）。重みは未保存 | `ppo2_medium3/train_curve.json` の先頭・末尾の `step`・`wall_s` |
| 4 | 停滞の判定が「2 秒窓」と「3 s」で並ぶ（HANDOVER L81、図メモ L56・L79） | 一般の停滞は 2 s 窓で進み 2 cm 未満、押し中は 3 s。対象が違い両方正しい | `crab_face.py` の `STALL_V`・`STALL_S`・`PUSH_STALL_S` |
| 5 | 見出し「筋書き（v5 = take 6）」（旧 README L14） | 本文は take 46 の筋書き（支配人 5 手、輪の万歳）。見出しだけ更新漏れ | 旧 README L16、`take46.json` の `manager.decisions`（5 手） |
| 6 | `report/timeline_ortiz.png` の時刻は take 46 版（図メモ L106。take 51 版に描き直し済み、旧図は `figures/timeline_ortiz_take46.png`） | take 51 は物理同一（sha256・5 手の sim 時刻）、施工 ×4・省略なしで以後の動画は約 +2.86 s（5 手は 2.8〜2.9 s） | 両 JSON `state_digest`・`decisions[].video_t`・`cuts`、依頼文 L42 |
| 7 | 提出版は 2:44、省略 2 か所 sim 22→54 s・110→172 s（HANDOVER §0b、旧 README L24、構成案） | take 46 の仕様。提出版 take 51 は施工 ×4・省略なしで 2:47（167.0 s） | `take51.json` の `cuts`（空）・`video_silent.seconds` |
| 8 | 気分ネットの学習「CPU 1 分」（図メモ L102、旧 README L86） | 学習ループは 3.5 s。「1 分」はデータ読み込みを含むスクリプト全体の目安 | `mood_net/meta.json` の `train_s` |
| 9 | 「§7.16b の設計表どおり」（設計メモ L573） | §7.16b は存在しない。§7.16 の表情表を指す | 設計メモの見出し一覧 |
| 10 | 評価 v2：固定ルール 25、Q 表 23、PPO 中 19、PPO 小 0、ランダム 9（/30）（HANDOVER L34、設計メモ §7.6） | 話が独立していない版。最終は評価 v4：29／26／25／23／14（固定ルール／PPO v2.2／Q 表／PPO 中／ランダム） | `comparison_v2.md`・`comparison_v4.md` |
| 11 | 「course-builder は講座のもの」（構成案 L14 が指す案 2） | 自作。別リポジトリ physical-ai-course-builder を同じ課題のために開発 | 構成案 L14、`../physical-ai-course-builder/LICENSE` |
| 12 | 表情ログ「23 区間」（図メモ L106） | take 46 の表情ログは 26 行。23 は図で隣接する区間をまとめた数 | `take46.json` の `face.log`（26 要素） |
| 13 | 支配人 v1 の観測 32 次元（HANDOVER L122、設計メモ L167） | 35＝16+3+結果 8+手 6+2。32 は初版 3dabe92 の docstring、コードは 33→34（69427a9）→35（4b15858） | `archive/manager_env.py` `OBS_DIM`、`git log -p -- manager_env.py` |
| 14 | 公式ポリシー 4 本（構成案 L13・L32）。図メモ L90 の列挙も 4 つ | 5 本：Microduck の `velstand`・`alpha_sitstand`、Jumper の `locomotion`・`jump`・`dance_crab` | `v7_full.py`・`v7_policies.py` の読み込み |
| 15 | 押し上げ 63%（22/35）（旧 README L57、設計メモ L303・L339・L345・L366） | 旧コース・評価 v2 の固定ルールの値。新コース・評価 v4 の固定ルールは 22/30＝73% | v2 は設計メモ §7.6（決定ログの集計）、v4 は `baselines_v4/eval_rule.json` |
| 16 | 行動（6）とセリフ：6 手に 1 本ずつ（設計メモ L260） | 実装の定型セリフは 8 本。6 手の 6 本に、2 回目以降の PUSH の `PUSH_RETRY` と、倒れた相手への PUSH の `NUDGE` が加わる | `crab_help.py` の `LINES`・`bubble_line` |

## take 番号と版の対応

take 番号は通し描画の連番で、`out/v7_full_report_take*.json`（出来事・判断・表情ログ・最終状態の sha256）が各 take の一次記録である。
提出動画の本編は PPO v2.2・輪の万歳の take 58 で、同じ設定（施工・呼ぶ・戻る・集合 ×4、END の後 1 s、`--speedup CALL=4 RETURN=4 CELEBRATE=4 --tail-write 1.0`）の固定ルール版 take 57 を比較用に描画した。
take 58 は 4 手・2:35（155.5 s）で物理は take 52・47 と同一、take 57 は 5 手・2:37（157.3 s）で物理は take 51・46 と同一である。
以前の速度設定（施工 ×4、省略なし）の 4 本と、同じ物理の記録版（×2、省略 2 か所）の対応は次のとおり（出所：各 report JSON の `manager.policy`、`state_digest`、`manager.decisions`、`video_silent.seconds`）。
全 take の台帳は `takes.md` にある。

| 版 | 施工 ×4、省略なし | 記録版（×2、省略 2 か所） | 支配人の手数 | 動画の長さ（施工 ×4 版） |
|---|---|---|---|---|
| 固定ルール・輪の万歳 | take 51 | take 46（2:44） | 5 | 2:47（167.0 s） |
| PPO v2.2・輪の万歳 | take 52 | take 47 | 4 | 2:45（165.2 s） |
| Q 表・輪の万歳 | take 53 | take 48 | 8 | 2:46（166.3 s） |
| 固定ルール・追走 | take 54 | take 49 | 5 | 2:44（163.7 s） |

各対（51 と 46、52 と 47、53 と 48、54 と 49）は `state_digest` が一致し、3 体とも渡り切っている。
take 50 は施工 ×4 の初版で、描画の標本周期が変わったため物理の経路が変わった（sim 390.66 s、5 手・3 体渡り切りは同じ）。記録として残す。
take 46 より前の take（結末の変遷、旧コース、顔なし版、失敗版）の意味は `takes.md`（台帳 1・2、「失敗版と変種の意味」）にまとめ、経緯の原文は `HANDOVER.md` §0b と `README_development.md` L100 にある。

## 図の経緯

報告書の図 7 枚は `report/` にある。図版は作者側で作成し、記載の数値はコード・評価結果・出来事ログと照合した。
ファイル名の `_ortiz` は GitHub アカウント名 ortiz-ai-partners に由来し、改名していない。
読者向けのキャプションは「何を示すか＋読み方＋出所」に限り、作成の経緯は本節にまとめる。
Microduck の外観が映る図と提出動画は、コードの MIT と分けて CC BY-NC-SA 4.0 の条件で扱う（帰属：Pollen Robotics、microduck_rl。`THIRD_PARTY.md`「本リポジトリで作成したもの」）。

| 図 | ファイル（`report/`） | 生成元 | 照合した内容と出所 |
|---|---|---|---|
| 全体の仕組み（2 つの AI と 3 体） | `system_overview_ortiz.png` | 依頼文から作図 | 観測 46、6 手、3 方式の規模、気分ネット 53-32-32-5、公式ポリシー 5 本（次元は 4 本分。face_rules_chart.md L90 は `alpha_sitstand` を欠く、訂正表 14）。図中の「CPU で 1 分」は訂正表 8。作品名・「カニ」・「CPU 1 分」の表記を直した版に差し替え、旧版は `figures/system_overview_ortiz_v1.png` |
| 表情の決め方（17 規則） | `face_rules_chart_ortiz.png` | face_rules_chart.md の判定図を顔アイコン付きで清書。元 `.webp` は `figures/` | 条件と順序が `crab_face.py` の 17 規則と一致（face_rules_chart.md L84） |
| 支配人 AI の比較（30 シード、2×2） | `results_managers_ortiz.png` | 作図 | 評価 v4 の渡り切り・天面到達・2×2・手数・転倒（`out/manager_runs/comparison_v4.md`） |
| コースと 3 体の動線（平面図） | `course_plan_ortiz.png` | 作図 | 座標が `crab_help.py`・`v7_full.py`・`../physical-ai-course-builder/scene_fork_tracks.xml` と一致（face_rules_chart.md L98） |
| 気分ネットの学習データと流れ | `mood_net_pipeline_ortiz.png` | 作図 | 35 話・47,952 サンプル・450 エポック・0.80／0.83（`mood_net/meta.json`・`report.md`）。「CPU 1 分」は訂正表 8 |
| 表情 11 種の一覧 | `faces_sheet_ja.png` | `analysis/face_sheet.py` が生成 | `crab_face.py` の描画そのもの |
| 動画の構成タイムライン | `timeline_ortiz.png` | 作図。初版 `figures/timeline_ortiz_v1_dense.png` を帯 2 本と印だけに絞って作り直し | take 51 の `video_t` と表情ログ（`timeline_brief_take51.md` の依頼で描き直し、時刻・速度区間・5 手・顔の 12 区間が一致）。本編 take 58（4 手）の時刻とは一致しない。旧図は `figures/timeline_ortiz_take46.png` |

## 結果表の原本（`out/manager_runs/`）

評価と学習の結果はスクリプトが書き出した Markdown で、生成物なので移動も編集もしない。
読者向けの表は `docs/results.md` と `docs/mood_net_and_faces.md` に転記し、ここは原本として参照する。
`comparison_v2.md` 〜 `comparison_v4.md` の 4 つは見出しが同一なので、ファイル名で区別する。

| ファイル | 条件 | 位置づけ |
|---|---|---|
| `comparison_v2.md` | 評価 v2：旧コース（継ぎ目 5 cm）、エピソード非独立 | 評価の独立性を直す前の値。反省の裏付けとして残す |
| `comparison_v3.md` | 評価 v3：旧コース、独立化後 | `comparison_v3b.md` に包含 |
| `comparison_v3b.md` | 評価 v3 ＋ PPO v2.2 | 旧コースとの比較（PPO v2.2 16/30 → 評価 v4 で 26/30） |
| `comparison_v4.md` | 評価 v4：新コース（継ぎ目 1 cm）、30 シード 5000〜5029、独立 | 最終結果 |
| `face_value.md` | PPO v2.2 の批評家 V(s) を気分に使う案の下調べ | 不採用の記録（押し上げ中も V ≈ −21〜−22） |
| `mood_net/report.md` | 気分ネット v2 の成績とスキル別のしきい値 | 現行モデルの成績 |
