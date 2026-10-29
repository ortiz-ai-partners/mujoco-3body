"""v7 progress clip - physics only (no external forces), official policies + own servos.

Scene A: jumper walks (locomotion policy), turns, then three forward jumps (jump policy
         + backward leg sweep).
Scene B: microduck (velstand) rights itself from its back, walks, turns, and does the
         head choreography (peer down, tilt, straighten, look around).

    python v7_progress_video.py   -> out/v7_progress_physics_only.mp4
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock, Video
from v6_robots import body_tilt_deg, build_arena
from v7_policies import MD_CONTROL_DT, JumperJump, JumperLocomotion, MicroduckPolicy, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"
TITLE = "v7 | 物理のみ：外力なし、公式ポリシー＋自前のサーボ"


def official_md_servos(model):
    A = mujoco.mjtObj.mjOBJ_ACTUATOR
    for a in range(model.nu):
        if (mujoco.mj_id2name(model, A, a) or "").startswith("md-"):
            model.actuator_gainprm[a, 0] = 0.55
            model.actuator_biasprm[a, 1] = -0.55
            model.actuator_biasprm[a, 2] = 0.0
            model.actuator_forcerange[a] = [-0.96, 0.96]


def scene_jumper(video, cap):
    model, data = build_arena(STAGE_XML, jp_pose=(-2.0, -0.6, 0.0), timestep=0.001)
    loco, jump = JumperLocomotion(model, data), JumperJump(model, data)
    loco.hold_home(data)
    for _ in range(300):
        mujoco.mj_step(model, data)
    data.time = 0.0
    loco.reset()
    renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0
    cam = CameraRig(lookat=data.xpos[jump.bid], distance=1.6, azimuth=150, elevation=-16, tau=0.6)
    cam.snap()
    clock = FrameClock(VIDEO_FPS, 1.0)
    script = [(1.0, "loco", (0, 0, 0)), (5.0, "loco", (0.3, 0, 0)), (7.0, "loco", (0, 0, 1.0)),
              (9.0, "loco", (0.3, 0, 0)), (10.0, "loco", (0, 0, 0)),
              (11.6, "jump", 0.9), (12.4, "loco", (0, 0, 0)), (14.0, "jump", 0.9),
              (14.8, "loco", (0, 0, 0)), (16.4, "jump", 1.2), (18.0, "loco", (0, 0, 0))]
    mode, k, seg = "loco", 0, -1
    label = ""
    while data.time < script[-1][0]:
        t = data.time
        i = next(i for i, s in enumerate(script) if t < s[0])
        if i != seg:
            seg = i
            kind, arg = script[i][1], script[i][2]
            if kind == "jump":
                mode = "jump"
                jump.reset(sweep=arg)
                set_pd_gains(model, jump.act_ids, jump.kp, jump.kd)
                label = f"公式ジャンプ＋脚の後方掃き {arg:.1f} rad（前方ジャンプ）"
            else:
                if mode == "jump":
                    loco.reset()
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
                mode = "loco"
                loco.set_command(*arg)
                label = ("公式ロコモーション 前進 0.3 m/s" if arg[0] else
                         "公式ロコモーション 旋回 1.0 rad/s" if arg[2] else "公式ロコモーション 静止立位")
        if k % 5 == 0:
            if mode == "jump":
                jump.step(model, data)
                if jump.finished():
                    mode = "loco"
                    loco.reset()
                    set_pd_gains(model, loco.act_ids, 10.0, 0.5)
            else:
                loco.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        if clock.due(data.time):
            p = data.xpos[jump.bid]
            cam.aim(lookat=[p[0], p[1], 0.12])
            renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
            video.add(cap.draw(renderer.render(), TITLE,
                               [f"跳跳: {label}", f"高さ {p[2]:.3f} m  傾き {body_tilt_deg(data, jump.bid):4.1f}°"],
                               footer=f"scene A  sim {t:5.2f} s"))
    renderer.close()
    print(f"scene A done: moved {np.linalg.norm(data.xpos[jump.bid][:2] - np.array([-2.0, -0.6])):.2f} m")


def scene_microduck(video, cap):
    model, data = build_arena(STAGE_XML, md_pose=(-1.2, -0.6, 0.0), timestep=0.005)
    official_md_servos(model)
    pol = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "md-trunk_base_freejoint")
    adr = model.jnt_qposadr[jid]
    data.qpos[adr + 2] = 0.15
    data.qpos[adr + 3:adr + 7] = [0.0, 1.0, 0.0, 0.0]        # on its back: initial condition only
    data.qvel[:] = 0
    pol.hold_default(data)
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
    opt = mujoco.MjvOption()
    cam = CameraRig(lookat=data.xpos[pol.bid], distance=1.1, azimuth=150, elevation=-14, tau=0.6)
    cam.snap()
    clock = FrameClock(VIDEO_FPS, 1.0)
    # (until, twist, head, label)
    script = [(4.0, (0, 0, 0), (0, 0, 0, 0), "仰向けから自力で起き上がる（velstand）"),
              (9.0, (0.3, 0, 0), (0, 0, 0, 0), "歩行 指令 0.3 m/s（公式サーボ kp 0.55）"),
              (11.0, (0, 0, 1.5), (0, 0, 0, 0), "旋回 1.5 rad/s"),
              (12.0, (0, 0, 0), (0, 0, 0, 0), "静止"),
              (14.0, (0, 0, 0), (0.3, 0.4, 0, 0), "首を下げてのぞき込む"),
              (15.5, (0, 0, 0), (0.1, 0.1, 0, 0.3), "首をかしげる"),
              (17.0, (0, 0, 0), (0, 0, 0, 0), "まっすぐに戻す（ぐわぁぁ？）"),
              (18.2, (0, 0, 0), (0, 0, 0.8, 0), "きょろきょろ"),
              (19.4, (0, 0, 0), (0, 0, -0.8, 0), "きょろきょろ"),
              (20.4, (0, 0, 0), (0, 0, 0, 0), "静止")]
    k = 0
    steps = round(MD_CONTROL_DT / model.opt.timestep)
    while data.time < script[-1][0]:
        t = data.time
        until, twist, head, label = next(s for s in script if t < s[0])
        pol.twist[:] = twist
        pol.head[:] = head
        if k % steps == 0:
            pol.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        if clock.due(data.time):
            p = data.xpos[pol.bid]
            cam.aim(lookat=[p[0], p[1], 0.12])
            renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
            video.add(cap.draw(renderer.render(), TITLE,
                               [f"パッカン: {label}", f"高さ {p[2]:.3f} m  傾き {body_tilt_deg(data, pol.bid):5.1f}°"],
                               footer=f"scene B  sim {t:5.2f} s"))
        if k % 100 == 0:
            R = data.xmat[pol.bid].reshape(3, 3)
            print(f"  B t={t:5.2f} {label} z={data.xpos[pol.bid][2]:.3f} tilt={body_tilt_deg(data, pol.bid):5.1f} "
                  f"yaw={math.degrees(math.atan2(R[1, 0], R[0, 0])):6.1f}")
    renderer.close()


def main():
    cap = Captioner()
    video = Video(OUT_DIR / "v7_progress_physics_only.mp4")
    scene_jumper(video, cap)
    scene_microduck(video, cap)
    size = video.close()
    print(f"Done: {video.path} ({size / 1024:.0f} KB, {video.frames} frames)")


if __name__ == "__main__":
    main()
