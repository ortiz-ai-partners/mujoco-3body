"""The crab-assisted crossing: skills the manager can call, shared by the learning environment
(manager2_env.py) and the story (v7_full.py).

ゆうころ (2026-10-28): the bulldozer must not handle the duck (lifting by the neck could break it);
the crab helps instead - "a beautiful friendship".  Experiment v7_test_crab_push.py (same night):
the seated duck, FACING the crab, pushed at 0.3 m/s with the crab's body at its neutral height,
climbs the 16-degree ramp leaning only 6-12 degrees, survives the crest, stands up on the landing
once the crab has backed off, and walks across and down by itself (crossed at 86.6 s).  Seated
facing uphill it leans 40 degrees back onto the crab and topples at the crest; standing it is
knocked over at the first contact.

Every skill is a generator: it sets commands for the duck (official velstand / sitstand policies)
and the crab (official locomotion policy), yields once per control tick (the owner steps the
physics), and finally returns a result string.  Physics only - nothing is ever moved by hand.

Actions (and the fixed line the manager's speech bubble shows):
  0 WAIT      「ちょっと待とう」                           4 s, everybody holds (a fallen duck gets up by itself)
  1 SEAT      「パッカン、カニさんの方を向いて座って」       stand if needed, walk to the seat at the ramp's foot,
                                                        turn to face south (the crab's side), sit
  2 PUSH      「カニさん、そっと押し上げてあげて」           the crab gets behind the duck in the lane, closes in
                                                        gently, pushes at 0.3 m/s until the landing, settles
  3 BACK_OFF  「カニさん、少し離れて」                      the crab reverses until 0.6 m clear (a fallen or
                                                        seated duck needs room to get up)
  4 STANDUP   「パッカン、立てる？」                        sitstand flag 0 -> velstand; a fallen duck: wait for
                                                        velstand's own recovery
  5 WALK_ON   「パッカン、そのまま進んで」                   the duck walks north along the lane: across the
                                                        landing, down the far ramp, onto the floor
"""
from __future__ import annotations

import math

import numpy as np

from v6_robots import robots_in_contact
from v7_full import CONTROL_DT, wrap

# ── the course along the lane (out/v6_stage_built.xml, world frame) ─────────
LANE_X = 1.45                      # the push / walk line: the course's centre (x 0.98-1.98).  The story's duck lane
                                   # (1.22) is 24 cm from the west edge: pushing there the crab's left feet stood on
                                   # the edge (stalled pushes), and after a trip on the landing the duck walked off
                                   # the west side and dropped 0.44 m (headless take-6 test, 10/28)
TOE_Y = -2.0                       # the up-ramp's toe
CREST_Y = -0.495                   # top edge of the up-ramp (landing surface z = 0.44)
DECK_N_Y = 0.548                   # top edge of the down-ramp
DOWN_TOE_Y = 2.05                  # the down-ramp's toe
SEAT_Y = TOE_Y - 0.35              # where the duck sits to be pushed
FACE_SOUTH = -math.pi / 2          # the duck faces the crab: back to the slope
FACING_TOL = math.radians(15.0)
CRAB_PUSH_VX = 0.3                 # the only speed that climbed (0.2 leaned and fell, 0.4 fell, 0.5 fell)
WALK_VX = 0.3                      # the duck's walking speed on the ramps and the floor
WALK_DECK_VX = 0.3                 # across the landing (the seam between the two deck pieces trips it either way:
                                   # 6-seed sweep 10/28, 0.2 m/s crossed 3/6, 0.3 m/s 4/6)

ACTIONS = ["WAIT", "SEAT", "PUSH", "BACK_OFF", "STANDUP", "WALK_ON"]
LINES = {
    "WAIT": "ちょっと待とう",
    "SEAT": "パッカン、カニさんの方を向いて座って",
    "PUSH": "カニさん、そっと押し上げてあげて",
    "PUSH_RETRY": "もう一回いこう。カニさん、そっと押し上げてあげて",
    "BACK_OFF": "カニさん、少し離れて",
    "STANDUP": "パッカン、立てる？",
    "WALK_ON": "パッカン、そのまま進んで",
}
RESULT_SLOTS = ["none", "waited", "seated", "pushed_up", "fell", "stalled", "slipped", "cleared", "standing",
                "still_down", "crossed", "walked", "nothing"]
