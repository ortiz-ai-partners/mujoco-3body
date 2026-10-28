"""The crab's face: an expression on its display panel, chosen from the manager's action and its result.

ゆうころ 10/28 夕:「カニの表情を AI 管理できたりする？ 例えば押しているときは一生懸命な＞＜とか、おうえんしてるときは
にっこりとか」→ the expression table below (the consultation's proposal, approved as is), shown in a corner inset
("顔モニター") because on the story's cameras the panel is only 10-20 px tall and faces away from them while pushing.

What is official and what is ours
  * The real Jumper has two round 0.9-inch TFT "expression displays" (jumper/docs/HARDWARE.md).  The official repository
    ships one face animation, for the dance task: tasks/jumper/dance/media/demo.mp4, a 57 s loop of eye shapes (open,
    blink, half-closed, sparkle) that plays on the displays beside the exported performance.  There is no API that picks
    an expression from the robot's state - the face is content, not control.
  * This module is the island's.  It derives from jumper/out/face_tools/face_display.py (10/11, the lesson videos: a
    render-only screen on the display panel, one material per expression, picked every frame from the simulation
    state).  The pictures are drawn with PIL; the sparkle borrows the official animation's four-pointed star.

Render-only, physics untouched
  The screen is a contype=0 / conaffinity=0 / density=0 mesh geom on `display_module_link` (the 10.7 x 3.9 cm front
  plate), 0.4 mm proud of it; the face camera is a camera.  Neither adds mass, contacts or joints, and the expression is
  switched by writing `model.geom_matid`.  Checked, not assumed: `v7_full.py --test` with and without `--no-face` gives
  the same events, the same manager decisions and the same final state digest (out/v7_full_report_facecheck_{A,B}.json,
  HANDOVER.md).

The expression table ("AI 管理": a function of the manager's chosen action and its result, like the speech bubbles)
  | situation                                     | from                                 | face     |
  | entering, waiting, playing                    | BUILD / FOLLOW_IN; WAIT in the rescue| neutral  |
  | walking to its post, climbing, jumping        | WALK / JUMP outside the play         | serious  |
  | pushing                                       | the PUSH skill running               | cross    |
  | pushing for 5 s and more (ゆうころ 10/28 夕)    | PUSH, 5 s of contact with the duck   | sweat    |
  | the push did not work (stalled / slipped /    | the skill after a failed PUSH        | sweat    |
  |   nothing / the duck fell)                    |                                      |          |
  | seating, backing off, standing the duck up    | SEAT / BACK_OFF / STANDUP / WALK_ON  | serious  |
  | cheering, the celebration dance               | DANCE / FREEZE                       | happy    |
  | the duck has crossed                          | until the celebration dance starts   | sparkle  |
  | fallen over                                   | tilt > 50 deg                        | spiral   |
  Not learned: nothing scores a face, so a learned one would be arbitrary.  The "?" for a decision failure that the
  consultation mentioned is not in: whether a repeated action was a mistake is the evaluation's judgement (2x2 in
  MANAGER_DESIGN.md), not a state the manager has.

The mood AI (ゆうころ 10/28 夜:「本物の推論で 2 つの AI を走らせるように」, take 38-)
  A second network runs beside the manager and infers the crab's mood: `MoodAI`, the mood net trained by
  analysis/mood_train.py on analysis/mood_data.py's data (the rule, PPO and random managers in the learning
  environment, the manager's 46-dim observation every 0.1 s inside every skill, how the skill ended and whether
  the duck got across).  Every control step of the rescue it reads the manager's observation, the running skill and
  its elapsed time and infers p(this move ends well) and p(the duck gets across): a 53-32-32-2 MLP, a wholly
  separate network from every manager (out/manager_runs/mood_net/).  p(move ends well), smoothed, is the mood:
  confident above MOOD_P_HI, worried below MOOD_P_LO, neutral between.  The mood then colours the table above:
  during a push, worry sweats before the 5 s; while waiting, confidence smiles and worry sweats; seating / backing
  off / standing the duck up sweat when worried.  The PPO v2.2 critic was tried first (--face-ai critic): it reads
  every mid-push state as hopeless (V -22) because it only ever saw decision points (analysis/face_value.py), so it
  is kept as a record, not used.  `--face-ai table` switches the mood off.
"""
from __future__ import annotations

import math
import os
import tempfile

