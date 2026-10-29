"""Train and evaluate the v2 manager (crab-assisted crossing) with Stable-Baselines3 PPO on manager2_env.

    python manager2_train.py train --envs 12 --steps 3000 --run ppo2_small
    python manager2_train.py eval  --run ppo2_small --episodes 30
    python manager2_train.py demo  --run ppo2_small --policy ppo --seed 5003

train: PPO, small MLP (64x64), parallel envs (one MuJoCo scene per process).  One env step is one
skill (4-90 simulated seconds), so `--steps` counts decisions, not simulator ticks.
eval: the trained policy, the fixed-rule policy and a random policy on the same seeds (same start
scenario and placement), with crossing rate, landing rate, time, falls, pushes, wasted actions.
Everything is written under out/manager_runs/<run>/ (model, decision logs, summary json).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from manager2_env import ACTIONS, ManagerEnv, random_policy, rule_policy, run_episodes, summarize
from v6_common import OUT_DIR

RUNS = OUT_DIR / "manager_runs"


def make_env(rank, run_dir, max_episode_s, env_kwargs=None):
    def _init():
        return ManagerEnv(seed=100 + rank, max_episode_s=max_episode_s, log_path=run_dir / f"train_env{rank}.jsonl",
                          **(env_kwargs or {}))
    return _init


def parse_weights(text, valid):
    """'toe_fallen=0.3,touching=0.4' -> [(name, weight), ...] (names must be in `valid`); None when empty."""
    if not text:
        return None
    table = []
    for item in text.split(","):
        name, w = item.split("=")
        if name.strip() not in valid:
            raise SystemExit(f"unknown name '{name}' in weights (valid: {sorted(valid)})")
        table.append((name.strip(), float(w)))
    return table


class CurveCallback:
    """Collect per-episode returns from the vec env infos (SB3 Monitor-free) and save model checkpoints."""

    def __init__(self, path, run_dir=None, ckpt_every=2000):
        self.path, self.rows, self.t0 = path, [], time.perf_counter()
        self.run_dir, self.ckpt_every, self.next_ckpt = run_dir, ckpt_every, None

    def __call__(self, locals_, globals_):
        model = locals_["self"]
        for i, done in enumerate(locals_["dones"]):
            if done:
                info = locals_["infos"][i]
                self.rows.append({"env": i, "step": int(model.num_timesteps), "success": bool(info.get("success")),
                                  "landed": bool(info.get("landed")), "wall_s": round(time.perf_counter() - self.t0, 1)})
        if len(self.rows) % 20 == 0 and self.rows:
            self.path.write_text(json.dumps(self.rows, indent=0), encoding="utf-8")
        if self.run_dir is not None:
            # checkpoints every `ckpt_every` decisions, numbered by the model's step count plus a "latest" copy
            # (the continued-training run ppo2_medium3 was interrupted part-way and its weights were lost - until here
            # the model was only saved at the end; intermediate policies can now also be evaluated)
            step = int(model.num_timesteps)
            if self.next_ckpt is None:
                self.next_ckpt = (step // self.ckpt_every + 1) * self.ckpt_every
            if step >= self.next_ckpt:
                model.save(self.run_dir / f"ckpt_{step}")
                model.save(self.run_dir / "ppo_manager_latest")
                self.next_ckpt += self.ckpt_every
        return True


def train(args):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
    torch.set_num_threads(2)
    from manager2_env import CRAB_SPOTS_DECK, CRAB_SPOTS_RAMP, CRAB_SPOTS_TOE, SCENARIOS
    run_dir = RUNS / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    env_kwargs = {"scenarios": parse_weights(args.scenario_weights, {s for s, _ in SCENARIOS}),
                  "crab_spots_toe": parse_weights(args.crab_toe_weights, {s for s, _ in CRAB_SPOTS_TOE}),
                  "crab_spots_deck": parse_weights(args.crab_deck_weights, {s for s, _ in CRAB_SPOTS_DECK}),
                  "crab_spots_ramp": parse_weights(args.crab_ramp_weights, {s for s, _ in CRAB_SPOTS_RAMP}),
                  "reward": args.reward}
    fns = [make_env(i, run_dir, args.max_episode_s, env_kwargs) for i in range(args.envs)]
    venv = SubprocVecEnv(fns, start_method="spawn") if args.envs > 1 else DummyVecEnv(fns)
    n_steps = max(8, args.rollout)
    if args.init_from:
        # continued training: the saved policy/value nets and optimizer, new seed and (optionally) new draw tables
        model = PPO.load(RUNS / args.init_from / "ppo_manager", env=venv, device="cpu", verbose=1)
        model.set_random_seed(args.seed)
        if args.ent_coef is not None:
            model.ent_coef = args.ent_coef
    else:
        model = PPO("MlpPolicy", venv, n_steps=n_steps, batch_size=min(64, n_steps * args.envs), n_epochs=6,
                    learning_rate=3e-4, gamma=0.99, gae_lambda=0.95, ent_coef=args.ent_coef if args.ent_coef is not None else 0.02,
                    clip_range=0.2, policy_kwargs=dict(net_arch=[64, 64]), seed=args.seed, device="cpu", verbose=1)
    t0 = time.perf_counter()
    cb = CurveCallback(run_dir / "train_curve.json", run_dir=run_dir, ckpt_every=args.ckpt_every)
    model.learn(total_timesteps=args.steps, callback=cb, reset_num_timesteps=not args.init_from)
    wall = time.perf_counter() - t0
    model.save(run_dir / "ppo_manager")
    venv.close()
    cb.path.write_text(json.dumps(cb.rows, indent=0), encoding="utf-8")
    summary = {"run": args.run, "envs": args.envs, "steps": args.steps, "rollout": int(model.n_steps), "wall_s": round(wall, 1),
               "episodes": len(cb.rows), "train_success_rate": round(sum(r["success"] for r in cb.rows) / max(1, len(cb.rows)), 3),
               "init_from": args.init_from, "ent_coef": float(model.ent_coef), "reward": args.reward,
               "draw_tables": {k: v for k, v in env_kwargs.items() if v and k != "reward"}}
    (run_dir / "train_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def load_policies(run_dir):
    policies = {}
    if (run_dir / "ppo_manager.zip").exists():
        from stable_baselines3 import PPO
        model = PPO.load(run_dir / "ppo_manager", device="cpu")
        policies["ppo"] = lambda o, s: int(model.predict(o, deterministic=True)[0])
    policies["rule"] = rule_policy
    rng = np.random.default_rng(7)
    policies["random"] = lambda o, s: random_policy(o, s, rng)
    return policies


def evaluate(args):
    run_dir = RUNS / args.run
    out_dir = RUNS / (args.out or args.run)                # --out keeps an earlier evaluation of the same run
    out_dir.mkdir(parents=True, exist_ok=True)
    if getattr(args, "rule_near_lip", "on") == "off":
        import crab_help
        crab_help.RULE_NEAR_LIP = False                    # the earlier rule (baselines_v2), for a like-for-like check
    env = ManagerEnv(seed=0, max_episode_s=args.max_episode_s, log_path=out_dir / "eval_decisions.jsonl")
    policies = load_policies(run_dir)
    report = {}
    for name in args.policies:
        if name not in policies:
            print(f"no policy '{name}' (missing model?)")
            continue
        recs = run_episodes(env, policies[name], args.episodes, seed0=args.seed0, verbose=args.verbose)
        report[name] = summarize(recs)
        (out_dir / f"eval_{name}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "eval_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


def demo(args):
    """Record one episode of a policy (ppo / rule / random) as a video with the manager's speech bubbles."""
    run_dir = RUNS / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    env = ManagerEnv(seed=0, max_episode_s=args.max_episode_s, log_path=run_dir / f"demo_{args.policy}.jsonl")
    pol = load_policies(run_dir)[args.policy]
    out = args.video or (run_dir / f"demo_{args.policy}_seed{args.seed}.mp4")
    hard = {k: v for k, v in (("scenario", args.scenario), ("crab", args.crab)) if v}
    env.scene.start_recording(out, speed=args.speed)
    recs = run_episodes(env, pol, 1, seed0=args.seed, hard=hard or None)
    print("video", env.scene.stop_recording())
    print(json.dumps(recs[0], ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--run", default="ppo2_small")
    d.add_argument("--policy", choices=["ppo", "rule", "random"], default="ppo")
    d.add_argument("--seed", type=int, default=5000)
    d.add_argument("--scenario")
    d.add_argument("--crab")
    d.add_argument("--video", type=Path)
    d.add_argument("--speed", type=float, default=2.0)
    d.add_argument("--max-episode-s", type=float, default=240.0)
    t = sub.add_parser("train")
    t.add_argument("--run", default="ppo2_small")
    t.add_argument("--envs", type=int, default=12)
    t.add_argument("--steps", type=int, default=3000, help="total decisions (env steps) across all envs")
    t.add_argument("--rollout", type=int, default=24, help="decisions per env per PPO update")
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--max-episode-s", type=float, default=240.0)
    t.add_argument("--init-from", help="continue training from out/manager_runs/<run>/ppo_manager.zip")
    t.add_argument("--ent-coef", type=float, help="entropy coefficient (default 0.02, or the loaded model's)")
    t.add_argument("--scenario-weights", help="e.g. toe_seated_ok=0.2,toe_fallen=0.3 (names of SCENARIOS; replaces the table)")
    t.add_argument("--crab-toe-weights", help="e.g. behind=0.4,beside=0.2,touching=0.4")
    t.add_argument("--crab-deck-weights", help="e.g. touching=0.7,behind=0.3")
    t.add_argument("--crab-ramp-weights", help="e.g. touching=0.7,behind=0.3 (the ramp_fallen scenario)")
    t.add_argument("--reward", choices=["v2.1", "v2.2"], default="v2.1",
                   help="v2.2 also counts a SEAT / STANDUP that ends still_down as a wasted move (training only)")
    t.add_argument("--ckpt-every", type=int, default=2000, help="save ckpt_<steps>.zip and ppo_manager_latest.zip every N decisions")
    e = sub.add_parser("eval")
    e.add_argument("--run", default="ppo2_small")
    e.add_argument("--episodes", type=int, default=30)
    e.add_argument("--seed0", type=int, default=5000)
    e.add_argument("--policies", nargs="+", default=["ppo", "rule", "random"])
    e.add_argument("--max-episode-s", type=float, default=240.0)
    e.add_argument("--verbose", action="store_true")
    e.add_argument("--rule-near-lip", choices=["on", "off"], default="on",
                   help="off = the rule without the near_lip push condition (as evaluated in baselines_v2)")
    e.add_argument("--out", help="output directory under out/manager_runs/ (default: the run's own; keeps earlier evaluations)")
    args = ap.parse_args()
    if args.cmd == "train":
        train(args)
    elif args.cmd == "demo":
        demo(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
