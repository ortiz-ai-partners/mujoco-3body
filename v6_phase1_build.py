"""v6 Phase 1 - the bulldozer builds the two-slope course (こもれびの小さな峠).

Physics and control come unchanged from physical-ai-course-builder
(Simulation + SlopeAssembly: rule control, free-body parts, no teleport).
This script only adds offscreen time-lapse rendering and saves the finished
stage as an independent scene (out/v6_stage_built.xml) for the later phases.

    python v6_phase1_build.py                 # -> out/v6_phase1_build.mp4
    python v6_phase1_build.py --preview DIR   # stills only, to check framing
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import (OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig,
                       FrameClock, Video, body_poses, built_stage_xml, course_builder,
                       settle_check)

SPEED = 4.0
BUILD_SECONDS_EST = 200.0   # measured 197 s on MuJoCo 3.11; drives the slow camera orbit
COURSE_CENTER = np.array([1.5, 0.0, 0.2])
TARGETS = {"up_1": (1.5, -1.0), "down_1": (1.5, 1.05)}

PHASE_TEXT = {
    "UP": "上り坂を運搬・設置",
    "RAISE_UP": "フォークを上げる",
    "TO_DOWN": "空荷で下り坂の置き場へ",
    "PRECISE_LANE": "レーン位置合わせ",
    "ALIGN": "向きを合わせる",
    "RETREAT_FOR_ALIGNMENT": "後退して差し込み準備",
    "LOWER": "フォークを下げる",
    "DOWN": "下り坂を運搬・設置",
    "RAISE_DOWN": "フォークを上げる",
    "TO_START": "スタート地点へ移動",
    "CROSS": "完成した峠を走破",
}


def phase_label(pilot):
    if pilot.done:
        return "施工完了" if pilot.success else f"停止: {pilot.reason}"
    return PHASE_TEXT.get(pilot.phase, pilot.phase)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path, help="save stills to this directory instead of a video")
    ap.add_argument("--speed", type=float, default=SPEED, help="time-lapse factor")
    ap.add_argument("--az-start", type=float, default=55.0, help="camera azimuth at t=0")
    ap.add_argument("--az-end", type=float, default=140.0, help="camera azimuth at the end")
    ap.add_argument("--elevation", type=float, default=-38.0)
    ap.add_argument("--distance", type=float, default=6.0, help="base distance; grows with spread")
    args = ap.parse_args()

    app, slope_assembly, _ = course_builder()
    xml = slope_assembly.assembly_xml(app.ROOT / "scene_fork_tracks.xml")
    sim = app.Simulation(scene_xml=xml)
    pilot = slope_assembly.SlopeAssembly(sim)
    model, data = sim.model, sim.data
    print(f"MuJoCo {mujoco.__version__} | Phase 1 build | dt={model.opt.timestep} "
          f"nq={model.nq} ngeom={model.ngeom} | x{args.speed:g}")

    renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
    opt = mujoco.MjvOption()
    cap = Captioner()
    cam = CameraRig(lookat=[-0.5, 0, 0.2], distance=args.distance + 2.5,
                    azimuth=args.az_start, elevation=args.elevation, tau=1.5)
    cam.snap()
    clock = FrameClock(VIDEO_FPS, args.speed)
    video = None if args.preview else Video(OUT_DIR / "v6_phase1_build.mp4")
    preview_times = [0.5, 15, 40, 70, 100, 130, 160, 190] if args.preview else []
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)

    timeline = []
    last_phase = None
    t_wall = time.perf_counter()

    def render_frame():
        sim.tracks.update(model, data)
        mujoco.mj_forward(model, data)
        dozer = data.body("dozer").xpos
        spread = float(np.linalg.norm(dozer[:2] - COURSE_CENTER[:2]))
        look = 0.5 * dozer + 0.5 * COURSE_CENTER
        look[2] = 0.2
        u = min(1.0, data.time / BUILD_SECONDS_EST)
        orbit = u * u * (3 - 2 * u)
        cam.aim(lookat=look, distance=args.distance + 0.6 * spread,
                azimuth=args.az_start + (args.az_end - args.az_start) * orbit)
        renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
        frame = renderer.render()
        return cap.draw(frame, "Phase 1 | ブルドーザーがコースを施工（ルール制御・物理）",
                        [phase_label(pilot), pilot.stage],
                        footer=f"sim {data.time:6.1f} s   x{clock.speed:g}")

    while not pilot.done:
        action = pilot.action(sim)
        if pilot.phase != last_phase:
            timeline.append({"t": round(float(data.time), 2), "phase": pilot.phase})
            last_phase = pilot.phase
            print(f"  t={data.time:7.2f}s  {pilot.phase:<22s} wall {time.perf_counter() - t_wall:5.0f}s")
        sim.step(*action)
        if video is not None:
            if clock.due(data.time):
                video.add(render_frame())
        elif preview_times and data.time >= preview_times[0]:
            cam.snap()
            imageio.imwrite(args.preview / f"p1_t{int(preview_times[0]):03d}.png", render_frame())
            preview_times.pop(0)

    print(f"Construction finished: success={pilot.success} t={data.time:.2f}s "
          f"reason='{pilot.reason}' wall {time.perf_counter() - t_wall:.0f}s")

    # Outro: hold on the finished course at real time.
    clock.speed = 1.0
    for _ in range(int(2.5 / app.CONTROL_DT)):
        sim.step(0, 0, 0)
        if video is not None and clock.due(data.time):
            video.add(render_frame())
    if args.preview:
        imageio.imwrite(args.preview / "p1_final.png", render_frame())
    renderer.close()

    sim.observe()
    poses = body_poses(model, data)
    stage_xml = built_stage_xml(xml, poses)
    (OUT_DIR / "v6_stage_built.xml").write_text(stage_xml, encoding="utf-8")
    drift = settle_check(stage_xml)
    errors = {n: float(np.linalg.norm(np.array(poses[n]["pos"][:2]) - np.array(t)))
              for n, t in TARGETS.items() if n in poses}
    report = {
        "mujoco": mujoco.__version__,
        "success": bool(pilot.success),
        "reason": pilot.reason,
        "seconds": round(float(data.time), 2),
        "placement_errors_m": errors,
        "parts": pilot.results,
        "vehicle_rise_m": pilot.max_rise,
        "surfaces_touched": len(pilot.touched),
        "timeline": timeline,
        "poses": poses,
        "stage_xml": str(OUT_DIR / "v6_stage_built.xml"),
        "stage_xml_settle_drift_m": drift,
        "video": None if video is None else {"path": str(video.path), "frames": video.frames,
                                             "speed": args.speed},
    }
    if video is not None:
        report["video"]["bytes"] = video.close()
    (OUT_DIR / "v6_phase1_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("timeline", "poses")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
