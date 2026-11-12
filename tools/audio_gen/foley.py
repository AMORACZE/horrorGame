"""Footsteps, interaction foley and UI clicks.

Each public function takes a seeded numpy Generator and a variant index and
returns a mono float array. Loudness normalisation, fades and export are done
by gen_audio.py, so these only need to get the *shape* and *timbre* right.

Approach (no samples, only physics-flavoured synthesis):
  impact  = contact force pulse (width ~ hardness)  ->  modal resonator bank
            (+ a short noise "click" for the contact itself);
  sliding = band-passed noise with a random grain process, sometimes plus a
            low-rate stick-slip judder;
  creaks / squeaks = stick-slip pulse trains through resonators;
  glass / metal = high-Q decaying partials with inharmonic ratios.
All one-shots get a faint convolution with a synthetic domestic room so they
are never perfectly anechoic (the World bus adds the rest).
"""
from __future__ import annotations

import numpy as np

from . import dsp
from .dsp import SR, samples

# --------------------------------------------------------------------------- shared helpers


def _scale(vals, rng: np.random.Generator, j: float):
    return [v * (1.0 + rng.uniform(-j, j)) for v in vals]


def impact(rng: np.random.Generator, n: int, at: float, width: float, freqs, t60s, gains,
           gain: float = 1.0, click: float = 0.0, click_band=(1500, 8000), click_decay=0.003,
           jitter: float = 0.04, roughness: float = 0.0) -> np.ndarray:
    """One modal impact placed at time `at` inside an n-sample buffer."""
    out = np.zeros(n)
    exc = np.zeros(n)
    p = dsp.contact_pulse(width, rng=rng, roughness=roughness)
    p = p / (np.sum(np.abs(p)) + 1e-12)  # unit impulse: modes ring at ~gain, softer = duller
    dsp.mix_at(exc, p, samples(at))
    out += dsp.resonator_bank(exc, freqs, t60s, gains, rng=rng, jitter=jitter)
    if click > 0:
        m = samples(0.05)
        c = dsp.bandpass(dsp.white(rng, m), click_band[0], click_band[1]) * dsp.env_ad(m, 0.0002, click_decay)
        dsp.mix_at(out, c, samples(at), click)
    return out * gain


def weight_thump(rng: np.random.Generator, n: int, at: float, width: float = 0.014, gain: float = 1.0,
                 fc: float = 140.0) -> np.ndarray:
    """Low-frequency body-weight transfer into the floor."""
    out = np.zeros(n)
    p = dsp.contact_pulse(width)
    m = len(p) + samples(0.08)
    p = dsp.lowpass(dsp.pad(p, m), fc, 2)
    p -= np.linspace(p.mean(), 0, m) * 0  # keep shape; DC removed later
    dsp.mix_at(out, p, samples(at), gain)
    return out


def metal_click(rng: np.random.Generator, n: int, at: float, base: float = 2600.0, gain: float = 1.0,
                ring: float = 0.04) -> np.ndarray:
    ratios = [1.0, 1.52, 2.17, 2.86, 3.71, 4.6]
    freqs = [base * r * rng.uniform(0.97, 1.03) for r in ratios]
    t60 = [ring * rng.uniform(0.6, 1.4) / (1 + 0.3 * i) for i in range(len(ratios))]
    g = [rng.uniform(0.4, 1.0) / (1 + 0.4 * i) for i in range(len(ratios))]
    return impact(rng, n, at, 0.00008, freqs, t60, g, gain=gain, click=0.5, click_band=(2500, 12000),
                  click_decay=0.0015, jitter=0.0)


def plastic_click(rng: np.random.Generator, n: int, at: float, base: float = 1500.0, gain: float = 1.0,
                  ring: float = 0.015) -> np.ndarray:
    ratios = [1.0, 1.43, 2.3, 3.1, 4.4]
    freqs = [base * r * rng.uniform(0.95, 1.05) for r in ratios]
    t60 = [ring * rng.uniform(0.7, 1.3) for _ in ratios]
    g = [rng.uniform(0.5, 1.0) / (1 + 0.3 * i) for i in range(len(ratios))]
    return impact(rng, n, at, 0.00015, freqs, t60, g, gain=gain, click=0.8, click_band=(1800, 11000),
                  click_decay=0.0012, jitter=0.0)


def wood_knock(rng: np.random.Generator, n: int, at: float, base: float = 200.0, gain: float = 1.0,
               width: float = 0.0012, ring: float = 0.08, n_modes: int = 9, click: float = 0.15) -> np.ndarray:
    # plate-like inharmonic series for a wooden panel
    ratios = [1.0, 1.59, 2.14, 2.65, 3.48, 4.4, 5.5, 6.9, 8.6, 10.7][:n_modes]
    freqs = [base * r for r in ratios]
    t60 = [ring * rng.uniform(0.7, 1.3) / (1 + 0.18 * i) for i in range(len(freqs))]
    g = [rng.uniform(0.4, 1.0) / (1 + 0.25 * i) for i in range(len(freqs))]
    return impact(rng, n, at, width, freqs, t60, g, gain=gain, click=click, click_band=(1200, 7000),
                  jitter=0.05)


