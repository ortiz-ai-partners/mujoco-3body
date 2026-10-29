"""How often does the whole story succeed?  Many headless full runs (construction included) from slightly different starts.

    python analysis/fullrun_stats.py --runs 30 --workers 10                   -> out/fullrun_stats/ppo2_v22/
    python analysis/fullrun_stats.py --manager rule --name rule --runs 30     -> out/fullrun_stats/rule/

Each run is `v7_full.py --test` (no render) with the submitted settings and its own seed s (from --seed0): `--seed s` draws
where the duck and the crab wander and when they cry, `--spawn-jitter s` offsets the three robots' starting poses (BZ by up
to 2 cm and 2 deg, the duck and the crab by up to 5 cm and 10 deg) before the first step.  Nothing else changes; nothing
moves a robot during a run.  The course pieces start where they always do.

A run succeeds when BZ, the crab and the duck have all crossed (the report's `three_crossed`) and no course piece moved more
than 4 cm (`course_disturbed` empty).  The per-run reports go to the output folder (run_<s>.json, run_<s>.log) and the tally to
summary.json / summary.md.  A run already in the folder is not run again (delete it to redo it).

Note: a headless run does not do the per-frame forward pass of a render, so its physics path is not the one of the rendered
video with the same settings (docs/devlog/HANDOVER.md, section 0b); the statistics are over valid physics runs of the same
story, not over renders.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def run_one(seed, args, folder):
    rep = folder / f"run_{seed}.json"
    if rep.exists():
        return seed, "cached", 0.0
    tag = f"_fullstat_{args.name}_{seed}"
    cmd = [sys.executable, str(ROOT / "v7_full.py"), "--test", "--manager", args.manager, "--seed", str(seed),
           "--spawn-jitter", str(seed)]
    if args.manager != "rule":
        cmd += ["--run", args.run]
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONIOENCODING="utf-8")
    t0 = time.perf_counter()
    with open(folder / f"run_{seed}.log", "w", encoding="utf-8") as log:
        res = subprocess.run(cmd + ["--tag", tag], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
    src = OUT / f"v7_full_report{tag}.json"
    if res.returncode == 0 and src.exists():
        src.replace(rep)
        return seed, "ok", time.perf_counter() - t0
    return seed, f"rc={res.returncode}", time.perf_counter() - t0


def outcome(r):
    tc, dist = r["three_crossed"], r["course_disturbed"]
    falls = sum(1 for e in r["events"] if e["event"].startswith("MD fell"))
    if not r["construction"]["success"]:
        why = f"construction: {r['construction']['reason']}"
    elif dist:
        why = "course moved: " + ", ".join(f"{k} {v} m" for k, v in dist.items())
    elif not tc["crab"]:
        why = "crab did not cross"
    elif not tc["duck"]:
        why = "duck did not cross (" + " > ".join(f"{d['action']}:{d.get('result', '途中')}" for d in r["manager"]["decisions"]) + ")"
    else:
        why = ""
    return {"success": bool(tc["bz"] and tc["crab"] and tc["duck"] and not dist), "bz": tc["bz"], "crab": tc["crab"],
            "duck": tc["duck"], "course_disturbed": dist, "duck_falls": falls, "moves": len(r["manager"]["decisions"]),
            "sim_s": r["sim_seconds"], "why": why}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--seed0", type=int, default=7000)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--manager", choices=["rule", "ppo", "tabq"], default="ppo")
    ap.add_argument("--run", default="ppo2_v22", help="the learned manager (out/manager_runs/<run>/)")
    ap.add_argument("--name", default=None, help="output folder name (default: the run, or the manager for rule)")
    args = ap.parse_args()
    args.name = args.name or (args.run if args.manager != "rule" else args.manager)
    folder = OUT / "fullrun_stats" / args.name
    folder.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.seed0, args.seed0 + args.runs))
    with ThreadPoolExecutor(args.workers) as pool:
        for seed, status, wall in pool.map(lambda s: run_one(s, args, folder), seeds):
            print(f"seed {seed}: {status} ({wall:.0f} s)", flush=True)

    rows = {}
    for s in seeds:
        p = folder / f"run_{s}.json"
        if p.exists():
            rows[s] = outcome(json.load(open(p, encoding="utf-8")))
    n, ok = len(rows), sum(r["success"] for r in rows.values())
    summary = {"manager": args.manager, "run": args.run if args.manager != "rule" else None, "seeds": [seeds[0], seeds[-1]],
               "runs": n, "success": ok, "bz_crossed": sum(r["bz"] for r in rows.values()),
               "crab_crossed": sum(r["crab"] for r in rows.values()), "duck_crossed": sum(r["duck"] for r in rows.values()),
               "course_disturbed": sum(bool(r["course_disturbed"]) for r in rows.values()),
               "runs_with_duck_falls": sum(r["duck_falls"] > 0 for r in rows.values()),
               "bz_yaw_deg": {s: round(math.degrees(json.load(open(folder / f"run_{s}.json", encoding="utf-8"))["settings"]["spawn"]["bz_offset"][2]), 2)
                              for s in rows},
               "per_run": rows}
    (folder / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = [f"# 通しの成功数 — {args.manager}{'（' + args.run + '）' if args.manager != 'rule' else ''}、{n} 回（シード {seeds[0]}〜{seeds[-1]}）", "",
             f"3 体とも渡り切り・コースの部材が動かない：**{ok}/{n}**。BZ {summary['bz_crossed']}、跳跳 {summary['crab_crossed']}、"
             f"パッカン {summary['duck_crossed']}、部材の移動 {summary['course_disturbed']} 回、パッカンが転んだ回 {summary['runs_with_duck_falls']}。", "",
             "| シード | 成否 | 手数 | パッカンの転倒 | sim s | 失敗の所 |", "|---|---|---|---|---|---|"]
    for s, r in rows.items():
        lines.append(f"| {s} | {'成功' if r['success'] else '失敗'} | {r['moves']} | {r['duck_falls']} | {r['sim_s']} | {r['why']} |")
    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