STAGES = ["toe", "ramp_up", "deck", "ramp_down", "north", "beside"]
OBS_DIM = 3 + 2 + 4 + 2 + len(STAGES) + 7 + len(RESULT_SLOTS) + len(ACTIONS) + 3


def now(h):
    return float(h.data.time)


def course_z(y):
    """Height of the course surface on its centre line at world y (0 off the course)."""
    if TOE_Y <= y <= CREST_Y:
        return 0.44 * (y - TOE_Y) / (CREST_Y - TOE_Y)
    if CREST_Y < y < DECK_N_Y:
        return 0.44
    if DECK_N_Y <= y <= DOWN_TOE_Y:
        return 0.44 * (DOWN_TOE_Y - y) / (DOWN_TOE_Y - DECK_N_Y)
    return 0.0


def reverse_command(h, vx=-0.3):
    """Reverse the crab straight down the line: heading held north, lateral drift corrected toward the line
    (a plain reverse from the crest drifted 14 cm west and the crab later walked off the ramp's edge)."""
    q = h.crab_xyz()
    e_yaw = wrap(math.pi / 2 - h.crab.yaw(h.data))
    e_lat = LANE_X - q[0]
    h.crab.loco.set_command(vx, float(np.clip(-1.0 * e_lat, -0.1, 0.1)), float(np.clip(2.0 * e_yaw, -0.8, 0.8)))


class Helpers:
    """What the skills and the observation read from the simulator (true state, as an overhead camera would see)."""

    def __init__(self, model, data, duck, crab):
        self.model, self.data, self.duck, self.crab = model, data, duck, crab
        self.md_root = int(model.body_rootid[duck.bid])
        self.jp_root = int(model.body_rootid[crab.bid])

    def touching(self):
        return robots_in_contact(self.model, self.data, self.md_root, self.jp_root)

    def duck_xyz(self):
        return np.array(self.duck.pos(self.data), dtype=float)

    def crab_xyz(self):
        return np.array(self.crab.pos(self.data), dtype=float)

    def tilt(self):
        return float(self.duck.tilt(self.data))

    def facing_err(self):
        return wrap(self.duck.yaw(self.data) - FACE_SOUTH)

    def facing_ok(self):
        return abs(self.facing_err()) < FACING_TOL

    def crab_dist(self):
        return float(np.linalg.norm(self.duck_xyz()[:2] - self.crab_xyz()[:2]))

    def stage(self):
        x, y, z = self.duck_xyz()
        if TOE_Y + 0.05 < y < DOWN_TOE_Y - 0.05 and (abs(x - LANE_X) > 0.5 or z < course_z(y) - 0.10):
            return "beside"                                  # off the side of the course, on the floor
        if y >= DOWN_TOE_Y + 0.05 or (y >= DOWN_TOE_Y - 0.1 and z < 0.2):
            return "north"
        if y >= DECK_N_Y - 0.03:
            return "ramp_down"
        if y >= CREST_Y + 0.03:
            return "deck"
        if y >= TOE_Y + 0.03 and z > 0.09:
            return "ramp_up"
        return "toe"

    def duck_up(self):
        return self.duck.mode in ("STAND", "WALK", "WALK_ON", "TURN") and self.tilt() < 15.0

    def crossed(self):
        return self.stage() == "north" and self.duck_up()


def hold_seated(h):
    """The sitstand policy keeps sitting only while its flag is held (every tick while seated)."""
    if h.duck.mode == "SIT":
        h.duck.sit.twist[:] = (1.0, 0.0, 0.0)


def check_seated_fall(h):
    """Tipped while seated: velstand takes over (Duck.control only watches the standing modes).  Returns True once."""
    d = h.duck
    if d.mode == "SIT" and h.tilt() > 60.0:
        d.resume, d.fell_at, d.upright_since = "STAND", now(h), None
        d.use("vel")
        d.set_mode("FALLEN", now(h))
        return True
    return False


def _hold(h, seconds):
    t0 = now(h)
    while now(h) - t0 < seconds:
        hold_seated(h)
        yield


