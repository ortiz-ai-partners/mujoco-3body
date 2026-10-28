"""Training data for the crab's mood net (crab_face.MoodAI, ゆうころ 10/28 夜「本物の推論で 2 つの AI」).

Runs managers (the fixed rule, the PPO v2.2 policy, and random moves for variety) in the learning environment's Scene
over the start scenarios and, every 0.1 s inside every skill, records the manager's 46-dim observation, which skill is
running and for how long, and - once the skill has ended - how it ended and whether the episode ended in a crossing.
The mood net (analysis/mood_train.py) learns from this to infer, at any control step of a rescue, "will this move end
well?" and "will the duck get across?".  The PPO critic's V(s) is recorded beside it for comparison (face_value.py
showed the critic reading every mid-push state as hopeless, -22: it only ever saw decision points).

    python analysis/mood_data.py --seeds 2 --policies rule ppo random --name mood_data
    -> out/manager_runs/mood_data.npz (obs, skill, t_in_skill, ok, crossed, V, episode ids)

Training-only teleported starts; no video; physics as in training.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np                                  # noqa: E402
import torch                                        # noqa: E402
from stable_baselines3 import PPO                   # noqa: E402

from crab_help import ACTIONS, SKILLS, observation, rule_action      # noqa: E402
from manager2_env import COURSE_TOLERANCE, SCENARIOS, Scene          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOD = {"seated", "pushed_up", "cleared", "standing", "crossed", "walked", "waited"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="ppo2_v22")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=8000)
    ap.add_argument("--policies", nargs="+", default=["rule", "ppo", "random"])
    ap.add_argument("--random-seeds", type=int, default=1)
    ap.add_argument("--max-s", type=float, default=240.0)
    ap.add_argument("--every", type=float, default=0.1)
    ap.add_argument("--name", default="mood_data")
    args = ap.parse_args()

    ppo = PPO.load(os.path.join(ROOT, "out", "manager_runs", args.run, "ppo_manager"), device="cpu")

    def value(obs):
        ten, _ = ppo.policy.obs_to_tensor(np.asarray(obs, dtype=np.float32))
        with torch.no_grad():
            return float(ppo.policy.predict_values(ten))

    scene = Scene()
    every = max(1, int(round(args.every / 0.02)))
    OBS, SK, TS, OK, CR, V, EP, RES = [], [], [], [], [], [], [], []
    episodes = []
    wall0 = time.perf_counter()
    ep_id = 0
    for pol in args.policies:
        n_seeds = args.random_seeds if pol == "random" else args.seeds
        for scen, _w in SCENARIOS:
            for k in range(n_seeds):
                seed = args.seed0 + k + (100 if pol == "random" else 0)
                rng = np.random.default_rng(seed)
                scene.reset(np.random.default_rng(seed), hard={"scenario": scen})
                steps, success, damaged, result = 0, False, False, "none"
                first = len(OBS)
                while scene.t - scene.t0_episode < args.max_s and steps < 40:
                    obs = observation(scene.h, scene)
                    if pol == "rule":
                        a = rule_action(scene.h, scene)
                    elif pol == "ppo":
                        a = int(ppo.predict(obs, deterministic=True)[0])
                    else:
                        a = int(rng.integers(len(ACTIONS)))
                    name = ACTIONS[a]
                    gen = SKILLS[name](scene.h)
                    t_start, mode0 = scene.t, scene.duck.mode
                    tick, first_skill = 0, len(OBS)
                    try:
                        while True:
                            next(gen)
                            scene.sim.command(0, 0, 0)
                            scene.tick()
                            tick += 1
                            if tick % every == 0:
                                o = observation(scene.h, scene)
                                OBS.append(o)
                                SK.append(a)
                                TS.append(scene.t - t_start)
                                V.append(value(o))
                                EP.append(ep_id)
                    except StopIteration as stop:
                        result = stop.value
                    ok = result in GOOD
                    OK.extend([ok] * (len(OBS) - first_skill))
                    RES.extend([result] * (len(OBS) - first_skill))
                    if name == "PUSH" and mode0 == "FALLEN":
                        scene.nudges += 1
                    elif name == "PUSH" and result != "nothing":
                        scene.pushes += 1
                    if not scene.landed and scene.h.stage() in ("deck", "ramp_down", "north"):
                        scene.landed = True
                    damaged = scene.course_damage > COURSE_TOLERANCE
                    success = (not damaged) and scene.h.crossed() and scene.confirm_up(2.0)
                    scene.last_result, scene.last_action = result, a
                    steps += 1
                    if success or damaged:
                        break
                CR.extend([bool(success)] * (len(OBS) - first))
                episodes.append({"id": ep_id, "policy": pol, "scenario": scen, "seed": seed, "steps": steps,
                                 "crossed": bool(success), "damaged": bool(damaged), "samples": len(OBS) - first,
                                 "sim_s": round(scene.t - scene.t0_episode, 1)})
                print(f"{pol:6s} {scen:17s} seed {seed}: {'crossed' if success else 'not crossed'} in {steps} moves, "
                      f"{len(OBS) - first} samples  ({time.perf_counter() - wall0:.0f} s)", flush=True)
                ep_id += 1
    out = os.path.join(ROOT, "out", "manager_runs", args.name + ".npz")
    np.savez_compressed(out, obs=np.asarray(OBS, np.float32), skill=np.asarray(SK, np.int64), t_in_skill=np.asarray(TS, np.float32),
                        ok=np.asarray(OK, bool), crossed=np.asarray(CR, bool), V=np.asarray(V, np.float32),
                        episode=np.asarray(EP, np.int64), result=np.asarray(RES))
    json.dump(episodes, open(os.path.join(ROOT, "out", "manager_runs", args.name + "_episodes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"wrote {out}: {len(OBS)} samples from {len(episodes)} episodes; skill ok {np.mean(OK):.2f}, crossed {np.mean(CR):.2f}")


if __name__ == "__main__":
    main()
