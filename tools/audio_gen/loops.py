"""Seamless loops: ambience beds (stereo) and positional hums (mono).

Every loop is built from *periodic* material only (FFT-shaped noise, integer-
cycle tones and LFOs, circularly placed events, circular filtering and
convolution), so sample N-1 flows into sample 0 exactly as any other pair of
neighbouring samples would. No crossfade is needed; the analyser checks it.
"""
from __future__ import annotations

import numpy as np

from . import dsp
from .dsp import SR, TAU, samples
from . import distant


# --------------------------------------------------------------------------- periodic helpers

def phase_from_rate(rate: np.ndarray, cycles: int | None = None) -> np.ndarray:
    """Phase (in cycles) for a rate curve, rescaled to land on an integer cycle count."""
    ph = np.cumsum(rate) / SR
    k = cycles if cycles is not None else max(1, int(round(ph[-1])))
    return ph * (k / ph[-1]), k


def pulses_c(rng: np.random.Generator, n: int, rate: np.ndarray, amp: np.ndarray,
             amp_jitter: float = 0.3, time_jitter: float = 0.0) -> np.ndarray:
    """Periodic impulse train following a rate curve (integer pulse count over n)."""
    ph, k = phase_from_rate(rate)
    idx = np.searchsorted(ph, np.arange(k) + 0.5)
    if time_jitter > 0:
        per = SR / np.maximum(rate[np.minimum(idx, n - 1)], 1)
        idx = idx + (rng.standard_normal(k) * time_jitter * per).astype(int)
    idx %= n
    out = np.zeros(n)
    a = amp[idx] * (1 + amp_jitter * rng.standard_normal(k))
    np.add.at(out, idx, a)
    return out