# ── skills ───────────────────────────────────────────────────────────────────
def skill_wait(h, seconds=4.0):
    h.crab.loco.set_command(0, 0, 0)
    yield from _hold(h, seconds)
    return "waited"


def skill_seat(h, max_s=32.0):
    """Get up if seated, wait if fallen, walk to the seat at the ramp's foot when far from it, turn to face
    south (the crab comes from there), sit down.  Result: seated / fell / still_down / nothing."""
    d = h.duck
    h.crab.loco.set_command(0, 0, 0)
    t0 = now(h)
    if d.mode == "SIT":
        d.sit.twist[:] = 0                                   # sitstand flag 0: stand up
        d.sit.head[:] = 0
        t1 = now(h)
        while now(h) - t1 < 3.5:
            d.sit.twist[:] = 0
            yield
        d.use("vel")
        d.set_mode("STAND", now(h))
    while d.mode == "FALLEN" and now(h) - t0 < 10.0:        # velstand gets it up by itself if nothing blocks it
        yield
    if d.mode == "FALLEN":
        return "still_down"
    for _ in range(int(1.0 / CONTROL_DT)):                   # on its feet: a moment to steady
        yield
    p = h.duck_xyz()
    if h.stage() in ("toe", "beside") and float(np.linalg.norm(p[:2] - (LANE_X, SEAT_Y))) > 0.30:
        goals = [(LANE_X, SEAT_Y)]
        if h.stage() == "beside":                            # off the course's side: round its foot, never up its side
            side = 1.0 if p[0] >= LANE_X else -1.0
            goals.insert(0, (LANE_X + 0.9 * side, SEAT_Y - 0.1))
        for g in goals:
            d.walk_to(g, now(h), stop_dist=0.22)
            while d.mode in ("WALK", "FALLEN") and now(h) - t0 < max_s - 9.0:
                yield
    d.use("vel")
    d.set_mode("TURN", now(h))
    ok_since = None
    while now(h) - t0 < max_s - 4.0:
        if d.mode == "FALLEN":
            yield
            continue
        if d.mode != "TURN":
            d.set_mode("TURN", now(h))
        err = h.facing_err()
        # velstand needs at least ~0.35 rad/s to turn at all (the story's TURN); within 2.3 deg hold still.
        # The push is sensitive to the facing: 6 deg off, the crab's push drifts the duck sideways and it
        # tips at the ramp's toe (debug 10/28, seed 1000), so the re-seat aims tighter than the 4.6 deg before.
        wz = 0.0 if abs(err) < 0.04 else math.copysign(min(1.0, max(0.35, 2.5 * abs(err))), -err)
        d.pol.twist[:] = (0.0, 0.0, wz)
        if abs(err) < 0.04:
            ok_since = ok_since if ok_since is not None else now(h)
            if now(h) - ok_since > 0.5:
                break
        else:
            ok_since = None
        yield
    d.pol.twist[:] = 0
    if d.mode == "FALLEN":
        return "fell"
    d.use("sit")
    d.set_mode("SIT", now(h))
    d.sit.twist[:] = (1.0, 0.0, 0.0)
    d.sit.head[:] = (0.3, 0.2, 0.0, 0.0)
    t1 = now(h)
    while now(h) - t1 < 2.5:
        hold_seated(h)
        yield
    if d.mode == "FALLEN":
        return "fell"
    return "seated" if (d.mode == "SIT" and h.facing_ok() and h.tilt() < 25.0) else "nothing"


