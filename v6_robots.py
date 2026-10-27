"""Robots on the built stage: arena assembly, resets and controllers for MD and JP.

Honesty notes for the report
----------------------------
* BZ construction (Phase 1) is pure physics + rule control.
* MD walks with a scripted gait; a *virtual harness* (external force/torque on
  the trunk via xfrc_applied) keeps it upright and pulls it along the path.
  It is a demo aid, not a balance controller, and it is switched off for the fall.
* MD servo gains are raised from the XML's kp=0.55 / 0.96 Nm (which sags under
  its own weight without the trained policy) to idealised values.
* JP uses the jumper repo's HOME pose and PD gains; its hop is scripted and a
  guidance force steers it (also a demo aid). Contacts are real physics.
"""
from __future__ import annotations

import math
import warnings

import mujoco
import numpy as np

from v6_common import JP_XML, MD_XML, VIDEO_H, VIDEO_W, quat_to_yaw

# ── Jumper facts (jumper/tasks/jumper/common/constants.py) ───────────────
JP_HOME = {
    "LF_J0_joint": -0.5507, "LF_J1_joint": -1.0658,
    "LF_J2_joint": -0.4408, "LF_J3_joint": -1.374, "LF_J4_joint": 0.0,
    "RF_J0_joint": 0.5524, "RF_J1_joint": -1.066,
    "RF_J2_joint": 0.4414, "RF_J3_joint": 1.4173, "RF_J4_joint": 0.0,
    "LM_J0_joint": 0.0012, "LM_J1_joint": 0.5356, "LM_J2_joint": -1.8271,
    "RM_J0_joint": -0.0012, "RM_J1_joint": -0.5376, "RM_J2_joint": 1.8313,
    "LR_J0_joint": 0.6313, "LR_J1_joint": 0.5534, "LR_J2_joint": -1.8648,
    "RR_J0_joint": -0.6326, "RR_J1_joint": -0.5548, "RR_J2_joint": 1.8678,
}
JP_STAND_Z = 0.10647
JP_KP, JP_KD, JP_EFFORT = 10.0, 0.5, 1.7464

# ── Microduck: idealised servo gains for the demo ────────────────────────
MD_KP, MD_KV, MD_FORCE = 8.0, 0.3, 5.0
MD_STAND_Z = 0.12


def yaw_quat(yaw):
    return [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]


def upright_torque(data, bid, w_local, yaw_des, k, d, cap):
    """PD torque (world frame) that turns body `bid` toward level with heading yaw_des."""
    err = np.zeros(3)
    mujoco.mju_subQuat(err, np.array(yaw_quat(yaw_des)), data.xquat[bid])
    tau_local = k * err - d * w_local
    n = np.linalg.norm(tau_local)
    if n > cap:
        tau_local *= cap / n
    return data.xmat[bid].reshape(3, 3) @ tau_local


def body_tilt_deg(data, bid):
    return math.degrees(math.acos(max(-1.0, min(1.0, data.xmat[bid].reshape(3, 3)[2, 2]))))


_GROUND_GROUPS = np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8)   # stage geoms only (robots use 1-3)


def ground_height(model, data, x, y):
    """Height of the stage (floor or slope deck) under world point (x, y)."""
    pnt = np.array([x, y, 1.5])
    geomid = np.array([-1], dtype=np.int32)
    dist = mujoco.mj_ray(model, data, pnt, np.array([0.0, 0.0, -1.0]), _GROUND_GROUPS, 1, -1, geomid)
    return float(1.5 - dist) if dist >= 0 else 0.0


def _prefixed(model, objtype, prefix):
    n = {mujoco.mjtObj.mjOBJ_ACTUATOR: model.nu, mujoco.mjtObj.mjOBJ_JOINT: model.njnt}[objtype]
    return [i for i in range(n)
            if (mujoco.mj_id2name(model, objtype, i) or "").startswith(prefix)]


