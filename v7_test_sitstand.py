"""v7 check: velstand -> sitstand (sit, peer with the head while seated, stand) -> velstand.

    <jumper venv python> v7_test_sitstand.py [--preview DIR]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR, VIDEO_H, VIDEO_W, Captioner, CameraRig
from v6_robots import body_tilt_deg, build_arena
from v7_policies import MD_CONTROL_DT, MicroduckPolicy
from v7_progress_video import official_md_servos

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()
    model, data = build_arena(STAGE_XML, md_pose=(-1.0, -0.5, 0.0), timestep=0.005)
    official_md_servos(model)
    vel = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
    sit = MicroduckPolicy(model, data, POLICY_DIR / "alpha_sitstand.onnx")
    vel.hold_default(data)
    head_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "md-jaw_soft")
    # (until, policy, flag, head)
    script = [(2.0, "vel", 0.0, (0, 0, 0, 0)),
              (3.0, "sit", 0.0, (0, 0, 0, 0)),          # hand over while standing (flag 0 = stand)
              (6.0, "sit", 1.0, (0, 0, 0, 0)),          # sit
              (8.5, "sit", 1.0, (0.8, 0.9, 0, 0)),      # peer down while seated
              (10.0, "sit", 1.0, (0.3, 0.3, 0, 0.3)),   # tilt head
              (11.5, "sit", 1.0, (0, 0, 0, 0)),         # straighten
              (12.5, "sit", 1.0, (0, 0, 0.8, 0)),       # look around
              (13.5, "sit", 1.0, (0, 0, -0.8, 0)),
              (17.0, "sit", 0.0, (0, 0, 0, 0)),         # stand back up
              (19.0, "vel", 0.0, (0, 0, 0, 0)),         # back to velstand
              (22.0, "vel", 0.0, (0, 0, 0, 0))]
    renderer = None
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        cap = Captioner()
        cam = CameraRig(lookat=data.xpos[vel.bid], distance=0.9, azimuth=150, elevation=-10, tau=0.5)
        marks = [1.0, 4.0, 5.9, 8.0, 9.8, 13.0, 16.5, 21.0]
    steps = round(MD_CONTROL_DT / model.opt.timestep)
    k, cur = 0, None
    while data.time < script[-1][0]:
        t = data.time
        until, which, flag, head = next(s for s in script if t < s[0])
        pol = vel if which == "vel" else sit
        if pol is not cur:
            if cur is not None:
                pol.reset()
                pol.last_action[:] = cur.last_action      # hand over the last action too
            cur = pol
            print(f"  t={t:5.2f} -> {which}")
        pol.twist[:] = (flag if which == "sit" else 0.0, 0.0, 0.0)
        pol.head[:] = head
        if k % steps == 0:
            pol.step(model, data)
        mujoco.mj_step(model, data)
        k += 1
        if k % 100 == 0:
            p = data.xpos[vel.bid]
            print(f"  t={t:5.2f} {which} flag={flag} head={head} trunk z={p[2]:.3f} tilt={body_tilt_deg(data, vel.bid):5.1f} "
                  f"head z={data.xpos[head_bid][2]:.3f} head fwd={data.xpos[head_bid][0] - p[0]:+.3f}")
        if renderer is not None and marks and t >= marks[0]:
            cam.aim(lookat=[data.xpos[vel.bid][0], data.xpos[vel.bid][1], 0.1])
            cam.snap()
            renderer.update_scene(data, cam.cam, opt)
            imageio.imwrite(args.preview / f"sit_t{marks[0]:04.1f}.png",
                            cap.draw(renderer.render(), "v7 | パッカン 公式 sitstand（座る→のぞき込む→立つ）",
                                     [f"{which} flag={flag} head={head}"], footer=f"sim {t:5.2f} s"))
            marks.pop(0)
        if np.any(np.isnan(data.qpos)):
            print("NaN!")
            break
    print(f"final trunk z={data.xpos[vel.bid][2]:.3f} tilt={body_tilt_deg(data, vel.bid):.1f}")


if __name__ == "__main__":
    main()