def skill_push(h, max_s=90.0, vx=CRAB_PUSH_VX):
    """The crab gets behind the duck in the lane (swinging out to the side if it is in front), closes in at
    0.12 m/s until it touches, pushes at `vx` until the duck is on the landing, then a gentle push until the
    duck sits upright.  Result: pushed_up / fell / stalled / slipped / nothing (never pushes a fallen duck)."""
    d, c = h.duck, h.crab
    t0 = now(h)
    if d.mode == "FALLEN":
        c.loco.set_command(0, 0, 0)
        yield from _hold(h, 1.5)
        return "nothing"
    if c.mode != "WALK":
        c.set_mode("WALK", now(h), h.model)
    c.loco.posture[3] = 0.0                                  # neutral body height: the only height that climbs
    phase, t_phase = "behind", now(h)
    y_best, t_best = h.duck_xyz()[1], now(h)
    settle_t0 = None
    while now(h) - t0 < max_s:
        hold_seated(h)
        h.push_phase = phase                                 # for the logs: where a push ended
        p, q = h.duck_xyz(), h.crab_xyz()
        if d.mode == "FALLEN":
            c.loco.set_command(0, 0, 0)
            yield from _hold(h, 0.5)
            return "fell"
        if abs(p[0] - LANE_X) > 0.45 and p[2] > 0.1 and phase in ("push", "settle"):
            c.loco.set_command(0, 0, 0)                      # the duck is sliding off the side
            yield from _hold(h, 0.5)
            return "slipped"
        # the push line is the duck's own line (clipped to the course's middle), not the lane's centre: aiming at
        # the lane while the duck sat 3 cm off it drifted the duck sideways and tipped it at the toe (debug 10/28)
        tx = float(np.clip(p[0], LANE_X - 0.2, LANE_X + 0.2))
        if phase == "behind":
            B = np.array([tx, p[1] - 0.60])
            side = 1.0 if q[0] >= LANE_X else -1.0
            beside_course = (TOE_Y - 0.3 < q[1] < DOWN_TOE_Y + 0.3) and abs(q[0] - LANE_X) > 0.45
            if beside_course:                                # on the floor beside the course: round its foot first
                dist, _ = c.steer(h.data, (LANE_X + 0.9 * side, TOE_Y - 0.9), 0.3)
            elif q[1] > p[1] - 0.30 and p[1] < TOE_Y + 0.1:  # in front of / beside the duck at the foot: swing out
                dist, _ = c.steer(h.data, (LANE_X + 0.85 * side, p[1] - 0.75), 0.3)
            elif q[1] > p[1] - 0.30:                         # on the course ahead of the duck: back down past it
                reverse_command(h)
            else:
                dist, _ = c.steer(h.data, B, 0.3)
                if dist < 0.20:
                    phase, t_phase = "align", now(h)
            if now(h) - t_phase > 40.0:
                c.loco.set_command(0, 0, 0)
                yield from _hold(h, 0.5)
                return "stalled"
        elif phase == "align":
            # square up before touching: heading north, on the duck's line, 0.6 m behind.  A crab that starts
            # the push 10-20 cm off the line turns in place instead of walking (its steering gives no forward
            # speed beyond 0.4 rad of bearing error) and the push stalls (smoke 10/28, seeds 1000/1002).
            e_yaw = wrap(math.pi / 2 - c.yaw(h.data))
            e_lat = tx - q[0]                                # + : the line is to the crab's right (it faces north)
            e_fwd = (p[1] - 0.60) - q[1]
            c.loco.set_command(float(np.clip(1.0 * e_fwd, -0.15, 0.15)), float(np.clip(-1.5 * e_lat, -0.15, 0.15)),
                               float(np.clip(3.0 * e_yaw, -1.0, 1.0)))
            if abs(e_yaw) < 0.08 and abs(e_lat) < 0.03 and abs(e_fwd) < 0.15:
                phase, t_phase = "approach", now(h)
            elif now(h) - t_phase > 15.0:
                c.loco.set_command(0, 0, 0)
                yield from _hold(h, 0.5)
                return "stalled"
        elif phase == "approach":
            c.steer(h.data, (tx, p[1] + 0.15), 0.12)         # close the gap gently
            if h.touching():
                phase, t_phase = "push", now(h)
                y_best, t_best = p[1], now(h)
            elif now(h) - t_phase > 14.0:
                c.loco.set_command(0, 0, 0)
                yield from _hold(h, 0.5)
                return "stalled"
        elif phase == "push":
            # push at `vx` only while in contact; after losing contact close in again at 0.12 (the experiment's
            # rule).  Keeping 0.3 through a lost contact rammed the duck at the ramp's lip: 8/8 toppled at
            # y -1.95 in the 10/28 sweep, whatever the facing or the lateral offset
            c.steer(h.data, (tx, p[1] + 0.15), vx if h.touching() else 0.12)
            if p[1] > CREST_Y + 0.07 and p[2] > 0.45:
                phase, t_phase = "settle", now(h)
            if p[1] > y_best + 0.03:
                y_best, t_best = p[1], now(h)
            elif now(h) - t_best > 15.0:
                c.loco.set_command(0, 0, 0)
                yield from _hold(h, 0.5)
                return "stalled"
            if abs(q[0] - LANE_X) > 0.42 or (q[2] < p[2] - 0.30 and p[2] > 0.2):
                c.loco.set_command(0, 0, 0)                  # the crab is off the lane / fell off the ramp
                yield from _hold(h, 0.5)
                return "slipped"
        elif phase == "settle":
            c.steer(h.data, (tx, p[1] + 0.15), 0.12)         # a last gentle push until it sits upright
            if (h.tilt() < 15.0 and now(h) - t_phase > 1.0) or now(h) - t_phase > 4.0:
                c.loco.set_command(0, 0, 0)
                yield from _hold(h, 0.5)
                return "pushed_up"
        yield
    c.loco.set_command(0, 0, 0)
    yield from _hold(h, 0.5)
    return "stalled"


