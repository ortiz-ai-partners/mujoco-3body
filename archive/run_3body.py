"""3-body arena with independent 50 Hz control loops for each robot.

Architecture
------------
Physics timestep : 0.002 s  (500 Hz)
Control frequency: 50 Hz    (every 10 physics steps)
Each robot owns a Controller that reads its sensors and writes its actuators.

Scenario
--------
Phase 1 (0-3 s): BZ drives toward origin, MD stands, JP stands
Phase 2 (3-5 s): BZ brakes, JP walks toward MD
Phase 3 (5-7 s): JP nudges MD, MD falls, MD recovers (STAND PD)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # archive/: resolve v6_common etc. from the repository root

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

PHYSICS_DT = 0.002        # 500 Hz
CONTROL_DT = 0.02         # 50 Hz
SUBSTEPS = int(CONTROL_DT / PHYSICS_DT)  # 10
SIM_DURATION = 8.0        # seconds
REPORT_INTERVAL = 1.0     # print status every N seconds


# ── Helpers ──────────────────────────────────────────────────────────────
def _act_ids(model: mujoco.MjModel, prefix: str) -> np.ndarray:
    """Return sorted actuator indices whose names start with *prefix*."""
    ids = []
    for i in range(model.nu):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        if name and name.startswith(prefix):
            ids.append(i)
    return np.array(ids, dtype=int)


def _body_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def _joint_qpos(model: mujoco.MjModel, data: mujoco.MjData, jname: str) -> np.ndarray:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
    adr = model.jnt_qposadr[jid]
    n = 7 if model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE else 1
    return data.qpos[adr : adr + n]


# ── Controller interface ─────────────────────────────────────────────────
class Controller(Protocol):
    def reset(self, model: mujoco.MjModel, data: mujoco.MjData) -> None: ...
    def step(self, model: mujoco.MjModel, data: mujoco.MjData, t: float) -> None: ...


# ── Bulldozer controller ─────────────────────────────────────────────────
@dataclass
class BulldozerCtrl:
    """Scripted: drive forward, stop near target, lift blade."""

    act_ids: np.ndarray = field(default_factory=lambda: np.array([]))
    target_x: float = -1.0   # stop when dozer x > this
    drive_speed: float = 4.0
    blade_target: float = 0.3
    _stopped: bool = False

    def reset(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        self.act_ids = _act_ids(model, "bz-")
        self._stopped = False
        self._drive_ids = {
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, n): n
            for n in ["bz-drive_lf", "bz-drive_lr", "bz-drive_rf", "bz-drive_rr"]
        }
        self._blade_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, "bz-blade_lift"
        )
        self._body_id = _body_id(model, "bz-dozer")

    def step(self, model: mujoco.MjModel, data: mujoco.MjData, t: float) -> None:
        dozer_x = data.xpos[self._body_id][0]

        if not self._stopped and dozer_x > self.target_x:
            self._stopped = True

        if self._stopped:
            for aid in self._drive_ids:
                data.ctrl[aid] = 0.0
        else:
            for aid in self._drive_ids:
                data.ctrl[aid] = self.drive_speed

        # Lift blade smoothly over first 2 seconds
        blade_frac = min(t / 2.0, 1.0)
        data.ctrl[self._blade_id] = self.blade_target * blade_frac


# ── Microduck controller ─────────────────────────────────────────────────
@dataclass
class MicroduckCtrl:
    """PD controller: hold STAND pose, with optional velocity command."""

    act_ids: np.ndarray = field(default_factory=lambda: np.array([]))
    stand_ctrl: np.ndarray = field(default_factory=lambda: np.array([]))
    _body_id: int = -1

    def reset(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        self.act_ids = _act_ids(model, "md-")

        # Extract STAND keyframe ctrl values
        key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "md-STAND")
        if key_id >= 0:
            full_ctrl = model.key_ctrl[key_id]
            self.stand_ctrl = full_ctrl[self.act_ids].copy()
        else:
            self.stand_ctrl = np.zeros(len(self.act_ids))

        self._body_id = _body_id(model, "md-trunk_base")

        # Apply STAND keyframe as initial state
        mujoco.mj_resetDataKeyframe(model, data, key_id)

    def step(self, model: mujoco.MjModel, data: mujoco.MjData, t: float) -> None:
        # Maintain STAND pose at all times (recovery after fall = same target)
        data.ctrl[self.act_ids] = self.stand_ctrl

    @property
    def trunk_z(self):
        return self._trunk_z

    def read_state(self, data: mujoco.MjData) -> dict:
        pos = data.xpos[self._body_id]
        return {"x": pos[0], "y": pos[1], "z": pos[2]}


# ── Jumper controller ─────────────────────────────────────────────────────
@dataclass
class JumperCtrl:
    """PD standing controller with scripted walk-toward-target."""

    act_ids: np.ndarray = field(default_factory=lambda: np.array([]))
    _body_id: int = -1
    _root_jnt: int = -1

    # Standing pose: all joints at 0 (legs straight down)
    stand_pose: np.ndarray = field(default_factory=lambda: np.array([]))

    # Walk parameters
    walk_start_t: float = 3.0
    target_pos: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0]))
    gait_freq: float = 2.0       # Hz
    gait_amp: float = 0.4        # radians

    def reset(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        self.act_ids = _act_ids(model, "jp-")
        self.stand_pose = np.zeros(len(self.act_ids))
        self._body_id = _body_id(model, "jp-base_link")
        self._root_jnt = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT, "jp-floating_base"
        )

        # Set initial height
        if self._root_jnt >= 0:
            adr = model.jnt_qposadr[self._root_jnt]
            data.qpos[adr + 2] = 0.08

        # Identify leg joint groups for gait pattern
        self._leg_groups = {}
        leg_prefixes = ["LM", "RM", "LR", "RR"]
        for lp in leg_prefixes:
            ids = []
            for i, aid in enumerate(self.act_ids):
                aname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aid)
                if aname and f"jp-{lp}_" in aname:
                    ids.append(i)
            self._leg_groups[lp] = ids

        # Front arms: tuck them
        self._arm_groups = {}
        for ap in ["LF", "RF"]:
            ids = []
            for i, aid in enumerate(self.act_ids):
                aname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aid)
                if aname and f"jp-{ap}_" in aname:
                    ids.append(i)
            self._arm_groups[ap] = ids

    def step(self, model: mujoco.MjModel, data: mujoco.MjData, t: float) -> None:
        ctrl = self.stand_pose.copy()

        if t >= self.walk_start_t:
            # Tripod gait: LM+RR vs RM+LR, alternating swing/stance
            phase = (t - self.walk_start_t) * self.gait_freq * 2 * np.pi
            swing_a = np.sin(phase) * self.gait_amp
            swing_b = np.sin(phase + np.pi) * self.gait_amp

            # Group A: LM, RR
            for lp, offset in [("LM", swing_a), ("RR", swing_a)]:
                ids = self._leg_groups.get(lp, [])
                if len(ids) >= 2:
                    ctrl[ids[0]] = 0.0           # hip yaw: straight
                    ctrl[ids[1]] = offset * 0.8  # thigh: swing
                    if len(ids) >= 3:
                        ctrl[ids[2]] = -offset * 0.5  # calf: counter-swing

            # Group B: RM, LR
            for lp, offset in [("RM", swing_b), ("LR", swing_b)]:
                ids = self._leg_groups.get(lp, [])
                if len(ids) >= 2:
                    ctrl[ids[0]] = 0.0
                    ctrl[ids[1]] = offset * 0.8
                    if len(ids) >= 3:
                        ctrl[ids[2]] = -offset * 0.5

        # Front arms: tucked position
        for ap in ["LF", "RF"]:
            ids = self._arm_groups.get(ap, [])
            if len(ids) >= 3:
                ctrl[ids[1]] = -0.3  # upper arm fold
                ctrl[ids[2]] = 0.2   # forearm

        data.ctrl[self.act_ids] = ctrl

    def read_state(self, data: mujoco.MjData) -> dict:
        pos = data.xpos[self._body_id]
        return {"x": pos[0], "y": pos[1], "z": pos[2]}


# ── Arena builder (reused from build_3body_arena.py) ─────────────────────
def build_arena() -> tuple[mujoco.MjModel, mujoco.MjData]:
    bz_spec = mujoco.MjSpec.from_file(str(BZ_XML))
    md_spec = mujoco.MjSpec.from_file(str(MD_XML))
    jp_spec = mujoco.MjSpec.from_file(str(JP_XML))

    arena = mujoco.MjSpec()
    arena.modelname = "arena_3body"
    arena.option.timestep = PHYSICS_DT
    arena.option.integrator = 3   # implicitfast
    arena.option.cone = 1         # elliptic
    arena.option.iterations = 60

    # Ground
    floor = arena.worldbody.add_geom()
    floor.name = "arena_floor"
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.size = [20, 20, 0.1]
    floor.rgba = [0.15, 0.2, 0.25, 1.0]

    # Bulldozer at (-4, 0)
    bz_f = arena.worldbody.add_frame()
    bz_f.name = "bulldozer_origin"
    bz_f.pos = [-4, 0, 0]
    arena.attach(bz_spec, prefix="bz-", frame=bz_f)

    # Microduck at origin
    md_f = arena.worldbody.add_frame()
    md_f.name = "microduck_origin"
    md_f.pos = [0, 0, 0]
    arena.attach(md_spec, prefix="md-", frame=md_f)

    # Jumper at (2, 0)
    jp_f = arena.worldbody.add_frame()
    jp_f.name = "jumper_origin"
    jp_f.pos = [2, 0, 0]
    arena.attach(jp_spec, prefix="jp-", frame=jp_f)

    # Add position actuators for jumper (XML has none)
    JP_JOINTS = [
        "LF_J0_joint", "LF_J1_joint", "LF_J2_joint", "LF_J3_joint", "LF_J4_joint",
        "RF_J0_joint", "RF_J1_joint", "RF_J2_joint", "RF_J3_joint", "RF_J4_joint",
        "LM_J0_joint", "LM_J1_joint", "LM_J2_joint",
        "RM_J0_joint", "RM_J1_joint", "RM_J2_joint",
        "LR_J0_joint", "LR_J1_joint", "LR_J2_joint",
        "RR_J0_joint", "RR_J1_joint", "RR_J2_joint",
    ]
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

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = arena.compile()
    data = mujoco.MjData(model)
    return model, data


# ── Main loop ────────────────────────────────────────────────────────────
def main():
    print(f"MuJoCo {mujoco.__version__} | Python {sys.version.split()[0]}")
    print(f"Physics {1/PHYSICS_DT:.0f} Hz | Control {1/CONTROL_DT:.0f} Hz "
          f"| {SUBSTEPS} substeps | {SIM_DURATION}s")
    print()

    model, data = build_arena()
    print(f"Arena: nq={model.nq} nv={model.nv} nu={model.nu} "
          f"nbody={model.nbody} ngeom={model.ngeom}")
    print()

    # Instantiate controllers
    bz = BulldozerCtrl()
    md = MicroduckCtrl()
    jp = JumperCtrl()

    controllers: list[Controller] = [bz, md, jp]
    for c in controllers:
        c.reset(model, data)

    print(f"Controllers initialized:")
    print(f"  Bulldozer: {len(bz.act_ids)} actuators, target_x={bz.target_x}")
    print(f"  Microduck: {len(md.act_ids)} actuators, STAND pose loaded")
    print(f"  Jumper:    {len(jp.act_ids)} actuators, walk starts t={jp.walk_start_t}s")
    print()

    # Simulation loop
    n_ctrl_steps = int(SIM_DURATION / CONTROL_DT)
    next_report = REPORT_INTERVAL

    print("t(s)    | BZ-dozer x,z       | MD-trunk x,z       | JP-base x,z        | contacts")
    print("--------+--------------------+--------------------+--------------------+---------")

    for ctrl_step in range(n_ctrl_steps):
        t = ctrl_step * CONTROL_DT

        # 1) Each controller reads sensors and writes ctrl
        for c in controllers:
            c.step(model, data, t)

        # 2) Physics substeps
        for _ in range(SUBSTEPS):
            mujoco.mj_step(model, data)

        # 3) Check for NaN
        if np.any(np.isnan(data.qpos)):
            print(f"\n!!! NaN at t={data.time:.3f}s — aborting")
            return

        # 4) Report
        if data.time >= next_report - 1e-6:
            bz_pos = data.xpos[_body_id(model, "bz-dozer")]
            md_pos = data.xpos[_body_id(model, "md-trunk_base")]
            jp_pos = data.xpos[_body_id(model, "jp-base_link")]

            print(
                f"{data.time:6.2f}s | "
                f"x={bz_pos[0]:+6.2f} z={bz_pos[2]:.3f} | "
                f"x={md_pos[0]:+6.2f} z={md_pos[2]:.3f} | "
                f"x={jp_pos[0]:+6.2f} z={jp_pos[2]:.3f} | "
                f"{data.ncon:3d}"
            )
            next_report += REPORT_INTERVAL

    # Final summary
    print()
    print("=" * 72)
    print(f"Simulation complete: {data.time:.2f}s, {n_ctrl_steps} control steps")
    bz_state = "stopped" if bz._stopped else "driving"
    md_st = md.read_state(data)
    jp_st = jp.read_state(data)
    md_standing = md_st["z"] > 0.08
    print(f"  Bulldozer: {bz_state}")
    print(f"  Microduck: z={md_st['z']:.3f} ({'standing' if md_standing else 'fallen'})")
    print(f"  Jumper:    pos=({jp_st['x']:.2f}, {jp_st['y']:.2f}, {jp_st['z']:.3f})")
    print(f"  NaN: {np.any(np.isnan(data.qpos))}")


if __name__ == "__main__":
    main()
