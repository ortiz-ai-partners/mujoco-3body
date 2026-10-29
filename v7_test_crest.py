"""Crab high-centres on the crest of the up-slope: can it push through at full speed, or jump over?

    python v7_test_crest.py [--sweep 1.0]
"""
from __future__ import annotations

import argparse
import math

import mujoco
import numpy as np

from v6_common import OUT_DIR, quat_to_yaw
from v6_robots import body_tilt_deg, build_arena
from v7_full import wrap
from v7_policies import JumperJump, JumperLocomotion, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", type=float, default=1.0)
    ap.add_argument("--x", type=float, default=1.75)
    args = ap.parse_args()
    model, data = build_arena(STAGE_XML, jp_pose=(args.x, -3.3, math.pi / 2), timestep=0.001)
    loco, jump = JumperLocomotion(model, data), JumperJump(model, data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    data.time = 0.0
    loco.reset()
    mode, k = "walk", 0
    mark = (0.0, -9.0)
    stuck_count = 0
    while data.time < 40.0:
        t = data.time
        p = data.xpos[loco.bid]
        if p[1] > 2.6:
            print(f"  crossed! t={t:.1f} y={p[1]:+.2f} z={p[2]:.3f}")
            break
        if p[1] > mark[1] + 0.03:
            mark = (t, float(p[1]))
        if k % 5 == 0:
            if mode == "walk":
                d = np.array([args.x, 3.2]) - p[:2]
                err = wrap(math.atan2(d[1], d[0]) - quat_to_yaw(data.xquat[loco.bid]))
                vx = 0.8 if stuck_count == 1 else 0.5
                loco.set_command(vx if abs(err) < 0.4 else 0.0, 0.0, float(np.clip(3.0 * err, -2.0, 2.0)))
                loco.step(model, data)
                if t - mark[0] > 3.0 and p[1] > -1.5:
                    stuck_count += 1
                    mark = (t, float(p[1]))
                    if stuck_count == 1:
                        print(f"  t={t:.1f} stuck at y={p[1]:+.2f} z={p[2]:.3f}; trying full speed 0.8")
                    else:
                        print(f"  t={t:.1f} still stuck at y={p[1]:+.2f}; JUMP (sweep {args.sweep})")
                        mode = "jump"
                        jump.reset(sweep=args.sweep)
                        set_pd_gains(model, jump.act_ids, jump.kp, jump.kd)
            else:
                jump.step(model, data)
                if jump.finished():
                    mode = "walk"
                    loco.reset()
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
                    mark = (t, float(p[1]))
                    print(f"  t={t:.1f} landed y={p[1]:+.2f} z={p[2]:.3f} tilt={body_tilt_deg(data, loco.bid):.1f}")
        mujoco.mj_step(model, data)
        k += 1
        if k % 2000 == 0:
            print(f"  t={t:5.1f} [{mode}] y={p[1]:+.3f} z={p[2]:.3f} tilt={body_tilt_deg(data, loco.bid):5.1f}")
        if np.any(np.isnan(data.qpos)):
            print("NaN")
            break
    print(f"end y={data.xpos[loco.bid][1]:+.2f} z={data.xpos[loco.bid][2]:.3f} tilt={body_tilt_deg(data, loco.bid):.1f}")


if __name__ == "__main__":
    main()
