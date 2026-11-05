"""Procedural, copyright-free sound design synced to a reel's beats.

Templates write <render_dir>/sfx_cues.json: {"duration": s, "mood": "...", "cues": [{"t": s, "type": ...}]}
This module synthesises every sound from scratch (numpy), so there is nothing to license.

    python scripts/sfx.py output/psych_01_essay_memory      # writes sfx.wav next to the frames

Cue types: impact, whoosh, pop, tick_run (needs "dur"), ding, riser (needs "dur"), chime, swoosh_out
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def _t(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SR)) / SR


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / max(decay, 1e-4))


def _lowpass(x: np.ndarray, cutoff_hz) -> np.ndarray:
    """One-pole low-pass (cutoff may be an array for sweeps), vectorised in short blocks."""
    cutoff = np.broadcast_to(np.asarray(cutoff_hz, dtype=float), x.shape)
    alpha = 1 - np.exp(-2 * np.pi * np.clip(cutoff, 1, SR / 2.5) / SR)
    y = np.empty_like(x, dtype=float)
    sweeping = np.ndim(cutoff_hz) > 0 and np.ptp(np.asarray(cutoff_hz)) > 0
    cap = 32 if sweeping else 2048
    prev, i, n = 0.0, 0, len(x)
    while i < n:
        a = float(alpha[i])
        r = 1 - a
        block = max(8, min(cap, int(25 / max(-np.log(r), 1e-9))))  # keep r**-k finite
        j = min(n, i + block)
        k = np.arange(j - i)
        rk = r ** k
        acc = np.cumsum(x[i:j] / rk) * a
        y[i:j] = rk * (acc + prev * r)
        prev = y[j - 1]
        i = j
    return y


def whoosh(length=0.45, up=True):
    t = _t(length)
    noise = rng.standard_normal(len(t))
    sweep = np.linspace(300, 5000, len(t)) if up else np.linspace(5000, 300, len(t))
    body = _lowpass(noise, sweep) - _lowpass(noise, sweep * 0.25)
    env = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 2
    return 0.9 * body * env


def pop(freq=520):
    t = _t(0.09)
    f = freq * (1 - 0.45 * t / t[-1])
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return 0.5 * s * _env(len(t), 0.002, 0.03)


def tick(freq=2200):
    t = _t(0.03)
    return 0.25 * np.sin(2 * np.pi * freq * t) * _env(len(t), 0.0005, 0.006)


def tick_run(dur=1.3, n=18):
    out = np.zeros(int(dur * SR) + SR // 10)
    for k in range(n):
        u = k / max(1, n - 1)
        when = dur * (1 - (1 - u) ** 2.2)  # ticks slow down as the counter eases out
        s = tick(1600 + 1400 * u)
        i = int(when * SR)
        out[i : i + len(s)] += s
    return out


def bell(freq=880, length=1.6, gain=0.35):
    t = _t(length)
    partials = [(1, 1.0), (2.0, 0.45), (2.76, 0.3), (5.4, 0.12)]
    s = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t * (2.2 + m)) for m, a in partials)
    return gain * s * _env(len(t), 0.003, 9.0)


def ding():
    return bell(1046.5, 1.4, 0.3)


def chime():
    a, b = bell(659.3, 1.8, 0.25), bell(987.8, 1.8, 0.22)
    out = np.zeros(len(a) + SR // 6)
    out[: len(a)] += a
    out[SR // 6 : SR // 6 + len(b)] += b
    return out


def impact():
    t = _t(1.1)
    f = 90 * np.exp(-t * 2.5) + 38
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    hit = _lowpass(rng.standard_normal(len(t)), 1800) * np.exp(-t * 18)
    return 0.9 * boom + 0.5 * hit


def riser(dur=1.2):
    t = _t(dur)
    noise = _lowpass(rng.standard_normal(len(t)), np.linspace(400, 7000, len(t)))
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 720, len(t))) / SR)
    env = (t / dur) ** 2
    return 0.35 * (noise * 0.8 + tone * 0.25) * env


def pad(duration, mood="calm"):
    """Low ambient bed so the reel never sounds empty (sits under music if added)."""
    roots = {"calm": [110.0, 164.8, 220.0], "warm": [98.0, 146.8, 196.0], "tense": [110.0, 116.5, 164.8],
             "bright": [130.8, 196.0, 261.6]}.get(mood, [110.0, 164.8, 220.0])
    t = _t(duration)
    s = np.zeros(len(t))
    for i, f in enumerate(roots):
        lfo = 1 + 0.003 * np.sin(2 * np.pi * (0.07 + 0.03 * i) * t)
        s += np.sin(2 * np.pi * f * lfo * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t)
    s = _lowpass(s, 900)
    fade = np.clip(np.minimum(t / 1.5, (duration - t) / 1.5), 0, 1)
    return 0.05 * s * fade


SOUNDS = {
    "impact": lambda c: impact(),
    "whoosh": lambda c: whoosh(c.get("dur", 0.45), True),
    "swoosh_out": lambda c: whoosh(0.35, False) * 0.6,
    "pop": lambda c: pop(c.get("freq", 520)),
    "tick_run": lambda c: tick_run(c.get("dur", 1.3)),
    "ding": lambda c: ding(),
    "riser": lambda c: riser(c.get("dur", 1.2)),
    "chime": lambda c: chime(),
}
# Sounds whose peak should land ON the cue time (they build up before it).
LEAD_IN = {"whoosh": 0.5, "riser": 1.0}


def render(cues_path: Path, out_path: Path) -> Path:
    data = json.loads(cues_path.read_text())
    duration = float(data["duration"])
    mix = np.zeros((int(duration * SR) + SR, 2))
    bed = pad(duration, data.get("mood", "calm"))
    mix[: len(bed), 0] += bed
    mix[: len(bed), 1] += bed
    for k, cue in enumerate(data["cues"]):
        kind = cue["type"]
        if kind not in SOUNDS:
            continue
        s = SOUNDS[kind](cue) * float(cue.get("gain", 1.0))
        lead = LEAD_IN.get(kind, 0.0) * len(s) / SR if kind in LEAD_IN else 0.0
        start = max(0, int((cue["t"] - lead) * SR))
        end = min(len(mix), start + len(s))
        pan = float(cue.get("pan", ((k * 37) % 11 - 5) / 25))  # gentle stereo spread
        mix[start:end, 0] += s[: end - start] * (1 - max(pan, 0))
        mix[start:end, 1] += s[: end - start] * (1 + min(pan, 0))
    mix = mix[: int(duration * SR)]
    peak = np.max(np.abs(mix)) or 1.0
    mix = np.tanh(mix / peak * 1.2) * 0.85  # soft limiter
    pcm = (mix * 32767).astype("<i2")
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path


if __name__ == "__main__":
    d = Path(sys.argv[1])
    print(render(d / "sfx_cues.json", d / "sfx.wav"))
