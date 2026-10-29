"""The opening self-introduction of the submitted video (about 13 s): the manager AI introduces itself and the three
robots in its own voice, as typed text with a small round face, before the simulation starts.

Render-only.  The robot portraits are drawn from the same MuJoCo models as the main video (the arena at its start,
before anything moves); no physics is stepped.  Text is Japanese with a smaller English line under each sentence.
The sound is soft typing blips and a chime per card, synthesised here (no recorded material).

    python intro.py                      -> out/intro.mp4 (+ out/intro_silent.mp4, out/intro.wav)
    python intro.py --tag _v2            -> out/intro_v2.mp4 ...
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import crab_face
from v6_common import _FONTS, OUT_DIR, VIDEO_FPS, VIDEO_H, VIDEO_W, Video, course_builder
from v6_robots import build_arena

MD_START = (4.0, 0.6, -math.pi / 2)        # same spawn poses as v7_full.py
JP_PARK = (4.6, 1.2, math.pi)
SR = 44100
DURATION = 15.1

# what the manager AI says (Japanese, English)
HELLO = ("はじめまして。", "支配人 AI の アイランドマスターです。", "Hello. I'm Island Master, the manager AI.")
PURPOSE = ("きょうは松尾研の講座の最終課題として、3 体のロボットが", "力を合わせて峠を越えるところを見てもらいます。",
           "Today, for the Matsuo Lab course's final project: three robots team up to cross a pass.")
TEAM = ("きょうの仲間を紹介します。", "Let me introduce today's team.")
CARDS = [
    ("ブルドーザー", "道をつくる職人。坂も自分で運びます。", "The builder. Carries its own ramps."),
    ("パッカン", "がんばり屋。でも、坂は少し苦手。", "Tries hard. Not so good on slopes."),
    ("跳跳（ちょうちょう）", "身軽で世話好きなカニ。愛称は「ちょーさん」。", "A nimble, helpful crab. We call it Cho-san."),
]
JOB = ("うまくいかないとき、次の一手を考えるのが わたしの仕事です。", "When things go wrong, choosing the next move is my job.")

# timeline (s)
T_HELLO = (0.3, 2.1)
T_PURPOSE = 2.7
T_TEAM = 7.2
T_CARDS = (7.6, 8.9, 10.2)
T_JOB = 11.6
T_FADE = 14.5
CPS = 15.0                                   # typed characters per second

BG = (14, 24, 38)
INK = (240, 244, 250)
SUB = (170, 184, 204)
ACCENT = (64, 176, 166)


def font(px):
    path = next((p for p in _FONTS if p.exists()), None)
    return ImageFont.truetype(str(path), px) if path else ImageFont.load_default()


def fit(text, px, max_w):
    """The largest font size up to px at which text fits in max_w pixels."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while px > 10 and probe.textbbox((0, 0), text, font=font(px))[2] > max_w:
        px -= 1
    return font(px)


def render_stills():
    """Wide shot of the arena at its start and three portraits (BZ, duck, crab with a happy face)."""
    app, slope_assembly, _ = course_builder()
    xml = slope_assembly.assembly_xml(app.ROOT / "scene_fork_tracks.xml")
    model, data = build_arena(xml, md_pose=MD_START, jp_pose=JP_PARK, timestep=0.005, face=True)
    face = crab_face.FaceDriver(model, "jp-")
    model.geom_matid[face.gid] = face.mat["happy"]
    mujoco.mj_forward(model, data)
    bz = data.xpos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dozer")].copy()
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0

    def shot(w, h, lookat, distance, azimuth, elevation):
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = lookat
        cam.distance, cam.azimuth, cam.elevation = distance, azimuth, elevation
        r = mujoco.Renderer(model, height=h, width=w)
        r.update_scene(data, camera=cam, scene_option=opt)
        img = Image.fromarray(r.render().copy())
        r.close()
        return img

    wide = shot(VIDEO_W, VIDEO_H, [0.6, 0.2, 0.2], 9.0, 55, -32)
    portraits = [
        shot(360, 230, [bz[0], bz[1], 0.25], 2.4, 215, -18),
        shot(360, 230, [MD_START[0], MD_START[1], 0.16], 0.50, 235, -8),
        shot(360, 230, [JP_PARK[0], JP_PARK[1], 0.10], 0.70, 0, -14),
    ]
    return wide, portraits


