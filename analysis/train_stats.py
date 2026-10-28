"""Training-record analysis for a manager2 PPO run.

Reads out/manager_runs/<run>/train_env*.jsonl (one record per decision, per env),
splits training time into quintiles by record index (envs step in lockstep under
SubprocVecEnv, so the index is a global step), and prints:
  * action mix per quintile
  * episode success / landed per quintile and per start scenario (first vs last quintile)
  * wasted actions and pushes per episode, first vs last quintile
"""
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

run_dir = Path(sys.argv[1])
files = sorted(glob.glob(str(run_dir / "train_env*.jsonl")))
per_env = []
for f in files:
    recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    per_env.append(recs)
n = max(len(r) for r in per_env)
q = 5
bounds = [round(i * n / q) for i in range(q + 1)]
print(f"{run_dir.name}: {len(per_env)} envs, {n} decisions per env")

# action mix per quintile
print("\naction mix per training quintile (all envs):")
for i in range(q):
    c = Counter()
    for recs in per_env:
        for r in recs[bounds[i]:bounds[i + 1]]:
            c[r["action"]] += 1
    tot = sum(c.values())
    print(f"  Q{i + 1} n={tot:5d}  " + "  ".join(f"{a}:{c[a] / tot * 100:4.0f}%" for a in ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]))

# episodes: group by (env, episode); episode belongs to the quintile of its last record
episodes = []
for e, recs in enumerate(per_env):
    by_ep = defaultdict(list)
    for idx, r in enumerate(recs):
        by_ep[r["episode"]].append((idx, r))
    for ep, items in by_ep.items():
        idx_last, last = items[-1]
        # a truncated final episode (training stopped) has no terminal flag; keep it anyway
        episodes.append({
            "env": e, "ep": ep, "quintile": min(q - 1, int(idx_last * q / n)),
            "success": last["success"], "landed": last["landed"],
            "scenario": last["draw"]["scenario"], "crab": last["draw"].get("crab"),
            "n_actions": len(items), "wasted": sum(r["wasted"] for _, r in items),
            "pushes": last["pushes"], "falls": last["falls"],
            "t_end": last["t"], "actions": [r["action"] for _, r in items],
            "results": [r["result"] for _, r in items],
            "damaged": any(r["course_damaged"] for _, r in items),
        })
print(f"\nepisodes: {len(episodes)} (incl. the truncated last one per env)")
print("per quintile: success / landed / wasted per ep / pushes per ep / actions per ep / course damaged:")
for i in range(q):
    eps = [x for x in episodes if x["quintile"] == i]
    if not eps:
        continue
    print(f"  Q{i + 1} eps={len(eps):3d}  success {sum(x['success'] for x in eps) / len(eps) * 100:4.0f}%  "
          f"landed {sum(x['landed'] for x in eps) / len(eps) * 100:4.0f}%  "
          f"wasted {sum(x['wasted'] for x in eps) / len(eps):5.2f}  pushes {sum(x['pushes'] for x in eps) / len(eps):4.2f}  "
          f"actions {sum(x['n_actions'] for x in eps) / len(eps):5.1f}  damaged {sum(x['damaged'] for x in eps)}")

print("\nper scenario, first quintile vs last quintile (success n/N):")
scen = sorted({x["scenario"] for x in episodes})
for s in scen:
    a = [x for x in episodes if x["scenario"] == s and x["quintile"] == 0]
    b = [x for x in episodes if x["scenario"] == s and x["quintile"] == q - 1]
    al = [x for x in episodes if x["scenario"] == s]
    print(f"  {s:20s} Q1 {sum(x['success'] for x in a):3d}/{len(a):3d}   Q5 {sum(x['success'] for x in b):3d}/{len(b):3d}   all {sum(x['success'] for x in al):3d}/{len(al):3d}")

print("\nskill reliability over the whole run (action -> result):")
stats = defaultdict(Counter)
for recs in per_env:
    for r in recs:
        stats[r["action"]][r["result"]] += 1
for a in ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]:
    c = stats[a]
    tot = sum(c.values())
    if tot:
        print(f"  {a:8s} n={tot:4d}  " + "  ".join(f"{k}:{v}" for k, v in c.most_common()))

print("\nmost common action sequences among successful episodes in the last quintile:")
seqs = Counter(" > ".join(x["actions"]) for x in episodes if x["quintile"] == q - 1 and x["success"])
for s, k in seqs.most_common(6):
    print(f"  {k:3d}x  {s}")
print("\nmost common action sequences among failed episodes in the last quintile:")
seqs = Counter(" > ".join(x["actions"][:8]) + (" ..." if len(x["actions"]) > 8 else "") for x in episodes if x["quintile"] == q - 1 and not x["success"])
for s, k in seqs.most_common(6):
    print(f"  {k:3d}x  {s}")
