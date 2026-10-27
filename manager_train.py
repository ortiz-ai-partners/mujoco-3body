"""Train and evaluate the manager (Island Master) with Stable-Baselines3 PPO on ManagerEnv.

    <jumper venv python> manager_train.py train --envs 8 --steps 1024 --run ppo_smoke
    <jumper venv python> manager_train.py eval  --run ppo_smoke --episodes 30

train: PPO, small MLP (64x64), parallel envs (one MuJoCo scene per process).  One env step is one
skill (5-110 simulated seconds), so `--steps` counts decisions, not simulator ticks.
eval: the trained policy, the fixed-rule policy and a random policy on the same seeds (same initial
docking error, same crab placement), with recovery rate, time, wasted retries and collisions.
Everything is written under out/manager_runs/<run>/ (model, decision logs, summary json).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from manager_env import ACTIONS, ManagerEnv, random_policy, rule_policy, run_episodes
from v6_common import OUT_DIR

RUNS = OUT_DIR / "manager_runs"


def make_env(rank, run_dir, max_episode_s):
    def _init():
        env = ManagerEnv(seed=100 + rank, max_episode_s=max_episode_s, log_path=run_dir / f"train_env{rank}.jsonl")
        return env
    return _init


def train(args):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
    run_dir = RUNS / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    fns = [make_env(i, run_dir, args.max_episode_s) for i in range(args.envs)]
    venv = SubprocVecEnv(fns, start_method="spawn") if args.envs > 1 else DummyVecEnv(fns)
    n_steps = max(8, args.rollout)
    model = PPO("MlpPolicy", venv, n_steps=n_steps, batch_size=min(64, n_steps * args.envs), n_epochs=6,
                learning_rate=3e-4, gamma=0.99, gae_lambda=0.95, ent_coef=0.02, clip_range=0.2,
                policy_kwargs=dict(net_arch=[64, 64]), seed=args.seed, device="cpu", verbose=1,
                tensorboard_log=None)
    t0 = time.perf_counter()
    model.learn(total_timesteps=args.steps)
    wall = time.perf_counter() - t0
    model.save(run_dir / "ppo_manager")
    venv.close()
    summary = {"run": args.run, "envs": args.envs, "steps": args.steps, "rollout": n_steps, "wall_s": round(wall, 1)}
    (run_dir / "train_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def evaluate(args):
    run_dir = RUNS / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    env = ManagerEnv(seed=0, max_episode_s=args.max_episode_s, log_path=run_dir / "eval_decisions.jsonl")
    policies = {}
    if (run_dir / "ppo_manager.zip").exists():
        from stable_baselines3 import PPO
        model = PPO.load(run_dir / "ppo_manager", device="cpu")
        policies["ppo"] = lambda o, s: int(model.predict(o, deterministic=True)[0])
    policies["rule"] = rule_policy
    rng = np.random.default_rng(7)
    policies["random"] = lambda o, s: random_policy(o, s, rng)
    report = {}
    for name in args.policies:
        if name not in policies:
            print(f"no policy '{name}' (missing model?)")
            continue
        recs = run_episodes(env, policies[name], args.episodes, seed0=args.seed0, verbose=args.verbose)
        succ = [r for r in recs if r["success"]]
        report[name] = {
            "episodes": len(recs),
            "recovery_rate": round(len(succ) / len(recs), 3),
            "median_time_to_recover_s": round(float(np.median([r["sim_s"] for r in succ])), 1) if succ else None,
            "mean_return": round(float(np.mean([r["return"] for r in recs])), 2),
            "mean_steps": round(float(np.mean([r["steps"] for r in recs])), 2),
            "lift_attempts_per_episode": round(float(np.mean([r["actions"].count("LIFT_BEHIND") for r in recs])), 2),
            "lifted_episodes": sum(1 for r in recs if "lifted" in r["results"]),
            "mean_wall_s": round(float(np.mean([r["wall_s"] for r in recs])), 1),
            "action_counts": {a: sum(r["actions"].count(a) for r in recs) for a in ACTIONS},
        }
        (run_dir / f"eval_{name}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    (run_dir / "eval_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


def demo(args):
    """Record one episode of a policy (ppo / rule / random) as a video with the manager's speech bubbles."""
    run_dir = RUNS / args.run
    env = ManagerEnv(seed=0, max_episode_s=args.max_episode_s, log_path=run_dir / f"demo_{args.policy}.jsonl")
    if args.policy == "ppo":
        from stable_baselines3 import PPO
        model = PPO.load(run_dir / "ppo_manager", device="cpu")
        pol = lambda o, s: int(model.predict(o, deterministic=True)[0])
    elif args.policy == "rule":
        pol = rule_policy
    else:
        rng = np.random.default_rng(3)
        pol = lambda o, s: random_policy(o, s, rng)
    out = args.video or (run_dir / f"demo_{args.policy}_seed{args.seed}.mp4")
    env.scene.start_recording(out, speed=args.speed)
    recs = run_episodes(env, pol, 1, seed0=args.seed)
    print("video", env.scene.stop_recording())
    print(json.dumps(recs[0], ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--run", default="ppo_smoke")
    d.add_argument("--policy", choices=["ppo", "rule", "random"], default="ppo")
    d.add_argument("--seed", type=int, default=5000)
    d.add_argument("--video", type=Path)
    d.add_argument("--speed", type=float, default=2.0)
    d.add_argument("--max-episode-s", type=float, default=240.0)
    t = sub.add_parser("train")
    t.add_argument("--run", default="ppo_smoke")
    t.add_argument("--envs", type=int, default=8)
    t.add_argument("--steps", type=int, default=1024, help="total decisions (env steps) across all envs")
    t.add_argument("--rollout", type=int, default=32, help="decisions per env per PPO update")
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--max-episode-s", type=float, default=240.0)
    e = sub.add_parser("eval")
    e.add_argument("--run", default="ppo_smoke")
    e.add_argument("--episodes", type=int, default=20)
    e.add_argument("--seed0", type=int, default=5000)
    e.add_argument("--policies", nargs="+", default=["ppo", "rule", "random"])
    e.add_argument("--max-episode-s", type=float, default=240.0)
    e.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.cmd == "train":
        train(args)
    elif args.cmd == "demo":
        demo(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
