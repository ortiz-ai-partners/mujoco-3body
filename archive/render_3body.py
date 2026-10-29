"""3-body arena — render to MP4 with independent 50 Hz control loops.

Fixes vs run_3body.py
---------------------
- Arena build separated from simulation (no premature stepping).
- Per-robot reset instead of mj_resetDataKeyframe (which wiped all robots).
- Camera tracks the action.

Scenario  (10 s)
--------
Phase 1 (0–3 s)  : BZ drives +x toward origin, blade rising. MD stands. JP stands.
Phase 2 (3–6 s)  : BZ brakes near MD. JP walks toward MD (tripod gait).
Phase 3 (6–8 s)  : JP reaches MD, contact → MD topples.
Phase 4 (8–10 s) : MD PD tries to recover. Outro.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # archive/: resolve v6_common etc. from the repository root

import imageio
import mujoco
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[2]  # archive/: one level deeper than before the move; BASE is still the parent of the repository
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
OUT_DIR = Path(__file__).resolve().parents[1] / "out"  # archive/: still <repository>/out


# ── Helpers ──────────────────────────────────────────────────────────────
def _act_ids(model, prefix):
    return np.array([
        i for i in range(model.nu)
        if (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or "").startswith(prefix)
    ], dtype=int)


def _body_id(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


# ── Arena builder ────────────────────────────────────────────────────────
JP_JOINTS = [
    "LF_J0_joint", "LF_J1_joint", "LF_J2_joint", "LF_J3_joint", "LF_J4_joint",
    "RF_J0_joint", "RF_J1_joint", "RF_J2_joint", "RF_J3_joint", "RF_J4_joint",
    "LM_J0_joint", "LM_J1_joint", "LM_J2_joint",
    "RM_J0_joint", "RM_J1_joint", "RM_J2_joint",
    "LR_J0_joint", "LR_J1_joint", "LR_J2_joint",
    "RR_J0_joint", "RR_J1_joint", "RR_J2_joint",
]


def build_arena():
    bz_spec = mujoco.MjSpec.from_file(str(BZ_XML))
    md_spec = mujoco.MjSpec.from_file(str(MD_XML))
    jp_spec = mujoco.MjSpec.from_file(str(JP_XML))

    arena = mujoco.MjSpec()
    arena.modelname = "arena_3body"
    arena.option.timestep = PHYSICS_DT
    arena.option.integrator = 3   # implicitfast
    arena.option.cone = 1         # elliptic
    arena.option.iterations = 60
    arena.visual.global_.offwidth = VIDEO_W
    arena.visual.global_.offheight = VIDEO_H

    # Ground — checker texture for visual interest
    tex = arena.add_texture()
    tex.name = "floor_checker"
    tex.type = mujoco.mjtTexture.mjTEXTURE_2D
    tex.builtin = mujoco.mjtBuiltin.mjBUILTIN_CHECKER
    tex.rgb1 = [0.15, 0.20, 0.25]
    tex.rgb2 = [0.20, 0.25, 0.30]
    tex.width = 512
    tex.height = 512

    mat = arena.add_material()
    mat.name = "floor_mat"
    mat.textures[0] = "floor_checker"
    mat.texrepeat = [10, 10]
    mat.reflectance = 0.1

    floor = arena.worldbody.add_geom()
    floor.name = "arena_floor"
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.size = [20, 20, 0.1]
    floor.material = "floor_mat"

    # --- Layout (tighter for interaction) ---
    #  BZ at (-2,0)  →  MD at (0.8,0)  ←  JP at (2,0)
    bz_f = arena.worldbody.add_frame()
    bz_f.name = "bulldozer_origin"
    bz_f.pos = [-2, 0, 0]
    arena.attach(bz_spec, prefix="bz-", frame=bz_f)

    md_f = arena.worldbody.add_frame()
    md_f.name = "microduck_origin"
    md_f.pos = [0.8, 0, 0]
    arena.attach(md_spec, prefix="md-", frame=md_f)

    jp_f = arena.worldbody.add_frame()
    jp_f.name = "jumper_origin"
    jp_f.pos = [1.5, 0, 0]
    arena.attach(jp_spec, prefix="jp-", frame=jp_f)

    # Jumper actuators
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

    # Disable child-scene floor geoms (z-fighting + contact interference)
    for prefix in ["bz-", "md-"]:
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{prefix}floor")
        if gid >= 0:
            model.geom_contype[gid] = 0
            model.geom_conaffinity[gid] = 0
            model.geom_rgba[gid] = [0, 0, 0, 0]

    data = mujoco.MjData(model)
    return model, data


# ── Per-robot reset (does NOT wipe other robots) ─────────────────────────
MD_FRAME_POS = np.array([0.8, 0.0, 0.0])
JP_FRAME_POS = np.array([1.5, 0.0, 0.0])


def reset_microduck(model, data):
    """Set Microduck joints to STAND pose, adjusting freejoint for frame offset."""
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
                kf = model.key_qpos[key_id][qadr:qadr+7].copy()
                kf[0:3] += MD_FRAME_POS
                data.qpos[qadr:qadr+7] = kf
            else:
                data.qpos[qadr] = model.key_qpos[key_id][qadr]


def reset_jumper(model, data):
    """Set jumper to standing height at its frame position, facing -x."""
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "jp-floating_base")
    if jid >= 0:
        adr = model.jnt_qposadr[jid]
        data.qpos[adr + 0] = JP_FRAME_POS[0]
        data.qpos[adr + 1] = JP_FRAME_POS[1]
        data.qpos[adr + 2] = 0.08
        # Face -x: 180 deg rotation about z → quat = (0, 0, 0, 1)
        data.qpos[adr + 3] = 0.0  # w
        data.qpos[adr + 4] = 0.0  # x
        data.qpos[adr + 5] = 0.0  # y
        data.qpos[adr + 6] = 1.0  # z


# ── Controllers ──────────────────────────────────────────────────────────
class BulldozerCtrl:
    def __init__(self):
        self.act_ids = np.array([], dtype=int)
        self._drive_ids = []
        self._blade_id = -1
        self._body_id = -1
        self._stopped = False

    def reset(self, model, data):
        self.act_ids = _act_ids(model, "bz-")
        self._drive_ids = [
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, n)
            for n in ["bz-drive_lf", "bz-drive_lr", "bz-drive_rf", "bz-drive_rr"]
        ]
        self._blade_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "bz-blade_lift")
        self._body_id = _body_id(model, "bz-dozer")
        self._stopped = False

    def step(self, model, data, t):
        dozer_x = data.xpos[self._body_id][0]
        # Stop when dozer reaches near microduck
        if not self._stopped and dozer_x > 0.0:
            self._stopped = True

        speed = 0.0 if self._stopped else 5.0
        for aid in self._drive_ids:
            data.ctrl[aid] = speed

        blade_frac = min(t / 2.0, 1.0)
        data.ctrl[self._blade_id] = 0.35 * blade_frac


class MicroduckCtrl:
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
            aname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, gid) or ""
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
        # Upward assist to counter integrator-induced sag
        md_z = data.xpos[self._body_id][2]
        target_z = 0.11
        if md_z < target_z:
            data.xfrc_applied[self._body_id][2] = (target_z - md_z) * 80.0

    def pos(self, data):
        return data.xpos[self._body_id].copy()


class JumperCtrl:
    def __init__(self):
        self.act_ids = np.array([], dtype=int)
        self._body_id = -1
        self._leg_groups = {}
        self._arm_groups = {}
        self.jump_start_t = 1.0
        self._last_jump_t = -10.0
        self._jump_period = 0.6
        self._jump_phase_dur = 0.12

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
                    aname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aid)
                    if aname and f"jp-{lp}_" in aname:
                        ids.append(i)
                target_dict[lp] = ids

    def step(self, model, data, t):
        ctrl = np.zeros(len(self.act_ids))

        if t >= self.jump_start_t:
            cycle_t = (t - self.jump_start_t) % self._jump_period
            jumping = cycle_t < self._jump_phase_dur

            if jumping:
                # Crouch then extend: all legs push down
                extend = 1.0
                for lp in ["LM", "RM", "LR", "RR"]:
                    ids = self._leg_groups.get(lp, [])
                    if len(ids) >= 3:
                        ctrl[ids[1]] = -extend * 1.2
                        ctrl[ids[2]] = extend * 0.8
                # Front legs push too
                for ap in ["LF", "RF"]:
                    ids = self._arm_groups.get(ap, [])
                    if len(ids) >= 3:
                        ctrl[ids[1]] = -extend * 0.8
                        ctrl[ids[2]] = extend * 0.6
            else:
                # Tuck legs for airborne / landing
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

            # Jump force toward MD
            jp_pos = data.xpos[self._body_id]
            md_x = 0.8
            data.xfrc_applied[self._body_id][:] = 0
            dist = jp_pos[0] - md_x
            if jumping:
                data.xfrc_applied[self._body_id][2] = 15.0
                data.xfrc_applied[self._body_id][0] = -10.0
            elif dist > 0.05:
                data.xfrc_applied[self._body_id][0] = -4.0 * min(dist, 1.0)
            # Center on y=0
            data.xfrc_applied[self._body_id][1] = -jp_pos[1] * 3.0
        else:
            data.xfrc_applied[self._body_id][:] = 0

        data.ctrl[self.act_ids] = ctrl

    def pos(self, data):
        return data.xpos[self._body_id].copy()


# ── Camera ───────────────────────────────────────────────────────────────
def make_camera(t, bz_pos, md_pos, jp_pos):
    """Tracking camera: slow orbit around the action."""
    cam = mujoco.MjvCamera()
    cx = (bz_pos[0] + md_pos[0] + jp_pos[0]) / 3
    cy = (bz_pos[1] + md_pos[1] + jp_pos[1]) / 3
    cam.lookat[:] = [cx, cy, 0.15]
    cam.distance = 3.5
    cam.azimuth = 160 + t * 5   # slow orbit
    cam.elevation = -20
    return cam


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    print(f"MuJoCo {mujoco.__version__} | Rendering {VIDEO_W}x{VIDEO_H} @ {VIDEO_FPS} fps")
    OUT_DIR.mkdir(exist_ok=True)

    model, data = build_arena()
    print(f"Arena: nq={model.nq} nv={model.nv} nu={model.nu} nbody={model.nbody}")

    # Per-robot reset
    reset_microduck(model, data)
    reset_jumper(model, data)
    mujoco.mj_forward(model, data)

    # Controllers
    bz = BulldozerCtrl()
    md = MicroduckCtrl()
    jp = JumperCtrl()
    for c in [bz, md, jp]:
        c.reset(model, data)

    # Renderer
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

        # Render frame
        if ctrl_step % RENDER_EVERY == 0:
            bz_p = data.xpos[bz._body_id]
            md_p = md.pos(data)
            jp_p = jp.pos(data)
            cam = make_camera(t, bz_p, md_p, jp_p)

            renderer.update_scene(data, cam, scene_option)
            frame = renderer.render()
            frames.append(frame.copy())
            frame_count += 1

        if int(t) != int(t - CONTROL_DT) and t > 0:
            bz_p = data.xpos[bz._body_id]
            md_p = md.pos(data)
            jp_p = jp.pos(data)
            phase = "drive" if not bz._stopped else "stop"
            print(
                f"  t={t:5.1f}s  BZ({phase}) x={bz_p[0]:+.2f}  "
                f"MD z={md_p[2]:.3f}  JP x={jp_p[0]:+.2f}"
            )

    renderer.close()

    # Encode video
    video_path = OUT_DIR / "3body_arena.mp4"
    print(f"\nEncoding {frame_count} frames → {video_path}")
    writer = imageio.get_writer(str(video_path), fps=VIDEO_FPS, codec="libx264",
                                output_params=["-crf", "23", "-pix_fmt", "yuv420p"])
    for f in frames:
        writer.append_data(f)
    writer.close()

    print(f"Done: {video_path}  ({video_path.stat().st_size / 1024:.0f} KB)")

    # Final state
    md_z = md.pos(data)[2]
    print(f"\nFinal: BZ {'stopped' if bz._stopped else 'driving'}, "
          f"MD z={md_z:.3f} ({'standing' if md_z > 0.08 else 'fallen'}), "
          f"JP pos=({jp.pos(data)[0]:.2f}, {jp.pos(data)[1]:.2f})")


if __name__ == "__main__":
    main()
