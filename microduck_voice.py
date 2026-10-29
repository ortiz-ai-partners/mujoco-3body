"""The Microduck's official voice, ported to Python for the video's soundtrack.

Source: the `sounds` crate of pollen-robotics/microduck (Apache-2.0, Copyright Pollen Robotics) - the seedable synth
the real robot renders its voice bank with and plays through its audio codec (`robotd/src/sound.rs`).  This file is a
line-for-line port of `sounds/src/{rng,synth,personality,voices}.rs`: the same xoshiro256++ stream seeded through
splitmix64, the same personality traits drawn in the same order, the same recipes at the same 48 kHz.  Only the
`theremin` stream and the bank tooling are left out.

Tags, as the robot uses them: `chirp` (the everyday call, the mouth trigger), `greet` (waking up, often a double
"wak-wak"), `inquire` (a rising question), `alarm` (a startled yelp), `peck` (a low tock, the goodbye),
`coo` (soft and drowsy), `wheee` (the joy ride: start, loop, end).

    python microduck_voice.py --seed 7 --out out/microduck_voice      -> one wav per tag x variant (48 kHz mono)
"""
from __future__ import annotations

import argparse
import math
import wave
import zlib
from pathlib import Path

import numpy as np

SR = 48_000
TUNED_SR = 22_050.0
_M64 = (1 << 64) - 1
TAU = 2.0 * math.pi


def _rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & _M64


class Rng:
    """xoshiro256++ seeded through splitmix64 (sounds/src/rng.rs)."""

    def __init__(self, seed):
        x = seed & 0xFFFFFFFF
        s = []
        for _ in range(4):
            x = (x + 0x9E3779B97F4A7C15) & _M64
            z = x
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M64
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M64
            s.append(z ^ (z >> 31))
        self.s = s
        self.spare = None

    def next_u64(self):
        s = self.s
        result = (_rotl((s[0] + s[3]) & _M64, 23) + s[0]) & _M64
        t = (s[1] << 17) & _M64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl(s[3], 45)
        return result

    def random(self):
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def uniform(self, lo, hi):
        return lo + (hi - lo) * self.random()

    def integers(self, lo, hi):
        return lo + int(math.floor(self.random() * (hi - lo)))

    def choice(self, choices):
        return choices[self.integers(0, len(choices))]

    def standard_normal(self):
        if self.spare is not None:
            z, self.spare = self.spare, None
            return z
        r = 1.0 - self.random()
        theta = TAU * self.random()
        mag = math.sqrt(-2.0 * math.log(r))
        self.spare = float(np.float32(mag * math.sin(theta)))
        return float(np.float32(mag * math.cos(theta)))

    def standard_normal_vec(self, n):
        return np.array([self.standard_normal() for _ in range(n)], dtype=np.float32)