def glass_ring(rng: np.random.Generator, n: int, at: float, f1: float, gain: float = 1.0,
               t60: float = 0.9) -> np.ndarray:
    ratios = [1.0, 2.32, 4.25, 6.63, 9.38]
    freqs = [f1 * r * rng.uniform(0.995, 1.005) for r in ratios]
    t60s = [t60 / (1 + 0.9 * i) for i in range(len(ratios))]
    amps = [1.0, 0.55, 0.3, 0.16, 0.08]
    m = n - samples(at)
    if m <= 0:
        return np.zeros(n)
    r = dsp.modal_ring(m, freqs, t60s, amps, rng)
    # beating from slight asymmetry: each mode is a close doublet
    r += 0.5 * dsp.modal_ring(m, [f * 1.0018 for f in freqs], t60s, amps, rng)
    r *= dsp.env_ad(m, 0.00005, 1e9)
    tick = dsp.highpass(dsp.white(rng, m), 3000) * dsp.env_ad(m, 0.00005, 0.0008)
    out = np.zeros(n)
    dsp.mix_at(out, r + 0.6 * tick, samples(at), gain)
    return out


def air_whoosh(rng: np.random.Generator, n: int, start: float, dur: float, gain: float = 1.0,
               lo: float = 60.0, hi: float = 700.0) -> np.ndarray:
    m = samples(dur)
    x = dsp.bandpass(dsp.white(rng, m), lo, hi)
    e = np.sin(np.linspace(0, np.pi, m)) ** 2
    e *= np.linspace(0.6, 1.0, m)
    out = np.zeros(n)
    dsp.mix_at(out, x * e, samples(start), gain)
    return out


def creak(rng: np.random.Generator, n: int, start: float, dur: float, f_lo: float, f_hi: float,
          body_freqs, body_t60: float = 0.05, gain: float = 1.0, irregular: float = 0.12,
          jitter: float = 0.06) -> np.ndarray:
    """Stick-slip creak: rate glides between f_lo and f_hi with a random path."""
    m = samples(dur)
    path = dsp.smooth_noise(rng, m, 3.0 / max(dur, 0.1), 0, 1)
    rate = f_lo + (f_hi - f_lo) * path
    amp = np.sin(np.linspace(0, np.pi, m)) ** 0.7 * dsp.smooth_noise(rng, m, 6.0, 0.35, 1.0)
    exc = dsp.stick_slip(rng, m, rate, amp, jitter=jitter, irregular=irregular)
    t60 = [body_t60 * rng.uniform(0.7, 1.3) for _ in body_freqs]
    g = [rng.uniform(0.5, 1.0) for _ in body_freqs]
    y = dsp.resonator_bank(exc, body_freqs, t60, g, rng=rng, jitter=0.03)
    y = dsp.lowpass(y, 7000, 1) + 0.15 * dsp.bandpass(exc, 500, 5000)
    out = np.zeros(n)
    dsp.mix_at(out, y, samples(start), gain)
    return out


def room(rng: np.random.Generator, x: np.ndarray, wet: float = 0.12, rt60: float = 0.42,
         dims=(4.0, 3.5, 2.44)) -> np.ndarray:
    ir = dsp.room_ir(rng, rt60=rt60, dims=dims, length=rt60 * 1.1)
    return dsp.reverb(x, ir, wet)


# --------------------------------------------------------------------------- footsteps

