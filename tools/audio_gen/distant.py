"""Random ambient one-shots: the house settling and the neighbourhood far away.

These are texture, never events: everything outside is heard from inside a
closed house (distance filtering + outdoor echoes + wall transmission).
"""
from __future__ import annotations

import numpy as np

from . import dsp
from .dsp import SR, TAU, samples


def _outdoor(rng, x, metres, wall=True):
    from .loops import outdoor_ir
    y = dsp.reverb(x, outdoor_ir(rng, False, 1.4), 0.7)
    y = dsp.distance(y, metres)
    if wall:
        y = dsp.through_wall(y)
    return y


# --------------------------------------------------------------------------- house settle

def house_settle(rng: np.random.Generator, v: int) -> np.ndarray:
    from . import foley
    n = samples(2.2)
    out = np.zeros(n)
    kind = v % 6
    beam = [118, 176, 263, 355, 498, 690, 940]
    t60 = [0.25, 0.2, 0.16, 0.12, 0.09, 0.06, 0.045]
    g = [0.7, 1.0, 0.9, 0.8, 0.6, 0.4, 0.25]
    s = foley._scale
    if kind in (0, 3):      # single sharp tick of a joint slipping
        out += foley.impact(rng, n, 0.05, rng.uniform(0.0002, 0.0004), s(beam, rng, 0.1), t60, g, 1.0,
                            click=0.4, click_band=(1500, 7000))
    elif kind in (1, 4):    # double tick
        out += foley.impact(rng, n, 0.05, 0.0003, s(beam, rng, 0.1), t60, g, 1.0, click=0.35)
        out += foley.impact(rng, n, 0.05 + rng.uniform(0.18, 0.6), 0.0004, s(beam, rng, 0.1), t60, g,
                            rng.uniform(0.4, 0.7), click=0.3)
    elif kind == 2:         # short low creak of a joist
        out += foley.creak(rng, n, 0.05, rng.uniform(0.25, 0.45), 35, 75, s([210, 340, 520, 760], rng, 0.1),
                           0.06, gain=1.0, irregular=0.3, jitter=0.15)
        out += foley.impact(rng, n, 0.04, 0.0004, s(beam, rng, 0.1), t60, g, 0.5, click=0.2)
    else:                   # muffled knock inside a wall cavity
        out += foley.impact(rng, n, 0.05, 0.0012, s([95, 150, 230, 330, 470], rng, 0.1),
                            [0.12, 0.1, 0.08, 0.06, 0.05], [1, .9, .7, .5, .3], 1.0)
        out = dsp.lowpass(out, 1800, 2)
    # heard from somewhere else in the house
    ir = dsp.room_ir(rng, rt60=0.55, dims=(5.0, 4.0, 2.44), length=0.7)
    out = dsp.reverb(out, ir, 0.45)
    return dsp.lowpass(out, rng.uniform(4500, 7000), 1)


# --------------------------------------------------------------------------- dog

def _bark(rng, f_peak):
    d = rng.uniform(0.13, 0.22)
    m = samples(d)
    tt = np.arange(m) / SR
    f0 = np.interp(tt, [0, d * 0.25, d], [f_peak * 0.7, f_peak, f_peak * 0.6])
    f0 *= 1 + 0.03 * dsp.smooth_noise(rng, m, 40, -1, 1)
    ph = TAU * np.cumsum(f0) / SR
    src = sum(np.sin(h * ph + 0.3 * h) / h ** 0.7 for h in range(1, 16))
    src += 0.35 * np.sin(0.5 * ph)  # subharmonic roughness
    src = dsp.asym_saturate(src * 0.4, 3.0, 0.2)
    src += 0.6 * dsp.bandpass(dsp.white(rng, m), 500, 4000)
    y = np.zeros(m)
    for f, q, gdb in ((620, 3, 10), (1350, 4, 8), (2600, 5, 4)):
        y += dsp.eq(src, "bandpass", f * rng.uniform(0.93, 1.07), q) * dsp.db(gdb)
    env = np.clip(tt / 0.008, 0, 1) * np.exp(-tt / (d * 0.45))
    return y * env


def distant_dog(rng: np.random.Generator, v: int) -> np.ndarray:
    n = samples(5.0)
    x = np.zeros(n)
    t = 0.1
    fp = rng.uniform(420, 620)
    bursts = int(rng.integers(1, 3))
    for b in range(bursts):
        for _ in range(int(rng.integers(2, 5))):
            dsp.mix_at(x, _bark(rng, fp * rng.uniform(0.94, 1.06)), samples(t), rng.uniform(0.6, 1.0))
            t += rng.uniform(0.3, 0.55)
        t += rng.uniform(0.6, 1.2)
        if t > 3.4:
            break
    y = _outdoor(rng, x, rng.uniform(150, 300))
    return dsp.pad(y, n)


