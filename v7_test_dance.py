"""v7 check: does the jumper dance under its official dance policy, physics only?

    <jumper venv python> v7_test_dance.py [--seconds 30] [--start 0] [--dt 0.001] [--name dance_crab]
                                          [--video out/v7_dance_test.mp4]

Reports height / tilt / drift every 2 s and the first fall (tilt > 60 deg), optionally writing a
clip of the dance.  No external forces: PD actuators (kp 10 / kd 0.5) and the policy only.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import mujoco
import numpy as np

from v6_common import OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, Video
from v6_robots import body_tilt_deg, build_arena
from v7_policies import JumperDance, JumperLocomotion, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
JP_POSE = (3.6, -1.0, math.pi / 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--start", type=float, default=0.0, help="where in the recording the dance starts (s)")
    ap.add_argument("--dt", type=float, default=0.001)
    ap.add_argument("--name", default="dance_crab")
    ap.add_argument("--video", type=Path)
    args = ap.parse_args()

    model, data = build_arena(STAGE_XML, jp_pose=JP_POSE, timestep=args.dt)
    dance = JumperDance(model, data, name=args.name)
    loco = JumperLocomotion(model, data)
    loco.hold_home(data)
    for _ in range(int(0.3 / args.dt)):          # settle on its feet at HOME first
        mujoco.mj_step(model, data)
    data.time = 0.0
    set_pd_gains(model, dance.act_ids, dance.kp, dance.kd)
    dance.reset(t_start=args.start)
    print(f"MuJoCo {mujoco.__version__} | {args.name} | obs {dance.dim} | dt {model.opt.timestep} "
          f"| control_dt {dance.control_dt} | recording {dance.duration:.1f} s, starting at {args.start} s", flush=True)

    video = renderer = None
    if args.video:
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=data.xpos[dance.bid], distance=1.3, azimuth=160, elevation=-15, tau=0.6)
        cam.snap()
        video = Video(args.video)
        next_frame = 0.0

    start = data.xpos[dance.bid].copy()
    every = max(1, round(dance.control_dt / args.dt))
    k, fell = 0, None
    while data.time < args.seconds and not dance.finished():
        if k % every == 0:
            dance.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        p = data.xpos[dance.bid]
        tilt = body_tilt_deg(data, dance.bid)
        if tilt > 60.0 and fell is None:
            fell = float(data.time)
            print(f"  FELL at t={data.time:.2f} (tilt {tilt:.0f})", flush=True)
        if video is not None and data.time >= next_frame:
            next_frame += 1.0 / VIDEO_FPS
            look = p.copy()
            look[2] = 0.08
            cam.aim(lookat=look)
            renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
            video.add(cap.draw(renderer.render(), f"v7 | 跳跳 公式ダンスポリシー {args.name} ― 自前の脚のみ・外力なし",
                               [f"参照 demo.motion {dance.t_since_go():5.1f} s / {dance.duration:.0f} s",
                                f"高さ {p[2]:.3f} m   傾き {tilt:4.1f}°"],
                               footer=f"sim {data.time:5.1f} s"))
        if k % int(round(2.0 / args.dt)) == 0:
            print(f"  t={data.time:5.1f} z={p[2]:.3f} tilt={tilt:5.1f} drift={np.linalg.norm(p[:2] - start[:2]):.3f} "
                  f"|a|max={np.abs(dance.last_action).max():.2f}", flush=True)
        if np.any(np.isnan(data.qpos)):
            print("NaN!")
            break
    p = data.xpos[dance.bid]
    print(f"end t={data.time:.1f} z={p[2]:.3f} tilt={body_tilt_deg(data, dance.bid):.1f} "
          f"drift={np.linalg.norm(p[:2] - start[:2]):.3f} fell={fell}")
    if video is not None:
        size = video.close()
        renderer.close()
        print(f"video {args.video} frames={video.frames} bytes={size}")


if __name__ == "__main__":
    main()
