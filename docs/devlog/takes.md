# take 台帳 — 通し動画（`v7_full.py`）の全テイク

本文書は開発記録（`docs/devlog/`）の一部で、通し台本 `v7_full.py` が描画した全テイク（take 4〜58）の設定・結果・物理の系譜・採否・所在を 1 か所に集めた台帳である。
方針：日付と take 番号はこの文書と devlog の原文にだけ置く。README と `docs/` の本文では版を条件名で呼ぶ（提出動画、本編（take 58）、固定ルール版（take 57）、以前の 2:47 版（take 51）、PPO 版（take 52）、Q 表版、追走版、旧コース（継ぎ目 5 cm）、評価 v4 など）。
例外はファイル名で、`out/3body_arena_v7_take51.mp4` や `out/v7_full_report_take46.json` は固有名としてそのまま引用し、改名しない。
数値の出所は各 take の報告 `out/v7_full_report_take*.json`（キー名を併記）、MP4 の長さは ffmpeg の実測、所在は `git ls-files out/` の結果である。執筆時点は 2026-10-29（日付の年はすべて 2026）。

## 読み方（列の定義と略号）

- 日付：報告 JSON の更新時刻の日付。take 4・5 は JSON と MP4 の時刻が git の取り出し時刻（10-27 20:25）で上書きされているため、git タグ `take4`／`take5` のコミット日（10-27）を使う。
- 設定：支配人｜結末・終幕｜顔｜速度・省略｜jitter を略号で書く。
  - 支配人（`manager.policy`）：rule＝固定ルール（`crab_help.rule_action`）、PPO＝`ppo2_v22`（報酬 v2.2 で継続学習した PPO）、PPO 中＝`ppo2_medium2`、Q＝表形式 Q `tabq2_small`。
  - 結末（`ending`）：push＝BZ のフォークが座ったパッカンを押し倒し自力で起きる（`--ending push`、take 4・5）、crab＝跳跳が押し上げる（`--ending crab`、take 6 以降すべて）。
  - 終幕（`--finale`、JSON の `events` の文言で判別）：around＝跳跳が東側を回り込んで離れた所でダンス、procession＝跳跳が追走しゴールで三人の万歳、circle＝輪になって万歳。
    終幕に至らない失敗 take 8・11〜13・15・17・19・21・26 は `HANDOVER.md` §0b の記述による。take 8 は `--finale` の追加（git コミット e3a40dd）より前で、終幕は around だけだった。
  - 顔（`face.on`、`face.mood_ai.kind`）：なし／表＝表情表（`--face-ai table` 相当）／気分 v1＝気分ネット 53-32-32-2（`--face-ai mood`）／組み立て＝気分ネット v2 53-32-32-5＋計測値（11 顔・17 規則）／決め手＝組み立て＋決め手の値をモニターに表示。
  - 速度・省略：施工区間の倍速（×4 または ×2）。施工より後は ×2、万歳のダンスは ×1（`SPEED`、`SPEED_DANCE`）。省略 2＝ジャンプカット 2 か所（sim 22→54 s、110→172 s、`cuts`）。
  - jitter：`--jitter` の秒数（応援ダンスの開始位置をずらして物理経路だけを変えるダイヤル、既定 0）。JSON に記録されないため devlog の記述（`HANDOVER.md` §0b）から転記した。
- 長さ：音声付き MP4 の実測（m:ss.s、ffmpeg の Duration）。音声なしの `video_silent.seconds` とは 0.1 s 以内で一致する。
  take 50〜54 は MP4 の `mvhd` の長さ（160.20／166.97／165.17／166.33／163.70 s）と `video_silent.seconds` が 0.1 s 以内で一致することを確認した。
  take 55〜57 は ffmpeg の Duration がいずれも 2:37.30 で、`video_silent.seconds` 157.3（4,719 フレーム）と一致する。take 58 は 2:35.47 で、155.5（4,664 フレーム）と一致する。
- 手数：`manager.decisions` の件数。3 体：`three_crossed` の true の数／3。
  take 4（ヘッドレス報告 `out/v7_full_report.json`）と take 5 の報告にはこのキーが無く、`events` から数えた（BZ と跳跳は渡り、パッカンはフォークで倒されて渡らない）。
- digest：`state_digest`（最終状態 qpos＋qvel の sha256）の先頭 8 桁。take 30 以降の報告にだけ記録される。take 29 以前の同一性は `sim_seconds`・`events` の件数と時刻・`manager.decisions` の一致で判定した。
- 所在：MP4 と report JSON の git 追跡状態（追跡／未追跡）。執筆時点の `git ls-files out/` による。公開リポジトリの最終構成（旧 MP4 の Release 移動など）で変わった場合はこの列を更新する。
  未追跡には 2 種類ある：`.gitignore` の対象（`*_cutbug*`・`*_longnotice*`・`*_widebox*`・`*_silent.mp4`）と、`git add` されていないだけのもの（`git status` で `??`）。
  後者は失敗 take 11〜13・15・17・19・21・26 と、成功だが候補にしなかった take 29 の MP4、take 50・55・56 の MP4、take 58 の MP4・JSON・描画ログ、`take6test`・`take8test` の JSON である
  （take 51〜54・57 の MP4 と take 50〜57 の JSON・描画ログは、この追記の時点で追跡に入っている）。

## 系譜の全体像（結末・コース・顔・速度の変遷）

- 結末：押し倒し（take 4・5、`--ending push`）→ 持ち上げ（`--ending lift`、ヘッドレス試行のみで描画 take なし、BZ の寄せ残差 5〜12 cm が窓 ±1.5 cm に届かず未完）→ 押し上げ（take 6 以降、`--ending crab`）。
  BZ がパッカンを扱う結末は安全上の要件（首を持ち上げると破損の恐れ）で封印し、以後の手助けは跳跳が担う（`MANAGER_DESIGN.md` §6、`HANDOVER.md` §0b 冒頭）。
- 終幕：around（take 6〜8）→ procession（take 9・10・12・18・19・25・33、BZ も向き直る版は 37・41・45・49・54）→ circle（take 11 以降の既定）。
- 支配人：固定ルール（take 6 から）、学習済み Q 表（take 7 から）、PPO 中（take 8 のみ、描画版は失敗）、PPO v2.2（take 22 から。提出版の本編 take 58 もこれ）。
- 固定ルールの修正：take 13 の失敗（座り直しの位置 y −2.01 が座席 −2.13 から 12 cm で `crab_help.py` の `SEAT_TOL` 0.12 m の境界にあり、`at_seat` が偽のまま SEAT を 7 回要求）から PUSH 条件に `near_lip` を追加（`MANAGER_DESIGN.md` §7.9）。
- コース：v1＝継ぎ目 5 cm（take 4〜23）→ v2＝継ぎ目 1 cm（take 24 以降、course-builder の `INSTALLATION_GAP` 0.05→0.01、`MANAGER_DESIGN.md` §7.14）。
- 顔：なし（take 29 まで）→ 表（30〜37、30〜33 は左下 320×160、34〜37 は右上 240×120 で字幕の下、押して 5 秒で汗）→ 気分 v1（38〜41、モニター一段）→ 組み立て（42〜45）→ 決め手（46〜54）。
- 速度・省略：施工 ×4（take 5〜10、take 4 は描画の報告がなく不明）→ 全区間 ×2 以下（11〜33、長さ 3:16.7〜4:21.3）→ ×2＋省略 2（34〜49、成功版は 2:40.8〜2:44.1）→ 施工 ×4・省略なし（50〜54、2:40.2〜2:47.0）
  → 呼ぶ・戻る・集合も ×4、END 後の尾 1 s（55〜58、`--speedup CALL=4 RETURN=4 CELEBRATE=4 --tail-write 1.0`、固定ルールの 55〜57 は 2:37.3、PPO の 58 は 2:35.5）。
