"""Is the PPO v2.2 critic's V(s) a usable mood for the crab?  (crab_face.MoodAI, ゆうころ 10/28 夜)

Runs the rule manager and the PPO v2.2 manager in the learning environment's Scene over the start scenarios (a few
seeds each) and evaluates ppo2_v22's value network every 0.1 s inside the skills - the same inference the story's
mood AI makes at every control step.  Tabulates V by situation (duck mode x stage, skill x contact, last result,
scenario at the start, episodes that end in a crossing vs the others) so that MOOD_HI / MOOD_LO can be read off.

    python analysis/face_value.py --seeds 2 --policies rule ppo --name face_value
    -> out/manager_runs/face_value.md and face_value.json (every sample)

The scenes are the training environment's (teleported starts), not the story: V in the story is logged in the take's
report (face.mood_ai.v_series).
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


def stats(vals):
    a = np.asarray(vals, dtype=float)
    return {"n": int(a.size), "mean": round(float(a.mean()), 2), "p10": round(float(np.percentile(a, 10)), 2),
            "p50": round(float(np.percentile(a, 50)), 2), "p90": round(float(np.percentile(a, 90)), 2)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="ppo2_v22")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=7000)
    ap.add_argument("--policies", nargs="+", default=["rule", "ppo"])
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--max-s", type=float, default=240.0)
    ap.add_argument("--every", type=float, default=0.1, help="s between samples inside a skill")
    ap.add_argument("--name", default="face_value")
    args = ap.parse_args()

    ppo = PPO.load(os.path.join(ROOT, "out", "manager_runs", args.run, "ppo_manager"), device="cpu")

    def value(obs):
        ten, _ = ppo.policy.obs_to_tensor(np.asarray(obs, dtype=np.float32))
        with torch.no_grad():
            return float(ppo.policy.predict_values(ten))

    scene = Scene()
    every = max(1, int(round(args.every / 0.02)))
    rows, episodes = [], []
    wall0 = time.perf_counter()
    for pol in args.policies:
        for scen, _w in SCENARIOS:
            if args.scenarios and scen not in args.scenarios:
                continue
            for k in range(args.seeds):
                seed = args.seed0 + k
                scene.reset(np.random.default_rng(seed), hard={"scenario": scen})
                v0 = value(observation(scene.h, scene))
                steps, success, damaged, result = 0, False, False, "none"
                first = len(rows)
                while scene.t - scene.t0_episode < args.max_s and steps < 40:
                    obs = observation(scene.h, scene)
                    a = rule_action(scene.h, scene) if pol == "rule" else int(ppo.predict(obs, deterministic=True)[0])
                    name = ACTIONS[a]
                    gen = SKILLS[name](scene.h)
                    t_start, mode0 = scene.t, scene.duck.mode
                    tick = 0
                    try:
                        while True:
                            next(gen)
                            scene.sim.command(0, 0, 0)
                            scene.tick()
                            tick += 1
                            if tick % every == 0:
                                rows.append({"policy": pol, "scenario": scen, "seed": seed, "step": steps, "skill": name,
                                             "t_in_skill": round(scene.t - t_start, 1), "duck": scene.duck.mode,
                                             "stage": scene.h.stage(), "touching": bool(scene.h.touching()),
                                             "last_result": scene.last_result, "V": round(value(observation(scene.h, scene)), 3)})
                    except StopIteration as stop:
                        result = stop.value
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
                for r in rows[first:]:
                    r["crossed"] = bool(success)
                ep = {"policy": pol, "scenario": scen, "seed": seed, "steps": steps, "crossed": bool(success),
                      "damaged": bool(damaged), "sim_s": round(scene.t - scene.t0_episode, 1), "V_start": round(v0, 2),
                      "V_end": rows[-1]["V"] if len(rows) > first else None}
                episodes.append(ep)
                print(f"{pol:4s} {scen:17s} seed {seed}: {'crossed' if success else 'not crossed'} in {steps} moves, "
                      f"V start {v0:+.2f} end {ep['V_end']:+.2f}  ({time.perf_counter() - wall0:.0f} s)", flush=True)

    def group(key):
        g = {}
        for r in rows:
            g.setdefault(key(r), []).append(r["V"])
        return {k: stats(v) for k, v in sorted(g.items())}

    tables = {
        "duck x stage": group(lambda r: f"{r['policy']} | {r['duck']} | {r['stage']}"),
        "skill x contact": group(lambda r: f"{r['policy']} | {r['skill']} | {'touching' if r['touching'] else 'apart'}"),
        "last result": group(lambda r: f"{r['policy']} | {r['last_result']}"),
        "episode outcome": group(lambda r: f"{r['policy']} | {'crossed' if r['crossed'] else 'not crossed'}"),
        "scenario (all samples)": group(lambda r: f"{r['policy']} | {r['scenario']}"),
    }
    lines = [f"# 気分 AI の下調べ — PPO v2.2 の価値 V(s)（{args.run}、{len(rows)} サンプル、{len(episodes)} 話、0.1 s ごと）", ""]
    lines += ["| 方策 | 場面 | シード | 手数 | 渡り切り | V 開始 | V 終了 |", "|---|---|---|---|---|---|---|"]
    for e in episodes:
        lines.append(f"| {e['policy']} | {e['scenario']} | {e['seed']} | {e['steps']} | {'○' if e['crossed'] else '×'} | "
                     f"{e['V_start']:+.2f} | {e['V_end'] if e['V_end'] is None else format(e['V_end'], '+.2f')} |")
    for title, tab in tables.items():
        lines += ["", f"## {title}", "", "| 区分 | n | 平均 | p10 | p50 | p90 |", "|---|---|---|---|---|---|"]
        for k, s in tab.items():
            lines.append(f"| {k} | {s['n']} | {s['mean']:+.2f} | {s['p10']:+.2f} | {s['p50']:+.2f} | {s['p90']:+.2f} |")
    out_md = os.path.join(ROOT, "out", "manager_runs", args.name + ".md")
    out_json = os.path.join(ROOT, "out", "manager_runs", args.name + ".json")
    open(out_md, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"episodes": episodes, "samples": rows}, open(out_json, "w", encoding="utf-8"), ensure_ascii=False)
    print("\n".join(lines))
    print("wrote", out_md)


if __name__ == "__main__":
    main()
