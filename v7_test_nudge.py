"""The nudge (PUSH on a fallen duck; an experiment, not adopted): the duck lying across the landing's seam, the crab
0.6 m behind.  Does velstand get it up on its own in 4 s?  If not, does the nudge move it, and does velstand get it
up afterwards?  Built stage; the robots are placed by teleport (test only).

    python v7_test_nudge.py [--video out/v7_nudge_test.mp4]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import mujoco
import numpy as np

import crab_help as ch
from manager2_env import Scene


def run_skill(s, gen):
    try:
        while True:
            next(gen)
            s.sim.command(0, 0, 0)
            s.tick()
    except StopIteration as stop:
        return stop.value


def case(s, label, duck_xy, yaw, roll, crab_xy, video=None):
    model, data, duck, crab, h = s.model, s.data, s.duck, s.crab, s.h
    qpos, qvel, ctrl, act = s.init
    mujoco.mj_resetData(model, data)
    data.qpos[:] = qpos; data.qvel[:] = qvel; data.ctrl[:] = ctrl; data.act[:] = act
    s.t, s.sub_k, s.falls, s.was_fallen = 0.0, 0, 0, False
    s.course_damage, s.course_moved_body, s.pushes, s.nudges, s.landed = 0.0, "", 0, 0, True
    s.last_result, s.last_action, s.decisions = "none", None, []
    duck.vel.reset(); duck.sit.reset(); duck.pol = duck.vel; duck.mode = "STAND"; duck.goal = None; duck.gaze = None
    crab.loco.reset(); crab.mode = "HOLD"
    crab.loco.hold_home(data)
    s.teleport("md", duck_xy, yaw, z=0.44 + 0.10, roll=math.radians(roll))
    s.teleport("jp", crab_xy, math.pi / 2, z=0.44 + 0.115)
    mujoco.mj_forward(model, data)
    s.course_ref = data.xpos[s.course_bids][:, :2].copy()
    duck.resume, duck.fell_at, duck.upright_since = "STAND", s.t, None
    duck.set_mode("FALLEN", s.t)
    s.run(0.4)
    crab.loco.set_command(0, 0, 0)
    s.bubble_text = f"nudge test: {label}"
    # 1) WAIT 4 s: does velstand get it up by itself?
    s.run(4.0)
    up_alone = duck.mode != "FALLEN"
    p_before = h.duck_xyz().copy()
    res, moved, up_after = None, 0.0, None
    if not up_alone:
        # 2) the nudge (PUSH on a fallen duck)
        res = run_skill(s, ch.skill_push(h))
        moved = float(h.duck_xyz()[1] - p_before[1])
        # 3) WAIT 8 s: up now?
        s.run(8.0)
        up_after = duck.mode != "FALLEN"
    p = h.duck_xyz()
    print(f"{label:34s} up alone: {up_alone!s:5s}  nudge: {res!s:8s} moved {moved:+.2f} m  up after: {up_after!s:5s}  "
          f"duck at ({p[0]:+.2f},{p[1]:+.2f}) tilt {h.tilt():4.0f}  crab {h.crab_dist():.2f} m  course moved {s.course_damage:.3f}")
    return up_alone, res, moved, up_after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path)
    args = ap.parse_args()
    s = Scene(dt=0.001)
    if args.video:
        s.start_recording(args.video, speed=2.0)
    seam = 0.04
    cases = [
        ("on the seam, facing north, roll +80", (ch.LANE_X, seam), math.pi / 2, 80.0, (ch.LANE_X, seam - 0.6)),
        ("on the seam, facing north, roll -80", (ch.LANE_X, seam), math.pi / 2, -80.0, (ch.LANE_X, seam - 0.6)),
        ("on the seam, facing east, roll +80", (ch.LANE_X, seam), 0.0, 80.0, (ch.LANE_X, seam - 0.6)),
        ("on the seam, facing west, roll +80", (ch.LANE_X, seam), math.pi, 80.0, (ch.LANE_X, seam - 0.6)),
        ("10 cm before the seam, north, +80", (ch.LANE_X, seam - 0.10), math.pi / 2, 80.0, (ch.LANE_X, seam - 0.7)),
        ("off the line 15 cm west, north, +80", (ch.LANE_X - 0.15, seam), math.pi / 2, 80.0, (ch.LANE_X, seam - 0.6)),
    ]
    out = [case(s, *c) for c in cases]
    if args.video:
        print("video", s.stop_recording())
    n_down = sum(1 for o in out if not o[0])
    n_up_after = sum(1 for o in out if o[3])
    print(f"\nstill down after 4 s: {n_down}/{len(out)}; up after the nudge: {n_up_after}/{n_down}")


if __name__ == "__main__":
    main()