- 画面と音（55 以降）：支配人の帯（56 から、`--no-band` で外せる）、呼び名「カニさん」→「ちょーさん」（56 から）、パッカンの声 1/3（56 から）、跳跳の声 1/2 とステレオの左右振り分け（57 から）。
  省略の初版（`*_cutbug`）は物理を変えたため失敗版として残し、2 回目で全長版と物理が一致した（`HANDOVER.md` §0b「ジャンプカットの罠」）。
- 評価：v2（10-28、エピソード非独立、`out/manager_runs/comparison_v2.md`）→ v3（10-28、`mj_resetData` で独立、旧コース、`comparison_v3.md`・`comparison_v3b.md`）→ v4（10-28、新コース・30 シード同一、`comparison_v4.md`）。
  v4 の結果は固定ルール 29/30、PPO v2.2 26/30、Q 表 25/30、PPO 中 23/30、ランダム 14/30（`comparison_v4.md`）。

## 物理同一の系譜（ダイジェストで確認）

描画版の物理はコードと設定が同じなら決定的で、顔・気分ネット・省略・施工 ×4 の書き出し間引きは物理を変えない。次の系譜は `state_digest` の一致で確認した（take 29 以前は出来事と手順の一致）。
51＝46、52＝47、53＝48、54＝49 は sha256 の 64 桁全体が一致し、`manager.decisions` の sim 時刻（`t`）と結果（`result`）、`face.mood_ai.inferences`（5,236／5,050／5,239／5,236）も対ごとに一致する。
55＝56＝57＝51 も 64 桁全体が一致し、`events` の sim 時刻、`manager.decisions` の `t`・`result`・`duration_s`、`face`（`log`・`effort_series`・`mood_ai`）が同じ。
違いは書き出し（`video_t`）と画面・音（吹き出しの文言、`chirps`）だけである（`python analysis/timeline_times.py out/v7_full_report_take57.json --compare out/v7_full_report_take51.json`）。
58＝52 も同じで、64 桁全体、`events` の sim 時刻（60 件）、`manager.decisions` の `t`・`result`・`duration_s`、`face`（`log`・`effort_series`・`mood_ai`）が一致する
（`python analysis/timeline_times.py out/v7_full_report_take58.json --compare out/v7_full_report_take52.json`）。

| 系譜 | 条件 | digest | take | 根拠 |
|---|---|---|---|---|
| A | rule・circle・コース v2 | 678fd3ca | 24＝30＝34＝38＝42＝46＝51＝55＝56＝57（34_longnotice・46_widebox も同一） | 30 以降は digest 一致。24＝30 は 62 出来事・5 手・sim 404.22 s の一致（`MANAGER_DESIGN.md` §7.16、`analysis/face_check.py`） |
| B | PPO・circle・コース v2 | aafa49e7 | 27＝31＝35＝39＝43＝47＝52＝58（35_longnotice・47_widebox も同一） | 同上。27＝31 は 60 出来事・4 手・sim 400.6 s の一致 |
| C | Q・circle・jitter 0.4・コース v2 | f53de6e4 | 28＝32＝36＝40＝44＝48＝53（36_longnotice も同一） | 同上。28＝32 は 8 手・sim 402.9 s の一致（`HANDOVER.md` §0b） |
| D | rule・procession（BZ が向き直る）・コース v2 | be8fb01e | 37＝41＝45＝49＝54 | digest 一致。sim 397.72 s |
| E | rule・procession（旧、BZ は後ろ向き）・コース v2 | 7a17ebf0 | 25＝33 | 33 の digest。25 は 57 出来事・5 手・sim 398.52 s の一致 |
| F | rule・circle・コース v1 | —（記録前） | 14＝16 | 61 出来事・5 手・sim 381.46 s、長さ 3:19.7 の一致（カメラの向きだけが違う） |
| G | Q・jitter 0・コース v1（失敗） | —（記録前） | 15＝17＝19 | 79 出来事・18 手・sim 497.46 s の一致（終幕に依らず救助までの物理は同じ） |
| H | rule・応援なし・コース v1（失敗） | —（記録前） | 11＝12 | 47 出来事・5 手・sim 522.5 s の一致 |
| X | 省略の初版実装（失敗） | 8b1170b1 | 34_cutbug＝35_cutbug＝36_cutbug | 支配人の出番の前に時間切れになるため支配人の種類に依らず同一（0 手、sim 522.5 s） |
| — | rule・circle・施工 ×4 の初版（標本周期を変更） | 768e78f7 | 50 のみ | 系譜 A と別経路。5 手・3/3 は同じ |

系譜 D が E と分かれるのは take 37 で追走の終幕に「パッカンが天面を歩く間に BZ がフォークを上げて向き直る」動きを加えたためで、BZ の動きが変わるので物理経路も変わる（`HANDOVER.md` §0b take 34〜37 の項）。
take 28 と 29 は同じ 8 手で渡り切ったが jitter が違う（0.4／0.8）ので別経路（sim 402.9 s／402.1 s）。

## 台帳 1：設定と結果

### コース v1（継ぎ目 5 cm）、顔なし

| take | 日付 | 設定 | 長さ | 手数・3 体 | digest |
|---|---|---|---|---|---|
| 4 | 10-27 | 旧筋書き・push・速度は不明（描画の報告がなく、ヘッドレス報告は `video_t` がすべて 0） | 2:37.9 | —・2/3（ヘッドレス報告の値） | —（記録前） |
| 5 | 10-27 | push・戯れ・天面ジャンプ・応援ダンス入り・施工の走破開始（sim 165.0 s）まで ×4、以後 ×2（跳跳の登坂は ×1） | 2:22.1 | —・2/3 | —（記録前） |
| 6 | 10-28 | rule・crab・around・応援なし・先回りなし・施工 ×4 | 3:45.8 | 8・3/3 | — |
| 7 | 10-28 | Q・around・施工 ×4 | 3:22.7 | 8・3/3 | — |
| 8 | 10-28 | PPO 中・around・施工 ×4 | 3:50.7 | 16・2/3 | — |
| 9 | 10-28 | rule・procession・施工 ×4 | 3:43.7 | 8・3/3 | — |
| 10 | 10-28 | Q・procession・施工 ×4 | 3:17.1 | 8・3/3 | — |
| 11 | 10-28 | rule・circle・応援なし・全区間 ×2 以下 | 4:21.3 | 5・1/3 | — |
| 12 | 10-28 | rule・procession・応援なし・×2 | 4:21.3 | 5・1/3 | — |
| 13 | 10-28 | rule・circle・応援・先回り・登坂修正 | 4:06.8 | 11・2/3 | — |
| 14 | 10-28 | rule・circle・応援・先回り・輪のカメラは東から | 3:19.7 | 5・3/3 | — |
| 15 | 10-28 | Q・circle・東カメラ | 4:10.0 | 18・2/3 | — |
| 16 | 10-28 | rule・circle・輪のカメラは南から | 3:19.7 | 5・3/3 | — |
| 17 | 10-28 | Q・circle・南カメラ | 4:10.0 | 18・2/3 | — |
| 18 | 10-28 | rule・procession | 3:16.7 | 5・3/3 | — |
| 19 | 10-28 | Q・procession | 4:10.0 | 18・2/3 | — |
| 20 | 10-28 | Q・circle・jitter 0.4 | 3:21.4 | 6・3/3 | — |
| 21 | 10-28 | Q・circle・jitter 0.8 | 4:09.2 | 13・2/3 | — |
| 22 | 10-28 | PPO・circle・jitter 0.4 | 4:13.7 | 7・3/3 | — |
| 23 | 10-28 | PPO・circle・jitter 0.8 | 3:18.5 | 4・3/3 | — |

