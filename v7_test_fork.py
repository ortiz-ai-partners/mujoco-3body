"""Does the fork tip the seated duck over, or just push it along?  The LIFT ending, standalone.

    <jumper venv python> v7_test_fork.py [--dy 0 0.1 0.2] [--lift 0 0.06]

BZ is put 1.9 m east of the seated duck, facing west, with its centreline dy north of the duck's
centre and the fork held at height `lift` while it slides in; then the story's insert / lift /
hold / lower / back sequence runs (the same commands as v7_full.py's LIFT stage).  Reports the
duck's max tilt, whether it tipped over (tilt > 60), how far it was pushed, and whether velstand
got it back up.  Placing BZ by writing its pose is for this test only - never in the video.
"""
from __future__ import annotations

import argparse
import json
import math

import mujoco
import numpy as np

from v6_common import OUT_DIR, course_builder
from v6_phase4_full import ArenaSim
from v6_robots import build_arena, robots_in_contact
from v7_full import CONTROL_DT, Duck, official_md_servos
from v7_policies import MD_CONTROL_DT

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
MD_SEAT = (1.22, -2.10, math.pi / 2)        # where the duck sits in the story, facing the ramp


def run(dy, lift_h, tracks_mod, mode="tip", height=0.49, back_speed=0.25, hold=2.5, side="east", standing=False,
        skew_deg=0.0):
    """mode 'tip': the story's original sequence (full-rate lift to 0.49, back at 0.25).
    mode 'lift': the gentle one (ゆうころ 10/27: lifting the duck is the heart-warming ending) -
    lift at 0.6 rate to `height`, hold, lower at 0.4 rate, back off at `back_speed`."""
    model, data = build_arena(STAGE_XML, md_pose=MD_SEAT, timestep=0.001)
    official_md_servos(model)
    duck = Duck(model, data)
    sim = ArenaSim(model, data, tracks_mod)
    J = mujoco.mjtObj.mjOBJ_JOINT
    base = model.jnt_qposadr[mujoco.mj_name2id(model, J, "base")]
    lift_j = model.jnt_qposadr[mujoco.mj_name2id(model, J, "lift")]
    bz_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dozer")
    md_root, bz_root = model.body_rootid[duck.bid], model.body_rootid[bz_bid]
    if side == "east":        # the fork comes at the duck's right side; dy = centreline offset to the north
        data.qpos[base:base + 3] = (MD_SEAT[0] + 1.9, MD_SEAT[1] + dy, 0.30)
        data.qpos[base + 3:base + 7] = (0.0, 0.0, 0.0, 1.0)      # yaw pi: facing west
    else:                     # from behind the duck (it faces north); dy = centreline offset to the east.
        # skew_deg rotates BZ's approach about the aim point: its centreline still passes dy beside the
        # duck, but the tines come in at that angle (how much skew does the two-tine lift tolerate?)
        yaw = math.pi / 2 + math.radians(skew_deg)
        aim = np.array([MD_SEAT[0] + dy, MD_SEAT[1]])
        start = aim - 1.9 * np.array([math.cos(yaw), math.sin(yaw)])
        data.qpos[base:base + 3] = (start[0], start[1], 0.30)
        data.qpos[base + 3:base + 7] = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
    data.qpos[lift_j] = 0.0
    data.qvel[:] = 0
    sim.lift_target = 0.0
    mujoco.mj_forward(model, data)

    md_every = round(MD_CONTROL_DT / model.opt.timestep)
    stats = {"mode": mode, "from": side, "standing": standing, "skew_deg": skew_deg, "dy": dy, "lift": lift_h,
             "height": height, "back": back_speed,
             "max_tilt": 0.0, "max_z": 0.0, "fell_at": None, "up_at": None, "events": []}
    gentle = mode == "lift"
    start = duck.pos(data).copy()
    phase, t0, k = "stand", 0.0, 0

    def ev(t, s):
        stats["events"].append(f"{t:6.2f}s {s}")

    while data.time < 70.0:
        t = data.time
        tilt = float(duck.tilt(data))
        p_md, p_bz = duck.pos(data), data.xpos[bz_bid]
        if phase not in ("stand", "sit_in"):
            stats["max_tilt"] = max(stats["max_tilt"], tilt)
            stats["max_z"] = max(stats["max_z"], float(p_md[2]))
        if duck.mode == "SIT" and tilt > 60.0:
            duck.resume, duck.fell_at, duck.upright_since = "STAND", t, None
            duck.use("vel")
            duck.set_mode("FALLEN", t)
            stats["fell_at"] = round(t, 2)
            ev(t, f"duck tipped over (tilt {tilt:.0f}) at ({p_md[0]:+.2f},{p_md[1]:+.2f}) during {phase}")
        if duck.mode == "SIT":
            duck.sit.twist[:] = (1.0, 0.0, 0.0)
        if phase == "stand":
            sim.command(0, 0, 0)
            if t > 1.0:
                phase, t0 = "sit_in", t
                if not standing:                     # --standing: the duck stays on its feet (velstand, zero twist)
                    duck.use("sit")
                    duck.set_mode("SIT", t)
                    duck.sit.head[:] = (0.3, 0.5, 0, 0)
        elif phase == "sit_in":
            sim.command(0, 0, 1.0 if sim.lift_target < lift_h else 0.0)
            if t - t0 > 3.0:
                phase, t0 = "insert", t
                ev(t, f"seated z={p_md[2]:.3f} tilt={tilt:.0f}; fork at {sim.lift_target:.2f}; BZ slides in")
        elif phase == "insert":
            dist = float(np.linalg.norm(p_md[:2] - p_bz[:2]))
            sim.command(0.15, 0.0, 0.0 if lift_h > 0 else -1.0)
            if dist < 0.98 or t - t0 > 25:
                phase, t0 = "lift", t
                ev(t, f"lift: duck {dist:.2f} m ahead, touching={robots_in_contact(model, data, md_root, bz_root)}, "
                      f"tilt={tilt:.0f}, pushed {np.linalg.norm(p_md[:2] - start[:2]):.2f} m")
        elif phase == "lift":
            sim.command(0, 0, 0.6 if gentle else 1.0)
            if sim.lift_target >= height - 1e-6 or t - t0 > 4.0:
                phase, t0 = "hold", t
                ev(t, f"fork up ({sim.lift_target:.2f}): duck z={p_md[2]:.3f} tilt={tilt:.0f}")
        elif phase == "hold":
            sim.command(0, 0, 0)
            if t - t0 > hold:
                phase, t0 = "lower", t
                ev(t, f"end of hold: duck z={p_md[2]:.3f} tilt={tilt:.0f}")
        elif phase == "lower":
            sim.command(0, 0, -0.4 if gentle else -1.0)
            if sim.lift_target <= 0.0 or t - t0 > 6.0:
                phase, t0 = "back", t
                ev(t, f"fork down: duck z={p_md[2]:.3f} tilt={tilt:.0f}")
        elif phase == "back":
            sim.command(-back_speed, 0, 0)
            if t - t0 > (6.0 if gentle else 2.5):            # gentle: long enough for the tines to clear
                phase, t0 = "wait", t
                sim.command(0, 0, 0)
                if duck.mode == "SIT":
                    duck.sit.twist[:] = 0
        elif phase == "wait":
            sim.command(0, 0, 0)
            if duck.mode == "SIT":
                duck.sit.twist[:] = 0
                if t - t0 > 3.5:
                    duck.use("vel")
                    duck.set_mode("STAND", t)
            if t - t0 > 15.0:
                break
        if stats["fell_at"] is not None and stats["up_at"] is None and duck.mode not in ("FALLEN",) \
                and t > stats["fell_at"] + 0.5:
            stats["up_at"] = round(t, 2)
            ev(t, f"duck back up by itself ({t - stats['fell_at']:.1f} s)")
        duck.control(data, t)
        for _ in range(round(CONTROL_DT / model.opt.timestep)):
            if k % md_every == 0:
                duck.step(model, data)
            mujoco.mj_step(model, data)
            k += 1
    p = duck.pos(data)
    stats.update(final_mode=duck.mode, final_tilt=round(float(duck.tilt(data)), 1), final_z=round(float(p[2]), 3),
                 pushed=round(float(np.linalg.norm(p[:2] - start[:2])), 2), max_tilt=round(stats["max_tilt"], 1),
                 max_z=round(stats["max_z"], 3))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dy", type=float, nargs="+", default=[0.0, 0.1, 0.2])
    ap.add_argument("--lift", type=float, nargs="+", default=[0.0, 0.06])
    ap.add_argument("--mode", choices=["tip", "lift"], default="tip")
    ap.add_argument("--height", type=float, default=0.49)
    ap.add_argument("--back-speed", type=float, default=0.25)
    ap.add_argument("--hold", type=float, default=2.5)
    ap.add_argument("--from", dest="side", choices=["east", "south"], default="east",
                    help="east: at the duck's right side (the story so far); south: from behind the duck")
    ap.add_argument("--standing", action="store_true", help="the duck stays standing (velstand) instead of sitting")
    ap.add_argument("--skew", type=float, nargs="+", default=[0.0], help="approach skew in degrees (--from south only)")
    args = ap.parse_args()
    _, _, tracks_mod = course_builder()
    for lift_h in args.lift:
        for dy in args.dy:
            for skew in args.skew:
                s = run(dy, lift_h, tracks_mod, mode=args.mode, height=args.height, back_speed=args.back_speed,
                        hold=args.hold, side=args.side, standing=args.standing, skew_deg=skew)
                print(json.dumps({k: v for k, v in s.items() if k != "events"}), flush=True)
                for e in s["events"]:
                    print("   ", e, flush=True)


if __name__ == "__main__":
    main()
