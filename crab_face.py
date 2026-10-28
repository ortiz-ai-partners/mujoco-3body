"""The crab's face: an expression composed from what a second AI infers and what the simulation measures.

ゆうころ 10/28 夕〜夜:「カニの表情を AI 管理できたりする？」→ a table keyed by the manager's action (takes 30-37)
→「本物の推論で 2 つの AI を走らせるように」→ a mood net beside the manager (takes 38-41)
→「複数の確率と計測値から表情を組み立てるものを精密に設計したい」→ this version (take 42-): the face is composed from
   the mood net's four outcome probabilities and the crossing estimate, and from measured effort, contact, progress
   and events, by the priority rules below.  The monitor shows the values that decide the face.

What is official and what is ours
  * The real Jumper has two round 0.9-inch TFT "expression displays" (jumper/docs/HARDWARE.md).  The official repository
    ships one face animation, for the dance task (tasks/jumper/dance/media/demo.mp4: open, blink, half-closed, sparkle).
    There is no API that picks an expression from the robot's state.
  * This module is the island's.  The screen derives from jumper/out/face_tools/face_display.py (10/11, the lesson
    videos); the pictures are drawn with PIL; the sparkle borrows the official animation's four-pointed star.

Render-only, physics untouched
  The screen is a contype=0 / conaffinity=0 / density=0 mesh geom on `display_module_link` (the 10.7 x 3.9 cm front
  plate), 0.4 mm proud of it; the face camera is a camera; the expression is switched by writing `model.geom_matid`;
  the mood net only reads the manager's observation.  Checked: `v7_full.py --test` with and without the face gives the
  same final-state digest, events and decisions (analysis/face_check.py).

The faces (10, + 困り with a drop)
  neutral まる目 / serious 真剣 / spiral ぐるぐる / cross ＞＜ / sweat ＞＜汗 / happy にっこり / sparkle キラキラ /
  troubled 困り / troubled_sweat 困り汗 / relief ほっ / shock ガーン

The inputs
  inferred (MoodAI, the mood net, analysis/mood_train.py): p_success / p_stall / p_fall / p_nothing - how the running
    move will end (success / stops or slips / the duck falls / nothing happens or the duck stays down), and p_cross -
    the duck gets across in the end.  Read every control step of the rescue from the manager's own observation, the
    running skill and its elapsed time.  A separate network from every manager.
  measured: effort (the contact force the crab puts on the duck, smoothed, / PUSH_FORCE_REF; the sum of the actuator
    forces was tried first and does not separate pushing from walking: headless D, push 5.4 vs walking 4.9 N·m),
    contact with the duck and the time spent pushing (contact flickers every half second while pushing, so pushing
    is latched until contact has been lost for CONTACT_GAP_S), the duck's progress while pushed and during its own
    ramp attempts (stalled = less than STALL_V * STALL_S of advance over the last STALL_S), the duck's mode (a
    fall), the crab's tilt, the stage, the running skill and how the last one ended.

The rules (the first that holds wins; FaceDriver.choose)
   1 the crab's tilt over 50 deg                                                   -> spiral
   2 the duck has just fallen, or the push just ended with a fall (1.5 s)          -> shock
   3 the duck has crossed, until the celebration dance                            -> sparkle
   4 the celebration dance                                                         -> happy
   5 the last move just ended well (2 s)                                           -> relief
   6 watching the duck's ramp attempts: it stalls, backs off or gives up           -> troubled
   7 watching the duck's ramp attempts: it is climbing (the cheer dance too)       -> happy
   8 pushing, in contact: p_stall+p_fall >= 40%, p_fall >= 30%, or no progress 2 s -> troubled_sweat
   9 pushing, in contact: effort >= 0.7 or 5 s of contact                          -> sweat
  10 pushing, in contact                                                           -> cross
  11 the last move stalled or made the duck fall, until p_success passes the smile line -> troubled
  12 going to push / seating / backing off / standing up / seeing off: p_fall >= 30% or p_success < trouble line -> troubled
  13 the same moves: p_success >= the smile line                                   -> happy
  14 the same moves, in between                                                    -> serious
  15 waiting: p_cross >= 60% / <= 30%                                              -> happy / troubled
  16 the crab's own climb and jumps                                                -> serious
  17 otherwise (playing, idle, walking, waiting)                                   -> neutral
  The smile and trouble lines come from the mood net's held-out data (meta.json: 80% of the moves that ended well lie
  above the smile line, 80% of the failed ones below the trouble line).  Thresholds carry a 5% hysteresis and a face
  is held 0.5 s (spiral, shock and the first contact are immediate).
"""
from __future__ import annotations