# ── Arena ────────────────────────────────────────────────────────────────
def build_arena(stage_xml, md_pose=None, jp_pose=None, timestep=0.002):
    """Stage (a scene file, or an XML string) + optional MD / JP.  Poses are (x, y, yaw)."""
    if str(stage_xml).lstrip().startswith("<"):
        spec = mujoco.MjSpec.from_string(str(stage_xml))
    else:
        spec = mujoco.MjSpec.from_file(str(stage_xml))
    spec.modelname = "arena_v6"
    spec.option.timestep = timestep
    spec.visual.global_.offwidth = VIDEO_W
    spec.visual.global_.offheight = VIDEO_H
    sky = spec.add_texture()
    sky.name = "sky"
    sky.type = mujoco.mjtTexture.mjTEXTURE_SKYBOX
    sky.builtin = mujoco.mjtBuiltin.mjBUILTIN_GRADIENT
    sky.rgb1 = [0.55, 0.72, 0.90]
    sky.rgb2 = [0.12, 0.16, 0.24]
    sky.width = sky.height = 512

    if md_pose is not None:
        child = mujoco.MjSpec.from_file(str(MD_XML))
        f = spec.worldbody.add_frame()
        f.name = "md_origin"
        spec.attach(child, prefix="md-", frame=f)
    if jp_pose is not None:
        child = mujoco.MjSpec.from_file(str(JP_XML))
        f = spec.worldbody.add_frame()
        f.name = "jp_origin"
        spec.attach(child, prefix="jp-", frame=f)
        for jname in JP_HOME:
            act = spec.add_actuator()
            act.name = f"jp-{jname}"
            act.target = f"jp-{jname}"
            act.trntype = mujoco.mjtTrn.mjTRN_JOINT
            act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
            act.gainprm[0] = JP_KP
            act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
            act.biasprm[1] = -JP_KP
            act.biasprm[2] = -JP_KD
            act.forcerange = [-JP_EFFORT, JP_EFFORT]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = spec.compile()

    # The child scenes bring their own lights; keep only the stage's own.
    for i in range(1, model.nlight):
        model.light_active[i] = 0
    gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "md-floor")
    if gid >= 0:
        model.geom_contype[gid] = 0
        model.geom_conaffinity[gid] = 0
        model.geom_rgba[gid] = [0, 0, 0, 0]
    for aid in _prefixed(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "md-"):
        model.actuator_gainprm[aid, 0] = MD_KP
        model.actuator_biasprm[aid, 1] = -MD_KP
        model.actuator_biasprm[aid, 2] = -MD_KV
        model.actuator_forcerange[aid] = [-MD_FORCE, MD_FORCE]

    data = mujoco.MjData(model)
    if md_pose is not None:
        reset_md(model, data, md_pose)
    if jp_pose is not None:
        reset_jp(model, data, jp_pose)
    mujoco.mj_forward(model, data)
    return model, data


def reset_md(model, data, pose):
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "md-STAND")
    for j in _prefixed(model, mujoco.mjtObj.mjOBJ_JOINT, "md-"):
        adr = model.jnt_qposadr[j]
        if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
            data.qpos[adr:adr + 3] = [pose[0], pose[1], MD_STAND_Z + 0.004]
            data.qpos[adr + 3:adr + 7] = yaw_quat(pose[2])
        else:
            data.qpos[adr] = model.key_qpos[key][adr]
    acts = _prefixed(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "md-")
    data.ctrl[acts] = model.key_ctrl[key][acts]


def reset_jp(model, data, pose):
    for j in _prefixed(model, mujoco.mjtObj.mjOBJ_JOINT, "jp-"):
        adr = model.jnt_qposadr[j]
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j)[3:]
        if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
            data.qpos[adr:adr + 3] = [pose[0], pose[1], JP_STAND_Z + 0.005]
            data.qpos[adr + 3:adr + 7] = yaw_quat(pose[2])
        else:
            data.qpos[adr] = JP_HOME[name]
    for aid in _prefixed(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "jp-"):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, aid)[3:]
        data.ctrl[aid] = JP_HOME[name]


