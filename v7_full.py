"""v7 - the whole story in ONE continuous simulation, physics only.

No external forces anywhere.  Every robot moves through its own actuators:
  BZ  course-builder's SlopeAssembly / Navigator (rule control), fork + wheels.
  MD  official velstand.onnx / alpha_sitstand.onnx (pollen-robotics), XML servos.
  JP  official locomotion.onnx / jump.onnx (jumper bundle), PD kp 10 / 20.

Stages (ゆうころ 10/27 夜の筋書き)
  BUILD      BZ builds the course; MD wanders beyond it; JP waits in the west.
  FOLLOW_IN  BZ crosses; MD walks to the foot of the ramp.
  RAMP       MD tries the 16-degree ramp, backs off, tries again, gives up and sits down.
  CLIMB      JP walks in past the sitting duck, climbs the ramp (pushes through the
             crest at full speed), crosses and comes down behind BZ.  MD watches,
             "ぐわぁぁ？", looks around.
  CALL       MD calls BZ; JP steps out of BZ's turning circle.
  LIFT       BZ drives back around the course with JP trailing it, and JP goes round to the duck's
             south side and cheers it with the official dance policy while BZ works the fork:
               --ending push  (take 5) from the duck's side, fork at 6 cm: tips the seated duck over,
                              velstand gets it back on its feet by itself.
               --ending lift  the duck first turns its back on the ramp and sits again; BZ docks
                              straight behind it (line following, fine aim, creep) and scoops it up
                              with both tines under its hips - a 2 cm window (see HANDOVER.md), so
                              whether it lifts, shoves or misses is decided by the physics of the take.

    <jumper venv python> v7_full.py --test            # no render
    <jumper venv python> v7_full.py --preview DIR     # stills
    <jumper venv python> v7_full.py                   # -> out/3body_arena_v7.mp4 (+ chirps)
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
import wave
from pathlib import Path

import imageio
import mujoco
import numpy as np

from v6_common import (HERE, OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Captioner, CameraRig, FrameClock,
                       Video, course_builder, quat_to_yaw)
from v6_phase4_full import ArenaSim, PHASE_TEXT
from v6_robots import body_tilt_deg, build_arena, robots_in_contact
from v7_policies import MD_CONTROL_DT, JumperDance, JumperJump, JumperLocomotion, MicroduckPolicy, set_pd_gains

CONTROL_DT = 0.02
POLICY_DIR = HERE / "policies" / "microduck"
COURSE_CENTER = np.array([1.5, 0.0, 0.2])
MD_START = (4.0, 0.6, -math.pi / 2)
WANDER_ZONE = (3.0, 5.0, -1.8, 1.8)
WAIT_SPOT = (3.2, -2.6)
DUCK_LANE_X = 1.2                      # the duck's line up the ramp (left half of the deck)
CRAB_LANE_X = 1.72                     # the crab's line (right half; deck edge x=2.0, feet reach +-0.22:
                                       # at 1.78 the right feet sat on the edge and slipped off - test #13)
RAMP_START_Y = -3.0
JP_PARK = (4.6, 1.2, math.pi)          # in the play zone with the duck, out of BZ's work corridor
CRAB_WATCH = (4.5, -2.1)               # where the crab watches the duck's ramp attempts (off the duck's
                                       # path to WAIT_SPOT: test #12 had the duck walk into its legs)
ASIDE_SPOT = (0.5, 2.0)                # the crab steps here before BZ drives back: west of the course's north end.
                                       # BZ leaves east then south, so the crab is never ahead of it (test #13 had
                                       # the crab waiting at (2.6, 1.9), in BZ's lane, and BZ shoved it 1.5 m)
CHEER_TEXT = {"wait": "BZ の後ろで待つ", "aside": "BZ の進路を空ける", "aside_done": "BZ を見る",
              "follow": "BZ について戻る（locomotion）", "detour": "BZ の東側を回り込む", "spot": "パッカンの南側へ",
              "face": "パッカンの方を向く", "dance": "応援ダンス（公式 dance ポリシー）"}
# video speed per stage.  ゆうころ 10/28 昼: the submission rules allow up to 2x (3x would need the organisers' OK), so
# nothing above 2x any more (takes 6-10 ran the construction at 4x); the celebration's dance itself plays at 1x
SPEED = {"BUILD": 2.0, "FOLLOW_IN": 2.0, "RAMP": 2.0, "CLIMB": 2.0, "CALL": 2.0, "LIFT": 2.0, "END": 1.0,
         "RETURN": 2.0, "RESCUE": 2.0, "CELEBRATE": 2.0}
SPEED_DANCE = 1.0

MD_TEXT = {"STAND": "立位", "WALK": "歩行", "BACK": "後ずさり", "FALLEN": "転倒 → 自力で起き上がり中（velstand）",
           "SIT": "お座り（sitstand）", "CALL": "ブルドーザーを呼ぶ", "TURN": "向きを変える（velstand）",
           "WALK_ON": "レーンを北へ歩く（velstand）", "CHEER": "パタパタ（velstand の旋回＋首振り）"}

# ── the goal celebration (ゆうころ 10/28 朝: 「坂を降り始めたらカニも後を追いかけて、ゴールで BZ もアームを上げて、
#    パッカンもパタパタして、カニも腕を上げるダンス」) ──
ARM_SLOTS = slice(0, 10)        # the crab's two front arms in the policies' wire order: LF_J0..J4, RF_J0..J4
# the official dance keeps the claws low for its first 4 s and has both up (0.21 m) from 8 to 13 s (v7_test_cheer.py
# --dance-only); at 12.4 s the dance is frozen - the policy's last joint targets are held - for the final "banzai".
# (Writing that frame's joint angles as plain PD targets did not hold the arms up: without the policy's
#  compensation the claws sagged to 0.07 m, test 2.)
CHEER_DANCE_S = 12.4            # the official dance (its claws go up), then
CHEER_HOLD_S = 3.0              # the pose held with the fork up and the duck flapping

# ── the circle (ゆうころ 10/28 昼: 「みんなで顔を合わせようか、円になって中央を向き、ブルドーザーはアームを上下、アヒルは
#    手がなかったので屈伸しながら首を振る」) ──
# ── the crab cheers the duck's ramp attempts (ゆうころ 10/28 昼: 「カニ、ぱっかんがチャレンジしているとき万歳で踊って応援してほしい」) ──
CHEER_SPOT = (2.4, -2.7)        # south-east of the ramp's foot, 1.4 m from the duck's lane, off BZ's course (BZ is done by then)
CHEER_DANCE_START = 8.0         # where in the dance recording to begin: a claw is up 8-15 s, both 19-24.5 s, one 21-29.5 s,
                                # both again 37.5-41 s (v7_test_cheer.py --dance-only --seconds 236); the attempts last ~32 s

CIRCLE_BZ = (1.55, 3.07)        # BZ's post after its crossing: it cannot go further north (its raised tines reach 1.38 m,
                                # the wall is at y 4.5: v7_test_bz_drive.py), so it turns round on the spot with the fork
                                # up (the tines then pass 0.5 m above the far ramp's foot).  The duck and the crab go to
                                # their places (1.56 m from BZ, outside the tines' 1.38 m sweep) before it turns
CIRCLE_BZ_END = (1.56, 3.42)    # where the turn leaves it: its tracks slip ~0.35 m north while it turns (v7_test_bz_drive.py)
CIRCLE_R = 0.92                 # the circle's radius.  BZ turns round while the duck is still walking on (pre-positioning), so
                                # nobody is under its tines; its fork then pumps between 0.2 and 0.5 m up (never down to the
                                # floor: the lowered tines would reach the far ramp's toe)
CIRCLE_C = (CIRCLE_BZ_END[0], CIRCLE_BZ_END[1] - CIRCLE_R)        # (1.56, 2.50): on the floor north of the far ramp's toe
CIRCLE_MD = (CIRCLE_C[0] - 0.95, CIRCLE_C[1])                      # the duck west of the centre, the crab east: a half circle
CIRCLE_JP = (CIRCLE_C[0] + 0.95, CIRCLE_C[1])                      # with BZ at the top, everyone facing the centre
CIRCLE_VIA = (1.52, 2.32)       # both go north of the ramp's toe first (headless test 2: the duck cutting across the toe's
                                # corner to a spot beside the ramp got stuck on its lip for 40 s)


def cheer_circle_tick(rel, duck, crab, sim, model, data, t):
    """One control tick of the circle celebration (rel = seconds since it began).  BZ pumps its fork up and down; the
    duck squats (alpha_sitstand's sit flag on for 2 s, off for 2.5 s: it has no hands) while shaking its head; the crab
    does the official dance and holds its claws up at the end.  Policy commands and joint targets only.  Returns True
    once the celebration is over (the duck's last squat ends standing)."""
    up = (rel % 2.4) < 1.2
    sim.command(0.0, 0.0, 1.0 if up else (-1.0 if sim.lift_target > 0.22 else 0.0))   # pumps between 0.2 and 0.5
    if duck.mode in ("STAND", "WALK", "TURN"):
        duck.use("sit")
        duck.set_mode("SIT", t)
    if duck.mode == "SIT":
        flag = 1.0 if (rel % 4.5) >= 2.5 else 0.0                              # stand 2.5 s, squat 2 s, ...
        duck.sit.twist[:] = (flag, 0.0, 0.0)
        duck.sit.head[:] = (0.15 + 0.2 * math.sin(2 * math.pi * 2.0 * rel), 0.25,
                            0.6 * math.sin(2 * math.pi * 2.0 * rel + math.pi / 2), 0.0)
    if rel < CHEER_DANCE_S:
        if crab.mode != "DANCE":
            crab.dance_start = 0.0
            crab.set_mode("DANCE", t, model)
    elif crab.mode != "FREEZE":
        crab.set_mode("FREEZE", t, model)
    return rel >= CHEER_DANCE_S + CHEER_HOLD_S


def cheer_tick(rel, duck, crab, sim, model, data, t):
    """One control tick of the goal celebration (rel = seconds since it began).  BZ pumps its fork twice, then raises
    it and keeps it up; the duck "flaps": velstand turns it left and right while its head bobs and rolls; the crab
    does the official dance and then holds both arms up.  Policy commands and joint targets only (no external
    forces).  Returns True once the celebration is over."""
    if rel < 4.0:
        sim.command(0.0, 0.0, 1.0 if (rel % 2.0) < 1.0 else -1.0)           # two pumps
    else:
        sim.command(0.0, 0.0, 1.0 if sim.lift_target < 0.5 else 0.0)        # up, and stays up
    if duck.mode in ("STAND", "WALK", "TURN"):
        duck.set_mode("CHEER", t)
    if duck.mode == "CHEER":
        wz = 1.0 * math.sin(2 * math.pi * 0.5 * rel)                        # a slow left-right twist
        bob = 0.25 * math.sin(2 * math.pi * 2.5 * rel)                       # the head bobs ...
        roll = 0.45 * math.sin(2 * math.pi * 2.5 * rel + math.pi / 2)       # ... and rolls: the flap
        duck.cheer = (np.array([0.0, 0.0, wz], dtype=np.float32), np.array([bob, 0.15, 0.0, roll], dtype=np.float32))
    if rel < CHEER_DANCE_S:
        if crab.mode != "DANCE":
            crab.dance_start = 0.0
            crab.set_mode("DANCE", t, model)
    elif crab.mode != "FREEZE":
        crab.set_mode("FREEZE", t, model)                                   # holds the dance's last targets: claws up
    return rel >= CHEER_DANCE_S + CHEER_HOLD_S
PLAY_TEXT = {"chase": "パッカンに近づく（locomotion）", "hop": "ぴょん！（jump）", "wander": "うろうろ（locomotion）",
             "rest": "ひと休み、パッカンを見る", "worry": "心配して離れて待つ", "to_watch": "見学位置へ",
             "watch": "見学位置へ", "watching": "見学中", "dance": "ダンス（公式 dance ポリシー）"}


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def official_md_servos(model):
    A = mujoco.mjtObj.mjOBJ_ACTUATOR
    for a in range(model.nu):
        if (mujoco.mj_id2name(model, A, a) or "").startswith("md-"):
            model.actuator_gainprm[a, 0] = 0.55
            model.actuator_biasprm[a, 1] = -0.55
            model.actuator_biasprm[a, 2] = 0.0
            model.actuator_forcerange[a] = [-0.96, 0.96]


class Chirps:
    """Synthesised electronic voice for MD, placed on the video timeline."""

    KINDS = {
        "quack": [(950, 820, 0.17, 0.08, 0.5), (0, 0, 0.07, 0, 0), (980, 840, 0.19, 0.08, 0.5)],
        "worried": [(1500, 850, 0.30, 0.03, 0.45), (0, 0, 0.12, 0, 0), (1400, 800, 0.34, 0.03, 0.45)],
        "gwaa": [(520, 1050, 0.55, 0.05, 0.35), (0, 0, 0.18, 0, 0), (600, 1300, 0.40, 0.05, 0.6)],
        "call": [(900, 1500, 0.22, 0.04, 0.8), (0, 0, 0.10, 0, 0), (900, 1500, 0.22, 0.04, 0.8),
                 (0, 0, 0.10, 0, 0), (950, 1700, 0.3, 0.04, 0.9)],
        "happy": [(1300, 1900, 0.12, 0.0, 0.5), (0, 0, 0.05, 0, 0), (1600, 2400, 0.16, 0.02, 0.5)],
        "sigh": [(900, 600, 0.6, 0.02, 0.35)],
        # the crab's voice: dry clicks and a little trill (its "song")
        "clack": [(2300, 2000, 0.05, 0.0, 0.45), (0, 0, 0.04, 0, 0), (2400, 2100, 0.05, 0.0, 0.45),
                  (0, 0, 0.04, 0, 0), (2200, 1900, 0.06, 0.0, 0.45)],
        "trill": [(1700, 2600, 0.14, 0.35, 0.35), (0, 0, 0.03, 0, 0), (1800, 2700, 0.14, 0.35, 0.35),
                  (0, 0, 0.03, 0, 0), (1600, 2900, 0.2, 0.35, 0.4)],
    }

    MASTER_GAIN = 0.45          # ゆうころ: 音は小さめで

    def __init__(self):
        self.events = []

    def add(self, video_t, kind, pitch=1.0):
        self.events.append((float(video_t), kind, float(pitch)))

    @staticmethod
    def _tone(f0, f1, dur, sr, amp, vib):
        n = int(dur * sr)
        tt = np.arange(n) / sr
        f = np.linspace(f0, f1, n) * (1 + vib * np.sin(2 * np.pi * 30 * tt))
        ph = 2 * np.pi * np.cumsum(f) / sr
        env = np.minimum(1.0, np.minimum(tt / 0.015, (dur - tt) / 0.04))
        env = env * np.linspace(0.6, 1.0, n) if f1 > f0 else env
        return amp * env * (np.sin(ph) + 0.25 * np.sin(2 * ph))

    def wav(self, path, length_s, sr=22050):
        out = np.zeros(int((length_s + 1.0) * sr))
        for t0, kind, pitch in self.events:
            cursor = int(t0 * sr)
            for f0, f1, dur, vib, amp in self.KINDS[kind]:
                n = int(dur * sr)
                if f0 > 0 and cursor + n < len(out):
                    out[cursor:cursor + n] += self._tone(f0 * pitch, f1 * pitch, dur, sr, amp, vib)
                cursor += n
        out = np.clip(out * self.MASTER_GAIN, -1, 1)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((out * 32767).astype(np.int16).tobytes())


class Duck:
    """Microduck under its official policies; behaviours are commands only."""

    def __init__(self, model, data):
        self.vel = MicroduckPolicy(model, data, POLICY_DIR / "velstand.onnx")
        self.sit = MicroduckPolicy(model, data, POLICY_DIR / "alpha_sitstand.onnx")
        self.pol = self.vel
        self.bid = self.vel.bid
        self.mode = "STAND"
        self.t_mode = 0.0
        self.goal = None
        self.stop_dist = 0.25
        self.gaze = None
        self.cheer = None                               # (twist, head) while CHEER (set by cheer_tick)
        self.fell_at = None
        self.upright_since = None
        self.resume = "STAND"
        self.events = []
        self.vel.hold_default(data)

    def set_mode(self, mode, t):
        if mode != self.mode:
            self.events.append({"t": round(t, 2), "mode": mode})
            self.mode, self.t_mode = mode, t

    def pos(self, data):
        return data.xpos[self.bid]

    def yaw(self, data):
        return quat_to_yaw(data.xquat[self.bid])

    def tilt(self, data):
        return body_tilt_deg(data, self.bid)

    def use(self, which):
        new = self.vel if which == "vel" else self.sit
        if new is not self.pol:
            new.reset()
            new.last_action[:] = self.pol.last_action
            self.pol = new

    def walk_to(self, xy, t, stop_dist=0.25, vx=0.3):
        self.goal = np.asarray(xy, dtype=float)
        self.stop_dist = stop_dist
        self.walk_vx = vx
        self.set_mode("WALK", t)

    def steer(self, data, target_xy, vx=0.3):
        d = np.asarray(target_xy) - self.pos(data)[:2]
        err = wrap(math.atan2(d[1], d[0]) - self.yaw(data))
        wz = float(np.clip(2.5 * err, -1.5, 1.5))
        self.pol.twist[:] = (vx if abs(err) < 0.6 else 0.0, 0.0, wz)
        return float(np.linalg.norm(d)), err

    def look_at(self, data, xyz, pitch=None):
        d = np.asarray(xyz[:2]) - self.pos(data)[:2]
        e = wrap(math.atan2(d[1], d[0]) - self.yaw(data))
        self.pol.head[2] = float(np.clip(e, -0.8, 0.8))
        if pitch is not None:
            self.pol.head[1] = pitch

    def control(self, data, t):
        """Decide commands for this tick (every MD_CONTROL_DT)."""
        tilt = self.tilt(data)
        if self.mode not in ("FALLEN", "SIT") and tilt > 60.0:
            self.resume = self.mode if self.mode in ("WALK", "STAND") else "STAND"
            self.fell_at = t
            self.upright_since = None
            self.use("vel")
            self.set_mode("FALLEN", t)
        if self.mode == "FALLEN":
            self.pol.twist[:] = 0
            self.pol.head[:] = 0
            if tilt < 15.0 and self.pos(data)[2] > 0.10:
                self.upright_since = t if self.upright_since is None else self.upright_since
                if t - self.upright_since > 0.6:
                    self.set_mode(self.resume, t)
            else:
                self.upright_since = None
            return
        if self.mode == "WALK":
            dist, err = self.steer(data, self.goal, vx=getattr(self, "walk_vx", 0.3))
            if dist < self.stop_dist:
                self.pol.twist[:] = 0
                self.set_mode("STAND", t)
        elif self.mode in ("STAND", "CALL"):
            self.pol.twist[:] = 0
        elif self.mode == "BACK":
            self.pol.twist[:] = (-0.3, 0.0, 0.0)
        elif self.mode == "TURN":
            pass                                        # twist set by the stage logic (turning in place)
        elif self.mode == "CHEER":                      # the goal celebration: twist and head from cheer_tick
            self.pol.twist[:] = self.cheer[0] if self.cheer is not None else 0.0
        if self.mode == "CHEER" and self.cheer is not None:
            self.pol.head[:] = self.cheer[1]
        elif self.mode != "SIT":
            if self.gaze is not None:
                self.look_at(data, self.gaze)
            else:
                self.pol.head[:] = 0

    def step(self, model, data):
        self.pol.step(model, data)


class Crab:
    """Jumper under its official locomotion / jump policies."""

    def __init__(self, model, data):
        self.loco = JumperLocomotion(model, data)
        self.jump = JumperJump(model, data)
        self.dance = JumperDance(model, data)
        self.dance_every = max(1, round(self.dance.control_dt / 0.005))    # 50 Hz inside the 200 Hz step()
        self.dance_k = 0
        self.dance_start = 0.0                                             # where in the recording to begin
        self.bid = self.loco.bid
        self.mode = "HOLD"
        self.t_mode = 0.0
        self.events = []
        self.sweep = 1.0
        self.loco.hold_home(data)

    def set_mode(self, mode, t, model=None):
        if mode != self.mode:
            if mode == "JUMP":
                self.jump.reset(sweep=self.sweep)
                set_pd_gains(model, self.jump.act_ids, self.jump.kp, self.jump.kd)
            elif mode == "DANCE":
                self.dance.reset(t_start=self.dance_start)
                self.dance_k = 0
                set_pd_gains(model, self.dance.act_ids, self.dance.kp, self.dance.kd)
            elif self.mode in ("JUMP", "HOLD", "DANCE", "FREEZE"):
                self.loco.reset()
                set_pd_gains(model, self.loco.act_ids, 10.0, 0.5)
            self.events.append({"t": round(t, 2), "mode": mode})
            self.mode, self.t_mode = mode, t

    def pos(self, data):
        return data.xpos[self.bid]

    def yaw(self, data):
        return quat_to_yaw(data.xquat[self.bid])

    def steer(self, data, target_xy, vx):
        d = np.asarray(target_xy) - self.pos(data)[:2]
        err = wrap(math.atan2(d[1], d[0]) - self.yaw(data))
        self.loco.set_command(vx if abs(err) < 0.4 else 0.0, 0.0, float(np.clip(3.0 * err, -2.0, 2.0)))
        return float(np.linalg.norm(d)), err

    def step(self, model, data):
        """Every 0.005 s of simulated time (200 Hz) once the physics runs at 0.001."""
        if self.mode == "HOLD":
            self.loco.hold_home(data)
        elif self.mode == "JUMP":
            self.jump.step(model, data)
        elif self.mode == "DANCE":
            if self.dance_k % self.dance_every == 0:
                self.dance.step(model, data)
            self.dance_k += 1
        elif self.mode == "FREEZE":
            pass                                        # the last joint targets stay (the celebration's final pose)
        else:
            self.loco.step(model, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--until", default="END")
    ap.add_argument("--max-sim", type=float, default=520.0)
    ap.add_argument("--dt-build", type=float, default=0.005)
    ap.add_argument("--dt-action", type=float, default=0.001)
    ap.add_argument("--tag", default="", help="suffix for the output names, e.g. _take5 (keeps earlier takes)")
    ap.add_argument("--ending", choices=["push", "lift", "crab"], default="crab",
                    help="push: take 5 - BZ comes at the seated duck's side, the fork tips it over, it gets up by itself; "
                         "lift: the duck turns its back and BZ docks behind it to scoop it up (a 2 cm window - see HANDOVER); "
                         "crab (take 6, ゆうころ 10/28: BZ must not handle the duck): the crab comes back and the manager AI "
                         "chooses the skills (crab_help.py) that get the duck across - seat, push, back off, stand, walk")
    ap.add_argument("--manager", choices=["rule", "ppo", "tabq"], default="rule",
                    help="who decides in the rescue: fixed rules, the PPO policy, or the learned Q table")
    ap.add_argument("--run", default="ppo2_small", help="out/manager_runs/<run>/ (ppo_manager.zip for ppo, tabq.json for tabq)")
    ap.add_argument("--rescue-max", type=float, default=240.0, help="simulated seconds the manager gets")
    ap.add_argument("--finale", choices=["circle", "procession", "around"], default="circle",
                    help="circle (ゆうころ 10/28 昼, take 11-): the crab follows the duck down, BZ drives up and turns round, the three "
                         "form a circle facing the centre - BZ pumps its fork, the duck squats and shakes its head, the crab dances; "
                         "procession (take 9/10): the crab follows the duck down and the three cheer where the duck stopped; "
                         "around (take 6/7): the crab backs down the up-ramp and walks round the course to the duck")
    ap.add_argument("--jitter", type=float, default=0.0,
                    help="seconds added to where the crab's cheer dance starts in its recording (CHEER_DANCE_START). The only "
                         "purpose is to change the physics path of a rendered take: the rendered physics is deterministic "
                         "for given code, so a learned manager that fails on one path (take 17: the Q table re-seats "
                         "instead of backing off after a stalled push) can be tried on another. Say which jitter a take used")
    ap.add_argument("--no-prestage", action="store_true",
                    help="switch off the pre-positioning (ゆうころ 10/28 昼): by default an idle robot already walks to where its "
                         "next action starts - the crab to the foot of its lane while the duck tries the ramp again, back round "
                         "the course to the lane behind the seat while the duck is still calling, and BZ to its circle spot "
                         "while the duck walks on across the landing")
    args = ap.parse_args()
    args.prestage = not args.no_prestage

    app, slope_assembly, tracks_mod = course_builder()
    xml = slope_assembly.assembly_xml(app.ROOT / "scene_fork_tracks.xml")
    model, data = build_arena(xml, md_pose=MD_START, jp_pose=JP_PARK, timestep=args.dt_build)
    official_md_servos(model)
    duck, crab = Duck(model, data), Crab(model, data)
    for _ in range(100):
        mujoco.mj_step(model, data)
    data.time = 0.0
    sim = ArenaSim(model, data, tracks_mod)
    pilot = slope_assembly.SlopeAssembly(sim)
    nav = None
    rng = np.random.default_rng(11)
    bz_bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dozer")
    md_root, jp_root, bz_root = (model.body_rootid[duck.bid], model.body_rootid[crab.bid],
                                 model.body_rootid[bz_bid])
    print(f"MuJoCo {mujoco.__version__} | v7 full | dt={model.opt.timestep} nq={model.nq} nu={model.nu}", flush=True)

    render = not args.test
    video = None
    chirps = Chirps()
    if render:
        renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = 0
        cap = Captioner()
        cam = CameraRig(lookat=[-0.5, 0, 0.2], distance=8.5, azimuth=55, elevation=-38, tau=1.5)
        cam.snap()
        clock = FrameClock(VIDEO_FPS, SPEED["BUILD"])
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
        else:
            video = Video(OUT_DIR / f"3body_arena_v7{args.tag}_silent.mp4")

    stage, stage_t0 = "BUILD", 0.0
    events = []
    wander_next, next_quack = 0.0, 3.0
    wait_sent = False
    last_phase = None
    sub_k = 0
    last_shot = -1e9
    duck_prev_mode = duck.mode
    ramp = {"phase": None, "t0": 0.0}
    play = {"phase": "chase", "until": 12.0, "goal": None, "next_cry": 4.0}
    climb = {"phase": "approach", "mark": (0.0, -9.0), "boost_until": -1.0, "crest_said": False, "gone_said": False}
    call_t0 = lift_t0 = None
    lift_phase = None
    cheer = {"phase": "wait"}
    turnback = {"phase": "wait", "t0": 0.0}
    course_ref, course_disturbed = None, {}
    # the crab ending: the manager AI picks the crab_help skills (shared with the learning environment)
    import types
    import crab_help as ch                                   # imported here: crab_help imports this module
    h = ch.Helpers(model, data, duck, crab)
    book = types.SimpleNamespace(last_result="none", last_action=None, pushes=0, nudges=0, t0_episode=0.0, course_damage=0.0,
                                 course_tolerance=0.04)
    if args.manager == "ppo":
        from stable_baselines3 import PPO
        ppo = PPO.load(OUT_DIR / "manager_runs" / args.run / "ppo_manager", device="cpu")
        manager_policy = lambda obs: int(ppo.predict(obs, deterministic=True)[0])
        manager_name = f"PPO 方策（{args.run}）"
    elif args.manager == "tabq":
        from manager2_tabq import TabQ, state_key
        tabq = TabQ.load(OUT_DIR / "manager_runs" / args.run / "tabq.json")
        tabq_rng = np.random.default_rng(1)
        # state_key reads scene.h / .last_result / .duck / .pushes: the story's helpers and book serve the same
        tabq_view = types.SimpleNamespace(h=h, duck=duck, last_result="none", pushes=0)

        def manager_policy(obs):
            tabq_view.last_result, tabq_view.pushes = book.last_result, book.pushes
            return tabq.act(state_key(tabq_view), 0.0, tabq_rng)
        manager_name = f"学習済み Q 表（{args.run}）"
    else:
        manager_policy = lambda obs: ch.rule_action(h, book)
        manager_name = "固定ルール"
    ret = {"route": []}
    mgr = {"gen": None, "n": 0, "name": "", "line": "", "decisions": [], "t0": 0.0, "t_dec": 0.0, "crossed": False}
    cel = {"phase": "start", "route": [], "t_dance": 0.0, "following": False, "mark": (0.0, -9.0), "boost_until": -1.0}
    bzf = {"phase": "idle"}                                  # BZ's move to its circle spot: idle / drive / turn / ready
    RAMP_TEXT = {"try1": "坂に挑む（1 回目）", "back": "いったん後ずさり", "try2": "もう一回挑む（2 回目）",
                 "handover": "やっぱり無理…", "sit": "諦めて座り込む（sitstand）"}

    def video_t():
        return (video.frames if video is not None else 0) / VIDEO_FPS

    def event(t, text):
        events.append({"t": round(t, 2), "video_t": round(video_t(), 2), "event": text})
        print(f"  t={t:7.2f}s  [{stage}] {text}", flush=True)

    def set_stage(t, new):
        nonlocal stage, stage_t0
        stage, stage_t0 = new, t
        event(t, f"stage -> {new}")
        if render:
            clock.speed = SPEED.get(new, 1.0)

    def quack(kind, pitch=1.0):
        chirps.add(video_t(), kind, pitch)

    def cry(who):
        """A random cry: the duck's or the crab's, with a random pitch."""
        if who == "duck":
            quack(str(rng.choice(["quack", "quack", "quack", "happy", "gwaa", "sigh"])), float(rng.uniform(0.85, 1.2)))
        else:
            quack(str(rng.choice(["clack", "clack", "trill"])), float(rng.uniform(0.9, 1.15)))

    def play_goal():
        """A random spot in the play zone at least 1 m from the duck (the crab's wander target)."""
        for _ in range(20):
            g = (rng.uniform(WANDER_ZONE[0], WANDER_ZONE[1]), rng.uniform(WANDER_ZONE[2], WANDER_ZONE[3]))
            if np.linalg.norm(np.asarray(g) - duck.pos(data)[:2]) > 1.0:
                break
        return g

    def crab_go(target, vx, stop=0.3):
        """Walk the crab toward target (locomotion); True once within stop, where it halts."""
        dist, _ = crab.steer(data, target, vx)
        if dist < stop:
            crab.loco.set_command(0, 0, 0)
            return True
        return False

    def crab_follow(t, keep=0.8, vmax=0.45):
        """Procession finale: the crab walks the lane north behind the duck, its speed set by the gap (it stops `keep` m
        behind), and pushes through at 0.8 m/s for 3 s when it stalls on the landing (the seams catch its feet) while
        the duck is well ahead.  (Headless test 2: a "stall" counted while the crab was deliberately slow close behind
        the duck sent it charging at 0.8 m/s into the duck's back at the far ramp's lip; the duck fell.)"""
        q_md, q_jp = duck.pos(data), crab.pos(data)
        gap = float(q_md[1] - q_jp[1])
        if abs(q_md[0] - ch.LANE_X) > 0.4 or q_md[1] > ch.DOWN_TOE_Y + 0.3:
            gap = 2.0                                            # the duck has left the lane: come down freely
        vx = float(np.clip(0.8 * (gap - keep), 0.0, vmax))
        if t < cel["boost_until"]:
            vx = 0.8 if gap > 1.0 else vx                            # never charge at a duck closer than 1 m
        elif vx < 0.2 or q_jp[1] > cel["mark"][1] + 0.03:
            cel["mark"] = (t, float(q_jp[1]))                         # moving, or holding back on purpose: no stall
        elif t - cel["mark"][0] > 2.5 and q_jp[2] > 0.45 and gap > 1.2:
            cel["boost_until"] = t + 3.0
            cel["mark"] = (t, float(q_jp[1]))
            event(t, f"JP stalls on the landing at y={q_jp[1]:+.2f}; full speed 0.8 for 3 s")
        crab.steer(data, (ch.LANE_X, q_jp[1] + 1.0), vx)

    def bz_reposition(t):
        """Circle finale: BZ raises its fork (phase "raise") and turns round on the spot to face the goal ("turn" ->
        "ready"), while the duck is still walking on across the landing (pre-positioning): nobody is near its 1.38 m
        tines then.  It cannot drive north (the wall is 5 cm from its raised tines), so the circle forms around its post."""
        yaw = quat_to_yaw(data.xquat[bz_bid])
        if bzf["phase"] == "raise":
            sim.command(0.0, 0.0, 1.0 if sim.lift_target < 0.5 else 0.0)
            if sim.lift_target >= 0.5:
                bzf["phase"] = "turn"
                event(t, "BZ's fork is up; it turns round on the spot to face the goal")
        elif bzf["phase"] == "turn":
            err = wrap(-math.pi / 2 - yaw)
            if abs(err) < 0.04:
                bzf["phase"] = "ready"
                sim.command(0, 0, 0)
                event(t, "BZ faces south: the circle is complete")
            else:
                sim.command(0.0, math.copysign(1.0 if abs(err) > 0.2 else 0.4, err), 1.0 if sim.lift_target < 0.5 else 0.0)
        else:
            sim.command(0, 0, 0)

    def duck_to_place(t):
        """Circle finale: the duck walks to its place in two legs - north of the ramp's toe first, then west - once BZ has
        turned round (so it never walks under the tines)."""
        leg = cel.get("md_leg", 0)
        if leg == 0 and bzf["phase"] == "ready" and duck.mode == "STAND" and t - stage_t0 > 1.0:
            cel["md_leg"] = 1
            duck.walk_to(CIRCLE_VIA, t, stop_dist=0.2, vx=0.25)
            event(t, "the duck walks to its place in the circle (north of the toe first)")
        elif leg == 1 and duck.mode == "STAND":
            cel["md_leg"] = 2
            duck.walk_to(CIRCLE_MD, t, stop_dist=0.15, vx=0.25)

    def caption():
        p_md, p_jp = duck.pos(data), crab.pos(data)
        if stage == "BUILD":
            return ("v7 | 施工（BZ ルール制御）＋ パッカンと跳跳が戯れる ― 物理のみ・外力なし",
                    [f"BZ: {PHASE_TEXT.get(pilot.phase, pilot.phase)}   {pilot.stage}",
                     f"パッカン: {MD_TEXT.get(duck.mode, duck.mode)}（velstand）   跳跳: {PLAY_TEXT.get(play['phase'], play['phase'])}"])
        if stage == "FOLLOW_IN":
            return ("v7 | BZ が峠を走破 → パッカンが後を追う ― 物理のみ",
                    [f"BZ: {'走破完了' if pilot.done else PHASE_TEXT.get(pilot.phase, pilot.phase)}",
                     f"パッカン: 坂の入口へ  高さ {p_md[2]:.2f} m"])
        if stage == "RAMP":
            jp_line = ("跳跳: 万歳で踊って応援（公式 dance ポリシー）" if crab.mode == "DANCE"
                       else "跳跳: 自分のレーンの足元へ先回り" if climb.get("prestaged") else "跳跳: 応援の位置へ")
            return ("v7 | パッカン、16° の坂に挑む ― 公式 velstand・公式サーボ、物理のまま",
                    [f"パッカン: {RAMP_TEXT.get(ramp['phase'], '')}  y={p_md[1]:+.2f} m（坂の入口 y=-1.86）  傾き {duck.tilt(data):4.0f}°", jp_line])
        if stage == "CLIMB":
            return ("v7 | 跳跳が横から坂を登る ― 公式 locomotion、物理のみ",
                    [f"跳跳: {climb['phase']}  高さ {p_jp[2]:.2f} m（天面 ≈0.54）", f"パッカン: {MD_TEXT.get(duck.mode, duck.mode)}、カニを目で追う"])
        if stage == "CALL" and args.ending == "crab":
            return ("v7 | パッカンが仲間を呼ぶ（固定プログラム）",
                    ["パッカン: ぐわっ！ぐわっ！（渡り切った跳跳の方を向く）", "跳跳: 振り返ってパッカンを見る"])
        if stage == "CALL":
            duck_line = ("パッカン: ぐわっ！ぐわっ！（ブルドーザーの方を向く）" if turnback["phase"] == "wait"
                         else "パッカン: 坂に背を向けて座り直す（ふてくされ）")
            return ("v7 | パッカンがブルドーザーを呼ぶ", [duck_line, f"跳跳: {CHEER_TEXT.get(cheer['phase'], cheer['phase'])}"])
        if stage == "RETURN":
            return ("v7 | 跳跳がコースの東側を回って戻ってくる（固定プログラム）― BZ は触れない",
                    [f"跳跳: locomotion 0.5 m/s  残り経由点 {len(ret['route'])}", f"パッカン: {MD_TEXT.get(duck.mode, duck.mode)}、跳跳を目で追う"])
        if stage == "RESCUE":
            touch = "接触あり" if h.touching() else "接触なし"
            line1 = (f"支配人（{manager_name}）：「{mgr['line']}」  {mgr['n']} 手目 {mgr['name']}" if mgr["gen"] is not None
                     else f"支配人（{manager_name}）：（観察中）  直前の結果 {book.last_result}")
            return ("v7 | 支配人AI〈アイランドマスター〉が次の一手を選ぶ ― 手助けは跳跳、物理のみ",
                    [line1, f"パッカン: {MD_TEXT.get(duck.mode, duck.mode)}  {h.stage()}  傾き {duck.tilt(data):3.0f}°   跳跳: {touch}  押し上げ {book.pushes} 回"])
        if stage == "CELEBRATE" or (stage == "END" and args.ending == "crab" and mgr["crossed"]):
            circle = args.finale == "circle"
            jp_text = {"start": "…", "follow": "パッカンの後について坂を降りる（locomotion）",
                       "gather": "輪の位置へ" if circle else "パッカンの横へ",
                       "face": "中央を向く" if circle else "パッカンの方を向く", "descend": "坂を後ろ向きに降りる", "around": "回り込んでパッカンのそばへ",
                       "dance": ("腕を上げて応援ダンス（公式 dance ポリシー）→ 両腕を上げて万歳" if args.finale in ("procession", "circle")
                                 else "応援ダンス（公式 dance ポリシー）")}
            title = ("v7 | 3 体ともコースを渡った！ ゴールで輪になって万歳（固定プログラム）" if circle
                     else "v7 | 3 体ともコースを渡った！ ゴールで三人そろって万歳（固定プログラム）" if args.finale == "procession"
                     else "v7 | 3 体ともコースを渡った！ 跳跳の応援ダンス、BZ はフォークで万歳（固定プログラム）")
            md_text = ("屈伸しながら首を振る（sitstand）" if circle and cel["phase"] == "dance" and duck.mode == "SIT"
                       else "輪の位置へ歩く" if circle and duck.mode == "WALK" else "中央を向く（velstand）" if duck.mode == "TURN"
                       else MD_TEXT.get(duck.mode, duck.mode))
            bz_text = (("フォークを上げ下げ" if circle else "フォーク万歳") if cel["phase"] == "dance"
                       else {"raise": "フォークを上げる", "turn": "その場で向きを変える",
                             "ready": "みんなの方を向いて待つ"}.get(bzf["phase"], "見守る"))
            return (title,
                    [f"跳跳: {jp_text.get(cel['phase'], cel['phase'])}",
                     f"パッカン: {md_text}  北側の床 y={p_md[1]:+.2f}   BZ: {bz_text}"])
        return (("v7 | BZ が後ろからフォークで持ち上げる、跳跳は応援ダンス ― 物理のみ" if args.ending == "lift"
                 else "v7 | BZ が戻ってきてフォークで持ち上げを試みる、跳跳は応援ダンス ― 物理のみ"),
                [f"BZ: {lift_phase or 'navigating'}   跳跳: {CHEER_TEXT.get(cheer['phase'], cheer['phase'])}",
                 f"パッカン: {MD_TEXT.get(duck.mode, duck.mode)}  高さ {p_md[2]:.3f} m"])

    def render_frame():
        sim.tracks.update(model, data)
        mujoco.mj_forward(model, data)
        p_md, p_jp, p_bz = duck.pos(data), crab.pos(data), data.xpos[bz_bid]
        if stage == "BUILD":
            spread = float(np.linalg.norm(p_bz[:2] - COURSE_CENTER[:2]))
            look = 0.5 * p_bz + 0.5 * COURSE_CENTER
            look[2] = 0.2
            u = min(1.0, data.time / 200.0)
            cam.aim(lookat=look, distance=6.0 + 0.6 * spread, azimuth=55 + 85 * u * u * (3 - 2 * u), elevation=-38)
        elif stage == "FOLLOW_IN":
            look = 0.5 * p_md + 0.5 * p_bz
            look[2] = 0.2
            cam.aim(lookat=look, distance=3.0 + 0.5 * float(np.linalg.norm(p_md[:2] - p_bz[:2])), azimuth=120, elevation=-20)
        elif stage == "RAMP":
            look = 0.6 * p_md + 0.4 * p_jp                                  # the duck's attempt with the cheering crab behind
            look[2] = 0.15
            cam.aim(lookat=look, distance=2.0 + 0.4 * float(np.linalg.norm(p_md[:2] - p_jp[:2])), azimuth=15, elevation=-10)
        elif stage == "CLIMB":
            if climb["phase"] in ("approach", "pass"):
                look = 0.5 * p_md + 0.5 * p_jp
                look[2] = 0.15
                cam.aim(lookat=look, distance=2.2, azimuth=15, elevation=-10)
            else:
                cam.aim(lookat=[p_jp[0], p_jp[1], p_jp[2]], distance=2.4, azimuth=15, elevation=-12)
        elif stage == "CALL":
            cam.aim(lookat=[p_md[0], p_md[1], 0.10], distance=1.1, azimuth=135, elevation=-10)
        elif stage == "RETURN":
            look = 0.5 * p_md + 0.5 * p_jp
            look[2] = 0.2
            cam.aim(lookat=look, distance=3.2 + 0.5 * float(np.linalg.norm(p_md[:2] - p_jp[:2])), azimuth=100, elevation=-24)
        elif stage == "RESCUE":
            look = 0.5 * p_md + 0.5 * p_jp                                  # the crab-push experiment's framing
            look[2] = 0.2 + 0.5 * max(0.0, p_md[2] - 0.15)
            cam.aim(lookat=look, distance=2.6 + 0.5 * float(np.linalg.norm(p_md[:2] - p_jp[:2])), azimuth=15, elevation=-14)
        elif stage == "CELEBRATE" and args.finale == "circle" and cel["phase"] in ("gather", "face", "dance"):
            # from the south, looking north: BZ at the far side facing the camera, the duck on the left, the crab on the
            # right, both in profile facing the centre (take 14's view from the east put the duck far behind the fork)
            cam.aim(lookat=[(p_bz[0] + p_md[0] + p_jp[0]) / 3, (p_bz[1] + p_md[1] + p_jp[1]) / 3, 0.25], distance=3.6, azimuth=92, elevation=-20)
        elif stage == "CELEBRATE" and args.finale in ("procession", "circle") and cel["following"]:
            pts = [p_md, p_jp] if cel["phase"] == "follow" else [p_md, p_jp, p_bz]   # the procession, then the three
            look = np.mean(pts, axis=0)
            look[2] = 0.25
            spread = max(float(np.linalg.norm(a[:2] - b[:2])) for a in pts for b in pts)
            cam.aim(lookat=look, distance=2.4 + 0.6 * spread, azimuth=150, elevation=-18)
        elif stage == "CELEBRATE":
            look = 0.6 * p_md + 0.4 * p_bz
            look[2] = 0.2
            cam.aim(lookat=look, distance=3.4, azimuth=150, elevation=-18)
        else:
            look = 0.5 * p_bz + 0.5 * p_md
            look[2] = 0.15
            if args.ending == "lift":
                # from the west-north-west: the duck faces west once it has turned its back on the ramp, so its
                # face is toward the camera, BZ comes up behind it, the crab dances on the right
                cam.aim(lookat=look, distance=2.6 if lift_phase in ("dock", "aim2", "creep", "lift", "hold", "lower", "back", "wait") else 3.4,
                        azimuth=330, elevation=-16)
            else:                                                       # take 5's shot, from the south-east
                cam.aim(lookat=look, distance=2.6 if lift_phase in ("insert", "lift", "hold", "lower", "back", "wait") else 3.4,
                        azimuth=135, elevation=-18)
        renderer.update_scene(data, cam.step(1.0 / VIDEO_FPS), opt)
        title, lines = caption()
        return cap.draw(renderer.render(), title, lines, footer=f"sim {data.time:6.1f} s   x{clock.speed:g}")

    t_wall = time.perf_counter()
    k = 0
    while stage != "END" and data.time < args.max_sim:
        t = k * CONTROL_DT
        k += 1
        dt = model.opt.timestep
        substeps = round(CONTROL_DT / dt)
        p_md, p_jp, p_bz = duck.pos(data).copy(), crab.pos(data).copy(), data.xpos[bz_bid].copy()

        # ── BZ ────────────────────────────────────────────────────────
        if stage in ("BUILD", "FOLLOW_IN", "RAMP", "CLIMB") and not pilot.done:
            sim.command(*pilot.action(sim))
            if pilot.phase != last_phase:
                last_phase = pilot.phase
                event(t, f"BZ {pilot.phase}")
                if pilot.phase == "TO_START":
                    # course-builder's own return route turns at (-1, -3.2): with the fork raised the tips
                    # reach 1.38 m ahead, 8 cm short of the scene's south wall (y=-4.5).  Test #12 touched
                    # it (fork_right <-> wall at y=-4.50) and the empty-transfer check aborted the build.
                    # Same route and settings, corner 20 cm further from the wall.
                    from navigation import Navigator
                    pilot.pilot = Navigator(sim, [[-1, .75], [-1, -3.0], [pilot.target_x, -3.0]],
                                            fast_empty=pilot.fast_empty)
                    event(t, "TO_START route: corner at y=-3.0 (course-builder default -3.2) for fork clearance")
            if pilot.done:
                event(t, f"construction done: success={pilot.success} ({pilot.reason})")
                course_ref = {n: data.xpos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)][:2].copy()
                              for n in ("up_1", "down_1", "block_1", "block_2")}     # the course as built
                if not pilot.success:                         # diagnostic: what did BZ touch?
                    G = mujoco.mjtObj.mjOBJ_GEOM
                    for i in range(data.ncon):
                        c = data.contact[i]
                        names = [mujoco.mj_id2name(model, G, int(g)) or f"geom{int(g)}" for g in c.geom]
                        roots = [int(model.body_rootid[model.geom_bodyid[int(g)]]) for g in c.geom]
                        if bz_root in roots and "floor" not in names:
                            event(t, f"  contact {names[0]} <-> {names[1]} at ({c.pos[0]:+.2f},{c.pos[1]:+.2f},{c.pos[2]:.2f})")
                model.opt.timestep = args.dt_action
                event(t, f"physics step -> {args.dt_action}")
        elif stage not in ("LIFT", "CELEBRATE"):
            sim.command(0, 0, 0)

        # ── stages ────────────────────────────────────────────────────
        if stage == "BUILD":
            sep = float(np.linalg.norm(p_md[:2] - p_jp[:2]))
            # the duck: wander, sometimes toward the crab, and watch it when it is close
            if duck.mode == "STAND" and t >= wander_next and not wait_sent:
                if rng.uniform() < 0.4:
                    duck.walk_to(p_jp[:2], t, stop_dist=0.75)        # go and see the crab, not into its legs
                else:
                    duck.walk_to((rng.uniform(WANDER_ZONE[0], WANDER_ZONE[1]),
                                  rng.uniform(WANDER_ZONE[2], WANDER_ZONE[3])), t, stop_dist=0.2)
                wander_next = 1e9
            if duck.mode == "STAND" and wander_next == 1e9 and not wait_sent:
                wander_next = t + rng.uniform(1.0, 3.0)
            if duck.mode == "WALK" and sep < 0.55 and not wait_sent:    # too close: stop and look, don't bump
                duck.set_mode("STAND", t)
                wander_next = t + rng.uniform(1.0, 2.0)
            if not wait_sent:
                duck.gaze = p_jp[:2] if sep < 1.3 else None
            # the crab: come up to the duck, hop, wander off, repeat (locomotion + jump policies).
            # It never touches the duck: it hops from 0.95 m, yields inside 0.6 m while wandering,
            # and backs away to wait whenever the duck is down - a crab beside a fallen duck blocks
            # velstand's get-up (test #11: 27 s on the ground with the crab hopping next to it).
            if not wait_sent:
                if crab.mode == "HOLD":
                    crab.set_mode("WALK", t, model)
                    play.update(phase="chase", until=t + 12.0)
                if duck.mode == "FALLEN" and play["phase"] not in ("hop", "worry"):
                    play.update(phase="worry")
                    cry("crab")
                if play["phase"] == "chase":
                    dist, _ = crab.steer(data, p_md[:2], 0.4)
                    if dist < 0.95 or t > play["until"]:
                        crab.sweep = 0.0
                        crab.set_mode("JUMP", t, model)
                        play.update(phase="hop")
                        cry("crab")
                elif play["phase"] == "hop":
                    if crab.jump.finished():
                        crab.set_mode("WALK", t, model)
                        if duck.mode == "FALLEN":
                            play.update(phase="worry")
                        else:
                            play.update(phase="wander", goal=play_goal(), until=t + 10.0)
                elif play["phase"] == "wander":
                    dist, _ = crab.steer(data, play["goal"], 0.4)
                    if sep < 0.6:
                        crab.loco.set_command(0, 0, 0)       # let the duck pass
                    if dist < 0.3 or t > play["until"]:
                        crab.loco.set_command(0, 0, 0)
                        play.update(phase="rest", until=t + rng.uniform(1.0, 2.5))
                elif play["phase"] == "rest":
                    crab.steer(data, p_md[:2], 0.0)          # face the duck while resting
                    if t > play["until"]:
                        play.update(phase="chase", until=t + 12.0)
                elif play["phase"] == "worry":
                    if sep < 1.1:                            # give the duck room to get up
                        away = p_jp[:2] + (p_jp[:2] - p_md[:2]) / max(sep, 1e-6)
                        crab.steer(data, away, 0.3)
                    else:
                        crab.steer(data, p_md[:2], 0.0)      # wait at a distance, facing the duck
                    if duck.mode != "FALLEN":
                        play.update(phase="rest", until=t + 1.5)
            if t >= next_quack:
                cry("duck")
                next_quack = t + rng.uniform(5.0, 12.0)
            if t >= play["next_cry"]:
                cry("crab")
                play["next_cry"] = t + rng.uniform(7.0, 16.0)
            if pilot.phase == "TO_START" and not wait_sent:
                wait_sent = True
                duck.walk_to(WAIT_SPOT, t, stop_dist=0.25)
                play.update(phase="to_watch")
                event(t, "MD heads to the waiting spot by the course start; JP to its watch spot")
            if wait_sent:
                if play["phase"] == "to_watch":                 # let a hop finish before walking off
                    if crab.mode != "JUMP" or crab.jump.finished():
                        crab.set_mode("WALK", t, model)
                        play.update(phase="watch")
                elif play["phase"] == "watch":
                    dist, _ = crab.steer(data, CRAB_WATCH, 0.4)
                    if dist < 0.3:
                        crab.loco.set_command(0, 0, 0)
                        play.update(phase="watching")
                else:
                    crab.steer(data, p_md[:2], 0.0)
                if duck.mode == "STAND":
                    duck.gaze = p_bz[:2]
            if pilot.phase == "CROSS":
                set_stage(t, "FOLLOW_IN")
                duck.gaze = None
                duck.walk_to((DUCK_LANE_X, RAMP_START_Y), t, stop_dist=0.25)
                quack("quack")
        elif stage == "FOLLOW_IN":
            # the crab comes over from its watch spot to cheer at the ramp's foot (pre-positioning while BZ crosses) -
            # only once the duck has passed on its way to the ramp (take 13: their paths crossed, the duck fell twice)
            if crab.mode != "WALK":
                crab.set_mode("WALK", t, model)
            if p_md[0] < 2.2 or ramp.get("crab_coming"):
                ramp["crab_coming"] = True
                if crab_go(CHEER_SPOT, 0.5, stop=0.3):
                    crab.steer(data, p_md[:2], 0.0)
            else:
                crab.steer(data, p_md[:2], 0.0)
            if duck.mode == "STAND":
                set_stage(t, "RAMP")
                ramp.update(phase="try1", t0=t)
                duck.walk_to((DUCK_LANE_X, 3.0), t, stop_dist=0.3)
                event(t, "MD: " + RAMP_TEXT["try1"])
                next_quack = t + 1.0
        elif stage == "RAMP":
            rel = t - ramp["t0"]
            ph = ramp["phase"]
            if ph in ("try1", "back", "try2"):
                # the crab cheers the attempts on: the official dance from its claws-up stretch, facing the duck
                if not ramp.get("cheer"):
                    if crab.mode != "WALK":
                        crab.set_mode("WALK", t, model)
                    if crab_go(CHEER_SPOT, 0.5, stop=0.3):
                        _, err = crab.steer(data, p_md[:2], 0.0)
                        if abs(err) < 0.3:
                            ramp["cheer"] = True
                            crab.dance_start = CHEER_DANCE_START + args.jitter
                            crab.set_mode("DANCE", t, model)
                            cry("crab")
                            event(t, "JP cheers the duck on with its dance, claws up (official dance policy)")
            elif args.prestage:
                # pre-positioning (ゆうころ 10/28 昼): once the duck gives up, the crab walks to the foot of its lane and
                # faces north, so the climb starts the moment the duck has sat down
                if not climb.get("prestaged"):
                    climb["prestaged"] = True
                    if crab.mode != "WALK":
                        crab.set_mode("WALK", t, model)
                    event(t, "JP pre-positions at the foot of its lane while the duck sits down")
                if crab_go((CRAB_LANE_X, -3.5), 0.5, stop=0.3):
                    crab.steer(data, (CRAB_LANE_X, -2.5), 0.0)   # face north, ready to go
            elif crab.mode != "DANCE":
                crab.steer(data, p_md[:2], 0.0)             # the crab watches from its spot
            if ph == "try1":
                if duck.mode == "WALK":
                    duck.goal = np.array([DUCK_LANE_X, min(3.0, p_md[1] + 0.8)])
                elif duck.mode == "STAND":
                    duck.walk_to((DUCK_LANE_X, 3.0), t, stop_dist=0.3)
                if t >= next_quack:
                    quack("quack")
                    next_quack = t + rng.uniform(3.0, 5.0)
                if rel > 14.0:
                    ramp.update(phase="back", t0=t)
                    duck.set_mode("BACK", t)
                    event(t, "MD: " + RAMP_TEXT["back"] + f" (reached y={p_md[1]:+.2f}, ramp toe -1.86)")
                    quack("worried")
            elif ph == "back":
                if rel > 2.5:
                    ramp.update(phase="try2", t0=t)
                    duck.walk_to((DUCK_LANE_X, 3.0), t, stop_dist=0.3)
                    event(t, "MD: " + RAMP_TEXT["try2"])
                    quack("quack")
            elif ph == "try2":
                if duck.mode == "WALK":
                    duck.goal = np.array([DUCK_LANE_X, min(3.0, p_md[1] + 0.8)])
                elif duck.mode == "STAND":
                    duck.walk_to((DUCK_LANE_X, 3.0), t, stop_dist=0.3)
                if rel > 11.0:
                    ramp.update(phase="handover", t0=t)
                    duck.use("sit")
                    duck.set_mode("SIT", t)
                    duck.sit.twist[:] = 0
                    duck.sit.head[:] = (0.3, 0.4, 0, 0)
                    event(t, "MD: " + RAMP_TEXT["handover"] + f" (reached y={p_md[1]:+.2f})")
                    quack("sigh")
            elif ph == "handover":
                if rel > 0.6:
                    ramp.update(phase="sit", t0=t)
                    duck.sit.twist[:] = (1.0, 0.0, 0.0)
                    duck.sit.head[:] = (0.3, 0.5, 0, 0)
                    event(t, "MD: " + RAMP_TEXT["sit"])
            elif ph == "sit":
                duck.sit.twist[:] = (1.0, 0.0, 0.0)
                if 1.5 <= rel < 3.5:                      # 2 s of head shaking with the rising cry
                    if "shake" not in ramp:
                        ramp["shake"] = True
                        quack("gwaa")
                        event(t, "MD: 首を振りながら「ぐわぁぁ？」")
                    duck.sit.head[:] = (0.1, 0.2, 0.6 * math.sin(2 * math.pi * 2.0 * (rel - 1.5)), 0.0)
                elif rel >= 3.5:
                    duck.sit.head[:] = (0.3, 0.5, 0, 0)
                if rel > 4.2:
                    set_stage(t, "CLIMB")
                    climb.update(phase="approach", mark=(t, float(p_jp[1])))
                    crab.set_mode("WALK", t, model)
                    cry("crab")
                    event(t, "JP sets off from the foot of its lane" if climb.get("prestaged") else "JP leaves its watch spot for the foot of the ramp")
        elif stage == "CLIMB":
            duck.sit.twist[:] = (1.0, 0.0, 0.0)
            ph = climb["phase"]
            if ph == "approach":
                if climb.get("route"):                                      # after a slip: round the course's east side first
                    if crab_go(climb["route"][0], 0.5, stop=0.35):
                        climb["route"].pop(0)
                    dist = 9.0
                else:
                    dist, err = crab.steer(data, (CRAB_LANE_X, -3.5), 0.5)  # 1.6 m south of the toe: room to line up
                duck.look_at(data, p_jp, pitch=0.3)
                if dist < 0.3:
                    climb["phase"] = "pass"
                    quack("worried")
                    event(t, "JP passes beside the sitting duck and starts up the ramp")
            elif ph in ("pass", "climb", "boost"):
                target_vx = 0.8 if (ph == "boost" and t < climb["boost_until"]) else 0.5
                # lane keeping: the right half (x 1.72) past the sitting duck and up the ramp, then the course's centre
                # (x 1.50) once over the crest - takes 11/12 (10/28 noon) drifted to x 1.90 on the landing after the jump
                # and slipped off its east edge (feet reach 0.22 m, edge at 2.0), then lay wedged against the deck's side
                lane_x = CRAB_LANE_X if p_jp[1] < -0.40 else 1.50
                crab.steer(data, (lane_x, p_jp[1] + 0.6), target_vx)        # aim 0.6 m ahead on the lane
                if p_jp[1] > climb["mark"][1] + 0.03:
                    climb["mark"] = (t, float(p_jp[1]))
                if ph == "pass" and p_jp[1] > -1.6:
                    climb["phase"] = "climb"
                if (ph != "pass" and p_jp[2] < 0.16 and -1.3 < p_jp[1] < 0.5 and abs(p_jp[0] - CRAB_LANE_X) > 0.2
                        and climb.get("retries", 0) < 2):
                    # at floor height beside the deck (which is >= 0.26 m high there) = slipped off its side
                    # (test #13): back to the foot and try again.  Not the far ramp's bottom (y > 0.5, test #14).
                    climb["retries"] = climb.get("retries", 0) + 1
                    climb["phase"] = "approach"
                    climb["mark"] = (t, -9.0)
                    # away from the deck's side first (east), then south round the course, then the foot of the lane
                    # (take 11: the straight way back from (2.33, -0.10) pressed it against the deck's side for 60 s)
                    climb["route"] = [(2.9, float(p_jp[1]) - 0.3), (2.7, -3.3)]
                    quack("worried")
                    event(t, f"JP slipped off the ramp's side at y={p_jp[1]:+.2f}; round the east side back to the foot (retry {climb['retries']})")
                if p_jp[2] > 0.5 and not climb["crest_said"]:
                    climb["crest_said"] = True
                    quack("gwaa")
                    event(t, f"JP on the crest (z={p_jp[2]:.2f}); duck: ぐわぁぁ？")
                if ph != "boost" and t - climb["mark"][0] > 2.5 and p_jp[1] > -1.5:
                    heading_err = wrap(math.pi / 2 - crab.yaw(data))
                    if p_jp[2] > 0.38 and climb.get("jumps", 0) == 0 and abs(heading_err) < 0.15:
                        climb["jumps"] = 1                                # the one showcase jump at the crest (ゆうころ)
                        climb["phase"] = "jump"
                        crab.sweep = 1.0
                        crab.set_mode("JUMP", t, model)
                        event(t, f"JP stuck at the crest (y={p_jp[1]:+.2f} z={p_jp[2]:.2f}); forward jump")
                    elif p_jp[2] > 0.38 and abs(heading_err) >= 0.15:    # not facing north: turn first, no jump
                        climb["mark"] = (t, float(p_jp[1]))
                    elif p_jp[2] > 0.38:                                  # stalled again on top: push through
                        climb["phase"] = "boost"
                        climb["boost_until"] = t + 5.0
                        event(t, f"JP stalls on top at y={p_jp[1]:+.2f}; full speed 0.8")
                    else:                                                 # slow on the incline is fine: keep walking
                        climb["mark"] = (t, float(p_jp[1]))
                if ph == "boost" and t >= climb["boost_until"]:
                    climb["phase"] = "climb"
                    climb["mark"] = (t, float(p_jp[1]))
                # the duck's head follows the crab; it looks up when the crab is above
                duck.look_at(data, p_jp, pitch=-0.25 if p_jp[2] > 0.3 else 0.1)
                if p_jp[1] > 0.6 and not climb["gone_said"]:
                    climb["gone_said"] = True
                    event(t, "JP over the top; duck looks around")
                if p_jp[1] > 2.2:
                    crab.set_mode("IDLE", t, model)
                    crab.loco.set_command(0, 0, 0)
                    climb["phase"] = "done"
                    climb["done_t"] = t
                    event(t, f"JP crossed the course and stops behind BZ (z={p_jp[2]:.2f})")
            elif ph == "jump":
                duck.look_at(data, p_jp, pitch=-0.25)
                if crab.jump.finished():
                    climb["phase"] = "climb"
                    climb["mark"] = (t, float(p_jp[1]))
                    crab.set_mode("WALK", t, model)
                    event(t, f"JP landed at y={p_jp[1]:+.2f} z={p_jp[2]:.2f}")
            elif ph == "done":
                rel = t - climb["done_t"]
                duck.sit.head[:] = (0.0, 0.0, 0.8 if rel < 1.2 else -0.8 if rel < 2.4 else 0.0, 0.0)
                if 1.1 < rel < 1.3 and "kyoro" not in climb:
                    climb["kyoro"] = True
                    quack("quack")
                if rel > 3.0:
                    set_stage(t, "CALL")
                    call_t0 = t
            if t - stage_t0 > 90.0:
                event(t, "CLIMB timeout; moving on")
                crab.set_mode("IDLE", t, model)
                set_stage(t, "CALL")
                call_t0 = t
        elif stage == "CALL" and args.ending == "crab":
            # the duck calls toward its friend across the course; the crab turns and looks back
            rel = t - call_t0
            duck.sit.twist[:] = (1.0, 0.0, 0.0)
            duck.look_at(data, p_jp, pitch=0.0)
            if crab.mode != "WALK":
                crab.set_mode("WALK", t, model)
            if args.prestage and rel > 1.5:
                # pre-positioning (ゆうころ 10/28 昼): the crab starts back while the duck is still calling, and its route
                # ends in the lane 0.8 m behind the seat - where the push skill starts - instead of 1.7 m away south-east
                if not ret.get("set"):
                    ret.update(route=[(3.0, 2.4), (3.0, -2.4), (2.4, -3.3), (ch.LANE_X, ch.SEAT_Y - 0.8)], set=True)
                    cry("crab")
                    event(t, "JP heads back round the east side of the course to the lane behind the seat (pre-positioning)")
                if ret["route"] and crab_go(ret["route"][0], 0.7, stop=0.35):
                    ret["route"].pop(0)
            else:
                crab.steer(data, p_md[:2], 0.0)
            if rel > 0.8 and "c1" not in climb:
                climb["c1"] = True
                quack("call")
            if rel > 3.0 and "c2" not in climb:
                climb["c2"] = True
                quack("call")
            if rel > 5.0:
                set_stage(t, "RETURN")
                if not ret.get("set"):
                    ret["route"] = [(3.0, 2.4), (3.0, -2.4), (2.6, -3.2)]      # east of the course, then south-east of the seat
                    cry("crab")
                event(t, "JP comes back round the east side of the course to the duck (fixed programme; BZ stays put)")
        elif stage == "RETURN":
            duck.sit.twist[:] = (1.0, 0.0, 0.0)
            duck.look_at(data, p_jp, pitch=0.0)
            if ret["route"]:
                if crab_go(ret["route"][0], 0.7 if (ret.get("set") and len(ret["route"]) > 1) else 0.5, stop=0.35):
                    ret["route"].pop(0)
            if not ret["route"] or t - stage_t0 > 70.0:
                crab.loco.set_command(0, 0, 0)
                set_stage(t, "RESCUE")
                mgr.update(gen=None, n=0, t0=t)
                book.t0_episode = t
                event(t, f"the manager ({manager_name}) takes over: duck {duck.mode}/{h.stage()} at ({p_md[0]:+.2f},{p_md[1]:+.2f}), "
                         f"crab at ({p_jp[0]:+.2f},{p_jp[1]:+.2f}), {h.crab_dist():.2f} m")
        elif stage == "RESCUE":
            if course_disturbed:
                book.course_damage = max(course_disturbed.values())
            if mgr["gen"] is None:                             # a decision point: observe, choose, speak, start the skill
                obs = ch.observation(h, book)
                a = manager_policy(obs)
                name = ch.ACTIONS[a]
                mgr.update(gen=ch.SKILLS[name](h), action=a, name=name, line=ch.bubble_line(a, book, h), t_dec=t, n=mgr["n"] + 1)
                mgr["decisions"].append({"n": mgr["n"], "t": round(t, 1), "video_t": round(video_t(), 1), "action": name,
                                         "bubble": mgr["line"], "duck": duck.mode, "stage": h.stage(),
                                         "touching": bool(h.touching()), "crab_dist": round(h.crab_dist(), 2),
                                         "last_result": book.last_result})
                event(t, f"MANAGER #{mgr['n']}: {name} 「{mgr['line']}」 (duck {duck.mode}/{h.stage()}, crab {h.crab_dist():.2f} m, "
                         f"touching={h.touching()}, last={book.last_result})")
                if name in ("SEAT", "STANDUP", "WALK_ON"):
                    quack("quack")
                elif name == "PUSH":
                    cry("crab")
            try:
                next(mgr["gen"])
            except StopIteration as stop:
                result = stop.value
                book.last_result, book.last_action = result, mgr["action"]
                if mgr["name"] == "PUSH" and mgr["decisions"][-1]["duck"] == "FALLEN":
                    book.nudges += 1
                elif mgr["name"] == "PUSH" and result != "nothing":
                    book.pushes += 1
                mgr["decisions"][-1].update(result=result, duration_s=round(t - mgr["t_dec"], 1))
                mgr["gen"] = None
                event(t, f"MANAGER result: {mgr['name']} -> {result} (duck {duck.mode}/{h.stage()} at ({p_md[0]:+.2f},{p_md[1]:+.2f}) z={p_md[2]:.2f})")
                if result == "pushed_up":
                    quack("happy")
                # crossed: WALK_ON says so, or the duck is on its feet on the north floor after any other skill (it
                # fell on the far ramp, slid down and got up by itself: headless test 2 kept WAITing there until the
                # time limit - the learning environment checks h.crossed() after every skill, so does the story now)
                if result == "crossed" or (h.crossed() and not mgr["crossed"]):
                    mgr["crossed"] = True
                    quack("happy")
                    event(t, f"DUCK CROSSED THE COURSE (y={p_md[1]:+.2f} z={p_md[2]:.3f}) - all three have crossed"
                             + ("" if result == "crossed" else f" (on its feet on the north floor after {mgr['name']} -> {result})"))
                    set_stage(t, "CELEBRATE")
                    cel.update(phase="start")
            # procession finale: once the duck walks on across the landing, the crab (in the lane behind it) follows
            # 0.8 m behind, over the top and down the far ramp.  (Starting only at the far ramp's lip left the crab
            # at the crest when the duck was already down: a 30 s gap, headless test 1.)
            if (mgr["gen"] is not None and args.finale in ("procession", "circle") and mgr["name"] == "WALK_ON" and duck.mode == "WALK_ON"
                    and p_md[1] > ch.CREST_Y + 0.05
                    and (cel["following"] or (abs(p_jp[0] - ch.LANE_X) < 0.4 and p_jp[1] < p_md[1]))):
                if not cel["following"]:
                    cel.update(following=True, mark=(t, float(p_jp[1])))
                    if crab.mode != "WALK":
                        crab.set_mode("WALK", t, model)
                    cry("crab")
                    event(t, f"JP follows the duck across the landing and down the far ramp (procession finale), {h.crab_dist():.2f} m behind")
                    if args.finale == "circle" and args.prestage and bzf["phase"] == "idle":
                        bzf["phase"] = "raise"               # pre-positioning: BZ gets its fork up meanwhile
                        event(t, "BZ raises its fork while the duck walks on (pre-positioning for the circle)")
                crab_follow(t)
            if bzf["phase"] in ("raise", "turn"):
                bz_reposition(t)
            if ch.check_seated_fall(h):
                event(t, f"MD tipped over while seated (tilt {duck.tilt(data):.0f}); velstand takes over")
            if stage == "RESCUE" and t - mgr["t0"] > args.rescue_max:
                event(t, f"RESCUE timeout after {args.rescue_max:.0f} s: duck {duck.mode}/{h.stage()}")
                set_stage(t, "END")
        elif stage == "CELEBRATE":
            if bzf["phase"] != "idle":
                bz_reposition(t)
            circle = args.finale == "circle"
            if cel["phase"] == "start":
                if args.finale in ("procession", "circle") and not cel["following"] and p_jp[1] > ch.CREST_Y and abs(p_jp[0] - ch.LANE_X) < 0.4:
                    cel.update(following=True, mark=(t, float(p_jp[1])))   # already past the crest in the lane: come down
                    if crab.mode != "WALK":
                        crab.set_mode("WALK", t, model)
                if args.finale in ("procession", "circle") and cel["following"]:
                    cel["phase"] = "follow"
                    if circle and bzf["phase"] == "idle":
                        bzf["phase"] = "raise"
                    event(t, "JP comes down the far ramp after the duck; " + ("the three form a circle at the goal" if circle
                                                                              else "the duck walks on toward BZ; the three meet at the goal"))
                else:
                    cel.update(phase="descend", route=[(2.8, -3.0), (2.9, 1.2), (p_md[0] + 0.9, p_md[1] - 0.1)])
                    if crab.mode != "WALK":
                        crab.set_mode("WALK", t, model)
                    event(t, "JP backs down the ramp, goes round the course to the duck; then the cheering dance")
            elif cel["phase"] == "follow":                  # down the far ramp on the lane, 0.5 m behind the duck
                if circle:
                    duck_to_place(t)
                elif not cel.get("walked") and t - stage_t0 > 1.5 and duck.mode == "STAND":
                    cel["walked"] = True                     # a few gentle steps on toward BZ: clears the ramp's foot for
                    duck.walk_to((ch.LANE_X, 2.5), t, stop_dist=0.2, vx=0.2)   # the crab (walking off at once from the
                    # ramp's last 8 cm at 0.3 m/s tripped it in headless test 3: tilt 74, up again in 1.6 s)
                crab_follow(t, keep=0.5)
                if (p_jp[1] > ch.DOWN_TOE_Y - 0.3 and p_jp[2] < 0.26) or t - stage_t0 > 40.0:
                    cel.update(phase="gather", route=[CIRCLE_VIA, CIRCLE_JP] if circle else [(p_md[0] + 0.9, p_md[1] - 0.15)])
                    event(t, f"JP is down the far ramp (y={p_jp[1]:+.2f} z={p_jp[2]:.2f}); goes to "
                             + ("its place in the circle" if circle else "the duck's side"))
            elif cel["phase"] == "descend":                 # straight back down the ramp's centre line, never off its side
                if p_jp[2] < 0.13 and p_jp[1] < ch.TOE_Y - 0.3 or t - stage_t0 > 25.0:
                    crab.loco.set_command(0, 0, 0)
                    cel["phase"] = "around"
                else:
                    ch.reverse_command(h)
            elif cel["phase"] in ("around", "gather"):
                if circle and bzf["phase"] != "ready":
                    crab.loco.set_command(0, 0, 0)           # (no pre-positioning: BZ still turning, its tines sweep 1.38 m)
                elif cel["route"] and crab_go(cel["route"][0], 0.5 if cel["phase"] == "around" else 0.4, stop=0.25 if circle else 0.35):
                    cel["route"].pop(0)
                if circle:
                    duck_to_place(t)
                if (not cel["route"] and (not circle or (cel.get("md_leg") == 2 and duck.mode == "STAND"))) or t - stage_t0 > 60.0:
                    cel.update(phase="face", t_face=t)
                    if circle:
                        event(t, f"the duck and the crab are in their places ({np.linalg.norm(p_md[:2] - p_bz[:2]):.2f} / "
                                 f"{np.linalg.norm(p_jp[:2] - p_bz[:2]):.2f} m from BZ, which is {bzf['phase']})")
            elif cel["phase"] == "face":
                if circle:
                    # BZ turns round (bz_reposition), the crab turns on the spot, the duck turns under velstand: all face the
                    # centre, taken from where BZ actually ends up (its tracks slip ~0.35 m north while it turns)
                    centre = (float(p_bz[0]), float(p_bz[1]) - CIRCLE_R)
                    _, err_jp = crab.steer(data, centre, 0.0)
                    if duck.mode == "STAND" and not cel.get("turning"):
                        cel["turning"] = True
                        duck.use("vel")
                        duck.set_mode("TURN", t)
                    err_md = wrap(math.atan2(centre[1] - p_md[1], centre[0] - p_md[0]) - duck.yaw(data))
                    if duck.mode == "TURN":
                        if abs(err_md) < 0.12:
                            duck.pol.twist[:] = 0
                            duck.set_mode("STAND", t)
                        else:
                            duck.pol.twist[:] = (0.0, 0.0, float(np.clip(2.5 * err_md, -1.2, 1.2)))
                    md_ok = cel.get("turning") and duck.mode == "STAND" and abs(err_md) < 0.3
                    if (abs(err_jp) < 0.2 and md_ok and bzf["phase"] == "ready") or t - cel["t_face"] > 30.0:
                        cel.update(phase="dance", t_dance=t, last_cry=-9.0)
                        if render:
                            clock.speed = SPEED_DANCE
                        cry("crab")
                        quack("happy")
                        event(t, f"the circle: BZ pumps its fork, the duck squats and shakes its head, the crab dances with its claws up "
                                 f"(duck {abs(err_md):.2f} rad, crab {abs(err_jp):.2f} rad off the centre)")
                else:
                    _, err = crab.steer(data, p_md[:2], 0.0)
                    if abs(err) < 0.2 or t - stage_t0 > 70.0:
                        cel.update(phase="dance", t_dance=t, last_cry=-9.0)
                        if render:
                            clock.speed = SPEED_DANCE
                        cry("crab")
                        quack("happy")
                        if args.finale == "procession":
                            event(t, "the three cheer at the goal: BZ's fork up, the duck flaps, the crab dances with its arms up")
                        else:
                            crab.set_mode("DANCE", t, model)
                            event(t, "JP dances beside the duck (official dance policy); BZ raises its fork twice")
            elif cel["phase"] == "dance":
                rel = t - cel["t_dance"]
                if circle:
                    if duck.mode == "SIT" and duck.tilt(data) > 60.0:     # toppled while squatting: velstand takes over
                        duck.resume, duck.fell_at, duck.upright_since = "STAND", t, None
                        duck.use("vel")
                        duck.set_mode("FALLEN", t)
                        event(t, f"the duck toppled while squatting (tilt {duck.tilt(data):.0f}); velstand takes over")
                    if cheer_circle_tick(rel, duck, crab, sim, model, data, t):
                        set_stage(t, "END")
                    elif rel - cel["last_cry"] > 1.6:
                        cel["last_cry"] = rel
                        if int(rel / 1.6) % 2 == 0:
                            quack("happy", float(rng.uniform(0.9, 1.15)))
                        else:
                            cry("crab")
                elif args.finale == "procession":
                    if cheer_tick(rel, duck, crab, sim, model, data, t):
                        duck.cheer = None
                        if duck.mode == "CHEER":
                            duck.set_mode("STAND", t)
                        set_stage(t, "END")
                    elif rel - cel["last_cry"] > 1.6:
                        cel["last_cry"] = rel
                        if int(rel / 1.6) % 2 == 0:
                            quack("happy", float(rng.uniform(0.9, 1.15)))
                        else:
                            cry("crab")
                else:
                    if rel < 6.0:
                        sim.command(0.0, 0.0, 1.0 if (rel % 3.0) < 1.5 else -1.0)      # fork up, down, up, down
                    else:
                        sim.command(0.0, 0.0, -1.0 if sim.lift_target > 0 else 0.0)
                    if rel > 12.0:
                        set_stage(t, "END")
            if cel["phase"] != "dance" and bzf["phase"] in ("idle", "ready"):
                sim.command(0, 0, 0)
            if duck.mode == "STAND":
                duck.gaze = p_jp[:2]
        elif stage == "CALL":
            rel = t - call_t0
            if cheer["phase"] == "wait":                     # the crab clears BZ's turning circle
                cheer["phase"] = "aside"
                crab.set_mode("WALK", t, model)
            if cheer["phase"] == "aside" and crab_go(ASIDE_SPOT, 0.5):
                cheer["phase"] = "aside_done"
            elif cheer["phase"] == "aside_done":
                crab.steer(data, p_bz[:2], 0.0)              # face BZ
            if rel > 0.8 and "c1" not in climb:
                climb["c1"] = True
                quack("call")
            if rel > 3.0 and "c2" not in climb:
                climb["c2"] = True
                quack("call")
            # then the duck turns its back on the ramp and sits down again (sulking), so that BZ can come up
            # behind it: v7_test_fork.py lifts the seated duck cleanly only with both tines under its hips
            # (approach from straight behind, centreline 1.5-3 cm to the duck's left); from the side one tine
            # hooks it at best and the set-down tips it.  ゆうころ 10/27: being lifted is the heart-warming ending.
            tb = turnback["phase"]
            if tb == "wait":
                duck.sit.twist[:] = (1.0, 0.0, 0.0)
                duck.look_at(data, p_bz, pitch=0.0)
                if rel > 4.0 and args.ending == "lift":
                    turnback.update(phase="start", t0=t)
            elif tb == "start":
                duck.sit.twist[:] = 0                                   # sitstand flag 0: stand up
                duck.sit.head[:] = 0
                if t - turnback["t0"] > 3.0:
                    duck.use("vel")
                    duck.set_mode("TURN", t)
                    turnback.update(phase="turn", t0=t)
            elif tb == "turn" and duck.mode == "TURN":
                err_w = wrap(math.pi - duck.yaw(data))                 # face west: back to the east, where BZ will come from
                wz = math.copysign(min(1.2, max(0.35, 2.0 * abs(err_w))), err_w) if abs(err_w) >= 0.05 else 0.0
                duck.vel.twist[:] = (0.0, 0.0, wz)
                if (abs(err_w) < 0.05 and t - turnback["t0"] > 1.0) or t - turnback["t0"] > 10.0:
                    duck.vel.twist[:] = 0
                    duck.use("sit")
                    duck.set_mode("SIT", t)
                    duck.sit.twist[:] = (1.0, 0.0, 0.0)
                    duck.sit.head[:] = (0.3, 0.4, 0, 0)
                    turnback.update(phase="seated", t0=t)
                    quack("sigh")
                    event(t, f"duck turns its back on the ramp and sits down again (yaw {math.degrees(duck.yaw(data)):.0f} deg)")
            elif tb == "turn" and duck.mode == "STAND":                # stumbled and got up (velstand): sit anyway
                if t - turnback["t0"] > 10.0:
                    turnback["t0"] = t - 9.0
            elif tb == "seated":
                duck.sit.twist[:] = (1.0, 0.0, 0.0)
                duck.sit.head[:] = (0.3, 0.4, 0, 0)
            if (tb == "seated" and t - turnback["t0"] > 2.5) or (args.ending == "push" and rel > 5.0):
                set_stage(t, "LIFT")
                lift_phase = "navigate"
                lift_t0 = t
                cheer["phase"] = "follow"
                crab.set_mode("WALK", t, model)
                if args.ending == "lift":
                    yaw_d = duck.yaw(data)
                    facing = np.array([math.cos(yaw_d), math.sin(yaw_d)])
                    left_d = np.array([-math.sin(yaw_d), math.cos(yaw_d)])
                    turnback["axis_u"] = facing                         # BZ docks along the duck's facing direction...
                    turnback["axis_p"] = p_md[:2] + 0.022 * left_d      # ...on a line 2.2 cm to the duck's left (tines under both hips)
                    approach = p_md[:2] - 3.2 * facing                  # 3.2 m straight behind: room to line up while docking
                    event(t, f"BZ drives back around the course to behind the duck ({approach[0]:+.2f},{approach[1]:+.2f}); "
                             f"duck yaw {math.degrees(yaw_d):.0f} deg")
                else:                                                   # "push" (take 5): at the seated duck's right side, from the east
                    turnback["axis_u"] = np.array([-1.0, 0.0])
                    turnback["axis_p"] = p_md[:2].copy()
                    approach = np.array([p_md[0] + 1.9, p_md[1]])
                    event(t, "BZ drives back around the course to the duck's east side")
                nav = make_navigator(sim, [[3.3, 3.0], [float(approach[0]), float(approach[1])]])
        elif stage == "LIFT":
            # the crab comes back with BZ and cheers the duck with a dance (ゆうころ 10/27 深夜):
            # trail BZ at 1.7 m, then go round BZ's east side to the duck's south, face it, dance.
            if cheer["phase"] == "follow":
                d_bz = float(np.linalg.norm(p_jp[:2] - p_bz[:2]))
                crab.steer(data, p_bz[:2], 0.6 if d_bz > 1.7 else 0.0)
                if lift_phase != "navigate":
                    cheer["phase"] = "detour"
                    cheer["route"] = [(5.6, p_md[1] + 0.7), (5.6, p_md[1] - 1.8), (3.0, p_md[1] - 1.7)]   # clear of BZ (3.2 m behind the duck) and block_2
                    event(t, "JP goes round BZ's east side to the duck's south")
            elif cheer["phase"] == "detour":
                if crab_go(cheer["route"][0], 0.5, stop=0.35):
                    cheer["route"].pop(0)
                    if not cheer["route"]:
                        cheer["phase"] = "spot"
            elif cheer["phase"] == "spot":
                if crab_go((p_md[0] + 0.2, p_md[1] - 1.1), 0.5, stop=0.2):
                    cheer["phase"] = "face"
            elif cheer["phase"] == "face":
                _, err = crab.steer(data, p_md[:2], 0.0)
                if abs(err) < 0.2:
                    cheer["phase"] = "dance"
                    crab.set_mode("DANCE", t, model)
                    cry("crab")
                    event(t, "JP starts its cheering dance beside the duck (official dance policy)")
            if duck.mode == "SIT":
                duck.sit.twist[:] = (1.0, 0.0, 0.0)
                if lift_phase == "hold":                                # up on the fork: look around
                    duck.sit.head[:] = (0.1, -0.1, 0.7 * math.sin(2 * math.pi * 0.5 * (t - lift_t0)), 0.0)
                else:
                    duck.look_at(data, p_bz, pitch=0.0)                 # over its shoulder, as far as the neck goes
                if duck.tilt(data) > 60.0:                 # the fork tipped the sitting duck over
                    duck.resume = "STAND"
                    duck.fell_at = t
                    duck.upright_since = None
                    duck.use("vel")
                    duck.set_mode("FALLEN", t)
                    event(t, f"the fork tips the duck over (tilt {duck.tilt(data):.0f}); velstand takes over")
            elif duck.mode == "STAND":
                duck.gaze = p_bz[:2]
            yaw_bz = quat_to_yaw(data.xquat[bz_bid])
            left_bz = np.array([-math.sin(yaw_bz), math.cos(yaw_bz)])
            A, u = turnback["axis_p"], turnback["axis_u"]           # docking line: through A, direction u (BZ travels along u)
            rel_bz = p_bz[:2] - A
            e_lat = float(u[0] * rel_bz[1] - u[1] * rel_bz[0])      # BZ's offset from the line, + = left of travel
            psi = wrap(yaw_bz - math.atan2(u[1], u[0]))             # BZ's heading error against the line
            d = A - p_bz[:2]
            dist_bz = float(np.linalg.norm(p_md[:2] - p_bz[:2]))
            err = wrap(math.atan2(d[1], d[0]) - yaw_bz)             # bearing error to A (coarse aim)
            lat_bz = float(left_bz @ (p_md[:2] - p_bz[:2]))         # the duck's offset to BZ's left; -0.022 is the target
            if lift_phase == "navigate":
                sim.command(*nav.action(sim))
                if nav.done:
                    lift_phase = "aim"
                    lift_t0 = t
                    event(t, f"BZ arrived ({nav.reason}); aims at the duck")
            elif lift_phase == "aim":
                # coarse aim at the target; for "lift" the fine alignment is the docking controller's job
                turn = 0.0 if abs(err) <= 0.03 else math.copysign(0.7 if abs(err) > 0.1 else 0.3, err)
                sim.command(0.0, turn, 0.0)
                if abs(err) <= 0.03 or t - lift_t0 > 20.0:
                    lift_phase = "dock" if args.ending == "lift" else "insert"
                    lift_t0 = t
                    event(t, f"BZ aimed (bearing {err:+.3f} rad, {e_lat:+.3f} m off the line, heading {psi:+.3f}); "
                             + ("docks along the line at floor level" if args.ending == "lift" else "slides the fork in at 6 cm")
                             + f" ({dist_bz:.2f} m)")
            elif lift_phase == "insert":
                # "push" ending (take 5): fork held ~6 cm up while sliding in from the side.  At floor level the
                # tines shove the seated duck along (v7_test_fork.py: pushed 0.3 m, no tip); at 6 cm they catch it
                # above its seat and tip it over (tilt 92) - and velstand gets it back on its feet by itself.
                lift_cmd = 1.0 if sim.lift_target < 0.06 else (-1.0 if sim.lift_target > 0.075 else 0.0)
                sim.command(0.15, float(np.clip(2.0 * err, -0.3, 0.3)), lift_cmd)
                if dist_bz < 0.98 or t - lift_t0 > 25:
                    lift_phase = "lift"
                    lift_t0 = t
                    event(t, f"BZ lifts (duck {dist_bz:.2f} m ahead, touching={robots_in_contact(model, data, md_root, bz_root)})")
            elif lift_phase == "dock":
                # line following onto the docking line (lateral + heading feedback), tines at floor level.
                # v7_test_fork.py from straight behind: both tines slide under the hips and lift the duck when
                # the centreline is 1.5-3 cm to its left; 0 or 4.5 cm shoves / tips it, 6 cm misses.  Test #17:
                # pure pursuit left 3.7 cm and ~4 deg of skew at contact -> lifted crooked (tilt 35) and dropped.
                # Test #18: line following alone still arrived 5 cm / 4 deg off -> three steps: follow the line
                # to 1.55 m, stop and aim the centreline at the hips (0.006 rad ~ 1 cm at the tines), creep in.
                fwd = 0.12                                                        # slow: the line follower is better damped
                turn = float(np.clip(-(1.5 * e_lat + 3.0 * psi), -0.45, 0.45))    # #19/#20 overshot (6-10 cm, 7 deg) at 0.15-0.2
                sim.command(fwd, turn, -1.0)
                if dist_bz < 1.50 or t - lift_t0 > 90:
                    lift_phase = "aim2"
                    lift_t0 = t
                    event(t, f"BZ stops at {dist_bz:.2f} m ({e_lat:+.3f} m off the line, heading {psi:+.3f} rad); fine aim at the hips")
            elif lift_phase == "aim2":
                turn = 0.0 if abs(err) <= 0.006 else math.copysign(0.5 if abs(err) > 0.08 else 0.22, err)
                sim.command(0.0, turn, -1.0)
                if abs(err) <= 0.006 or t - lift_t0 > 25.0:
                    lift_phase = "creep"
                    lift_t0 = t
                    event(t, f"BZ aimed (bearing {err:+.4f} rad, skew {psi:+.3f} rad, {e_lat:+.3f} m off the line); creeps in")
            elif lift_phase == "creep":
                sim.command(0.10, float(np.clip(2.0 * err, -0.2, 0.2)), -1.0)     # keep the centreline on the hips
                if dist_bz < 1.40 and "lat_logged" not in climb:
                    climb["lat_logged"] = True
                    event(t, f"tines reach the duck: BZ {e_lat:+.3f} m off the line, heading {psi:+.3f} rad; "
                             f"duck {lat_bz:+.3f} m left of BZ's centreline (target -0.022)")
                if dist_bz < 0.98 or t - lift_t0 > 40:
                    lift_phase = "lift"
                    lift_t0 = t
                    event(t, f"BZ lifts (duck {dist_bz:.2f} m ahead, {lat_bz:+.3f} m left, {e_lat:+.3f} m off the line, "
                             f"touching={robots_in_contact(model, data, md_root, bz_root)})")
            elif lift_phase == "lift":
                gentle = args.ending == "lift"
                sim.command(0.0, 0.0, 0.6 if gentle else 1.0)           # lift: gently to 0.30 m; push: to the top (take 5)
                if sim.lift_target >= (0.30 if gentle else 0.49) - 1e-6 or t - lift_t0 > 4.0:
                    lift_phase = "hold"
                    lift_t0 = t
                    lifted = p_md[2] > 0.15
                    event(t, f"fork up ({sim.lift_target:.2f}); duck z={p_md[2]:.3f} tilt={duck.tilt(data):.0f}"
                             + (" - lifted!" if lifted else " - not on the fork"))
                    quack("happy" if lifted else "worried")
            elif lift_phase == "hold":
                sim.command(0.0, 0.0, 0.0)
                if 1.8 < t - lift_t0 < 2.0 and "hold_quack" not in climb and args.ending == "lift":
                    climb["hold_quack"] = True
                    quack("quack", 1.1)
                if t - lift_t0 > (4.0 if args.ending == "lift" else 2.5):
                    lift_phase = "lower"
                    lift_t0 = t
            elif lift_phase == "lower":
                sim.command(0.0, 0.0, -0.4 if args.ending == "lift" else -1.0)     # lift: gently down
                if sim.lift_target <= 0.0 or t - lift_t0 > 6.0:
                    lift_phase = "back"
                    lift_t0 = t
                    event(t, f"fork down; duck z={p_md[2]:.3f} tilt={duck.tilt(data):.0f}")
            elif lift_phase == "back":
                if args.ending == "lift":
                    sim.command(-0.15, 0.0, 0.0)                        # slowly, until the tines are clear of the duck
                    done_back = dist_bz > 2.0 or t - lift_t0 > 25.0
                else:
                    sim.command(-0.25, 0.0, 0.0)                        # take 5
                    done_back = t - lift_t0 > 2.5
                if done_back:
                    sim.command(0, 0, 0)
                    lift_phase = "wait"
                    lift_t0 = t
                    if duck.mode == "SIT":                 # still seated: stand up on its own (sitstand flag 0)
                        duck.sit.twist[:] = 0
                        event(t, "duck stands up (sitstand flag 0)")
            elif lift_phase == "wait":
                sim.command(0, 0, 0)
                if duck.mode == "SIT":
                    duck.sit.twist[:] = 0                   # sitstand flag 0: stand up
                    duck.sit.head[:] = 0
                if duck.mode == "SIT" and t - lift_t0 > 3.5:
                    duck.use("vel")
                    duck.set_mode("STAND", t)
                if duck.mode == "STAND":
                    duck.gaze = p_jp[:2]                    # the duck turns to the dancing crab
                if duck.mode == "STAND" and t - lift_t0 > 3.0 and "end_quack" not in climb:
                    climb["end_quack"] = True
                    quack("happy")
                    event(t, "duck is on its feet; happy")
                if (duck.mode == "STAND" and t - lift_t0 > 8.0) or t - lift_t0 > 45.0:
                    set_stage(t, "END")
        if stage == args.until and args.until != "END":
            set_stage(t, "END")
        # the course must survive the rescue (ゆうころ): report any part nudged beyond course-builder's 4 cm
        if course_ref is not None:
            for n, p0 in course_ref.items():
                moved = float(np.linalg.norm(data.xpos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)][:2] - p0))
                if moved > 0.04 and n not in course_disturbed:
                    course_disturbed[n] = round(moved, 3)
                    event(t, f"COURSE DISTURBED: {n} moved {moved:.3f} m")
        if duck.mode != duck_prev_mode:
            if duck.mode == "FALLEN":
                event(t, f"MD fell (tilt {duck.tilt(data):.0f}) at ({p_md[0]:+.2f},{p_md[1]:+.2f})")
                quack("worried")
            elif duck_prev_mode == "FALLEN":
                event(t, f"MD is back on its feet by itself ({t - duck.fell_at:.1f} s)")
                quack("happy")
            duck_prev_mode = duck.mode

        # ── robots + physics ──────────────────────────────────────────
        md_every = round(MD_CONTROL_DT / dt)
        jp_every = max(1, round(0.005 / dt))       # the crab infers at 200 Hz whatever the physics step
        duck.control(data, t)
        for s in range(substeps):
            if sub_k % md_every == 0:
                duck.step(model, data)
            if sub_k % jp_every == 0:
                crab.step(model, data)
            mujoco.mj_step(model, data)
            sub_k += 1
            if video is not None and clock.due(data.time):
                video.add(render_frame())
        if args.preview and (data.time - last_shot >= 15.0):
            last_shot = data.time
            cam.snap()
            imageio.imwrite(args.preview / f"v7_t{int(data.time):04d}_{stage}.png", render_frame())
        if np.any(np.isnan(data.qpos)):
            event(t, "NaN in qpos - aborting")
            break
        if k % 500 == 0:
            print(f"  t={t:6.1f}s [{stage}] BZ {pilot.stage if not pilot.done else 'done'} @({p_bz[0]:+.2f},{p_bz[1]:+.2f}) "
                  f"MD({duck.mode}) @({p_md[0]:+.2f},{p_md[1]:+.2f}) z={p_md[2]:.3f} tilt={duck.tilt(data):4.1f} "
                  f"JP({crab.mode}) @({p_jp[0]:+.2f},{p_jp[1]:+.2f}) z={p_jp[2]:.2f} wall {time.perf_counter() - t_wall:5.0f}s",
                  flush=True)

    if video is not None:
        for _ in range(int(2.5 / CONTROL_DT)):
            duck.control(data, data.time)
            dt = model.opt.timestep
            for s in range(round(CONTROL_DT / dt)):
                if sub_k % round(MD_CONTROL_DT / dt) == 0:
                    duck.step(model, data)
                if sub_k % max(1, round(0.005 / dt)) == 0:
                    crab.step(model, data)
                mujoco.mj_step(model, data)
                sub_k += 1
                if clock.due(data.time):
                    video.add(render_frame())
    if render:
        renderer.close()

    report = {"mujoco": mujoco.__version__, "sim_seconds": round(float(data.time), 2),
              "construction": {"success": bool(pilot.success), "reason": pilot.reason,
                               "parts": pilot.results, "rise_m": pilot.max_rise, "surfaces": len(pilot.touched)},
              "course_disturbed": course_disturbed,
              "ending": args.ending,
              "manager": {"policy": manager_name, "decisions": mgr["decisions"], "duck_crossed": mgr["crossed"]},
              "three_crossed": {"bz": bool(pilot.success), "crab": climb["phase"] == "done", "duck": mgr["crossed"]},
              "events": events, "md_events": duck.events, "jp_events": crab.events, "chirps": chirps.events}
    if video is not None:
        size = video.close()
        report["video_silent"] = {"path": str(video.path), "frames": video.frames, "bytes": size}
        wav = OUT_DIR / f"3body_arena_v7{args.tag}_chirps.wav"
        chirps.wav(wav, video.frames / VIDEO_FPS)
        final = OUT_DIR / f"3body_arena_v7{args.tag}.mp4"
        import imageio_ffmpeg
        res = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(video.path), "-i", str(wav),
                              "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(final)],
                             capture_output=True, text=True)
        report["video"] = {"path": str(final), "ffmpeg_rc": res.returncode,
                           "bytes": final.stat().st_size if final.exists() else None}
        print(f"Done: {final} ({video.frames} frames, ffmpeg rc={res.returncode})")
    (OUT_DIR / f"v7_full_report{args.tag}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("events", "md_events", "jp_events", "chirps")},
                     indent=2, ensure_ascii=False))
    for e in events:
        print(f"  {e['t']:7.2f}s  {e['event']}")


def make_navigator(sim, waypoints):
    from navigation import Navigator
    return Navigator(sim, waypoints, allow_reverse=True)


if __name__ == "__main__":
    main()