import math
import os
import tempfile

import mujoco
import numpy as np

EXPRESSIONS = ("neutral", "serious", "spiral", "cross", "sweat", "happy", "sparkle",
               "troubled", "troubled_sweat", "relief", "shock")
JA = {"neutral": "まる目", "serious": "真剣", "spiral": "ぐるぐる", "cross": "＞＜", "sweat": "＞＜汗",
      "happy": "にっこり", "sparkle": "キラキラ", "troubled": "困り", "troubled_sweat": "困り汗", "relief": "ほっ",
      "shock": "ガーン"}
GLOW = (120, 235, 255)              # the display's colour
TEX_W, TEX_H = 640, 232             # texture size, about the panel's aspect (10.0 x 3.4 cm drawn area)
PANEL_HY, PANEL_HZ = 0.0170, 0.0500   # half extents of the drawn area (3.4 x 10 cm)

TILT_ON, TILT_OFF = 50.0, 35.0      # deg from upright: spiral on above / off below
SPIRAL_HOLD = 0.6                   # s the spiral stays after a fall
HOLD = 0.5                          # s a face stays at least (ゆうころ: 0.5 秒以上保つ)

# the face monitor: a camera in front of the panel, rendered into a small inset in the caption's row
PIP_W, PIP_H = 240, 120
CAM_DIST = 0.30                     # m in front of the panel (beyond the renderer's near plane, in front of the folded arms)
PIP_FILL = 0.72                     # the panel's 10 cm fill this much of the inset's width

# measured signals
PUSH_SWEAT_S = 5.0                  # s of pushing in contact after which the face sweats (ゆうころ)
PUSH_FORCE_REF = 10.0               # N: the contact force on the duck that reads as effort 1.0 (calibrated on a headless run,
                                    # see HANDOVER; the duck weighs about 15 N)
EFFORT_HI, EFFORT_LO = 0.70, 0.55   # effort above: sweat while pushing; it stays until the effort is back under EFFORT_LO
EFFORT_TAU = 0.3                    # s, smoothing of the effort
CONTACT_GAP_S = 1.0                 # s without contact after which a push no longer counts as pushing
STALL_V, STALL_S = 0.01, 2.0        # m/s along y: under STALL_V * STALL_S of advance over the last STALL_S = not moving
PUSH_STALL_S = 3.0                  # s of no progress while pushing before the face worries (the crab pauses ~2 s at the
                                    # ramp's lip to line up: crab_help lip_pause, headless E at 292.5 s)
SHOCK_S, RELIEF_S = 1.5, 2.0        # s the shock and the relief faces last

# the mood net
MOOD_NET = "mood_net"               # out/manager_runs/<MOOD_NET>/mood_net.pt + meta.json (analysis/mood_train.py)
MOOD_RUN = "ppo2_v22"               # the PPO whose critic --face-ai critic reads (the first attempt, a record)
MOOD_TAU = 0.5                      # s, smoothing of the inferred probabilities
P_FALL = 0.30                       # p(the duck falls) above: trouble
P_STALL_FALL = 0.40                 # p(stops) + p(falls) above, while pushing: trouble
P_CROSS_HI, P_CROSS_LO = 0.60, 0.30 # waiting: p(gets across) above -> happy, below -> troubled
P_HYST = 0.05                       # a line is crossed back only this far past it
SMILE_DEFAULT, TROUBLE_DEFAULT = 0.60, 0.40   # the smile / trouble lines when meta.json has none
MOOD_HI, MOOD_LO = 6.0, 2.0         # critic option: V above / below
MOOD_DROP, MOOD_DROP_S, MOOD_HYST = 2.0, 2.0, 0.5
MOOD_JA = {"confident": "自信", "neutral": "ふつう", "worried": "不安"}

