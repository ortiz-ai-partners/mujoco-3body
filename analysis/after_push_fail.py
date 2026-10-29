"""What does each manager do right after a PUSH that failed (stalled / slipped / fell)?

Sources:
  * eval decision logs (deterministic, 30 shared seeds): rule + random (baselines_v2, split where the episode
    counter restarts), tabq (tabq2_small), ppo (ppo2_medium2)
  * training logs of the PPO runs, per quintile (ppo2_medium2 complete, ppo2_medium3 so far)

For every PUSH with a failing result: the next action in the same episode, broken down by the push phase in which
the push ended (behind/align/approach = the crab never touched; push/settle = it was touching), the result of
that next action, and whether the episode ended in a crossing.  Then, for FALLEN states: what follows a BACK_OFF
that cleared (does the duck get up on its own?).
"""
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "out" / "manager_runs"
ACTS = ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]
FAIL = ("stalled", "slipped", "fell")


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def split_episodes(recs):
    """Group consecutive records by episode; a restart of the counter starts a new block."""
    eps, cur, last_ep = [], [], None
    for r in recs:
        if cur and r["episode"] != last_ep:
            eps.append(cur)
            cur = []
        cur.append(r)
        last_ep = r["episode"]
    if cur:
        eps.append(cur)
    return eps


def split_policies(recs, n_per_policy=30):
    eps = split_episodes(recs)
    return [sum(eps[i:i + n_per_policy], []) for i in range(0, len(eps), n_per_policy)]


def report(label, eps):
    nxt = defaultdict(Counter)          # phase group -> next action
    nxt_res = defaultdict(Counter)      # (next action) -> its result
    outcome = defaultdict(Counter)      # next action -> episode crossed?
    n_fail = Counter()
    for ep in eps:
        crossed = ep[-1]["success"]
        for i, r in enumerate(ep):
            if r["action"] == "PUSH" and r["result"] in FAIL:
                touching = r.get("push_phase") in ("push", "settle") or r["result"] == "fell"
                grp = f"{r['result']}/{'touching' if touching else 'not touching'}"
                n_fail[grp] += 1
                if i + 1 < len(ep):
                    a = ep[i + 1]["action"]
                    nxt[grp][a] += 1
                    nxt_res[a][ep[i + 1]["result"]] += 1
                    outcome[a]["crossed" if crossed else "failed"] += 1
                else:
                    nxt[grp]["(episode ended)"] += 1
    tot = sum(n_fail.values())
    print(f"\n== {label}: {tot} failed pushes in {len(eps)} episodes")
    for grp in sorted(nxt):
        c = nxt[grp]
        print(f"  after {grp:22s} n={sum(c.values()):3d}  " + "  ".join(f"{a}:{c[a]}" for a in ACTS + ["(episode ended)"] if c[a]))
    for a in ACTS:
        if nxt_res[a]:
            print(f"     next {a:8s} -> " + "  ".join(f"{k}:{v}" for k, v in nxt_res[a].most_common())
                  + f"   | episode crossed {outcome[a]['crossed']}/{sum(outcome[a].values())}")
    # fallen + BACK_OFF cleared: what happens next
    after_clear = Counter()
    after_clear_res = Counter()
    for ep in eps:
        for i, r in enumerate(ep):
            if r["action"] == "BACK_OFF" and r["result"] == "cleared" and r["duck_before"] == "FALLEN" and i + 1 < len(ep):
                after_clear[ep[i + 1]["action"]] += 1
                after_clear_res[(ep[i + 1]["action"], ep[i + 1]["result"])] += 1
    if after_clear:
        print(f"  fallen duck, BACK_OFF cleared -> next: " + "  ".join(f"{a}:{n}" for a, n in after_clear.most_common())
              + " | results: " + "  ".join(f"{a}/{res}:{n}" for (a, res), n in after_clear_res.most_common(8)))


def quintiles(run, q=5):
    files = sorted(glob.glob(str(RUNS / run / "train_env*.jsonl")))
    per_env = [load(f) for f in files]
    n = max(len(r) for r in per_env)
    for i in range(q):
        lo, hi = round(i * n / q), round((i + 1) * n / q)
        eps = []
        for recs in per_env:
            eps += split_episodes(recs[lo:hi])
        report(f"{run} training Q{i + 1} (decisions {lo}-{hi} per env)", eps)


if __name__ == "__main__":
    which = sys.argv[1:] or ["eval", "ppo2_medium2", "ppo2_medium3"]
    if "eval" in which:
        rule, random_ = split_policies(load(RUNS / "baselines_v2" / "eval_decisions.jsonl"))[:2]
        report("rule (eval, 30 seeds)", split_episodes(rule))
        report("random (eval, 30 seeds)", split_episodes(random_))
        report("tabq2_small (eval, 30 seeds)", split_episodes(load(RUNS / "tabq2_small" / "eval_decisions.jsonl")))
        report("ppo2_medium2 (eval, 30 seeds)", split_episodes(load(RUNS / "ppo2_medium2" / "eval_decisions.jsonl")))
    for run in which:
        if run != "eval":
            quintiles(run)
