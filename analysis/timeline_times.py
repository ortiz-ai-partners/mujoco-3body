"""Video-time table of a rendered take, for the report's timeline figure (the submitted render shows the construction
at 4x with no jump cuts, so the figure is read off that render's times).

Reads out/v7_full_report_<tag>.json and prints, in video time (m:ss.s) and simulated seconds:
  * the speed segments (inferred from consecutive events: sim seconds per video second),
  * the stage changes and the story events (crossings, the manager's decisions, the circle),
  * the crab's face log mapped to video time (the log is in simulated seconds; the mapping interpolates between the
    events' (t, video_t) anchors, which include every stage change and the dance start, so it is exact up to a frame).
With --compare it prints the same table for a second take and the video-time shift of each shared event, and ends with
the line 'state_digest equal: True/False'.  Headless (--test) reports work too: their video times are all 0:00.0, and a
report without the face (face.log null) or with the older 3-element face rows prints a shorter face section.

    python analysis/timeline_times.py out/v7_full_report_take51.json --compare out/v7_full_report_take46.json
"""
from __future__ import annotations

import argparse
import bisect
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")


def mmss(v):
    return f"{int(v // 60)}:{v % 60:04.1f}"


class Mapping:
    """sim time -> video time, piecewise linear between the report's events."""

    def __init__(self, report):
        pts = sorted({(0.0, 0.0)} | {(e["t"], e["video_t"]) for e in report["events"]})
        self.t = [p[0] for p in pts]
        self.v = [p[1] for p in pts]

    def __call__(self, t):
        i = bisect.bisect_right(self.t, t) - 1
        if i >= len(self.t) - 1:
            return self.v[-1] + (t - self.t[-1]) / self.speed_after(len(self.t) - 1)
        t0, t1, v0, v1 = self.t[i], self.t[i + 1], self.v[i], self.v[i + 1]
        if t1 == t0 or v1 == v0:
            return v1
        return v0 + (t - t0) * (v1 - v0) / (t1 - t0)

    def speed_after(self, i):
        j = i
        while j > 0 and (self.v[j] - self.v[j - 1]) <= 0:
            j -= 1
        if j == 0:
            return 2.0
        return (self.t[j] - self.t[j - 1]) / (self.v[j] - self.v[j - 1])

    def segments(self):
        """[(video_from, video_to, speed)]: the speed (sim seconds per video second, to the nearest 0.5) over stretches of
        at least half a video second, merged where it stays the same.  A stretch whose ratio is far above the video speeds
        in use contains a jump cut; it is reported as 'cut (N s of sim not shown)'."""
        out, i0 = [], 0
        for i in range(1, len(self.t)):
            dv, dt = self.v[i] - self.v[i0], self.t[i] - self.t[i0]
            if dv < 0.5 and i < len(self.t) - 1:
                continue                                    # too short to measure; take it with the next stretch
            if dv <= 0:
                i0 = i
                continue
            ratio = dt / dv
            sp = f"cut ({dt - dv * 2:.0f} s of sim not shown)" if ratio > 8.5 else f"x{round(ratio * 2) / 2:g}"
            if out and out[-1][2] == sp:
                out[-1] = (out[-1][0], self.v[i], sp)
            else:
                out.append((self.v[i0], self.v[i], sp))
            i0 = i
        return out


KEY = ("stage ->", "crossed", "JUMP CUT", "manager", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON", "circle",
       "dance", "jump", "landed", "seated", "pushed_up", "cleared", "standing", "gives up", "sits", "over the top",
       "calls", "heads back", "fork")


def table(report, m, title):
    print(f"\n=== {title} ===")
    print("speed segments (video from-to, sim seconds per video second):")
    for a, b, sp in m.segments():
        print(f"  {mmss(a)} - {mmss(b)}  {sp}")
    print("\nevents (video  sim  text):")
    for e in report["events"]:
        txt = e["event"]
        if any(k.lower() in txt.lower() for k in KEY):
            print(f"  {mmss(e['video_t']):>7}  {e['t']:7.2f}  {txt}")
    dec = report.get("manager", {}).get("decisions")
    if dec:
        print("\nmanager decisions:")
        for d in dec:
            t = d.get("t") if isinstance(d, dict) else None
            print(f"  {mmss(m(t)) if t is not None else '?':>7}  {t if t is not None else '?':>7}  {json.dumps(d, ensure_ascii=False)[:160]}")
    face = report.get("face")
    log = face.get("log") if isinstance(face, dict) else face
    if not log:
        print("\nface log: none (run without the face)")
    else:
        # rows are [t, face, reason] in older reports and [t, face, reason, rule, values] in current ones
        print("\nface log (video  sim  face  reason  rule):")
        for row in log:
            t, expr, reason = row[0], row[1], row[2]
            rule = f"  (rule {row[3]})" if len(row) > 3 else ""
            print(f"  {mmss(m(t)):>7}  {t:7.2f}  {expr:<15} {reason}{rule}")
    last = report["events"][-1]
    print(f"\nlast event at video {mmss(last['video_t'])} (sim {last['t']:.2f} s); sim_seconds {report['sim_seconds']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--compare", help="another take's report: print its table and the per-event video-time shift")
    args = ap.parse_args()
    r = json.load(open(args.report, encoding="utf-8"))
    m = Mapping(r)
    table(r, m, args.report)
    if args.compare:
        r2 = json.load(open(args.compare, encoding="utf-8"))
        m2 = Mapping(r2)
        table(r2, m2, args.compare)
        print("\n=== shift (first minus second) for shared events ===")
        by2 = {(round(e["t"], 2), e["event"]): e["video_t"] for e in r2["events"]}
        for e in r["events"]:
            k = (round(e["t"], 2), e["event"])
            if k in by2 and any(x.lower() in e["event"].lower() for x in KEY):
                print(f"  {mmss(e['video_t']):>7} vs {mmss(by2[k]):>7}  {e['video_t'] - by2[k]:+6.2f} s  {e['event'][:70]}")
        same = r["state_digest"] == r2["state_digest"]
        print(f"\nstate_digest equal: {same}  ({r['state_digest'][:12]} / {r2['state_digest'][:12]})")


if __name__ == "__main__":
    main()