take 4 の描画に対応する報告は残っていない。`out/v7_full_report.json` は同じコミット（git タグ `take4`）に入っているヘッドレス報告で、`video_t` がすべて 0、`video_silent`／`video` を持たない。
take 4 の行の 3 体 2/3 はその報告の値で（sim 409.1 s、BZ のフォークで押し倒す出来事を含む）、描画版の速度と出来事の時刻はこの報告から決められない。
take 5 の速度は `out/v7_full_report_take5.json` の `events[].t` と `video_t` の比による。MP4 `out/3body_arena_v7_take4.mp4` は `out/3body_arena_v7.mp4` と同一内容（sha256 一致）である。

### コース v2（継ぎ目 1 cm）、顔なし、全長

| take | 日付 | 設定 | 長さ | 手数・3 体 | digest |
|---|---|---|---|---|---|
| 24 | 10-28 | rule・circle | 3:31.1 | 5・3/3 | —（系譜 A） |
| 25 | 10-28 | rule・procession | 3:28.2 | 5・3/3 | —（系譜 E） |
| 26 | 10-28 | Q・circle・jitter 0 | 4:14.8 | 39・2/3 | — |
| 27 | 10-28 | PPO・circle・jitter 0 | 3:29.3 | 4・3/3 | —（系譜 B） |
| 28 | 10-28 | Q・circle・jitter 0.4 | 3:30.4 | 8・3/3 | —（系譜 C） |
| 29 | 10-28 | Q・circle・jitter 0.8 | 3:30.0 | 8・3/3 | — |

### コース v2、顔付き、全長（顔モニター左下 320×160）

| take | 日付 | 設定 | 長さ | 手数・3 体 | digest |
|---|---|---|---|---|---|
| 30 | 10-28 | rule・circle・顔 表 | 3:31.1 | 5・3/3 | 678fd3ca |
| 31 | 10-28 | PPO・circle・顔 表 | 3:29.3 | 4・3/3 | aafa49e7 |
| 32 | 10-28 | Q・circle・jitter 0.4・顔 表 | 3:30.4 | 8・3/3 | f53de6e4 |
| 33 | 10-28 | rule・procession・顔 表 | 3:28.2 | 5・3/3 | 7a17ebf0 |

### コース v2、×2＋省略 2 か所（顔モニター右上 240×120）

| take | 日付 | 設定 | 長さ | 手数・3 体 | digest |
|---|---|---|---|---|---|
| 34_cutbug | 10-28 | rule・circle・顔 表・省略の初版実装 | 3:34.3 | 0・1/3 | 8b1170b1 |
| 35_cutbug | 10-28 | PPO・circle・顔 表・省略の初版実装 | 3:34.3 | 0・1/3 | 8b1170b1 |
| 36_cutbug | 10-28 | Q・circle・jitter 0.4・顔 表・省略の初版実装 | 3:34.3 | 0・1/3 | 8b1170b1 |
| 34_longnotice | 10-28 | rule・circle・顔 表・省略 2（注記が長い版） | 2:44.1 | 5・3/3 | 678fd3ca |
| 35_longnotice | 10-28 | PPO・circle・顔 表・省略 2（注記が長い版） | 2:42.3 | 4・3/3 | aafa49e7 |
| 36_longnotice | 10-28 | Q・circle・jitter 0.4・顔 表・省略 2（注記が長い版） | 2:43.5 | 8・3/3 | f53de6e4 |
| 34 | 10-28 | rule・circle・顔 表（字幕の下、5 秒で汗）・省略 2 | 2:44.1 | 5・3/3 | 678fd3ca |
| 35 | 10-28 | PPO・circle・顔 表・省略 2 | 2:42.3 | 4・3/3 | aafa49e7 |
| 36 | 10-28 | Q・circle・jitter 0.4・顔 表・省略 2 | 2:43.5 | 8・3/3 | f53de6e4 |
| 37 | 10-28 | rule・procession（BZ が向き直る）・顔 表・省略 2 | 2:40.8 | 5・3/3 | be8fb01e |
| 38 | 10-28 | rule・circle・気分 v1・モニター一段・省略 2 | 2:44.1 | 5・3/3 | 678fd3ca |
| 39 | 10-28 | PPO・circle・気分 v1・省略 2 | 2:42.3 | 4・3/3 | aafa49e7 |
| 40 | 10-28 | Q・circle・jitter 0.4・気分 v1・省略 2 | 2:43.5 | 8・3/3 | f53de6e4 |
| 41 | 10-28 | rule・procession・気分 v1・省略 2 | 2:40.8 | 5・3/3 | be8fb01e |
| 42 | 10-28 | rule・circle・組み立て・省略 2 | 2:44.1 | 5・3/3 | 678fd3ca |
| 43 | 10-28 | PPO・circle・組み立て・省略 2 | 2:42.3 | 4・3/3 | aafa49e7 |
| 44 | 10-28 | Q・circle・jitter 0.4・組み立て・省略 2 | 2:43.5 | 8・3/3 | f53de6e4 |
| 45 | 10-28 | rule・procession・組み立て・省略 2 | 2:40.8 | 5・3/3 | be8fb01e |
| 46_widebox | 10-28 | rule・circle・決め手（文字で字幕箱が広がる版）・省略 2 | 2:44.1 | 5・3/3 | 678fd3ca |
| 47_widebox | 10-28 | PPO・circle・決め手（同上）・省略 2 | 2:42.3 | 4・3/3 | aafa49e7 |
| 46 | 10-28 | rule・circle・決め手・省略 2 | 2:44.1 | 5・3/3 | 678fd3ca |
| 47 | 10-28 | PPO・circle・決め手・省略 2 | 2:42.3 | 4・3/3 | aafa49e7 |
| 48 | 10-28 | Q・circle・jitter 0.4・決め手・省略 2 | 2:43.5 | 8・3/3 | f53de6e4 |
| 49 | 10-28 | rule・procession・決め手・省略 2 | 2:40.8 | 5・3/3 | be8fb01e |

### コース v2、施工 ×4・省略なし（`--build-speed 4 --no-cuts`）

