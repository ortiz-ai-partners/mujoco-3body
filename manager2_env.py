"""The manager's world, v2: getting the duck across the course with the crab's help, as a Gym episode
whose actions are the skills in crab_help.py.

ゆうころ (2026-10-27/28): the manager AI ("Island Master") decides what to do next when things do not
go to plan; the robots keep moving with the code already here (official Microduck and Jumper
policies, physics only, no external forces); the bulldozer must not handle the duck, the crab helps.
The overall success condition is that all three cross the built course; BZ and the crab already do,
so this scene is the duck's crossing: it gave up at the foot of the 16-degree ramp, the crab is near.

One episode: the duck at the foot of the up-ramp (seated facing the crab / seated facing elsewhere /
standing / fallen) or, less often, already on the landing with the crab still against its back; the
crab behind it in the lane, beside it, or touching it.  The manager picks a skill, the skill runs
to completion (4-90 simulated seconds), the manager sees the outcome and picks again, until the duck
stands on the floor north of the course (success), the course is damaged (failure) or time runs out.

Training-only liberties: the robots are placed by writing their poses at reset.  Never in a video.
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json
import math
import time
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from crab_help import (ACTIONS, CREST_Y, DECK_N_Y, FACE_SOUTH, LANE_X, OBS_DIM, RESULT_SLOTS, SEAT_Y, SKILLS, STAGES,
                       TOE_Y, Helpers, bubble_line, check_seated_fall, hold_seated, observation, rule_action)
from v6_common import OUT_DIR, course_builder
from v6_phase4_full import ArenaSim
from v6_robots import build_arena
from v7_full import CONTROL_DT, Crab, Duck, official_md_servos
from v7_policies import MD_CONTROL_DT, set_pd_gains

STAGE_XML = OUT_DIR / "v6_stage_built.xml"
BZ_PARK = (3.4, -1.6, math.pi)              # BZ watches from the east, well off the lane; it never moves here
REWARD = {"success": 10.0, "per_second": -0.03, "landing_bonus": 3.0, "fall": -1.0, "wasted": -1.0,
          "wait_idle": -0.5, "timeout": -5.0, "course_damaged": -10.0}
# (10/28 01:40: "wasted" now also covers a skill that ends stalled / slipped - reward v2.1; ppo2_small and
#  baselines_v2 were run under v2.0 without it, their returns differ by that term only)
COURSE_BODIES = ("up_1", "down_1", "block_1", "block_2")
COURSE_TOLERANCE = 0.04                     # m, course-builder's own "Placed slope disturbed" tolerance
SCENARIOS = [("toe_seated_ok", 0.30), ("toe_seated_wrong", 0.20), ("toe_standing", 0.20), ("toe_fallen", 0.10),
             ("deck_seated", 0.15), ("deck_fallen", 0.05)]
CRAB_SPOTS_TOE = [("behind", 0.65), ("beside", 0.25), ("touching", 0.10)]
CRAB_SPOTS_DECK = [("touching", 0.70), ("behind", 0.30)]


def ramp_z(y):
    """Surface height of the up-ramp at world y (0 at the toe, 0.44 at the crest)."""
    return float(np.clip(0.44 * (y - TOE_Y) / (CREST_Y - TOE_Y), 0.0, 0.44))


SLOPE = math.atan2(0.44, CREST_Y - TOE_Y)   # the ramps' incline (16.3 deg)


def quat_yaw_roll(yaw, roll, pitch=0.0):
    """yaw about world z, then pitch about the body's y (negative = nose up), then roll about the body's x."""
    qy = np.array([math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)])
    qp = np.array([math.cos(pitch / 2), 0.0, math.sin(pitch / 2), 0.0])
    qr = np.array([math.cos(roll / 2), math.sin(roll / 2), 0.0, 0.0])
    tmp, out = np.zeros(4), np.zeros(4)
    mujoco.mju_mulQuat(tmp, qy, qp)
    mujoco.mju_mulQuat(out, tmp, qr)
    return out


def pick(rng, table):
    names, probs = zip(*table)
    return str(rng.choice(names, p=np.asarray(probs) / sum(probs)))


class Scene:
    """Three robots in the built stage; the skills come from crab_help; this class owns the physics loop,
    the reset draws and the bookkeeping the manager reads."""

    course_tolerance = COURSE_TOLERANCE

    def __init__(self, dt=0.001):
        _, _, tracks_mod = course_builder()
        self.model, self.data = build_arena(STAGE_XML, md_pose=(LANE_X, SEAT_Y, FACE_SOUTH),
                                            jp_pose=(LANE_X, SEAT_Y - 0.8, math.pi / 2), timestep=dt)
        official_md_servos(self.model)
        self.sim = ArenaSim(self.model, self.data, tracks_mod)
        self.duck = Duck(self.model, self.data)
        self.crab = Crab(self.model, self.data)
        self.h = Helpers(self.model, self.data, self.duck, self.crab)
        J = mujoco.mjtObj.mjOBJ_JOINT
        self.bz_bid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "dozer")
        self.course_bids = np.array([mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, n) for n in COURSE_BODIES])
        self.free = {}
        for j in range(self.model.njnt):
            if self.model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
                name = mujoco.mj_id2name(self.model, J, j) or ""
                key = "bz" if name == "base" else "md" if name.startswith("md-") else "jp" if name.startswith("jp-") else None
                if key:
                    self.free[key] = (int(self.model.jnt_qposadr[j]), int(self.model.jnt_dofadr[j]))
        assert set(self.free) == {"bz", "md", "jp"}, self.free
        self.teleport("bz", BZ_PARK[:2], BZ_PARK[2], z=0.30)
        for _ in range(100):
            mujoco.mj_step(self.model, self.data)
        self.init = (self.data.qpos.copy(), self.data.qvel.copy(), self.data.ctrl.copy(), self.data.act.copy())
        self.dt = dt
        self.substeps = round(CONTROL_DT / dt)
        self.md_every = round(MD_CONTROL_DT / dt)
        self.jp_every = max(1, round(0.005 / dt))
        self.rec = False
        self.bubble_text, self.bubble_sub = "", ""
        self.t = 0.0
        self.sub_k = 0

    # ── recording (demo videos; evaluation runs stay headless) ───────────
    def start_recording(self, path, speed=2.0):
        from v6_common import VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock, Video
        self.renderer = mujoco.Renderer(self.model, height=VIDEO_H, width=VIDEO_W)
        self.vopt = mujoco.MjvOption()
        self.vopt.geomgroup[1] = 0
        self.cap = Captioner()
        self.cam = CameraRig(lookat=[LANE_X, -1.5, 0.2], distance=2.8, azimuth=15, elevation=-14, tau=1.0)
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
        p_md, p_jp = self.h.duck_xyz(), self.h.crab_xyz()
        look = 0.5 * (p_md + p_jp)
        look[2] = 0.2 + 0.5 * max(0.0, p_md[2] - 0.15)
        dist = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
        self.cam.aim(lookat=look, distance=2.6 + 0.5 * dist, azimuth=15, elevation=-14)
        self.renderer.update_scene(self.data, self.cam.step(1.0 / self.fps), self.vopt)
        title = "支配人AI〈アイランドマスター〉 パッカンを渡らせる判断 ― 学習環境 v2（手助けはカニ、物理のみ）"
        line1 = f"支配人：「{self.bubble_text}」" if self.bubble_text else "支配人：（観察中）"
        return self.cap.draw(self.renderer.render(), title, [line1, self.bubble_sub],
                             footer=f"sim {self.t:6.1f} s   x{self.clock.speed:g}")

    # ── low level ────────────────────────────────────────────────────────
    def teleport(self, key, xy, yaw, z=None, roll=0.0, pitch=0.0):
        qadr, dadr = self.free[key]
        if z is None:
            z = float(self.data.qpos[qadr + 2])
        self.data.qpos[qadr:qadr + 3] = (xy[0], xy[1], z)
        self.data.qpos[qadr + 3:qadr + 7] = quat_yaw_roll(yaw, roll, pitch)
        self.data.qvel[dadr:dadr + 6] = 0.0

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
        if check_seated_fall(self.h):
            self.falls += 1
        elif self.duck.mode == "FALLEN" and not self.was_fallen:
            self.falls += 1
        self.was_fallen = self.duck.mode == "FALLEN"
        if self.course_ref is not None:
            moved = np.linalg.norm(self.data.xpos[self.course_bids][:, :2] - self.course_ref, axis=1)
            if float(moved.max()) > self.course_damage:
                self.course_damage = float(moved.max())
                self.course_moved_body = COURSE_BODIES[int(np.argmax(moved))]
        if np.any(np.isnan(self.data.qpos)):
            raise FloatingPointError("NaN in qpos")

    def run(self, seconds):
        for _ in range(int(round(seconds / CONTROL_DT))):
            hold_seated(self.h)
            self.sim.command(0, 0, 0)
            self.tick()

    def run_skill(self, gen):
        """Drive a crab_help skill generator to its result."""
        try:
            while True:
                next(gen)
                self.sim.command(0, 0, 0)
                self.tick()
        except StopIteration as stop:
            return stop.value

    # ── reset ────────────────────────────────────────────────────────────
    def reset(self, rng, hard=None, scenarios=None, crab_spots_toe=None, crab_spots_deck=None):
        """Place the duck and the crab for one of the scenarios (training-only teleports), then let the duck
        take its starting state physically (stand, or stand then sit).  `hard` overrides the random draw
        (scenario, crab, dx, dy, yaw_err_deg, gap, lat).  `scenarios` / `crab_spots_*` replace the default
        draw tables (continued training with more weight on rare starts; evaluation keeps the defaults)."""
        qpos, qvel, ctrl, act = self.init
        self.data.qpos[:] = qpos
        self.data.qvel[:] = qvel
        self.data.ctrl[:] = ctrl
        self.data.act[:] = act
        self.data.time = 0.0
        self.t, self.sub_k = 0.0, 0
        self.falls = 0
        self.was_fallen = False
        self.course_ref, self.course_damage, self.course_moved_body = None, 0.0, ""
        self.pushes = 0
        self.landed = False
        self.last_result, self.last_action = "none", None
        self.decisions = []
        d, c = self.duck, self.crab
        d.vel.reset(); d.sit.reset(); d.pol = d.vel; d.mode = "STAND"; d.t_mode = 0.0
        d.goal = None; d.gaze = None; d.fell_at = None; d.upright_since = None; d.resume = "STAND"; d.events = []
        c.loco.reset(); c.mode = "HOLD"; c.events = []
        set_pd_gains(self.model, c.loco.act_ids, 10.0, 0.5)
        c.loco.hold_home(self.data)
        c.loco.posture[3] = 0.0

        draw = {"scenario": pick(rng, scenarios or SCENARIOS), "dx": float(rng.uniform(-0.06, 0.06)), "dy": float(rng.uniform(-0.06, 0.06)),
                "yaw_err_deg": float(rng.uniform(-10, 10)), "gap": float(rng.uniform(0.55, 1.0)),
                "lat": float(rng.uniform(-0.15, 0.15)), "side": float(rng.choice([-1.0, 1.0])),
                "wrong_yaw_deg": float(rng.uniform(40, 320)), "any_yaw_deg": float(rng.uniform(0, 360)),
                "deck_y": float(rng.choice([rng.uniform(CREST_Y + 0.12, -0.10), rng.uniform(0.16, DECK_N_Y - 0.22)]))}
        # (on the landing, but never seated on the 4 cm seam between its two pieces, y +0.02..+0.06)
        draw["crab"] = pick(rng, (crab_spots_deck or CRAB_SPOTS_DECK) if draw["scenario"].startswith("deck")
                            else (crab_spots_toe or CRAB_SPOTS_TOE))
        if hard:
            draw.update(hard)
        self.draw = draw
        sc = draw["scenario"]
        on_deck = sc.startswith("deck")
        if on_deck:
            duck_xy = np.array([LANE_X + draw["dx"], draw["deck_y"]])
            z_floor = 0.44
        else:
            duck_xy = np.array([LANE_X + draw["dx"], SEAT_Y + draw["dy"]])
            z_floor = 0.0
        if sc == "toe_seated_wrong":
            yaw_d = FACE_SOUTH + math.radians(draw["wrong_yaw_deg"])
        elif sc == "toe_standing":
            yaw_d = math.radians(draw["any_yaw_deg"])
        else:
            yaw_d = FACE_SOUTH + math.radians(draw["yaw_err_deg"])
        fallen = sc.endswith("fallen")
        z_stand = float(self.data.qpos[self.free["md"][0] + 2])            # the standing height from the arena's init
        if fallen:
            self.teleport("md", duck_xy, yaw_d, z=z_floor + 0.10, roll=math.radians(80.0))
        else:
            self.teleport("md", duck_xy, yaw_d, z=z_floor + z_stand + 0.005)
        # the crab
        spot = draw["crab"]
        if spot == "behind":
            crab_xy = np.array([LANE_X + draw["lat"], duck_xy[1] - draw["gap"]])
            yaw_c = math.atan2(*(duck_xy - crab_xy)[::-1])
        elif spot == "beside":
            crab_xy = np.array([LANE_X + 0.9 * draw["side"], duck_xy[1] + 0.5 * draw["lat"]])
            yaw_c = math.atan2(*(duck_xy - crab_xy)[::-1])
        else:                                                                # touching: right against its back
            crab_xy = np.array([LANE_X + 0.5 * draw["lat"], duck_xy[1] - 0.28])
            yaw_c = math.pi / 2
        # on the incline the crab is pitched nose-up to the slope and dropped from 3 cm: a level crab written
        # onto the 16-degree ramp had its front feet 4 cm inside the incline and the contact solver threw both
        # robots a metre (debug 10/28: duck fallen on the far ramp, crab on the floor beside the course)
        on_incline = 0.0 < ramp_z(crab_xy[1]) < 0.44
        self.teleport("jp", crab_xy, yaw_c, z=ramp_z(crab_xy[1]) + 0.115 + (0.03 if on_incline else 0.0),
                      pitch=(-SLOPE * math.cos(yaw_c - math.pi / 2)) if on_incline else 0.0)
        mujoco.mj_forward(self.model, self.data)
        # the crab holds its home pose (PD) until a skill walks it, as in the experiment; standing under the
        # locomotion policy with a zero command for the 4 s of the duck's sit changed its state enough that
        # every push then toppled the duck at the ramp's lip (sweeps 10/28: 0/14 vs the experiment's 2/2)
        c.loco.set_command(0, 0, 0)
        if fallen:
            d.resume, d.fell_at, d.upright_since = "STAND", self.t, None
            d.set_mode("FALLEN", self.t)
            self.run(0.4)
        else:
            self.run(1.0)
            if sc != "toe_standing":
                d.use("sit"); d.set_mode("SIT", self.t); d.sit.twist[:] = (1.0, 0.0, 0.0); d.sit.head[:] = (0.3, 0.2, 0, 0)
                self.run(3.0)
        self.falls = 0                                                       # nothing before the first decision counts
        self.was_fallen = self.duck.mode == "FALLEN"
        self.course_ref = self.data.xpos[self.course_bids][:, :2].copy()
        self.course_damage = 0.0
        self.landed = self.h.stage() in ("deck", "ramp_down", "north")
        self.t0_episode = self.t
        return observation(self.h, self)

    def confirm_up(self, seconds=2.0):
        for _ in range(int(seconds / CONTROL_DT)):
            self.sim.command(0, 0, 0)
            self.tick()
            if not self.h.crossed():
                return False
        return True


class ManagerEnv(gym.Env):
    """Gym wrapper: one step = one skill; reward = crossing, landing milestone, time, falls, waste."""

    metadata = {"render_modes": []}

    def __init__(self, seed=0, max_episode_s=240.0, log_path=None, dt=0.001, scenarios=None, crab_spots_toe=None,
                 crab_spots_deck=None):
        super().__init__()
        self.scene = Scene(dt=dt)
        self.max_episode_s = max_episode_s
        self.log_path = Path(log_path) if log_path else None
        self.draw_tables = dict(scenarios=scenarios, crab_spots_toe=crab_spots_toe, crab_spots_deck=crab_spots_deck)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(ACTIONS))
        self.rng = np.random.default_rng(seed)
        self.episode_id = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.episode_id += 1
        obs = self.scene.reset(self.rng, hard=(options or {}).get("hard"), **self.draw_tables)
        self.wall0 = time.perf_counter()
        return obs, {"draw": self.scene.draw}

    def step(self, action):
        s, h = self.scene, self.scene.h
        action = int(action)
        name = ACTIONS[action]
        bubble = bubble_line(action, s)
        s.bubble_text = bubble
        s.bubble_sub = (f"指示 {name}（{len(s.decisions) + 1} 手目）   直前の結果：{s.last_result}   押し上げ {s.pushes} 回   "
                        f"パッカン：{s.duck.mode}／{h.stage()}")
        t_start = s.t
        falls0 = s.falls
        stage0, mode0 = h.stage(), s.duck.mode
        already_seated = h.seated_for_push() or (s.duck.mode == "SIT" and h.facing_ok() and stage0 == "ramp_up")
        result = s.run_skill(SKILLS[name](h))
        wasted = 0.0
        if name == "SEAT" and already_seated:
            wasted += 1.0
        if name in ("PUSH", "BACK_OFF", "STANDUP", "WALK_ON") and result == "nothing":
            wasted += 1.0
        if result in ("stalled", "slipped"):
            wasted += 1.0                                    # a futile call (e.g. WALK_ON into the ramp): the small PPO
                                                             # run of 10/28 repeated it 24 times at -0.9 each (time only)
        if name == "WAIT" and mode0 != "FALLEN" and stage0 != "north":
            wasted += -REWARD["wait_idle"]
        if name == "PUSH" and result != "nothing":
            s.pushes += 1
        falls = min(s.falls - falls0, 2)
        stage = h.stage()
        landing = 0.0
        if not s.landed and stage in ("deck", "ramp_down", "north"):
            s.landed = True
            landing = REWARD["landing_bonus"]
        damaged = s.course_damage > COURSE_TOLERANCE
        success = (not damaged) and h.crossed() and s.confirm_up(2.0)
        duration = s.t - t_start
        timeout = (s.t - s.t0_episode) >= self.max_episode_s
        reward = REWARD["per_second"] * duration - wasted + REWARD["fall"] * falls + landing
        if damaged:
            reward += REWARD["course_damaged"]
        elif success:
            reward += REWARD["success"]
        elif timeout:
            reward += REWARD["timeout"]
        s.last_result, s.last_action = result, action
        obs = observation(h, s)
        rec = {"episode": self.episode_id, "t": round(t_start, 1), "action": name, "bubble": bubble, "result": result,
               "duration_s": round(duration, 1), "reward": round(reward, 3), "success": bool(success),
               "stage_before": stage0, "stage_after": stage, "duck_before": mode0, "duck_after": s.duck.mode,
               "falls": int(falls), "pushes": s.pushes, "landed": bool(s.landed), "wasted": wasted,
               "push_phase": getattr(h, "push_phase", "") if name == "PUSH" else "",
               "course_damage_m": round(s.course_damage, 3), "course_damaged": bool(damaged),
               "course_moved_body": s.course_moved_body, "draw": s.draw}
        s.decisions.append(rec)
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        terminated = bool(success or damaged)
        truncated = bool(timeout and not terminated)
        info = {"result": result, "bubble": bubble, "success": success, "course_damaged": damaged,
                "course_damage_m": s.course_damage, "landed": s.landed, "wall_s": time.perf_counter() - self.wall0}
        return obs, float(reward), terminated, truncated, info


# ── baseline policies ────────────────────────────────────────────────────────
def rule_policy(obs, scene: Scene):
    return rule_action(scene.h, scene)


def random_policy(obs, scene: Scene, rng):
    return int(rng.integers(len(ACTIONS)))


def run_episodes(env: ManagerEnv, policy, n, seed0=1000, verbose=True, hard=None):
    out = []
    for i in range(n):
        obs, info = env.reset(seed=seed0 + i, options={"hard": hard} if hard else None)
        total, steps, done = 0.0, 0, False
        t_wall = time.perf_counter()
        while not done:
            a = policy(obs, env.scene)
            obs, r, term, trunc, info = env.step(a)
            total += r
            steps += 1
            done = term or trunc
        s = env.scene
        rec = {"seed": seed0 + i, "scenario": s.draw["scenario"], "crab": s.draw["crab"], "return": round(total, 2),
               "steps": steps, "success": bool(info["success"]), "landed": bool(s.landed), "falls": s.falls, "pushes": s.pushes,
               "course_damaged": bool(info.get("course_damaged", False)), "course_damage_m": round(float(s.course_damage), 3),
               "sim_s": round(s.t - s.t0_episode, 1), "wall_s": round(time.perf_counter() - t_wall, 1),
               "actions": [d["action"] for d in s.decisions], "results": [d["result"] for d in s.decisions],
               "stage_end": s.h.stage(), "draw": s.draw}
        out.append(rec)
        if verbose:
            print(json.dumps(rec, ensure_ascii=False), flush=True)
    return out


def summarize(recs):
    succ = [r for r in recs if r["success"]]
    return {"episodes": len(recs), "crossing_rate": round(len(succ) / max(1, len(recs)), 3),
            "landing_rate": round(sum(r["landed"] for r in recs) / max(1, len(recs)), 3),
            "median_time_to_cross_s": round(float(np.median([r["sim_s"] for r in succ])), 1) if succ else None,
            "mean_return": round(float(np.mean([r["return"] for r in recs])), 2),
            "mean_steps": round(float(np.mean([r["steps"] for r in recs])), 2),
            "mean_falls": round(float(np.mean([r["falls"] for r in recs])), 2),
            "mean_pushes": round(float(np.mean([r["pushes"] for r in recs])), 2),
            "course_damaged": sum(r["course_damaged"] for r in recs),
            "mean_wall_s": round(float(np.mean([r["wall_s"] for r in recs])), 1),
            "action_counts": {a: sum(r["actions"].count(a) for r in recs) for a in ACTIONS},
            "by_scenario": {sc: {"n": sum(1 for r in recs if r["scenario"] == sc),
                                 "crossed": sum(1 for r in recs if r["scenario"] == sc and r["success"])}
                            for sc, _ in SCENARIOS}}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="smoke test: a few episodes with the rule / random policy")
    ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--policy", choices=["rule", "random"], default="rule")
    ap.add_argument("--log", type=Path, default=OUT_DIR / "manager2_smoke.jsonl")
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--scenario", choices=[s for s, _ in SCENARIOS], help="force the start scenario")
    ap.add_argument("--crab", choices=["behind", "beside", "touching"], help="force the crab's start spot")
    ap.add_argument("--video", type=Path, help="record the episodes with the manager's speech bubble as caption")
    ap.add_argument("--speed", type=float, default=2.0)
    ap.add_argument("--max-episode-s", type=float, default=240.0)
    args = ap.parse_args()
    hard = {}
    if args.scenario:
        hard["scenario"] = args.scenario
    if args.crab:
        hard["crab"] = args.crab
    env = ManagerEnv(seed=0, max_episode_s=args.max_episode_s, log_path=args.log)
    rng = np.random.default_rng(0)
    pol = rule_policy if args.policy == "rule" else (lambda o, s: random_policy(o, s, rng))
    if args.video:
        env.scene.start_recording(args.video, speed=args.speed)
    recs = run_episodes(env, pol, args.episodes, seed0=args.seed0, hard=hard or None)
    if args.video:
        print("video", env.scene.stop_recording())
    print(json.dumps(summarize(recs), ensure_ascii=False, indent=1))
