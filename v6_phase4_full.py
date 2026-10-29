"""v6 Phase 4 - the whole story in ONE continuous simulation (no resets, no teleports).

Note: this is the v6 version with demo aids (external forces).  The submitted story is v7_full.py,
which imports only ArenaSim and PHASE_TEXT from here and uses no external force.

  BUILD   BZ builds the two-slope course (SlopeAssembly, rule control, physics);
          MD wanders in the free area beyond the course (requirement: it wanders while the course is built).
  FOLLOW  When BZ starts crossing, MD comes over and follows it up the course,
          quacking (requirement: it follows BZ while quacking).
  CRAB    JP hops in, pounces on MD, MD falls and is helped up (virtual harness),
          JP ends up on its back; MD walks over and looks at it, worried.
  RESCUE  BZ drives over and nudges the crab back onto its feet with the fork;
          the crab hops away, MD quacks happily.

Demo aids (reported as such): MD harness / gaze / quack animation, JP hop
assist + guidance force, JP righting assist while BZ touches it.  Everything
else is MuJoCo physics.  Construction is the untouched course-builder code.

    python v6_phase4_full.py --test            # no render
    python v6_phase4_full.py --preview DIR     # stills at key moments
    python v6_phase4_full.py                   # -> out/3body_arena_v6.mp4 (+ chirps)
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
import wave
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import (OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock,
                       Video, course_builder, quat_to_yaw)
from v6_robots import (JumperCtrl, MicroduckCtrl, body_tilt_deg, build_arena, robots_in_contact,
                       upright_torque)

CONTROL_DT = 0.02
COURSE_X = 1.5
COURSE_CENTER = np.array([1.5, 0.0, 0.2])
MD_START = (4.0, 0.6, -math.pi / 2)
WANDER_ZONE = (3.0, 5.0, -1.8, 1.8)
WAIT_SPOT = (3.2, -2.6)
JP_PARK = (5.2, 2.6)
SPEED_BUILD, SPEED_FOLLOW, SPEED_ACTION = 4.0, 2.0, 1.0
FALL_TILT_DEG, FALL_Z, FLIP_TILT_DEG = 55.0, 0.07, 120.0
T_LIE, T_RECOVER = 1.5, 2.0

PHASE_TEXT = {
    "UP": "上り坂を運搬・設置", "RAISE_UP": "フォークを上げる", "TO_DOWN": "空荷で下り坂の置き場へ",
    "PRECISE_LANE": "レーン位置合わせ", "ALIGN": "向きを合わせる",
    "RETREAT_FOR_ALIGNMENT": "後退して差し込み準備", "LOWER": "フォークを下げる",
    "DOWN": "下り坂を運搬・設置", "RAISE_DOWN": "フォークを上げる", "TO_START": "スタート地点へ移動",
    "CROSS": "完成した峠を走破",
}
MD_TEXT = {"STAND": "立位", "WALK": "歩行", "HIT": "接触！", "FALLEN": "転倒（物理のまま）",
           "RECOVER": "復帰（ハーネス補助）"}
JP_TEXT = {"STAND": "待機", "HOP": "ホップで接近", "FLEE": "逃走！", "REST": "休憩",
           "FLIPPED": "ひっくり返った", "RIGHTING": "起き上がる（押し＋補助）"}


class ArenaSim:
    """What SlopeAssembly / Transport / Navigator need from course-builder's Simulation."""

    def __init__(self, model, data, tracks_mod):
        self.model, self.data = model, data
        self.lift_target = 0.0
        self.tracks = tracks_mod.TrackAnimation(model)

    def observe(self):
        mujoco.mj_forward(self.model, self.data)

    def command(self, forward=0.0, turn=0.0, lift=0.0):
        self.lift_target = float(np.clip(self.lift_target + lift * 0.3 * CONTROL_DT, 0, 0.5))
        left = float(np.clip(forward * 5.0 - turn * 4.0, -8, 8))
        right = float(np.clip(forward * 5.0 + turn * 4.0, -8, 8))
        self.data.ctrl[0:5] = [left, left, right, right, self.lift_target]