# ── Microduck controller ─────────────────────────────────────────────────
class MicroduckCtrl:
    """Scripted gait + virtual harness.  Modes: STAND, WALK, FALLEN, RECOVER."""

    GAIT_HZ = 1.6
    HIP_SWING = 0.28      # rad, hip pitch
    KNEE_LIFT = 0.50      # rad, swing-leg knee
    # harness gains (N/m, N s/m, N m/rad, N m s/rad) and caps
    KP_XY, KD_XY, KP_Z, KD_Z = 30.0, 6.0, 80.0, 10.0
    KR, DR = 3.0, 0.06
    F_MAX, T_MAX = 6.0, 1.2

    def __init__(self, model, data, pose, speed=0.15):
        self.bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "md-trunk_base")
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "md-trunk_base_freejoint")
        self.dadr = model.jnt_dofadr[jid]
        self.act_ids = np.array(_prefixed(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "md-"), dtype=int)
        self.local = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, a)[3:]: i
                      for i, a in enumerate(self.act_ids)}
        key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "md-STAND")
        self.stand = model.key_ctrl[key][self.act_ids].copy()
        self.yaw = pose[2]
        self.heading = np.array([math.cos(self.yaw), math.sin(self.yaw)])
        self.anchor = np.array(pose[:2], dtype=float)
        self.speed = speed
        self.path_s = 0.0
        self.phase = 0.0
        self.mode = "STAND"
        self.t_mode = 0.0
        self.harness = 1.0
        self.z_des = MD_STAND_Z
        self.mass = float(model.body_subtreemass[self.bid])
        self.events = []
        self.gaze = None          # world xy to turn the head toward
        self.quack = False        # head bobbing ("ガーガー")
        self.goal = None
        self.arrived = False
        self.stop_dist = 0.32
        self.terrain = False      # follow the stage height (slopes) with the harness

    def set_mode(self, mode, t):
        if mode != self.mode:
            self.events.append({"t": round(t, 3), "mode": mode})
            self.mode, self.t_mode = mode, t

    def rebase(self, data):
        """Restart the path from where the trunk is now (after a fall)."""
        self.anchor = data.xpos[self.bid][:2].copy()
        self.path_s = 0.0
        self.goal = None
        self.arrived = False

    def walk_to(self, xy, data, stop_dist=0.32):
        """Turn toward a world point and walk until `stop_dist` from it."""
        self.rebase(data)
        d = np.asarray(xy, dtype=float) - self.anchor
        self.yaw = math.atan2(d[1], d[0])
        self.heading = np.array([math.cos(self.yaw), math.sin(self.yaw)])
        self.goal = np.asarray(xy, dtype=float)
        self.stop_dist = stop_dist

    # observations
    def pos(self, data):
        return data.xpos[self.bid]

    def tilt_deg(self, data):
        return math.degrees(math.acos(max(-1.0, min(1.0, data.xmat[self.bid].reshape(3, 3)[2, 2]))))

    def step(self, model, data, t, dt):
        ctrl = self.stand.copy()
        if self.mode == "WALK":
            if self.goal is not None and np.linalg.norm(self.goal - data.xpos[self.bid][:2]) < self.stop_dist:
                self.arrived = True
            if not self.arrived:
                self.path_s += self.speed * dt
            self.phase += 2 * math.pi * self.GAIT_HZ * dt
            s = math.sin(self.phase)
            swing = -self.HIP_SWING * s
            ctrl[self.local["left_hip_pitch"]] += swing
            ctrl[self.local["right_hip_pitch"]] += swing
            ctrl[self.local["left_ankle"]] -= swing * 0.8
            ctrl[self.local["right_ankle"]] -= swing * 0.8
            ctrl[self.local["left_knee"]] += self.KNEE_LIFT * max(0.0, s)
            ctrl[self.local["right_knee"]] -= self.KNEE_LIFT * max(0.0, -s)
            if self.gaze is None:
                ctrl[self.local["head_yaw"]] += 0.15 * math.sin(0.7 * self.phase)
        elif self.mode == "FALLEN":
            ctrl = data.ctrl[self.act_ids].copy()      # go limp at the last command
        if self.mode in ("STAND", "WALK"):
            if self.gaze is not None:
                d = np.asarray(self.gaze, dtype=float) - data.xpos[self.bid][:2]
                yaw = quat_to_yaw(data.xquat[self.bid])
                e = (math.atan2(d[1], d[0]) - yaw + math.pi) % (2 * math.pi) - math.pi
                ctrl[self.local["head_yaw"]] += float(np.clip(e, -0.8, 0.8))
            if self.quack:
                ctrl[self.local["head_pitch"]] += 0.18 * math.sin(2 * math.pi * 3.0 * t)
                ctrl[self.local["neck_pitch"]] += 0.10 * math.sin(2 * math.pi * 3.0 * t)
        data.ctrl[self.act_ids] = ctrl

        # virtual harness (pulls harder while righting the robot after a fall)
        boost = 2.0 if self.mode == "RECOVER" else 1.0
        p = data.xpos[self.bid]
        if self.terrain:
            self.z_des = ground_height(model, data, p[0], p[1]) + MD_STAND_Z
        v = data.qvel[self.dadr:self.dadr + 3]
        w_local = data.qvel[self.dadr + 3:self.dadr + 6]
        target = self.anchor + self.heading * self.path_s
        F = np.zeros(3)
        F[:2] = self.KP_XY * (target - p[:2]) - self.KD_XY * v[:2]
        F[2] = self.KP_Z * (self.z_des - p[2]) - self.KD_Z * v[2]
        n = np.linalg.norm(F)
        if n > self.F_MAX * boost:
            F *= self.F_MAX * boost / n
        tau = upright_torque(data, self.bid, w_local, self.yaw, self.KR * boost, self.DR,
                             self.T_MAX * boost)
        data.xfrc_applied[self.bid, :3] = F * self.harness
        data.xfrc_applied[self.bid, 3:] = tau * self.harness


