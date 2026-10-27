"""v7 check: crab walks up to the duck and forward-jumps into it - what does physics do?

MD: velstand, official servos, standing.  JP: locomotion with heading control, then a
forward jump (sweep 1.2).  No external forces.  dt = 0.001 (jumper contract).

    <jumper venv python> v7_test_collision.py [--sweep 1.2] [--jump-dist 0.55] [--preview DIR]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR, VIDEO_H, VIDEO_W, Captioner, CameraRig, quat_to_yaw
from v6_robots import body_tilt_deg, build_arena, robots_in_contact
from v7_policies import MD_CONTROL_DT, JumperJump, JumperLocomotion, MicroduckPolicy, set_pd_gains
from v7_progress_video import official_md_servos

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"
MD_POSE = (0.0, -0.5, math.pi / 2)
JP_POSE = (-1.6, -0.5, 0.0)
SIM_DT = 0.001


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", type=float, default=1.2)
    ap.add_argument("--jump-dist", type=float, default=0.55)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--seconds", type=float, default=14.0)
    ap.add_argument("--ram", action="store_true", help="no jump: walk at full speed into the duck")
    args = ap.parse_args()
    model, data = build_arena(STAGE_XML, md_pose=MD_POSE, jp_pose=JP_POSE, timestep=SIM_DT)
    official_md_servos(model)
    md = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
    loco, jump = JumperLocomotion(model, data), JumperJump(model, data)
    md.hold_default(data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    data.time = 0.0
    loco.reset()
    md_root, jp_root = model.body_rootid[md.bid], model.body_rootid[jump.bid]

    renderer = None
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=data.xpos[md.bid], distance=1.6, azimuth=120, elevation=-16, tau=0.5)
        next_shot = 0.0

    mode, k = "walk", 0
    events = []
    t_contact = t_fell = t_up = None
    md_fell = False
    md_steps = round(MD_CONTROL_DT / SIM_DT)
    while data.time < args.seconds:
        t = data.time
        p_md, p_jp = data.xpos[md.bid], data.xpos[jump.bid]
        d = p_md[:2] - p_jp[:2]
        dist = float(np.linalg.norm(d))
        if k % md_steps == 0:
            md.step(model, data)
        if k % 5 == 0:
            if mode == "walk":
                err = wrap(math.atan2(d[1], d[0]) - quat_to_yaw(data.xquat[jump.bid]))
                vx = (0.8 if dist < 1.2 else 0.35) if args.ram else 0.35
                loco.set_command(vx if abs(err) < 0.4 else 0.0, 0.0, float(np.clip(3.0 * err, -2.0, 2.0)))
                loco.step(model, data)
                if args.ram and t_contact is not None and t >= t_contact + 1.0:
                    mode = "after"
                    loco.set_command(0, 0, 0)
                    events.append((round(t, 2), "JP stops pushing"))
                elif not args.ram and dist < args.jump_dist and abs(err) < 0.25:
                    mode, t_pause = "pause", t
                    loco.set_command(0, 0, 0)
                    events.append((round(t, 2), f"JP within {dist:.2f} m, stops"))
            elif mode == "pause":
                loco.step(model, data)
                if t >= t_pause + 0.4:
                    mode = "jump"
                    jump.reset(sweep=args.sweep)
                    set_pd_gains(model, jump.act_ids, jump.kp, jump.kd)
                    events.append((round(t, 2), f"JP jumps (sweep {args.sweep})"))
            elif mode == "jump":
                jump.step(model, data)
                if jump.finished():
                    mode = "after"
                    loco.reset()
                    loco.set_command(0, 0, 0)
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
                    events.append((round(t, 2), "JP jump finished -> locomotion idle"))
            else:
                loco.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        touching = robots_in_contact(model, data, md_root, jp_root)
        if touching and t_contact is None:
            t_contact = t
            events.append((round(t, 2), "contact JP-MD"))
        md_tilt = body_tilt_deg(data, md.bid)
        if md_tilt > 60 and not md_fell:
            md_fell, t_fell = True, t
            events.append((round(t, 2), f"MD fell (tilt {md_tilt:.0f})"))
        if md_fell and t_up is None and md_tilt < 15 and p_md[2] > 0.10 and t > t_fell + 0.5:
            t_up = t
            events.append((round(t, 2), f"MD back on its feet after {t - t_fell:.1f} s"))
        if k % 250 == 0:
            print(f"  t={t:5.2f} [{mode}] dist={dist:.2f} MD z={p_md[2]:.3f} tilt={md_tilt:5.1f} "
                  f"JP z={p_jp[2]:.3f} tilt={body_tilt_deg(data, jump.bid):5.1f} touch={touching}")
        if renderer is not None and t >= next_shot:
            look = 0.5 * (p_md + p_jp)
            cam.aim(lookat=[look[0], look[1], 0.12], distance=1.2 + 0.5 * dist)
            cam.snap()
            renderer.update_scene(data, cam.cam, opt)
            imageio.imwrite(args.preview / f"col_t{t:05.2f}.png",
                            cap.draw(renderer.render(), "v7 | 跳跳がパッカンに飛びつく（物理のみ）", [f"JP {mode}"],
                                     footer=f"sim {t:5.2f} s"))
            next_shot += 0.5
        if np.any(np.isnan(data.qpos)):
            print("NaN!")
            break
    print("events:")
    for e in events:
        print(f"  {e[0]:6.2f}s  {e[1]}")
    print(f"final: MD z={data.xpos[md.bid][2]:.3f} tilt={body_tilt_deg(data, md.bid):.1f}  "
          f"JP z={data.xpos[jump.bid][2]:.3f} tilt={body_tilt_deg(data, jump.bid):.1f}")


if __name__ == "__main__":
    main()
