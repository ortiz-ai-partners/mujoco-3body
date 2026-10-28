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
SEAT_Y = TOE_Y - 0.13              # where the duck sits to be pushed: 13 cm before the ramp's lip.  Seated 35 cm
                                   # before it, the duck toppled at the lip in 20/20 pushes on 10/28 (its seated
                                   # posture degrades while it slides); seated 15 cm before it, it climbed 3/3
SEAT_TOL = 0.12                    # "seated at the seat" within this (m)
PUSH_TO_Y = CREST_Y + 0.08         # the push ends once the duck sits on the landing.  Pushing it on past the seam of
                                   # the two deck pieces (4 cm gap at y +0.02..+0.06) was tried on 10/28: the crab
                                   # itself stalls where its body straddles the crest, so the duck walks the landing
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
    "NUDGE": "カニさん、そっと押してずらしてあげて",
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

    def at_seat(self):
        p = self.duck_xyz()
        return abs(p[0] - LANE_X) < SEAT_TOL and abs(p[1] - SEAT_Y) < SEAT_TOL

    def seated_for_push(self):
        return self.duck.mode == "SIT" and self.facing_ok() and self.at_seat()

    def near_lip(self):
        """Seated on the line anywhere from the seat to just past the ramp's lip: close enough for a push.  (Take 13,
        10/28: re-seated 2 cm outside SEAT_TOL at y -2.01, the rule asked for SEAT seven more times - the skill reports
        'seated' wherever the duck sits down - until the time ran out.)"""
        p = self.duck_xyz()
        return abs(p[0] - LANE_X) < 0.2 and SEAT_Y - SEAT_TOL < p[1] < TOE_Y + 0.12

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
    if h.stage() in ("toe", "beside") and not h.at_seat():
        goals = [(LANE_X, SEAT_Y)]
        if h.stage() == "beside":                            # off the course's side: round its foot, never up its side
            side = 1.0 if p[0] >= LANE_X else -1.0
            goals.insert(0, (LANE_X + 0.9 * side, SEAT_Y - 0.2))
        for i, g in enumerate(goals):
            tol = 0.25 if i < len(goals) - 1 else 0.07       # the seat itself precisely: the push needs the lip close
            if float(np.linalg.norm(h.duck_xyz()[:2] - g)) <= tol:
                continue
            d.use("vel")
            d.set_mode("WALK_ON", now(h))                    # steered here each tick, stops within `tol`
            while now(h) - t0 < max_s - 9.0:
                if d.mode == "STAND":
                    d.set_mode("WALK_ON", now(h))
                if d.mode == "WALK_ON":
                    dist, _ = d.steer(h.data, g, vx=0.3)
                    if dist <= tol:
                        break
                yield
            if d.mode in ("WALK_ON", "WALK"):
                d.pol.twist[:] = 0
                d.set_mode("STAND", now(h))
            for _ in range(int(0.6 / CONTROL_DT)):
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


