"""v6 Phase 3 - Jumper hops in, touches Microduck, MD falls and is helped back up.

Stage = out/v6_stage_built.xml (Phase 1 result).  MD walks as in Phase 2;
JP (jumper) starts to the side, hops toward MD with its PD-driven legs plus a
guidance force (demo aid), the contact is real physics, the harness lets go
so MD falls, then the harness pulls MD upright again (assisted recovery, not
a self-righting policy) and MD resumes walking.

    python v6_phase3_jp_contact.py --test          # no render: metrics log
    python v6_phase3_jp_contact.py --preview DIR   # stills
    python v6_phase3_jp_contact.py                 # -> out/v6_phase3_jp_contact.mp4
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock, Video
from v6_robots import JumperCtrl, MicroduckCtrl, body_tilt_deg, build_arena, robots_in_contact

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
MD_POSE = (-0.3, -1.8, math.pi / 2)
MD_SPEED = 0.15
JP_START = (-2.3, -0.3)
CONTROL_DT = 0.02
T_WALK, T_HOP, DURATION = 1.0, 3.0, 22.0
FALL_TILT_DEG, FALL_Z = 55.0, 0.07
T_LIE, T_RECOVER = 1.5, 2.0

MODE_TEXT = {"STAND": "立位", "WALK": "歩行（スクリプト歩容＋仮想ハーネス）",
             "HIT": "接触！（ハーネス解除、物理のまま）",
             "FALLEN": "転倒（ハーネス解除、物理のまま）",
             "RECOVER": "復帰（仮想ハーネスで引き起こし＝演出用補助）"}
JP_TEXT = {"STAND": "待機", "HOP": "ホップで接近", "FLEE": "逃走！", "REST": "休憩",
           "FLIPPED": "ひっくり返った（物理のまま）"}
FLEE_DIST = 2.5
FLIP_TILT_DEG = 120.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--azimuth", type=float, default=45.0)
    ap.add_argument("--elevation", type=float, default=-16.0)
    args = ap.parse_args()

    jp_yaw = math.atan2(MD_POSE[1] + 1.5 - JP_START[1], MD_POSE[0] - JP_START[0])
    model, data = build_arena(STAGE_XML, md_pose=MD_POSE, jp_pose=(*JP_START, jp_yaw))
    md = MicroduckCtrl(model, data, MD_POSE, speed=MD_SPEED)
    jp = JumperCtrl(model, data)
    print(f"MuJoCo {mujoco.__version__} | Phase 3 | dt={model.opt.timestep} nq={model.nq} "
          f"nu={model.nu} ngeom={model.ngeom} | MD {md.mass:.2f} kg  JP {jp.mass:.2f} kg")

    render = not args.test
    video = None
    preview_times = []
    if render:
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0          # jumper collision meshes
        cap = Captioner()
        cam = CameraRig(lookat=md.pos(data), distance=2.2, azimuth=args.azimuth,
                        elevation=args.elevation, tau=0.8)
        cam.snap()
        clock = FrameClock(VIDEO_FPS, 1.0)
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            preview_times = [0.5, 5.0, 7.0, 9.0, 11.0, 13.0, 16.0, 21.0]
        else:
            video = Video(OUT_DIR / "v6_phase3_jp_contact.mp4")

    def render_frame():
        p_md, p_jp = md.pos(data), jp.pos(data)
        sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
        look = 0.6 * p_md + 0.4 * p_jp
        look[2] = 0.12
        cam.aim(lookat=look, distance=1.6 + 0.6 * min(sep, 2.5))
        renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
        frame = renderer.render()
        return cap.draw(frame, "Phase 3 | 跳跳が接近 → 接触 → パッカン転倒 → 復帰",
                        [f"パッカン: {MODE_TEXT.get(md.mode, md.mode)}" + ("   ガーガー…" if md.quack else ""),
                         f"跳跳: {JP_TEXT.get(jp.mode, jp.mode)}   誘導力 "
                         f"{np.linalg.norm(data.xfrc_applied[jp.bid, :2]):.1f} N（演出用補助）"],
                        footer=f"sim {data.time:5.1f} s   x1")

    substeps = round(CONTROL_DT / model.opt.timestep)
    md_root = model.body_rootid[md.bid]
    jp_root = model.body_rootid[jp.bid]
    log, events = [], []
    t_contact = None
    noticed = False
    flee_target = None
    for k in range(int(DURATION / CONTROL_DT)):
        t = k * CONTROL_DT
        p_md, p_jp = md.pos(data).copy(), jp.pos(data).copy()
        sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
        # scenario
        if md.mode == "STAND" and t >= T_WALK and not noticed:
            md.set_mode("WALK", t)
        if jp.mode == "STAND" and t >= T_HOP:
            jp.set_mode("HOP", t)
        if md.mode == "WALK" and jp.mode == "HOP" and sep < 1.1 and not noticed:
            noticed = True
            md.set_mode("STAND", t)                 # MD notices the crab and stops to look
            events.append({"t": round(t, 2), "event": "MD stops, looks at JP"})
        md.gaze = p_jp[:2] if (jp.mode != "STAND" and t_contact is None) else None
        touching = robots_in_contact(model, data, md_root, jp_root)
        if touching and t_contact is None:
            t_contact = t
            events.append({"t": round(t, 2), "event": "contact JP-MD"})
            md.harness = 0.0
            md.set_mode("HIT", t)
        if md.mode == "HIT":
            if md.tilt_deg(data) > FALL_TILT_DEG or p_md[2] < FALL_Z:
                md.set_mode("FALLEN", t)
                events.append({"t": round(t, 2), "event": "MD fell"})
            elif t >= md.t_mode + 2.0:
                md.set_mode("RECOVER", t)         # shoved but still standing
                md.rebase(data)
        jp_tilt = body_tilt_deg(data, jp.bid)
        if jp.mode in ("HOP", "FLEE") and t_contact is not None and jp_tilt > FLIP_TILT_DEG \
                and t >= t_contact + 0.5:
            jp.set_mode("FLIPPED", t)
            events.append({"t": round(t, 2), "event": "JP flipped onto its back"})
        if jp.mode == "HOP" and t_contact is not None and t >= t_contact + 0.6:
            away = p_jp[:2] - p_md[:2]
            away /= max(1e-6, np.linalg.norm(away))
            flee_target = p_jp[:2] + away * FLEE_DIST
            jp.set_mode("FLEE", t)
        if jp.mode == "FLEE" and (np.linalg.norm(flee_target - p_jp[:2]) < 0.3 or t >= jp.t_mode + 6.0):
            jp.set_mode("REST", t)
        if md.mode == "FALLEN" and t >= md.t_mode + T_LIE:
            md.set_mode("RECOVER", t)
            md.rebase(data)
            away = p_md[:2] - p_jp[:2]
            md.anchor = p_md[:2] + away / max(1e-6, np.linalg.norm(away)) * 0.35   # get clear of the crab first
        if md.mode == "RECOVER":
            md.harness = min(1.0, (t - md.t_mode) / T_RECOVER)
            if md.harness >= 1.0 and md.tilt_deg(data) < 15.0:
                md.set_mode("WALK", t)
                if jp.mode == "FLIPPED":
                    md.walk_to(p_jp[:2], data)          # go and check on the crab
                    events.append({"t": round(t, 2), "event": "MD walks to the flipped JP"})
                else:
                    md.rebase(data)
        if md.mode == "WALK" and md.goal is not None and md.arrived:
            md.set_mode("STAND", t)
            md.gaze = p_jp[:2]
            md.quack = True
            events.append({"t": round(t, 2), "event": "MD looks at JP, quacks"})
        if md.mode == "STAND" and md.quack:
            md.gaze = p_jp[:2]
        # controllers + physics
        md.step(model, data, t, CONTROL_DT)
        jp.step(model, data, t, CONTROL_DT,
                target_xy=flee_target if jp.mode == "FLEE" else p_md[:2])
        for _ in range(substeps):
            mujoco.mj_step(model, data)
            if video is not None and clock.due(data.time):
                video.add(render_frame())
        if preview_times and data.time >= preview_times[0]:
            cam.snap()
            imageio.imwrite(args.preview / f"p3_t{preview_times[0]:04.1f}.png", render_frame())
            preview_times.pop(0)
        if k % 25 == 0:
            p_md, p_jp = md.pos(data), jp.pos(data)
            row = {"t": round(t, 2), "md": md.mode, "jp": jp.mode,
                   "md_z": round(float(p_md[2]), 3), "md_tilt": round(md.tilt_deg(data), 1),
                   "jp_z": round(float(p_jp[2]), 3), "jp_zmax": round(jp.z_max, 3),
                   "jp_tilt": round(body_tilt_deg(data, jp.bid), 1),
                   "sep": round(float(np.linalg.norm(p_md[:2] - p_jp[:2])), 2),
                   "jp_v": round(float(np.linalg.norm(data.qvel[jp.dadr:jp.dadr + 2])), 2),
                   "touch": bool(touching)}
            log.append(row)
            print(row)
        if np.any(np.isnan(data.qpos)):
            print(f"NaN at t={t:.2f}")
            break

    if render:
        renderer.close()
    summary = {"contact_t": t_contact, "md_events": md.events, "jp_events": jp.events,
               "events": events, "jp_hop_zmax": round(jp.z_max, 3)}
    print(json.dumps(summary, ensure_ascii=False))
    if video is not None:
        size = video.close()
        report = {"video": str(video.path), "frames": video.frames, "bytes": size,
                  "md_pose": MD_POSE, "jp_start": JP_START, **summary, "log": log}
        (OUT_DIR / "v6_phase3_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                       encoding="utf-8")
        print(f"Done: {video.path} ({size / 1024:.0f} KB, {video.frames} frames)")


if __name__ == "__main__":
    main()