def event_env_c(rng: np.random.Generator, n: int, starts: list[float], durs: list[float],
                attack: float, release: float, shape: float = 1.0) -> np.ndarray:
    """Sum of trapezoid envelopes placed circularly (start times in seconds)."""
    e = np.zeros(n)
    for s, d in zip(starts, durs):
        m = samples(d)
        a = min(samples(attack), m // 2)
        r = min(samples(release), m // 2)
        seg = np.ones(m)
        seg[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
        seg[m - r:] = np.cos(np.linspace(0, np.pi / 2, r)) ** 2
        dsp.mix_circular(e, seg ** shape, samples(s))
    return e


def place(x: np.ndarray, pan: float, itd_ms: float = 0.0) -> np.ndarray:
    """Mono -> stereo with constant-power pan (-1..1) and a circular inter-aural delay."""
    th = (pan + 1) * np.pi / 4
    L = x * np.cos(th)
    R = x * np.sin(th)
    d = samples(abs(itd_ms) / 1000.0) * int(np.sign(pan))
    if d > 0:
        L = np.roll(L, d)
    elif d < 0:
        R = np.roll(R, -d)
    return np.stack([L, R], axis=1)


def outdoor_ir(rng: np.random.Generator, stereo: bool = True, length: float = 1.6) -> np.ndarray:
    """Suburban outdoor response: a few slap echoes off houses + a thin diffuse tail."""
    n = samples(length)
    ch = 2 if stereo else 1
    ir = np.zeros((n, ch))
    for c in range(ch):
        for _ in range(9):
            d = rng.uniform(0.03, 0.35)
            ir[samples(d), c] += rng.uniform(0.15, 0.5) * np.exp(-d / 0.25)
        t = dsp.tvec(n)
        tail = dsp.lowpass(dsp.white(rng, n), 2500) * np.exp(-6.91 * t / 1.1) * 0.03
        tail *= np.clip((t - 0.04) / 0.1, 0, 1)
        ir[:, c] = dsp.lowpass(ir[:, c], 4000, 1) + tail
    return ir if stereo else ir[:, 0]


def noise_c(rng, n, lo, hi, slope=0.0):
    return dsp.colored(rng, n, slope, lo=lo, hi=hi)


# --------------------------------------------------------------------------- ambience beds (stereo)

def room_tone(rng: np.random.Generator) -> np.ndarray:
    n = samples(48.0)
    common = dsp.colored(rng, n, -5.0, lo=18, hi=5000)
    out = np.zeros((n, 2))
    for c in range(2):
        own = dsp.colored(rng, n, -4.0, lo=18, hi=7000)
        out[:, c] = 0.55 * common + 0.75 * own
    # axial room modes of a ~4 m living room: the "pressure" of a closed room
    for f, g in ((42.0, 5.0), (49.0, 3.5), (71.0, 3.0), (94.0, 2.0), (141.0, 1.5)):
        out = dsp.eq_circular(out, "peak", f, 4.0, g)
    # slow breathing of the building (thermal, distant HVAC elsewhere on the street)
    lfo = dsp.periodic_lfo(rng, n, 6, 0.85, 1.15)
    rumble = dsp.lowpass_c(dsp.colored(rng, n, -6.0, lo=15), 70, 2)
    rumble /= np.std(rumble)
    out += 0.6 * rumble[:, None] * lfo[:, None]
    # air: very faint high hiss, as a quiet room never measures zero
    for c in range(2):
        out[:, c] += 0.03 * dsp.colored(rng, n, 0.0, lo=4000, hi=14000)
    # faint mains hum leaking from house wiring (barely there)
    t = dsp.tvec(n)
    hum = sum((0.6 / h) * np.sin(TAU * 60 * h * t + rng.uniform(0, TAU)) for h in (1, 2, 3))
    out += 0.02 * hum[:, None]
    return out


def _cicada(rng, n, start, dur, carrier, pulse_rate, gain):
    """One dog-day cicada song: buzz swells, holds, then sags in pitch as it ends."""
    m = samples(dur)
    t = np.arange(m) / SR
    e = np.clip(t / (dur * 0.25), 0, 1) ** 1.5
    e *= np.clip((dur - t) / (dur * 0.3), 0, 1) ** 0.8
    sag = 1.0 - 0.18 * np.clip((t - dur * 0.7) / (dur * 0.3), 0, 1) ** 2
    rate = pulse_rate * sag * dsp.smooth_noise(rng, m, 3, 0.97, 1.03)
    ph = np.cumsum(rate) / SR
    idx = np.searchsorted(ph, np.arange(int(ph[-1])) + 0.5)
    imp = np.zeros(m)
    np.add.at(imp, np.minimum(idx, m - 1), 1 + 0.4 * rng.standard_normal(len(idx)))
    am = 0.6 + 0.4 * np.sin(TAU * np.cumsum(dsp.smooth_noise(rng, m, 2, 38, 52)) / SR)
    y = dsp.resonator_bank(imp * e * am, [carrier * s for s in (1.0, 0.93, 1.08)], [0.006, 0.004, 0.004],
                           [1, 0.5, 0.4])
    y += 0.3 * dsp.bandpass(dsp.white(rng, m), carrier * 0.7, carrier * 1.4) * e * am
    out = np.zeros(n)
    dsp.mix_circular(out, y * gain, samples(start))
    return out


def _bird_chirps(rng, n, count, gain):
    out = np.zeros(n)
    for _ in range(count):
        s = rng.uniform(0, dsp.secs(n))
        k = int(rng.integers(1, 5))
        f0 = rng.uniform(2800, 4800)
        for j in range(k):
            d = rng.uniform(0.04, 0.12)
            m = samples(d)
            tt = np.arange(m) / SR
            sweep = f0 * (1 + rng.uniform(-0.35, 0.35) * tt / d)
            y = np.sin(TAU * np.cumsum(sweep) / SR) * np.sin(np.pi * tt / d) ** 2
            y += 0.2 * np.sin(2 * TAU * np.cumsum(sweep) / SR) * np.sin(np.pi * tt / d) ** 2
            dsp.mix_circular(out, y * gain * rng.uniform(0.4, 1.0), samples(s + j * rng.uniform(0.12, 0.2)))
    return out


def _mourning_dove(rng, n, start, gain):
    """coo-OOO-oo ... oo ... oo (the classic summer-suburb call), ~ 500 Hz."""
    out = np.zeros(n)
    notes = [(0.0, 0.35, 470, 520), (0.42, 0.55, 560, 500), (1.15, 0.45, 500, 470),
             (1.8, 0.45, 500, 470), (2.45, 0.45, 495, 465)]
    for t0, d, fa, fb in notes:
        m = samples(d)
        tt = np.arange(m) / SR
        f = np.interp(tt, [0, d * 0.3, d], [fa * 0.92, fa, fb])
        ph = TAU * np.cumsum(f) / SR
        y = np.sin(ph) + 0.15 * np.sin(2 * ph) + 0.03 * dsp.lowpass(dsp.white(rng, m), 900)
        y *= np.sin(np.pi * tt / d) ** 1.5 * (0.6 + 0.4 * np.sin(TAU * 9 * tt))
        dsp.mix_circular(out, y * gain, samples(start + t0))
    return out


def _crow(rng, n, start, gain):
    out = np.zeros(n)
    t0 = 0.0
    for _ in range(int(rng.integers(2, 5))):
        d = rng.uniform(0.25, 0.4)
        m = samples(d)
        tt = np.arange(m) / SR
        f = np.interp(tt, [0, d * 0.2, d], [520, 620, 480]) * rng.uniform(0.95, 1.05)
        ph = TAU * np.cumsum(f * (1 + 0.03 * dsp.white(rng, m))) / SR
        src = sum(np.sin(h * ph) / h ** 0.6 for h in range(1, 12))
        src = dsp.asym_saturate(src * 0.3, 3, 0.2) + 0.4 * dsp.bandpass(dsp.white(rng, m), 600, 3000)
        y = dsp.eq(src, "peak", 1300, 1.5, 9) * np.sin(np.pi * tt / d) ** 0.7
        dsp.mix_circular(out, y * gain, samples(start + t0))
        t0 += d + rng.uniform(0.25, 0.45)
    return out


def outside_afternoon(rng: np.random.Generator) -> np.ndarray:
    L = 60.0
    n = samples(L)
    out = np.zeros((n, 2))
    # --- cicadas in the trees: overlapping songs, never quite in sync
    for _ in range(9):
        s = rng.uniform(0, L)
        d = rng.uniform(9, 18)
        c = _cicada(rng, n, s, d, rng.uniform(4200, 5600), rng.uniform(180, 260), rng.uniform(0.6, 1.6))
        out += place(c, rng.uniform(-0.8, 0.8), 0.3)
    # constant distant drone of many insects (ground crickets / far cicadas)
    for c in range(2):
        drone = dsp.colored(rng, n, 0.0, lo=3800, hi=6500)
        am = 0.7 + 0.3 * np.sin(TAU * 42 * np.arange(n) / SR + rng.uniform(0, TAU)) ** 2
        out[:, c] += 0.12 * drone * am * dsp.periodic_lfo(rng, n, 5, 0.6, 1.0)
    # --- far traffic wash: a road a few blocks away
    wash = np.zeros((n, 2))
    for c in range(2):
        wash[:, c] = dsp.lowpass_c(dsp.colored(rng, n, -4.0, lo=40, hi=1600), 900, 2)
    swell = dsp.periodic_lfo(rng, n, 9, 0.35, 1.0, tilt=0.6)
    out += 0.3 * wash * swell[:, None]
    # --- a very distant mower for part of the minute
    mow = distant.mower_core(rng, n, 30.0, circular=True)
    me = event_env_c(rng, n, [rng.uniform(0, L)], [rng.uniform(22, 32)], 6.0, 7.0)
    out += place(dsp.distance(mow * me, 250, circular=True) * 0.25, rng.uniform(-0.6, 0.6), 0.2)
    # --- birds, distant
    out += place(_bird_chirps(rng, n, 9, 0.3), -0.4, 0.2) + place(_bird_chirps(rng, n, 7, 0.25), 0.5, 0.2)
    out += place(_mourning_dove(rng, n, rng.uniform(5, 20), 0.25), rng.uniform(-0.7, 0.7), 0.3)
    out += place(_mourning_dove(rng, n, rng.uniform(35, 50), 0.2), rng.uniform(-0.7, 0.7), 0.3)
    out += place(_crow(rng, n, rng.uniform(20, 32), 0.08), rng.uniform(-0.8, 0.8), 0.3)
    # outdoor space, then heard through the closed house
    out = dsp.reverb_circular(out, outdoor_ir(rng, True), 0.6)
    # through a closed single-pane window: highs drop ~12-15 dB, a little lift
    # near the glass coincidence frequency, the low end passes
    out = dsp.lowpass_c(out, 1800, 1)
    out = dsp.eq_circular(out, "peak", 3600, 1.2, 4)
    out = dsp.lowpass_c(out, 9000, 2)
    # a little in-room colour so it sits with room_tone
    out = dsp.eq_circular(out, "lowshelf", 120, 0.7, -3)
    return out


def wind_light(rng: np.random.Generator) -> np.ndarray:
    L = 40.0
    n = samples(L)
    gust = dsp.periodic_lfo(rng, n, 10, 0.0, 1.0, tilt=0.8) ** 1.8
    out = np.zeros((n, 2))
    for c in range(2):
        g = np.roll(gust, samples(rng.uniform(0.05, 0.4)))
        low = dsp.lowpass_c(dsp.colored(rng, n, -3.0, lo=30, hi=2000), 450, 2)
        leaves = dsp.colored(rng, n, 0.0, lo=1200, hi=6000)
        flutter = np.abs(dsp.lowpass_c(dsp.white(rng, n), 30, 1))
        flutter /= flutter.max()
        out[:, c] = low * (0.25 + 0.75 * g) + 0.5 * leaves * flutter * g ** 1.5
    # faint whistle at a window gap during stronger gusts
    whistle = dsp.eq_circular(dsp.white(rng, n), "bandpass", 880, 40) * 0.6
    out += place(whistle * gust ** 3, 0.3)
    out = dsp.through_wall(out, circular=True, closed_window=False)
    return out


# --------------------------------------------------------------------------- hums / positional loops (mono)

def fridge_hum(rng: np.random.Generator) -> np.ndarray:
    L = 12.0
    n = samples(L)
    t = dsp.tvec(n)
    rot = 57.5  # induction motor with slip: 3450 rpm
    y = np.zeros(n)
    # magnetostriction at twice mains + harmonics
    for h, a in ((1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.08), (6, 0.04)):
        y += a * np.sin(TAU * 120 * h * t + rng.uniform(0, TAU))
    y += 0.25 * np.sin(TAU * 60 * t)
    # rotational components beating against the 120 Hz
    # motor slip wanders a little with load; phase is forced onto whole cycles
    rot_ph, _ = phase_from_rate(rot + 0.25 * dsp.periodic_lfo(rng, n, 4, -1, 1))
    for h, a in ((1, 0.5), (2, 0.35), (3, 0.2), (4, 0.15), (6, 0.08), (8, 0.05)):
        y += a * np.sin(TAU * h * rot_ph + rng.uniform(0, TAU))
    wob = dsp.periodic_lfo(rng, n, 7, 0.85, 1.1)
    y *= wob
    # piston "chug" texture: mechanical noise modulated at rotation rate
    mech = dsp.bandpass_c(dsp.white(rng, n), 180, 2200, 2)
    chug = (0.5 + 0.5 * np.sin(TAU * rot_ph)) ** 3
    y += 0.22 * mech * (0.25 + chug)
    # fan + airflow behind the kick plate
    fan = dsp.colored(rng, n, -4.5, lo=80, hi=2500)
    y += 0.12 * fan + 0.06 * np.sin(TAU * 2 * rot * t)
    # loose panel buzzing when vibration builds up
    vib = np.sin(TAU * 120 * t) * dsp.periodic_lfo(rng, n, 5, 0.5, 1.25, tilt=0.5)
    hits = np.maximum(vib - 0.98, 0)
    hits = np.diff(hits, prepend=hits[-1])
    hits = np.maximum(hits, 0) * 40
    rat = dsp.filt_circular(hits, dsp._sos("bandpass", [900, 4500], 2))
    rat = dsp.eq_circular(rat, "peak", 1700, 6, 8)
    y += rat
    # body / cabinet coloration and kitchen
    y = dsp.eq_circular(y, "peak", 240, 2, 3)
    y = dsp.lowpass_c(y, 6000, 2)
    return y


def clock_tick(rng: np.random.Generator) -> np.ndarray:
    from . import foley
    beats = 12
    L = 12.0
    n = samples(L)
    out = np.zeros(n)
    asym = rng.uniform(0.47, 0.49)  # slightly out of beat: tick-tock unequal
    case = [310 * r for r in (1.0, 1.61, 2.3, 3.4, 4.7)]
    for b in range(beats):
        pair = b // 2
        t0 = pair * 2.0 * (L / beats) + (0 if b % 2 == 0 else 2.0 * (L / beats) * asym)
        m = samples(0.25)
        tone = 1.0 if b % 2 == 0 else 0.86
        g = dsp.db(rng.uniform(-1.5, 1.0))
        x = foley.metal_click(rng, m, 0.002, 3100 * tone * rng.uniform(0.99, 1.01), 0.8 * g, 0.012)
        x += foley.metal_click(rng, m, 0.002 + rng.uniform(0.004, 0.007), 4200 * tone, 0.35 * g, 0.008)
        x += foley.impact(rng, m, 0.002, 0.0003, case, [0.05, 0.04, 0.03, 0.02, 0.015],
                          [1, .7, .5, .3, .2], 0.5 * g)
        dsp.mix_circular(out, x, samples(t0 + 0.3))
    out += 0.004 * dsp.colored(rng, n, -3.0, lo=200, hi=6000)  # movement / room
    ir = dsp.room_ir(rng, rt60=0.4, length=0.5)
    return dsp.reverb_circular(out, ir, 0.15)


def tv_static(rng: np.random.Generator) -> np.ndarray:
    L = 10.0
    n = samples(L)
    t = dsp.tvec(n)
    x = dsp.colored(rng, n, 0.0, lo=150, hi=7500)
    # vertical-sync buzz leaking into the audio IF
    buzz = sum((1.0 / h) * np.sin(TAU * 60 * h * t + 0.3 * h) for h in range(1, 30))
    x += 0.18 * buzz
    x *= 1 + 0.05 * dsp.periodic_lfo(rng, n, 40, -1, 1)
    x += 0.03 * np.sin(TAU * 15734 * t)  # flyback whine (quiet but present)
    # small oval speaker in a plastic cabinet
    x = dsp.eq_circular(x, "peak", 380, 2, 6)
    x = dsp.eq_circular(x, "peak", 2600, 1.5, 4)
    x = dsp.asym_saturate(x * 0.4, 1.8, 0.1)
    x = dsp.highpass_c(x, 160, 2)
    return x


def light_buzz(rng: np.random.Generator) -> np.ndarray:
    L = 10.0
    n = samples(L)
    t = dsp.tvec(n)
    y = np.zeros(n)
    amps = {1: 1.0, 2: 0.6, 3: 0.5, 4: 0.25, 5: 0.2, 6: 0.12, 7: 0.1, 8: 0.06, 10: 0.04, 12: 0.03, 16: 0.02}
    for h, a in amps.items():
        y += a * np.sin(TAU * 120 * h * t + rng.uniform(0, TAU))
    y = dsp.asym_saturate(y * 0.5, 2.2, 0.3)
    sizzle = dsp.colored(rng, n, 0.0, lo=2000, hi=9000)
    sizzle *= (0.5 + 0.5 * np.abs(np.sin(TAU * 60 * t))) ** 4
    y += 0.06 * sizzle
    y *= dsp.periodic_lfo(rng, n, 9, 0.9, 1.05)
    y = dsp.eq_circular(y, "peak", 720, 3, 4)  # sheet-metal fixture
    return y


def _fly_segment(rng, m, base, on_glass):
    """Wingbeat tone for one flight segment (housefly ~190-260 Hz, rich harmonics)."""
    from . import foley
    tt = np.arange(m) / SR
    d = m / SR
    # erratic pitch: fast flutter + slower manoeuvres; frantic and higher on the glass
    f = base * dsp.smooth_noise(rng, m, 25, 0.95, 1.05) * dsp.smooth_noise(rng, m, 3, 0.94, 1.06)
    tick = np.zeros(m)
    if on_glass:
        f *= 1.12
        for b in np.sort(rng.uniform(0.0, d, int(rng.integers(2, 6)))):
            tick += foley.impact(rng, m, b, 0.0001, [2400, 3700, 5200, 7100], [0.01, 0.008, 0.006, 0.004],
                                 [1, .8, .6, .4], rng.uniform(0.3, 0.8), click=0.4, click_band=(3000, 11000))
    ph = TAU * np.cumsum(f) / SR
    # wing stroke is a skewed pulse: odd/even harmonics, falling ~1/h, slightly noisy
    src = np.zeros(m)
    for h in range(1, 26):
        a = (1.0 / h ** 1.05) * (1.0 if h % 2 else 0.7)
        src += a * np.sin(h * ph + 0.5 * h + 0.3 * np.sin(ph * 0.5))
    src += 0.35 * dsp.bandpass(dsp.white(rng, m), 800, 7000) * (0.4 + 0.6 * (0.5 + 0.5 * np.sin(ph)) ** 3)
    if on_glass:
        near = dsp.smooth_noise(rng, m, 12, 0.6, 1.0)  # on the pane: close, raspy, choppy
        src = dsp.asym_saturate(src * 0.6, 2.0, 0.2)
        cut = 3500 + 4000 * near
    else:
        # flight path: distance and orientation change quickly and unevenly
        near = dsp.smooth_noise(rng, m, 4.5, 0.0, 1.0) ** 1.6 * 0.85 + 0.15
        cut = 1200 + 6500 * near ** 1.5
    a_in = rng.uniform(0.02, 0.08) if on_glass else rng.uniform(0.08, 0.25)
    env = np.clip(tt / a_in, 0, 1) * np.clip((d - tt) / rng.uniform(0.03, 0.15), 0, 1)
    y = dsp.time_varying_lowpass(src * near * env, cut)
    return y + tick


def fly_buzz(rng: np.random.Generator) -> np.ndarray:
    """A housefly at a sunny window: cruising flights, bursts on the glass, silences."""
    L = 26.0
    n = samples(L)
    out = np.zeros(n)
    t = 0.7
    while t < L - 1.5:
        if rng.random() < 0.45:
            # a run of short bursts on/against the pane: bzz . bzzt . bz
            for _ in range(int(rng.integers(2, 6))):
                d = rng.uniform(0.12, 0.7)
                if t + d > L - 1.0:
                    break
                y = _fly_segment(rng, samples(d), rng.uniform(205, 240), True)
                dsp.mix_at(out, y, samples(t), rng.uniform(0.6, 1.0))
                t += d + rng.uniform(0.15, 0.9)
        else:
            d = min(rng.uniform(1.2, 4.0), L - 1.0 - t)
            if d < 0.5:
                break
            y = _fly_segment(rng, samples(d), rng.uniform(180, 210), False)
            dsp.mix_at(out, y, samples(t))
            t += d
        t += rng.uniform(0.8, 3.5)  # landed, walking about, silent
    return dsp.reverb_circular(out, dsp.room_ir(rng, rt60=0.4, length=0.5), 0.12)


def phone_dial_tone(rng: np.random.Generator) -> np.ndarray:
    L = 8.0
    n = samples(L)
    t = dsp.tvec(n)
    y = np.sin(TAU * 350 * t) + np.sin(TAU * 440 * t)
    y = dsp.asym_saturate(y * 0.5, 2.0, 0.15)  # carbon/dynamic earpiece
    y += 0.02 * dsp.colored(rng, n, -1.0, lo=300, hi=3400) + 0.02 * np.sin(TAU * 60 * t)
    y = dsp.bandpass_c(y, 300, 3400, 2)
    y = dsp.eq_circular(y, "peak", 1100, 1.2, 5)
    return y


def faucet_run(rng: np.random.Generator) -> np.ndarray:
    L = 12.0
    n = samples(L)
    out = np.zeros(n)
    # turbulent splash
    spl = dsp.colored(rng, n, -2.0, lo=250, hi=7000)
    turb = np.abs(dsp.lowpass_c(dsp.white(rng, n), 60, 1))
    turb /= turb.max()
    out += 0.18 * spl * (0.6 + 0.4 * turb)
    # Minnaert bubbles (van den Doel): rising chirps
    count = int(L * 420)
    for _ in range(count):
        r = np.exp(rng.uniform(np.log(0.0008), np.log(0.005)))
        f0 = 3.26 / r
        if f0 > 9000:
            continue
        damp = 0.043 * f0 + 0.0014 * f0 ** 1.5
        m = min(samples(5.0 / damp), samples(0.04))
        tt = np.arange(m) / SR
        xi = 0.1 * damp
        b = np.sin(TAU * f0 * np.cumsum(1 + xi * tt) / SR) * np.exp(-damp * tt)
        dsp.mix_circular(out, b * (r / 0.003) ** 1.2 * 0.5 * rng.uniform(0.3, 1), int(rng.integers(0, n)))
    out = dsp.eq_circular(out, "peak", 520, 2, 4)  # stainless sink drum
    out = dsp.eq_circular(out, "peak", 2900, 1, 2)
    return dsp.reverb_circular(out, dsp.room_ir(rng, rt60=0.45, length=0.5), 0.15)


def camcorder_motor(rng: np.random.Generator) -> np.ndarray:
    L = 10.0
    n = samples(L)
    t = dsp.tvec(n)
    y = np.zeros(n)
    for h, a in ((1, 1.0), (2, 0.5), (3, 0.4), (4, 0.2), (6, 0.12), (8, 0.06)):
        y += a * np.sin(TAU * 30 * h * t + rng.uniform(0, TAU))  # head drum 1800 rpm
    y *= 0.4
    whir = dsp.colored(rng, n, -2.0, lo=200, hi=4000) * (0.7 + 0.3 * np.sin(TAU * 30 * t)) ** 2
    y += 0.5 * whir
    y += 0.05 * np.sin(TAU * 910 * t) * dsp.periodic_lfo(rng, n, 6, 0.5, 1.0)  # capstan servo whine
    y = dsp.eq_circular(y, "lowshelf", 200, 0.7, 4)  # body-borne
    return dsp.lowpass_c(y, 5000, 2)


def camcorder_zoom(rng: np.random.Generator) -> np.ndarray:
    L = 4.0
    n = samples(L)
    t = dsp.tvec(n)
    fm = 230.0  # motor rotation (integer cycles over the loop)
    wob = dsp.periodic_lfo(rng, n, 8, -1, 1)
    ph = TAU * fm * t + 0.02 * np.cumsum(wob) / SR * TAU * 10
    y = np.zeros(n)
    for h in range(1, 10):
        y += (0.5 / h) * np.sin(h * ph)
    mesh = sum(np.sin(13 * k * ph) / k for k in (1, 2))  # worm-gear mesh
    y += 0.5 * mesh * (0.7 + 0.3 * np.sin(ph))
    brush = dsp.colored(rng, n, 0.0, lo=2000, hi=9000) * (0.5 + 0.5 * np.sin(ph)) ** 2
    y += 0.35 * brush
    y = dsp.eq_circular(y, "peak", 2990, 4, 6)
    return dsp.bandpass_c(y, 150, 9000, 2)


def tape_hiss(rng: np.random.Generator) -> np.ndarray:
    L = 10.0
    n = samples(L)
    x = dsp.colored(rng, n, 1.5, lo=600, hi=9500)  # rising hiss, VHS linear track bandwidth
    x = dsp.eq_circular(x, "peak", 5500, 0.8, 3)
    mod = dsp.colored(rng, n, -3.0, lo=20, hi=300) * 0.08  # modulation noise
    x += mod
    # very occasional dropout ticks
    return dsp.lowpass_c(x, 8500, 4)  # VHS linear audio track runs out of top end