def skill_back_off(h, max_s=7.0, clearance=0.6):
    """The crab reverses straight back until it is `clearance` from the duck and not touching it."""
    c = h.crab
    if c.mode != "WALK":
        c.set_mode("WALK", now(h), h.model)
    if h.crab_dist() > clearance and not h.touching():
        c.loco.set_command(0, 0, 0)
        yield from _hold(h, 1.0)
        return "nothing"
    t0 = now(h)
    while now(h) - t0 < max_s:
        hold_seated(h)
        reverse_command(h)
        if h.crab_dist() > clearance and not h.touching():
            break
        yield
    c.loco.set_command(0, 0, 0)
    yield from _hold(h, 0.6)
    return "cleared" if (h.crab_dist() > clearance and not h.touching()) else "stalled"


def skill_standup(h, max_s=16.0):
    """Seated: sitstand flag 0, then velstand.  Fallen: velstand's own recovery.  Result: standing / still_down / fell / nothing."""
    d = h.duck
    h.crab.loco.set_command(0, 0, 0)
    if h.duck_up():
        yield from _hold(h, 1.0)
        return "nothing"
    t0 = now(h)
    if d.mode == "SIT":
        d.sit.twist[:] = 0
        d.sit.head[:] = 0
        while now(h) - t0 < 3.5:
            d.sit.twist[:] = 0
            yield
        if d.mode == "SIT":
            d.use("vel")
            d.set_mode("STAND", now(h))
    t1 = now(h)
    while now(h) - t0 < max_s:
        if d.mode == "STAND" and h.tilt() < 15.0 and now(h) - t1 > 2.0:
            break
        yield
    if d.mode == "FALLEN":
        return "still_down"
    return "standing" if h.duck_up() else "fell"


def skill_walk_on(h, max_s=30.0):
    """The duck walks north along the course's centre line (velstand, 0.3 m/s; 0.2 across the landing); the crab
    holds still.  Result: crossed / walked / stalled / nothing (not on its feet)."""
    d, c = h.duck, h.crab
    if not h.duck_up():
        c.loco.set_command(0, 0, 0)
        yield from _hold(h, 1.0)
        return "nothing"
    t0 = now(h)
    y0 = h.duck_xyz()[1]
    y_best, t_best = y0, now(h)
    d.use("vel")
    d.set_mode("WALK_ON", now(h))                            # steered here each tick (Duck.control leaves this mode alone)
    while now(h) - t0 < max_s:
        p, q = h.duck_xyz(), h.crab_xyz()
        if d.mode == "STAND":                                # back on its feet after a fall: carry on
            d.set_mode("WALK_ON", now(h))
        if d.mode == "WALK_ON":
            d.steer(h.data, (LANE_X, p[1] + 1.0), vx=(WALK_DECK_VX if h.stage() == "deck" else WALK_VX))
        c.loco.set_command(0, 0, 0)                          # the crab holds: following up the ramp took it off the edge
        if h.crossed():
            d.pol.twist[:] = 0
            d.set_mode("STAND", now(h))
            c.loco.set_command(0, 0, 0)
            return "crossed"
        if p[1] > y_best + 0.02:
            y_best, t_best = p[1], now(h)
        elif now(h) - t_best > 10.0 and d.mode != "FALLEN":
            break
        yield
    if d.mode in ("WALK", "WALK_ON", "STAND"):
        d.pol.twist[:] = 0
        d.set_mode("STAND", now(h))
    c.loco.set_command(0, 0, 0)
    return "walked" if h.duck_xyz()[1] > y0 + 0.2 else "stalled"


