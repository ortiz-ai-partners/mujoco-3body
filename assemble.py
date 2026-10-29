"""Join the submission video: the course's opening card, the self-introduction, the main video and the course's end
card, with an optional background-music track mixed under the robots' voices at a constant level.

Everything is scaled to 1280x720 at 30 fps.  Clips without sound (the course's cards) get silence.  The music starts
where the course's opening card ends (or at --bgm-start seconds of the joined video).  By default it is faded out at
the end of the main video; --bgm-until end plays the file as it is (with its own ending) up to the end of the video.
--duck lowers the music while the robots speak (the earlier drafts; the submission keeps the music level constant).

    python assemble.py --op <op.mp4> --intro out/intro.mp4 --main out/3body_arena_v7_take56.mp4 --ed <ed.mp4> \
        --out out/submission.mp4 [--bgm music.wav --bgm-gain -18 --bgm-until end --bgm-fade 0]

The course's cards are not part of this repository (they belong to the course); pass their paths.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1280, 720, 30


def probe(path):
    """(duration in s, has_audio) from ffmpeg's banner."""
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stderr
    dur = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            h, m, s = line.split(",")[0].split()[1].split(":")
            dur = int(h) * 3600 + int(m) * 60 + float(s)
    return dur, ("Audio:" in out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--op", required=True)
    ap.add_argument("--intro", required=True)
    ap.add_argument("--main", required=True)
    ap.add_argument("--ed", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bgm", help="background music (wav); placed from --bgm-start and faded out at the main video's end")
    ap.add_argument("--bgm-start", type=float, default=None, help="seconds of the joined video where the music starts "
                    "(default: the start of the introduction)")
    ap.add_argument("--bgm-gain", type=float, default=-16.0, help="music level in dB before ducking")
    ap.add_argument("--bgm-fade", type=float, default=2.5, help="fade-out length in s, ending where the music stops (0: none)")
    ap.add_argument("--bgm-until", choices=["main", "end"], default="main",
                    help="where the music stops: the main video's end (default) or the end of the joined video")
    ap.add_argument("--duck", action="store_true", help="lower the music while the robots speak (sidechain)")
    args = ap.parse_args()

    clips = [args.op, args.intro, args.main, args.ed]
    info = [probe(c) for c in clips]
    for c, (d, a) in zip(clips, info):
        if d is None:
            sys.exit(f"cannot read {c}")
    starts, t = [], 0.0
    for d, _ in info:
        starts.append(t)
        t += d
    total = t
    main_end = starts[2] + info[2][0]

    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", c]
    fc = []
    for i, (d, has_a) in enumerate(info):
        fc.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
                  f"fps={FPS},format=yuv420p,setsar=1,trim=duration={d:.3f},setpts=PTS-STARTPTS[v{i}]")
        if has_a:
            fc.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=duration={d:.3f},"
                      f"asetpts=PTS-STARTPTS[a{i}]")
        else:
            fc.append(f"anullsrc=r=44100:cl=stereo,atrim=duration={d:.3f}[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i in range(4)) + "concat=n=4:v=1:a=1[v][voice]")
    out_a = "[voice]"
    if args.bgm:
        cmd += ["-i", args.bgm]
        start = starts[1] if args.bgm_start is None else args.bgm_start
        length = (main_end if args.bgm_until == "main" else total) - start
        fade = (f"afade=t=out:st={max(0.0, length - args.bgm_fade):.3f}:d={args.bgm_fade:.3f},"
                if args.bgm_fade > 0 else "")
        ms = int(round(start * 1000))
        fc.append(f"[4:a]aresample=44100,aformat=channel_layouts=stereo,atrim=duration={length:.3f},"
                  f"{fade}volume={args.bgm_gain}dB,adelay={ms}|{ms},apad=whole_dur={total:.3f}[bgm]")
        if args.duck:
            fc.append("[voice]asplit=2[voice1][key]")
            fc.append("[bgm][key]sidechaincompress=threshold=0.02:ratio=6:attack=8:release=350:makeup=1[ducked]")
            fc.append("[voice1][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[mix]")
        else:                                                  # constant music level under the voices
            fc.append("[voice][bgm]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[mix]")
        out_a = "[mix]"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", out_a,
            "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", args.out]
    res = subprocess.run(cmd)
    summary = {"out": args.out, "total_s": round(total, 2),
               "parts": [{"clip": c, "start_s": round(s, 2), "duration_s": round(d, 2)} for c, s, (d, _) in zip(clips, starts, info)],
               "bgm": args.bgm, "bgm_gain_db": args.bgm_gain if args.bgm else None,
               "bgm_until": args.bgm_until if args.bgm else None, "duck": bool(args.bgm and args.duck),
               "ffmpeg_rc": res.returncode}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
