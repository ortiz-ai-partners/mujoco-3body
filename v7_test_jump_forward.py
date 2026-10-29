"""v7 experiment: forward jump by sweeping the feet backward during the push (joint targets only).

    python v7_test_jump_forward.py
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from v6_common import OUT_DIR
from v6_robots import body_tilt_deg, build_arena
from v7_policies import JumperJump, JumperLocomotion, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
JP_POSE = (-1.5, -0.5, 0.0)
SIM_DT = 0.001


def run(sweep):
    model, data = build_arena(STAGE_XML, jp_pose=JP_POSE, timestep=SIM_DT)
    loco = JumperLocomotion(model, data)
    jump = JumperJump(model, data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    loco.reset()
    steps_per_ctrl = round(loco.control_dt / SIM_DT)
    mode, k = "loco", 0
    p0 = None
    z_max, tilt_max = 0.0, 0.0
    while data.time < 4.0:
        if mode == "loco" and data.time >= 1.0 and p0 is None:
            mode = "jump"
            jump.reset(sweep=sweep)
            set_pd_gains(model, jump.act_ids, jump.kp, jump.kd)
            p0 = data.xpos[jump.bid].copy()
            yaw0 = math.atan2(*(data.xmat[jump.bid].reshape(3, 3)[1::-1, 0]))
        if k % steps_per_ctrl == 0:
            if mode == "jump":
                jump.step(model, data)
                if jump.finished():
                    mode = "loco"
                    loco.reset()
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
            else:
                loco.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        if p0 is not None:
            z_max = max(z_max, float(data.xpos[jump.bid][2]))
            tilt_max = max(tilt_max, body_tilt_deg(data, jump.bid))
        if np.any(np.isnan(data.qpos)):
            return dict(sweep=sweep, nan=True)
    p = data.xpos[jump.bid]
    d = p[:2] - p0[:2]
    fwd = d[0] * math.cos(yaw0) + d[1] * math.sin(yaw0)
    lat = -d[0] * math.sin(yaw0) + d[1] * math.cos(yaw0)
    return dict(sweep=sweep, z_max=round(z_max, 3), fwd_m=round(float(fwd), 3), lat_m=round(float(lat), 3),
                tilt_max=round(tilt_max, 1), final_tilt=round(body_tilt_deg(data, jump.bid), 1),
                final_z=round(float(p[2]), 3))


def main():
    for sweep in (0.0, 0.3, 0.6, 0.9, 1.2):
        print(run(sweep))


if __name__ == "__main__":
    main()
