"""Tabular Q-learning manager on the v2 environment - the comparison baseline for the PPO (MLP) manager.

    <jumper venv python> manager2_tabq.py train --episodes 120 --run tabq2_small
    <jumper venv python> manager2_tabq.py eval  --run tabq2_small --episodes 30 --seed0 5000

The observation is discretised to a small key (last result x duck state x stage x facing ok x at the seat x
crab close x pushes); Q-learning with epsilon-greedy exploration.  Single process (one scene), about
40 s of wall time per episode.  It answers "would a table have done as well as the MLP?" on the shared
evaluation seeds, and is the fallback should PPO not learn within budget.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from crab_help import ACTIONS, RESULT_SLOTS
from manager2_env import ManagerEnv, Scene, run_episodes, summarize
from v6_common import OUT_DIR

RUNS = OUT_DIR / "manager_runs"


def state_key(scene: Scene) -> str:
    h = scene.h
    res = scene.last_result if scene.last_result in RESULT_SLOTS else "none"
    mode = scene.duck.mode if scene.duck.mode in ("SIT", "STAND", "FALLEN") else "other"
    close = int(h.touching() or h.crab_dist() < 0.5)
    return f"{res}|{mode}|{h.stage()}|f{int(h.facing_ok())}|s{int(h.at_seat())}|c{close}|n{min(scene.pushes, 2)}"


class TabQ:
    def __init__(self, alpha=0.2, gamma=0.95):
        self.q = defaultdict(lambda: [0.0] * len(ACTIONS))
        self.alpha, self.gamma = alpha, gamma

    def act(self, key, eps, rng):
        if rng.uniform() < eps:
            return int(rng.integers(len(ACTIONS)))
        q = self.q[key]
        best = max(q)
        return int(rng.choice([i for i, v in enumerate(q) if v == best]))

    def update(self, key, a, r, key2, done):
        target = r if done else r + self.gamma * max(self.q[key2])
        self.q[key][a] += self.alpha * (target - self.q[key][a])

    def save(self, path):
        Path(path).write_text(json.dumps({k: [round(v, 4) for v in vals] for k, vals in self.q.items()},
                                         ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path):
        obj = cls()
        for k, vals in json.loads(Path(path).read_text(encoding="utf-8")).items():
            obj.q[k] = list(vals)
        return obj


def train(args):
    run_dir = RUNS / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    env = ManagerEnv(seed=200, max_episode_s=args.max_episode_s, log_path=run_dir / "train_decisions.jsonl")
    agent = TabQ(alpha=args.alpha, gamma=args.gamma)
    rng = np.random.default_rng(args.seed)
    curve = []
    t0 = time.perf_counter()
    for ep in range(args.episodes):
        eps = max(args.eps_end, args.eps_start * (1 - ep / max(1, args.episodes * 0.7)))
        obs, _ = env.reset(seed=300 + ep)
        key = state_key(env.scene)
        total, done, steps = 0.0, False, 0
        while not done:
            a = agent.act(key, eps, rng)
            obs, r, term, trunc, info = env.step(a)
            done = term or trunc
            key2 = state_key(env.scene)
            agent.update(key, a, r, key2, done)
            key = key2
            total += r
            steps += 1
        curve.append({"episode": ep, "scenario": env.scene.draw["scenario"], "return": round(total, 2), "steps": steps,
                      "success": bool(info["success"]), "landed": bool(info.get("landed")), "eps": round(eps, 3),
                      "wall_s": round(time.perf_counter() - t0, 1)})
        print(json.dumps(curve[-1]), flush=True)
        if (ep + 1) % 10 == 0:
            agent.save(run_dir / "tabq.json")
            (run_dir / "train_curve.json").write_text(json.dumps(curve, indent=1), encoding="utf-8")
    agent.save(run_dir / "tabq.json")
    (run_dir / "train_curve.json").write_text(json.dumps(curve, indent=1), encoding="utf-8")
    print(json.dumps({"run": args.run, "episodes": args.episodes, "states": len(agent.q),
                      "train_success_rate": round(sum(c["success"] for c in curve) / max(1, len(curve)), 3),
                      "wall_s": round(time.perf_counter() - t0, 1)}, indent=1))


def evaluate(args):
    run_dir = RUNS / args.run
    out_dir = RUNS / (args.out or args.run)                # --out keeps an earlier evaluation of the same table
    out_dir.mkdir(parents=True, exist_ok=True)
    agent = TabQ.load(run_dir / "tabq.json")
    env = ManagerEnv(seed=0, max_episode_s=args.max_episode_s, log_path=out_dir / "eval_decisions.jsonl")
    rng = np.random.default_rng(1)
    recs = run_episodes(env, lambda o, s: agent.act(state_key(s), 0.0, rng), args.episodes, seed0=args.seed0)
    report = {"tabq": summarize(recs)}
    (out_dir / "eval_tabq.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "eval_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--run", default="tabq2_small")
    t.add_argument("--episodes", type=int, default=120)
    t.add_argument("--alpha", type=float, default=0.2)
    t.add_argument("--gamma", type=float, default=0.95)
    t.add_argument("--eps-start", type=float, default=0.3)
    t.add_argument("--eps-end", type=float, default=0.05)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--max-episode-s", type=float, default=240.0)
    e = sub.add_parser("eval")
    e.add_argument("--run", default="tabq2_small")
    e.add_argument("--episodes", type=int, default=30)
    e.add_argument("--seed0", type=int, default=5000)
    e.add_argument("--max-episode-s", type=float, default=240.0)
    e.add_argument("--out", help="output directory under out/manager_runs/ (default: the run's own)")
    args = ap.parse_args()
    train(args) if args.cmd == "train" else evaluate(args)


if __name__ == "__main__":
    main()