import mujoco
import numpy as np

EXPRESSIONS = ("neutral", "serious", "spiral", "cross", "sweat", "happy", "sparkle")
JA = {"neutral": "まる目", "serious": "真剣", "spiral": "ぐるぐる", "cross": "＞＜ 一生懸命", "sweat": "＞＜ 汗",
      "happy": "にっこり", "sparkle": "キラキラ"}
GLOW = (120, 235, 255)              # the display's colour
TEX_W, TEX_H = 640, 232             # texture size, about the panel's aspect (10.0 x 3.4 cm drawn area)
PANEL_HY, PANEL_HZ = 0.0170, 0.0500   # half extents of the drawn area (3.4 x 10 cm)

TILT_ON, TILT_OFF = 50.0, 35.0      # deg from upright: spiral on above / off below
SPIRAL_HOLD = 0.6                   # s the spiral stays after a fall (readable at 2x)
HOLD = 0.35                         # s an expression stays at least, so the face does not flicker

# the face monitor: a camera in front of the panel, rendered into a small inset.  320x160 at the bottom-left in takes
# 30-33; smaller and at the top-right from take 34 (ゆうころ 10/28 夕: 「もう少し小さくして右上の空欄に」)
PIP_W, PIP_H = 240, 120
CAM_DIST = 0.30                     # m in front of the panel (beyond the renderer's near plane, in front of the folded arms)
PIP_FILL = 0.72                     # the panel's 10 cm fill this much of the inset's width
PUSH_SWEAT_S = 5.0                  # s of pushing (PUSH skill, in contact with the duck) after which the face sweats

# the mood AI: the mood net's p(this move ends well), smoothed, read as confident / neutral / worried (see MoodAI)
MOOD_NET = "mood_net"             # out/manager_runs/<MOOD_NET>/mood_net.pt + meta.json (analysis/mood_train.py)
MOOD_RUN = "ppo2_v22"              # the PPO whose critic is the --face-ai critic option (a record, not the default)
MOOD_TAU = 0.5                      # s, time constant of the smoothing
MOOD_P_HI, MOOD_P_LO = 0.70, 0.35   # p(move ends well) above: confident; below: worried
MOOD_P_HYST = 0.05                  # a mood is left only once p is this far past its threshold
MOOD_HI, MOOD_LO = 6.0, 2.0         # critic option: V above / below
MOOD_DROP, MOOD_DROP_S = 2.0, 2.0   # critic option: a fall of V by this much within this many seconds is worry
MOOD_HYST = 0.5
MOOD_JA = {"confident": "自信", "neutral": "ふつう", "worried": "不安"}

FAILED_PUSH = ("stalled", "slipped", "nothing", "fell")
RESULT_JA = {"stalled": "動かない", "slipped": "滑った", "nothing": "変化なし", "fell": "転んだ"}
SKILL_JA = {"SEAT": "座らせる", "BACK_OFF": "少し離れる", "STANDUP": "立たせる", "WALK_ON": "見送る", "WAIT": "様子を見る"}


