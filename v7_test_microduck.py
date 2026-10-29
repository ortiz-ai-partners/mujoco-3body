"""v7 check: Microduck under the official velstand policy in plain MuJoCo (XML PD servos, no forces).

    python v7_test_microduck.py [--dt 0.005] [--policy velstand.onnx] [--preview DIR]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR, VIDEO_H, VIDEO_W, Captioner, CameraRig
from v6_robots import MD_STAND_Z, body_tilt_deg, build_arena, yaw_quat
from v7_policies import MD_CONTROL_DT, MicroduckPolicy

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"
MD_POSE = (-1.0, -0.5, 0.0)
SCRIPT = [  # (until_s, vx, vy, wz, head(4))
    (3.0, 0.0, 0.0, 0.0, (0, 0, 0, 0)),
    (9.0, 0.15, 0.0, 0.0, (0, 0, 0, 0)),
    (11.5, 0.0, 0.0, 0.8, (0, 0, 0, 0)),
    (13.0, 0.0, 0.0, 0.0, (0, 0, 0, 0)),
    (15.0, 0.0, 0.0, 0.0, (0.3, 0.4, 0.0, 0.0)),     # peer down
    (17.0, 0.0, 0.0, 0.0, (0.0, 0.0, 0.0, 0.25)),    # tilt head
    (19.0, 0.0, 0.0, 0.0, (0.0, 0.0, 0.7, 0.0)),     # look left
    (21.0, 0.0, 0.0, 0.0, (0.0, 0.0, -0.7, 0.0)),    # look right
    (22.0, 0.0, 0.0, 0.0, (0, 0, 0, 0)),
]


def lie_down(model, data, pol, how):
    """Initial condition only (no force): put the robot on its side or back and let it settle."""
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "md-trunk_base_freejoint")
    adr = model.jnt_qposadr[jid]
    data.qpos[adr + 2] = 0.15
    c, s = math.cos(math.pi / 4), math.sin(math.pi / 4)
    data.qpos[adr + 3:adr + 7] = {
        "back": [0.0, 1.0, 0.0, 0.0],          # 180 deg about x
        "side": [c, s, 0.0, 0.0],              # +90 deg roll
        "side2": [c, -s, 0.0, 0.0],            # -90 deg roll
        "face": [c, 0.0, s, 0.0],              # +90 deg pitch (nose down)
        "face2": [c, 0.0, -s, 0.0],            # -90 deg pitch
    }[how]
    data.qvel[:] = 0
    mujoco.mj_forward(model, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=0.005)
    ap.add_argument("--policy", default="velstand.onnx")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--fall", choices=("none", "side", "side2", "face", "face2", "back"), default="none",
                    help="start lying down instead of standing, to see the policy get up")
    ap.add_argument("--vx", type=float, default=0.15)
    ap.add_argument("--kp", type=float, default=0.55, help="servo kp (XML official 0.55)")
    ap.add_argument("--force", type=float, default=0.96, help="servo torque limit (XML official 0.96)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--settle", type=float, default=2.0,
                    help="seconds lying still (policy off, servos at default) before the policy starts")
    args = ap.parse_args()
    SCRIPT[1] = (9.0, args.vx, 0.0, 0.0, (0, 0, 0, 0))
    model, data = build_arena(STAGE_XML, md_pose=MD_POSE, timestep=args.dt)
    # build_arena idealised the MD servos for v6; put the official XML gains back
    A = mujoco.mjtObj.mjOBJ_ACTUATOR
    for a in range(model.nu):
        if (mujoco.mj_id2name(model, A, a) or "").startswith("md-"):
            model.actuator_gainprm[a, 0] = args.kp
            model.actuator_biasprm[a, 1] = -args.kp
            model.actuator_biasprm[a, 2] = 0.0
            model.actuator_forcerange[a] = [-args.force, args.force]
    pol = MicroduckPolicy(model, data, POLICY_DIR / args.policy)
    if args.fall != "none":
        lie_down(model, data, pol, args.fall)
    pol.hold_default(data)
    print(f"MuJoCo {mujoco.__version__} | microduck {args.policy} obs {pol.obs_dim} | dt {model.opt.timestep}"
          f" | start {args.fall}")

    renderer = None
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        cap = Captioner()
        cam = CameraRig(lookat=data.xpos[pol.bid], distance=1.0, azimuth=140, elevation=-15, tau=0.5)
        marks = [1.0, 5.0, 10.5, 14.0, 16.0, 18.0, 20.0] if args.fall == "none" else [0.2, 0.8, 1.5, 2.5, 4.0, 6.0]

    steps_per_ctrl = round(MD_CONTROL_DT / model.opt.timestep)
    start = data.xpos[pol.bid].copy()
    t_end = SCRIPT[-1][0] if args.fall == "none" else 8.0 + args.settle
    k = 0
    t_up = None
    settle = args.settle if args.fall != "none" else 0.0
    head_q = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "md-" + n) for n in
              ("neck_pitch", "head_pitch", "head_yaw", "head_roll")]
    head_adr = [model.jnt_qposadr[j] for j in head_q]
    while data.time < t_end:
        t = data.time
        if args.fall == "none":
            for until, vx, vy, wz, head in SCRIPT:
                if t < until:
                    pol.twist[:] = (vx, vy, wz)
                    pol.head[:] = head
                    break
        if k % steps_per_ctrl == 0:
            if t >= settle:
                pol.step(model, data)
            else:
                pol.hold_default(data)
        mujoco.mj_step(model, data)
        k += 1
        if args.fall != "none" and t_up is None and t > settle + 0.3 and body_tilt_deg(data, pol.bid) < 15 \
                and data.xpos[pol.bid][2] > 0.10:
            t_up = t
            print(f"  UP {t - settle:.2f}s after the policy started (lying pose at start: "
                  f"tilt {lying_tilt:.0f} z {lying_z:.3f})")
        if abs(t - settle) < 0.5 * model.opt.timestep:
            lying_tilt, lying_z = body_tilt_deg(data, pol.bid), float(data.xpos[pol.bid][2])
        if k % int(0.5 / model.opt.timestep) == 0 and not (args.quiet and t > 9.5):
            p = data.xpos[pol.bid]
            print(f"  t={t:5.2f} twist={pol.twist.round(2).tolist()} head={pol.head.round(2).tolist()} "
                  f"pos=({p[0]:+.3f},{p[1]:+.3f}) z={p[2]:.3f} tilt={body_tilt_deg(data, pol.bid):5.1f} "
                  f"headq={np.round(data.qpos[head_adr], 2).tolist()} |a|max={np.abs(pol.last_action).max():.2f}")
        if renderer is not None and marks and t >= marks[0]:
            cam.aim(lookat=[data.xpos[pol.bid][0], data.xpos[pol.bid][1], 0.12])
            cam.snap()
            renderer.update_scene(data, cam.cam, opt)
            imageio.imwrite(args.preview / f"md_{args.fall}_t{marks[0]:04.1f}.png",
                            cap.draw(renderer.render(), f"v7 | パッカン 公式 {args.policy}（XML サーボ、外力なし）",
                                     [f"twist {pol.twist.round(2).tolist()} head {pol.head.round(2).tolist()}"],
                                     footer=f"sim {t:5.2f} s"))
            marks.pop(0)
        if np.any(np.isnan(data.qpos)):
            print("NaN!")
            break
    p = data.xpos[pol.bid]
    print(f"moved {np.linalg.norm(p[:2] - start[:2]):.3f} m, final z={p[2]:.3f} tilt={body_tilt_deg(data, pol.bid):.1f}")


if __name__ == "__main__":
    main()
