"""v7 - official policies in plain MuJoCo, physics only.

Jumper: the bundle contract (jumper/out/bundle_example/jumper/locomotion.json)
transcribed from deploy/fsm/src/obs.rs.  The robot moves through its own PD
actuators (kp 10 / kd 0.5 / 1.7464 N*m); no external forces anywhere.
"""
from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort

from v6_common import BASE

JP_BUNDLE = BASE / "jumper" / "out" / "bundle_example" / "jumper"


def _session(path):
    """One ONNX session with a single thread: the policies are small MLPs, and many scenes run in
    parallel for the manager's training - the default (all cores per session) oversubscribes badly."""
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), sess_options=opts)


def projected_gravity(q):
    """World down axis in the body frame, from (w, x, y, z) - obs.rs::projected_gravity."""
    w, x, y, z = q
    return np.array([-2.0 * (x * z - w * y), -2.0 * (y * z + w * x), -(1.0 - 2.0 * (x * x + y * y))],
                    dtype=np.float32)


class JumperLocomotion:
    """jumper.posture policy ("locomotion" mode): velocity + posture commands, 200 Hz."""

    def __init__(self, model, data, prefix="jp-", bundle=JP_BUNDLE):
        c = json.loads((bundle / "locomotion.json").read_text(encoding="utf-8"))
        self.c = c
        self.sess = _session(bundle / "models" / "locomotion.onnx")
        self.in_name = self.sess.get_inputs()[0].name
        self.wire = c["wire_joint_order"]
        self.default = np.array([c["default_joint_pos"][j] for j in self.wire], dtype=np.float32)
        self.limits = np.array([c["joint_limits"][j] for j in self.wire], dtype=np.float32)
        self.obs_idx = np.array([self.wire.index(j) for j in c["obs_joint_order"]])
        self.act_idx = np.array([self.wire.index(j) for j in c["action_joint_order"]])
        self.scale = float(c["action_scale"])
        self.control_dt = float(c["control"]["control_dt"])
        self.terms = c["observation"]["terms"]
        self.dim = int(c["observation"]["dim"])
        gp = next(t for t in self.terms if t["name"] == "gait_phase")["params"]
        self.stride, self.fmin, self.fmax = gp["stride"], gp["freq_min"], gp["freq_max"]
        self.turn_r, self.gate_thr = gp["turn_radius"], gp["command_threshold"]
        self.neutral_h = next(t for t in self.terms if t["name"] == "posture_command")["params"]["neutral_height"]

        J, A = mujoco.mjtObj.mjOBJ_JOINT, mujoco.mjtObj.mjOBJ_ACTUATOR
        jids = [mujoco.mj_name2id(model, J, prefix + j) for j in self.wire]
        assert min(jids) >= 0, "jumper joints not found"
        self.qadr = np.array([model.jnt_qposadr[j] for j in jids])
        self.dadr = np.array([model.jnt_dofadr[j] for j in jids])
        self.act_ids = np.array([mujoco.mj_name2id(model, A, prefix + j) for j in self.wire])
        assert self.act_ids.min() >= 0, "jumper actuators not found"
        self.bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, prefix + "base_link")
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, prefix + "imu_ang_vel")
        self.gyro_adr = int(model.sensor_adr[sid])
        self.reset()

    def reset(self):
        self.phase = 0.0
        self.last_action = np.zeros(len(self.act_idx), dtype=np.float32)
        self.rings = {}
        self.cmd = np.zeros(3, dtype=np.float32)        # vx, vy, yaw_rate (body frame)
        self.posture = np.zeros(4, dtype=np.float32)    # twist, pitch, roll, height - neutral
        self.last_obs = None

    def set_command(self, vx=0.0, vy=0.0, wz=0.0):
        self.cmd = np.array([vx, vy, wz], dtype=np.float32)

    def frequency(self):
        v = math.hypot(self.cmd[0], self.cmd[1]) + abs(self.cmd[2]) * self.turn_r
        return min(max(v / (2.0 * self.stride), self.fmin), self.fmax)

    def _current(self, model, data):
        q = data.qpos[self.qadr].astype(np.float32)
        qd = data.qvel[self.dadr].astype(np.float32)
        tau = data.actuator_force[self.act_ids].astype(np.float32)
        gate = 1.0 if float(np.linalg.norm(self.cmd)) > self.gate_thr else 0.0
        a = self.phase * 2.0 * math.pi
        return {
            "base_ang_vel": data.sensordata[self.gyro_adr:self.gyro_adr + 3].astype(np.float32),
            "projected_gravity": projected_gravity(data.xquat[self.bid]),
            "joint_pos": (q - self.default)[self.obs_idx],
            "joint_vel": qd[self.obs_idx],
            "actions": self.last_action,
            "velocity_commands": self.cmd,
            "joint_torque": tau[self.obs_idx],
            "gait_phase": np.array([math.sin(a) * gate, math.cos(a) * gate], dtype=np.float32),
            "posture_command": self.posture,
        }

    def observe(self, model, data):
        cur = self._current(model, data)
        parts = []
        for t in self.terms:
            x = cur[t["name"]]
            H, S = int(t.get("history_length", 1)), int(t.get("history_stride", 1))
            if H > 1:
                ring = self.rings.get(t["name"])
                if ring is None:
                    ring = deque([x.copy() for _ in range(S * (H - 1) + 1)], maxlen=S * (H - 1) + 1)
                    self.rings[t["name"]] = ring
                else:
                    ring.append(x.copy())
                parts.extend(ring[i] for i in range(0, len(ring), S))     # oldest first
            else:
                parts.append(x)
        obs = np.concatenate(parts).astype(np.float32)
        assert obs.size == self.dim, (obs.size, self.dim)
        self.phase = (self.phase + self.frequency() * self.control_dt) % 1.0   # "after_frame"
        self.last_obs = obs
        return obs

    def step(self, model, data):
        """One inference (call every control_dt of simulated time); writes joint targets."""
        obs = self.observe(model, data)
        a = self.sess.run(None, {self.in_name: obs[None, :]})[0][0].astype(np.float32)
        self.last_action = a
        target = self.default.copy()
        target[self.act_idx] += self.scale * a
        target = np.clip(target, self.limits[:, 0], self.limits[:, 1])
        data.ctrl[self.act_ids] = target
        return a

    def hold_home(self, data):
        data.ctrl[self.act_ids] = self.default


