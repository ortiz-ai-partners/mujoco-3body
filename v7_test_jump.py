"""v7 check: the jumper's official high jump in plain MuJoCo - how high, how far?

    <jumper venv python> v7_test_jump.py [--preview DIR]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import OUT_DIR, VIDEO_H, VIDEO_W, Captioner, CameraRig
from v6_robots import body_tilt_deg, build_arena
from v7_policies import JumperJump, JumperLocomotion, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
JP_POSE = (-1.5, -0.5, 0.0)
SIM_DT = 0.001


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()
    model, data = build_arena(STAGE_XML, jp_pose=JP_POSE, timestep=SIM_DT)
    loco = JumperLocomotion(model, data)
    jump = JumperJump(model, data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    loco.reset()
    print(f"jump: obs {jump.dim} kp {jump.kp} duration {jump.r['duration']} t_go {jump.r['t_go']} "
          f"span {jump.r['span']} frames {len(jump.q)} cmd {len(jump.q_cmd)}")

    renderer = None
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=data.xpos[jump.bid], distance=1.3, azimuth=140, elevation=-12, tau=0.5)
        cam.snap()
        next_shot = 1.9

    steps_per_ctrl = round(loco.control_dt / SIM_DT)
    mode = "loco"
    t_jump = 2.0
    start = data.xpos[jump.bid].copy()
    z_max, k = 0.0, 0
    while data.time < 5.0:
        t = data.time
        if mode == "loco" and t >= t_jump:
            mode = "jump"
            jump.reset()
            set_pd_gains(model, jump.act_ids, jump.kp, jump.kd)
            p0 = data.xpos[jump.bid].copy()
            print(f"  t={t:.2f} -> JUMP mode (kp {jump.kp})")
        if k % steps_per_ctrl == 0:
            if mode == "jump":
                jump.step(model, data)
                if jump.finished():
                    mode = "loco"
                    loco.reset()
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
                    print(f"  t={t:.2f} -> back to locomotion; z_max {z_max:.3f} "
                          f"travel {np.linalg.norm(data.xpos[jump.bid][:2] - p0[:2]):.3f} m")
            else:
                loco.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        z_max = max(z_max, float(data.xpos[jump.bid][2])) if mode == "jump" else z_max
        if k % 250 == 0 and 1.8 <= t <= 4.0:
            p = data.xpos[jump.bid]
            print(f"  t={t:5.2f} [{mode}] z={p[2]:.3f} tilt={body_tilt_deg(data, jump.bid):5.1f} "
                  f"x={p[0]:+.3f} phase={min(jump.t_since_go() / jump.r['span'], 1.0):.2f}")
        if renderer is not None and t >= next_shot and t <= 4.0:
            cam.aim(lookat=[p0[0] if mode == 'jump' else data.xpos[jump.bid][0], data.xpos[jump.bid][1], 0.12])
            cam.snap()
            renderer.update_scene(data, cam.cam, opt)
            imageio.imwrite(args.preview / f"jump_t{t:04.2f}.png",
                            cap.draw(renderer.render(), "v7 | 跳跳 公式ジャンプ（自前の脚のみ）", [f"mode {mode}"],
                                     footer=f"sim {t:5.2f} s"))
            next_shot += 0.15
    p = data.xpos[jump.bid]
    print(f"final z={p[2]:.3f} tilt={body_tilt_deg(data, jump.bid):.1f} moved {np.linalg.norm(p[:2] - start[:2]):.3f} m")


if __name__ == "__main__":
    main()
