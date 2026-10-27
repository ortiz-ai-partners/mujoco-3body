"""The manager's world: the LIFT scene as a Gym episode whose actions are the existing skills.

ゆうころ (2026-10-27): put a manager AI ("Island Master") that decides what to do next when the
fork rescue does not go to plan.  The robots keep moving with the code already here (course-builder
rule control for BZ, the official Microduck and Jumper policies, physics only, no external forces);
the manager only chooses which skill runs next.

One episode: the duck sits at the foot of the ramp with its back to BZ; BZ has arrived a few metres
behind it with some docking error; the crab is nearby, sometimes in BZ's way.  The manager picks a
skill, the skill runs to completion (a macro step of 5-90 simulated seconds), the manager sees the
outcome and picks again, until the duck is on its feet (success) or time runs out.

Training-only liberties: the robots are placed by writing their poses at reset.  Never in a video.

Actions (and the fixed line the manager's speech bubble shows):
  0 WAIT       "ちょっと待とう"                              5 s, everybody holds
  1 DOCK       "BZ、後ろにまわって合わせて" / on a re-dock      drive back to 3 m behind the duck if close,
               "BZ、いったん下がって合わせ直して"              pure-pursuit onto its axis, fine aim at 1.5 m;
                                                           the manager then sees the achieved alignment
  2 LIFT       "BZ、そっと持ち上げて"                          creep in, scoop with both tines, lift gently,
                                                           set down, back off clear
  3 PUSH_SIDE  "別の方法にしよう — BZ、横から起こしてあげて"    take-5 method: at the duck's side, fork at
                                                           6 cm, tip it over, velstand gets it up
  4 STANDUP    "BZ は離れて。パッカン、自分で立てる？"          BZ backs away, the duck stands by itself
                                                           (sitstand flag 0 -> velstand)
  5 CLEAR      "カニさん、道を空けてね"                        the crab walks out of BZ's way

Observation: 32 floats from the simulator (duck/BZ/crab pose and status, BZ's alignment to the
docking line, fork height, progress, last result, last action).  See Scene.observation().

Calibration facts (v7_test_fork.py and the offset sweep of 10/27): both tines go under the seated
duck's hips only with BZ's centreline about 2.5 cm to the duck's left (window well under 1 cm here)
and up to ~6 deg of approach skew; a lift succeeds in a minority of well-docked attempts.  That is
the point: the manager has to learn when the odds are worth another go and when to switch.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from v6_common import OUT_DIR, course_builder, quat_to_yaw
from v6_phase4_full import ArenaSim
from v6_robots import build_arena, robots_in_contact
from v7_full import CONTROL_DT, Crab, Duck, make_navigator, official_md_servos, wrap
from v7_policies import MD_CONTROL_DT, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
DUCK_SEAT = (1.22, -2.10, math.pi)          # where the duck gives up in the story; facing west = back to the east
ACTIONS = ["WAIT", "DOCK", "LIFT", "PUSH_SIDE", "STANDUP", "CLEAR"]
LINES = {
    "WAIT": "ちょっと待とう",
    "DOCK": "BZ、後ろにまわって合わせて",
    "DOCK_RETRY": "BZ、いったん下がって合わせ直して",
    "LIFT": "BZ、そっと持ち上げて",
    "PUSH_SIDE": "別の方法にしよう — BZ、横から起こしてあげて",
    "STANDUP": "BZ は離れて。パッカン、自分で立てる？",
    "CLEAR": "カニさん、道を空けてね",
}
RESULT_SLOTS = ["none", "docked", "lifted", "shoved", "missed", "tipped", "standing"]
OBS_DIM = 16 + 3 + len(RESULT_SLOTS) + len(ACTIONS) + 2
# Reward (per decision).  The job is recovery; the lift is the outcome ゆうころ prefers, so it carries a
# bonus large enough that attempting it pays when the alignment makes success likely and not otherwise.
# The course is the whole point of the scene (ゆうころ: コースを壊さないようにしなきゃ): a slope part or block
# moved by more than course-builder's own 4 cm tolerance ends the episode as a failure.
REWARD = {"success": 10.0, "per_second": -0.03, "lift_bonus": 6.0, "wasted": -1.0, "wait_seated": -0.5,
          "collision": -3.0, "bz_tips_duck": -3.0, "timeout": -5.0, "course_damaged": -10.0}
COURSE_BODIES = ("up_1", "down_1", "block_1", "block_2")
COURSE_TOLERANCE = 0.04                     # m, the same as SlopeAssembly's "Placed slope disturbed"
GOOD_ALIGN = (0.02, math.radians(4.0))      # |e_lat| m, |skew| rad: "docked well enough to try"


def unit(yaw):
    return np.array([math.cos(yaw), math.sin(yaw)])


def left_of(yaw):
    return np.array([-math.sin(yaw), math.cos(yaw)])


class Scene:
    """Three robots in the built stage, the skills, and the bookkeeping the manager reads."""

    def __init__(self, dt=0.001):
        _, _, tracks_mod = course_builder()
        self.model, self.data = build_arena(STAGE_XML, md_pose=DUCK_SEAT, jp_pose=(1.4, -3.3, math.pi / 2), timestep=dt)
        official_md_servos(self.model)
        self.sim = ArenaSim(self.model, self.data, tracks_mod)
        self.duck = Duck(self.model, self.data)
        self.crab = Crab(self.model, self.data)
        J = mujoco.mjtObj.mjOBJ_JOINT
        self.bz_bid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "dozer")
        self.block2_bid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "block_2")
        self.course_bids = np.array([mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, n) for n in COURSE_BODIES])
        self.up1_xy = self.data.xpos[self.course_bids[0]][:2].copy()      # the up-ramp: the rescue happens at its foot
        self.bz_root = int(self.model.body_rootid[self.bz_bid])
        self.md_root = int(self.model.body_rootid[self.duck.bid])
        self.jp_root = int(self.model.body_rootid[self.crab.bid])
        self.lift_qadr = int(self.model.jnt_qposadr[mujoco.mj_name2id(self.model, J, "lift")])
        self.free = {}
        for j in range(self.model.njnt):
            if self.model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
                name = mujoco.mj_id2name(self.model, J, j) or ""
                key = "bz" if name == "base" else "md" if name.startswith("md-") else "jp" if name.startswith("jp-") else None
                if key:
                    self.free[key] = (int(self.model.jnt_qposadr[j]), int(self.model.jnt_dofadr[j]))
        assert set(self.free) == {"bz", "md", "jp"}, self.free
        for _ in range(100):
            mujoco.mj_step(self.model, self.data)
        self.init = (self.data.qpos.copy(), self.data.qvel.copy(), self.data.ctrl.copy(), self.data.act.copy())
        self.dt = dt
        self.aim_left = 0.025          # docking line offset to the duck's left (m); the offset sweep lifted only here
        self.substeps = round(CONTROL_DT / dt)
        self.md_every = round(MD_CONTROL_DT / dt)
        self.jp_every = max(1, round(0.005 / dt))
        self.rec = False
        self.bubble_text, self.bubble_sub = "", ""

    # ── recording (demo videos; evaluation runs stay headless) ───────────
    def start_recording(self, path, speed=2.0):
        from v6_common import VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock, Video
        self.renderer = mujoco.Renderer(self.model, height=VIDEO_H, width=VIDEO_W)
        self.vopt = mujoco.MjvOption()
        self.vopt.geomgroup[1] = 0
        self.cap = Captioner()
        self.cam = CameraRig(lookat=[2.0, -2.0, 0.15], distance=3.4, azimuth=330, elevation=-18, tau=1.0)
        self.cam.snap()
        self.clock = FrameClock(VIDEO_FPS, speed)
        self.fps = VIDEO_FPS
        self.video = Video(Path(path))
        self.rec = True

    def stop_recording(self):
        size = self.video.close()
        self.renderer.close()
        self.rec = False
        return self.video.path, self.video.frames, size

    def _render_frame(self):
        self.sim.tracks.update(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)
        p_md, p_bz = self.duck.pos(self.data), self.data.xpos[self.bz_bid]
        look = 0.5 * (p_md + p_bz)
        look[2] = 0.15
        dist = float(np.linalg.norm(p_md[:2] - p_bz[:2]))
        self.cam.aim(lookat=look, distance=2.4 + 0.45 * dist, azimuth=330, elevation=-18)
        self.renderer.update_scene(self.data, self.cam.step(1.0 / self.fps), self.vopt)
        title = "支配人AI〈アイランドマスター〉 救助の判断 ― 学習環境デモ（スキルは既存コード、物理のみ）"
        line1 = f"支配人：「{self.bubble_text}」" if self.bubble_text else "支配人：（観察中）"
        return self.cap.draw(self.renderer.render(), title, [line1, self.bubble_sub],
                             footer=f"sim {self.t:6.1f} s   x{self.clock.speed:g}")

    # ── low level ────────────────────────────────────────────────────────
    def teleport(self, key, xy, yaw, z=None):
        qadr, dadr = self.free[key]
        if z is None:
            z = float(self.data.qpos[qadr + 2])
        self.data.qpos[qadr:qadr + 3] = (xy[0], xy[1], z)
        self.data.qpos[qadr + 3:qadr + 7] = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
        self.data.qvel[dadr:dadr + 6] = 0.0

    def bz_pose(self):
        p = self.data.xpos[self.bz_bid]
        return p[:2].copy(), quat_to_yaw(self.data.xquat[self.bz_bid])

    def duck_pose(self):
        return self.duck.pos(self.data)[:2].copy(), self.duck.yaw(self.data)

    def tick(self):
        """One control tick (0.02 s): duck + crab policies, physics, event bookkeeping."""
        self.duck.control(self.data, self.t)
        for _ in range(self.substeps):
            if self.sub_k % self.md_every == 0:
                self.duck.step(self.model, self.data)
            if self.sub_k % self.jp_every == 0:
                self.crab.step(self.model, self.data)
            mujoco.mj_step(self.model, self.data)
            self.sub_k += 1
        self.t += CONTROL_DT
        if self.rec and self.clock.due(self.data.time):
            self.video.add(self._render_frame())
        tilt = float(self.duck.tilt(self.data))
        if self.duck.mode == "SIT" and tilt > 60.0:            # tipped while seated: velstand takes over
            self.duck.resume, self.duck.fell_at, self.duck.upright_since = "STAND", self.t, None
            self.duck.use("vel")
            self.duck.set_mode("FALLEN", self.t)
            self.falls += 1
            self.fell_in_skill = True
        if robots_in_contact(self.model, self.data, self.jp_root, self.bz_root):
            self.bz_crab_contact_ticks += 1
        if self.course_ref is not None:
            moved = np.linalg.norm(self.data.xpos[self.course_bids][:, :2] - self.course_ref, axis=1)
            self.course_damage = max(self.course_damage, float(moved.max()))
        if np.any(np.isnan(self.data.qpos)):
            raise FloatingPointError("NaN in qpos")

    def run(self, seconds, bz=(0.0, 0.0, 0.0)):
        for _ in range(int(round(seconds / CONTROL_DT))):
            self.duck_sit_cmd()
            self.sim.command(*bz)
            self.tick()

    def duck_sit_cmd(self):
        if self.duck.mode == "SIT":
            self.duck.sit.twist[:] = (1.0, 0.0, 0.0)

    # ── reset ────────────────────────────────────────────────────────────
    def reset(self, rng, hard=None):
        """Seat the duck facing west with its back to BZ; BZ behind it with a docking error; the crab nearby.

        hard: optional dict to override the random draw (lat, head_err, duck_yaw_err, duck_dxy, crab_in_path, crab_lat).
        """
        qpos, qvel, ctrl, act = self.init
        self.data.qpos[:] = qpos
        self.data.qvel[:] = qvel
        self.data.ctrl[:] = ctrl
        self.data.act[:] = act
        self.data.time = 0.0
        self.t, self.sub_k = 0.0, 0
        self.falls = self.bz_crab_contact_ticks = 0
        self.course_ref, self.course_damage = None, 0.0
        self.fell_in_skill = False
        self.attempts = 0
        self.docked = False
        self.dock_e_lat = self.dock_skew = float("nan")
        self.contact_lat_duck = self.contact_skew = float("nan")
        self.lifted_z = 0.0
        self.last_result, self.last_action = "none", None
        self.decisions = []
        d = self.duck
        d.vel.reset(); d.sit.reset(); d.pol = d.vel; d.mode = "STAND"; d.t_mode = 0.0
        d.goal = None; d.gaze = None; d.fell_at = None; d.upright_since = None; d.resume = "STAND"; d.events = []
        c = self.crab
        c.loco.reset(); c.mode = "HOLD"; c.events = []
        set_pd_gains(self.model, c.loco.act_ids, 10.0, 0.5)
        c.loco.hold_home(self.data)
        self.sim.lift_target = 0.0
        self.data.qpos[self.lift_qadr] = 0.0

        block2 = self.data.xpos[self.block2_bid][:2]
        for _ in range(50):
            draw = {"lat": float(rng.uniform(-0.30, 0.30)), "head_err": float(rng.uniform(-10, 10)),
                    "duck_yaw_err": float(rng.uniform(-10, 10)), "duck_dxy": rng.uniform(-0.05, 0.05, 2).tolist(),
                    "crab_in_path": bool(rng.uniform() < 0.30), "crab_lat": float(rng.uniform(-0.3, 0.3))}
            if hard:
                draw.update(hard)
            yaw_d = DUCK_SEAT[2] + math.radians(draw["duck_yaw_err"])
            duck_xy = np.array(DUCK_SEAT[:2]) + np.asarray(draw["duck_dxy"])
            f, l = unit(yaw_d), left_of(yaw_d)
            bz_xy = duck_xy - 2.6 * f + draw["lat"] * l
            # course-builder's block_2 sits at (4, -3): a BZ written on top of it explodes (debug 10/27).  Redraw.
            if float(np.linalg.norm(bz_xy - block2)) > 1.0 or hard:
                break
        self.draw = draw
        self.teleport("md", duck_xy, yaw_d)
        self.teleport("bz", bz_xy, yaw_d + math.radians(draw["head_err"]), z=0.30)
        if draw["crab_in_path"]:
            crab_xy = duck_xy - 1.4 * f + draw["crab_lat"] * l
        else:
            crab_xy = duck_xy + 1.1 * l                                 # the cheering spot, off the path
        self.teleport("jp", crab_xy, math.atan2(*(duck_xy - crab_xy)[::-1]), z=0.12)
        mujoco.mj_forward(self.model, self.data)
        # the duck: stand a moment (velstand), then sit down (sitstand); the crab stands on its feet
        c.set_mode("WALK", self.t, self.model)
        c.loco.set_command(0, 0, 0)
        self.run(1.0)
        d.use("sit"); d.set_mode("SIT", self.t); d.sit.twist[:] = (1.0, 0.0, 0.0); d.sit.head[:] = (0.3, 0.4, 0, 0)
        self.run(3.0)
        self.falls = self.bz_crab_contact_ticks = 0                      # nothing before the first decision counts
        self.course_ref = self.data.xpos[self.course_bids][:, :2].copy()  # the course as built: must not move from here
        self.course_damage = 0.0
        self.t0_episode = self.t
        return self.observation()

    # ── geometry the skills and the observation share ────────────────────
    def _geometry(self):
        duck_xy, yaw_d = self.duck_pose()
        bz_xy, yaw_bz = self.bz_pose()
        f, l = unit(yaw_d), left_of(yaw_d)
        A = duck_xy + self.aim_left * l                      # the docking line's target point beside the hips
        rel = bz_xy - A
        e_lat = float(f[0] * rel[1] - f[1] * rel[0])          # BZ's offset from the docking line, + = left of travel
        psi = wrap(yaw_bz - yaw_d)                            # BZ's heading against the duck's facing (skew)
        d_aim = A - bz_xy
        err = wrap(math.atan2(d_aim[1], d_aim[0]) - yaw_bz)   # bearing error to the target point
        dist = float(np.linalg.norm(duck_xy - bz_xy))
        return duck_xy, yaw_d, bz_xy, yaw_bz, f, l, A, e_lat, psi, err, dist

    def crab_in_path(self):
        duck_xy, _ = self.duck_pose()
        bz_xy, _ = self.bz_pose()
        c = self.crab.pos(self.data)[:2]
        seg = duck_xy - bz_xy
        L = float(np.linalg.norm(seg))
        if L < 1e-6:
            return False
        u = seg / L
        along = float((c - bz_xy) @ u)
        across = abs(float(u[0] * (c - bz_xy)[1] - u[1] * (c - bz_xy)[0]))
        return -0.3 < along < L + 0.2 and across < 0.55

    # ── skills (macro actions) ───────────────────────────────────────────
    def skill_wait(self, seconds=5.0):
        self.run(seconds)
        return "waited"

    def skill_clear(self, max_s=14.0):
        duck_xy, yaw_d = self.duck_pose()
        spot = duck_xy + 1.1 * left_of(yaw_d)
        if self.crab.mode != "WALK":
            self.crab.set_mode("WALK", self.t, self.model)
        t_end = self.t + max_s
        arrived = False
        while self.t < t_end:
            self.duck_sit_cmd()
            self.sim.command(0, 0, 0)
            dist, _ = self.crab.steer(self.data, spot, 0.5)
            if dist < 0.3:
                self.crab.loco.set_command(0, 0, 0)
                arrived = True
                break
            self.tick()
        for _ in range(int(1.0 / CONTROL_DT)):               # turn to face the duck
            self.duck_sit_cmd()
            self.sim.command(0, 0, 0)
            self.crab.steer(self.data, self.duck_pose()[0], 0.0)
            self.tick()
        self.crab.loco.set_command(0, 0, 0)
        return "cleared" if arrived else "waited"

    def skill_dock(self, max_s=100.0):
        """Reposition 3 m behind the duck if close (Navigator, reverse allowed), pure-pursuit onto the duck's
        axis, fine aim at the hips from 1.5 m.  Leaves BZ stopped; records the alignment it achieved."""
        self.docked = False
        duck_xy, yaw_d, bz_xy, yaw_bz, f, l, A, e_lat, psi, err, dist = self._geometry()
        nav = None
        if dist < 2.4:
            back = A - 3.0 * f
            nav = make_navigator(self.sim, [[float(back[0]), float(back[1])]])
        phase, t0 = ("retreat" if nav is not None else "aim"), self.t
        t_end = self.t + max_s
        while self.t < t_end:
            self.duck_sit_cmd()
            duck_xy, yaw_d, bz_xy, yaw_bz, f, l, A, e_lat, psi, err, dist = self._geometry()
            if phase == "retreat":
                self.sim.command(*nav.action(self.sim))
                if nav.done or self.t - t0 > 45.0:
                    phase, t0 = "aim", self.t
            elif phase == "aim":
                turn = 0.0 if abs(err) <= 0.03 else math.copysign(0.7 if abs(err) > 0.1 else 0.3, err)
                self.sim.command(0.0, turn, -1.0)
                if abs(err) <= 0.03 or self.t - t0 > 20.0:
                    phase, t0 = "dock", self.t
            elif phase == "dock":
                s_bz = float((bz_xy - A) @ f)                                  # station along the axis (negative: behind)
                P = A + (s_bz + 1.2) * f                                       # look-ahead point on the axis
                err_p = wrap(math.atan2(*(P - bz_xy)[::-1]) - yaw_bz)
                self.sim.command(0.15, float(np.clip(1.5 * err_p, -0.45, 0.45)), -1.0)
                if dist < 1.50 or self.t - t0 > 60.0:
                    phase, t0 = "aim2", self.t
            elif phase == "aim2":
                turn = 0.0 if abs(err) <= 0.006 else math.copysign(0.5 if abs(err) > 0.08 else 0.22, err)
                self.sim.command(0.0, turn, -1.0)
                if abs(err) <= 0.006 or self.t - t0 > 25.0:
                    self.sim.command(0, 0, -1.0)
                    break
            self.tick()
        duck_xy, yaw_d, bz_xy, yaw_bz, f, l, A, e_lat, psi, err, dist = self._geometry()
        self.dock_e_lat, self.dock_skew = e_lat, psi
        self.docked = dist < 1.8
        return "docked"

    def _lift_outcome(self, start_xy, lifted):
        duck_xy, _ = self.duck_pose()
        if lifted:
            return "lifted"
        if self.fell_in_skill:
            return "tipped"
        if float(np.linalg.norm(duck_xy - start_xy)) > 0.15:
            return "shoved"
        return "missed"

    def skill_lift(self, max_s=80.0):
        """From the docked pose: creep in holding the aim, scoop, lift gently to 0.30 m, hold, set down, back off."""
        self.fell_in_skill = False
        self.attempts += 1
        self.contact_lat_duck = self.contact_skew = float("nan")
        contact_logged = False
        start_xy, _ = self.duck_pose()
        t_end = self.t + max_s
        phase, t0 = "aim2", self.t
        lifted, lifted_z = False, 0.0
        while self.t < t_end:
            self.duck_sit_cmd()
            duck_xy, yaw_d, bz_xy, yaw_bz, f, l, A, e_lat, psi, err, dist = self._geometry()
            if phase == "aim2":                                                # re-check the aim (cheap when docked)
                turn = 0.0 if abs(err) <= 0.006 else math.copysign(0.5 if abs(err) > 0.08 else 0.22, err)
                self.sim.command(0.0, turn, -1.0)
                if abs(err) <= 0.006 or self.t - t0 > 15.0:
                    phase, t0 = "creep", self.t
            elif phase == "creep":
                self.sim.command(0.10, float(np.clip(2.0 * err, -0.2, 0.2)), -1.0)
                if dist < 1.55 and not contact_logged:                         # tines (1.3 m ahead) are about to touch
                    contact_logged = True
                    self.contact_lat_duck = float(left_of(yaw_bz) @ (duck_xy - bz_xy))   # target: -aim_left
                    self.contact_skew = psi
                if dist < 0.98 or self.t - t0 > 45.0:
                    phase, t0 = "lift", self.t
            elif phase == "lift":
                self.sim.command(0.0, 0.0, 0.6)
                if self.sim.lift_target >= 0.30 - 1e-6 or self.t - t0 > 4.0:
                    phase, t0 = "hold", self.t
            elif phase == "hold":
                self.sim.command(0.0, 0.0, 0.0)
                z = float(self.duck.pos(self.data)[2])
                lifted_z = max(lifted_z, z)
                if z > 0.15:
                    lifted = True
                if self.duck.mode == "SIT":
                    self.duck.sit.head[:] = (0.1, -0.1, 0.7 * math.sin(2 * math.pi * 0.5 * (self.t - t0)), 0.0)
                if self.t - t0 > 4.0:
                    phase, t0 = "lower", self.t
            elif phase == "lower":
                self.sim.command(0.0, 0.0, -0.4)
                if self.sim.lift_target <= 0.0 or self.t - t0 > 6.0:
                    phase, t0 = "back", self.t
            elif phase == "back":
                self.sim.command(-0.15, 0.0, 0.0)
                if dist > 2.0 or self.t - t0 > 25.0:
                    self.sim.command(0, 0, 0)
                    break
            self.tick()
        self.lifted_z = lifted_z
        self.docked = False
        return self._lift_outcome(start_xy, lifted)

    def skill_push_side(self, max_s=130.0):
        """Take 5's ending: come at the seated duck's right side, fork at 6 cm, tip it, back off."""
        self.fell_in_skill = False
        self.attempts += 1
        self.docked = False
        start_xy, yaw_d = self.duck_pose()
        # The duck sits 14 cm from the ramp's toe, so the tines must never point at the ramp when they pass
        # the duck (ゆうころ: コースを壊さないようにしなきゃ; the first try from the south shoved up_1 by 9 cm).
        # Candidates around the duck; keep those whose tine direction is not toward the ramp and whose start
        # is clear of it; prefer the duck's front (a genuinely different method from the lift from behind).
        f, l = unit(yaw_d), left_of(yaw_d)
        to_ramp = self.up1_xy - start_xy
        to_ramp = to_ramp / max(float(np.linalg.norm(to_ramp)), 1e-6)
        candidates = []
        for p in (start_xy + 1.9 * f, start_xy + 1.9 * l, start_xy - 1.9 * l, start_xy - 1.9 * f):
            d = start_xy - p
            d = d / float(np.linalg.norm(d))
            if float(d @ to_ramp) < 0.5 and float(np.linalg.norm(p - self.up1_xy)) > 1.6:
                candidates.append(p)
        approach = candidates[0] if candidates else start_xy + 1.9 * f
        nav = make_navigator(self.sim, [[float(approach[0]), float(approach[1])]])
        t_end = self.t + max_s
        phase, t0 = "navigate", self.t
        lifted = False
        while self.t < t_end:
            self.duck_sit_cmd()
            duck_xy, _ = self.duck_pose()
            bz_xy, yaw_bz = self.bz_pose()
            d = duck_xy - bz_xy
            dist = float(np.linalg.norm(d))
            err = wrap(math.atan2(d[1], d[0]) - yaw_bz)
            if phase == "navigate":
                self.sim.command(*nav.action(self.sim))
                if nav.done or self.t - t0 > 60.0:
                    phase, t0 = "aim", self.t
            elif phase == "aim":
                turn = 0.0 if abs(err) <= 0.03 else math.copysign(0.7 if abs(err) > 0.1 else 0.4, err)
                self.sim.command(0.0, turn, 0.0)
                if abs(err) <= 0.03 or self.t - t0 > 20.0:
                    phase, t0 = "insert", self.t
            elif phase == "insert":
                lift_cmd = 1.0 if self.sim.lift_target < 0.06 else (-1.0 if self.sim.lift_target > 0.075 else 0.0)
                self.sim.command(0.15, float(np.clip(2.0 * err, -0.3, 0.3)), lift_cmd)
                if dist < 0.98 or self.t - t0 > 25.0:
                    phase, t0 = "lift", self.t
            elif phase in ("lift", "hold"):
                self.sim.command(0.0, 0.0, 1.0 if phase == "lift" else 0.0)
                if float(self.duck.pos(self.data)[2]) > 0.15:
                    lifted = True
                if phase == "lift" and (self.sim.lift_target >= 0.49 or self.t - t0 > 3.0):
                    phase, t0 = "hold", self.t
                elif phase == "hold" and self.t - t0 > 2.5:
                    phase, t0 = "lower", self.t
            elif phase == "lower":
                self.sim.command(0.0, 0.0, -1.0)
                if self.sim.lift_target <= 0.0 or self.t - t0 > 3.0:
                    phase, t0 = "back", self.t
            elif phase == "back":
                self.sim.command(-0.25, 0.0, 0.0)
                if self.t - t0 > 2.5:
                    self.sim.command(0, 0, 0)
                    break
            self.tick()
        return self._lift_outcome(start_xy, lifted)

    def skill_standup(self, max_s=30.0):
        """BZ backs away, then the duck stands up by itself (sitstand flag 0, then velstand)."""
        self.docked = False
        t_end = self.t + max_s
        t0 = self.t
        while self.t < t_end:                                 # BZ clears off first
            self.duck_sit_cmd()
            duck_xy, _ = self.duck_pose()
            bz_xy, _ = self.bz_pose()
            if float(np.linalg.norm(duck_xy - bz_xy)) > 2.0 or self.t - t0 > 10.0:
                break
            self.sim.command(-0.25, 0.0, -1.0)
            self.tick()
        self.sim.command(0, 0, 0)
        t0 = self.t
        while self.t < t_end:
            self.sim.command(0, 0, 0)
            if self.duck.mode == "SIT":
                self.duck.sit.twist[:] = 0                    # flag 0: stand up
                self.duck.sit.head[:] = 0
                if self.t - t0 > 3.5:
                    self.duck.use("vel")
                    self.duck.set_mode("STAND", self.t)
            elif self.duck.mode == "STAND" and self.t - t0 > 5.0 and float(self.duck.tilt(self.data)) < 15.0:
                break
            self.tick()
        return "standing" if self.duck_standing() else "fell"

    def duck_standing(self):
        return self.duck.mode == "STAND" and float(self.duck.tilt(self.data)) < 15.0 and float(self.duck.pos(self.data)[2]) > 0.10

    def confirm_standing(self, seconds=3.0):
        for _ in range(int(seconds / CONTROL_DT)):
            self.sim.command(0, 0, 0)
            self.tick()
            if not self.duck_standing():
                return False
        return True

    # ── what the manager sees ────────────────────────────────────────────
    def observation(self):
        duck_xy, yaw_d, bz_xy, yaw_bz, f, l, A, e_lat, psi, err, dist = self._geometry()
        rel = bz_xy - duck_xy
        crab_xy = self.crab.pos(self.data)[:2]
        crel = crab_xy - duck_xy
        mode = self.duck.mode
        since_fall = (self.t - self.duck.fell_at) if (mode == "FALLEN" and self.duck.fell_at is not None) else 0.0
        obs = [
            float(rel @ f) / 3.0, float(rel @ l) / 3.0,                      # BZ in the duck's frame
            math.sin(psi), math.cos(psi),                                      # BZ heading vs the duck's facing
            float(self.sim.lift_target) / 0.5,                                 # fork height
            float(mode == "SIT"), float(mode == "STAND"), float(mode == "FALLEN"),
            float(mode not in ("SIT", "STAND", "FALLEN")),
            float(self.duck.tilt(self.data)) / 90.0, float(self.duck.pos(self.data)[2]) * 5.0,
            min(since_fall, 10.0) / 10.0,
            float(crel @ f) / 3.0, float(crel @ l) / 3.0,                    # crab in the duck's frame
            float(self.crab_in_path()), float(np.linalg.norm(crab_xy - bz_xy)) / 3.0,
            float(np.clip(e_lat / 0.3, -2.0, 2.0)), float(self.docked),      # alignment to the docking line, docked?
            min(self.course_damage, COURSE_TOLERANCE) / COURSE_TOLERANCE,      # how far the course has been nudged
        ]
        res = [0.0] * len(RESULT_SLOTS)
        res[RESULT_SLOTS.index(self.last_result if self.last_result in RESULT_SLOTS else "none")] = 1.0
        act = [0.0] * len(ACTIONS)
        if self.last_action is not None:
            act[self.last_action] = 1.0
        obs += res + act + [min(self.attempts, 3) / 3.0, min(self.t - self.t0_episode, 240.0) / 240.0]
        assert len(obs) == OBS_DIM, len(obs)
        return np.asarray(obs, dtype=np.float32)

    def well_docked(self):
        return self.docked and abs(self.dock_e_lat) < GOOD_ALIGN[0] and abs(self.dock_skew) < GOOD_ALIGN[1]

    def bubble(self, action):
        name = ACTIONS[action]
        if name == "DOCK" and (self.last_action is not None):
            return LINES["DOCK_RETRY"]
        return LINES[name]


class ManagerEnv(gym.Env):
    """Gym wrapper: one step = one skill; reward = recovery, time, waste, collisions, lift bonus."""

    metadata = {"render_modes": []}

    def __init__(self, seed=0, max_episode_s=240.0, log_path=None, dt=0.001):
        super().__init__()
        self.scene = Scene(dt=dt)
        self.max_episode_s = max_episode_s
        self.log_path = Path(log_path) if log_path else None
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(ACTIONS))
        self.rng = np.random.default_rng(seed)
        self.episode_id = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.episode_id += 1
        obs = self.scene.reset(self.rng, hard=(options or {}).get("hard"))
        self.wall0 = time.perf_counter()
        return obs, {"draw": self.scene.draw}

    def step(self, action):
        s = self.scene
        action = int(action)
        name = ACTIONS[action]
        bubble = s.bubble(action)
        s.bubble_text = bubble
        s.bubble_sub = (f"指示 {name}（{len(s.decisions) + 1} 手目）   直前の結果：{s.last_result}   持ち上げ試行 {s.attempts}   "
                        f"パッカン：{s.duck.mode}")
        t_start = s.t
        falls0, contact0 = s.falls, s.bz_crab_contact_ticks
        crab_blocked = s.crab_in_path()
        wasted = 0.0
        if name == "WAIT":
            result = s.skill_wait()
            if s.duck.mode == "SIT":
                wasted += -REWARD["wait_seated"]               # waiting on a seated duck changes nothing
        elif name == "DOCK":
            if s.well_docked():
                wasted += -REWARD["wait_seated"]               # re-docking an already good dock
            result = s.skill_dock()
        elif name == "LIFT":
            if s.last_result == "lifted":
                wasted += -REWARD["wasted"]                    # it was already lifted and set down
            result = s.skill_lift()
        elif name == "PUSH_SIDE":
            result = s.skill_push_side()
        elif name == "STANDUP":
            result = s.skill_standup()
        else:
            if not crab_blocked:
                wasted += -REWARD["wasted"]
            result = s.skill_clear()
        damaged = s.course_damage > COURSE_TOLERANCE
        success = (not damaged) and s.duck_standing() and s.confirm_standing(3.0)
        duration = s.t - t_start
        timeout = (s.t - s.t0_episode) >= self.max_episode_s
        collisions = 1.0 if (s.bz_crab_contact_ticks - contact0) > 5 else 0.0
        bz_tipped_duck = 1.0 if (s.falls - falls0) > 0 and name not in ("LIFT", "PUSH_SIDE") else 0.0
        reward = (REWARD["per_second"] * duration - wasted + REWARD["collision"] * collisions
                  + REWARD["bz_tips_duck"] * bz_tipped_duck)
        if result == "lifted":
            reward += REWARD["lift_bonus"]
        if damaged:
            reward += REWARD["course_damaged"]                             # the course is the point: hard failure
        elif success:
            reward += REWARD["success"]
        elif timeout:
            reward += REWARD["timeout"]
        s.last_result, s.last_action = result, action
        obs = s.observation()
        rec = {"episode": self.episode_id, "t": round(t_start, 1), "action": name, "bubble": bubble, "result": result,
               "duration_s": round(duration, 1), "reward": round(reward, 3), "success": bool(success),
               "attempts": s.attempts, "crab_blocked": bool(crab_blocked), "collision": bool(collisions),
               "duck_mode": s.duck.mode, "lifted_z": round(s.lifted_z, 3),
               "dock_e_lat": round(s.dock_e_lat, 3), "dock_skew": round(s.dock_skew, 3),
               "contact_lat_duck": round(s.contact_lat_duck, 3), "contact_skew": round(s.contact_skew, 3),
               "course_damage_m": round(s.course_damage, 3), "course_damaged": bool(damaged), "draw": s.draw}
        s.decisions.append(rec)
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        terminated = bool(success or damaged)
        truncated = bool(timeout and not terminated)
        info = {"result": result, "bubble": bubble, "success": success, "course_damaged": damaged,
                "course_damage_m": s.course_damage, "wall_s": time.perf_counter() - self.wall0}
        return obs, float(reward), terminated, truncated, info


# ── baseline policies (take the same observation the agent gets) ─────────
def rule_policy(obs, scene: Scene, max_lifts=2, max_redocks=2):
    """Fixed rules: clear the crab if it blocks; dock, re-dock while badly aligned (twice), lift when docked
    well; after two failed lifts (or once lifted) let the duck stand."""
    if scene.duck.mode == "FALLEN":
        return ACTIONS.index("WAIT")
    if scene.crab_in_path():
        return ACTIONS.index("CLEAR")
    if scene.last_result == "lifted" or scene.attempts >= max_lifts:
        return ACTIONS.index("STANDUP")
    if scene.well_docked():
        return ACTIONS.index("LIFT")
    redocks = sum(1 for d in scene.decisions if d["action"] == "DOCK")
    if scene.docked and redocks >= max_redocks + scene.attempts:
        return ACTIONS.index("LIFT")                                   # cannot do better: try anyway
    return ACTIONS.index("DOCK")


def random_policy(obs, scene: Scene, rng):
    return int(rng.integers(len(ACTIONS)))


def run_episodes(env: ManagerEnv, policy, n, seed0=1000, verbose=True):
    """Roll out n episodes with a policy(obs, scene) -> action; returns per-episode records."""
    out = []
    for i in range(n):
        obs, info = env.reset(seed=seed0 + i)
        total, steps, done = 0.0, 0, False
        t_wall = time.perf_counter()
        while not done:
            a = policy(obs, env.scene)
            obs, r, term, trunc, info = env.step(a)
            total += r
            steps += 1
            done = term or trunc
        rec = {"seed": seed0 + i, "return": round(total, 2), "steps": steps, "success": bool(info["success"]),
               "course_damaged": bool(info.get("course_damaged", False)), "course_damage_m": round(float(info.get("course_damage_m", 0.0)), 3),
               "sim_s": round(env.scene.t - env.scene.t0_episode, 1), "wall_s": round(time.perf_counter() - t_wall, 1),
               "actions": [d["action"] for d in env.scene.decisions], "results": [d["result"] for d in env.scene.decisions],
               "draw": env.scene.draw}
        out.append(rec)
        if verbose:
            print(json.dumps(rec, ensure_ascii=False), flush=True)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="smoke test: a few episodes with the rule / random policy")
    ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--policy", choices=["rule", "random"], default="rule")
    ap.add_argument("--log", type=Path, default=OUT_DIR / "manager_smoke.jsonl")
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--video", type=Path, help="record the episodes (x2) with the manager's speech bubble as caption")
    ap.add_argument("--speed", type=float, default=2.0)
    args = ap.parse_args()
    env = ManagerEnv(seed=0, log_path=args.log)
    rng = np.random.default_rng(0)
    pol = rule_policy if args.policy == "rule" else (lambda o, s: random_policy(o, s, rng))
    if args.video:
        env.scene.start_recording(args.video, speed=args.speed)
    recs = run_episodes(env, pol, args.episodes, seed0=args.seed0)
    if args.video:
        print("video", env.scene.stop_recording())
    print(json.dumps({"episodes": len(recs), "success_rate": sum(r["success"] for r in recs) / len(recs),
                      "mean_return": sum(r["return"] for r in recs) / len(recs),
                      "mean_wall_s": sum(r["wall_s"] for r in recs) / len(recs)}, indent=1))
