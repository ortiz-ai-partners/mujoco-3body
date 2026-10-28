"""Shared helpers for the v6 phased renders (BZ construction -> MD -> JP).

v1-v5 tried the whole scenario in one script; v6 follows HANDOVER.md section 8
and builds the video in phases that each export their own MP4.
"""
from __future__ import annotations

import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import imageio
import mujoco
import numpy as np

BASE = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "out"
COURSE_BUILDER = BASE / "physical-ai-course-builder"
BZ_XML = COURSE_BUILDER / "scene_fork_tracks.xml"
MD_XML = (BASE / "microduck_rl" / "src" / "mjlab_microduck"
          / "robot" / "microduck" / "scene.xml")
JP_XML = BASE / "jumper" / "assets" / "jumper" / "jumper.xml"

VIDEO_FPS = 30
VIDEO_W, VIDEO_H = 1280, 720

STAGE_BODIES = ("dozer", "up_1", "down_1", "block_1", "block_2")


def course_builder():
    """Import the course-builder modules (Simulation, SlopeAssembly, tracks) in place."""
    if str(COURSE_BUILDER) not in sys.path:
        sys.path.insert(0, str(COURSE_BUILDER))
    import app
    import slope_assembly
    import tracks
    return app, slope_assembly, tracks


# ── Captions ─────────────────────────────────────────────────────────────
_FONTS = [
    Path(r"C:\Windows\Fonts\meiryo.ttc"),
    Path(r"C:\Windows\Fonts\YuGothM.ttc"),
    Path(r"C:\Windows\Fonts\msgothic.ttc"),
]