# ---------------------------------------------------------------- the pictures
def _draw(expr):
    from PIL import Image, ImageDraw, ImageFilter

    W, H = TEX_W, TEX_H
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    lw = 22
    for side in (-1, 1):
        cx, cy = W / 2 + side * W * 0.22, H * 0.52
        if expr == "neutral":                       # round eyes
            r = H * 0.20
            d.ellipse((cx - r * 0.8, cy - r, cx + r * 0.8, cy + r), fill=255)
        elif expr == "serious":                     # focused: eyes cut by a lid slanting down to the centre
            w, h = H * 0.30, H * 0.20
            d.rounded_rectangle((cx - w, cy - h, cx + w, cy + h), radius=int(h * 0.6), fill=255)
            inner = cx - side * w                   # the lid is lower on the side nearer the centre
            outer = cx + side * w
            d.polygon([(inner, cy - h - 4), (inner, cy + h * 0.15), (outer, cy - h * 0.55),
                       (outer, cy - h - 4)], fill=0)
            d.line([(inner - side * 6, cy - h * 0.05), (outer + side * 4, cy - h * 0.95)], fill=255, width=lw // 2)
        elif expr == "spiral":                      # ぐるぐる
            pts = []
            turns, rmax = 2.6, H * 0.30
            for k in range(240):
                t = k / 239
                a = side * t * turns * 2 * np.pi
                r = rmax * t
                pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
            d.line(pts, fill=255, width=lw // 2 + 4, joint="curve")
        elif expr in ("cross", "sweat"):            # > <, pointing at each other
            a, b = H * 0.20, H * 0.26                # left eye ">" points right, right eye "<" points left
            d.line([(cx + side * a, cy - b), (cx - side * a, cy), (cx + side * a, cy + b)],
                   fill=255, width=lw, joint="curve")
        elif expr == "happy":                       # ^ ^
            a, b = H * 0.26, H * 0.22
            d.line([(cx - a, cy + b * 0.7), (cx, cy - b), (cx + a, cy + b * 0.7)], fill=255, width=lw, joint="curve")
        elif expr == "sparkle":                     # the official eye animation's four-pointed star, one per eye
            _star(d, cx, cy, H * 0.36, H * 0.11)
            _star(d, cx + side * H * 0.42, cy - H * 0.30, H * 0.12, H * 0.04)   # a small twinkle outside each eye
        else:
            raise ValueError(expr)
    if expr == "sweat":                             # a drop at the right temple
        x, y, r = W * 0.86, H * 0.22, H * 0.075
        d.polygon([(x, y - r * 1.9), (x - r * 0.95, y + r * 0.2), (x + r * 0.95, y + r * 0.2)], fill=255)
        d.ellipse((x - r, y - r * 0.4, x + r, y + r * 1.6), fill=255)
    glow = img.filter(ImageFilter.GaussianBlur(9))
    a = np.clip(np.asarray(img, np.float32) / 255 + np.asarray(glow, np.float32) / 255 * 0.55, 0, 1)
    base = np.array((6, 8, 12), np.float32)        # the screen's own black, a shade lighter than the panel
    rgb = base + (np.array(GLOW, np.float32) - base) * a[..., None]
    return Image.fromarray(rgb.astype(np.uint8), "RGB")


def _star(d, cx, cy, r_long, r_short):
    pts = []
    for k in range(8):
        r = r_long if k % 2 == 0 else r_short
        a = k * math.pi / 4 - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=255)


def write_textures(folder=None):
    folder = folder or tempfile.mkdtemp(prefix="crab_face_")
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for e in EXPRESSIONS:
        p = os.path.join(folder, f"face_{e}.png")
        _draw(e).save(p)
        paths[e] = p
    return paths


# ---------------------------------------------------------------- the screen and the face camera
def _display_frame(geom_pos, geom_quat):
    """The plate's mesh frame -> body frame."""
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, np.asarray(geom_quat, float))
    return np.asarray(geom_pos, float), R.reshape(3, 3)