def draw_avatar(d, cx, cy, r, blink, talk):
    """The manager AI's face: a round teal head, two eyes that blink, a mouth that moves while it talks."""
    for k in range(3, 0, -1):                                    # soft glow
        g = tuple(int(c * 0.25 + BG[i] * 0.75) for i, c in enumerate(ACCENT))
        d.ellipse([cx - r - 4 * k, cy - r - 4 * k, cx + r + 4 * k, cy + r + 4 * k], fill=g)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
    ex, ey, ew = 0.36 * r, -0.12 * r, 0.13 * r
    eh = 0.03 * r if blink else 0.22 * r
    for sx in (-1, 1):
        d.ellipse([cx + sx * ex - ew, cy + ey - eh, cx + sx * ex + ew, cy + ey + eh], fill=(250, 252, 255))
    if talk:
        mw, my, mh = 0.20 * r, 0.30 * r, 0.12 * r
        d.ellipse([cx - mw, cy + my - mh, cx + mw, cy + my + mh], fill=(250, 252, 255))
    else:
        mw, my = 0.30 * r, 0.12 * r
        d.arc([cx - mw, cy + my - mw * 0.9, cx + mw, cy + my + mw * 0.9], start=25, end=155, fill=(250, 252, 255),
              width=max(2, int(0.07 * r)))
    for sx in (-1, 1):                                          # cheeks
        cr = 0.09 * r
        d.ellipse([cx + sx * 0.62 * r - cr, cy + 0.16 * r - cr * 0.6, cx + sx * 0.62 * r + cr, cy + 0.16 * r + cr * 0.6],
                  fill=(236, 150, 150))


def typed(text, t, t0):
    n = int(max(0.0, t - t0) * CPS)
    return text[:n], n < len(text) and t >= t0