def footstep(surface: str, rng: np.random.Generator, v: int) -> np.ndarray:
    n = samples(0.5)
    out = np.zeros(n)
    toe_t = rng.uniform(0.065, 0.12)
    heel_t = 0.004
    if surface == "wood":
        modes = _scale([82, 117, 156, 209, 268, 345, 460, 615, 830, 1110, 1460, 1950], rng, 0.05)
        t60 = [0.22, 0.18, 0.15, 0.12, 0.1, 0.08, 0.07, 0.055, 0.045, 0.035, 0.03, 0.025]
        g = [0.9, 1.0, 0.8, 0.85, 0.7, 0.6, 0.55, 0.45, 0.35, 0.25, 0.18, 0.12]
        out += impact(rng, n, heel_t, rng.uniform(0.0012, 0.0022), modes, t60, g, 1.0, click=0.12,
                      click_band=(1500, 7000))
        out += weight_thump(rng, n, heel_t, 0.016, 0.9)
        out += impact(rng, n, toe_t, rng.uniform(0.0018, 0.003), modes, t60, g, 0.45, click=0.05)
        sc = dsp.friction_noise(rng, samples(0.05), 900, 5000, 220, dsp.env_ad(samples(0.05), 0.006, 0.012))
        dsp.mix_at(out, sc, samples(toe_t), 0.05)
        if v in (1, 4):
            out += creak(rng, n, toe_t + rng.uniform(0.02, 0.06), rng.uniform(0.12, 0.2), 70, 160,
                         _scale([310, 520, 790, 1180, 1650], rng, 0.08), 0.035, gain=0.004, irregular=0.25)
    elif surface == "carpet":
        modes = _scale([64, 92, 128, 176, 236, 320], rng, 0.06)
        t60 = [0.09, 0.08, 0.065, 0.05, 0.04, 0.03]
        g = [1.0, 0.9, 0.7, 0.5, 0.3, 0.15]
        out += impact(rng, n, heel_t, rng.uniform(0.006, 0.010), modes, t60, g, 1.0)
        out += weight_thump(rng, n, heel_t, 0.022, 1.1, fc=110)
        out += impact(rng, n, toe_t, rng.uniform(0.008, 0.012), modes, t60, g, 0.35)
        for t0, dur, lvl in ((heel_t, 0.06, 0.035), (toe_t - 0.01, rng.uniform(0.09, 0.14), 0.05)):
            m = samples(dur)
            e = dsp.env_ad(m, dur * 0.25, dur * 0.3)
            r = dsp.friction_noise(rng, m, 1200, 7500, 380, e, 0.9)
            r += dsp.crackle(rng, m, 2500, e, 2500, 9000) * 0.5
            dsp.mix_at(out, r, samples(t0), lvl)
        out = dsp.lowpass(out, 6500, 1)
    elif surface == "linoleum":
        modes = _scale([140, 205, 330, 515, 760, 1060, 1500, 2150], rng, 0.05)
        t60 = [0.06, 0.05, 0.045, 0.04, 0.032, 0.026, 0.02, 0.016]
        g = [0.6, 0.7, 0.9, 1.0, 0.8, 0.6, 0.45, 0.3]
        out += impact(rng, n, heel_t, rng.uniform(0.0008, 0.0013), modes, t60, g, 1.0, click=0.3,
                      click_band=(2000, 8000))
        out += weight_thump(rng, n, heel_t, 0.012, 0.6, fc=160)
        out += impact(rng, n, toe_t, rng.uniform(0.0012, 0.0018), modes, t60, g, 0.5, click=0.18)
        # sticky peel as the sole leaves the floor
        m = samples(0.04)
        peel = dsp.crackle(rng, m, 9000, dsp.env_ad(m, 0.004, 0.012), 2500, 10000, 0.0003)
        dsp.mix_at(out, peel, samples(toe_t + rng.uniform(0.09, 0.14)), 0.25)
        if v in (1, 4):
            m = samples(rng.uniform(0.04, 0.075))
            f0 = rng.uniform(1500, 2300)
            rate = f0 * (1 + 0.2 * np.linspace(0, 1, m) * rng.choice([-1, 1]))
            amp = np.sin(np.linspace(0, np.pi, m)) ** 1.5
            sq = dsp.stick_slip(rng, m, rate, amp, jitter=0.02, pulse_w=0.00012)
            sq = dsp.bandpass(sq, 1200, 9000)
            dsp.mix_at(out, sq, samples(toe_t + 0.01), 0.06)
    elif surface == "tile":
        modes = _scale([190, 880, 1580, 2380, 3300, 4650, 6200], rng, 0.04)
        t60 = [0.03, 0.045, 0.04, 0.035, 0.03, 0.022, 0.016]
        g = [0.5, 0.6, 0.8, 1.0, 0.85, 0.6, 0.4]
        out += impact(rng, n, heel_t, rng.uniform(0.0003, 0.0005), modes, t60, g, 1.0, click=0.5,
                      click_band=(2500, 11000), click_decay=0.002)
        out += weight_thump(rng, n, heel_t, 0.01, 0.35, fc=180)
        out += impact(rng, n, toe_t, rng.uniform(0.0004, 0.0007), modes, t60, g, 0.55, click=0.35,
                      click_band=(2500, 11000), click_decay=0.0015)
        m = samples(0.06)
        grit = dsp.crackle(rng, m, 4000, dsp.env_ad(m, 0.003, 0.02), 3000, 12000, 0.0002)
        dsp.mix_at(out, grit, samples(toe_t), 0.12)
    elif surface == "concrete":
        modes = _scale([105, 165, 255, 410], rng, 0.06)
        t60 = [0.04, 0.035, 0.03, 0.02]
        g = [1.0, 0.8, 0.6, 0.4]
        out += impact(rng, n, heel_t, rng.uniform(0.0006, 0.0009), modes, t60, g, 0.6, click=0.55,
                      click_band=(1200, 7000), click_decay=0.0025)
        out += weight_thump(rng, n, heel_t, 0.01, 0.4, fc=150)
        out += impact(rng, n, toe_t, rng.uniform(0.0007, 0.0011), modes, t60, g, 0.3, click=0.35,
                      click_band=(1200, 7000))
        dur = rng.uniform(0.07, 0.13)
        m = samples(dur)
        e = dsp.env_ad(m, 0.01, dur * 0.35)
        sc = dsp.friction_noise(rng, m, 1500, 9000, 500, e, 0.85) * 0.5
        sc += dsp.crackle(rng, m, 7000, e, 2000, 11000, 0.0003)
        dsp.mix_at(out, sc, samples(toe_t - 0.01), 0.14)
    else:
        raise ValueError(surface)
    return out


# --------------------------------------------------------------------------- doors

DOOR_MODES = [92, 137, 204, 281, 372, 505, 690, 930, 1270]  # hollow-core interior door


def door_open(rng, v):
    n = samples(1.4)
    out = np.zeros(n)
    # knob turning: spindle friction + spring
    m = samples(0.16)
    turn = dsp.friction_noise(rng, m, 1800, 7000, 600, dsp.env_points(m, [(0, 0), (0.03, 1), (0.14, 0.6), (0.16, 0)]))
    dsp.mix_at(out, turn, samples(0.02), 0.05)
    lt = rng.uniform(0.15, 0.2)
    out += metal_click(rng, n, lt, rng.uniform(2200, 2900), 0.5, 0.03)
    # door leaves the frame: small knock + panel answer
    out += wood_knock(rng, n, lt + 0.035, rng.uniform(170, 210), 0.25, 0.002, 0.07, click=0.05)
    out += air_whoosh(rng, n, lt + 0.05, rng.uniform(0.6, 0.9), 0.05, 50, 450)
    if v % 2 == 0:
        out += creak(rng, n, lt + 0.15, rng.uniform(0.3, 0.55), 180, 420,
                     _scale([640, 1080, 1750, 2600, 3500], rng, 0.1), 0.05, gain=0.008, irregular=0.18)
    # spring returns latch
    out += metal_click(rng, n, lt + rng.uniform(0.25, 0.35), rng.uniform(2700, 3300), 0.18, 0.02)
    return room(rng, out, 0.14)