# ── Microduck: scripts/infer_policy.py's observation, XML PD actuators (--no-bam) ──
MD_DEFAULT_POSE = np.array([
    0.0, -0.0873, -0.4579, -0.0049, 0.4530,        # left hip_yaw, hip_roll, hip_pitch, knee, ankle
    0.3491, 0.3491, 0.0, 0.0,                      # neck_pitch, head_pitch, head_yaw, head_roll
    0.0, 0.0873, 0.4579, 0.0049, -0.4530,          # right leg
], dtype=np.float32)
MD_CONTROL_DT = 0.02        # 50 Hz, decimation 4 at 0.005


class MicroduckPolicy:
    """Official Microduck ONNX policy in plain MuJoCo.

    Observation (infer_policy.py): [gyro(3), projected_gravity(3), joint_pos - default(14),
    joint_vel(14), last_action(14), command(3 | 13)].  Action: target = default + a * scale,
    fed to the XML position actuators (the --no-bam rehearsal path).
    """

    def __init__(self, model, data, onnx_path, prefix="md-", action_scale=1.0):
        self.sess = _session(onnx_path)
        inp = self.sess.get_inputs()[0]
        self.in_name = inp.name
        self.obs_dim = int(inp.shape[1])
        self.new_cmd = self.obs_dim == 61
        A = mujoco.mjtObj.mjOBJ_ACTUATOR
        self.act_ids = np.array([i for i in range(model.nu)
                                 if (mujoco.mj_id2name(model, A, i) or "").startswith(prefix)])
        assert len(self.act_ids) == 14, len(self.act_ids)
        self.qpos_idx = np.array([model.jnt_qposadr[model.actuator_trnid[a, 0]] for a in self.act_ids])
        self.qvel_idx = np.array([model.jnt_dofadr[model.actuator_trnid[a, 0]] for a in self.act_ids])
        self.bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, prefix + "trunk_base")
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, prefix + "imu_ang_vel")
        self.gyro_adr = int(model.sensor_adr[sid])
        self.default = MD_DEFAULT_POSE.copy()
        self.scale = action_scale
        self.reset()

    def reset(self):
        self.last_action = np.zeros(14, dtype=np.float32)
        self.twist = np.zeros(3, dtype=np.float32)
        self.head = np.zeros(4, dtype=np.float32)      # neck_pitch, head_pitch, head_yaw, head_roll
        self.body = np.zeros(6, dtype=np.float32)      # x y z roll pitch yaw
        self.flag = 0.0                                # sitstand posture flag (twist slot 0)

    def command(self):
        if self.new_cmd:
            c = np.zeros(13, dtype=np.float32)
            c[0:3] = self.twist
            c[3:7] = self.head
            c[7:13] = self.body
            return c
        return self.twist.copy()

    def observe(self, model, data):
        obs = np.concatenate([
            data.sensordata[self.gyro_adr:self.gyro_adr + 3].astype(np.float32),
            projected_gravity(data.xquat[self.bid]),
            data.qpos[self.qpos_idx].astype(np.float32) - self.default,
            data.qvel[self.qvel_idx].astype(np.float32),
            self.last_action,
            self.command(),
        ]).astype(np.float32)
        assert obs.size == self.obs_dim, (obs.size, self.obs_dim)
        return obs

    def step(self, model, data):
        obs = self.observe(model, data)
        a = self.sess.run(None, {self.in_name: obs[None, :]})[0][0].astype(np.float32)
        self.last_action = a
        target = self.default + a * self.scale
        if not self.new_cmd:
            target = target.copy()
            target[5:9] += self.head
        data.ctrl[self.act_ids] = target
        return a

    def hold_default(self, data):
        data.ctrl[self.act_ids] = self.default