| take | 日付 | 設定 | 長さ | 手数・3 体 | digest |
|---|---|---|---|---|---|
| 50 | 10-29 | rule・circle・決め手・施工 ×4（標本周期を ×4 に変更） | 2:40.2 | 5・3/3 | 768e78f7 |
| 51 | 10-29 | rule・circle・決め手・施工 ×4（標本は ×2 のまま 2 枚に 1 枚を書き出す） | 2:47.0 | 5・3/3 | 678fd3ca |
| 52 | 10-29 | PPO・circle・決め手・施工 ×4（51 と同じ方式） | 2:45.2 | 4・3/3 | aafa49e7 |
| 53 | 10-29 | Q・circle・jitter 0.4・決め手・施工 ×4（同上） | 2:46.3 | 8・3/3 | f53de6e4 |
| 54 | 10-29 | rule・procession・決め手・施工 ×4（同上） | 2:43.7 | 5・3/3 | be8fb01e |

### コース v2、施工・呼ぶ・戻る・集合 ×4、尾 1 s（`--build-speed 4 --no-cuts --speedup CALL=4 --speedup RETURN=4 --speedup CELEBRATE=4 --tail-write 1.0`）

| take | 日付 | 設定 | 長さ | 手数・3 体 | digest |
|---|---|---|---|---|---|
| 55 | 10-29 | rule・circle・決め手・短縮版（呼ぶ〜戻る・輪への集合を ×4、END 後の書き出し 2.5→1 s）。帯なし、吹き出しは「カニさん」、声は元の音量（モノラル） | 2:37.3 | 5・3/3 | 678fd3ca |
| 56 | 10-29 | 55＋支配人の帯（1 秒 15 文字、チャイムと打鍵音、英語の行 `LINES_EN`）、パッカンの声 1/3、呼び名「ちょーさん」（`LINES`） | 2:37.3 | 5・3/3 | 678fd3ca |
| 57 | 10-29 | 56＋跳跳の声 1/2、鳴いた機体の画面上の位置でステレオの左右に振る（定電力、幅 0.8） | 2:37.3 | 5・3/3 | 678fd3ca |
| 58 | 10-29 | PPO・circle・決め手。57 と同じ設定で支配人だけを PPO v2.2 にした最終版（`--manager ppo --run ppo2_v22`） | 2:35.5 | 4・3/3 | aafa49e7 |

設定の出所は各報告 JSON の `settings`（55 から記録される）：`write_every`（`BUILD`・`CALL`・`RETURN`・`CELEBRATE` が 2）と `tail_write_s` 1.0 は 4 本共通、
`band`（`cps` 15、`hold_s` 2.5）と `duck_voice_gain` 0.3333 は 56 から、`crab_voice_gain` 0.5 と `voice_pan`（`width` 0.8）は 57 から。58 は 57 と `manager`（ppo）・`run`（ppo2_v22）だけが違う。
音声は 55・56 がモノラル、57・58 がステレオ（ffmpeg の stream 表示）。`chirps` は 55 が 82 件、56・57 が 155 件（帯のチャイム 5・打鍵音 68 を含む）、58 が 143 件（チャイム 4・打鍵音 57）。

## 台帳 2：採否と所在

採否の区分：提出版＝本編 take 58（提出動画の 0:18.1 から、`assemble.py` で講座の OP／ED カードと自己紹介をつなぐ）、比較用＝58 と同じ設定の固定ルール版 57 と、施工 ×4・省略なしで描いた 51〜54（51 は以前の 2:47 版で 57 と、52 は 58 と物理が同一）、
候補＝その時点の提出候補（後の版に置き換えた）、記録＝成功したが置き換えた版、失敗＝目的を達しなかった版、不採用＝物理は正しいが表示や結末の要件で捨てた版。
失敗は 事実→原因→対処 の順に書く。所在は MP4／report JSON の順。

### take 4〜23（コース v1）

| take | 採否 | 理由（要点） | MP4 | JSON |
|---|---|---|---|---|
| 4 | 不採用（旧結末） | BZ がパッカンに触れる結末（押し倒し）は安全上の要件で封印。結末の BZ とパッカンの動きはこの版で固まった | 追跡（`3body_arena_v7.mp4` は同一内容） | 描画の報告なし（ヘッドレス報告 `v7_full_report.json` は追跡） |
| 5 | 不採用（旧結末） | 同上。戯れ・天面での前方ジャンプ・応援ダンスの演出はここで固まり、take 6 以降に引き継いだ | 追跡 | 追跡 |
| 6 | 記録 | 押し上げ結末で初めて 3 体が渡った。1 回目の押しが坂の途中で止まり（スキルの精度）、固定ルールの BACK_OFF→SEAT→PUSH の再試行が映る。施工 ×4 は後に撤回 | 追跡 | 追跡 |
| 7 | 記録 | 学習済み Q 表で初めて 3/3。先頭の 2 手（STANDUP→WALK_ON）と 7 手目の重複 STANDUP は学習の癖で、固定ルールが一度で押し上げる手順（5 手）より 3 手多い | 追跡 | 追跡 |
| 8 | 失敗 | 押しが坂で止まった後に STANDUP、転倒・密着の相手に SEAT を 9 回＝判断の失敗 2 か所。固定ルールと Q 表はここで BACK_OFF。報酬 v2.2 の動機（`MANAGER_DESIGN.md` §7.5b が take 8、§7.7〜7.8 が報酬 v2.2） | 追跡 | 追跡 |
| 9 | 記録 | 追走の終幕の初版。1 回目の押しが止まり再試行、8 手。施工 ×4 | 追跡 | 追跡 |
| 10 | 記録 | Q 表＋追走。8 手、転倒 0 | 追跡 | 追跡 |
| 11 | 失敗 | 跳跳が自分の登坂後に天面の東端から滑落し側面に挟まって登坂タイムアウト、救助に来られず PUSH が 3 回 stalled（跳跳は 2.18 m 離れたまま）。原因は峠の後もレーンの狙いが右寄り x 1.72 のままだった経路制御＝設計の不足（ヘッドレス検証は別経路で表れなかった） | 未追跡 | 追跡 |
| 12 | 失敗 | 11 と同一経路・同一失敗（終幕だけが違う）。対処：峠を越えたらレーン狙いをコース中央 x 1.50 へ、先読み 0.6 m、滑落時の退路を追加 | 未追跡 | 追跡 |
| 13 | 失敗 | 登坂修正は効いた。押しが止まり BACK_OFF 後の座り直しが y −2.01（座席 −2.13 から 12 cm、`SEAT_TOL` 0.12 の境界で `at_seat` が偽）。固定ルールは SEAT を 7 回続け（座る位置 y −2.01〜−1.96）時間切れ＝ルールの条件不足。対処：PUSH 条件に `near_lip` | 未追跡 | 追跡 |
| 14 | 記録 | 旧コースで初の全部入り成功（応援・先回り・輪、5 手、転倒 0）。輪のカメラが東からでパッカンが小さく映るため、以後は南から | 追跡 | 追跡 |
| 15 | 失敗 | Q 表が止まった押しの後に SEAT（状態キーは密着の有無しか見ず 0.24 m は非接触）→ 座り直し中に転倒 → 迷走 → 2 回目の押しで西へ押し流され時間切れ＝判断の失敗 | 未追跡 | 追跡 |
| 16 | 候補（旧コース、固定ルール・輪） | 14 と物理が同一（カメラは物理に影響しない）。輪の場面で BZ が奥で正面 | 追跡 | 追跡 |
| 17 | 失敗 | 15 と同一経路。対処：別の物理経路を試すために `--jitter` を追加 | 未追跡 | 追跡 |
| 18 | 候補（旧コース、固定ルール・追走） | 9 の撮り直し（全区間 ×2 以下）。5 手 | 追跡 | 追跡 |
| 19 | 失敗 | 15・17 と同一経路（救助までの物理は終幕に依らない） | 未追跡 | 追跡 |
| 20 | 候補（旧コース、Q 表） | jitter 0.4 の経路で 6 手で成功（押し上げ後に BACK_OFF を省いて立たせる） | 追跡 | 追跡 |
| 21 | 失敗 | 15 型の失敗。3 回目の PUSH（13 手中の 12 手目）が天面に届いた直後に時間切れ。旧コース・全区間 ×2 以下では Q 表は 3 経路（jitter 0／0.4／0.8）中 1 経路で渡った（施工 ×4 の 7・10 は別経路で 3/3） | 未追跡 | 追跡 |
| 22 | 記録 | PPO v2.2 が学習した「押しに失敗したら下がる」が映る（PUSH→fell→BACK_OFF→再押し）。7 手 | 追跡 | 追跡 |
| 23 | 候補（旧コース、PPO） | jitter 0.8 の経路で 4 手。短いので候補とした | 追跡 | 追跡 |

