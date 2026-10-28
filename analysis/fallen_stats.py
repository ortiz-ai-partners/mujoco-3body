"""What did the PPO run do when the duck was FALLEN (per training quintile), and how did it end?

Also: SEAT outcomes by where the duck sat (x offset from the lane), and the 'seated' results that
were off the lane, from the eval decision logs if present.
"""
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

run_dir = Path(sys.argv[1])
files = sorted(glob.glob(str(run_dir / "train_env*.jsonl")))
per_env = [[json.loads(l) for l in open(f, encoding="utf-8") if l.strip()] for f in files]
n = max(len(r) for r in per_env)
q = 5
print(f"{run_dir.name}: decisions with duck FALLEN before the action, per quintile")
for i in range(q):
    lo, hi = round(i * n / q), round((i + 1) * n / q)
    acts = Counter()
    res = defaultdict(Counter)
    for recs in per_env:
        for r in recs[lo:hi]:
            if r["duck_before"] == "FALLEN":
                acts[r["action"]] += 1
                res[r["action"]][r["result"]] += 1
    tot = sum(acts.values())
    print(f"  Q{i + 1} n={tot:4d}  " + "  ".join(f"{a}:{acts[a]}" for a in ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]))
    for a in ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]:
        if res[a]:
            print(f"       {a:8s} " + "  ".join(f"{k}:{v}" for k, v in res[a].most_common()))

# runs of still_down (the same action repeated while the duck stays down)
print("\nlongest runs of consecutive 'still_down' results per quintile (episodes with >=3):")
for i in range(q):
    lo, hi = round(i * n / q), round((i + 1) * n / q)
    runs = []
    for recs in per_env:
        cur = 0
        for r in recs[lo:hi]:
            if r["result"] == "still_down":
                cur += 1
            else:
                if cur >= 3:
                    runs.append(cur)
                cur = 0
        if cur >= 3:
            runs.append(cur)
    print(f"  Q{i + 1}: {len(runs)} runs, max {max(runs) if runs else 0}, mean {sum(runs) / len(runs) if runs else 0:.1f}")