GOOD_RESULTS = ("seated", "pushed_up", "cleared", "standing", "crossed", "walked")
FAILED_PUSH = ("stalled", "slipped", "nothing", "fell")
RESULT_JA = {"stalled": "動かない", "slipped": "滑った", "nothing": "変化なし", "fell": "転んだ", "still_down": "起きない"}
SKILL_JA = {"SEAT": "座らせる", "BACK_OFF": "少し離れる", "STANDUP": "立たせる", "WALK_ON": "見送る", "WAIT": "様子を見る",
            "PUSH": "押しに行く"}
RAMP_JA = {"try1": "坂に挑む", "try2": "もう一回", "back": "後ずさり", "handover": "諦める", "sit": "座り込む"}


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
        elif expr in ("troubled", "troubled_sweat"):   # 困り: half-closed eyes under brows whose inner ends lift
            w, h = H * 0.27, H * 0.12
            d.rounded_rectangle((cx - w, cy - h + H * 0.08, cx + w, cy + h + H * 0.08), radius=int(h * 0.9), fill=255)
            inner, outer = cx - side * w, cx + side * w        # the brow is higher at the end nearer the centre
            d.line([(inner, cy - H * 0.36), (outer, cy - H * 0.18)], fill=255, width=lw // 2 + 2)
        elif expr == "relief":                      # ほっ: eyes closed softly, curving down (content)
            a, b = H * 0.26, H * 0.18
            d.arc((cx - a, cy - b, cx + a, cy + b), start=15, end=165, fill=255, width=lw)
        elif expr == "shock":                       # ガーン: flat bar eyes (￣ ￣)
            a = H * 0.26
            d.line([(cx - a, cy - H * 0.06), (cx + a, cy - H * 0.06)], fill=255, width=lw)
        else:
            raise ValueError(expr)
    if expr in ("sweat", "troubled_sweat"):         # a drop at the right temple
        x, y, r = W * 0.86, H * 0.22, H * 0.075
        d.polygon([(x, y - r * 1.9), (x - r * 0.95, y + r * 0.2), (x + r * 0.95, y + r * 0.2)], fill=255)
        d.ellipse((x - r, y - r * 0.4, x + r, y + r * 1.6), fill=255)
    if expr == "shock":                             # a small open mouth (□) and shock lines above the centre
        m = H * 0.08
        d.rectangle((W / 2 - m, H * 0.62, W / 2 + m, H * 0.62 + 2 * m), outline=255, width=lw // 2)
        for k in (-1, 0, 1):
            d.line([(W / 2 + k * H * 0.14, H * 0.05), (W / 2 + k * H * 0.14, H * 0.24)], fill=255, width=lw // 3)
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


# ---------------------------------------------------------------- the second AI
class MoodAI:
    """The second AI beside the manager, run every control step of the rescue.

    kind "mood" (default): the mood net (analysis/mood_train.py) infers from the manager's observation, the running
    skill and its elapsed time how the move will end - p_success / p_stall / p_fall / p_nothing (they sum to 1) - and
    p_cross, whether the duck gets across.  `p` holds them smoothed (MOOD_TAU); the smile and trouble lines come from
    the net's meta.json.  kind "critic": the PPO v2.2 critic's V(s), the first attempt, kept as a record.  log: mood
    changes (critic) or nothing; series: [t, p_success, p_stall, p_fall, p_nothing, p_cross] (or [t, V]) once a second."""

    KEYS = ("p_success", "p_stall", "p_fall", "p_nothing", "p_cross")

    def __init__(self, kind="mood", run=MOOD_RUN, net=MOOD_NET):
        import json
        from pathlib import Path
        import torch
        self.torch = torch
        self.kind = kind
        here = Path(__file__).resolve().parent / "out" / "manager_runs"
        self.thr_smile, self.thr_trouble = SMILE_DEFAULT, TROUBLE_DEFAULT
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
            self.net = MoodNet(self.meta["n_in"], self.meta["hidden"], self.meta.get("n_out", 5))
            self.net.load_state_dict(torch.load(here / net / "mood_net.pt", map_location="cpu"))
            self.net.eval()
            self.features = features
            self.mean = np.asarray(self.meta["obs_mean"], np.float32)
            self.std = np.asarray(self.meta["obs_std"], np.float32)
            self.thr_smile = float(self.meta.get("thr_smile", SMILE_DEFAULT))
            self.thr_trouble = float(self.meta.get("thr_trouble", TROUBLE_DEFAULT))
            self.smile_by_skill = self.meta.get("thr_smile_by_skill", {})      # each move against its own lines
            self.trouble_by_skill = self.meta.get("thr_trouble_by_skill", {})
        self.ready = False
        self.raw = None
        self.p = None                                # smoothed probabilities (dict), mood net
        self.v = self.v_ema = None                   # critic
        self.mood = "neutral"                        # critic's reading
        self.hist = []
        self.log = []
        self.series = []
        self.t_prev = None
        self.n = 0

    def infer(self, obs, skill_idx=0, t_in_skill=0.0):
        """One inference: a dict of the five probabilities (mood net), or {"V": value} (critic)."""
        with self.torch.no_grad():
            if self.kind == "critic":
                ten, _ = self.ppo.policy.obs_to_tensor(np.asarray(obs, dtype=np.float32))
                return {"V": float(self.ppo.policy.predict_values(ten))}
            x = self.features(np.asarray(obs, np.float32), int(skill_idx), float(t_in_skill), self.mean, self.std)
            out = self.net(self.torch.tensor(x)[None])[0]
            probs = self.torch.softmax(out[:4], dim=0)
            return {"p_success": float(probs[0]), "p_stall": float(probs[1]), "p_fall": float(probs[2]),
                    "p_nothing": float(probs[3]), "p_cross": float(self.torch.sigmoid(out[4]))}

    def update(self, obs, t, skill_idx=0, t_in_skill=0.0):
        self.raw = self.infer(obs, skill_idx, t_in_skill)
        dt = 0.0 if self.t_prev is None else max(0.0, t - self.t_prev)
        self.t_prev = t
        self.n += 1
        k = min(1.0, dt / MOOD_TAU) if MOOD_TAU > 0 else 1.0
        if self.kind == "critic":
            a = self.raw["V"]
            self.v = a
            self.v_ema = a if self.v_ema is None else self.v_ema + k * (a - self.v_ema)
            self.hist.append((t, self.v_ema))
            while self.hist and self.hist[0][0] < t - MOOD_DROP_S:
                self.hist.pop(0)
            drop = max((h for _, h in self.hist), default=self.v_ema) - self.v_ema
            mood = self.mood
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
            if mood != self.mood:
                self.mood = mood
                self.log.append([round(t, 2), round(self.v_ema, 2), mood])
            sample = [round(t, 2), round(a, 2)]
        else:
            if self.p is None:
                self.p = dict(self.raw)
            else:
                for key in self.KEYS:
                    self.p[key] += k * (self.raw[key] - self.p[key])
            sample = [round(t, 2)] + [round(self.p[key], 3) for key in self.KEYS]
        self.ready = True
        if not self.series or t - self.series[-1][0] >= 1.0:
            self.series.append(sample)
        return self.raw


# ---------------------------------------------------------------- composing the expression
class FaceDriver:
    """Composes the expression every control step from the mood AI's values and the measured signals (the rules in the
    module docstring), and sets the screen's material.  update() runs rendered or headless, so the face timeline and
    the values behind it are in every report (`log`: [t, expression, reason, rule, values])."""

    def __init__(self, model, prefix="jp-", mood_ai=None):
        self.model = model
        self.mood_ai = mood_ai
        self.gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, prefix + "face_screen")
        self.mat = {e: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MATERIAL, prefix + f"face_mat_{e}") for e in EXPRESSIONS}
        if self.gid < 0 or min(self.mat.values()) < 0:
            raise RuntimeError("the model has no face (build_arena(face=True))")
        self.cam_name = prefix + "face_cam"
        self.expr, self.reason, self.rule, self.since = "neutral", "登場", 17, -1e9
        self.t_prev = None
        self.spiral_until = self.shock_until = self.relief_until = -1e9
        self.push_contact_s = 0.0                    # s spent pushing the duck during the current PUSH (contact, latched)
        self.pushing = False                         # in contact during PUSH, latched over CONTACT_GAP_S gaps
        self.contact_gap_s = 0.0
        self.stall_s = 0.0                           # s the pushed duck has not moved
        self.ramp_stall_s = 0.0                      # s the duck has not moved during its own ramp attempt
        self.effort = 0.0                            # smoothed contact force on the duck, / PUSH_FORCE_REF
        self.y_hist = []                             # (t, duck y) over the last STALL_S seconds
        self.duck_mode_prev = None
        self.n_results_seen = 0
        self.trouble_latched = False                 # the last move stalled or made the duck fall
        self.skill_prev = None
        self.log = []
        self.effort_series = []                      # [t, effort, raw sum] once a second, for the calibration record
        self.model.geom_matid[self.gid] = self.mat[self.expr]

    # -- helpers
    def _p(self, key, default=0.0):
        m = self.mood_ai
        if m is not None and m.kind != "critic" and m.ready and m.p is not None:
            return m.p[key]
        return default

    def _lines(self, skill=None):
        """(smile line, trouble line) for `skill` - each move against its own lines (meta.json), else the overall ones."""
        m = self.mood_ai
        if m is not None and m.kind != "critic":
            if skill is not None and skill in getattr(m, "smile_by_skill", {}):
                return m.smile_by_skill[skill], m.trouble_by_skill.get(skill, m.thr_trouble)
            return m.thr_smile, m.thr_trouble
        return SMILE_DEFAULT, TROUBLE_DEFAULT

    def _above(self, value, line, when_on):
        """value >= line with hysteresis: once on, it stays on until value < line - P_HYST."""
        return value >= (line - P_HYST if when_on else line)

    def _below(self, value, line, when_on):
        return value <= (line + P_HYST if when_on else line)

    # -- the rules
    def choose(self, t, s):
        """(expression, reason, rule number) for the state `s` this control step."""
        if s["tilt"] > TILT_ON or (self.expr == "spiral" and s["tilt"] > TILT_OFF):
            self.spiral_until = t + SPIRAL_HOLD
        if t < self.spiral_until:
            return "spiral", "転倒", 1
        if t < self.shock_until:
            return "shock", "パッカンが転んだ", 2
        stage, mode, skill = s["stage"], s["crab_mode"], s.get("skill")
        if s["crossed"] and stage in ("CELEBRATE", "END"):
            if mode in ("DANCE", "FREEZE"):
                return "happy", "祝賀ダンス", 4
            return "sparkle", "パッカンが渡り切った", 3
        if t < self.relief_until:
            return "relief", "うまくいった", 5
        if stage == "RAMP":
            phase = s.get("ramp_phase")
            if phase in ("back", "handover", "sit") or (phase in ("try1", "try2") and self.ramp_stall_s >= STALL_S):
                return "troubled", f"パッカンが登れない（{RAMP_JA.get(phase, phase)}）", 6
            if phase in ("try1", "try2"):
                return "happy", "パッカンを応援", 7
            if mode in ("WALK", "JUMP"):
                return "neutral", "持ち場へ", 17
            return "happy", "応援ダンス", 7
        if mode == "DANCE":
            return "happy", "応援ダンス", 7
        if stage == "RESCUE":
            if skill is None:                       # between two skills (one control step): keep the face
                return self.expr, self.reason, self.rule
            smile, trouble = self._lines(skill)
            ps, pst, pf, pc = self._p("p_success", 0.5), self._p("p_stall"), self._p("p_fall"), self._p("p_cross", 0.5)
            if skill == "PUSH" and self.pushing:
                if (pst + pf >= P_STALL_FALL) or pf >= P_FALL or self.stall_s >= PUSH_STALL_S:
                    why = ("進みが止まった" if self.stall_s >= PUSH_STALL_S else f"転ばせる {pf:.0%}" if pf >= P_FALL
                           else f"止まる＋転ぶ {pst + pf:.0%}")
                    return "troubled_sweat", "押しながら、" + why, 8
                hard = self.effort >= (EFFORT_LO if self.expr == "sweat" else EFFORT_HI)       # with hysteresis
                if hard or self.push_contact_s >= PUSH_SWEAT_S:
                    why = f"力 {self.effort:.1f}" if hard else "接触 5 秒超"
                    return "sweat", "押し上げ中、" + why, 9
                return "cross", "押し上げ中", 10
            if self.trouble_latched:
                return "troubled", f"直前の押しが{RESULT_JA.get(s.get('last_result'), '失敗')}", 11
            if skill in ("SEAT", "BACK_OFF", "STANDUP", "WALK_ON", "PUSH"):
                name = SKILL_JA[skill]
                on_t = self.expr == "troubled"
                fall_risk = skill == "PUSH" and pf >= P_FALL             # the fall estimate is sharp for the push only
                if fall_risk or self._below(ps, trouble, on_t):
                    return "troubled", f"{name}、成功 {ps:.0%}" + (f" 転ぶ {pf:.0%}" if fall_risk else ""), 12
                if self._above(ps, smile, self.expr == "happy"):
                    return "happy", f"{name}、成功 {ps:.0%}", 13
                return "serious", f"{name}、成功 {ps:.0%}", 14
            if skill == "WAIT":
                if self._above(pc, P_CROSS_HI, self.expr == "happy"):
                    return "happy", f"様子を見る、渡れる {pc:.0%}", 15
                if self._below(pc, P_CROSS_LO, self.expr == "troubled"):
                    return "troubled", f"様子を見る、渡れる {pc:.0%}", 15
                return "neutral", "様子を見る", 17
        if stage == "CLIMB" and mode in ("WALK", "JUMP"):
            return "serious", "坂を登る", 16
        if mode == "FREEZE":
            return "happy", "万歳", 4
        return "neutral", {"BUILD": "戯れ・待機", "FOLLOW_IN": "戯れ・待機", "CALL": "待機", "RETURN": "戻る"}.get(stage, "待機"), 17

    def update(self, t, obs=None, **s):
        """One control step.  s: stage, crab_mode, tilt, skill, skill_idx, t_in_skill, touching, last_result, n_results,
        crossed, duck_mode, duck_y, ramp_phase, effort_raw.  obs: the manager's observation (the rescue) for the mood AI."""
        dt = 0.0 if self.t_prev is None else max(0.0, t - self.t_prev)
        self.t_prev = t
        skill = s.get("skill")
        # measured: the force on the duck, pushing (latched over contact gaps), the duck's progress over STALL_S
        if s.get("push_force") is not None:
            k = min(1.0, dt / EFFORT_TAU) if EFFORT_TAU > 0 else 1.0
            self.effort += k * (s["push_force"] / PUSH_FORCE_REF - self.effort)
        if s.get("duck_y") is not None:
            self.y_hist.append((t, s["duck_y"]))
            while self.y_hist and self.y_hist[0][0] < t - STALL_S:
                self.y_hist.pop(0)
        advance = (self.y_hist[-1][1] - self.y_hist[0][1]) if len(self.y_hist) > 1 else 1.0
        window = (self.y_hist[-1][0] - self.y_hist[0][0]) if len(self.y_hist) > 1 else 0.0
        still = window >= STALL_S - 0.05 and abs(advance) < STALL_V * STALL_S
        if skill == "PUSH":
            if s.get("touching"):
                self.pushing, self.contact_gap_s = True, 0.0
            elif self.pushing:
                self.contact_gap_s += dt
                if self.contact_gap_s > CONTACT_GAP_S:
                    self.pushing = False
        else:
            self.pushing, self.contact_gap_s, self.push_contact_s = False, 0.0, 0.0
        if self.pushing:
            self.push_contact_s += dt
            self.stall_s = self.stall_s + dt if still else 0.0
        else:
            self.stall_s = 0.0
        if s.get("stage") == "RAMP" and s.get("ramp_phase") in ("try1", "try2"):
            self.ramp_stall_s = self.ramp_stall_s + dt if still else 0.0
        else:
            self.ramp_stall_s = 0.0
        # events: a move just ended, the duck fell
        n_results = int(s.get("n_results", 0))
        if n_results > self.n_results_seen:
            self.n_results_seen = n_results
            r = s.get("last_result")
            if r in GOOD_RESULTS:
                self.relief_until = t + RELIEF_S
                self.trouble_latched = False
            if r == "fell":
                self.shock_until = t + SHOCK_S
            if r in ("stalled", "slipped", "fell"):
                self.trouble_latched = True
        if s.get("duck_mode") == "FALLEN" and self.duck_mode_prev not in (None, "FALLEN"):
            self.shock_until = t + SHOCK_S
        self.duck_mode_prev = s.get("duck_mode")
        self.skill_prev = skill
        # the second AI
        if self.mood_ai is not None and obs is not None and s.get("skill_idx") is not None:
            self.mood_ai.update(obs, t, s["skill_idx"], s.get("t_in_skill", 0.0))
        if self.trouble_latched and self._p("p_success", 0.0) >= self._lines(skill)[0]:
            self.trouble_latched = False
        want, reason, rule = self.choose(t, s)
        immediate = want in ("spiral", "shock") or (want == "cross" and self.expr != "cross")
        if want != self.expr and (immediate or t - self.since >= HOLD):
            self.expr, self.since = want, t
            self.model.geom_matid[self.gid] = self.mat[want]
        if want == self.expr:
            self.reason, self.rule = reason, rule
        if not self.log or self.log[-1][1] != self.expr or self.log[-1][3] != self.rule:   # a new face or a new rule
            self.log.append([round(t, 2), self.expr, self.reason, self.rule, self.values()])
        if not self.effort_series or t - self.effort_series[-1][0] >= 1.0:
            self.effort_series.append([round(t, 2), round(self.effort, 3), round(float(s.get("push_force") or 0.0), 2),
                                       round(float(s.get("effort_raw") or 0.0), 2)])
        return self.expr

    # -- what the monitor shows
    def values(self):
        """The numbers behind the face right now (rounded), for the log and the monitor."""
        v = {"effort": round(self.effort, 2), "contact_s": round(self.push_contact_s, 1), "stall_s": round(self.stall_s, 1),
             "pushing": self.pushing}
        m = self.mood_ai
        if m is not None and m.ready:
            if m.kind == "critic":
                v["V"] = round(m.v_ema, 2)
            else:
                v.update({k: round(m.p[k], 3) for k in MoodAI.KEYS})
        return v

    def title_label(self):
        """The monitor's top line: the AI's values when it is reading, else a note that the face is render-only."""
        m = self.mood_ai
        if m is not None and m.ready:
            if m.kind == "critic":
                return f"気分 AI V={m.v_ema:+.1f} {MOOD_JA[m.mood]}"
            p = m.p
            return (f"成功{p['p_success'] * 100:.0f} 止{p['p_stall'] * 100:.0f} 転{p['p_fall'] * 100:.0f} "
                    f"空{p['p_nothing'] * 100:.0f}｜渡{p['p_cross'] * 100:.0f}")     # %, kept short: the box must stay narrow
        return "跳跳の顔（表示パネル・描画のみ）"

    def bars(self):
        """(label, value) for the four outcome bars under the face, or None."""
        m = self.mood_ai
        if m is not None and m.ready and m.kind != "critic":
            return [("成", m.p["p_success"]), ("止", m.p["p_stall"]), ("転", m.p["p_fall"]), ("空", m.p["p_nothing"])]
        return None

    def measured_label(self):
        s = f"力 {self.effort:.1f}"
        if self.push_contact_s > 0:
            s += f"  接触 {self.push_contact_s:.0f} 秒"
        if self.stall_s >= 1.0:
            s += "  止まっている"
        return s

    def label(self):
        return f"{JA[self.expr]}：{self.reason}"


if __name__ == "__main__":
    # write the pictures next to this file, for a look (out/face_textures/)
    here = os.path.dirname(os.path.abspath(__file__))
    for e, p in write_textures(os.path.join(here, "out", "face_textures")).items():
        print(e, p)
