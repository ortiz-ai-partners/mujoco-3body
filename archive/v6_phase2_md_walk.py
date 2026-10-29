"""v6 Phase 2 - Microduck walks on the built stage (phases A1 / A2 / B1 of the v6 plan).

Stage = out/v6_stage_built.xml (the Phase 1 result: slopes + parked dozer).
MD is attached with MjSpec.attach and walks a straight line with a scripted
gait plus a virtual harness (see v6_robots.MicroduckCtrl - a demo aid, not a
balance controller).

    python v6_phase2_md_walk.py --test            # no render: height / tilt / direction log
    python v6_phase2_md_walk.py --preview DIR     # stills
    python v6_phase2_md_walk.py                   # -> out/v6_phase2_md_walk.mp4
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # archive/: resolve v6_common etc. from the repository root

import imageio
import mujoco
import numpy as np

from v6_common import OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock, Video
from v6_robots import MicroduckCtrl, build_arena

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
MD_POSE = (-0.3, -1.8, math.pi / 2)    # x, y, yaw: walks +y, 1.3 m left of the course deck
MD_SPEED = 0.15
CONTROL_DT = 0.02
T_WALK_START, T_WALK_END, DURATION = 1.0, 13.0, 14.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="no rendering, print a metrics log")
    ap.add_argument("--preview", type=Path, help="save stills to this directory")
    ap.add_argument("--azimuth", type=float, default=45.0)
    ap.add_argument("--elevation", type=float, default=-16.0)
    ap.add_argument("--distance", type=float, default=1.7)
    ap.add_argument("--no-harness-xy", action="store_true",
                    help="test: no horizontal pull, so the gait alone moves the body")
    args = ap.parse_args()

    model, data = build_arena(STAGE_XML, md_pose=MD_POSE)
    md = MicroduckCtrl(model, data, MD_POSE, speed=MD_SPEED)
    if args.no_harness_xy:
        md.KP_XY = md.KD_XY = 0.0
    print(f"MuJoCo {mujoco.__version__} | Phase 2 | dt={model.opt.timestep} nq={model.nq} "
          f"nu={model.nu} ngeom={model.ngeom} | MD mass {md.mass:.3f} kg")

    render = not args.test
    video = None
    preview_times = []
    if render:
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=md.pos(data), distance=args.distance, azimuth=args.azimuth,
                        elevation=args.elevation, tau=0.8)
        cam.snap()
        clock = FrameClock(VIDEO_FPS, 1.0)
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            preview_times = [0.5, 3.0, 3.15, 3.3, 3.45, 7.0, 13.5]
        else:
            video = Video(OUT_DIR / "v6_phase2_md_walk.mp4")

    def render_frame():
        look = md.pos(data).copy()
        look[2] = 0.12
        cam.aim(lookat=look)
        renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
        frame = renderer.render()
        return cap.draw(frame, "Phase 2 | パッカンが施工済みステージを歩く",
                        [f"mode {md.mode}   スクリプト歩容＋仮想ハーネス {md.harness:.0%}（演出用補助）"],
                        footer=f"sim {data.time:5.1f} s   x1")

    substeps = round(CONTROL_DT / model.opt.timestep)
    start_xy = md.pos(data)[:2].copy()
    log = []
    for k in range(int(DURATION / CONTROL_DT)):
        t = k * CONTROL_DT
        if md.mode == "STAND" and T_WALK_START <= t < T_WALK_END:
            md.set_mode("WALK", t)
        if md.mode == "WALK" and t >= T_WALK_END:
            md.set_mode("STAND", t)
        md.step(model, data, t, CONTROL_DT)
        for _ in range(substeps):
            mujoco.mj_step(model, data)
            if video is not None and clock.due(data.time):
                video.add(render_frame())
        if preview_times and data.time >= preview_times[0]:
            cam.snap()
            imageio.imwrite(args.preview / f"p2_t{preview_times[0]:04.1f}.png", render_frame())
            preview_times.pop(0)
        if k % 25 == 0:
            p = md.pos(data)
            d = p[:2] - start_xy
            row = {"t": round(t, 2), "z": round(float(p[2]), 4), "tilt_deg": round(md.tilt_deg(data), 1),
                   "fwd_m": round(float(d @ md.heading), 3),
                   "left_m": round(float(-d[0] * md.heading[1] + d[1] * md.heading[0]), 3),
                   "F_N": np.round(data.xfrc_applied[md.bid, :3], 2).tolist(),
                   "T_Nm": np.round(data.xfrc_applied[md.bid, 3:], 3).tolist()}
            log.append(row)
            print(row)
        if np.any(np.isnan(data.qpos)):
            print(f"NaN at t={t:.2f}")
            break

    if render:
        renderer.close()
    if video is not None:
        size = video.close()
        report = {"video": str(video.path), "frames": video.frames, "bytes": size,
                  "md_pose": MD_POSE, "speed": MD_SPEED, "events": md.events, "log": log}
        (OUT_DIR / "v6_phase2_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                       encoding="utf-8")
        print(f"Done: {video.path} ({size / 1024:.0f} KB, {video.frames} frames)")


if __name__ == "__main__":
    main()