# --------------------------------------------------------------------------- car

def distant_car(rng: np.random.Generator, v: int) -> np.ndarray:
    L = rng.uniform(8.0, 10.5)
    n = samples(L)
    t = dsp.tvec(n)
    tc = L * rng.uniform(0.42, 0.58)
    speed = rng.uniform(10, 15)          # m/s, residential street
    closest = rng.uniform(25, 45)        # metres
    x = speed * (t - tc)
    r = np.sqrt(x ** 2 + closest ** 2)
    vr = speed * x / r                    # radial velocity (receding positive)
    dop = 343.0 / (343.0 + vr)
    amp = (closest / r) ** 1.2
    tires = dsp.colored(rng, n, -3.0, lo=150, hi=4000)
    tires = dsp.eq(tires, "peak", 900, 0.8, 4)
    f_eng = rng.uniform(32, 45)  # firing frequency at cruise
    f = f_eng * dop * (1 + 0.01 * dsp.smooth_noise(rng, n, 1, -1, 1))
    ph = TAU * np.cumsum(f) / SR
    eng = sum(np.sin(h * ph + rng.uniform(0, TAU)) / h ** 0.8 for h in range(1, 12))
    eng = dsp.lowpass(eng, 700, 2)
    y = (tires * 0.8 + eng * 0.35) * amp
    # brightness follows proximity
    y = dsp.time_varying_lowpass(y, 800 + 3500 * amp ** 2)
    y = _outdoor(rng, y, closest * 1.5)
    y = dsp.pad(y, n)
    return dsp.fade(y, 1.5, 2.0)


# --------------------------------------------------------------------------- mower

def mower_core(rng: np.random.Generator, n: int, seconds_per_pass: float, circular: bool = False) -> np.ndarray:
    """Single-cylinder four-stroke under governor, with load dips and turning passes."""
    t = dsp.tvec(n)
    if circular:
        load = dsp.periodic_lfo(rng, n, max(2, int(dsp.secs(n) / 1.5)), 0.0, 1.0, tilt=0.4) ** 4
        turn = dsp.periodic_lfo(rng, n, max(1, int(dsp.secs(n) / seconds_per_pass)), 0.0, 1.0, tilt=0.2)
    else:
        load = dsp.smooth_noise(rng, n, 0.8, 0.0, 1.0) ** 4
        turn = 0.5 + 0.5 * np.sin(TAU * t / seconds_per_pass + rng.uniform(0, TAU))
    rpm = rng.uniform(3000, 3300) * (1 - 0.09 * load)
    fire = rpm / 60.0 / 2.0  # one power stroke every two revolutions
    if circular:
        from .loops import pulses_c
        imp = pulses_c(rng, n, fire, np.ones(n), 0.25, 0.04)
    else:
        imp = dsp.stick_slip(rng, n, fire, np.ones(n), jitter=0.03, pulse_w=0.0015)
    bank = (dsp.resonator_bank_c if circular else dsp.resonator_bank)
    muffler = bank(imp, [165, 240, 410, 620, 980], [0.05, 0.04, 0.03, 0.025, 0.02], [1, .9, .7, .5, .3])
    bark = dsp.lowpass_c(imp, 2500, 2) if circular else dsp.lowpass(imp, 2500, 2)
    blade = np.sin(TAU * np.cumsum(rpm / 60.0 * 2) / SR) * 0.15
    whoosh = dsp.colored(rng, n, -2.0, lo=200, hi=2500) * 0.25
    # each power stroke is also a puff of exhaust noise
    k = samples(0.009)
    puff_k = dsp.white(rng, k) * np.exp(-np.arange(k) / samples(0.0025))
    puff = np.fft.irfft(np.fft.rfft(imp) * np.fft.rfft(puff_k, n), n) if circular else \
        np.convolve(imp, puff_k)[:n]
    puff = (dsp.lowpass_c if circular else dsp.lowpass)(puff, 3000, 2)
    puff /= np.std(puff) + 1e-12
    y = muffler * 0.15 + bark * 2.0 + puff * 0.25 + blade + whoosh * 0.06 * (0.5 + load)
    # facing towards / away from us changes level and brightness
    y = y * (0.35 + 0.65 * turn)
    return y


def distant_mower(rng: np.random.Generator, v: int) -> np.ndarray:
    L = rng.uniform(14.0, 20.0)
    n = samples(L)
    y = mower_core(rng, n, rng.uniform(6, 10))
    y = _outdoor(rng, y, rng.uniform(180, 320))
    y = dsp.pad(y, n)
    return dsp.fade(y, 3.0, 4.0)
