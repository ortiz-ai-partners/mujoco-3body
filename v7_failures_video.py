"""v7 failure footage (physics only) for ゆうころ to inspect:

  A  the duck tries the 16-degree ramp, backs off, tries again, gives up and sits down
  B  the crab walks up the same ramp under its official locomotion policy (can it?)
  C  the crab pounces, the duck falls and does not get up (under investigation)

    <jumper venv python> v7_failures_video.py   -> out/v7_failures_physics_only.mp4
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock, Video, quat_to_yaw
from v6_robots import body_tilt_deg, build_arena, robots_in_contact
from v7_full import official_md_servos, wrap
from v7_policies import MD_CONTROL_DT, JumperJump, JumperLocomotion, MicroduckPolicy, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"
TITLE = "v7 失敗集 | 物理のみ・外力なし（公式ポリシー＋自前のサーボ）"


class Shot:
    def __init__(self, model, data, video, cap, lookat, distance, azimuth, elevation, speed=1.0):
        self.model, self.data, self.video, self.cap = model, data, video, cap
        self.renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[1] = 0
        self.cam = CameraRig(lookat=lookat, distance=distance, azimuth=azimuth, elevation=elevation, tau=0.6)
        self.cam.snap()
        self.clock = FrameClock(VIDEO_FPS, speed)
        self.clock.next_t = data.time

    def frame(self, lookat, lines, footer, distance=None):
        if self.clock.due(self.data.time):
            self.cam.aim(lookat=lookat, distance=distance)
            self.renderer.update_scene(self.data, self.cam.step(1.0 / VIDEO_FPS), self.opt)
            self.video.add(self.cap.draw(self.renderer.render(), TITLE, lines, footer=footer))

    def close(self):
        self.renderer.close()


def duck_steer(pol, data, target, vx=0.3):
    d = np.asarray(target) - data.xpos[pol.bid][:2]
    err = wrap(math.atan2(d[1], d[0]) - quat_to_yaw(data.xquat[pol.bid]))
    pol.twist[:] = (vx if abs(err) < 0.6 else 0.0, 0.0, float(np.clip(2.5 * err, -1.5, 1.5)))
    return float(np.linalg.norm(d))


def scene_a(video, cap):
    model, data = build_arena(STAGE_XML, md_pose=(1.2, -3.0, math.pi / 2), timestep=0.005)
    official_md_servos(model)
    vel = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
    sit = MicroduckPolicy(model, data, POLICY_DIR / "alpha_sitstand.onnx")
    vel.hold_default(data)
    pol = vel
    shot = Shot(model, data, video, cap, lookat=data.xpos[vel.bid], distance=1.7, azimuth=15, elevation=-10)
    steps = round(MD_CONTROL_DT / model.opt.timestep)
    # (until, phase)
    plan = [(1.0, "stand"), (13.0, "try1"), (15.5, "back"), (25.5, "try2"), (26.5, "handover"), (32.0, "sit")]
    labels = {"stand": "立位", "try1": "坂に挑む（1 回目）", "back": "いったん後ずさり", "try2": "もう一回挑む（2 回目）",
              "handover": "やっぱり無理…", "sit": "諦めて座り込む（sitstand）"}
    k, y_max = 0, -9.0
    while data.time < plan[-1][0]:
        t = data.time
        phase = next(p for u, p in plan if t < u)
        if phase in ("try1", "try2"):
            duck_steer(pol, data, (1.2, 3.0))
        elif phase == "back":
            pol.twist[:] = (-0.3, 0.0, 0.0)
        elif phase == "handover":
            if pol is vel:
                sit.reset()
                sit.last_action[:] = vel.last_action
                pol = sit
            pol.twist[:] = (0.0, 0.0, 0.0)
            pol.head[:] = (0.3, 0.4, 0, 0)
        elif phase == "sit":
            pol.twist[:] = (1.0, 0.0, 0.0)
            pol.head[:] = (0.3, 0.5, 0, 0)
        else:
            pol.twist[:] = 0
        if k % steps == 0:
            pol.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        p = data.xpos[vel.bid]
        y_max = max(y_max, float(p[1]))
        shot.frame([p[0], p[1], 0.12],
                   [f"A パッカン: {labels[phase]}", f"y={p[1]:+.2f} m（坂の入口 y=-1.86）  高さ {p[2]:.3f}  傾き {body_tilt_deg(data, vel.bid):4.1f}°"],
                   f"scene A  sim {t:5.1f} s")
        if k % 500 == 0:
            print(f"  A t={t:5.1f} {phase} y={p[1]:+.3f} z={p[2]:.3f} tilt={body_tilt_deg(data, vel.bid):.1f}")
    shot.close()
    print(f"scene A: farthest y = {y_max:+.3f} (ramp toe -1.86)")


def scene_b(video, cap):
    model, data = build_arena(STAGE_XML, jp_pose=(1.75, -3.3, math.pi / 2), timestep=0.001)
    loco = JumperLocomotion(model, data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    data.time = 0.0
    loco.reset()
    shot = Shot(model, data, video, cap, lookat=data.xpos[loco.bid], distance=2.2, azimuth=15, elevation=-12)
    k, z_max, y_max = 0, 0.0, -9.0
    while data.time < 28.0:
        t = data.time
        p = data.xpos[loco.bid]
        if t < 1.0:
            loco.set_command(0, 0, 0)
        elif p[1] < 2.9:
            d = np.array([1.75, 3.2]) - p[:2]
            err = wrap(math.atan2(d[1], d[0]) - quat_to_yaw(data.xquat[loco.bid]))
            loco.set_command(0.5 if abs(err) < 0.4 else 0.0, 0.0, float(np.clip(3.0 * err, -2.0, 2.0)))
        else:
            loco.set_command(0, 0, 0)
        if k % 5 == 0:
            loco.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        z_max, y_max = max(z_max, float(p[2])), max(y_max, float(p[1]))
        shot.frame([p[0], p[1], p[2]],
                   [f"B 跳跳: 坂を登る（公式 locomotion 0.5 m/s）", f"y={p[1]:+.2f} m  高さ {p[2]:.3f} m（天面なら ≈0.55）  傾き {body_tilt_deg(data, loco.bid):4.1f}°"],
                   f"scene B  sim {t:5.1f} s")
        if k % 2000 == 0:
            print(f"  B t={t:5.1f} y={p[1]:+.3f} z={p[2]:.3f} tilt={body_tilt_deg(data, loco.bid):.1f}")
        if np.any(np.isnan(data.qpos)):
            break
    shot.close()
    print(f"scene B: farthest y = {y_max:+.3f}, max z = {z_max:.3f}")


def scene_c(video, cap):
    model, data = build_arena(STAGE_XML, md_pose=(0.4, 2.7, 0.0), jp_pose=(-1.2, 2.7, 0.0), timestep=0.001)
    official_md_servos(model)
    md = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
    loco, jump = JumperLocomotion(model, data), JumperJump(model, data)
    md.hold_default(data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    data.time = 0.0
    loco.reset()
    md_root, jp_root = model.body_rootid[md.bid], model.body_rootid[loco.bid]
    shot = Shot(model, data, video, cap, lookat=data.xpos[md.bid], distance=1.5, azimuth=120, elevation=-14)
    mode, k, t_mode, t_fall = "walk", 0, 0.0, None
    while data.time < 22.0:
        t = data.time
        p_md, p_jp = data.xpos[md.bid], data.xpos[loco.bid]
        sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
        tilt = body_tilt_deg(data, md.bid)
        if tilt > 60 and t_fall is None:
            t_fall = t
            print(f"  C MD fell at t={t:.2f}")
        if k % 20 == 0:
            md.twist[:] = 0
            md.head[:] = 0
            md.step(model, data)
        if k % 5 == 0:
            if mode == "walk":
                d = p_md[:2] - p_jp[:2]
                err = wrap(math.atan2(d[1], d[0]) - quat_to_yaw(data.xquat[loco.bid]))
                loco.set_command(0.35 if abs(err) < 0.4 else 0.0, 0.0, float(np.clip(3.0 * err, -2.0, 2.0)))
                loco.step(model, data)
                if sep < 0.32 and abs(err) < 0.25:
                    mode, t_mode = "pause", t
                    loco.set_command(0, 0, 0)
            elif mode == "pause":
                loco.step(model, data)
                if t - t_mode > 0.4:
                    mode = "jump"
                    jump.reset(sweep=1.2)
                    set_pd_gains(model, jump.act_ids, jump.kp, jump.kd)
            elif mode == "jump":
                jump.step(model, data)
                if jump.finished():
                    mode, t_mode = "back", t
                    loco.reset()
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
                    loco.set_command(-0.3, 0, 0)
            elif mode == "back":
                loco.step(model, data)
                if sep > 1.1 or t - t_mode > 6.0:
                    mode = "idle"
                    loco.set_command(0, 0, 0)
            else:
                loco.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        if t_fall is not None and k % 2000 == 0:
            q = data.qpos[md.qpos_idx] - md.default
            print(f"  C t={t:5.1f} down {t - t_fall:4.1f}s tilt={tilt:5.1f} z={p_md[2]:.3f} touch={robots_in_contact(model, data, md_root, jp_root)} "
                  f"joints-default={np.array2string(q, precision=2)} grav={np.array2string(md.observe(model, data)[3:6], precision=2)} |a|={np.abs(md.last_action).max():.2f}")
        shot.frame([p_md[0], p_md[1], 0.1],
                   [f"C 跳跳: {mode}   パッカン: {'転倒' if tilt > 60 else '立位'}（velstand は動作中）",
                    f"パッカン 傾き {tilt:5.1f}°  高さ {p_md[2]:.3f}   間隔 {sep:.2f} m"],
                   f"scene C  sim {t:5.1f} s", distance=1.2 + 0.4 * min(sep, 2.0))
    shot.close()


def main():
    cap = Captioner()
    video = Video(OUT_DIR / "v7_failures_physics_only.mp4")
    scene_a(video, cap)
    scene_b(video, cap)
    scene_c(video, cap)
    size = video.close()
    print(f"Done: {video.path} ({size / 1024:.0f} KB, {video.frames} frames)")


if __name__ == "__main__":
    main()