class Personality:
    """Stable vocal traits from one seed (sounds/src/personality.rs); the draw order is the Rust struct's."""

    FIELDS = ("pitch_spread", "glide_bias", "brightness", "tilt", "nasal", "harmonic_skew", "formant_n",
              "formant_gain", "vibrato_rate_hz", "vibrato_depth", "jitter_depth", "breath", "quackiness", "am_rate_hz",
              "am_depth", "warble_hz", "warble_depth", "attack_sharpness", "speed")

    def __init__(self, seed):
        rng = Rng(seed)
        self.seed = seed & 0xFFFFFFFF
        self.register = rng.choice([-1.0, 0.0, 0.0, 1.0]) + rng.uniform(-0.4, 0.4)
        base = rng.uniform(160.0, 380.0)
        self.pitch_center_hz = min(620.0, max(110.0, base * 2.0 ** (self.register * 0.45)))
        self.pitch_spread = rng.uniform(0.4, 1.2)
        self.glide_bias = rng.uniform(-1.0, 1.0)
        self.brightness = rng.uniform(0.05, 0.55)
        self.tilt = rng.uniform(1.4, 2.8)
        self.nasal = rng.uniform(0.1, 1.0)
        self.harmonic_skew = rng.uniform(-1.0, 1.0)
        self.formant_n = rng.integers(1, 6)
        self.formant_gain = rng.uniform(0.0, 1.4)
        self.vibrato_rate_hz = rng.uniform(3.5, 9.5)
        self.vibrato_depth = rng.uniform(0.0, 0.7)
        self.jitter_depth = rng.uniform(0.03, 0.35)
        self.breath = rng.uniform(0.0, 0.30)
        self.quackiness = rng.uniform(0.2, 1.0)
        self.am_rate_hz = rng.uniform(18.0, 55.0)
        self.am_depth = rng.uniform(0.15, 0.70)
        self.warble_hz = rng.uniform(7.0, 18.0)
        self.warble_depth = rng.uniform(0.0, 1.4)
        self.attack_sharpness = rng.uniform(0.0, 1.0)
        self.speed = rng.uniform(0.82, 1.22)

    def copy(self, **changes):
        p = object.__new__(Personality)
        p.__dict__.update(self.__dict__)
        p.__dict__.update(changes)
        return p

    def variant_rng(self, tag, variant):
        h = ((self.seed * 1_000_003) & _M64) ^ zlib.crc32(tag.encode()) ^ ((variant * 2_654_435_761) & _M64)
        return Rng(h & 0xFFFFFFFF)

    def harmonics(self):
        n_harm = 7
        weights = []
        for n in range(1, n_harm + 1):
            base = 1.0 / n ** self.tilt
            high_lift = self.brightness * (n / n_harm) ** 1.5
            nasal = self.nasal * (0.6 if n in (2, 3) else 0.0)
            if self.harmonic_skew >= 0.0:
                skew = self.harmonic_skew * (0.4 if n % 2 == 0 else -0.2)
            else:
                skew = -self.harmonic_skew * (-0.3 if n % 2 == 0 else 0.4)
            formant = self.formant_gain if n == self.formant_n else 0.0
            weights.append(max(0.0, base + high_lift + nasal + skew + formant * base * 1.5))
        weights[0] = max(weights[0], 0.7)
        return weights


# ── synth primitives (sounds/src/synth.rs) ─────────────────────────────────────
def t_axis(dur):
    n = max(1, int(round(dur * SR)))
    return (np.arange(n) / SR).astype(np.float32)


def lerp(t, points):
    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])
    return np.interp(t.astype(np.float64), xs, ys).astype(np.float32)


def expdecay(t, attack_s, decay_s):
    attack, decay = max(attack_s, 1e-4), max(decay_s, 1e-4)
    a = np.clip(t / attack, 0.0, 1.0)
    d = np.exp(-np.maximum(t - attack, 0.0) / decay)
    return (a * d).astype(np.float32)


def bell(t, attack_s, release_s):
    total = float(t[-1]) if len(t) else 0.0
    rel_start = max(total - release_s, 0.0)
    attack, release = max(attack_s, 1e-4), max(release_s, 1e-4)
    x = t.astype(np.float64)
    v = np.ones_like(x)
    v = np.where(x < attack_s, x / attack, v)
    v = np.where(x > rel_start, np.maximum(1.0 - (x - rel_start) / release, 0.0), v)
    return np.clip(v, 0.0, 1.0).astype(np.float32)


def phase_from_freq(freq):
    return (TAU * np.cumsum(freq.astype(np.float64)) / SR).astype(np.float32)


def harmonic_osc(phase, weights):
    out = np.zeros_like(phase)
    for n, w in enumerate(weights, start=1):
        if w != 0.0:
            out += np.float32(w) * np.sin(n * phase)
    return out


def vibrato(t, rate_hz, depth_semitones, phase):
    if rate_hz <= 0.0 or depth_semitones <= 0.0:
        return np.ones_like(t)
    lfo = np.sin(TAU * rate_hz * t.astype(np.float64) + phase)
    return (2.0 ** (depth_semitones * lfo / 12.0)).astype(np.float32)


def jitter(t, depth_semitones, rng):
    if depth_semitones <= 0.0:
        return np.ones_like(t)
    raw = rng.standard_normal_vec(len(t))
    k = max(1, int(round(64.0 * SR / TUNED_SR)))
    smoothed = np.convolve(raw, np.ones(k, dtype=np.float32) / k, mode="same")
    return (2.0 ** (depth_semitones * smoothed.astype(np.float64) / 12.0)).astype(np.float32)