def door_close(rng, v):
    n = samples(1.3)
    out = np.zeros(n)
    hit = rng.uniform(0.28, 0.4)
    out += air_whoosh(rng, n, 0.0, hit + 0.02, 0.07, 50, 400)
    # latch bevel scrapes the strike plate just before the slab lands
    m = samples(0.03)
    scr = dsp.friction_noise(rng, m, 2500, 9000, 900, dsp.env_ad(m, 0.005, 0.01))
    dsp.mix_at(out, scr, samples(hit - 0.03), 0.08)
    modes = _scale(DOOR_MODES, rng, 0.05)
    t60 = [0.28, 0.24, 0.2, 0.16, 0.13, 0.1, 0.08, 0.06, 0.045]
    g = [1.0, 0.9, 0.8, 0.75, 0.6, 0.5, 0.4, 0.3, 0.2]
    out += impact(rng, n, hit, rng.uniform(0.0018, 0.003), modes, t60, g, 1.0, click=0.1)
    out += wood_knock(rng, n, hit + 0.002, rng.uniform(240, 300), 0.6, 0.0012, 0.05, click=0.1)
    out += weight_thump(rng, n, hit, 0.01, 0.6, fc=120)
    out += metal_click(rng, n, hit + rng.uniform(0.015, 0.03), rng.uniform(2300, 2800), 0.45, 0.04)
    # rattle in the frame
    for k in range(rng.integers(1, 3)):
        out += wood_knock(rng, n, hit + 0.05 + 0.03 * k + rng.uniform(0, 0.02), rng.uniform(200, 260),
                          0.12 / (k + 1), 0.0015, 0.04, click=0.05)
    return room(rng, out, 0.2, 0.5)


def door_locked(rng, v):
    n = samples(1.0)
    out = np.zeros(n)
    m = samples(0.1)
    turn = dsp.friction_noise(rng, m, 1500, 6000, 600, dsp.env_ad(m, 0.02, 0.04))
    dsp.mix_at(out, turn, samples(0.01), 0.05)
    t = rng.uniform(0.08, 0.12)
    for k in range(int(rng.integers(2, 4))):
        g = 1.0 if k == 0 else rng.uniform(0.5, 0.8)
        out += metal_click(rng, n, t, rng.uniform(1700, 2200), 0.6 * g, 0.03)
        out += wood_knock(rng, n, t + 0.003, rng.uniform(190, 240), 0.45 * g, 0.0015, 0.06, click=0.08)
        out += weight_thump(rng, n, t, 0.008, 0.25 * g, fc=200)
        t += rng.uniform(0.11, 0.2)
    m = samples(0.12)
    back = dsp.friction_noise(rng, m, 1500, 6000, 600, dsp.env_ad(m, 0.02, 0.04))
    dsp.mix_at(out, back, samples(min(t, 0.85)), 0.04)
    return room(rng, out, 0.16)


def door_creak(rng, v):
    dur = rng.uniform(1.3, 2.4)
    n = samples(dur + 0.4)
    out = creak(rng, n, 0.02, dur, rng.uniform(90, 160), rng.uniform(380, 700),
                _scale([520, 880, 1330, 1900, 2650, 3550], rng, 0.08), 0.06, gain=1.0,
                irregular=rng.uniform(0.1, 0.22), jitter=0.05)
    # the door slab answers faintly
    out += 0.0008 * dsp.resonator_bank(out, _scale(DOOR_MODES[:6], rng, 0.05), [0.12] * 6, [1, .8, .6, .5, .4, .3])
    out += air_whoosh(rng, n, 0.05, dur, 0.04, 50, 350) * 6
    return room(rng, out, 0.18, 0.5)


# --------------------------------------------------------------------------- drawers / cabinets

DRAWER_MODES = [178, 305, 468, 690, 975, 1390, 1950]


def _slide(rng, n, start, dur, gain, judder=(30, 60)):
    m = samples(dur)
    e = dsp.env_points(m, [(0, 0), (dur * 0.15, 1), (dur * 0.75, 0.8), (dur, 0)])
    fr = dsp.friction_noise(rng, m, 250, 3500, 150, e, 0.7)
    rate = rng.uniform(*judder) * dsp.smooth_noise(rng, m, 5, 0.7, 1.3)
    jud = dsp.stick_slip(rng, m, rate, e, jitter=0.2, pulse_w=0.002, irregular=0.2)
    body = dsp.resonator_bank(jud, _scale(DRAWER_MODES, rng, 0.06), [0.04] * 7, [1, .9, .8, .6, .5, .35, .2])
    y = fr * 0.6 + body * 0.02
    out = np.zeros(n)
    dsp.mix_at(out, y, samples(start), gain)
    return out


def _contents(rng, n, t0, t1, count, gain):
    out = np.zeros(n)
    for _ in range(count):
        t = rng.uniform(t0, t1)
        if rng.random() < 0.5:
            out += metal_click(rng, n, t, rng.uniform(2500, 4200), gain * rng.uniform(0.2, 1), 0.05)
        else:
            out += wood_knock(rng, n, t, rng.uniform(500, 900), gain * rng.uniform(0.3, 1), 0.0008, 0.02, 5, 0.2)
    return out


def drawer_open(rng, v):
    n = samples(1.1)
    dur = rng.uniform(0.4, 0.6)
    out = _slide(rng, n, 0.03, dur, 1.0)
    out += wood_knock(rng, n, 0.03, rng.uniform(160, 200), 0.25, 0.002, 0.05, click=0.05)
    out += _contents(rng, n, 0.05, dur, int(rng.integers(2, 5)), 0.25)
    out += wood_knock(rng, n, 0.03 + dur, rng.uniform(150, 190), 0.3, 0.003, 0.06, click=0.03)
    return room(rng, out, 0.12)


