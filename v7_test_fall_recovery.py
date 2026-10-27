"""Why does velstand not get up after the crab's pounce in the arena (it does standalone)?

Reproduces scene C headless and, while the duck stays down, tries in order:
  +4 s  policy reset (last_action -> 0)        -> if it gets up, stale state was the cause
  +9 s  servos to default for 1 s, then policy  -> if it gets up, the lying pose was the cause

    <jumper venv python> v7_test_fall_recovery.py
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR, quat_to_yaw
from v6_robots import body_tilt_deg, build_arena, robots_in_contact
from v7_full import official_md_servos, wrap
from v7_policies import JumperJump, JumperLocomotion, MicroduckPolicy, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"


def main():
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
    head_q = [model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "md-" + n)]
              for n in ("neck_pitch", "head_pitch", "head_yaw", "head_roll")]
    mode, k, t_mode, t_fall = "walk", 0, 0.0, None
    did = set()
    hold_until = -1.0
    while data.time < 30.0:
        t = data.time
        p_md, p_jp = data.xpos[md.bid], data.xpos[loco.bid]
        sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
        tilt = body_tilt_deg(data, md.bid)
        if tilt > 60 and t_fall is None:
            t_fall = t
            print(f"MD fell at t={t:.2f}")
        if t_fall is not None and tilt < 15 and p_md[2] > 0.10 and "up" not in did:
            did.add("up")
            print(f"MD UP at t={t:.2f} ({t - t_fall:.1f} s after the fall), after: {sorted(did)}")
        down = (t - t_fall) if t_fall is not None else -1
        if down > 4.0 and "reset" not in did:
            did.add("reset")
            md.reset()
            print(f"  t={t:.2f}: policy reset")
        if down > 9.0 and "hold" not in did:
            did.add("hold")
            hold_until = t + 1.0
            print(f"  t={t:.2f}: servos to default for 1 s")
        if down > 10.0 and "reset2" not in did and t > hold_until:
            did.add("reset2")
            md.reset()
            print(f"  t={t:.2f}: policy resumes (reset)")
        if down > 16.0 and "freeze" not in did:
            did.add("freeze")
            print(f"  t={t:.2f}: joints-default={np.array2string(data.qpos[md.qpos_idx] - md.default, precision=2)}")
            print(f"         head q={np.round(data.qpos[head_q], 2).tolist()} grav={np.array2string(md.observe(model, data)[3:6], precision=2)}")
            print(f"         touch crab={robots_in_contact(model, data, md_root, jp_root)} sep={sep:.2f} z={p_md[2]:.3f} tilt={tilt:.1f}")
            # which geoms is the duck touching?
            names = set()
            for i in range(data.ncon):
                c = data.contact[i]
                for g in (c.geom1, c.geom2):
                    if model.body_rootid[model.geom_bodyid[g]] == md_root:
                        other = c.geom2 if g == c.geom1 else c.geom1
                        names.add(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, other) or f"geom{other}")
            print(f"         duck touches: {sorted(names)}")
        if k % 20 == 0:
            md.twist[:] = 0
            md.head[:] = 0
            if t < hold_until:
                md.hold_default(data)
            else:
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
        if k % 2000 == 0 and t_fall is not None:
            print(f"  t={t:5.1f} down {down:4.1f}s tilt={tilt:5.1f} z={p_md[2]:.3f} sep={sep:.2f} |a|={np.abs(md.last_action).max():.2f}")
    print(f"end: tilt={tilt:.1f} z={p_md[2]:.3f} did={sorted(did)}")


if __name__ == "__main__":
    main()
