"""List the failed episodes of an eval_<policy>.json: scenario, falls, stage at the end, last actions/results."""
import json
import sys
recs = json.load(open(sys.argv[1], encoding="utf-8"))
for r in recs:
    if r["success"]:
        continue
    tail = list(zip(r["actions"], r["results"]))
    head = tail[:6]
    last = tail[-3:]
    print(f"seed {r['seed']} {r['scenario']}/{r['crab']} falls={r['falls']} pushes={r['pushes']} landed={r['landed']} "
          f"end={r['stage_end']} steps={r['steps']} sim={r['sim_s']:.0f}s dmg={r['course_damage_m']:.3f}")
    print("    first:", " ".join(f"{a}:{b}" for a, b in head))
    print("    last :", " ".join(f"{a}:{b}" for a, b in last))
