"""Test loading the bulldozer's MJCF files with MuJoCo 3.11."""
import sys
from pathlib import Path

import mujoco
import numpy as np

BULLDOZER_DIR = Path(__file__).resolve().parent.parent / "physical-ai-course-builder"
SCENES = [
    "scene.xml",
    "scene_fork.xml",
    "scene_tracks.xml",
    "scene_fork_tracks.xml",
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

        bodies = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
                  for i in range(model.nbody)]
        joints = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
                  for i in range(model.njnt)]
        actuators = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
                     for i in range(model.nu)]

        result["bodies"] = [b for b in bodies if b]
        result["joints"] = [j for j in joints if j]
        result["actuators"] = actuators

        # Run 100 steps to check stability
        for _ in range(100):
            mujoco.mj_step(model, data)
        dozer_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dozer")
        if dozer_id >= 0:
            result["dozer_pos_after_100steps"] = data.xpos[dozer_id].tolist()
        result["time_after_100steps"] = float(data.time)

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def main():
    print(f"MuJoCo version: {mujoco.__version__}")
    print(f"Python: {sys.version}")
    print()

    for name in SCENES:
        path = BULLDOZER_DIR / name
        if not path.exists():
            print(f"SKIP {name}: file not found")
            continue

        r = test_load(path)
        if r["ok"]:
            print(f"OK   {name}")
            print(f"     nq={r['nq']} nv={r['nv']} nu={r['nu']} "
                  f"nbody={r['nbody']} njnt={r['njnt']} ngeom={r['ngeom']} "
                  f"timestep={r['timestep']}")
            print(f"     bodies: {r['bodies']}")
            print(f"     joints: {r['joints']}")
            print(f"     actuators: {r['actuators']}")
            print(f"     dozer pos @100steps: {r.get('dozer_pos_after_100steps', 'N/A')}")
            print(f"     sim time @100steps: {r['time_after_100steps']:.4f}s")
        else:
            print(f"FAIL {name}")
            print(f"     {r['error']}")
        print()


if __name__ == "__main__":
    main()
