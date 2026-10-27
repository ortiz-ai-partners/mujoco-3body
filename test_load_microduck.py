"""Test loading Microduck's MJCF files with MuJoCo 3.11."""
import sys
from pathlib import Path

import mujoco
import numpy as np

MICRODUCK_DIR = (
    Path(__file__).resolve().parent.parent
    / "microduck_rl"
    / "src"
    / "mjlab_microduck"
    / "robot"
    / "microduck"
)

SCENES = [
    "scene.xml",
    "scene_walk.xml",
    "scene_walk_backlash.xml",
    "scene_allcollisions.xml",
    "scene_backlash.xml",
    "scene_rollers.xml",
    "scene_ball.xml",
    "scene_apartment.xml",
]


def test_load(xml_path: Path) -> dict:
    result = {"file": xml_path.name, "ok": False, "error": None}
    try:
        model = mujoco.MjModel.from_xml_path(str(xml_path))
        data = mujoco.MjData(model)
        mujoco.mj_step(model, data)

        result["ok"] = True
        result["nq"] = model.nq
        result["nv"] = model.nv
        result["nu"] = model.nu
        result["nbody"] = model.nbody
        result["njnt"] = model.njnt
        result["ngeom"] = model.ngeom
        result["timestep"] = model.opt.timestep

        bodies = [
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
            for i in range(model.nbody)
        ]
        actuators = [
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            for i in range(model.nu)
        ]

        result["bodies"] = [b for b in bodies if b]
        result["actuators"] = actuators

        # Run 200 steps from STAND keyframe if available
        key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
        if key_id >= 0:
            mujoco.mj_resetDataKeyframe(model, data, key_id)
            result["keyframe"] = "STAND"
        else:
            result["keyframe"] = "(default)"

        for _ in range(200):
            mujoco.mj_step(model, data)

        trunk_id = -1
        for name in ["trunk", "base_link", "body"]:
            tid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
            if tid >= 0:
                trunk_id = tid
                break
        if trunk_id < 0:
            for i in range(1, model.nbody):
                n = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
                if n:
                    trunk_id = i
                    break

        if trunk_id >= 0:
            name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, trunk_id)
            result["trunk_name"] = name
            result["trunk_pos_200steps"] = data.xpos[trunk_id].tolist()

        result["time_200steps"] = float(data.time)
        result["nan_check"] = bool(np.any(np.isnan(data.qpos)))

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def main():
    print(f"MuJoCo version: {mujoco.__version__}")
    print(f"Python: {sys.version}")
    print(f"MJCF dir: {MICRODUCK_DIR}")
    print()

    ok_count = 0
    fail_count = 0
    skip_count = 0

    for name in SCENES:
        path = MICRODUCK_DIR / name
        if not path.exists():
            print(f"SKIP {name}: file not found")
            skip_count += 1
            continue

        r = test_load(path)
        if r["ok"]:
            ok_count += 1
            nan_flag = " NaN!" if r["nan_check"] else ""
            print(f"OK   {name}{nan_flag}")
            print(
                f"     nq={r['nq']} nv={r['nv']} nu={r['nu']} "
                f"nbody={r['nbody']} njnt={r['njnt']} ngeom={r['ngeom']} "
                f"timestep={r['timestep']}"
            )
            print(f"     actuators({r['nu']}): {r['actuators']}")
            if "trunk_name" in r:
                print(
                    f"     {r['trunk_name']} pos @200steps (from {r['keyframe']}): "
                    f"{r.get('trunk_pos_200steps', 'N/A')}"
                )
            print(f"     sim time @200steps: {r['time_200steps']:.4f}s")
        else:
            fail_count += 1
            print(f"FAIL {name}")
            print(f"     {r['error']}")
        print()

    print(f"--- Summary: {ok_count} OK, {fail_count} FAIL, {skip_count} SKIP ---")


if __name__ == "__main__":
    main()