def add_face(spec, prefix="jp-", folder=None):
    """Add the screen geom, one material per expression and the face camera to the arena `spec` (after the crab was
    attached with `prefix`).  Returns {"geom": name, "camera": name, "materials": {expression: material name}}."""
    body = next((b for b in spec.bodies if b.name == prefix + "display_module_link"), None)
    if body is None:
        raise RuntimeError(f"no {prefix}display_module_link in this model")
    # the plate's geometry, measured on the shipped mesh (MuJoCo centres a mesh on its inertia frame): 3.7 mm thick
    # along mesh x, 3.9 cm along mesh y, 10.7 cm along mesh z; geom pos/quat place that frame in the body
    # (jumper/assets/jumper/jumper.xml, display_module_link_visual)
    pos, R = _display_frame((-0.00170, 0.0, -0.00070), (0.6747, 0.6748, -0.2115, 0.2115))
    nx = R @ np.array([1.0, 0.0, 0.0])
    front = 1.0 if nx[0] > 0 else -1.0             # the face the robot looks out of (+x of the body is forward)
    off = front * (0.0019 + 0.0004)                # 0.4 mm proud of the plate's surface
    hy, hz = PANEL_HY, PANEL_HZ
    corners = [(off, -hy, -hz), (off, -hy, hz), (off, hy, hz), (off, hy, -hz)]
    verts = np.array([pos + R @ np.array(c) for c in corners])
    up_y = 1.0 if (R @ np.array([0.0, 1.0, 0.0]))[2] > 0 else -1.0     # which mesh-y direction is "up" on the face
    right_z = 1.0 if (R @ np.array([0.0, 0.0, 1.0]))[1] > 0 else -1.0  # the robot's +y side is on the viewer's right
    uv = []
    for (_, y, z) in corners:
        u = 0.5 + 0.5 * (z / hz) * right_z
        v = 0.5 - 0.5 * (y / hy) * up_y            # texture rows run downwards
        uv.append((u, v))
    normal = R @ np.array([front, 0.0, 0.0])       # out of the face, body frame
    n = np.cross(verts[1] - verts[0], verts[2] - verts[0])
    faces = [0, 1, 2, 0, 2, 3] if float(n @ normal) > 0 else [0, 2, 1, 0, 3, 2]   # wound to face outwards
    mesh = spec.add_mesh(name=prefix + "face_screen_mesh")
    mesh.uservert = verts.ravel().tolist()
    mesh.usertexcoord = np.array(uv).ravel().tolist()
    mesh.userface = faces
    mesh.inertia = mujoco.mjtMeshInertia.mjMESH_INERTIA_SHELL   # a flat sheet has no volume
    mats = {}
    for e, p in write_textures(folder).items():
        tex = spec.add_texture(name=prefix + f"face_tex_{e}", type=mujoco.mjtTexture.mjTEXTURE_2D, file=p)
        mat = spec.add_material(name=prefix + f"face_mat_{e}")
        mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = tex.name
        mat.emission = 1.0
        mat.specular = 0.15
        mat.shininess = 0.6
        mat.texuniform = False
        mats[e] = mat.name
    g = body.add_geom(name=prefix + "face_screen", type=mujoco.mjtGeom.mjGEOM_MESH, meshname=mesh.name,
                      contype=0, conaffinity=0, density=0, group=2, material=mats["neutral"])
    # the face camera: in front of the panel's centre, looking back at it, the panel's up on screen up
    centre = pos + R @ np.array([off, 0.0, 0.0])
    up = R @ np.array([0.0, up_y, 0.0])
    x_cam = np.cross(up, normal)                   # the viewer's right (looking along -normal with `up` up)
    rot = np.column_stack([x_cam, up, normal])     # the camera looks along its -z
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, rot.ravel())
    cam = body.add_camera(name=prefix + "face_cam")
    cam.pos = (centre + normal * CAM_DIST).tolist()
    cam.quat = quat.tolist()
    span_v = (2 * hz / PIP_FILL) * (PIP_H / PIP_W)                        # vertical extent seen at the panel
    cam.fovy = math.degrees(2 * math.atan(span_v / 2 / CAM_DIST))
    return {"geom": g.name, "camera": cam.name, "materials": mats}