def drawer_close(rng, v):
    n = samples(1.0)
    dur = rng.uniform(0.25, 0.4)
    out = _slide(rng, n, 0.02, dur, 1.0, (40, 80))
    hit = 0.02 + dur
    out += wood_knock(rng, n, hit, rng.uniform(140, 175), 1.4, 0.0015, 0.09, click=0.15)
    out += weight_thump(rng, n, hit, 0.008, 0.5, fc=180)
    out += _contents(rng, n, hit + 0.01, hit + 0.12, int(rng.integers(2, 5)), 0.3)
    return room(rng, out, 0.14)


def cabinet_open(rng, v):
    n = samples(0.9)
    out = np.zeros(n)
    t = rng.uniform(0.03, 0.06)
    out += plastic_click(rng, n, t, rng.uniform(1300, 1800), 0.5, 0.012)
    out += wood_knock(rng, n, t + 0.004, rng.uniform(290, 360), 0.45, 0.001, 0.05, click=0.1)
    out += air_whoosh(rng, n, t + 0.02, rng.uniform(0.3, 0.45), 0.03, 80, 600)
    if v in (1, 3):
        out += creak(rng, n, t + 0.08, rng.uniform(0.15, 0.3), 250, 520,
                     _scale([800, 1300, 2050, 2900], rng, 0.1), 0.04, gain=0.006, irregular=0.2)
    return room(rng, out, 0.12)


def cabinet_close(rng, v):
    n = samples(0.9)
    out = np.zeros(n)
    hit = rng.uniform(0.14, 0.24)
    out += air_whoosh(rng, n, 0.0, hit, 0.04, 80, 600)
    out += wood_knock(rng, n, hit, rng.uniform(270, 340), 1.0, 0.0013, 0.08, click=0.15)
    out += plastic_click(rng, n, hit + rng.uniform(0.006, 0.015), rng.uniform(1300, 1700), 0.45, 0.012)
    out += weight_thump(rng, n, hit, 0.006, 0.25, fc=220)
    return room(rng, out, 0.14)


# --------------------------------------------------------------------------- switches & buttons

def _wall_switch(rng, lower: bool):
    n = samples(0.35)
    out = np.zeros(n)
    t = 0.01
    m = samples(0.012)
    lever = dsp.friction_noise(rng, m, 2000, 8000, 900, dsp.env_ad(m, 0.003, 0.004))
    dsp.mix_at(out, lever, samples(t), 0.08)
    t += rng.uniform(0.006, 0.011)
    base = rng.uniform(1700, 2100) * (0.9 if lower else 1.0)
    out += plastic_click(rng, n, t, base, 1.0, 0.01)
    out += metal_click(rng, n, t + 0.0005, rng.uniform(3800, 4600), 0.35, 0.012)
    out += wood_knock(rng, n, t, rng.uniform(210, 260), 0.35, 0.0007, 0.025, 6, 0.0)  # wall box / plate
    out += plastic_click(rng, n, t + rng.uniform(0.012, 0.02), base * 1.2, 0.18, 0.008)  # settle
    return room(rng, out, 0.1)


def switch_on(rng, v):
    return _wall_switch(rng, False)


def switch_off(rng, v):
    return _wall_switch(rng, True)


def lamp_click(rng, v):
    n = samples(0.35)
    out = np.zeros(n)
    m = samples(0.04)
    tw = dsp.friction_noise(rng, m, 2000, 9000, 700, dsp.env_ad(m, 0.02, 0.01))
    dsp.mix_at(out, tw, samples(0.005), 0.05)
    t = 0.04
    out += metal_click(rng, n, t, rng.uniform(2900, 3500), 1.0, 0.03)
    out += plastic_click(rng, n, t + 0.001, rng.uniform(1100, 1400), 0.5, 0.012)
    out += metal_click(rng, n, t + rng.uniform(0.012, 0.025), rng.uniform(3600, 4300), 0.35, 0.02)
    return room(rng, out, 0.1)


def button_press(rng, v):
    n = samples(0.4)
    out = np.zeros(n)
    t = 0.01
    out += plastic_click(rng, n, t, rng.uniform(950, 1250), 1.0, 0.012)
    out += weight_thump(rng, n, t, 0.004, 0.2, fc=400)
    out += plastic_click(rng, n, t + rng.uniform(0.09, 0.16), rng.uniform(1300, 1600), 0.45, 0.008)
    return room(rng, out, 0.1)


# --------------------------------------------------------------------------- handling

def pickup(rng, v):
    n = samples(0.6)
    out = np.zeros(n)
    m = samples(rng.uniform(0.08, 0.15))
    hand = dsp.friction_noise(rng, m, 600, 6000, 250, dsp.env_ad(m, 0.02, 0.03), 0.8)
    dsp.mix_at(out, hand, samples(0.0), 0.12)
    t = rng.uniform(0.05, 0.1)
    out += wood_knock(rng, n, t, rng.uniform(380, 520), 0.25, 0.0025, 0.03, 7, 0.03)
    m = samples(rng.uniform(0.04, 0.09))
    scr = dsp.friction_noise(rng, m, 900, 7000, 400, dsp.env_ad(m, 0.005, 0.02))
    dsp.mix_at(out, scr, samples(t + 0.01), 0.18)
    m = samples(0.25)
    cloth = dsp.friction_noise(rng, m, 400, 5000, 120, dsp.env_ad(m, 0.06, 0.06), 0.9)
    dsp.mix_at(out, cloth, samples(t + 0.05), 0.06)
    return room(rng, out, 0.1)


