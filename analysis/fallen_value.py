"""Return-to-go by next action after a push that dropped the duck (PUSH -> fell: the crab is touching a fallen duck).

For the PPO training logs: per next action, n, mean undiscounted and discounted (0.99/step) sum of rewards over the
rest of the episode, mean immediate reward, and the crossing rate.  This is the signal PPO has to separate
BACK_OFF from the futile SEAT / STANDUP / WAIT in that state.
"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

RUNS = Path(r"D:\IslandMaster\mujoco_3body\out\manager_runs")
ACTS = ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]


def episodes(run):
    out = []
    for f in sorted(glob.glob(str(RUNS / run / "train_env*.jsonl"))):
        recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        cur, last = [], None
        for r in recs:
            if cur and r["episode"] != last:
                out.append(cur)
                cur = []
            cur.append(r)
            last = r["episode"]
        if cur:
            out.append(cur)
    return out


def table(label, eps, pick):
    g = defaultdict(list)
    for ep in eps:
        for i in range(len(ep) - 1):
            if pick(ep, i):
                a = ep[i + 1]["action"]
                rew = [r["reward"] for r in ep[i + 1:]]
                G = sum(rew)
                Gd = sum(r * 0.99 ** k for k, r in enumerate(rew))
                g[a].append((G, Gd, rew[0], ep[-1]["success"], len(rew)))
    print(f"\n== {label}")
    print(f"  {'next':9s} {'n':>4s} {'G':>7s} {'G0.99':>7s} {'r_now':>6s} {'cross':>6s} {'steps left':>10s}")
    for a in ACTS:
        v = g[a]
        if not v:
            continue
        n = len(v)
        print(f"  {a:9s} {n:4d} {sum(x[0] for x in v) / n:7.2f} {sum(x[1] for x in v) / n:7.2f} {sum(x[2] for x in v) / n:6.2f} "
              f"{sum(x[3] for x in v) / n:6.2f} {sum(x[4] for x in v) / n:10.1f}")


if __name__ == "__main__":
    for run in sys.argv[1:] or ["ppo2_medium2", "ppo2_medium3"]:
        eps = episodes(run)
        table(f"{run}: after PUSH -> fell (crab touching a fallen duck)", eps,
              lambda ep, i: ep[i]["action"] == "PUSH" and ep[i]["result"] == "fell")
        table(f"{run}: after PUSH -> stalled while touching (push/settle phase)", eps,
              lambda ep, i: ep[i]["action"] == "PUSH" and ep[i]["result"] == "stalled" and ep[i].get("push_phase") in ("push", "settle"))
        table(f"{run}: any FALLEN state where the previous result was not 'cleared' (crab likely still close)", eps,
              lambda ep, i: ep[i + 1]["duck_before"] == "FALLEN" and ep[i]["result"] != "cleared")
