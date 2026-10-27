"""3-body arena v4 — Bulldozer stage + Microduck + Jumper.

Uses scene_fork_tracks.xml as base arena (includes floor, walls, 4 blocks,
ball, delivery zones).  Microduck + Jumper are MjSpec.attach'ed into it.

Scenario (10 s)
--------
Phase 1 (0-3 s)  : BZ drives +x, fork pushes block_1 toward delivery zone.
                    MD walks in place at (2.5, 0). JP waits at (4.5, 0).
Phase 2 (3-5 s)  : BZ continues push. JP starts jumping toward MD.
Phase 3 (5-8 s)  : JP reaches MD, contact.
Phase 4 (8-10 s) : MD topples / recovery attempt. Outro.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import imageio
import mujoco
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
BZ_XML = BASE / "physical-ai-course-builder" / "scene_fork_tracks.xml"
MD_XML = (
    BASE / "microduck_rl" / "src" / "mjlab_microduck"
    / "robot" / "microduck" / "scene.xml"
)
JP_XML = BASE / "jumper" / "assets" / "jumper" / "jumper.xml"

PHYSICS_DT = 0.002
CONTROL_DT = 0.02
SUBSTEPS = int(CONTROL_DT / PHYSICS_DT)
SIM_DURATION = 10.0

VIDEO_FPS = 30
VIDEO_W, VIDEO_H = 1280, 720
RENDER_EVERY = max(1, int(1.0 / (VIDEO_FPS * CONTROL_DT)))
OUT_DIR = Path(__file__).resolve().parent / "out"


# ── Helpers ──────────────────────────────────────────────────────────────
def _act_ids(model, prefix):
    return np.array([
        i for i in range(model.nu)
        if (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or "")
           .startswith(prefix)
    ], dtype=int)


def _body_id(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


# ── JP joints (jumper XML has no <actuator>) ─────────────────────────────
JP_JOINTS = [
    "LF_J0_joint", "LF_J1_joint", "LF_J2_joint", "LF_J3_joint", "LF_J4_joint",
    "RF_J0_joint", "RF_J1_joint", "RF_J2_joint", "RF_J3_joint", "RF_J4_joint",
    "LM_J0_joint", "LM_J1_joint", "LM_J2_joint",
    "RM_J0_joint", "RM_J1_joint", "RM_J2_joint",
    "LR_J0_joint", "LR_J1_joint", "LR_J2_joint",
    "RR_J0_joint", "RR_J1_joint", "RR_J2_joint",
]

# ── Layout ───────────────────────────────────────────────────────────────
# BZ scene: dozer at (-3, 0, 0.30), block_1 at (-1.5, 0, 0.26)
# Green delivery zones at (2.5, 0), (2.5, ±1.6)
MD_FRAME_POS = np.array([2.5, 0.0, 0.0])
JP_FRAME_POS = np.array([4.5, 0.0, 0.0])


# ── Arena builder ────────────────────────────────────────────────────────
def build_arena():
    """BZ scene as base, attach MD + JP."""
    arena = mujoco.MjSpec.from_file(str(BZ_XML))
    arena.modelname = "arena_3body_v4"

    arena.option.timestep = PHYSICS_DT
    arena.visual.global_.offwidth = VIDEO_W
    arena.visual.global_.offheight = VIDEO_H

    md_spec = mujoco.MjSpec.from_file(str(MD_XML))
    jp_spec = mujoco.MjSpec.from_file(str(JP_XML))

    md_f = arena.worldbody.add_frame()
    md_f.name = "microduck_origin"
    md_f.pos = list(MD_FRAME_POS)
    arena.attach(md_spec, prefix="md-", frame=md_f)

    jp_f = arena.worldbody.add_frame()
    jp_f.name = "jumper_origin"
    jp_f.pos = list(JP_FRAME_POS)
    arena.attach(jp_spec, prefix="jp-", frame=jp_f)

    for jname in JP_JOINTS:
        act = arena.add_actuator()
        act.name = f"jp-{jname}"
        act.target = f"jp-{jname}"
        act.trntype = mujoco.mjtTrn.mjTRN_JOINT
        act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
        act.gainprm[0] = 50.0
        act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        act.biasprm[1] = -50.0
        act.biasprm[2] = -0.5

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = arena.compile()

    # Disable MD child-scene floor (BZ floor is the main floor)
    gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "md-floor")
    if gid >= 0:
        model.geom_contype[gid] = 0
        model.geom_conaffinity[gid] = 0
        model.geom_rgba[gid] = [0, 0, 0, 0]

    data = mujoco.MjData(model)
    return model, data


# ── Per-robot reset ──────────────────────────────────────────────────────
def reset_microduck(model, data):
    key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "md-STAND")
    if key_id < 0:
        return
    act_ids = _act_ids(model, "md-")
    data.ctrl[act_ids] = model.key_ctrl[key_id][act_ids]
    for i in range(model.njnt):
        jname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        if jname and jname.startswith("md-"):
            qadr = model.jnt_qposadr[i]
            if model.jnt_type[i] == mujoco.mjtJoint.mjJNT_FREE:
                kf = model.key_qpos[key_id][qadr:qadr + 7].copy()
                kf[0:3] += MD_FRAME_POS
                data.qpos[qadr:qadr + 7] = kf
            else:
                data.qpos[qadr] = model.key_qpos[key_id][qadr]


def reset_jumper(model, data):
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "jp-floating_base")
    if jid >= 0:
        adr = model.jnt_qposadr[jid]
        data.qpos[adr + 0] = JP_FRAME_POS[0]
        data.qpos[adr + 1] = JP_FRAME_POS[1]
        data.qpos[adr + 2] = 0.08
        data.qpos[adr + 3] = 0.0   # w  — face -x
        data.qpos[adr + 4] = 0.0
        data.qpos[adr + 5] = 0.0
        data.qpos[adr + 6] = 1.0   # z


# ── Controllers ──────────────────────────────────────────────────────────
class BulldozerCtrl:
    """Drive +x pushing block_1, raise fork, stop near delivery zone."""

    def __init__(self):
        self._drive_ids = []
        self._blade_id = -1
        self._body_id = -1
        self._stopped = False

    def reset(self, model, data):
        self._drive_ids = [
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, n)
            for n in ["drive_lf", "drive_lr", "drive_rf", "drive_rr"]
        ]
        self._blade_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, "blade_lift"
        )
        self._body_id = _body_id(model, "dozer")
        self._stopped = False

    def step(self, model, data, t):
        dozer_x = data.xpos[self._body_id][0]

        if not self._stopped and dozer_x > 1.5:
            self._stopped = True

        speed = 0.0 if self._stopped else 5.0
        for aid in self._drive_ids:
            if aid >= 0:
                data.ctrl[aid] = speed

        if t < 1.5:
            blade_pos = 0.05
        elif t < 4.0:
            blade_pos = 0.05 + (t - 1.5) / 2.5 * 0.25
        else:
            blade_pos = 0.30
        if self._blade_id >= 0:
            data.ctrl[self._blade_id] = blade_pos

    def pos(self, data):
        return data.xpos[self._body_id].copy()


class MicroduckCtrl:
    """Walk in place with leg oscillation + stand-assist."""

    def __init__(self):
        self.act_ids = np.array([], dtype=int)
        self.stand_ctrl = np.array([])
        self._body_id = -1
        self._local_hip_pitch = {}
        self._local_knee = {}

    def reset(self, model, data):
        self.act_ids = _act_ids(model, "md-")
        key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "md-STAND")
        if key_id >= 0:
            self.stand_ctrl = model.key_ctrl[key_id][self.act_ids].copy()
        else:
            self.stand_ctrl = np.zeros(len(self.act_ids))
        self._body_id = _body_id(model, "md-trunk_base")
        for local_i, gid in enumerate(self.act_ids):
            aname = (
                mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, gid)
                or ""
            )
            if "hip_pitch" in aname:
                side = "L" if "left" in aname else "R"
                self._local_hip_pitch[side] = local_i
            elif "knee" in aname:
                side = "L" if "left" in aname else "R"
                self._local_knee[side] = local_i

    def step(self, model, data, t):
        ctrl = self.stand_ctrl.copy()
        freq = 2.0
        phase = t * freq * 2 * np.pi
        for side, sign in [("L", 1.0), ("R", -1.0)]:
            sw = np.sin(phase) * sign
            if side in self._local_hip_pitch:
                ctrl[self._local_hip_pitch[side]] += sw * 0.15
            if side in self._local_knee:
                ctrl[self._local_knee[side]] += sw * 0.10
        data.ctrl[self.act_ids] = ctrl
        md_z = data.xpos[self._body_id][2]
        target_z = 0.12
        if md_z < target_z:
            data.xfrc_applied[self._body_id][2] = (target_z - md_z) * 200.0

    def pos(self, data):
        return data.xpos[self._body_id].copy()


class JumperCtrl:
    """Jump toward Microduck from behind."""

    def __init__(self):
        self.act_ids = np.array([], dtype=int)
        self._body_id = -1
        self._leg_groups = {}
        self._arm_groups = {}
        self.jump_start_t = 2.0
        self._jump_period = 0.5
        self._jump_phase_dur = 0.14

    def reset(self, model, data):
        self.act_ids = _act_ids(model, "jp-")
        self._body_id = _body_id(model, "jp-base_link")
        for prefix_list, target_dict in [
            (["LM", "RM", "LR", "RR"], self._leg_groups),
            (["LF", "RF"], self._arm_groups),
        ]:
            for lp in prefix_list:
                ids = []
                for i, aid in enumerate(self.act_ids):
                    aname = mujoco.mj_id2name(
                        model, mujoco.mjtObj.mjOBJ_ACTUATOR, aid
                    )
                    if aname and f"jp-{lp}_" in aname:
                        ids.append(i)
                target_dict[lp] = ids

    def step(self, model, data, t):
        ctrl = np.zeros(len(self.act_ids))

        if t >= self.jump_start_t:
            cycle_t = (t - self.jump_start_t) % self._jump_period
            jumping = cycle_t < self._jump_phase_dur

            if jumping:
                extend = 1.0
                for lp in ["LM", "RM", "LR", "RR"]:
                    ids = self._leg_groups.get(lp, [])
                    if len(ids) >= 3:
                        ctrl[ids[1]] = -extend * 1.2
                        ctrl[ids[2]] = extend * 0.8
                for ap in ["LF", "RF"]:
                    ids = self._arm_groups.get(ap, [])
                    if len(ids) >= 3:
                        ctrl[ids[1]] = -extend * 0.8
                        ctrl[ids[2]] = extend * 0.6
            else:
                tuck = 0.5
                for lp in ["LM", "RM", "LR", "RR"]:
                    ids = self._leg_groups.get(lp, [])
                    if len(ids) >= 3:
                        ctrl[ids[1]] = tuck * 0.6
                        ctrl[ids[2]] = -tuck * 0.4
                for ap in ["LF", "RF"]:
                    ids = self._arm_groups.get(ap, [])
                    if len(ids) >= 3:
                        ctrl[ids[1]] = -0.3
                        ctrl[ids[2]] = 0.2

            jp_pos = data.xpos[self._body_id]
            md_x = MD_FRAME_POS[0]
            data.xfrc_applied[self._body_id][:] = 0
            dist = jp_pos[0] - md_x

            if jumping:
                data.xfrc_applied[self._body_id][2] = 25.0
                data.xfrc_applied[self._body_id][0] = -20.0
            elif dist > 0.05:
                data.xfrc_applied[self._body_id][0] = -8.0 * min(dist, 2.0)
            data.xfrc_applied[self._body_id][1] = -jp_pos[1] * 3.0
        else:
            data.xfrc_applied[self._body_id][:] = 0

        data.ctrl[self.act_ids] = ctrl

    def pos(self, data):
        return data.xpos[self._body_id].copy()


# ── Camera ───────────────────────────────────────────────────────────────
def make_camera(t, bz_pos, md_pos, jp_pos):
    cam = mujoco.MjvCamera()
    cx = (bz_pos[0] + md_pos[0] + jp_pos[0]) / 3
    cy = (bz_pos[1] + md_pos[1] + jp_pos[1]) / 3
    cam.lookat[:] = [cx, cy, 0.20]
    cam.distance = 6.0
    cam.azimuth = 150 + t * 3
    cam.elevation = -25
    return cam


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    print(f"MuJoCo {mujoco.__version__} | v4 BZ-stage render")
    print(f"  {VIDEO_W}x{VIDEO_H} @ {VIDEO_FPS} fps, {SIM_DURATION}s")
    OUT_DIR.mkdir(exist_ok=True)

    model, data = build_arena()
    print(f"Arena: nq={model.nq} nv={model.nv} nu={model.nu} nbody={model.nbody}")

    reset_microduck(model, data)
    reset_jumper(model, data)
    mujoco.mj_forward(model, data)

    bz = BulldozerCtrl()
    md = MicroduckCtrl()
    jp = JumperCtrl()
    for c in [bz, md, jp]:
        c.reset(model, data)

    renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
    scene_option = mujoco.MjvOption()

    n_ctrl_steps = int(SIM_DURATION / CONTROL_DT)
    frames = []
    frame_count = 0

    print(f"Simulating {SIM_DURATION}s ({n_ctrl_steps} ctrl steps)...")

    for ctrl_step in range(n_ctrl_steps):
        t = ctrl_step * CONTROL_DT

        bz.step(model, data, t)
        md.step(model, data, t)
        jp.step(model, data, t)

        for _ in range(SUBSTEPS):
            mujoco.mj_step(model, data)

        if np.any(np.isnan(data.qpos)):
            print(f"NaN at t={data.time:.3f}s!")
            break

        if ctrl_step % RENDER_EVERY == 0:
            bz_p = bz.pos(data)
            md_p = md.pos(data)
            jp_p = jp.pos(data)
            cam = make_camera(t, bz_p, md_p, jp_p)
            renderer.update_scene(data, cam, scene_option)
            frame = renderer.render()
            frames.append(frame.copy())
            frame_count += 1

        if int(t) != int(t - CONTROL_DT) and t > 0:
            bz_p = bz.pos(data)
            md_p = md.pos(data)
            jp_p = jp.pos(data)
            phase = "drive" if not bz._stopped else "stop"
            print(
                f"  t={t:5.1f}s  BZ({phase}) x={bz_p[0]:+.2f}  "
                f"MD z={md_p[2]:.3f}  JP x={jp_p[0]:+.2f}"
            )

    renderer.close()

    video_path = OUT_DIR / "3body_arena_v4.mp4"
    print(f"\nEncoding {frame_count} frames -> {video_path}")
    writer = imageio.get_writer(
        str(video_path), fps=VIDEO_FPS, codec="libx264",
        output_params=["-crf", "23", "-pix_fmt", "yuv420p"],
    )
    for f in frames:
        writer.append_data(f)
    writer.close()

    sz = video_path.stat().st_size
    print(f"Done: {video_path}  ({sz / 1024:.0f} KB)")

    md_z = md.pos(data)[2]
    print(
        f"\nFinal: BZ {'stopped' if bz._stopped else 'driving'}, "
        f"MD z={md_z:.3f} ({'standing' if md_z > 0.08 else 'fallen'}), "
        f"JP pos=({jp.pos(data)[0]:.2f}, {jp.pos(data)[1]:.2f})"
    )


if __name__ == "__main__":
    main()