def _lerp_row(table, idx):
    i0 = int(math.floor(idx))
    i1 = min(i0 + 1, len(table) - 1)
    a = idx - i0
    return (1.0 - a) * table[i0] + a * table[i1]


def set_pd_gains(model, act_ids, kp, kd):
    for a in act_ids:
        model.actuator_gainprm[a, 0] = kp
        model.actuator_biasprm[a, 1] = -kp
        model.actuator_biasprm[a, 2] = -kd


class JumperJump:
    """jumper.jump: a residual on the recorded high jump (high_jump_flat), 200 Hz, kp 20."""

    def __init__(self, model, data, prefix="jp-", bundle=JP_BUNDLE):
        c = json.loads((bundle / "jump.json").read_text(encoding="utf-8"))
        self.c = c
        self.sess = _session(bundle / "models" / "jump.onnx")
        self.in_name = self.sess.get_inputs()[0].name
        self.wire = c["wire_joint_order"]
        self.default = np.array([c["default_joint_pos"][j] for j in self.wire], dtype=np.float32)
        self.limits = np.array([c["joint_limits"][j] for j in self.wire], dtype=np.float32)
        self.obs_idx = np.array([self.wire.index(j) for j in c["obs_joint_order"]])
        self.act_idx = np.array([self.wire.index(j) for j in c["action_joint_order"]])
        self.scale = float(c["action_scale"])
        self.control_dt = float(c["control"]["control_dt"])
        self.kp, self.kd = float(c["control"]["kp"]), float(c["control"]["kd"])
        self.terms = c["observation"]["terms"]
        self.dim = int(c["observation"]["dim"])
        r = c["reference"]
        self.r = r
        traj = json.loads((bundle / r["file"]).read_text(encoding="utf-8"))
        order = traj["joint_order"]
        perm = [order.index(j) for j in self.wire]
        self.q = np.asarray(traj["q"], dtype=np.float32)[:, perm]
        self.q_cmd = np.asarray(traj["q_cmd"], dtype=np.float32)[:, perm]
        assert len(self.q) == r["n_frames"] and len(self.q_cmd) == r["n_cmd"]

        J, A = mujoco.mjtObj.mjOBJ_JOINT, mujoco.mjtObj.mjOBJ_ACTUATOR
        jids = [mujoco.mj_name2id(model, J, prefix + j) for j in self.wire]
        self.qadr = np.array([model.jnt_qposadr[j] for j in jids])
        self.dadr = np.array([model.jnt_dofadr[j] for j in jids])
        self.act_ids = np.array([mujoco.mj_name2id(model, A, prefix + j) for j in self.wire])
        self.bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, prefix + "base_link")
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, prefix + "imu_ang_vel")
        self.gyro_adr = int(model.sensor_adr[sid])
        self.reset()

    # Forward jump (ゆうころ 10/27): sweep every foot backward with the hip yaw J0 while
    # the legs push, so the vertical high jump gets a forward component.  Joint targets
    # only - no external force.  Left legs +J0 moves the foot toward -x, right legs -J0.
    SWEEP_SIGN = {"LF_J0_joint": 1.0, "LM_J0_joint": 1.0, "LR_J0_joint": 1.0,
                  "RF_J0_joint": -1.0, "RM_J0_joint": -1.0, "RR_J0_joint": -1.0}
    SWEEP_PHASES = (0.26, 0.38, 0.44, 0.56)   # ramp up, full, release, back to zero (jump phase)

    def reset(self, sweep=0.0):
        self.step_n = 0
        self.last_action = np.zeros(len(self.act_idx), dtype=np.float32)
        self.sweep = float(sweep)
        self.sweep_idx = np.array([self.wire.index(j) for j in self.SWEEP_SIGN])
        self.sweep_sign = np.array(list(self.SWEEP_SIGN.values()), dtype=np.float32)

    def sweep_gain(self, phase):
        a, b, c, d = self.SWEEP_PHASES
        if phase <= a or phase >= d:
            return 0.0
        if phase < b:
            return (phase - a) / (b - a)
        if phase <= c:
            return 1.0
        return (d - phase) / (d - c)

    def t_since_go(self):
        return self.step_n * self.control_dt

    def finished(self):
        return self.r["t_go"] + self.t_since_go() >= self.r["duration"]

    def q_at(self, tsg):
        idx = (self.r["t_go"] + tsg) * self.r["rec_hz"]
        idx = min(max(idx, self.r["go_frame"]), len(self.q) - 1)
        return _lerp_row(self.q, idx)

    def baseline(self, tsg):
        t_abs = tsg + self.r["t_go"] + self.r.get("baseline_lead_s", 0.0)
        idx = min(max(t_abs * self.r["control_hz"], 0.0), len(self.q_cmd) - 1)
        return _lerp_row(self.q_cmd, idx)

    def observe(self, model, data):
        tsg = self.t_since_go()
        q = data.qpos[self.qadr].astype(np.float32)
        qd = data.qvel[self.dadr].astype(np.float32)
        parts = [data.sensordata[self.gyro_adr:self.gyro_adr + 3].astype(np.float32),
                 projected_gravity(data.xquat[self.bid]),
                 (q - self.default)[self.obs_idx], qd[self.obs_idx], self.last_action,
                 np.array([min(max(tsg / self.r["span"], 0.0), 1.0)], dtype=np.float32)]
        for la in self.r["lookahead_s"]:
            parts.append((self.q_at(tsg + la) - self.default)[self.obs_idx])
        obs = np.concatenate(parts).astype(np.float32)
        assert obs.size == self.dim, (obs.size, self.dim)
        return obs, self.baseline(tsg)

    def step(self, model, data):
        obs, base = self.observe(model, data)
        a = self.sess.run(None, {self.in_name: obs[None, :]})[0][0].astype(np.float32)
        self.last_action = a
        target = base.copy()
        target[self.act_idx] += self.scale * a
        if self.sweep:
            g = self.sweep_gain(self.t_since_go() / self.r["span"])
            target[self.sweep_idx] += self.sweep * g * self.sweep_sign
        target = np.clip(target, self.limits[:, 0], self.limits[:, 1])
        data.ctrl[self.act_ids] = target
        self.step_n += 1
        return a