SKILLS = {"WAIT": skill_wait, "SEAT": skill_seat, "PUSH": skill_push, "BACK_OFF": skill_back_off,
          "STANDUP": skill_standup, "WALK_ON": skill_walk_on}


# ── what the manager sees ────────────────────────────────────────────────────
def observation(h, book):
    """45 floats.  `book` carries the bookkeeping: last_result, last_action, pushes, t0_episode, course_damage,
    course_tolerance."""
    p, q = h.duck_xyz(), h.crab_xyz()
    d = h.duck
    mode = d.mode
    since_fall = (now(h) - d.fell_at) if (mode == "FALLEN" and d.fell_at is not None) else 0.0
    e = h.facing_err()
    yaw_c = h.crab.yaw(h.data) - math.pi / 2                 # the crab's heading against north (the push direction)
    stage = h.stage()
    obs = [
        (p[0] - LANE_X) / 0.5, (p[1] - TOE_Y) / 2.0, p[2] * 2.0,
        math.sin(e), math.cos(e),
        float(mode == "SIT"), float(mode in ("STAND", "TURN")), float(mode == "FALLEN"), float(mode in ("WALK", "WALK_ON")),
        h.tilt() / 90.0, min(since_fall, 10.0) / 10.0,
    ]
    obs += [float(stage == s) for s in STAGES]
    obs += [(q[0] - LANE_X) / 0.5, (q[1] - p[1]) / 1.5, h.crab_dist() / 2.0, float(h.touching()), q[2] * 2.0,
            math.sin(yaw_c), math.cos(yaw_c)]
    res = [0.0] * len(RESULT_SLOTS)
    res[RESULT_SLOTS.index(book.last_result if book.last_result in RESULT_SLOTS else "none")] = 1.0
    act = [0.0] * len(ACTIONS)
    if book.last_action is not None:
        act[book.last_action] = 1.0
    obs += res + act + [min(book.pushes, 3) / 3.0, min(now(h) - book.t0_episode, 240.0) / 240.0,
                        min(book.course_damage, book.course_tolerance) / book.course_tolerance]
    assert len(obs) == OBS_DIM, len(obs)
    return np.asarray(obs, dtype=np.float32)


def bubble_line(action, book):
    name = ACTIONS[action]
    if name == "PUSH" and book.pushes > 0:
        return LINES["PUSH_RETRY"]
    return LINES[name]


# ── the fixed-rule manager (baseline, and the story's fallback) ──────────────
def rule_action(h, book):
    """Fixed rules written from the experiments: a fallen duck needs room, then time; on the landing it stands
    and walks; at the foot it sits facing the crab, then the crab pushes; after a stalled push the crab backs
    off and the duck re-seats."""
    d = h.duck
    stage = h.stage()
    close = h.touching() or h.crab_dist() < 0.5
    if d.mode == "FALLEN":
        return ACTIONS.index("BACK_OFF" if close else "WAIT")
    if stage == "north":
        return ACTIONS.index("WAIT")
    if stage in ("deck", "ramp_down"):
        if d.mode == "SIT":
            return ACTIONS.index("BACK_OFF" if close else "STANDUP")
        return ACTIONS.index("WALK_ON")
    # at the foot, on the up-ramp, or beside the course
    if book.last_result in ("stalled", "slipped") and close:
        return ACTIONS.index("BACK_OFF")
    if d.mode == "SIT" and h.facing_ok() and stage in ("toe", "ramp_up"):
        return ACTIONS.index("PUSH")
    return ACTIONS.index("SEAT")
