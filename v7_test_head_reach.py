"""How far forward/down can velstand bring the head while staying balanced? (physics only)

    python v7_test_head_reach.py
"""
from __future__ import annotations

import mujoco
import numpy as np

from v6_common import HERE, OUT_DIR
from v6_robots import body_tilt_deg, build_arena
from v7_policies import MD_CONTROL_DT, MicroduckPolicy
from v7_progress_video import official_md_servos

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
POLICY_DIR = HERE / "policies" / "microduck"
# (neck_pitch, head_pitch, head_yaw, head_roll), (body x, y, z, roll, pitch, yaw)
CASES = [
    ("rest", (0, 0, 0, 0), (0, 0, 0, 0, 0, 0)),
    ("neck.3 head.4", (0.3, 0.4, 0, 0), (0, 0, 0, 0, 0, 0)),
    ("neck.6 head.8", (0.6, 0.8, 0, 0), (0, 0, 0, 0, 0, 0)),
    ("neck1.0 head1.0", (1.0, 1.0, 0, 0), (0, 0, 0, 0, 0, 0)),
    ("neck1.1 head1.1", (1.1, 1.1, 0, 0), (0, 0, 0, 0, 0, 0)),
    ("neck1.0 head1.0 + body pitch .2", (1.0, 1.0, 0, 0), (0, 0, 0, 0, 0.2, 0)),
    ("neck1.0 head1.0 + body x+.02 z-.03", (1.0, 1.0, 0, 0), (0.02, 0, -0.03, 0, 0, 0)),
    ("neck1.1 head1.1 + body pitch .3 z-.03", (1.1, 1.1, 0, 0), (0, 0, -0.03, 0, 0.3, 0)),
]


def main():
    for name, head, body in CASES:
        model, data = build_arena(STAGE_XML, md_pose=(-1.0, -0.5, 0.0), timestep=0.005)
        official_md_servos(model)
        pol = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
        pol.hold_default(data)
        head_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "md-jaw_soft")
        steps = round(MD_CONTROL_DT / model.opt.timestep)
        k, t_cmd = 0, 1.5
        rest = None
        tilt_max = 0.0
        while data.time < 5.0:
            if data.time >= t_cmd:
                pol.head[:] = head
                pol.body[:] = body
            if k % steps == 0:
                pol.step(model, data)
            mujoco.mj_step(model, data)
            k += 1
            if data.time < t_cmd - 0.05:
                rest = (data.xpos[head_bid] - data.xpos[pol.bid]).copy()
            else:
                tilt_max = max(tilt_max, body_tilt_deg(data, pol.bid))
        R = data.xmat[pol.bid].reshape(3, 3)
        rel = R.T @ (data.xpos[head_bid] - data.xpos[pol.bid])     # head in trunk frame
        rest_rel = R.T @ rest
        print(f"{name:40s} head fwd {rel[0]:+.3f} m (rest {rest_rel[0]:+.3f})  up {rel[2]:+.3f} "
              f"(rest {rest_rel[2]:+.3f})  head world z {data.xpos[head_bid][2]:.3f}  trunk z {data.xpos[pol.bid][2]:.3f}"
              f"  tilt now {body_tilt_deg(data, pol.bid):4.1f} max {tilt_max:4.1f}")


if __name__ == "__main__":
    main()