def putdown(rng, v):
    n = samples(0.6)
    out = np.zeros(n)
    t = rng.uniform(0.04, 0.08)
    table = _scale([185, 262, 418, 612, 885, 1290, 1880, 2620], rng, 0.05)
    t60 = [0.1, 0.09, 0.08, 0.07, 0.06, 0.045, 0.035, 0.025]
    out += impact(rng, n, t, rng.uniform(0.0015, 0.003), table, t60, [1, .9, .9, .8, .6, .5, .35, .2], 1.0, 0.12)
    out += plastic_click(rng, n, t, rng.uniform(1200, 2200), 0.2, 0.02)
    t2 = t + rng.uniform(0.015, 0.04)
    out += impact(rng, n, t2, 0.002, table, t60, [1, .9, .9, .8, .6, .5, .35, .2], 0.3, 0.05)
    m = samples(0.15)
    cloth = dsp.friction_noise(rng, m, 500, 5000, 120, dsp.env_ad(m, 0.03, 0.04), 0.9)
    dsp.mix_at(out, cloth, samples(t + 0.06), 0.04)
    return room(rng, out, 0.12)


def _gestures(rng, n, count, min_d, max_d):
    e = np.zeros(n)
    for _ in range(count):
        d = rng.uniform(min_d, max_d)
        m = samples(d)
        s = rng.uniform(0, max(0.0, dsp.secs(n) - d - 0.05))
        g = np.sin(np.linspace(0, np.pi, m)) ** rng.uniform(0.7, 2.0) * rng.uniform(0.4, 1.0)
        dsp.mix_at(e, g, samples(s))
    return np.clip(e, 0, 1.3)


def paper_rustle(rng, v):
    dur = rng.uniform(0.8, 1.4)
    n = samples(dur + 0.2)
    e = _gestures(rng, n, int(rng.integers(2, 5)), 0.15, 0.5)
    crink = dsp.crackle(rng, n, 6000, e, 1500, 11000, 0.0004, 1.6)
    flap = dsp.bandpass(dsp.white(rng, n), 250, 2500) * dsp.lowpass(e, 20) * 0.08
    rub = dsp.friction_noise(rng, n, 2500, 10000, 300, e, 0.8) * 0.12
    out = crink + flap + rub
    return room(rng, out, 0.1)


def cloth_rustle(rng, v):
    dur = rng.uniform(0.6, 1.2)
    n = samples(dur + 0.2)
    e = _gestures(rng, n, int(rng.integers(1, 4)), 0.2, 0.6)
    # fabric moves in little slips and catches, not as a steady hiss
    slips = np.abs(dsp.lowpass(dsp.white(rng, n), 45, 2))
    slips = (slips / (slips.max() + 1e-12)) ** 2.2
    rub = dsp.friction_noise(rng, n, 300, 5500, 220, e * (0.15 + 0.85 * slips / (slips.mean() * 2.5)), 0.7)
    rub = dsp.eq(rub, "peak", 1300, 0.7, 4)
    rub = dsp.lowpass(rub, 6000, 2)
    fib = dsp.crackle(rng, n, 1200, e * slips * 3, 1800, 7000, 0.0005) * 0.6
    return room(rng, rub * 0.4 + fib, 0.08)


def book_slide(rng, v):
    n = samples(1.0)
    dur = rng.uniform(0.3, 0.55)
    m = samples(dur)
    e = dsp.env_points(m, [(0, 0), (0.05, 1), (dur * 0.7, 0.9), (dur, 0)])
    fr = dsp.friction_noise(rng, m, 300, 5000, 200, e, 0.75)
    jud = dsp.stick_slip(rng, m, rng.uniform(25, 50) * np.ones(m), e, jitter=0.3, pulse_w=0.003, irregular=0.25)
    jud = dsp.resonator_bank(jud, _scale([220, 390, 610, 900], rng, 0.08), [0.03] * 4, [1, .8, .6, .4])
    out = np.zeros(n)
    dsp.mix_at(out, fr * 0.5 + jud * 0.015, samples(0.02))
    out += wood_knock(rng, n, 0.02 + dur, rng.uniform(170, 220), 0.4, 0.004, 0.06, click=0.02)
    return room(rng, out, 0.12)


def thud_soft(rng, v):
    n = samples(0.8)
    out = np.zeros(n)
    t = 0.02
    modes = _scale([52, 78, 116, 168, 236, 330], rng, 0.07)
    out += impact(rng, n, t, rng.uniform(0.008, 0.014), modes, [0.16, 0.13, 0.1, 0.08, 0.06, 0.04],
                  [1, .9, .7, .5, .35, .2], 1.0)
    out += weight_thump(rng, n, t, 0.02, 1.2, fc=120)
    m = samples(0.12)
    puff = dsp.lowpass(dsp.white(rng, m), 900) * dsp.env_ad(m, 0.004, 0.03)
    dsp.mix_at(out, puff, samples(t), 0.15)
    return room(rng, out, 0.16, 0.5)


def window_rattle(rng, v):
    n = samples(1.2)
    out = np.zeros(n)
    glass = _scale([176, 305, 462, 672, 915, 1390, 2080, 2950], rng, 0.05)
    t60 = [0.12, 0.1, 0.09, 0.08, 0.07, 0.05, 0.04, 0.03]
    g = [0.6, 0.8, 1.0, 0.9, 0.7, 0.5, 0.4, 0.25]
    t = 0.02
    k = int(rng.integers(5, 11))
    for i in range(k):
        a = (1 - i / k) ** 1.2 * rng.uniform(0.5, 1.0)
        out += impact(rng, n, t, rng.uniform(0.0006, 0.0012), glass, t60, g, a, click=0.2,
                      click_band=(2000, 9000))
        if rng.random() < 0.5:
            out += wood_knock(rng, n, t + 0.002, rng.uniform(260, 330), 0.4 * a, 0.0012, 0.03, click=0.05)
        t += rng.uniform(0.018, 0.06)
    return room(rng, out, 0.16)


