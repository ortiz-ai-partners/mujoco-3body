"""Independent test of the deployed mood net: fresh episodes that played no part in its training.

    python analysis/mood_data.py --seed0 9000 --policies rule   --name mood_test_rule     (and ppo, random)
    python analysis/mood_test.py mood_test_rule mood_test_ppo mood_test_random
    -> out/manager_runs/mood_net/test_report.md, test_metrics.json

The held-out quarter used in analysis/mood_train.py is not an independent test: the input normalisation was computed
over all samples (held-out included), the epoch was chosen on the held-out balanced accuracy, and the face lines were
read off the held-out data.  Here the net, its normalisation and its lines are taken as they are (mood_net.pt, meta.json)
and scored on episodes collected afterwards with seeds the training data never used (8000-8001 and 8100 there; 9000-9001
and 9100 here), same managers and the same seven start scenes.  Samples inside one episode are correlated, so the number
of episodes is reported beside the number of samples.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np                                   # noqa: E402
import torch                                         # noqa: E402

from crab_help import ACTIONS                        # noqa: E402
from mood_train import CLASS_OF, MoodNet, balanced, features   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = os.path.join(ROOT, "out", "manager_runs", "mood_net")


def main(names):
    meta = json.load(open(os.path.join(NET, "meta.json"), encoding="utf-8"))
    net = MoodNet(meta["n_in"], meta["hidden"], meta.get("n_out", 5))
    net.load_state_dict(torch.load(os.path.join(NET, "mood_net.pt"), map_location="cpu"))
    net.eval()
    mean, std = np.asarray(meta["obs_mean"], np.float32), np.asarray(meta["obs_std"], np.float32)

    parts = [np.load(os.path.join(ROOT, "out", "manager_runs", n + ".npz")) for n in names]
    obs = np.concatenate([d["obs"] for d in parts])
    skill = np.concatenate([d["skill"] for d in parts])
    ts = np.concatenate([d["t_in_skill"] for d in parts])
    crossed = np.concatenate([d["crossed"] for d in parts]).astype(bool)
    res = np.concatenate([d["result"] for d in parts])
    ep = np.concatenate([d["episode"] + 1000 * k for k, d in enumerate(parts)])
    cls = np.array([CLASS_OF.get(str(r), 3) for r in res], np.int64)
    with torch.no_grad():
        out = net(torch.tensor(features(obs, skill, ts, mean, std)))
        P = torch.softmax(out[:, :4], 1).numpy()
        PC = torch.sigmoid(out[:, 4]).numpy()

    good = cls == 0
    m = {"episodes": int(len(np.unique(ep))), "samples": int(len(cls)),
         "outcome4_acc": round(float((P.argmax(1) == cls).mean()), 3),
         "success_vs_not_acc": round(float(((P[:, 0] >= 0.5) == good).mean()), 3),
         "success_vs_not_balanced_acc": round(balanced(P[:, 0] >= 0.5, good), 3),
         "crossed_acc": round(float(((PC >= 0.5) == crossed).mean()), 3),
         "crossed_balanced_acc": round(balanced(PC >= 0.5, crossed), 3)}
    # the face lines, read off the old held-out data: do they still split the new moves 80 / 20?
    lines = {}
    for k, name in enumerate(ACTIONS):
        sk = skill == k
        if not sk.any() or name not in meta["thr_smile_by_skill"]:
            continue
        smile, trouble = meta["thr_smile_by_skill"][name], meta["thr_trouble_by_skill"][name]
        g, b = sk & good, sk & ~good
        lines[name] = {"good_above_smile": round(float((P[g, 0] >= smile).mean()), 2) if g.any() else None,
                       "bad_below_trouble": round(float((P[b, 0] <= trouble).mean()), 2) if b.any() else None,
                       "n_good": int(g.sum()), "n_bad": int(b.sum())}
    m["face_lines_by_skill"] = lines
    m["heldout_in_training"] = {k: meta["metrics"][k] for k in ("outcome4/heldout", "success_vs_not/heldout", "crossed/heldout")}
    json.dump(m, open(os.path.join(NET, "test_metrics.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    h = meta["metrics"]
    rows = [f"# 気分ネットの独立テスト — {m['episodes']} 試行・{m['samples']:,} サンプル（{', '.join(names)}）", "",
            "学習に使っていないシードで集め直したデータで、提出動画で使ったネット（重み・正規化・表情の線）をそのまま採点した。", "",
            "| 指標 | 独立テスト | 学習時の見送り分（独立でない） |", "|---|---|---|",
            f"| 4 分類の正解率 | {m['outcome4_acc']} | {h['outcome4/heldout']['acc']} |",
            f"| 成功か失敗かの正解率 | {m['success_vs_not_acc']} | {h['success_vs_not/heldout']['acc']} |",
            f"| 成功か失敗かの均衡正解率 | {m['success_vs_not_balanced_acc']} | {h['success_vs_not/heldout']['balanced_acc']} |",
            f"| 渡れるかの正解率 | {m['crossed_acc']} | {h['crossed/heldout']['acc']} |",
            f"| 渡れるかの均衡正解率 | {m['crossed_balanced_acc']} | {h['crossed/heldout']['balanced_acc']} |", "",
            "表情の線（学習時の見送り分で、うまく終わった手の 8 割が上・失敗した手の 8 割が下になるよう決めた）を新しいデータに当てた割合：", "",
            "| 手 | うまく終わった手のうち にっこりの線以上 | 失敗した手のうち 困りの線以下 |", "|---|---|---|"]
    for name, v in lines.items():
        rows.append(f"| {name} | {v['good_above_smile']}（n {v['n_good']}） | {v['bad_below_trouble']}（n {v['n_bad']}） |")
    open(os.path.join(NET, "test_report.md"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["mood_test_rule", "mood_test_ppo", "mood_test_random"]))
