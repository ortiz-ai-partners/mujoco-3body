"""BZ's drive and turn on the built stage, for the circle finale (test only: BZ is placed by teleport).

    <jumper venv python> v7_test_bz_drive.py          # forward with the fork low / high, then a turn on the spot
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from manager2_env import Scene
from v6_common import quat_to_yaw
from v7_full import CONTROL_DT, wrap


def run(s, seconds, fn, label):
    model, data = s.model, s.data
    bid = s.bz_bid
    print(f"\n== {label}")
    t0 = s.t
    n = int(round(seconds / CONTROL_DT))
    for k in range(n):
        p = data.xpos[bid]
        yaw = quat_to_yaw(data.xquat[bid])
        cmd = fn(s.t - t0, p, yaw)
        s.sim.command(*cmd)
        s.tick()
        if k % 50 == 0 or k == n - 1:
            v = float(np.linalg.norm(data.qvel[:2]))
            print(f"  t={s.t - t0:5.1f}  pos=({p[0]:+.2f},{p[1]:+.2f}) z={p[2]:.3f} yaw={yaw:+.2f}  lift={s.sim.lift_target:.2f}  "
                  f"speed={v:.2f}  cmd={tuple(round(float(c), 2) for c in cmd)}  tilt_z={data.xmat[bid][8]:.3f}")


def place(s, xy, yaw):
    s.teleport("bz", xy, yaw, z=0.30)
    mujoco.mj_forward(s.model, s.data)
    s.run(1.0)


def main():
    s = Scene(dt=0.001)
    s.course_ref = s.data.xpos[s.course_bids][:, :2].copy()
    s.course_damage, s.course_moved_body, s.falls, s.was_fallen = 0.0, "", 0, False
    # (10/28 noon) from its post (1.55, 3.07) facing north BZ cannot drive on: with the fork raised its tines reach 1.38 m,
    # the wall's inner face is at y 4.5 - it moved 6 cm and stopped, fork up or down.  So the circle forms around its post.
    place(s, (1.55, 3.07), math.pi / 2)
    run(s, 6.0, lambda rel, p, yaw: (0.6, float(np.clip(2.0 * wrap(math.pi / 2 - yaw), -0.4, 0.4)), -1.0 if s.sim.lift_target > 0.02 else 0.0),
        "forward 0.6 from the post, heading north, fork lowering (blocked by the wall)")
    place(s, (1.55, 3.07), math.pi / 2)
    run(s, 3.0, lambda rel, p, yaw: (0.0, 0.0, 1.0), "fork up at the post")
    run(s, 16.0, lambda rel, p, yaw: (0.0, math.copysign(1.0 if abs(wrap(-math.pi / 2 - yaw)) > 0.2 else 0.4, wrap(-math.pi / 2 - yaw))
                                     if abs(wrap(-math.pi / 2 - yaw)) > 0.04 else 0.0, 1.0 if s.sim.lift_target < 0.5 else 0.0),
        "turn on the spot to face south with the fork up")
    run(s, 8.0, lambda rel, p, yaw: (0.0, 0.0, 1.0 if (rel % 2.4) < 1.2 else (-1.0 if s.sim.lift_target > 0.22 else 0.0)),
        "pump the fork between 0.2 and 0.5 facing south")
    print(f"\ncourse moved: {float(s.course_damage):.3f} m ({s.course_moved_body})")


if __name__ == "__main__":
    main()