def make_frames(wide, portraits):
    bg = wide.filter(ImageFilter.GaussianBlur(6))
    shade = Image.new("RGB", bg.size, BG)
    bg = Image.blend(bg, shade, 0.72)
    f_jp, f_en = font(38), font(22)
    f_team = font(30)
    f_name, f_line, f_line_en = font(28), font(21), font(17)
    frames, events = [], []                                      # events: (time, kind) for the sound
    n_frames = int(round(DURATION * VIDEO_FPS))
    last_counts = {}
    for i in range(n_frames):
        t = i / VIDEO_FPS
        img = bg.copy()
        d = ImageDraw.Draw(img)
        blink = (t % 2.7) < 0.12
        talking = False

        if t < T_TEAM:                                           # 1: hello and what this is, big face
            line1, line2 = HELLO[0], HELLO[1]
            both, active = typed(line1 + line2, t, T_HELLO[0])
            p1, p2 = PURPOSE[0], PURPOSE[1]
            pboth, pactive = typed(p1 + p2, t, T_PURPOSE)
            talking = (active or pactive) and int(t * 10) % 2 == 0
            draw_avatar(d, 230, 330, 90, blink, talking)
            x = 370
            d.text((x, 168), both[:len(line1)], font=f_jp, fill=INK)
            d.text((x, 220), both[len(line1):], font=fit(line2, 38, VIDEO_W - x - 40), fill=INK)
            if t > T_HELLO[0] + len(line1 + line2) / CPS:
                d.text((x + 2, 276), HELLO[2], font=f_en, fill=SUB)
            d.text((x, 350), pboth[:len(p1)], font=fit(p1, 30, VIDEO_W - x - 40), fill=INK)
            d.text((x, 394), pboth[len(p1):], font=fit(p2, 30, VIDEO_W - x - 40), fill=INK)
            if t > T_PURPOSE + len(p1 + p2) / CPS:
                d.text((x + 2, 446), PURPOSE[2], font=fit(PURPOSE[2], 20, VIDEO_W - x - 40), fill=SUB)
            if t < T_PURPOSE:
                key, cnt = "hello", len(both)
            else:
                key, cnt = "purpose", len(pboth)
        else:                                                    # 2: the team, small face top-left
            draw_avatar(d, 86, 84, 44, blink, False)
            jp, active = typed(TEAM[0], t, T_TEAM)
            d.text((150, 52), jp, font=f_team, fill=INK)
            if t > T_TEAM + len(TEAM[0]) / CPS:
                d.text((152, 94), TEAM[1], font=f_en, fill=SUB)
            key, cnt = "team", len(jp)
            if active and int(t * 10) % 2 == 0:
                draw_avatar(d, 86, 84, 44, blink, True)
            dim = t >= T_JOB
            for k, (t0, (name, line, line_en), pic) in enumerate(zip(T_CARDS, CARDS, portraits)):
                if t < t0:
                    continue
                a = min(1.0, (t - t0) / 0.35)
                x0, y0 = 52 + k * 400, 160 + int((1 - a) * 30)
                card = Image.new("RGB", (376, 340), (26, 38, 56))
                card.paste(pic, (8, 8))
                cd = ImageDraw.Draw(card)
                cd.text((12, 248), name, font=f_name, fill=INK)
                cd.text((12, 286), line, font=fit(line, 21, 352), fill=INK)
                cd.text((12, 314), line_en, font=fit(line_en, 17, 352), fill=SUB)
                if dim:
                    card = Image.blend(card, Image.new("RGB", card.size, BG), min(0.45, (t - T_JOB) / 0.6 * 0.45))
                mask = Image.new("L", card.size, int(255 * a))
                img.paste(card, (x0, y0), mask)
                if t0 <= t < t0 + 1.0 / VIDEO_FPS:
                    events.append((t, "chime"))
            if t >= T_JOB:                                       # 3: the job, a band at the bottom
                band = Image.new("RGB", (VIDEO_W, 120), (10, 18, 30))
                img.paste(band, (0, 560), Image.new("L", band.size, 215))
                jp2, active2 = typed(JOB[0], t, T_JOB)
                f_job = fit(JOB[0], 32, VIDEO_W - 80)
                tw = d.textbbox((0, 0), JOB[0], font=f_job)[2]
                d.text(((VIDEO_W - tw) // 2, 578), jp2, font=f_job, fill=INK)
                if t > T_JOB + len(JOB[0]) / CPS:
                    ew = d.textbbox((0, 0), JOB[1], font=f_en)[2]
                    d.text(((VIDEO_W - ew) // 2, 630), JOB[1], font=f_en, fill=SUB)
                key, cnt = "job", len(jp2)
                if active2 and int(t * 10) % 2 == 0:
                    draw_avatar(d, 86, 84, 44, blink, True)

        if cnt > last_counts.get(key, 0):                        # new characters typed this frame
            for _ in range(cnt - last_counts.get(key, 0)):
                events.append((t, "blip"))
            last_counts[key] = cnt
        if t >= T_FADE:                                          # fade to black into the main video
            img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), min(1.0, (t - T_FADE) / (DURATION - T_FADE)))
        frames.append(np.asarray(img))
    return frames, events


def make_sound(events):
    n = int(DURATION * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(7)
    seen = {}
    for t, kind in events:
        k = seen.get((round(t, 3), kind), 0)
        seen[(round(t, 3), kind)] = k + 1
        t = t + k * (1.0 / VIDEO_FPS) / 3                        # spread the blips of one frame
        i0 = int(t * SR)
        if kind == "blip":
            dur = 0.035
            f = 760 + 120 * rng.integers(0, 4)
            amp = 0.10
            env_len = int(dur * SR)
            tt = np.arange(env_len) / SR
            env = np.exp(-tt / 0.012) * np.minimum(1, tt / 0.002)
            w = amp * env * np.sin(2 * math.pi * f * tt)
        else:
            dur = 0.9
            tt = np.arange(int(dur * SR)) / SR
            env = np.exp(-tt / 0.28) * np.minimum(1, tt / 0.004)
            w = 0.16 * env * (np.sin(2 * math.pi * 1046.5 * tt) + 0.6 * np.sin(2 * math.pi * 1318.5 * tt)
                              + 0.25 * np.sin(2 * math.pi * 2093.0 * tt))
        i1 = min(n, i0 + len(w))
        out[i0:i1] += w[: i1 - i0]
    fade = int((DURATION - T_FADE) * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(out)) or 1.0
    out = out / peak * 0.5
    stereo = np.stack([out, out], axis=1)
    return (stereo * 32767).astype(np.int16)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="", help="suffix for the output names")
    args = ap.parse_args()
    wide, portraits = render_stills()
    frames, events = make_frames(wide, portraits)
    silent = OUT_DIR / f"intro{args.tag}_silent.mp4"
    v = Video(silent)
    for f in frames:
        v.add(f)
    v.close()
    wav = OUT_DIR / f"intro{args.tag}.wav"
    pcm = make_sound(events)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    final = OUT_DIR / f"intro{args.tag}.mp4"
    res = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav),
                          "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(final)])
    print(f"wrote {final} ({len(frames)} frames, {len(frames) / VIDEO_FPS:.1f} s, ffmpeg rc={res.returncode})")
    still_dir = OUT_DIR / f"intro{args.tag}_stills"
    still_dir.mkdir(exist_ok=True)
    for t in (6.6, 10.9, 14.0):
        Image.fromarray(frames[int(t * VIDEO_FPS)]).save(still_dir / f"t{t:04.1f}.png")
    return 0 if res.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
