"""Train the crab's mood net: the second AI that infers, at any control step of a rescue, "will this move end well?"
and "will the duck get across?" (crab_face.MoodAI, ゆうころ 10/28 夜「本物の推論で 2 つの AI」).

Data: out/manager_runs/mood_data.npz from analysis/mood_data.py (the manager's 46-dim observation every 0.1 s inside
every skill, which skill, how long it has run, how it ended, whether the episode ended crossed).  Features: the
observation (standardised) + the skill one-hot (6) + time in the skill (/60 s) = 53.  Net: 53-32-32-2, tanh, two
sigmoid outputs trained with BCE.  Episodes are split by id (every 4th held out) so the numbers below are on moves
the net never saw.

    python analysis/mood_train.py --data mood_data --out mood_net
    -> out/manager_runs/mood_net/mood_net.pt, meta.json (normalisation, layout, metrics), report.md
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


def features(obs, skill, t_in_skill, mean, std):
    """The mood net's input from the manager's observation, the running skill and its elapsed time."""
    obs = (np.asarray(obs, np.float32) - mean) / std
    oh = np.zeros((obs.shape[0], N_SKILLS), np.float32) if obs.ndim == 2 else np.zeros(N_SKILLS, np.float32)
    if obs.ndim == 2:
        oh[np.arange(obs.shape[0]), np.asarray(skill, np.int64)] = 1.0
        ts = (np.minimum(np.asarray(t_in_skill, np.float32), T_SCALE) / T_SCALE)[:, None]
        return np.concatenate([obs, oh, ts], axis=1)
    oh[int(skill)] = 1.0
    return np.concatenate([obs, oh, [min(float(t_in_skill), T_SCALE) / T_SCALE]]).astype(np.float32)


class MoodNet(torch.nn.Module):
    def __init__(self, n_in=46 + N_SKILLS + 1, hidden=32):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(n_in, hidden), torch.nn.Tanh(), torch.nn.Linear(hidden, hidden),
                                       torch.nn.Tanh(), torch.nn.Linear(hidden, 2))

    def forward(self, x):
        return self.net(x)


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
    obs, skill, ts, ok, crossed, ep = d["obs"], d["skill"], d["t_in_skill"], d["ok"], d["crossed"], d["episode"]
    mean, std = obs.mean(0), obs.std(0) + 1e-6
    X = features(obs, skill, ts, mean, std)
    Y = np.stack([ok, crossed], 1).astype(np.float32)
    test = (ep % 4) == 3
    train = ~test
    Xt, Yt = torch.tensor(X[train]), torch.tensor(Y[train])
    Xv, Yv = torch.tensor(X[test]), torch.tensor(Y[test])
    net = MoodNet(X.shape[1], args.hidden)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    t0 = time.perf_counter()
    best, best_epoch, best_state = -float("inf"), -1, None
    for epoch in range(args.epochs):
        net.train()
        opt.zero_grad()
        loss = loss_fn(net(Xt), Yt)
        loss.backward()
        opt.step()
        if epoch % 10 == 0 or epoch == args.epochs - 1:
            net.eval()
            with torch.no_grad():
                lv = float(loss_fn(net(Xv), Yv))
            with torch.no_grad():                              # the epoch is chosen by the held-out balanced accuracy of
                pv = torch.sigmoid(net(Xv))[:, 0] >= 0.5        # "the move ends well" (BCE picked epoch 50, a soft net:
                yv = Yv[:, 0] > 0.5                             # pushed_up 0.80 vs fell 0.49; 800 epochs straight gave
                tpr = float(pv[yv].float().mean())              # 1.00 vs 0.00 but overconfident errors)
                tnr = float((~pv[~yv]).float().mean())
                score = (tpr + tnr) / 2 - 0.01 * lv
            if score > best:
                best, best_epoch = score, epoch
                best_state = {k: v.clone() for k, v in net.state_dict().items()}
            if epoch % 100 == 0 or epoch == args.epochs - 1:
                print(f"epoch {epoch:4d} train {float(loss.detach()):.3f} heldout bce {lv:.3f} (best score {best:.3f} at {best_epoch})", flush=True)
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        P = torch.sigmoid(net(torch.tensor(X))).numpy()
    metrics = {}
    for j, name in enumerate(("skill_ok", "crossed")):
        for split, m in (("train", train), ("heldout", test)):
            p, y = P[m, j], Y[m, j] > 0.5
            pred = p >= 0.5
            acc = float((pred == y).mean())
            tpr = float(pred[y].mean()) if y.any() else float("nan")
            tnr = float((~pred[~y]).mean()) if (~y).any() else float("nan")
            metrics[f"{name}/{split}"] = {"n": int(m.sum()), "acc": round(acc, 3), "balanced_acc": round((tpr + tnr) / 2, 3),
                                          "mean_p_when_true": round(float(p[y].mean()), 3) if y.any() else None,
                                          "mean_p_when_false": round(float(p[~y].mean()), 3) if (~y).any() else None}
    # p(skill ok) by skill and eventual result, held out: the discrimination the face will show
    res = d["result"]
    by = {}
    for i in np.where(test)[0]:
        by.setdefault((int(skill[i]), str(res[i])), []).append(float(P[i, 0]))
    out_dir = os.path.join(ROOT, "out", "manager_runs", args.out)
    os.makedirs(out_dir, exist_ok=True)
    torch.save(net.state_dict(), os.path.join(out_dir, "mood_net.pt"))
    meta = {"data": args.data, "n_samples": int(len(X)), "n_episodes": int(ep.max() + 1), "n_in": int(X.shape[1]),
            "hidden": args.hidden, "epochs": args.epochs, "obs_mean": mean.tolist(), "obs_std": std.tolist(),
            "t_scale": T_SCALE, "outputs": ["p_skill_ok", "p_crossed"], "metrics": metrics,
            "best_epoch": best_epoch, "best_heldout_score": round(best, 4),
            "train_s": round(time.perf_counter() - t0, 1)}
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from crab_help import ACTIONS
    lines = [f"# 気分ネット（{args.out}）— {len(X)} サンプル、{int(ep.max() + 1)} 話、53-{args.hidden}-{args.hidden}-2", "",
             "| 出力 | 分割 | n | 正解率 | 均衡正解率 | p（真のとき） | p（偽のとき） |", "|---|---|---|---|---|---|---|"]
    for k, v in metrics.items():
        lines.append(f"| {k.split('/')[0]} | {k.split('/')[1]} | {v['n']} | {v['acc']} | {v['balanced_acc']} | {v['mean_p_when_true']} | {v['mean_p_when_false']} |")
    lines += ["", "## 見送り分：スキルと結末ごとの p(スキルがうまく終わる)", "", "| スキル | 結末 | n | p の平均 |", "|---|---|---|---|"]
    for (sk, r), ps in sorted(by.items()):
        lines.append(f"| {ACTIONS[sk]} | {r} | {len(ps)} | {np.mean(ps):.2f} |")
    open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("wrote", out_dir)


if __name__ == "__main__":
    main()