### take 24〜33（コース v2、全長）

| take | 採否 | 理由（要点） | MP4 | JSON |
|---|---|---|---|---|
| 24 | 記録 | 新コースの初版（固定ルール・輪、5 手、3:31）。顔付きの 30 以降に置き換え | 追跡 | 追跡 |
| 25 | 記録 | 固定ルール・追走の新コース版。33 に置き換え | 追跡 | 追跡 |
| 26 | 失敗 | 押し上げ後に BACK_OFF なしで STANDUP→転倒→復帰→WALK_ON で下り坂で転倒（継ぎ目ではない）。転んだ相手に打つ手が行動集合になく Q 表は WAIT を続け時間切れ＝行動集合の限界 | 未追跡 | 追跡 |
| 27 | 記録 | PPO・輪の新コース版（4 手、jitter 0）。31 に置き換え | 追跡 | 追跡 |
| 28 | 記録 | Q 表・輪の新コース版（8 手、jitter 0.4）。32 に置き換え | 追跡 | 追跡 |
| 29 | 記録 | jitter 0.8 でも同じ 8 手で成功。新コース・全長では Q 表は 3 経路（jitter 0／0.4／0.8）中 2 経路で渡った（旧コース・全区間 ×2 以下では 1/3） | 未追跡 | 追跡 |
| 30〜33 | 記録 | 24・27・28・25 の顔付き撮り直し。物理は元と一致（系譜 A・B・C・E）。省略入りの 34〜37 に置き換え | 追跡 | 追跡 |

### take 34〜49（コース v2、×2＋省略）

| take | 採否 | 理由（要点） | MP4 | JSON |
|---|---|---|---|---|
| 34〜36_cutbug | 失敗 | 省略区間で `render_frame()` を呼ばず毎フレームの `mj_forward` が抜けて物理経路が変化。施工走破開始 176.4→180.7 s、戯れ中にパッカンが 4 回転倒、支配人の出番なしで時間切れ（0 手） | 未追跡 | 追跡 |
| 34〜36_longnotice | 不採用 | 省略の注記の文が長く、右下の sim 時計と重なった。物理は 34〜36 と同一 | 未追跡 | 追跡 |
| 34〜37 | 候補 | 省略入りの初版（顔 表、5 秒で汗、追走は BZ が向き直る）。物理は 30〜32 と一致、37 は新しい系譜 D。38〜41 に置き換え | 追跡 | 追跡 |
| 38〜41 | 候補 | 気分ネット v1 を支配人と並走させた版。物理は 34〜37 と一致。42〜45 に置き換え | 追跡 | 追跡 |
| 42〜45 | 候補 | 表情の組み立て版（11 顔・17 規則）。46〜49 に置き換え | 追跡 | 追跡 |
| 46_widebox・47_widebox | 不採用 | 決め手の文で字幕箱の幅が広がった版。物理は 46・47 と同一。対処：文字を 300 px で折り返す（`v6_common.Captioner`） | 未追跡 | 追跡 |
| 46 | 記録（×2＋省略、51〜54 に置き換え） | 固定ルール・輪の版、5 手、2:44.1。施工 ×4 の 51 に置き換え（物理同一） | 追跡 | 追跡 |
| 47 | 記録（×2＋省略、51〜54 に置き換え） | PPO 版、4 手、2:42.3。52 に置き換え（物理同一） | 追跡 | 追跡 |
| 48 | 記録（×2＋省略、51〜54 に置き換え） | Q 表版、8 手、2:43.5、jitter 0.4。53 に置き換え（物理同一） | 追跡 | 追跡 |
| 49 | 記録（×2＋省略、51〜54 に置き換え） | 追走版、5 手、2:40.8。54 に置き換え（物理同一） | 追跡 | 追跡 |

### take 50〜54（コース v2、施工 ×4・省略なし）

| take | 採否 | 理由（要点） | MP4 | JSON |
|---|---|---|---|---|
| 50 | 記録 | 施工 ×4 の初版。フレームの標本周期そのものを ×4 にしたため毎フレームの forward の回数が変わり経路が変化（digest 768e78f7）。それでも 5 手・3/3・2:40.2 | 未追跡 | 追跡 |
| 51 | 比較用（以前の 2:47 版、候補から置き換え） | 標本は ×2 のまま 2 枚に 1 枚だけ書き出す方式。46 と digest・5 手・sim 時刻がすべて一致。施工は省略なし、2:47.0。57 に置き換え（物理同一）、比較の基準として残す | 追跡 | 追跡 |
| 52 | 比較用（PPO 版） | 47 と digest 一致。4 手（SEAT→PUSH→STANDUP→WALK_ON、押し上げ後の BACK_OFF を省く）、2:45.2 | 追跡 | 追跡 |
| 53 | 比較用（Q 表版） | 48 と digest 一致。8 手、jitter 0.4、2:46.3。先頭の STANDUP→WALK_ON（stalled）と 7 手目の重複 STANDUP（nothing）は学習の癖 | 追跡 | 追跡 |
| 54 | 比較用（追走版） | 49 と digest 一致。5 手は 51 と同じ順・同じ sim 時刻、終幕だけが追走（ゴールで三人の万歳）、2:43.7 | 追跡 | 追跡 |

take 50〜54 の描画ログ（`out/v7_take50render.log`〜`v7_take54render.log`）も追跡に入っている（この追記の時点の `git ls-files out/`）。当初の執筆時点では 50〜54 はすべて `git add` 前だった。
take 51 の圧縮複製（同じ内容の小さい MP4、4.4 MB）は `.gitignore` の `*.notion.mp4` の対象。`HANDOVER.md` §0b のテイク毎の記録は take 49 で終わり、50〜58 の一次記録は report JSON・描画ログ・この台帳である。

### take 55〜58（コース v2、施工・呼ぶ・戻る・集合 ×4、尾 1 s）