# ── Jumper controller ────────────────────────────────────────────────────
class JumperCtrl:
    """Scripted hop cycle on the PD-driven legs + a guidance force toward a target.

    Modes: STAND, HOP, REST.  Leg signs follow jumper's probe_gymnast.py
    (knee extension: left legs J2 +, right legs J2 -; thigh down: LM/LR J1 -,
    RM/RR J1 +).  The guidance force is a demo aid; contacts are real physics.
    """

    PERIOD, T_CROUCH, T_PUSH = 0.6, 0.22, 0.12
    FLEX, PUSH, THIGH, ARMS, LAND_FLEX = 0.5, 1.2, 0.6, 0.7, 0.25
    V_MAX, K_DIST, KV = 0.9, 10.0, 40.0
    F_MAX_AIR, F_MAX_GROUND = 12.0, 5.0     # feet friction eats a ground push; steer in flight
    Z_ASSIST = 12.0                         # N during the push: hard floor + kp=10 legs hop only 4 cm
    POUNCE_DIST, POUNCE_GAIN = 0.6, 1.7     # the last hop onto the target is a harder one
    K_ATT, D_ATT, T_ATT_MAX = 1.5, 0.1, 0.8  # keep level in flight / landing, heading toward target
    KNEE = {"LM": 1.0, "RM": -1.0, "LR": 1.0, "RR": -1.0}
    THIGH_DOWN = {"LM": -1.0, "RM": 1.0, "LR": -1.0, "RR": 1.0}

    def __init__(self, model, data):
        self.bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "jp-base_link")
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "jp-floating_base")
        self.dadr = model.jnt_dofadr[jid]
        self.act = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, a)[3:]: a
                    for a in _prefixed(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "jp-")}
        self.mass = float(model.body_subtreemass[self.bid])
        self.mode = "STAND"
        self.t_mode = 0.0
        self.events = []
        self.z_max = 0.0
        self.assist_upright = False     # righting aid while something pushes it (demo aid)

    def set_mode(self, mode, t):
        if mode != self.mode:
            self.events.append({"t": round(t, 3), "mode": mode})
            self.mode, self.t_mode = mode, t

    def pos(self, data):
        return data.xpos[self.bid]

    def step(self, model, data, t, dt, target_xy):
        ctrl = dict(JP_HOME)
        F = np.zeros(3)
        tau = np.zeros(3)
        p = data.xpos[self.bid]
        if self.mode == "RIGHTING" and self.assist_upright:
            yaw = quat_to_yaw(data.xquat[self.bid])
            tau = upright_torque(data, self.bid, data.qvel[self.dadr + 3:self.dadr + 6], yaw,
                                 4.0, 0.2, 2.5)
            F[2] = 6.0
        if self.mode in ("HOP", "FLEE"):
            self.z_max = max(self.z_max, float(p[2]))
            d = np.asarray(target_xy, dtype=float) - p[:2]
            dist = float(np.linalg.norm(d))
            boost = self.POUNCE_GAIN if (self.mode == "HOP" and dist < self.POUNCE_DIST) else 1.0
            c = (t - self.t_mode) % self.PERIOD
            if c < self.T_CROUCH:
                a = min(1.0, c / 0.08)
                for leg, s in self.KNEE.items():
                    ctrl[f"{leg}_J2_joint"] -= s * self.FLEX * a
            elif c < self.T_CROUCH + self.T_PUSH:
                F[2] = self.Z_ASSIST * boost
                for leg, s in self.KNEE.items():
                    ctrl[f"{leg}_J2_joint"] += s * self.PUSH
                for leg, s in self.THIGH_DOWN.items():
                    ctrl[f"{leg}_J1_joint"] += s * self.THIGH
                ctrl["LF_J1_joint"] += self.ARMS
                ctrl["RF_J1_joint"] += self.ARMS
                ctrl["LF_J2_joint"] += 0.5 * self.ARMS
                ctrl["RF_J2_joint"] -= 0.5 * self.ARMS
            else:
                for leg, s in self.KNEE.items():
                    ctrl[f"{leg}_J2_joint"] -= s * self.LAND_FLEX
            v = data.qvel[self.dadr:self.dadr + 3]
            v_des = (d / dist * min(self.V_MAX * boost, self.K_DIST * dist) if dist > 1e-3
                     else np.zeros(2))
            F[:2] = self.KV * (v_des - v[:2])
            f_max = (self.F_MAX_AIR if p[2] > JP_STAND_Z + 0.012 else self.F_MAX_GROUND) * boost
            n = np.linalg.norm(F[:2])
            if n > f_max:
                F[:2] *= f_max / n
            yaw_des = math.atan2(d[1], d[0]) if dist > 0.05 else quat_to_yaw(data.xquat[self.bid])
            tau = upright_torque(data, self.bid, data.qvel[self.dadr + 3:self.dadr + 6], yaw_des,
                                 self.K_ATT, self.D_ATT, self.T_ATT_MAX)
        for name, aid in self.act.items():
            data.ctrl[aid] = ctrl[name]
        data.xfrc_applied[self.bid, :3] = F
        data.xfrc_applied[self.bid, 3:] = tau


def robots_in_contact(model, data, root_a, root_b):
    for i in range(data.ncon):
        ga, gb = map(int, data.contact[i].geom)
        ra = model.body_rootid[model.geom_bodyid[ga]]
        rb = model.body_rootid[model.geom_bodyid[gb]]
        if (ra == root_a and rb == root_b) or (ra == root_b and rb == root_a):
            return True
    return False