class Captioner:
    def __init__(self, title_px=30, body_px=24):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.ok = False
            return
        self.Image, self.ImageDraw = Image, ImageDraw
        font_path = next((p for p in _FONTS if p.exists()), None)
        if font_path is None:
            self.title = self.body = self.small = self.tiny = ImageFont.load_default()
        else:
            self.title = ImageFont.truetype(str(font_path), title_px)
            self.body = ImageFont.truetype(str(font_path), body_px)
            self.title_s = ImageFont.truetype(str(font_path), 24)      # the caption shrinks to these beside the monitor
            self.body_s = ImageFont.truetype(str(font_path), 20)
            self.small = ImageFont.truetype(str(font_path), 18)
            self.tiny = ImageFont.truetype(str(font_path), 15)
        if font_path is None:
            self.title_s, self.body_s = self.title, self.body
        self.ok = True

    @staticmethod
    def _wrap(d, text, font, limit):
        """Split `text` into lines no wider than `limit` px (by characters: Japanese has no spaces)."""
        out, cur = [], ""
        for ch in text:
            if cur and d.textbbox((0, 0), cur + ch, font=font)[2] > limit:
                out.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            out.append(cur)
        return out or [""]

    def draw(self, frame, title, lines=(), footer=None, inset=None, notice=None):
        """inset: (image HxWx3, label above, label below) - the crab's face monitor, a small box at the top-right in the
        same row as the caption box (ゆうころ 10/28 夜: 「一番上の文字情報の枠と同じ列に、二段じゃなく一段で」).  The
        caption shrinks its fonts, then wraps its lines, so that it always fits beside the monitor.  notice: a line in a
        box at the bottom-left (a jump cut)."""
        if not self.ok:
            return frame
        img = self.Image.fromarray(frame)
        d = self.ImageDraw.Draw(img, "RGBA")
        pad = 14
        h, w = frame.shape[:2]
        ibox_w = ibox_h = 0
        if inset is not None:
            if isinstance(inset, tuple):                                   # (pic, above, below): the older callers
                inset = {"pic": inset[0], "above": inset[1], "reason": inset[2]}
            pic, above = inset["pic"], inset.get("above") or ""
            bars, below, reason = inset.get("bars"), inset.get("below") or "", inset.get("reason") or ""
            ih, iw = pic.shape[:2]
            ipad = 8
            ba = d.textbbox((0, 0), above, font=self.tiny) if above else (0, 0, 0, 0)
            bb = d.textbbox((0, 0), below, font=self.tiny) if below else (0, 0, 0, 0)
            br = d.textbbox((0, 0), reason, font=self.small) if reason else (0, 0, 0, 0)
            bars_h = 18 if bars else 0
            ibox_w = max(iw, ba[2], bb[2], br[2]) + 2 * ipad
            ibox_h = ipad + ba[3] + 4 + ih + 4 + bars_h + (4 if bars else 0) + bb[3] + (4 if below else 0) + br[3] + ipad
        max_w = (w - 16 - ibox_w - 12 - 16) if inset is not None else (w - 32)
        for tf, bf in ((self.title, self.body), (self.title_s, self.body_s)):
            texts = [(t, tf) for t in self._wrap(d, title, tf, max_w - 2 * pad)]
            for ln in lines:
                if ln:
                    texts += [(t, bf) for t in self._wrap(d, ln, bf, max_w - 2 * pad)]
            boxes = [d.textbbox((0, 0), t, font=f) for t, f in texts]
            box_w = max(b[2] for b in boxes) + 2 * pad
            if box_w <= max_w and len(texts) == 1 + sum(1 for ln in lines if ln):
                break                                                # fits without wrapping at these fonts
        box_h = sum(b[3] for b in boxes) + pad * (len(texts) + 1)
        d.rectangle([16, 16, 16 + box_w, 16 + box_h], fill=(10, 14, 20, 150))
        y = 16 + pad
        for (t, f), b in zip(texts, boxes):
            d.text((16 + pad, y), t, font=f, fill=(255, 255, 255, 255))
            y += b[3] + pad
        if inset is not None:
            x0, y0 = w - 16 - ibox_w, 16                                 # the same row as the caption box
            d.rectangle([x0, y0, x0 + ibox_w, y0 + ibox_h], fill=(10, 14, 20, 150))
            yy = y0 + ipad
            if above:
                d.text((x0 + ipad, yy), above, font=self.tiny, fill=(225, 225, 225, 255))
                yy += ba[3] + 4
            img.paste(self.Image.fromarray(pic), (x0 + ipad, yy))
            d.rectangle([x0 + ipad - 1, yy - 1, x0 + ipad + iw, yy + ih], outline=(120, 235, 255, 200))
            yy += ih + 4
            if bars:                                                     # the four outcome bars: label, then a bar
                cell = iw / len(bars)
                for i, (lab, val) in enumerate(bars):
                    bx = x0 + ipad + int(i * cell)
                    d.text((bx, yy), lab, font=self.tiny, fill=(225, 225, 225, 255))
                    bw = int(cell) - 22
                    d.rectangle([bx + 18, yy + 4, bx + 18 + bw, yy + 14], fill=(40, 50, 60, 220))
                    d.rectangle([bx + 18, yy + 4, bx + 18 + int(bw * max(0.0, min(1.0, float(val)))), yy + 14],
                                fill=(120, 235, 255, 255))
                yy += bars_h + 4
            if below:
                d.text((x0 + ipad, yy), below, font=self.tiny, fill=(225, 225, 225, 255))
                yy += bb[3] + 4
            if reason:
                d.text((x0 + ipad, yy), reason, font=self.small, fill=(255, 255, 255, 255))
        if notice:
            h, w = frame.shape[:2]
            nb = d.textbbox((0, 0), notice, font=self.body)
            d.rectangle([16, h - nb[3] - 2 * pad - 16, 16 + nb[2] + 2 * pad, h - 16], fill=(60, 30, 10, 170))
            d.text((16 + pad, h - nb[3] - pad - 16), notice, font=self.body, fill=(255, 230, 180, 255))
        if footer:
            h, w = frame.shape[:2]
            fb = d.textbbox((0, 0), footer, font=self.body)
            d.rectangle([w - fb[2] - 2 * pad - 16, h - fb[3] - 2 * pad - 16, w - 16, h - 16],
                        fill=(10, 14, 20, 150))
            d.text((w - fb[2] - pad - 16, h - fb[3] - pad - 16), footer,
                   font=self.body, fill=(235, 235, 235, 255))
        return np.asarray(img)