| take | 採否 | 理由（要点） | MP4 | JSON |
|---|---|---|---|---|
| 55 | 記録（短縮版） | 自己紹介と講座のカードを足しても 3 分に収まる長さにするため、`--speedup` で CALL・RETURN・CELEBRATE（輪のダンスの前まで）を ×4、`--tail-write 1.0` で END 後の書き出しを 1 s にした。51 と digest・62 出来事の sim 時刻と文言・5 手がすべて一致、157.3 s。56 に置き換え | 未追跡 | 追跡 |
| 56 | 記録 | 55＋支配人の帯、パッカンの声 1/3、呼び名「ちょーさん」。digest は 55 と同一（帯は描画のみ、`intro.draw_avatar` を借りるだけで台本の乱数を使わない）。出来事は MANAGER #1〜#3 の 3 行で吹き出しの「カニさん」が「ちょーさん」に変わるだけ。57 に置き換え | 未追跡 | 追跡 |
| 57 | 比較用（固定ルール版、58 と同じ設定） | 56＋跳跳の声 1/2、鳴き声のステレオの左右振り分け（`v6_common.screen_xy` で画面上の位置を求める、描画側のみ）。digest・出来事・判断・`face` は 56 と同一。これを本編にした試作の結合は 178.41 s。提出動画の支配人を学習した AI にするため本編は 58 に置き換え、57 は評価で最良の固定ルールを同じ設定で示す比較として残す | 追跡 | 追跡 |
| 58 | 提出版（本編） | 57 と同じ設定で支配人を PPO v2.2 にした版。4 手（SEAT→PUSH→STANDUP→WALK_ON、押し上げ後の BACK_OFF を省く）、すべて成功、転倒 0。digest・出来事の sim 時刻・判断・`face` は 52 と同一、155.5 s。提出動画は `assemble.py` で講座の OP（3.04 s）＋自己紹介 `out/intro.mp4`（15.1 s）＋本編＋講座の ED（2.97 s）＝176.58 s、BGM `music/marimba_bgm.py`（−16 dB、一定、58 の時刻に合わせた既定の版） | 追跡 | 追跡 |

所在は追記の時点の `git ls-files out/` と `git status --short`。描画ログ `out/v7_take55render.log`〜`v7_take58render.log` は追跡。
施工 ×4 の 2 方式の違いは `v7_full.py` の `--build-speed` の help と `SPEED` 直上のコメント、および `build_write_every` の分岐（`render_frame(write=False)` で標本は取り書き出しだけ省く）にある。

追跡 MP4 のうち take 8 以外には同じ内容の圧縮複製（小さい MP4）が並ぶ（take 4 の複製は take 番号のない旧名 `3body_arena_v7` の側にある）。
`*_cutbug`・`*_longnotice`・`*_widebox` の MP4 は `.gitignore` の対象で、同名の report JSON と描画ログ（`out/v7_take34_cutbugrender.log` など）は追跡のまま残る。

## 失敗版と変種の意味

- `*_cutbug`（take 34〜36 の 1 回目）：ジャンプカットの初版実装。省略区間でフレームを描かない＝`render_frame()` を呼ばない、としたため、描画のたびに入る `mj_forward`（ソルバーのウォームスタートを更新する）が省略区間だけ抜けて物理の経路が変わった。
  施工の走破開始が 176.4→180.7 s にずれ、戯れ中にパッカンが 4 回転倒して待機場所に着けず、3 本とも支配人の出番なしで時間切れ（0 手、BZ だけが渡った）。
  直し：省略区間でも `render_frame(write=False)` で軌道更新と `mj_forward` を毎フレーム呼び、描画と書き出しだけを省く。2 回目（34〜37）は全長版と digest が一致した（`HANDOVER.md` §0b）。
  教訓：描画版の物理は「フレームのたびの `mj_forward`」込みで決定的なので、フレームを間引くときも forward の呼び方を変えてはならない。take 50 も同じ理由で経路が変わった。
- `*_longnotice`（take 34〜36）：省略の注記「≫ 省略（sim a→b s）」の文が長く、右下の sim 時計と重なった版。注記を短くして撮り直した。物理は本採用版と同一。
- `*_widebox`（take 46・47）：顔モニターの決め手の文で字幕箱の幅が広がった版。`v6_common.Captioner` が 300 px で折り返すように直して撮り直した。物理は本採用版と同一
  （`out/v7_full_report_take46_widebox.json`・`take47_widebox.json` の `state_digest` が 46・47 と一致）。
- 未追跡の take（11〜13・15・17・19・21・26 は失敗、29 は成功）：29 は 28 と同じ手順の別経路なので候補にしなかった。他は上の台帳 2 に理由を書いた。report JSON は追跡されているので手順と時刻は追える。

## ヘッドレス検証の報告（MP4 なし）

`--test` の報告は `video_t` がすべて 0 で `video_silent`／`video` を持たず、描画版と物理経路が一致しない（毎フレームの `mj_forward` の有無）。描画の前の手順確認に使った。

| 報告 | 日付 | 支配人 | 手数・3 体 | 備考 |
|---|---|---|---|---|
| `take6test` | 10-28 | rule | 18・2/3 | WALK_ON を 14 回（walked 2、stalled 11、最後は結果なし）繰り返し時間切れ。`course_disturbed` に up_1 0.044 m・down_1 0.042 m＝コース破損の記録（未追跡） |
| `take6test2` | 10-28 | rule | 5・3/3 | 座席修正後の通し確認 |
| `take7test`・`take10test` | 10-28 | Q | 8・3/3 | 描画版 7・10 と同じ 8 手 |
| `take8test` | 10-28 | PPO 中 | 4・3/3 | ヘッドレスは 4 手で成功、描画版 take 8 は別経路で失敗（未追跡） |
| `take9test`〜`take9test4` | 10-28 | rule | 5／34／5／5 | 追走の終幕の確認。test2 は WALK_ON の後に WAIT を 28 回で時間切れ |
| `take11test`〜`take11test3` | 10-28 | rule | 5・3/3 | 登坂修正と ×2 上限の確認 |
| `take13test` | 10-28 | rule | 38・2/3 | WALK_ON で天面の継ぎ目につまずいて転倒、起きられず時間切れ（旧コースの既知のスキル側の失敗） |
| `take22test` | 10-28 | PPO | 47・2/3 | STANDUP 後に下り坂で転倒、WAIT／BACK_OFF の交互で時間切れ |
| `take37test` | 10-28 | rule | 5・3/3 | 省略入り版のヘッドレス確認（digest 9e244bec、sim 381.6 s） |
| `facecheck_A`／`facecheck_B` | 10-28 | rule | 5・3/3 | 顔なし／顔あり。digest c083a03c が一致、64 出来事・5 手・sim 385.6 s（`analysis/face_check.py`） |
| `moodcheck_B`〜`moodcheck_E` | 10-28 | rule | 5・3/3 | 省略あり、顔 表／気分ネットの各版。すべて digest c083a03c＝省略と気分ネットは物理を変えない |
| `test14`〜`test21` | 10-27 | — | — | take 5 前後の旧筋書き（持ち上げ結末の試行を含む）。`HANDOVER.md` §0 の #14〜#21 |

## 提出版 take 58 の時間軸（提出動画｜本編｜sim 秒）

速度区間（`python analysis/timeline_times.py out/v7_full_report_take58.json` の出力、本編の時刻）：×4 0:00〜0:44.1、×2 0:44.1〜1:20.4、×4 1:20.4〜1:24.3、×2 1:24.3〜2:14.8、
×4 2:14.8〜2:19.1、×1 2:19.1〜2:34.4（最後の出来事）。MP4 は 2:35.5。提出動画の時刻は本編＋18.14 s（講座の OP 3.04 s＋自己紹介 15.1 s、`assemble.py` の `parts[].start_s`）。
take 52 との違いは CALL の途中から（`--compare` の shift：跳跳が戻り始める出来事 −0.40 s、RETURN −1.27 s、RESCUE 以後 −3.93〜−3.94 s、輪のダンス以後 −8.20 s）。
take 57 とは 2 手目 PUSH の結果（sim 347.86 s）まで出来事の sim 時刻と動画時刻が同じで、その後は BACK_OFF がないぶん早く進む。