def pink_noise(n, rng):
    a = np.float32(0.985 ** (TUNED_SR / SR))
    white = rng.standard_normal_vec(n)
    pink = np.empty(n, np.float32)
    leak = np.float32(0.0)
    for i in range(n):
        leak = a * leak + white[i]
        pink[i] = leak
    return pink / (np.max(np.abs(pink)) + 1e-9)


def click(n, rng, length):
    out = np.zeros(n, np.float32)
    ln = min(length, n)
    for i in range(ln):
        fade = 1.0 - i / ln
        out[i] = rng.uniform(-1.0, 1.0) * fade * fade
    return out


def normalise(x, peak_dbfs):
    peak = float(np.max(np.abs(x))) + 1e-9
    return (x * (10.0 ** (peak_dbfs / 20.0) / peak)).astype(np.float32)


# ── recipes (sounds/src/voices.rs) ─────────────────────────────────────────────
def _attack(p, dur, snappy):
    soft, sharp = 0.04 * dur, 0.003 * dur
    return max(soft + (sharp - soft) * p.attack_sharpness * snappy, 0.001)


def _voice(p, t, freq, rng, am_scale, breath_scale):
    vib = vibrato(t, p.vibrato_rate_hz, p.vibrato_depth, rng.uniform(0.0, TAU))
    jit = jitter(t, p.jitter_depth, rng)
    body = harmonic_osc(phase_from_freq(freq * vib * jit), p.harmonics())
    am_d = p.am_depth * am_scale * p.quackiness
    if am_d > 0.01:
        body = body * (1.0 - am_d * (0.5 + 0.5 * np.sin(TAU * p.am_rate_hz * t.astype(np.float64)))).astype(np.float32)
    breath = p.breath * breath_scale
    if breath > 0.0:
        body = body + np.float32(breath) * pink_noise(len(t), rng)
    return body


def alarm(p, variant):
    rng = p.variant_rng("alarm", variant)
    dur = (0.20 + 0.12 * rng.random()) / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (1.25 + 0.35 * p.pitch_spread) * (0.94 + 0.12 * rng.random())
    peak_mul = 1.15 + 0.25 * p.pitch_spread + 0.10 * rng.random()
    fall_mul = 0.75 + 0.20 * (1.0 - p.pitch_spread)
    freq = lerp(t, [(0.0, f0), (0.05 * dur, f0 * peak_mul), (dur, f0 * fall_mul)])
    env = expdecay(t, _attack(p, dur, 1.0), dur * (0.40 + 0.20 * rng.random()))
    sig = _voice(p, t, freq, rng, 0.5, 1.0) * env
    crackle = np.float32(0.04 + 0.10 * p.brightness)
    sig = sig + crackle * np.array([rng.standard_normal() for _ in range(len(t))], np.float32) * env
    return normalise(sig, -3.0)


def _greet_syllable(p, rng, dur_scale, f0_scale):
    dur = (0.32 + 0.25 * rng.random()) * dur_scale / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (0.9 + 0.15 * rng.random()) * f0_scale
    bias, bend = p.glide_bias, 0.10 + 0.15 * p.pitch_spread
    start = f0 * (1.0 - bias * bend * 0.5)
    mid = f0 * (1.0 + bias * bend)
    end = f0 * (1.0 - bias * bend * 0.3) * (0.92 + 0.08 * rng.random())
    freq = lerp(t, [(0.0, start), (0.18 * dur, mid), (dur, end)])
    env = expdecay(t, _attack(p, dur, 0.5), dur * 0.7)
    return _voice(p, t, freq, rng, 1.0, 1.0) * env


def greet(p, variant):
    rng = p.variant_rng("greet", variant)
    sig = _greet_syllable(p, rng, 1.0, 1.0)
    if rng.random() < 0.4:
        gap = np.zeros(int((0.05 + 0.06 * rng.random()) / p.speed * SR), np.float32)
        f0_scale = 0.95 + 0.06 * rng.random()
        sig = np.concatenate([sig, gap, _greet_syllable(p, rng, 0.8, f0_scale)])
    return normalise(sig, -3.0)