# ── Video ────────────────────────────────────────────────────────────────
class Video:
    """Streams frames straight to ffmpeg; long time-lapses never sit in RAM."""

    def __init__(self, path, fps=VIDEO_FPS, crf=20):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._w = imageio.get_writer(
            str(self.path), fps=fps, codec="libx264",
            output_params=["-crf", str(crf), "-pix_fmt", "yuv420p"],
        )
        self.frames = 0

    def add(self, frame):
        self._w.append_data(frame)
        self.frames += 1

    def close(self):
        self._w.close()
        return self.path.stat().st_size


class FrameClock:
    """Grabs a frame whenever `speed` sim-seconds per video-second have elapsed."""

    def __init__(self, fps=VIDEO_FPS, speed=1.0):
        self.fps = fps
        self.speed = speed
        self.next_t = 0.0

    def due(self, t):
        if t + 1e-9 >= self.next_t:
            self.next_t += self.speed / self.fps
            return True
        return False


# ── Camera ───────────────────────────────────────────────────────────────
class CameraRig:
    """Free camera whose parameters glide toward a target (first-order lag)."""

    def __init__(self, lookat, distance, azimuth, elevation, tau=1.0):
        self.cam = mujoco.MjvCamera()
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.target = np.array([*lookat, distance, azimuth, elevation], dtype=float)
        self.state = self.target.copy()
        self.tau = tau
        self._apply()

    def aim(self, lookat=None, distance=None, azimuth=None, elevation=None):
        if lookat is not None:
            self.target[0:3] = lookat
        if distance is not None:
            self.target[3] = distance
        if azimuth is not None:
            self.target[4] = azimuth
        if elevation is not None:
            self.target[5] = elevation

    def snap(self):
        self.state[:] = self.target
        self._apply()

    def step(self, dt):
        a = 1.0 - math.exp(-dt / self.tau)
        self.state += a * (self.target - self.state)
        self._apply()
        return self.cam

    def _apply(self):
        self.cam.lookat[:] = self.state[0:3]
        self.cam.distance = self.state[3]
        self.cam.azimuth = self.state[4]
        self.cam.elevation = self.state[5]


# ── Built-stage snapshot (Notion phase A0) ───────────────────────────────
def body_poses(model, data, names=STAGE_BODIES):
    out = {}
    for n in names:
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)
        if bid >= 0:
            out[n] = {"pos": np.round(data.xpos[bid], 5).tolist(),
                      "quat": np.round(data.xquat[bid], 6).tolist()}
    return out


def built_stage_xml(assembly_xml_str, poses):
    """Rewrite the assembly scene so every stage body starts where construction left it."""
    root = ET.fromstring(assembly_xml_str)
    world = root.find("worldbody")
    for name, pose in poses.items():
        body = world.find(f"body[@name='{name}']")
        if body is None:
            continue
        body.set("pos", " ".join(f"{v:.5f}" for v in pose["pos"]))
        body.set("quat", " ".join(f"{v:.6f}" for v in pose["quat"]))
        body.attrib.pop("euler", None)
    return ET.tostring(root, encoding="unicode")


def settle_check(xml, bodies=("up_1", "down_1"), seconds=1.0):
    """Load a stage XML standalone and report how far the parts drift in `seconds`."""
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    start = {b: d.body(b).xpos.copy() for b in bodies}
    for _ in range(int(seconds / m.opt.timestep)):
        mujoco.mj_step(m, d)
    return {b: float(np.linalg.norm(d.body(b).xpos - start[b])) for b in bodies}


def quat_to_yaw(q):
    w, x, y, z = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