def faucet_squeak(rng, v):
    dur = rng.uniform(0.3, 0.65)
    n = samples(dur + 0.3)
    out = creak(rng, n, 0.02, dur, rng.uniform(450, 650), rng.uniform(800, 1250),
                _scale([1180, 2290, 3650, 5050, 6800], rng, 0.05), 0.05, gain=1.0,
                irregular=0.06, jitter=0.025)
    out += metal_click(rng, n, 0.02 + dur, 2400, 0.08, 0.04)
    return room(rng, out, 0.18, 0.35, (2.4, 1.8, 2.44))  # small bathroom/kitchen corner


def glass_clink(rng, v):
    n = samples(1.6)
    out = np.zeros(n)
    f1 = rng.uniform(1150, 1750)
    out += glass_ring(rng, n, 0.01, f1, 1.0, rng.uniform(0.7, 1.1))
    if v % 2 == 1:
        out += glass_ring(rng, n, 0.01 + rng.uniform(0.06, 0.14), f1 * rng.uniform(1.0, 1.08),
                          rng.uniform(0.3, 0.6), 0.8)
    # set on a wooden counter: body thump
    out += wood_knock(rng, n, 0.01, rng.uniform(250, 320), 0.15, 0.0008, 0.03, 6, 0.0)
    return room(rng, out, 0.14)


# --------------------------------------------------------------------------- appliances

def _hum_burst(rng, n, start, dur, f0=60.0, gain=1.0, decay=0.25):
    m = samples(dur)
    t = dsp.tvec(m)
    y = np.zeros(m)
    for h in range(1, 14):
        y += (1.0 / h ** 0.8) * np.sin(dsp.TAU * f0 * h * t + rng.uniform(0, dsp.TAU))
    y = dsp.asym_saturate(y * 0.6, 2.5, 0.2)
    y *= dsp.env_ad(m, 0.01, decay)
    out = np.zeros(n)
    dsp.mix_at(out, y, samples(start), gain)
    return out


def tv_on(rng, v):
    n = samples(2.2)
    out = np.zeros(n)
    out += plastic_click(rng, n, 0.01, rng.uniform(800, 1000), 1.0, 0.02)
    out += weight_thump(rng, n, 0.01, 0.004, 0.3, fc=300)
    out += plastic_click(rng, n, 0.05, rng.uniform(1100, 1300), 0.3, 0.01)
    rt = rng.uniform(0.12, 0.2)
    out += metal_click(rng, n, rt, rng.uniform(1800, 2300), 0.5, 0.02)  # power relay
    # degauss: a fat 60 Hz buzz that dies away, with a low magnetic thump
    out += _hum_burst(rng, n, rt + 0.005, 1.4, 60.0, 1.6, rng.uniform(0.3, 0.45))
    out += weight_thump(rng, n, rt + 0.005, 0.03, 1.5, fc=90)
    # EHT crackle as the screen charges
    e = np.zeros(n)
    s0 = samples(rt + 0.1)
    e[s0:] = dsp.env_ad(n - s0, 0.05, 0.4)
    out += dsp.crackle(rng, n, 35, e, 1500, 12000, 0.0003, 2.0) * 1.0
    # flyback whine fades in (NTSC line rate)
    t = dsp.tvec(n)
    wh = np.sin(dsp.TAU * 15734.0 * t) * np.clip((t - rt - 0.2) / 0.6, 0, 1)
    out += wh * 0.004
    # speaker un-mutes into a little hiss
    hiss = dsp.bandpass(dsp.white(rng, n), 300, 6000) * np.clip((t - rt - 0.9) / 0.5, 0, 1) * 0.01
    out += hiss
    return room(rng, out, 0.12)


def tv_off(rng, v):
    n = samples(1.3)
    out = np.zeros(n)
    out += plastic_click(rng, n, 0.01, rng.uniform(800, 1000), 1.0, 0.02)
    out += weight_thump(rng, n, 0.01, 0.004, 0.3, fc=300)
    t = dsp.tvec(n)
    # collapse: one sharp static tick, whine and hiss stop
    out += metal_click(rng, n, 0.03, rng.uniform(1500, 2000), 0.25, 0.015)
    e = np.zeros(n)
    s0 = samples(0.04)
    e[s0:] = dsp.env_ad(n - s0, 0.01, 0.25)
    out += dsp.crackle(rng, n, 30, e, 1500, 12000, 0.0003, 2.0) * 1.0
    whine = np.sin(dsp.TAU * 15734.0 * t) * np.exp(-t / 0.08) * 0.004
    out += whine
    out += _hum_burst(rng, n, 0.025, 0.3, 60.0, 0.5, 0.06)
    return room(rng, out, 0.12)


def phone_pickup(rng, v):
    n = samples(0.7)
    out = np.zeros(n)
    t = 0.02
    out += plastic_click(rng, n, t, rng.uniform(700, 900), 0.8, 0.025)
    out += weight_thump(rng, n, t, 0.005, 0.2, fc=300)
    for k in range(2):
        out += metal_click(rng, n, t + 0.02 + 0.012 * k + rng.uniform(0, 0.01), rng.uniform(2600, 3400),
                           0.35 / (k + 1), 0.02)
    m = samples(0.3)
    cord = dsp.friction_noise(rng, m, 500, 4500, 100, dsp.env_ad(m, 0.05, 0.08), 0.9)
    dsp.mix_at(out, cord, samples(t + 0.05), 0.06)
    return room(rng, out, 0.12)


def phone_hangup(rng, v):
    n = samples(1.2)
    out = np.zeros(n)
    t = 0.02
    out += plastic_click(rng, n, t, rng.uniform(650, 850), 1.0, 0.03)
    out += weight_thump(rng, n, t, 0.006, 0.4, fc=250)
    t2 = t + rng.uniform(0.02, 0.05)
    out += plastic_click(rng, n, t2, rng.uniform(750, 950), 0.7, 0.025)
    out += metal_click(rng, n, t2 + 0.006, rng.uniform(2500, 3100), 0.4, 0.02)
    if v == 2:  # ringer bell answers the hook-switch transient
        out += glass_ring(rng, n, t2 + 0.01, 1180.0, 0.025, 0.6)
    return room(rng, out, 0.12)