# ---------------------------------------------------------------- choosing the expression
class FaceDriver:
    """Picks the expression from the story's state (the table in the module docstring) and sets the screen's material.

    update() is called every control step, rendered or headless, so the face timeline is in every report."""

    def __init__(self, model, prefix="jp-", mood_ai=None):
        self.model = model
        self.mood_ai = mood_ai                       # a MoodAI, or None (the table alone)
        self.gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, prefix + "face_screen")
        self.mat = {e: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MATERIAL, prefix + f"face_mat_{e}") for e in EXPRESSIONS}
        if self.gid < 0 or min(self.mat.values()) < 0:
            raise RuntimeError("the model has no face (build_arena(face=True))")
        self.cam_name = prefix + "face_cam"
        self.expr, self.reason, self.since = "neutral", "登場", -1e9
        self.spiral_until = -1e9
        self.push_contact_s = 0.0                    # s spent pushing the duck (PUSH skill, in contact) in the current skill
        self.t_prev = None
        self.log = []                                # [t, expression, reason] at every change
        self.model.geom_matid[self.gid] = self.mat[self.expr]

    def choose(self, t, s):
        """(expression, reason) for state `s`: stage, crab_mode, tilt, skill, touching, last_action, last_result, crossed."""
        if s["tilt"] > TILT_ON or (self.expr == "spiral" and s["tilt"] > TILT_OFF):
            self.spiral_until = t + SPIRAL_HOLD
        if t < self.spiral_until:
            return "spiral", "転倒"
        if s["crab_mode"] in ("DANCE", "FREEZE"):
            return "happy", ("祝賀ダンス" if s["stage"] in ("CELEBRATE", "END") else "応援ダンス")
        if s["crossed"] and s["stage"] in ("CELEBRATE", "END"):
            return "sparkle", "パッカンが渡り切った"
        if s["stage"] == "RESCUE":
            mood = self.mood_ai.mood if (self.mood_ai is not None and self.mood_ai.ready) else "neutral"
            if s["skill"] is None:                  # between two skills (one control step): keep the face, no blink
                return self.expr, self.reason
            if s["skill"] == "PUSH":
                if self.push_contact_s >= PUSH_SWEAT_S:
                    return "sweat", "押し上げ中、5 秒超"
                if mood == "worried":
                    return "sweat", "押し上げ中、不安"
                return "cross", "押し上げ中"
            if s["last_action"] == "PUSH" and s["last_result"] in FAILED_PUSH:
                return "sweat", f"押し上げ → {RESULT_JA.get(s['last_result'], s['last_result'])}"
            if s["skill"] in ("SEAT", "BACK_OFF", "STANDUP", "WALK_ON"):
                if mood == "worried":
                    return "sweat", SKILL_JA[s["skill"]] + "、不安"
                return "serious", SKILL_JA[s["skill"]]
            if mood == "worried":
                return "sweat", "様子を見る、不安"
            if mood == "confident":
                return "happy", "様子を見る、自信"
            return "neutral", "様子を見る"
        if s["stage"] in ("BUILD", "FOLLOW_IN"):
            return "neutral", "戯れ・待機"
        if s["crab_mode"] in ("WALK", "JUMP"):
            return "serious", {"CLIMB": "坂を登る", "RETURN": "戻る", "RAMP": "持ち場へ", "CALL": "戻る準備",
                               "CELEBRATE": "輪の位置へ"}.get(s["stage"], "移動中")
        return "neutral", "待機"

    def update(self, t, obs=None, **state):
        """obs: the manager's observation this control step (the rescue), for the mood AI; None elsewhere."""
        dt = 0.0 if self.t_prev is None else max(0.0, t - self.t_prev)
        self.t_prev = t
        if self.mood_ai is not None and obs is not None and state.get("skill_idx") is not None:
            self.mood_ai.update(obs, t, state["skill_idx"], state.get("t_in_skill", 0.0))
        if state.get("skill") == "PUSH":
            if state.get("touching"):
                self.push_contact_s += dt
        elif state.get("skill") is not None:        # the next skill: the count starts again (None = between two skills)
            self.push_contact_s = 0.0
        want, reason = self.choose(t, state)
        if want != self.expr and (want == "spiral" or t - self.since >= HOLD):
            self.expr, self.since = want, t
            self.model.geom_matid[self.gid] = self.mat[want]
        if want == self.expr:
            self.reason = reason
        if not self.log or self.log[-1][1:] != [self.expr, self.reason]:    # every change of face or of its reason
            self.log.append([round(t, 2), self.expr, self.reason])
        return self.expr

    def label(self):
        return f"{JA[self.expr]}：{self.reason}"

    def title_label(self):
        """The monitor's top line: the mood AI's reading, or a note that the face is render-only."""
        m = self.mood_ai
        if m is not None and m.ready:
            if m.kind == "critic":
                return f"気分 AI V={m.v_ema:+.1f} {MOOD_JA[m.mood]}"
            return f"気分 AI 見込み {m.p_ema:.0%} {MOOD_JA[m.mood]}"
        return "跳跳の顔（表示パネル・描画のみ）"