def skill_push(h, max_s=90.0, vx=CRAB_PUSH_VX, start="behind", gate="far", toe_vx=None, duck_pitch=0.0, lip_pause=False):
    """The crab gets behind the duck in the lane (swinging out to the side if it is in front), closes in at
    0.12 m/s until it touches, pushes at `vx` until the duck is on the landing, then a gentle push until the
    duck sits upright.  Result: pushed_up / fell / stalled / slipped / nothing (never pushes a fallen duck).
    start: the first phase (experiments); gate: "far" = the experiment's rule (0.12 only while more than
    0.45 m behind the duck), "contact" = `vx` only while touching."""
    d, c = h.duck, h.crab
    t0 = now(h)
    if d.mode == "FALLEN":
        c.loco.set_command(0, 0, 0)                          # (a nudge of the fallen duck was tried on 10/28 noon and
        yield from _hold(h, 1.5)                             #  dropped: see skill_nudge below)
        return "nothing"
    if c.mode != "WALK":
        c.set_mode("WALK", now(h), h.model)
    c.loco.posture[3] = 0.0                                  # neutral body height: the only height that climbs
    phase, t_phase = start, now(h)
    y_best, t_best = h.duck_xyz()[1], now(h)
    lip_done = h.duck_xyz()[1] > TOE_Y - 0.10
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
            elif q[1] < p[1] - 0.25 and abs(q[0] - tx) < 0.35:   # already behind it (touching or near): just square up
                phase, t_phase = "align", now(h)
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
            e_fwd = max(0.0, (p[1] - 0.60) - q[1])           # never backs up here: closer than 0.6 m is fine
            c.loco.set_command(float(np.clip(1.0 * e_fwd, 0.0, 0.15)), float(np.clip(-1.5 * e_lat, -0.15, 0.15)),
                               float(np.clip(3.0 * e_yaw, -1.0, 1.0)))
            if abs(e_yaw) < 0.08 and abs(e_lat) < 0.03 and e_fwd < 0.15:
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
        elif phase == "pause":                               # a fresh approach-then-push right at the ramp's lip
            c.loco.set_command(0, 0, 0)
            if now(h) - t_phase > 1.0:
                phase, t_phase = "approach", now(h)
        elif phase == "push" and lip_pause and not lip_done and p[1] > TOE_Y - 0.09:
            # (experiment 10/28, off by default: a stop-and-re-approach at the lip did not save a push that had
            # started 0.35 m before it - 6/6 still toppled.  What matters is how far the seated duck slides on
            # the flat before the lip: see SEAT_Y)
            lip_done = True
            phase, t_phase = "pause", now(h)
            c.loco.set_command(0, 0, 0)
        elif phase == "push":
            if gate == "far":                                # the experiment's rule
                v = 0.12 if (not h.touching() and q[1] < p[1] - 0.45) else vx
            else:
                v = vx if h.touching() else 0.12
            if toe_vx is not None and p[1] < TOE_Y + 0.12:   # creep over the ramp's lip
                v = min(v, toe_vx)
            if d.mode == "SIT":
                d.sit.body[4] = duck_pitch                   # body pitch command while pushed (experiments)
            # (no burst over the crest: the crab's 0.8 m/s push-through moved the far ramp 7 cm in one run and
            # toppled the seated duck on the landing in another, 10/28; the push ends at the landing's edge)
            c.steer(h.data, (tx, p[1] + 0.15), v)
            # keep pushing across the landing until the duck is past the seam between the two deck pieces: the
            # pieces stand 4 cm apart there (raycast 10/28: floor at y +0.02..+0.06) and a walking duck's foot
            # drops into the slot - it tripped at y +0.07/+0.13 in every run and once could not get up
            if p[1] > PUSH_TO_Y and p[2] > 0.45:
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
            if d.mode == "SIT":
                d.sit.body[4] = 0.0
            c.steer(h.data, (tx, p[1] + 0.15), 0.12)         # a last gentle push until it sits upright
            if (h.tilt() < 15.0 and now(h) - t_phase > 1.0) or now(h) - t_phase > 4.0:
                c.loco.set_command(0, 0, 0)
                yield from _hold(h, 0.5)
                return "pushed_up"
        yield
    d.sit.body[4] = 0.0
    c.loco.set_command(0, 0, 0)
    yield from _hold(h, 0.5)
    return "stalled"