class JumperDance:
    """jumper.dance: the robot tracks a recorded dance (demo.motion), 50 Hz, kp 10 / kd 0.5.

    Observation (dance_crab.json, 209): clip_phase, ref_joint_pos (HOME-relative), ref_joint_vel
    (absolute), ref_future (3 lookaheads, HOME-relative), ref_tilt_error (recording's gravity
    direction minus the robot's), gyro, projected gravity, joint pos/vel, last action, torque.
    target = HOME + 0.25 * action (no residual baseline).  Transcribed from
    deploy/fsm/src/obs.rs and trajectory.rs (frame index clamps at the end, never wraps;
    root_quat is nearest-frame).
    """

    def __init__(self, model, data, prefix="jp-", bundle=JP_BUNDLE, name="dance_crab"):
        c = json.loads((bundle / f"{name}.json").read_text(encoding="utf-8"))
        self.c = c
        self.sess = _session(bundle / "models" / f"{name}.onnx")
        self.in_name = self.sess.get_inputs()[0].name
        self.wire = c["wire_joint_order"]
        self.default = np.array([c["default_joint_pos"][j] for j in self.wire], dtype=np.float32)
        self.limits = np.array([c["joint_limits"][j] for j in self.wire], dtype=np.float32)
        self.obs_idx = np.array([self.wire.index(j) for j in c["obs_joint_order"]])
        self.act_idx = np.array([self.wire.index(j) for j in c["action_joint_order"]])
        self.scale = float(c["action_scale"])
        self.control_dt = float(c["control"]["control_dt"])
        self.kp, self.kd = float(c["control"]["kp"]), float(c["control"]["kd"])
        self.terms = c["observation"]["terms"]
        self.dim = int(c["observation"]["dim"])
        r = c["reference"]
        assert not r.get("residual_action", False), "dance contract is not a residual"
        self.rec_hz = float(r["rec_hz"])
        self.lookahead = [float(x) for x in r["lookahead_s"]]
        self.duration = float(r["duration"])
        traj = json.loads((bundle / r["file"]).read_text(encoding="utf-8"))
        perm = [traj["joint_order"].index(j) for j in self.wire]
        self.q = np.asarray(traj["q"], dtype=np.float32)[:, perm]
        self.qd = np.asarray(traj["qd"], dtype=np.float32)[:, perm]
        self.root_quat = np.asarray(traj["root_quat"], dtype=np.float32)      # (w, x, y, z)
        self.n_frames = len(self.q)
        assert self.n_frames == int(r["n_frames"]) and len(self.qd) == self.n_frames

        J, A = mujoco.mjtObj.mjOBJ_JOINT, mujoco.mjtObj.mjOBJ_ACTUATOR
        jids = [mujoco.mj_name2id(model, J, prefix + j) for j in self.wire]
        self.qadr = np.array([model.jnt_qposadr[j] for j in jids])
        self.dadr = np.array([model.jnt_dofadr[j] for j in jids])
        self.act_ids = np.array([mujoco.mj_name2id(model, A, prefix + j) for j in self.wire])
        self.bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, prefix + "base_link")
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, prefix + "imu_ang_vel")
        self.gyro_adr = int(model.sensor_adr[sid])
        self.reset()

    def reset(self, t_start=0.0):
        """Start (or restart) the dance; t_start picks where in the recording it begins."""
        self.step_n = 0
        self.t_start = float(t_start)
        self.last_action = np.zeros(len(self.act_idx), dtype=np.float32)

    def t_since_go(self):
        return self.t_start + self.step_n * self.control_dt

    def finished(self):
        return self.t_since_go() >= self.duration

    def frame_at(self, t):
        return min(max(t * self.rec_hz, 0.0), float(self.n_frames - 1))

    def q_at(self, t):
        return _lerp_row(self.q, self.frame_at(t))

    def qd_at(self, t):
        return _lerp_row(self.qd, self.frame_at(t))

    def root_quat_at(self, t):
        return self.root_quat[min(int(round(self.frame_at(t))), len(self.root_quat) - 1)]

    def observe(self, model, data):
        tsg = self.t_since_go()
        q = data.qpos[self.qadr].astype(np.float32)
        qd = data.qvel[self.dadr].astype(np.float32)
        tau = data.actuator_force[self.act_ids].astype(np.float32)
        grav = projected_gravity(data.xquat[self.bid])
        a = self.frame_at(tsg) * 2.0 * math.pi / self.n_frames
        cur = {
            "clip_phase": np.array([math.sin(a), math.cos(a)], dtype=np.float32),
            "ref_joint_pos": (self.q_at(tsg) - self.default)[self.obs_idx],
            "ref_joint_vel": self.qd_at(tsg)[self.obs_idx],
            "ref_future": np.concatenate([(self.q_at(tsg + la) - self.default)[self.obs_idx]
                                          for la in self.lookahead]),
            "ref_tilt_error": projected_gravity(self.root_quat_at(tsg)) - grav,
            "base_ang_vel": data.sensordata[self.gyro_adr:self.gyro_adr + 3].astype(np.float32),
            "projected_gravity": grav,
            "joint_pos": (q - self.default)[self.obs_idx],
            "joint_vel": qd[self.obs_idx],
            "actions": self.last_action,
            "joint_torque": tau[self.obs_idx],
        }
        obs = np.concatenate([cur[t["name"]] for t in self.terms]).astype(np.float32)
        assert obs.size == self.dim, (obs.size, self.dim)
        return obs

    def step(self, model, data):
        """One inference (every control_dt = 0.02 s of simulated time); writes joint targets."""
        obs = self.observe(model, data)
        a = self.sess.run(None, {self.in_name: obs[None, :]})[0][0].astype(np.float32)
        self.last_action = a
        target = self.default.copy()
        target[self.act_idx] += self.scale * a
        target = np.clip(target, self.limits[:, 0], self.limits[:, 1])
        data.ctrl[self.act_ids] = target
        self.step_n += 1
        return a
