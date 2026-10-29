"""Train the crab's mood net: the second AI that infers, at any control step of a rescue, how the running move will
end - p_success / p_stall / p_fall / p_nothing - and whether the duck gets across (crab_face.MoodAI; requirement:
two AIs doing real inference in the video, the face composed from several probabilities and measured values).

Data: out/manager_runs/mood_data.npz from analysis/mood_data.py (the manager's 46-dim observation every 0.1 s inside
every skill, which skill, how long it has run, how it ended, whether the episode ended crossed).  Features: the
observation (standardised) + the skill one-hot (6) + time in the skill (/60 s) = 53.  Net: 53-32-32-5, tanh: four
logits (softmax over the outcome classes, cross-entropy) and one logit (the crossing, BCE).  Episodes are split by id
(every 4th held out); the epoch is chosen by the held-out balanced accuracy of "ends well vs not".

The outcome classes, from the skill's result:  success = seated / pushed_up / cleared / standing / crossed / walked /
waited;  stall = stalled / slipped;  fall = fell;  nothing = nothing / still_down.

The smile and trouble lines for the face (crab_face.py rules 12-14) are read off the held-out data: 80% of the
moves that ended well lie above the smile line (the 20th percentile of their p_success), 80% of the failed moves lie
below the trouble line (the 80th percentile of theirs).

    python analysis/mood_train.py --data mood_data --out mood_net
    -> out/manager_runs/mood_net/mood_net.pt, meta.json (normalisation, layout, thresholds, metrics), report.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)                     # crab_help, for the report's skill names
N_SKILLS = 6
T_SCALE = 60.0
CLASSES = ("success", "stall", "fall", "nothing")
CLASS_OF = {"seated": 0, "pushed_up": 0, "cleared": 0, "standing": 0, "crossed": 0, "walked": 0, "waited": 0,
            "stalled": 1, "slipped": 1, "fell": 2, "nothing": 3, "still_down": 3}


def features(obs, skill, t_in_skill, mean, std):
    """The mood net's input from the manager's observation, the running skill and its elapsed time."""
    obs = (np.asarray(obs, np.float32) - mean) / std
    if obs.ndim == 2:
        oh = np.zeros((obs.shape[0], N_SKILLS), np.float32)
        oh[np.arange(obs.shape[0]), np.asarray(skill, np.int64)] = 1.0
        ts = (np.minimum(np.asarray(t_in_skill, np.float32), T_SCALE) / T_SCALE)[:, None]
        return np.concatenate([obs, oh, ts], axis=1)
    oh = np.zeros(N_SKILLS, np.float32)
    oh[int(skill)] = 1.0
    return np.concatenate([obs, oh, [min(float(t_in_skill), T_SCALE) / T_SCALE]]).astype(np.float32)


class MoodNet(torch.nn.Module):
    def __init__(self, n_in=46 + N_SKILLS + 1, hidden=32, n_out=5):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(n_in, hidden), torch.nn.Tanh(), torch.nn.Linear(hidden, hidden),
                                       torch.nn.Tanh(), torch.nn.Linear(hidden, n_out))

    def forward(self, x):
        return self.net(x)


def balanced(pred, truth):
    tpr = float(pred[truth].mean()) if truth.any() else float("nan")
    tnr = float((~pred[~truth]).mean()) if (~truth).any() else float("nan")
    return (tpr + tnr) / 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="mood_data")
    ap.add_argument("--out", default="mood_net")
    ap.add_argument("--epochs", type=int, default=600)
    ap.add_argument("--hidden", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    torch.manual_seed(args.seed)
    d = np.load(os.path.join(ROOT, "out", "manager_runs", args.data + ".npz"))
    obs, skill, ts, crossed, ep, res = d["obs"], d["skill"], d["t_in_skill"], d["crossed"], d["episode"], d["result"]
    cls = np.array([CLASS_OF.get(str(r), 3) for r in res], np.int64)
    mean, std = obs.mean(0), obs.std(0) + 1e-6
    X = features(obs, skill, ts, mean, std)
    test = (ep % 4) == 3
    train = ~test
    Xt, Xv = torch.tensor(X[train]), torch.tensor(X[test])
    Ct, Cv = torch.tensor(cls[train]), torch.tensor(cls[test])
    Bt, Bv = torch.tensor(crossed[train].astype(np.float32)), torch.tensor(crossed[test].astype(np.float32))
    net = MoodNet(X.shape[1], args.hidden, 5)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    ce, bce = torch.nn.CrossEntropyLoss(), torch.nn.BCEWithLogitsLoss()

    def loss_of(out, c, b):
        return ce(out[:, :4], c) + bce(out[:, 4], b)

    t0 = time.perf_counter()
    best, best_epoch, best_state = -float("inf"), -1, None
    for epoch in range(args.epochs):
        net.train()
        opt.zero_grad()
        loss = loss_of(net(Xt), Ct, Bt)
        loss.backward()
        opt.step()
        if epoch % 10 == 0 or epoch == args.epochs - 1:
            net.eval()
            with torch.no_grad():
                out = net(Xv)
                lv = float(loss_of(out, Cv, Bv))
                ps = torch.softmax(out[:, :4], 1)[:, 0].numpy()
            score = balanced(ps >= 0.5, cls[test] == 0) - 0.01 * lv
            if score > best:
                best, best_epoch = score, epoch
                best_state = {k: v.clone() for k, v in net.state_dict().items()}
            if epoch % 100 == 0 or epoch == args.epochs - 1:
                print(f"epoch {epoch:4d} train {float(loss.detach()):.3f} heldout {lv:.3f} (best score {best:.3f} at {best_epoch})", flush=True)
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        out = net(torch.tensor(X))
        P = torch.softmax(out[:, :4], 1).numpy()
        PC = torch.sigmoid(out[:, 4]).numpy()
    metrics = {}
    for split, m in (("train", train), ("heldout", test)):
        pred4 = P[m].argmax(1)
        metrics[f"outcome4/{split}"] = {"n": int(m.sum()), "acc": round(float((pred4 == cls[m]).mean()), 3)}
        metrics[f"success_vs_not/{split}"] = {"n": int(m.sum()), "acc": round(float(((P[m, 0] >= 0.5) == (cls[m] == 0)).mean()), 3),
                                               "balanced_acc": round(balanced(P[m, 0] >= 0.5, cls[m] == 0), 3)}
        metrics[f"crossed/{split}"] = {"n": int(m.sum()), "acc": round(float(((PC[m] >= 0.5) == crossed[m]).mean()), 3),
                                        "balanced_acc": round(balanced(PC[m] >= 0.5, crossed[m]), 3)}
    from crab_help import ACTIONS

    def lines_for(mask):
        """(smile, trouble): 80% of the moves that ended well above the smile line, 80% of the failed ones below
        the trouble line, on the held-out samples in `mask`."""
        good, bad = mask & (cls == 0), mask & (cls != 0)
        smile = float(np.percentile(P[good, 0], 20)) if good.any() else 0.6
        trouble = float(np.percentile(P[bad, 0], 80)) if bad.any() else 0.4
        if trouble >= smile - 0.05:
            trouble = max(0.05, smile - 0.10)
        return round(smile, 3), round(trouble, 3)

    thr_smile, thr_trouble = lines_for(test)
    # per skill: the net's p_success runs on a different scale for each move (SEAT that ends seated averages 0.35,
    # PUSH that reaches the deck 0.99), so the face reads each move against its own lines
    by_skill = {ACTIONS[k]: lines_for(test & (skill == k)) for k in range(N_SKILLS) if (test & (skill == k)).any()}
    by = {}
    for i in np.where(test)[0]:
        by.setdefault((int(skill[i]), str(res[i])), []).append(P[i])
    out_dir = os.path.join(ROOT, "out", "manager_runs", args.out)
    os.makedirs(out_dir, exist_ok=True)
    torch.save(net.state_dict(), os.path.join(out_dir, "mood_net.pt"))
    meta = {"data": args.data, "n_samples": int(len(X)), "n_episodes": int(ep.max() + 1), "n_in": int(X.shape[1]),
            "n_out": 5, "hidden": args.hidden, "epochs": args.epochs, "best_epoch": best_epoch,
            "obs_mean": mean.tolist(), "obs_std": std.tolist(), "t_scale": T_SCALE,
            "outputs": ["p_success", "p_stall", "p_fall", "p_nothing", "p_cross"], "classes": list(CLASSES),
            "thr_smile": thr_smile, "thr_trouble": thr_trouble,
            "thr_smile_by_skill": {k: v[0] for k, v in by_skill.items()}, "thr_trouble_by_skill": {k: v[1] for k, v in by_skill.items()},
            "metrics": metrics, "train_s": round(time.perf_counter() - t0, 1)}
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines = [f"# 気分ネット（{args.out}）— {len(X)} サンプル、{int(ep.max() + 1)} 話、53-{args.hidden}-{args.hidden}-5、{best_epoch} エポック目", "",
             f"にっこりの線 {thr_smile:.2f}（見送り分でうまく終わった手の 8 割がこの上）、困りの線 {thr_trouble:.2f}（失敗した手の 8 割がこの下）", "",
             "スキルごとの線（にっこり／困り）：" + "、".join(f"{k} {v[0]:.2f}／{v[1]:.2f}" for k, v in by_skill.items()), "",
             "| 指標 | 分割 | n | 正解率 | 均衡正解率 |", "|---|---|---|---|---|"]
    for k, v in metrics.items():
        lines.append(f"| {k.split('/')[0]} | {k.split('/')[1]} | {v['n']} | {v['acc']} | {v.get('balanced_acc', '')} |")
    lines += ["", "## 見送り分：スキルと結末ごとの推論（成功／止まる／転ばせる／空振り の平均）", "",
              "| スキル | 結末 | n | 成功 | 止まる | 転ばせる | 空振り |", "|---|---|---|---|---|---|---|"]
    for (sk, r), ps in sorted(by.items()):
        a = np.mean(ps, axis=0)
        lines.append(f"| {ACTIONS[sk]} | {r} | {len(ps)} | {a[0]:.2f} | {a[1]:.2f} | {a[2]:.2f} | {a[3]:.2f} |")
    open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("wrote", out_dir)


if __name__ == "__main__":
    main()