def skill_nudge(h, max_s=30.0):
    """NOT IN USE - an experiment of 10/28 noon (ゆうころ「固定ルール、カニを近くに伴走させようか」), kept as a record.
    The idea: PUSH on a fallen duck = the crab comes up behind the lying duck on its line, shoves it 0.2 m north at
    0.12 m/s off the landing's seam (where velstand could not get it up in 6 of the rule's 7 evaluation-v3 failures)
    and backs away so that velstand can.  v7_test_nudge.py: a duck placed lying on the seam gets up by itself in 5 of
    6 poses; in the stuck pose the crab, starting 0.6 m behind, stalled on the crest's own seam and never reached it;
    in the env smoke (seed 7001) two nudges returned nothing and the shove moved the far deck piece 1.6 cm (course
    damage risk).  Dropped: skill_push returns nothing on a fallen duck as before, and the rule waits."""
    d, c = h.duck, h.crab
    t0 = now(h)
    if h.stage() in ("beside", "north") or d.mode != "FALLEN":
        c.loco.set_command(0, 0, 0)
        yield from _hold(h, 1.0)
        return "nothing"
    if c.mode != "WALK":
        c.set_mode("WALK", now(h), h.model)
    c.loco.posture[3] = 0.0
    p0 = h.duck_xyz().copy()
    phase, t_phase = "behind", now(h)
    while now(h) - t0 < max_s:
        p, q = h.duck_xyz(), h.crab_xyz()
        if d.mode != "FALLEN" and phase != "back":           # it got up meanwhile: just make room
            phase, t_phase = "back", now(h)
        tx = float(np.clip(p[0], LANE_X - 0.2, LANE_X + 0.2))
        if phase == "behind":                                # 0.45 m behind it on its line, facing north
            if q[1] > p[1] - 0.25 and abs(q[0] - tx) < 0.35:   # level with / ahead of it on the line: back down first
                reverse_command(h)
            else:
                e_yaw = wrap(math.pi / 2 - c.yaw(h.data))
                dist, _ = c.steer(h.data, (tx, p[1] - 0.45), 0.25)
                if dist < 0.12:
                    c.loco.set_command(0.0, 0.0, float(np.clip(3.0 * e_yaw, -1.0, 1.0)))
                    if abs(e_yaw) < 0.15:
                        phase, t_phase = "shove", now(h)
            if now(h) - t_phase > 15.0:
                phase, t_phase = "back", now(h)
        elif phase == "shove":
            c.steer(h.data, (tx, p[1] + 0.3), 0.12)
            if p[1] - p0[1] > 0.2 or now(h) - t_phase > 8.0:
                phase, t_phase = "back", now(h)
        elif phase == "back":
            reverse_command(h)
            if (h.crab_dist() > 0.6 and not h.touching()) or now(h) - t_phase > 7.0:
                break
        yield
    c.loco.set_command(0, 0, 0)
    yield from _hold(h, 0.5)
    return "cleared" if h.duck_xyz()[1] - p0[1] > 0.1 else "nothing"


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
    """The duck walks north along the course's centre line (velstand, 0.3 m/s); the crab holds still.  (In the story
    the crab follows the duck across the landing and down - the procession finale - but that stays out of the skill:
    the learned managers were trained with the crab holding, and the crab cannot help a fallen duck anyway, see
    skill_nudge.)  Result: crossed / walked / stalled / nothing (not on its feet)."""
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


def bubble_line(action, book, h=None):
    name = ACTIONS[action]
    if name == "PUSH" and h is not None and h.duck.mode == "FALLEN":
        return LINES["NUDGE"]
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
        if close and not (book.last_action == ACTIONS.index("BACK_OFF") and book.last_result == "stalled"):
            return ACTIONS.index("BACK_OFF")
        return ACTIONS.index("WAIT")                         # nothing in the action set helps a fallen duck (skill_nudge)
    if stage == "north":
        return ACTIONS.index("WAIT")
    if stage in ("deck", "ramp_down"):
        if d.mode == "SIT":
            pushed_and_stalled = book.last_action == ACTIONS.index("PUSH") and book.last_result in ("stalled", "slipped")
            if h.duck_xyz()[1] < PUSH_TO_Y - 0.05 and stage == "deck" and not pushed_and_stalled:
                return ACTIONS.index("PUSH")                 # seated short of the seam: the crab pushes it past
            return ACTIONS.index("BACK_OFF" if close else "STANDUP")   # (or: walk it across after a stalled push)
        return ACTIONS.index("WALK_ON")
    # at the foot, on the up-ramp, or beside the course
    if book.last_result in ("stalled", "slipped") and close:
        return ACTIONS.index("BACK_OFF")
    if d.mode == "SIT" and h.facing_ok() and (h.at_seat() or stage == "ramp_up" or (RULE_NEAR_LIP and h.near_lip())):
        return ACTIONS.index("PUSH")                         # seated at the lip (or already on the ramp), facing the crab
    return ACTIONS.index("SEAT")


RULE_NEAR_LIP = True               # the 10/28 noon addition to the rule (take 13); False reproduces the morning's rule
                                   # (baselines_v2) for a like-for-like check of the evaluation environment
