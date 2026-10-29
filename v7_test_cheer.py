"""Goal celebration test: the three at the goal after the crossing - BZ's fork up, the duck
flapping, the crab's dance with its claws up, then both arms held up.  Built stage; the robots are placed by
teleport (test only, never in a video); the celebration itself is policy commands and joint targets only.

    python v7_test_cheer.py --video out/v7_cheer_test.mp4     # the 13 s celebration, recorded
    python v7_test_cheer.py --dance-only --seconds 16         # the dance alone: claw heights, arm pose at the top
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np

from manager2_env import Scene
from v7_full import (ARM_SLOTS, CHEER_DANCE_S, CHEER_HOLD_S, CIRCLE_BZ_END, CIRCLE_C, CIRCLE_JP, CIRCLE_MD, CONTROL_DT,
                     cheer_circle_tick, cheer_tick)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--dance-only", action="store_true", help="only the crab's official dance (no duck / BZ moves)")
    ap.add_argument("--circle", action="store_true", help="the circle celebration: BZ pumps the fork, the duck squats, the crab dances")
    ap.add_argument("--seconds", type=float)
    args = ap.parse_args()

    s = Scene(dt=0.001)
    model, data, duck, crab = s.model, s.data, s.duck, s.crab
    z_stand = float(data.qpos[s.free["md"][0] + 2])
    if args.circle:
        # the circle: BZ at its spot facing south, the duck and the crab on the circle facing the centre
        s.teleport("bz", CIRCLE_BZ_END, -math.pi / 2, z=0.30)
        s.teleport("md", CIRCLE_MD, math.atan2(CIRCLE_C[1] - CIRCLE_MD[1], CIRCLE_C[0] - CIRCLE_MD[0]), z=z_stand + 0.005)
        s.teleport("jp", CIRCLE_JP, math.atan2(CIRCLE_C[1] - CIRCLE_JP[1], CIRCLE_C[0] - CIRCLE_JP[0]), z=0.115)
    else:
        # the positions after a crossing: BZ parked north of the course facing north, the duck on the floor just past the far
        # ramp's toe, the crab at the duck's east side facing it (the procession finale brings it there)
        s.teleport("bz", (1.55, 3.07), math.pi / 2, z=0.30)
        s.teleport("md", (1.45, 2.35), math.pi / 2, z=z_stand + 0.005)
        s.teleport("jp", (2.35, 2.15), math.pi, z=0.115)
    mujoco.mj_forward(model, data)
    s.course_ref = data.xpos[s.course_bids][:, :2].copy()          # the bookkeeping Scene.reset() would have set up
    s.course_damage, s.course_moved_body, s.falls, s.was_fallen = 0.0, "", 0, False
    duck.gaze = None
    if args.circle:
        s.bubble_text = "ゴールで輪になって万歳！"
        s.bubble_sub = "BZ：フォークを上げ下げ   パッカン：屈伸しながら首を振る（sitstand）   跳跳：腕を上げて応援ダンス（公式 dance ポリシー）"
    else:
        s.bubble_text = "ゴールで三人そろって万歳！"
        s.bubble_sub = "BZ：フォーク万歳   パッカン：パタパタ（velstand）   跳跳：腕を上げて応援ダンス（公式 dance ポリシー）"
    if args.video:
        s.start_recording(args.video, speed=args.speed)
    s.run(1.0)

    J = mujoco.mjtObj.mjOBJ_JOINT
    claws = [int(model.jnt_bodyid[mujoco.mj_name2id(model, J, f"jp-{n}_J4_joint")]) for n in ("LF", "RF")]
    arm_q = crab.loco.qadr[ARM_SLOTS]
    total = args.seconds or (CHEER_DANCE_S + CHEER_HOLD_S + 1.5)
    t0 = s.t
    rows, best, falls = [], (-1.0, None, 0.0), 0
    prev_mode = duck.mode
    for k in range(int(round(total / CONTROL_DT))):
        rel = s.t - t0
        if args.dance_only:
            if crab.mode != "DANCE":
                crab.set_mode("DANCE", s.t, model)
            s.sim.command(0, 0, 0)
        elif args.circle:
            if duck.mode == "SIT" and duck.tilt(data) > 60.0:      # toppled while squatting: velstand takes over
                duck.resume, duck.fell_at, duck.upright_since = "STAND", s.t, None
                duck.use("vel")
                duck.set_mode("FALLEN", s.t)
            cheer_circle_tick(rel, duck, crab, s.sim, model, data, s.t)
        else:
            cheer_tick(rel, duck, crab, s.sim, model, data, s.t)
        s.tick()
        if duck.mode == "FALLEN" and prev_mode != "FALLEN":
            falls += 1
        prev_mode = duck.mode
        if k % 5 == 0:
            zc = [float(data.xpos[b][2]) for b in claws]
            rows.append((round(rel, 2), round(zc[0], 3), round(zc[1], 3), duck.mode, crab.mode,
                         round(float(duck.tilt(data)), 1), round(float(s.sim.lift_target), 3), round(float(crab.pos(data)[2]), 3),
                         round(float(duck.pos(data)[2]), 3)))
            if min(zc) > best[0]:
                best = (min(zc), data.qpos[arm_q].copy(), rel)
    if args.video:
        print("video", s.stop_recording())
    print(f"dance recording: {crab.dance.duration:.2f} s, {crab.dance.n_frames} frames at {crab.dance.rec_hz:g} Hz")
    print("t     clawL  clawR  duck     crab   tilt  fork   crab_z  duck_z")
    for r in rows[::5]:
        print("  ".join(str(x) for x in r))
    print(f"\nclaws highest at rel={best[2]:.2f} s (min of the two: {best[0]:.3f} m); arm joints there (LF_J0..J4, RF_J0..J4):")
    print("  " + ", ".join(f"{float(v):.4f}" for v in best[1]))
    print(f"duck falls: {falls}; course moved: {float(s.course_damage):.3f} m; duck tilt at the end {float(duck.tilt(data)):.1f}")
    print(json.dumps({"best_rel": round(best[2], 2), "best_claw_z": round(best[0], 3), "arms": [round(float(v), 4) for v in best[1]],
                      "falls": falls, "course_damage_m": round(float(s.course_damage), 3)}))


if __name__ == "__main__":
    main()