def inquire(p, variant):
    rng = p.variant_rng("inquire", variant)
    dur = (0.42 + 0.25 * rng.random()) / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (0.88 + 0.10 * rng.random())
    rise = 1.15 + 0.50 * p.pitch_spread + 0.20 * max(p.glide_bias, 0.0) + 0.10 * rng.random()
    freq = lerp(t, [(0.0, f0 * 0.92), (0.30 * dur, f0 * 0.95), (dur, f0 * rise)])
    env = bell(t, dur * (0.06 + 0.10 * (1.0 - p.attack_sharpness)), dur * 0.32)
    return normalise(_voice(p, t, freq, rng, 0.6, 1.0) * env, -3.0)


def peck(p, variant):
    rng = p.variant_rng("peck", variant)
    dur = (0.16 + 0.12 * rng.random()) / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (0.45 + 0.20 * rng.random())
    freq = lerp(t, [(0.0, f0 * 1.5), (0.04 * dur, f0), (dur, f0 * 0.80)])
    env = expdecay(t, _attack(p, dur, 1.0), dur * 0.35)
    body = _voice(p, t, freq, rng, 0.3, 0.5) * env
    click_len = int((0.003 + 0.006 * p.attack_sharpness) * SR)
    body = body + np.float32(0.4 + 0.4 * p.attack_sharpness) * click(len(t), rng, click_len)
    return normalise(body, -3.0)


def _chirp_syllable(p, rng, f0, dur, contour):
    t = t_axis(dur)
    warble = vibrato(t, p.warble_hz, p.warble_depth, rng.uniform(0.0, TAU))
    freq = np.float32(f0) * lerp(t, contour) * warble
    env = expdecay(t, _attack(p, dur, 0.7), dur * 0.55)
    p_soft = p.copy(quackiness=p.quackiness * 0.2, brightness=p.brightness * 0.5, formant_gain=p.formant_gain * 0.5)
    return _voice(p_soft, t, freq, rng, 1.0, 0.4) * env


def chirp(p, variant):
    rng = p.variant_rng("chirp", variant)
    shape = variant % 4
    f0 = p.pitch_center_hz * (0.95 + 0.75 * rng.random())
    if shape == 0:                                       # rising blip
        dur = (0.10 + 0.10 * rng.random()) / p.speed
        peak = 1.12 + 0.10 * rng.random()
        sig = _chirp_syllable(p, rng, f0, dur, [(0.0, 0.88), (0.5 * dur, peak), (dur, 1.05)])
    elif shape == 1:                                     # falling blip
        dur = (0.10 + 0.10 * rng.random()) / p.speed
        start = 1.12 + 0.10 * rng.random()
        sig = _chirp_syllable(p, rng, f0, dur, [(0.0, start), (0.3 * dur, 1.0), (dur, 0.78)])
    elif shape == 2:                                     # trill
        dur = (0.22 + 0.14 * rng.random()) / p.speed
        p_trill = p.copy(warble_depth=max(p.warble_depth, 0.7) * 1.6)
        sig = _chirp_syllable(p_trill, rng, f0, dur, [(0.0, 1.0), (0.5 * dur, 1.06), (dur, 0.94)])
    else:                                                # double "wek-wek"
        dur = (0.08 + 0.05 * rng.random()) / p.speed
        a = _chirp_syllable(p, rng, f0, dur, [(0.0, 0.95), (0.4 * dur, 1.10), (dur, 0.88)])
        gap = np.zeros(int((0.03 + 0.03 * rng.random()) / p.speed * SR), np.float32)
        dur_b = dur * 0.9
        f0_b = f0 * (0.92 + 0.10 * rng.random())
        b = _chirp_syllable(p, rng, f0_b, dur_b, [(0.0, 0.95), (0.4 * dur_b, 1.10), (dur_b, 0.88)])
        sig = np.concatenate([a, gap, b])
    return normalise(sig, -6.0)


