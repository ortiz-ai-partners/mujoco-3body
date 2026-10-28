"""Skill reliability from eval_<policy>.json files: outcome counts per action."""
import json
import sys
from collections import Counter, defaultdict
for path in sys.argv[1:]:
    recs = json.load(open(path, encoding="utf-8"))
    stats = defaultdict(Counter)
    for r in recs:
        for a, res in zip(r["actions"], r["results"]):
            stats[a][res] += 1
    print(path)
    for a, c in stats.items():
        total = sum(c.values())
        print(f"  {a:8s} n={total:3d}  " + "  ".join(f"{k}:{v}" for k, v in c.most_common()))