| 出来事 | 提出動画 | 本編 | sim 秒 | 出所 |
|---|---|---|---|---|
| 施工完了＝BZ 渡り切り | 1:12.1 | 0:54.0 | 196.1 | `events`「construction done」 |
| パッカンが座り込む | 1:26.4 | 1:08.2 | 224.6 | `events`「MD: 諦めて座り込む」 |
| 跳跳が天面で前方ジャンプ | 1:33.6 | 1:15.4 | 239.0 | `events`「JP stuck at the crest; forward jump」 |
| 跳跳 渡り切り | 1:37.0 | 1:18.9 | 245.9 | `events`「JP crossed the course」 |
| 仲間を呼ぶ（以後 ×4） | 1:38.5 | 1:20.4 | 248.9 | `events`「stage -> CALL」 |
| 支配人 1 手目 SEAT（以後 ×2） | 1:42.4 | 1:24.3 | 264.6 | `manager.decisions[0]` |
| 2 手目 PUSH | 1:48.4 | 1:30.2 | 276.5 | `manager.decisions[1]` |
| 3 手目 STANDUP | 2:24.0 | 2:05.9 | 347.9 | `manager.decisions[2]` |
| 4 手目 WALK_ON | 2:26.8 | 2:08.7 | 353.4 | `manager.decisions[3]` |
| パッカン渡り切り（3 体そろう、以後 ×4） | 2:32.9 | 2:14.8 | 365.6 | `events`「DUCK CROSSED THE COURSE」 |
| 輪の万歳の開始（以後 ×1） | 2:37.2 | 2:19.1 | 382.7 | `events`「the circle: …」 |
| END | 2:52.6 | 2:34.4 | 398.1 | `events`「stage -> END」 |
| 本編の終わり（END＋1 s）／提出動画の終わり | 2:53.6／2:56.6 | 2:35.5 | 399.1 | `video_silent.seconds`、`tail_write_s`、`assemble.py` の `total_s` |

4 手の結果は seated／pushed_up／standing／crossed、所要は 11.9／71.3／5.5／12.2 s（`manager.decisions[].result`・`duration_s`）、転倒 0、コース破損なし（`course_disturbed` が空）。
STANDUP を選んだときの跳跳は 0.25 m 後ろで非接触（`crab_dist`、`touching`）。気分ネットの推論は 5,050 回、表情ログは 26 行で、いずれも 52 と同一。
出来事は 60 件で、57 の 62 件から BACK_OFF の決定と結果の 2 行が抜け、引き継ぎの行の支配人名が「PPO 方策（ppo2_v22）」、STANDUP の行の直前の結果が pushed_up になる（数字を除いた文言の比較）。
BGM は `music/marimba_bgm.py` の既定（`BGM_MAIN` なし）で 58 の時刻に合わせた版（173.6 s。天面を歩く区間を 14 拍から 12 拍に書き直した）。`BGM_MAIN=take57` で 57 用の版（175.4 s）を書く。

## 固定ルール版 take 57（比較用、58 と同じ設定）の時間軸（試作の提出動画｜本編｜sim 秒）

速度区間（`python analysis/timeline_times.py out/v7_full_report_take57.json` の出力、本編の時刻）：×4 0:00〜0:44.1、×2 0:44.1〜1:20.4、×4 1:20.4〜1:24.3、×2 1:24.3〜2:16.7、
×4 2:16.7〜2:20.9、×1 2:20.9〜2:36.3（最後の出来事）。MP4 は 2:37.3。試作の提出動画（57 を本編にした結合、`total_s` 178.41）の時刻は本編＋18.14 s（講座の OP 3.04 s＋自己紹介 15.1 s、`assemble.py` の `parts[].start_s`）。
take 51 との違いは CALL の途中から（`--compare` の shift：跳跳が戻り始める出来事 −0.40 s、RETURN −1.27 s、RESCUE 以後 −3.93〜−3.94 s、輪のダンス以後 −8.17 s）。

| 出来事 | 試作の提出動画 | 本編 | sim 秒 | 出所 |
|---|---|---|---|---|
| 施工完了＝BZ 渡り切り | 1:12.1 | 0:54.0 | 196.1 | `events`「construction done」 |
| パッカンが座り込む | 1:26.4 | 1:08.2 | 224.6 | `events`「MD: 諦めて座り込む」 |
| 跳跳が天面で前方ジャンプ | 1:33.6 | 1:15.4 | 239.0 | `events`「JP stuck at the crest; forward jump」 |
| 跳跳 渡り切り | 1:37.0 | 1:18.9 | 245.9 | `events`「JP crossed the course」 |
| 仲間を呼ぶ（以後 ×4） | 1:38.5 | 1:20.4 | 248.9 | `events`「stage -> CALL」 |
| 支配人 1 手目 SEAT（以後 ×2） | 1:42.4 | 1:24.3 | 264.6 | `manager.decisions[0]` |
| 2 手目 PUSH | 1:48.4 | 1:30.2 | 276.5 | `manager.decisions[1]` |
| 3 手目 BACK_OFF | 2:24.0 | 2:05.9 | 347.9 | `manager.decisions[2]` |
| 4 手目 STANDUP | 2:24.9 | 2:06.8 | 349.6 | `manager.decisions[3]` |
| 5 手目 WALK_ON | 2:27.7 | 2:09.6 | 355.2 | `manager.decisions[4]` |
| パッカン渡り切り（3 体そろう、以後 ×4） | 2:34.8 | 2:16.7 | 369.4 | `events`「DUCK CROSSED THE COURSE」 |
| 輪の万歳の開始（以後 ×1） | 2:39.0 | 2:20.9 | 386.3 | `events`「the circle: …」 |
| END | 2:54.4 | 2:36.3 | 401.7 | `events`「stage -> END」 |
| 本編の終わり（END＋1 s）／試作の提出動画の終わり | 2:55.4／2:58.4 | 2:37.3 | 402.7 | `video_silent.seconds`、`tail_write_s`、`assemble.py` の `total_s` |

## take 51（以前の 2:47 版、当時の提出候補）の時間軸（動画時刻｜sim 秒）

速度区間（`python analysis/timeline_times.py out/v7_full_report_take51.json` の出力）：×4 0:00〜0:44.1、×2 0:44.1〜2:29.1、×1 2:29.1〜2:44.5（最後の出来事）。MP4 は 2:47.0。
右下に sim 時計と x4／x2／x1 を常時表示する。take 46 との違いは施工区間だけで、施工より後の動画時刻はすべて +2.8〜2.9 s（表示の丸め。46 の SEAT 1:25.3 → 51 の 1:28.2）。

