"""v7 check: does the jumper stand and walk under its official locomotion policy, physics only?

    <jumper venv python> v7_test_jumper.py [--preview DIR]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import OUT_DIR, VIDEO_H, VIDEO_W, Captioner, CameraRig, body_poses
from v6_robots import body_tilt_deg, build_arena
from v7_policies import JumperLocomotion

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
JP_POSE = (-1.5, -0.5, 0.0)
SIM_DT = 0.001
SCRIPT = [  # (until_s, vx, vy, wz)
    (1.0, 0.0, 0.0, 0.0),
    (6.0, 0.3, 0.0, 0.0),
    (8.5, 0.0, 0.0, 1.0),
    (12.0, 0.3, 0.0, 0.0),
    (13.0, 0.0, 0.0, 0.0),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--dt", type=float, default=SIM_DT)
    args = ap.parse_args()
    model, data = build_arena(STAGE_XML, jp_pose=JP_POSE, timestep=args.dt)
    pol = JumperLocomotion(model, data)
    pol.hold_home(data)
    for _ in range(300):            # settle on its feet at HOME before the policy takes over
        mujoco.mj_step(model, data)
    pol.reset()
    print(f"MuJoCo {mujoco.__version__} | jumper locomotion | obs {pol.dim} | dt {model.opt.timestep} "
          f"| control_dt {pol.control_dt} | nu={model.nu}")

    renderer = cam = None
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=data.xpos[pol.bid], distance=1.4, azimuth=140, elevation=-18, tau=0.5)
        cam.snap()
        marks = [0.5, 3.0, 5.5, 7.5, 10.0, 12.5]

    steps_per_ctrl = max(1, round(pol.control_dt / args.dt))
    start = data.xpos[pol.bid].copy()
    k = 0
    t_end = SCRIPT[-1][0]
    while data.time < t_end:
        t = data.time
        for until, vx, vy, wz in SCRIPT:
            if t < until:
                pol.set_command(vx, vy, wz)
                break
        if k % steps_per_ctrl == 0:
            pol.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        if k % 500 == 0:
            p = data.xpos[pol.bid]
            v = data.qvel[pol.dadr[0] - 6:pol.dadr[0] - 3] if False else data.cvel[pol.bid][3:6]
            print(f"  t={t:5.2f} cmd={pol.cmd.round(2).tolist()} pos=({p[0]:+.3f},{p[1]:+.3f}) z={p[2]:.3f} "
                  f"tilt={body_tilt_deg(data, pol.bid):5.1f} |a|max={np.abs(pol.last_action).max():.2f} "
                  f"phase={pol.phase:.2f}")
        if renderer is not None and marks and t >= marks[0]:
            look = data.xpos[pol.bid].copy()
            cam.aim(lookat=look)
            cam.snap()
            renderer.update_scene(data, cam.cam, opt)
            frame = cap.draw(renderer.render(), "v7 | 跳跳 公式ロコモーションポリシー（自前の脚のみ）",
                             [f"cmd vx={pol.cmd[0]:.2f} wz={pol.cmd[2]:.2f}"], footer=f"sim {t:5.2f} s")
            imageio.imwrite(args.preview / f"jp_t{marks[0]:04.1f}.png", frame)
            marks.pop(0)
        if np.any(np.isnan(data.qpos)):
            print("NaN!")
            break
    p = data.xpos[pol.bid]
    print(f"moved {np.linalg.norm(p[:2] - start[:2]):.3f} m, final z={p[2]:.3f} tilt={body_tilt_deg(data, pol.bid):.1f}")


if __name__ == "__main__":
    main()
