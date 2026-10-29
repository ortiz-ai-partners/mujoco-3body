"""Does the render-only face change the physics path?  Compare two headless story reports.

    python analysis/face_check.py out/v7_full_report_facecheck_A.json out/v7_full_report_facecheck_B.json

A: v7_full.py --test --no-face, B: the same with the face (the default).  The screen geom (contype 0, density 0) and the
face camera add no mass, contacts or joints, so every event, every manager decision, the robots' mode changes and the
final state digest (sha256 of qpos+qvel) must be identical; only ngeom differs by one.  Exit code 1 if anything differs.
"""
from __future__ import annotations

import json
import sys


def events(r):
    # the jump-cut notes are about the video, not the physics: left out of the comparison
    return [(e["t"], e["event"]) for e in r["events"] if not e["event"].startswith("JUMP CUT")]


def decisions(r):
    return [{k: v for k, v in d.items() if k != "video_t"} for d in r["manager"]["decisions"]]


def main(pa, pb):
    a, b = (json.load(open(p, encoding="utf-8")) for p in (pa, pb))
    # a report from before the face (takes up to 29) has no state_digest / ngeom / face: those checks read n/a
    has_digest = "state_digest" in a and "state_digest" in b
    checks = {
        "sim_seconds": a["sim_seconds"] == b["sim_seconds"],
        "state_digest (sha256 of qpos+qvel at the end)": a["state_digest"] == b["state_digest"] if has_digest else None,
        "events (t, text)": events(a) == events(b),
        "manager decisions": decisions(a) == decisions(b),
        "duck mode changes": a["md_events"] == b["md_events"],
        "crab mode changes": a["jp_events"] == b["jp_events"],
        "three crossed": a["three_crossed"] == b["three_crossed"],
        "course disturbed": a["course_disturbed"] == b["course_disturbed"],
    }
    for tag, r in (("A", a), ("B", b)):
        face = r.get("face", {}).get("on")
        print(f"{tag}: face {'on' if face else 'off' if face is not None else 'n/a (older report)'}, ngeom {r.get('ngeom', 'n/a')}, "
              f"{r['sim_seconds']} s, {len(r['events'])} events, {len(r['manager']['decisions'])} decisions, "
              f"digest {r['state_digest'][:16] if 'state_digest' in r else 'n/a'}")
    ok = True
    for name, same in checks.items():
        print(f"  {'n/a    ' if same is None else 'same   ' if same else 'DIFFERS'}  {name}")
        ok &= same is not False
    if "ngeom" in a and "ngeom" in b:
        print(f"  {'differs by one (the screen)' if b['ngeom'] - a['ngeom'] == 1 else 'same' if a['ngeom'] == b['ngeom'] else 'UNEXPECTED'}  "
              f"ngeom {a['ngeom']} -> {b['ngeom']}")
    if events(a) != events(b):
        for x, y in zip(events(a), events(b)):
            if x != y:
                print(f"  first difference: A {x}  B {y}")
                break
    log = next((r["face"]["log"] for r in (b, a) if r.get("face", {}).get("on")), None) or []
    print(f"face timeline: {len(log)} changes")
    for t, expr, reason in log:
        print(f"    {t:7.2f}s  {expr:8s} {reason}")
    print("VERDICT:", "identical physics path" if ok else "THE PATHS DIFFER")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