| 出来事 | 動画 | sim 秒 | 出所 |
|---|---|---|---|
| 施工完了＝BZ 渡り切り（4/4 面、上昇 0.440 m） | 0:54.0 | 196.1 | `events`「construction done」、`construction.rise_m` |
| パッカンが座り込む | 1:08.2 | 224.6 | `events`「MD: 諦めて座り込む」 |
| 跳跳が天面で前方ジャンプ | 1:15.4 | 239.0 | `events`「JP stuck at the crest; forward jump」 |
| 跳跳 渡り切り | 1:18.9 | 245.9 | `events`「JP crossed the course」 |
| 支配人 1 手目 SEAT | 1:28.2 | 264.6 | `manager.decisions[0]` |
| 2 手目 PUSH（71.3 s、動画 36 s） | 1:34.2 | 276.5 | `manager.decisions[1]` |
| 3 手目 BACK_OFF | 2:09.8 | 347.9 | `manager.decisions[2]` |
| 4 手目 STANDUP | 2:10.7 | 349.6 | `manager.decisions[3]` |
| 5 手目 WALK_ON | 2:13.5 | 355.2 | `manager.decisions[4]` |
| パッカン渡り切り（3 体そろう） | 2:20.6 | 369.4 | `events`「DUCK CROSSED THE COURSE」 |
| 輪の万歳の開始（以後 ×1） | 2:29.1 | 386.3 | `events`「the circle: …」 |
| END | 2:44.5 | 401.7 | `events`「stage -> END」 |

5 手の結果は seated／pushed_up／cleared／standing／crossed、転倒 0、コース破損なし（`manager.decisions[].result`、`course_disturbed` が空）。
各手の所要は 11.9／71.3／1.7／5.5／14.2 s（`manager.decisions[].duration_s`）。
気分ネットの推論は 5,236 回（`face.mood_ai.inferences`）、表情ログは 26 行（`face.log`）。これらの値は 46 と同一である。
出来事は 51 が 62 件、46 が 64 件で、差は 46 だけにある省略の注記 2 件（`events` の「JUMP CUT: sim 22-54 s …」「JUMP CUT: sim 110-172 s …」）。他の 62 件は文言まで一致する。

take 50 では経路が変わり、施工完了 sim 196.12 s（51 は 196.08 s）、跳跳のジャンプ sim 241.5 s（51 は 239.0 s）、SEAT sim 267.0 s、PUSH は 56.1 s で天面に届き、渡り切り sim 356.0 s、END 388.2 s（`out/v7_full_report_take50.json`）。
take 50 の BACK_OFF は押し上げ直後に跳跳が接触したまま（`touching` true）で出され、51 では非接触（0.25 m）で出された点も違う。

## 以前の 2:47 版と比較用 3 本（take 51〜54）の時間軸の比較（動画時刻）

4 本とも施工は ×4 で 0:00〜0:44.1、支配人の 1 手目は 1:28.2（sim 264.6 s）、押し上げの完了は 2:09.7〜2:09.8（sim 347.7〜347.9 s）で、違いは支配人の手順と終幕にある。
出所は各 `out/v7_full_report_take5x.json` の `manager.decisions[].video_t`・`events[].video_t`・`video_silent.seconds`（`python analysis/timeline_times.py` で再出力できる）。

| 出来事 | 51 固定ルール・輪 | 52 PPO・輪 | 53 Q 表・輪 | 54 固定ルール・追走 |
|---|---|---|---|---|
| ×2 区間の終わり（終幕の開始、以後 ×1） | 2:29.1 | 2:27.3 | 2:28.4 | 2:25.8 |
| 支配人 1 手目 | 1:28.2 SEAT | 1:28.2 SEAT | 1:28.2 STANDUP | 1:28.2 SEAT |
| PUSH の開始 | 1:34.2 | 1:34.2 | 1:40.2（4 手目） | 1:34.2 |
| 押し上げ完了（pushed_up） | 2:09.8 | 2:09.8 | 2:09.7 | 2:09.8 |
| パッカン渡り切り（3 体そろう） | 2:20.6 | 2:18.7 | 2:20.7 | 2:20.6 |
| END ／ MP4 の長さ | 2:44.5 ／ 2:47.0 | 2:42.6 ／ 2:45.2 | 2:43.8 ／ 2:46.3 | 2:41.2 ／ 2:43.7 |

手順の全体（動画時刻、`manager.decisions`）：

- 52（PPO v2.2、4 手）：SEAT 1:28.2 → PUSH 1:34.2 → STANDUP 2:09.8（跳跳が 0.25 m に接触せず残ったまま）→ WALK_ON 2:12.6。BACK_OFF を省いた分、渡り切りが 51 より動画で 1.9 s（sim 3.7 s）早い。
- 53（Q 表、8 手）：STANDUP 1:28.2（standing）→ WALK_ON 1:31.0（stalled、坂の入口で止まる）→ SEAT 1:36.5 → PUSH 1:40.2 → BACK_OFF 2:09.8 → STANDUP 2:10.6 → STANDUP 2:13.4（nothing）→ WALK_ON 2:13.9。
  先頭 2 手は座った相手をまず立たせて歩かせる学習の癖で、sim 16.5 s（動画 8.3 s）を使う（`duration_s` 5.5＋11.0）。
  座り直しが 51 より短い分（SEAT 7.4 s、51 は 11.9 s）を差し引くと、PUSH の開始は 51 より sim 12.1 s（動画 6.0 s）遅い。take 7 のヘッドレス検証から同じ 8 手の型（`MANAGER_DESIGN.md` §7.6 の「学習済み Q 表を通し台本に載せた検証」）。
- 54（固定ルール・追走、5 手）：手順と sim 時刻は 51 と同一。終幕は 2:25.8 からゴール前で三人の万歳（`events`「the three cheer at the goal: …」）、輪への移動がないため END は 51 より動画で 3.3 s 早い。
- 表情ログの行数（`face.log`）：51 26 行、52 26 行、53 27 行、54 26 行、50 24 行。気分ネットの推論回数は上の系譜の節に記した。

## 出所一覧

- 各 take の報告：`out/v7_full_report_take*.json`（`manager.policy`、`manager.decisions`、`three_crossed`、`sim_seconds`、`state_digest`、`cuts`、`face`、`events`、`video_silent`）。
- MP4 の長さと更新時刻：`out/3body_arena_v7_take*.mp4` を ffmpeg（imageio-ffmpeg 同梱）の `-i` で計測。take 50〜54 は MP4 の `mvhd` ボックスの長さで確認。
- take 55〜58 の描画ログ：`out/v7_take55render.log`〜`out/v7_take58render.log`。設定は報告 JSON の `settings`。提出動画の結合は `assemble.py` の標準出力（`parts`、`total_s`）。
- 設定の経緯：`docs/devlog/HANDOVER.md` §0b（take 6〜49 のテイク毎の記録、ジャンプカットの罠）、`docs/devlog/MANAGER_DESIGN.md` §0・§6・§7.4〜7.18、`docs/devlog/README_development.md`（旧 README、`out/` の行）。
- 施工 ×4 の 2 方式：`v7_full.py` の `--build-speed` の help と `SPEED` 付近のコメント、`build_write_every` の分岐。help は `docs/devlog/HANDOVER.md` §0b（ジャンプカットの罠）を参照する。
- take 50〜54 の描画ログ：`out/v7_take50render.log`〜`out/v7_take54render.log`（起動行に `face=on mood_ai=mood_net`、出来事の sim 時刻）。
- 評価の版：`out/manager_runs/comparison_v2.md`・`comparison_v3.md`・`comparison_v3b.md`・`comparison_v4.md`。
- 追跡状態：`git ls-files out/`、`git status --short`、`.gitignore`。