def fridge_open(rng, v):
    n = samples(1.2)
    out = np.zeros(n)
    t = rng.uniform(0.06, 0.1)
    m = samples(0.06)
    peel = dsp.crackle(rng, m, 5000, dsp.env_ad(m, 0.01, 0.02), 600, 6000, 0.0006)
    dsp.mix_at(out, peel, samples(t - 0.02), 0.25)
    # seal lets go: low pressure pop
    out += weight_thump(rng, n, t, 0.02, 1.0, fc=90)
    m = samples(0.15)
    suck = dsp.bandpass(dsp.white(rng, m), 120, 1200) * dsp.env_ad(m, 0.005, 0.04)
    dsp.mix_at(out, suck, samples(t), 0.15)
    for _ in range(int(rng.integers(2, 5))):
        out += glass_ring(rng, n, t + rng.uniform(0.02, 0.25), rng.uniform(900, 1600), rng.uniform(0.04, 0.12), 0.35)
    out += air_whoosh(rng, n, t, rng.uniform(0.5, 0.7), 0.05, 50, 400)
    return room(rng, out, 0.14)


def fridge_close(rng, v):
    n = samples(1.3)
    out = np.zeros(n)
    hit = rng.uniform(0.2, 0.3)
    out += air_whoosh(rng, n, 0.0, hit, 0.06, 50, 400)
    modes = _scale([56, 83, 121, 168, 238, 331, 470], rng, 0.05)
    out += impact(rng, n, hit, rng.uniform(0.006, 0.01), modes, [0.18, 0.15, 0.12, 0.1, 0.08, 0.06, 0.04],
                  [1, .9, .8, .6, .45, .3, .2], 1.0)
    out += weight_thump(rng, n, hit, 0.02, 1.2, fc=100)
    m = samples(0.1)
    fump = dsp.lowpass(dsp.white(rng, m), 500) * dsp.env_ad(m, 0.003, 0.03)
    dsp.mix_at(out, fump, samples(hit), 0.2)
    for _ in range(int(rng.integers(3, 6))):
        out += glass_ring(rng, n, hit + rng.uniform(0.005, 0.2), rng.uniform(850, 1700), rng.uniform(0.05, 0.15), 0.35)
    return room(rng, out, 0.15)


def tape_insert(rng, v):
    n = samples(2.6)
    out = np.zeros(n)
    # flap and cassette slide
    out += plastic_click(rng, n, 0.02, rng.uniform(900, 1200), 0.4, 0.015)
    sd = rng.uniform(0.25, 0.35)
    m = samples(sd)
    sl = dsp.friction_noise(rng, m, 500, 6000, 300, dsp.env_points(m, [(0, 0), (0.03, 1), (sd, 0.6)]), 0.6)
    dsp.mix_at(out, sl, samples(0.03), 0.12)
    t = 0.03 + sd
    out += plastic_click(rng, n, t, rng.uniform(600, 800), 0.8, 0.03)
    # mechanism grabs it: motor whirr with gear mesh
    md = rng.uniform(0.9, 1.2)
    m = samples(md)
    tt = dsp.tvec(m)
    f = 95 * (1 + 0.3 * (1 - np.exp(-tt / 0.08))) * dsp.smooth_noise(rng, m, 8, 0.97, 1.03)
    ph = dsp.TAU * np.cumsum(f) / SR
    motor = sum((1 / h) * np.sin(h * ph) for h in range(1, 8))
    gear = dsp.bandpass(dsp.white(rng, m), 700, 2500) * (0.5 + 0.5 * np.sin(ph * 12)) ** 2
    me = dsp.env_points(m, [(0, 0), (0.03, 1), (md - 0.1, 0.9), (md, 0)])
    dsp.mix_at(out, (motor * 0.04 + gear * 0.1) * me, samples(t + 0.05))
    for k in range(3):
        out += plastic_click(rng, n, t + 0.1 + k * md / 3 + rng.uniform(0, 0.05), rng.uniform(500, 900), 0.4, 0.03)
    out += metal_click(rng, n, t + md + 0.05, 1800, 0.3, 0.03)
    out += plastic_click(rng, n, t + md + 0.06, 650, 0.6, 0.03)
    out += weight_thump(rng, n, t + md + 0.06, 0.006, 0.4, fc=200)
    return room(rng, out, 0.1)


# --------------------------------------------------------------------------- UI

def ui_tick(rng, v):
    n = samples(0.12)
    out = plastic_click(rng, n, 0.003, rng.uniform(2200, 2600), 1.0, 0.006)
    return dsp.lowpass(out, 9000, 1)


def ui_open(rng, v):
    n = samples(0.25)
    out = plastic_click(rng, n, 0.003, rng.uniform(1100, 1300), 1.0, 0.012)
    out += weight_thump(rng, n, 0.003, 0.004, 0.25, fc=400)
    out += plastic_click(rng, n, 0.035, rng.uniform(1700, 1900), 0.3, 0.008)
    return dsp.lowpass(out, 9000, 1)


def ui_close(rng, v):
    n = samples(0.22)
    out = plastic_click(rng, n, 0.003, rng.uniform(1500, 1700), 0.8, 0.01)
    out += plastic_click(rng, n, 0.022, rng.uniform(1000, 1200), 0.5, 0.012)
    return dsp.lowpass(out, 9000, 1)
