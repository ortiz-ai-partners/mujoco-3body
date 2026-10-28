# 気分ネット（mood_net）— 47952 サンプル、35 話、53-32-32-2

| 出力 | 分割 | n | 正解率 | 均衡正解率 | p（真のとき） | p（偽のとき） |
|---|---|---|---|---|---|---|
| skill_ok | train | 37180 | 0.898 | 0.891 | 0.807 | 0.284 |
| skill_ok | heldout | 10772 | 0.921 | 0.918 | 0.75 | 0.275 |
| crossed | train | 37180 | 0.838 | 0.823 | 0.616 | 0.2 |
| crossed | heldout | 10772 | 0.641 | 0.648 | 0.565 | 0.457 |

## 見送り分：スキルと結末ごとの p(スキルがうまく終わる)

| スキル | 結末 | n | p の平均 |
|---|---|---|---|
| WAIT | waited | 2480 | 0.74 |
| SEAT | nothing | 305 | 0.51 |
| SEAT | seated | 2573 | 0.58 |
| SEAT | still_down | 500 | 0.23 |
| PUSH | fell | 273 | 0.31 |
| PUSH | nothing | 135 | 0.17 |
| PUSH | pushed_up | 2357 | 0.91 |
| BACK_OFF | cleared | 33 | 0.91 |
| BACK_OFF | nothing | 70 | 0.67 |
| BACK_OFF | stalled | 532 | 0.19 |
| STANDUP | standing | 295 | 0.80 |
| STANDUP | still_down | 640 | 0.22 |
| WALK_ON | crossed | 529 | 0.83 |
| WALK_ON | nothing | 50 | 0.42 |
