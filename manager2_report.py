"""Compare the manager policies on the shared evaluation seeds and attribute failures.

    <jumper venv python> manager2_report.py --runs ppo2_small baselines_v2 tabq2_small

Reads out/manager_runs/<run>/eval_<policy>.json (written by manager2_train.py eval / manager2_tabq.py eval),
prints a markdown table (crossing rate, landing rate, time, decisions, falls, pushes, wasted actions, course
damage, per-scenario crossings) and the per-seed 2x2 attribution against the fixed-rule policy:
  rule crossed & policy crossed      -> both fine
  rule crossed & policy failed       -> the policy's decisions lost a solvable start (decision failure)
  rule failed  & policy crossed      -> the policy found a way the rules did not
  rule failed  & policy failed       -> the start defeated the skills either way (skill failure, e.g. the seam)
Writes out/manager_runs/comparison_v2.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from crab_help import ACTIONS
from manager2_env import SCENARIOS
from v6_common import OUT_DIR

RUNS = OUT_DIR / "manager_runs"


def load(run, policy):
    p = RUNS / run / f"eval_{policy}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def metrics(recs):
    succ = [r for r in recs if r["success"]]
    return {
        "episodes": len(recs),
        "crossing_rate": len(succ) / len(recs),
        "landing_rate": sum(r["landed"] for r in recs) / len(recs),
        "median_time_s": float(np.median([r["sim_s"] for r in succ])) if succ else float("nan"),
        "mean_return": float(np.mean([r["return"] for r in recs])),
        "mean_steps": float(np.mean([r["steps"] for r in recs])),
        "mean_falls": float(np.mean([r["falls"] for r in recs])),
        "mean_pushes": float(np.mean([r["pushes"] for r in recs])),
        "wasted_per_episode": float(np.mean([r["results"].count("nothing") for r in recs])),
        "course_damaged": sum(r["course_damaged"] for r in recs),
        "by_scenario": {sc: (sum(1 for r in recs if r["scenario"] == sc and r["success"]),
                             sum(1 for r in recs if r["scenario"] == sc)) for sc, _ in SCENARIOS},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=["ppo2_small", "baselines_v2", "tabq2_small"])
    ap.add_argument("--name", default="comparison_v2", help="output file name under out/manager_runs/ (without .md)")
    args = ap.parse_args()
    table = {}
    for run in args.runs:
        for policy in ("ppo", "rule", "random", "tabq"):
            recs = load(run, policy)
            if not recs:
                continue
            # the same policy kind from several runs (e.g. ppo small / medium) gets one row each
            label = policy if policy not in table else f"{policy} {run}"
            if label not in table:
                table[label] = (run, recs)
    if not table:
        print("no eval_*.json found")
        return
    lines = ["# 支配人 v2 — 同一シード評価の比較", ""]
    lines.append("| 方策 | run | 渡り切り | 天面到達 | 中央時間 s | 平均リターン | 手数 | 転倒 | 押し上げ | 無駄な手 | コース破損 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for policy, (run, recs) in table.items():
        m = metrics(recs)
        lines.append(f"| {policy} | {run} | {m['crossing_rate']:.0%} ({int(m['crossing_rate'] * m['episodes'])}/{m['episodes']}) | "
                     f"{m['landing_rate']:.0%} | {m['median_time_s']:.0f} | {m['mean_return']:+.2f} | {m['mean_steps']:.1f} | "
                     f"{m['mean_falls']:.2f} | {m['mean_pushes']:.2f} | {m['wasted_per_episode']:.2f} | {m['course_damaged']} |")
    lines += ["", "## 開始場面ごとの渡り切り（渡った／出た数）", ""]
    lines.append("| 場面 | " + " | ".join(table) + " |")
    lines.append("|---|" + "---|" * len(table))
    for sc, _ in SCENARIOS:
        row = [f"{metrics(recs)['by_scenario'][sc][0]}/{metrics(recs)['by_scenario'][sc][1]}" for _, recs in table.values()]
        lines.append(f"| {sc} | " + " | ".join(row) + " |")
    lines += ["", "## 行動の使用回数", ""]
    lines.append("| 方策 | " + " | ".join(ACTIONS) + " |")
    lines.append("|---|" + "---|" * len(ACTIONS))
    for policy, (run, recs) in table.items():
        lines.append(f"| {policy} | " + " | ".join(str(sum(r["actions"].count(a) for r in recs)) for a in ACTIONS) + " |")
    if "rule" in table:
        rule = {r["seed"]: r for r in table["rule"][1]}
        lines += ["", "## 失敗の帰属（固定ルールとの 2×2、同一シード）", ""]
        lines.append("| 方策 | 両方渡った | ルールは渡ったが方策は失敗（判断の失敗） | 方策だけ渡った | 両方失敗（スキルの失敗） |")
        lines.append("|---|---|---|---|---|")
        for policy, (run, recs) in table.items():
            if policy.startswith("rule"):
                continue
            cells = [0, 0, 0, 0]
            for r in recs:
                base = rule.get(r["seed"])
                if base is None:
                    continue
                idx = 0 if (base["success"] and r["success"]) else 1 if base["success"] else 2 if r["success"] else 3
                cells[idx] += 1
            lines.append(f"| {policy} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    text = "\n".join(lines) + "\n"
    (RUNS / f"{args.name}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