class Chirps:
    """Synthesised electronic voice for MD, placed on the video timeline."""

    def __init__(self):
        self.events = []

    def add(self, video_t, kind):
        self.events.append((float(video_t), kind))

    @staticmethod
    def _tone(f0, f1, dur, sr, amp=0.5, vib=0.0):
        n = int(dur * sr)
        tt = np.arange(n) / sr
        f = np.linspace(f0, f1, n) * (1 + vib * np.sin(2 * np.pi * 30 * tt))
        ph = 2 * np.pi * np.cumsum(f) / sr
        env = np.minimum(1.0, np.minimum(tt / 0.015, (dur - tt) / 0.04))
        return amp * env * (np.sin(ph) + 0.25 * np.sin(2 * ph))

    def wav(self, path, length_s, sr=22050):
        out = np.zeros(int((length_s + 1.0) * sr))
        for t0, kind in self.events:
            if kind == "happy":
                parts = [(1300, 1900, 0.12, 0.0), (0, 0, 0.05, 0), (1600, 2400, 0.16, 0.02)]
            elif kind == "worried":
                parts = [(1500, 850, 0.30, 0.03), (0, 0, 0.12, 0), (1400, 800, 0.34, 0.03)]
            else:   # "quack": excited gaa-gaa
                parts = [(950, 820, 0.17, 0.08), (0, 0, 0.07, 0), (980, 840, 0.19, 0.08)]
            cursor = int(t0 * sr)
            for f0, f1, dur, vib in parts:
                n = int(dur * sr)
                if f0 > 0 and cursor + n < len(out):
                    out[cursor:cursor + n] += self._tone(f0, f1, dur, sr, vib=vib)
                cursor += n
        out = np.clip(out, -1, 1)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--until", default="END", help="stop after this stage (test)")
    ap.add_argument("--max-sim", type=float, default=330.0)
    ap.add_argument("--dt-build", type=float, default=0.005,
                    help="physics step during construction (0.005 is what course-builder validated)")
    ap.add_argument("--dt-action", type=float, default=0.002, help="physics step once BZ is done")
    args = ap.parse_args()

    app, slope_assembly, tracks_mod = course_builder()
    xml = slope_assembly.assembly_xml(app.ROOT / "scene_fork_tracks.xml")
    model, data = build_arena(xml, md_pose=MD_START, jp_pose=(*JP_PARK, math.pi), timestep=args.dt_build)
    for _ in range(100):                      # settle, as course-builder's Simulation.reset does
        mujoco.mj_step(model, data)
    data.time = 0.0
    sim = ArenaSim(model, data, tracks_mod)
    pilot = slope_assembly.SlopeAssembly(sim)
    md = MicroduckCtrl(model, data, MD_START, speed=0.15)
    jp = JumperCtrl(model, data)
    nav = None
    rng = np.random.default_rng(7)
    print(f"MuJoCo {mujoco.__version__} | Phase 4 | dt={model.opt.timestep} nq={model.nq} "
          f"nu={model.nu} ngeom={model.ngeom}")

    render = not args.test
    video = None
    preview_marks = []
    chirps = Chirps()
    if render:
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=[-0.5, 0, 0.2], distance=8.5, azimuth=55, elevation=-38, tau=1.5)
        cam.snap()
        clock = FrameClock(VIDEO_FPS, SPEED_BUILD)
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
        else:
            video = Video(OUT_DIR / "3body_arena_v6_silent.mp4")

    stage = "BUILD"
    stage_t0 = 0.0
    events = []
    md_root, jp_root, bz_root = (model.body_rootid[md.bid], model.body_rootid[jp.bid],
                                 model.body_rootid[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dozer")])
    bz_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dozer")
    wander_next, wander_wait = 0.0, 0.0
    quack_until, next_quack = -1.0, 2.0
    t_contact = None
    noticed = False
    wait_sent = False
    rescue_nudge_t0 = None
    last_phase = None

    def video_t():
        return (video.frames if video is not None else 0) / VIDEO_FPS

    def event(t, text):
        events.append({"t": round(t, 2), "video_t": round(video_t(), 2), "event": text})
        print(f"  t={t:7.2f}s  [{stage}] {text}")

    def set_stage(t, new):
        nonlocal stage, stage_t0
        stage, stage_t0 = new, t
        event(t, f"stage -> {new}")

    def quack(t, kind, dur=1.0):
        nonlocal quack_until
        md.quack = True
        quack_until = t + dur
        chirps.add(video_t(), kind)

    def caption(t):
        if stage == "BUILD":
            title = "Phase 4 | 施工（BZ：ルール制御・物理） ＋ パッカンうろちょろ"
            lines = [f"BZ: {PHASE_TEXT.get(pilot.phase, pilot.phase)}   {pilot.stage}",
                     f"パッカン: {MD_TEXT.get(md.mode, md.mode)}（歩容スクリプト＋仮想ハーネス）"]
        elif stage in ("FOLLOW_IN", "FOLLOW"):
            title = "Phase 4 | BZ が峠を走破 → パッカンが後をついていく"
            lines = [f"BZ: {PHASE_TEXT.get(pilot.phase, pilot.phase) if not pilot.done else '走破完了'}",
                     "パッカン: " + ("ガーガー！" if md.quack else "後をついていく") + "（仮想ハーネス補助）"]
        elif stage == "CRAB":
            title = "Phase 4 | 跳跳が接近 → 接触 → パッカン転倒 → 復帰"
            lines = [f"パッカン: {MD_TEXT.get(md.mode, md.mode)}" + ("   ガーガー…" if md.quack else ""),
                     f"跳跳: {JP_TEXT.get(jp.mode, jp.mode)}（ホップ補助・誘導力は演出用）"]
        else:
            title = "Phase 4 | BZ が助けに来る"
            lines = [f"BZ: {'接近' if nav is not None and not nav.done else '押して起こす'}",
                     f"跳跳: {JP_TEXT.get(jp.mode, jp.mode)}   パッカン: "
                     + ("ガーガー！" if md.quack else MD_TEXT.get(md.mode, md.mode))]
        return title, lines

    def render_frame():
        sim.tracks.update(model, data)
        mujoco.mj_forward(model, data)
        p_md, p_jp, p_bz = md.pos(data), jp.pos(data), data.xpos[bz_bid]
        if stage == "BUILD":
            spread = float(np.linalg.norm(p_bz[:2] - COURSE_CENTER[:2]))
            look = 0.5 * p_bz + 0.5 * COURSE_CENTER
            look[2] = 0.2
            u = min(1.0, data.time / 200.0)
            cam.aim(lookat=look, distance=6.0 + 0.6 * spread,
                    azimuth=55 + 85 * u * u * (3 - 2 * u), elevation=-38)
        elif stage in ("FOLLOW_IN", "FOLLOW"):
            look = p_md.copy() + np.array([0.0, 0.7, 0.0])
            look[2] = p_md[2] + 0.05
            cam.aim(lookat=look, distance=2.8, azimuth=95, elevation=-16)
        elif stage == "CRAB":
            sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
            look = 0.6 * p_md + 0.4 * p_jp
            look[2] = 0.12
            cam.aim(lookat=look, distance=1.7 + 0.6 * min(sep, 2.5), azimuth=120, elevation=-16)
        else:
            look = 0.5 * p_bz + 0.5 * p_jp
            look[2] = 0.15
            cam.aim(lookat=look, distance=3.2, azimuth=135, elevation=-22)
        renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
        title, lines = caption(data.time)
        return cap.draw(renderer.render(), title, lines,
                        footer=f"sim {data.time:6.1f} s   x{clock.speed:g}")

    t_wall = time.perf_counter()
    k = 0
    while stage != "END" and data.time < args.max_sim:
        t = k * CONTROL_DT
        k += 1
        substeps = round(CONTROL_DT / model.opt.timestep)
        p_md, p_jp, p_bz = md.pos(data).copy(), jp.pos(data).copy(), data.xpos[bz_bid].copy()

        # ── BZ ────────────────────────────────────────────────────────
        if stage in ("BUILD", "FOLLOW_IN", "FOLLOW", "CRAB") and not pilot.done:
            sim.command(*pilot.action(sim))
            if pilot.phase != last_phase:
                last_phase = pilot.phase
                event(t, f"BZ {pilot.phase}")
            if pilot.done:
                event(t, f"construction done: success={pilot.success} ({pilot.reason})")
                model.opt.timestep = args.dt_action
                event(t, f"physics step -> {args.dt_action}")
        elif stage == "RESCUE" and nav is not None and not nav.done:
            sim.command(*nav.action(sim))
        else:
            sim.command(0, 0, 0)

        # ── stage logic ───────────────────────────────────────────────
        if stage == "BUILD":
            if md.mode == "STAND" and t >= wander_next:
                target = (rng.uniform(WANDER_ZONE[0], WANDER_ZONE[1]),
                          rng.uniform(WANDER_ZONE[2], WANDER_ZONE[3]))
                md.walk_to(target, data, stop_dist=0.15)
                md.set_mode("WALK", t)
            if md.mode == "WALK" and md.arrived:
                md.set_mode("STAND", t)
                wander_next = t + rng.uniform(1.0, 3.0)
            if t >= next_quack and md.mode == "WALK":
                quack(t, "quack", 0.8)
                next_quack = t + rng.uniform(8.0, 16.0)
            if pilot.phase == "TO_START" and not wait_sent:
                wait_sent = True
                md.walk_to(WAIT_SPOT, data, stop_dist=0.2)
                md.set_mode("WALK", t)
                wander_next = 1e9
                event(t, "MD heads to the waiting spot by the course start")
            if wait_sent and md.mode == "WALK" and md.arrived:
                md.set_mode("STAND", t)
                md.gaze = p_bz[:2]
            if pilot.phase == "CROSS":
                set_stage(t, "FOLLOW_IN")
                md.gaze = None
                md.walk_to((COURSE_X, -3.4), data, stop_dist=0.2)
                md.speed = 0.3
                md.GAIT_HZ = 2.2
                md.set_mode("WALK", t)
                quack(t, "quack", 1.2)
                if render:
                    clock.speed = SPEED_FOLLOW
        elif stage == "FOLLOW_IN":
            if md.mode == "WALK" and md.arrived:
                set_stage(t, "FOLLOW")
                md.rebase(data)
                md.anchor = np.array([COURSE_X, p_md[1]])
                md.yaw = math.pi / 2
                md.heading = np.array([0.0, 1.0])
                md.terrain = True
                md.set_mode("WALK", t)
            md.gaze = p_bz[:2]
        elif stage == "FOLLOW":
            md.gaze = p_bz[:2]
            if t >= next_quack:
                quack(t, "quack", 1.0)
                next_quack = t + rng.uniform(2.5, 4.5)
            if md.tilt_deg(data) > 50.0 and md.mode == "WALK":
                md.set_mode("RECOVER", t)
                event(t, "MD stumbled on the course; harness rights it")
            if md.mode == "RECOVER":
                md.harness = min(1.0, (t - md.t_mode) / 1.0)
                if md.tilt_deg(data) < 15.0 and t >= md.t_mode + 1.0:
                    md.set_mode("WALK", t)
                    md.anchor = np.array([COURSE_X, p_md[1]])
                    md.path_s = 0.0
            if p_md[1] > 2.35 and md.mode == "WALK":
                md.set_mode("STAND", t)
                md.terrain = False
                md.z_des = 0.12
                event(t, "MD arrived behind BZ")
            if md.mode == "STAND" and p_md[1] > 2.3 and t >= md.t_mode + 2.0:
                set_stage(t, "CRAB")
                md.quack = False
                md.speed, md.GAIT_HZ = 0.15, 1.6
                jp.set_mode("HOP", t)
                if render:
                    clock.speed = SPEED_ACTION
        elif stage == "CRAB":
            sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
            if jp.mode == "HOP" and sep < 1.1 and not noticed:
                noticed = True
                md.set_mode("STAND", t)
                event(t, "MD notices the crab, stops to look")
                quack(t, "worried", 1.0)
            if t_contact is None:
                md.gaze = p_jp[:2]
            touching = robots_in_contact(model, data, md_root, jp_root)
            if touching and t_contact is None:
                t_contact = t
                md.harness = 0.0
                md.set_mode("HIT", t)
                event(t, "contact JP-MD")
            if md.mode == "HIT":
                if md.tilt_deg(data) > FALL_TILT_DEG or p_md[2] < FALL_Z:
                    md.set_mode("FALLEN", t)
                    event(t, "MD fell")
                elif t >= md.t_mode + 2.0:
                    md.set_mode("RECOVER", t)
                    md.rebase(data)
            jp_tilt = body_tilt_deg(data, jp.bid)
            if jp.mode in ("HOP", "FLEE") and t_contact is not None and jp_tilt > FLIP_TILT_DEG \
                    and t >= t_contact + 0.5:
                jp.set_mode("FLIPPED", t)
                event(t, "JP flipped onto its back")
            if jp.mode == "HOP" and t_contact is not None and t >= t_contact + 0.6:
                jp.set_mode("FLEE", t)
            if jp.mode == "FLEE" and t >= jp.t_mode + 5.0:
                jp.set_mode("REST", t)
            if md.mode == "FALLEN" and t >= md.t_mode + T_LIE:
                md.set_mode("RECOVER", t)
                md.rebase(data)
                away = p_md[:2] - p_jp[:2]
                md.anchor = p_md[:2] + away / max(1e-6, np.linalg.norm(away)) * 0.35
            if md.mode == "RECOVER":
                md.harness = min(1.0, (t - md.t_mode) / T_RECOVER)
                if md.harness >= 1.0 and md.tilt_deg(data) < 15.0:
                    md.set_mode("WALK", t)
                    md.walk_to(p_jp[:2], data, stop_dist=0.4)
                    event(t, "MD is up again, walks to the crab")
            if md.mode == "WALK" and md.goal is not None and md.arrived:
                md.set_mode("STAND", t)
                md.gaze = p_jp[:2]
                quack(t, "worried", 1.2)
                event(t, "MD looks at the crab, worried")
            if md.mode == "STAND" and md.goal is not None and md.arrived and t >= md.t_mode + 2.5:
                if jp.mode == "FLIPPED":
                    set_stage(t, "RESCUE")
                    side = p_jp[:2] + np.array([1.4, 0.0])
                    nav = app_navigator(sim, [[float(p_bz[0]) + 1.6, float(p_bz[1])],
                                              [float(side[0]) + 0.3, float(side[1]) + 0.9],
                                              [float(side[0]), float(side[1])]])
                    event(t, "BZ heads over to help the crab")
                else:
                    set_stage(t, "END")
        elif stage == "RESCUE":
            md.gaze = p_bz[:2] if jp.mode != "RIGHTING" else p_jp[:2]
            if nav.done and rescue_nudge_t0 is None:
                rescue_nudge_t0 = t
                event(t, f"BZ arrived ({nav.reason}); nudges the crab with the fork")
            if rescue_nudge_t0 is not None:
                if t < rescue_nudge_t0 + 4.0:
                    sim.command(0.25, 0.0, -1.0)
                else:
                    sim.command(-0.2 if t < rescue_nudge_t0 + 6.0 else 0.0, 0.0, 0.0)
                if jp.mode == "FLIPPED" and robots_in_contact(model, data, jp_root, bz_root):
                    jp.set_mode("RIGHTING", t)
                    event(t, "fork touches the crab; righting assist on")
            if jp.mode == "RIGHTING":
                jp.assist_upright = True
                if body_tilt_deg(data, jp.bid) < 25.0 and t >= jp.t_mode + 0.8:
                    jp.assist_upright = False
                    jp.set_mode("FLEE", t)
                    quack(t, "happy", 1.2)
                    event(t, "crab is back on its feet, hops away; MD is happy")
            if jp.mode == "FLEE" and t >= jp.t_mode + 5.0:
                jp.set_mode("REST", t)
                set_stage(t, "END")
            if rescue_nudge_t0 is not None and t >= rescue_nudge_t0 + 12.0:
                set_stage(t, "END")
        if md.quack and t >= quack_until:
            md.quack = False
        if stage == args.until and args.until != "END":
            set_stage(t, "END")

        # ── robots + physics ──────────────────────────────────────────
        md.step(model, data, t, CONTROL_DT)
        flee_target = (p_jp[:2] + (p_jp[:2] - p_md[:2]) / max(1e-6, np.linalg.norm(p_jp[:2] - p_md[:2])) * 2.5
                       if jp.mode == "FLEE" else p_md[:2])
        jp.step(model, data, t, CONTROL_DT, target_xy=flee_target)
        for _ in range(substeps):
            mujoco.mj_step(model, data)
            if video is not None and clock.due(data.time):
                video.add(render_frame())
        if args.preview and preview_marks is not None and int(t) % 20 == 0 and abs(t - int(t)) < 1e-6:
            cam.snap()
            imageio.imwrite(args.preview / f"p4_t{int(t):03d}.png", render_frame())
        if np.any(np.isnan(data.qpos)):
            event(t, "NaN in qpos - aborting")
            break
        if k % 500 == 0:
            print(f"  t={t:6.1f}s [{stage}] BZ {pilot.stage if not pilot.done else 'done'} "
                  f"@({p_bz[0]:+.2f},{p_bz[1]:+.2f}) MD({md.mode}) @({p_md[0]:+.2f},{p_md[1]:+.2f}) "
                  f"z={p_md[2]:.3f} tilt={md.tilt_deg(data):4.1f} JP({jp.mode}) "
                  f"wall {time.perf_counter() - t_wall:5.0f}s")

    # outro
    if video is not None:
        substeps = round(CONTROL_DT / model.opt.timestep)
        for _ in range(int(2.5 / CONTROL_DT)):
            sim.command(0, 0, 0)
            md.step(model, data, data.time, CONTROL_DT)
            jp.step(model, data, data.time, CONTROL_DT, target_xy=md.pos(data)[:2])
            for _ in range(substeps):
                mujoco.mj_step(model, data)
                if clock.due(data.time):
                    video.add(render_frame())
    if render:
        renderer.close()

    report = {"mujoco": mujoco.__version__, "sim_seconds": round(float(data.time), 2),
              "construction": {"success": bool(pilot.success), "reason": pilot.reason,
                               "parts": pilot.results, "rise_m": pilot.max_rise,
                               "surfaces": len(pilot.touched)},
              "events": events, "md_events": md.events, "jp_events": jp.events,
              "chirps": chirps.events}
    if video is not None:
        size = video.close()
        report["video_silent"] = {"path": str(video.path), "frames": video.frames, "bytes": size}
        wav = OUT_DIR / "3body_arena_v6_chirps.wav"
        chirps.wav(wav, video.frames / VIDEO_FPS)
        final = OUT_DIR / "3body_arena_v6.mp4"
        import imageio_ffmpeg
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(video.path), "-i", str(wav),
               "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(final)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        report["video"] = {"path": str(final), "ffmpeg_rc": res.returncode,
                           "bytes": final.stat().st_size if final.exists() else None}
        print(f"Done: {final} ({video.frames} frames, ffmpeg rc={res.returncode})")
    (OUT_DIR / "v6_phase4_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("events", "md_events", "jp_events", "chirps")},
                     indent=2, ensure_ascii=False))
    for e in events:
        print(f"  {e['t']:7.2f}s  {e['event']}")


def app_navigator(sim, waypoints):
    from navigation import Navigator
    return Navigator(sim, waypoints, allow_reverse=True)


if __name__ == "__main__":
    main()
