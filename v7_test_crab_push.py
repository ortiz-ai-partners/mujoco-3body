"""Can the crab push the duck up the 16-degree ramp?  (ゆうころ 10/28: the crab helps instead of the bulldozer -
"a beautiful friendship"; the bulldozer must not handle the duck, lifting by the neck could break it.)

    <jumper venv python> v7_test_crab_push.py [--crab-vx 0.3 0.5] [--seconds 60] [--video out/v7_crab_push.mp4]

The duck (velstand, official servos) is commanded to walk north up the ramp from its toe; the crab
(official locomotion) walks behind it, aiming just ahead of the duck so its body keeps pressing on the
duck's back.  Physics only.  Reports the duck's progress, falls and recoveries, and contact.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np

from v6_common import OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, Video
from v6_robots import build_arena, robots_in_contact
from v7_full import CONTROL_DT, Crab, Duck, official_md_servos
from v7_policies import MD_CONTROL_DT

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
LANE_X = 1.22
TOE_Y = -2.0


def run(crab_vx, seconds, video_path=None, duck_vx=0.3, gap=0.35, crab_height=0.0, approach_vx=0.12):
    model, data = build_arena(STAGE_XML, md_pose=(LANE_X, TOE_Y - 0.35, math.pi / 2),
                              jp_pose=(LANE_X, TOE_Y - 0.35 - gap - 0.3, math.pi / 2), timestep=0.001)
    official_md_servos(model)
    duck, crab = Duck(model, data), Crab(model, data)
    md_root, jp_root = model.body_rootid[duck.bid], model.body_rootid[crab.bid]
    substeps, md_every, jp_every = round(CONTROL_DT / 0.001), round(MD_CONTROL_DT / 0.001), 5
    t, k = 0.0, 0
    rec = {"crab_vx": crab_vx, "duck_vx": duck_vx, "max_y": -9.0, "max_z": 0.0, "falls": 0, "recoveries": 0,
           "contact_s": 0.0, "events": []}
    video = None
    if video_path:
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=[LANE_X, -1.5, 0.2], distance=2.6, azimuth=15, elevation=-14, tau=0.8)
        cam.snap()
        video = Video(Path(video_path))
        next_frame = 0.0

    def tick():
        nonlocal t, k, next_frame
        duck.control(data, t)
        for _ in range(substeps):
            if k % md_every == 0:
                duck.step(model, data)
            if k % jp_every == 0:
                crab.step(model, data)
            mujoco.mj_step(model, data)
            k += 1
        t += CONTROL_DT
        if video is not None and data.time >= next_frame:
            next_frame += 1.0 / VIDEO_FPS
            look = 0.5 * (duck.pos(data) + crab.pos(data))
            look[2] = 0.2
            cam.aim(lookat=look)
            renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
            video.add(cap.draw(renderer.render(), "v7 | 跳跳がパッカンを坂で押し上げる実験 ― 公式ポリシー、物理のみ",
                               [f"パッカン: {duck.mode}  y={duck.pos(data)[1]:+.2f} z={duck.pos(data)[2]:.2f} 傾き {duck.tilt(data):3.0f}°",
                                f"跳跳: locomotion {crab_vx:.1f} m/s  接触 {'あり' if robots_in_contact(model, data, md_root, jp_root) else 'なし'}"],
                               footer=f"sim {t:5.1f} s"))

    for _ in range(int(1.0 / CONTROL_DT)):              # settle on their feet
        tick()
    duck.walk_to((LANE_X, 3.0), t, stop_dist=0.3)
    crab.set_mode("WALK", t, model)
    crab.loco.posture[3] = crab_height                    # posture command: body height above neutral (push at trunk level)
    was_fallen = False
    rec["crab_height"] = crab_height
    while t < seconds + 1.0:
        p_md, p_jp = duck.pos(data), crab.pos(data)
        if duck.mode == "WALK":
            duck.goal = np.array([LANE_X, p_md[1] + 1.0])              # keep walking up the lane
            duck.steer(data, duck.goal, vx=duck_vx)
        elif duck.mode == "STAND":
            duck.walk_to((LANE_X, p_md[1] + 1.0), t, stop_dist=0.3)
        # the crab aims a little ahead of the duck so it keeps pushing; it holds back when the duck is down
        touching = robots_in_contact(model, data, md_root, jp_root)
        if duck.mode == "FALLEN":
            crab.loco.set_command(0, 0, 0)                            # hold still: never shove a fallen duck
        elif not touching and p_jp[1] < p_md[1] - 0.45:
            crab.steer(data, (LANE_X, p_md[1] + 0.15), approach_vx)   # close the gap gently
        else:
            crab.steer(data, (LANE_X, p_md[1] + 0.15), crab_vx)       # sustained push, matched to the duck
        tick()
        touching = robots_in_contact(model, data, md_root, jp_root)
        rec["contact_s"] += CONTROL_DT if touching else 0.0
        rec["max_y"] = max(rec["max_y"], float(p_md[1]))
        rec["max_z"] = max(rec["max_z"], float(p_md[2]))
        if duck.mode == "FALLEN" and not was_fallen:
            rec["falls"] += 1
            rec["events"].append(f"{t:5.1f}s duck fell at y={p_md[1]:+.2f} z={p_md[2]:.2f}")
        if was_fallen and duck.mode != "FALLEN":
            rec["recoveries"] += 1
            rec["events"].append(f"{t:5.1f}s duck back up at y={p_md[1]:+.2f}")
        was_fallen = duck.mode == "FALLEN"
        if k % int(5.0 / 0.001) == 0:
            rec["events"].append(f"{t:5.1f}s duck y={p_md[1]:+.2f} z={p_md[2]:.2f} tilt={duck.tilt(data):3.0f} {duck.mode} | "
                                 f"crab y={p_jp[1]:+.2f} z={p_jp[2]:.2f} | touching={touching}")
        if p_md[1] > 0.3 and p_md[2] > 0.4:
            rec["events"].append(f"{t:5.1f}s DUCK ON THE LANDING (y={p_md[1]:+.2f}, z={p_md[2]:.2f})")
            rec["landing_t"] = round(t, 1)
            break
        if np.any(np.isnan(data.qpos)):
            rec["events"].append("NaN")
            break
    rec.update(end_y=round(float(duck.pos(data)[1]), 2), end_z=round(float(duck.pos(data)[2]), 3),
               end_mode=duck.mode, max_y=round(rec["max_y"], 2), max_z=round(rec["max_z"], 3), contact_s=round(rec["contact_s"], 1))
    if video is not None:
        video.close()
        renderer.close()
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crab-vx", type=float, nargs="+", default=[0.3, 0.5])
    ap.add_argument("--duck-vx", type=float, default=0.3)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--crab-height", type=float, nargs="+", default=[0.0])
    ap.add_argument("--video", type=Path, help="record the first variant")
    args = ap.parse_args()
    i = 0
    for h in args.crab_height:
        for vx in args.crab_vx:
            rec = run(vx, args.seconds, video_path=args.video if (i == 0 and args.video) else None, duck_vx=args.duck_vx, crab_height=h)
            i += 1
            print(json.dumps({k: v for k, v in rec.items() if k != "events"}), flush=True)
            for e in rec["events"]:
                print("   ", e, flush=True)


if __name__ == "__main__":
    main()