class MoodAI:
    """The second AI beside the manager, inferring the crab's mood every control step of the rescue.

    kind "mood" (default): the mood net (analysis/mood_train.py) infers p(this move ends well) and p(the duck gets
    across) from the manager's observation, the running skill and its elapsed time; p_ema (smoothed p(move ends
    well)) is read as confident / neutral / worried with hysteresis.  kind "critic": the PPO v2.2 critic's V(s), the
    first attempt, kept as a record.  log: [t, value, mood] at every mood change; series: [t, p_ok, p_cross] (or
    [t, V]) once a second."""

    def __init__(self, kind="mood", run=MOOD_RUN, net=MOOD_NET):
        import json
        from pathlib import Path
        import torch
        self.torch = torch
        self.kind = kind
        here = Path(__file__).resolve().parent / "out" / "manager_runs"
        if kind == "critic":
            from stable_baselines3 import PPO
            self.run = run
            self.ppo = PPO.load(here / run / "ppo_manager", device="cpu")
        else:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent / "analysis"))
            from mood_train import MoodNet, features
            self.run = net
            self.meta = json.load(open(here / net / "meta.json", encoding="utf-8"))
            self.net = MoodNet(self.meta["n_in"], self.meta["hidden"])
            self.net.load_state_dict(torch.load(here / net / "mood_net.pt", map_location="cpu"))
            self.net.eval()
            self.features = features
            self.mean = np.asarray(self.meta["obs_mean"], np.float32)
            self.std = np.asarray(self.meta["obs_std"], np.float32)
        self.ready = False
        self.v = self.v_ema = None                   # critic
        self.p_ok = self.p_cross = self.p_ema = None  # mood net
        self.mood = "neutral"
        self.hist = []
        self.log = []
        self.series = []
        self.t_prev = None
        self.n = 0

    def infer(self, obs, skill_idx=0, t_in_skill=0.0):
        """One inference: (p_ok, p_cross) for the mood net, (V, None) for the critic."""
        with self.torch.no_grad():
            if self.kind == "critic":
                ten, _ = self.ppo.policy.obs_to_tensor(np.asarray(obs, dtype=np.float32))
                return float(self.ppo.policy.predict_values(ten)), None
            x = self.features(np.asarray(obs, np.float32), int(skill_idx), float(t_in_skill), self.mean, self.std)
            p = self.torch.sigmoid(self.net(self.torch.tensor(x)[None]))[0]
            return float(p[0]), float(p[1])

    def update(self, obs, t, skill_idx=0, t_in_skill=0.0):
        a, b = self.infer(obs, skill_idx, t_in_skill)
        dt = 0.0 if self.t_prev is None else max(0.0, t - self.t_prev)
        self.t_prev = t
        self.n += 1
        k = min(1.0, dt / MOOD_TAU) if MOOD_TAU > 0 else 1.0
        mood = self.mood
        if self.kind == "critic":
            self.v = a
            self.v_ema = a if self.v_ema is None else self.v_ema + k * (a - self.v_ema)
            self.hist.append((t, self.v_ema))
            while self.hist and self.hist[0][0] < t - MOOD_DROP_S:
                self.hist.pop(0)
            drop = max((h for _, h in self.hist), default=self.v_ema) - self.v_ema
            if mood == "worried":
                if self.v_ema > MOOD_LO + MOOD_HYST and drop < MOOD_DROP * 0.5:
                    mood = "confident" if self.v_ema >= MOOD_HI else "neutral"
            elif mood == "confident":
                if self.v_ema < MOOD_HI - MOOD_HYST or drop >= MOOD_DROP:
                    mood = "worried" if (self.v_ema <= MOOD_LO or drop >= MOOD_DROP) else "neutral"
            elif self.v_ema <= MOOD_LO or drop >= MOOD_DROP:
                mood = "worried"
            elif self.v_ema >= MOOD_HI:
                mood = "confident"
            value, sample = self.v_ema, [round(t, 2), round(a, 2)]
        else:
            self.p_ok, self.p_cross = a, b
            pv = b if int(skill_idx) == 0 else a          # WAIT always "ends well" (waited): its mood is p(the duck gets across)
            self.p_ema = pv if self.p_ema is None else self.p_ema + k * (pv - self.p_ema)
            p = self.p_ema
            if mood == "worried":
                if p > MOOD_P_LO + MOOD_P_HYST:
                    mood = "confident" if p >= MOOD_P_HI else "neutral"
            elif mood == "confident":
                if p < MOOD_P_HI - MOOD_P_HYST:
                    mood = "worried" if p <= MOOD_P_LO else "neutral"
            elif p <= MOOD_P_LO:
                mood = "worried"
            elif p >= MOOD_P_HI:
                mood = "confident"
            value, sample = p, [round(t, 2), round(a, 3), round(b, 3)]
        self.ready = True
        if mood != self.mood:
            self.mood = mood
            self.log.append([round(t, 2), round(value, 3), mood])
        if not self.series or t - self.series[-1][0] >= 1.0:
            self.series.append(sample)
        return self.mood


if __name__ == "__main__":
    # write the seven pictures next to this file, for a look (out/face_textures/)
    here = os.path.dirname(os.path.abspath(__file__))
    for e, p in write_textures(os.path.join(here, "out", "face_textures")).items():
        print(e, p)
