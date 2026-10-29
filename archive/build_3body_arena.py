"""Build and test a 3-body arena: Bulldozer + Microduck + Jumper via MjSpec.attach."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # archive/: resolve v6_common etc. from the repository root

import mujoco
import numpy as np

BASE = Path(__file__).resolve().parents[2]  # archive/: one level deeper than before the move; BASE is still the parent of the repository

BZ_XML = BASE / "physical-ai-course-builder" / "scene_fork_tracks.xml"
MD_XML = BASE / "microduck_rl" / "src" / "mjlab_microduck" / "robot" / "microduck" / "scene.xml"
JP_XML = BASE / "jumper" / "assets" / "jumper" / "jumper.xml"


def build_arena():
    print(f"MuJoCo version: {mujoco.__version__}")
    print(f"Python: {sys.version}")
    print()

    bz_spec = mujoco.MjSpec.from_file(str(BZ_XML))
    md_spec = mujoco.MjSpec.from_file(str(MD_XML))
    jp_spec = mujoco.MjSpec.from_file(str(JP_XML))

    print(f"Loaded specs:")
    print(f"  Bulldozer: {bz_spec.modelname!r}")
    print(f"  Microduck: {md_spec.modelname!r}")
    print(f"  Jumper:    {jp_spec.modelname!r}")
    print()

    # --- Build arena ---
    arena = mujoco.MjSpec()
    arena.modelname = "arena_3body"

    # Physics: use Microduck's timestep (0.002) for stability,
    # with bulldozer's integrator and cone settings
    arena.option.timestep = 0.002
    arena.option.integrator = 3   # implicitfast
    arena.option.cone = 1         # elliptic
    arena.option.iterations = 60

    # Ground plane
    floor = arena.worldbody.add_geom()
    floor.name = "arena_floor"
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.size = [20, 20, 0.1]
    floor.pos = [0, 0, 0]
    floor.rgba = [0.15, 0.2, 0.25, 1.0]

    # Light (directional via mode=0 is default; skip fancy config, scenes bring their own)

    # --- Scenario layout (top view) ---
    # Bulldozer starts at (-4, 0) heading +x, builds course
    # Microduck (Packan) stands at (0, 0) on the course
    # Jumper waits at (2, 0), will approach Packan
    #
    #   BZ -->  [course]  MD  <-- JP
    #  (-4,0)             (0,0)   (2,0)

    # 1) Attach Bulldozer at (-4, 0)
    bz_frame = arena.worldbody.add_frame()
    bz_frame.name = "bulldozer_origin"
    bz_frame.pos = [-4, 0, 0]
    arena.attach(bz_spec, prefix="bz-", frame=bz_frame)

    # 2) Attach Microduck at origin
    md_frame = arena.worldbody.add_frame()
    md_frame.name = "microduck_origin"
    md_frame.pos = [0, 0, 0]
    arena.attach(md_spec, prefix="md-", frame=md_frame)

    # 3) Attach Jumper at (2, 0)
    #    Jumper XML already has <joint name="floating_base" type="free"/> on base_link
    jp_frame = arena.worldbody.add_frame()
    jp_frame.name = "jumper_origin"
    jp_frame.pos = [2, 0, 0]
    arena.attach(jp_spec, prefix="jp-", frame=jp_frame)
    print("Attached jumper (has existing floating_base freejoint)")

    # Jumper XML has no <actuator> section (mjrl-lab adds them at runtime).
    # Add position actuators for all motor joints so the arena can drive them.
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
        act.gainprm[0] = 50.0  # kp (from jumper default class)
        act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        act.biasprm[1] = -50.0
        act.biasprm[2] = -0.5  # damping
    print(f"Added {len(JP_JOINTS)} position actuators for jumper")

    # --- Compile ---
    print()
    model = arena.compile()
    data = mujoco.MjData(model)

    print(f"Arena compiled:")
    print(f"  nq={model.nq}  nv={model.nv}  nu={model.nu}")
    print(f"  nbody={model.nbody}  njnt={model.njnt}  ngeom={model.ngeom}")
    print(f"  timestep={model.opt.timestep}")
    print()

    # List all bodies
    bodies = []
    for i in range(model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
        bodies.append(name or f"(anon_{i})")
    print(f"Bodies ({model.nbody}):")
    for prefix in ["bz-", "md-", "jp-"]:
        group = [b for b in bodies if b.startswith(prefix)]
        print(f"  {prefix}: {len(group)} bodies")

    # List all actuators
    actuators = []
    for i in range(model.nu):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        actuators.append(name)
    print()
    print(f"Actuators ({model.nu}):")
    for prefix, label in [("bz-", "Bulldozer"), ("md-", "Microduck"), ("jp-", "Jumper")]:
        group = [a for a in actuators if a and a.startswith(prefix)]
        print(f"  {label} ({len(group)}): {group}")

    # --- Reset Microduck to STAND ---
    stand_key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "md-STAND")
    if stand_key >= 0:
        mujoco.mj_resetDataKeyframe(model, data, stand_key)
        print(f"\nReset to md-STAND keyframe")

    # Set jumper slightly above ground
    jp_root_jnt = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "jp-floating_base")
    if jp_root_jnt >= 0:
        qpos_adr = model.jnt_qposadr[jp_root_jnt]
        data.qpos[qpos_adr + 2] = 0.08  # z height

    # --- Simulate ---
    print("\nRunning 500 steps...")
    for step in range(500):
        mujoco.mj_step(model, data)
        if step % 100 == 99:
            nan = np.any(np.isnan(data.qpos))
            print(f"  step {step+1}: time={data.time:.3f}s  NaN={nan}")

    # --- Final positions ---
    print(f"\nFinal state (t={data.time:.3f}s):")
    for name in ["bz-dozer", "md-trunk_base", "jp-base_link"]:
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        if bid >= 0:
            pos = data.xpos[bid]
            print(f"  {name:20s} pos=[{pos[0]:+8.4f}, {pos[1]:+8.4f}, {pos[2]:+8.4f}]")

    nan_final = np.any(np.isnan(data.qpos))
    print(f"\nNaN in qpos: {nan_final}")
    print(f"Total contacts: {data.ncon}")

    if not nan_final:
        print("\n=== 3-BODY ARENA: ALL OK ===")
    else:
        print("\n=== 3-BODY ARENA: NaN DETECTED ===")

    return model, data


if __name__ == "__main__":
    build_arena()