def coo(p, variant):
    rng = p.variant_rng("coo", variant)
    dur = (0.85 + 0.55 * rng.random()) / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (0.42 + 0.15 * (1.0 - p.attack_sharpness)) * (0.94 + 0.12 * rng.random())
    drift_a = 1.0 + 0.05 * rng.random() + 0.04 * p.glide_bias
    freq = lerp(t, [(0.0, f0 * 0.94), (dur * 0.5, f0 * drift_a), (dur, f0 * 0.90)])
    env = bell(t, dur * (0.18 + 0.10 * (1.0 - p.attack_sharpness)), dur * 0.30)
    p_soft = p.copy(breath=max(p.breath, 0.12) + 0.10, quackiness=p.quackiness * 0.25, am_rate_hz=p.am_rate_hz * 0.30,
                    vibrato_rate_hz=p.vibrato_rate_hz * 0.45, vibrato_depth=p.vibrato_depth * 0.7)
    return normalise(_voice(p_soft, t, freq, rng, 1.0, 1.0) * env, -5.0)


def wheee_segments(p, variant):
    rng = p.variant_rng("wheee", variant)
    d_start = (0.80 + 0.30 * rng.random()) / p.speed
    d_loop = (1.60 + 0.60 * rng.random()) / p.speed
    d_end = (0.55 + 0.25 * rng.random()) / p.speed
    total = d_start + d_loop + d_end
    t = t_axis(total)
    t1, t2 = d_start, d_start + d_loop
    f0 = p.pitch_center_hz * (0.95 + 0.10 * rng.random())
    top = 1.6 + 0.5 * p.pitch_spread + 0.25 * rng.random()
    base = lerp(t, [(0.0, f0 * 0.85), (0.15 * d_start, f0), (t1, f0 * top), (t2, f0 * top),
                    (t2 + 0.25 * d_end, f0 * top * 1.04), (total, f0 * 0.60)])
    wob_hz = 4.5 + 3.0 * rng.random()
    swell = lerp(t, [(0.0, 0.15), (t1, 1.0), (total, 1.0)])
    wob = np.sin(TAU * wob_hz * t.astype(np.float64))
    freq = (base * 2.0 ** (0.5 * swell.astype(np.float64) * wob / 12.0)).astype(np.float32)
    env = lerp(t, [(0.0, 0.0), (min(0.06, 0.5 * d_start), 1.0), (t2 + 0.40 * d_end, 1.0), (total, 0.0)])
    p_joy = p.copy(vibrato_depth=p.vibrato_depth * 0.5, quackiness=p.quackiness * 0.5)
    sig = normalise(_voice(p_joy, t, freq, rng, 0.5, 0.5) * env, -4.0)
    n1, n2 = int(t1 * SR), int(t2 * SR)
    start, loop_seg, end = sig[:n1].copy(), sig[n1:n2].copy(), sig[n2:].copy()
    nx = min(int(0.08 * SR), len(loop_seg) // 2, n1)
    for i in range(nx):
        w = i / max(max(nx, 1) - 1.0, 1.0)
        tail = len(loop_seg) - nx + i
        loop_seg[tail] = (1.0 - w) * loop_seg[tail] + w * sig[n1 - nx + i]
    return start, loop_seg, end


def wheee(p, variant):
    start, loop_seg, end = wheee_segments(p, variant)
    return np.concatenate([start, loop_seg, loop_seg, end])


TAGS = {"alarm": alarm, "greet": greet, "inquire": inquire, "peck": peck, "chirp": chirp, "coo": coo, "wheee": wheee}


def variant_count(tag):
    return 12 if tag in ("greet", "chirp") else 6 if tag == "wheee" else 10


def render(tag, p, variant):
    return TAGS[tag](p, variant)


def write_wav(path, x, sr=SR):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=Path("out/microduck_voice"))
    args = ap.parse_args()
    p = Personality(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in p.__dict__.items()})
    for tag in TAGS:
        for v in range(variant_count(tag)):
            write_wav(args.out / f"{tag}_{v:02d}.wav", render(tag, p, v))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
