"""Signal-processing building blocks for the procedural sound library.

Everything works on float64 numpy arrays at SR (44.1 kHz). Mono signals are 1-D,
stereo signals are shape (n, 2). Functions never mutate their inputs.

Two families of helpers:
  * one-shot helpers (linear filters, convolution, envelopes);
  * *periodic* helpers for loops: noise shaped in the FFT domain, LFOs built
    from integer-cycle sinusoids, circular convolution and circular event
    placement. A loop built only from these is seamless by construction, so no
    crossfade is needed (the analyser verifies it anyway).
"""
from __future__ import annotations

import numpy as np
from scipy import signal

SR = 44100
TAU = 2.0 * np.pi


# --------------------------------------------------------------------------- basics

def secs(n: int) -> float:
    return n / SR


def samples(t: float) -> int:
    return int(round(t * SR))


def tvec(n: int) -> np.ndarray:
    return np.arange(n) / SR


def db(x: float) -> float:
    return 10.0 ** (x / 20.0)


def to_db(x: float) -> float:
    return 20.0 * np.log10(max(x, 1e-12))


def pad(x: np.ndarray, n: int) -> np.ndarray:
    """Pad (or trim) along axis 0 to length n."""
    if len(x) >= n:
        return x[:n].copy()
    shape = (n - len(x),) + x.shape[1:]
    return np.concatenate([x, np.zeros(shape)])


def mix_at(dst: np.ndarray, src: np.ndarray, start: int, gain: float = 1.0) -> None:
    """Add src into dst at sample offset start (clipped to dst bounds). In place."""
    if start >= len(dst):
        return
    s0 = max(0, -start)
    d0 = max(0, start)
    n = min(len(src) - s0, len(dst) - d0)
    if n > 0:
        dst[d0:d0 + n] += gain * src[s0:s0 + n]


def mix_circular(dst: np.ndarray, src: np.ndarray, start: int, gain: float = 1.0) -> None:
    """Add src into dst at start, wrapping around the end (for loops). In place."""
    n = len(dst)
    idx = (start + np.arange(len(src))) % n
    np.add.at(dst, idx, gain * src)


# --------------------------------------------------------------------------- noise

def white(rng: np.random.Generator, n: int) -> np.ndarray:
    return rng.standard_normal(n)


def colored(rng: np.random.Generator, n: int, slope_db_oct: float = -3.0,
            lo: float = 0.0, hi: float | None = None) -> np.ndarray:
    """Noise with a power slope in dB/octave, built in the FFT domain.

    The result is *circular* (periodic over n samples), which makes it ideal for
    loops; for one-shots that does not matter. -3 = pink, -6 = brown.
    """
    spec = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1] if n > 1 else 1.0
    mag = (f / 1000.0) ** (slope_db_oct / (20.0 * np.log10(2.0)))
    if lo > 0:
        mag *= 1.0 / np.sqrt(1.0 + (lo / f) ** 4)
    if hi is not None:
        mag *= 1.0 / np.sqrt(1.0 + (f / hi) ** 4)
    mag[0] = 0.0
    x = np.fft.irfft(spec * mag, n)
    return x / (np.std(x) + 1e-12)


def pink(rng: np.random.Generator, n: int) -> np.ndarray:
    return colored(rng, n, -3.0)


def brown(rng: np.random.Generator, n: int) -> np.ndarray:
    return colored(rng, n, -6.0, lo=15.0)


def spectral_shape(x: np.ndarray, freqs: list[float], gains_db: list[float]) -> np.ndarray:
    """Circular zero-phase EQ: piecewise-linear gain curve (log-frequency) applied via FFT."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    lf = np.log10(np.maximum(f, 1.0))
    g = np.interp(lf, np.log10(np.asarray(freqs)), np.asarray(gains_db))
    return np.fft.irfft(X * 10.0 ** (g / 20.0), n)


# --------------------------------------------------------------------------- filters

def _sos(kind: str, freq, order: int = 2) -> np.ndarray:
    return signal.butter(order, freq, btype=kind, fs=SR, output="sos")


def lowpass(x: np.ndarray, f: float, order: int = 2) -> np.ndarray:
    return signal.sosfilt(_sos("lowpass", min(f, SR * 0.49), order), x, axis=0)


def highpass(x: np.ndarray, f: float, order: int = 2) -> np.ndarray:
    return signal.sosfilt(_sos("highpass", f, order), x, axis=0)


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    return signal.sosfilt(_sos("bandpass", [lo, min(hi, SR * 0.49)], order), x, axis=0)


def lowpass_zp(x: np.ndarray, f: float, order: int = 2) -> np.ndarray:
    return signal.sosfiltfilt(_sos("lowpass", min(f, SR * 0.49), order), x, axis=0)


def biquad(kind: str, f0: float, q: float = 0.707, gain_db: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """RBJ cookbook biquad. kind: peak, lowshelf, highshelf, bandpass, notch."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = TAU * f0 / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * q)
    if kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        sa = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sa), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sa)]
        a = [(A + 1) + (A - 1) * cw + sa, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sa]
    elif kind == "highshelf":
        sa = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
        a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    elif kind == "bandpass":
        b = [alpha, 0.0, -alpha]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "notch":
        b = [1.0, -2 * cw, 1.0]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    else:
        raise ValueError(kind)
    b = np.asarray(b) / a[0]
    a = np.asarray(a) / a[0]
    return b, a


def eq(x: np.ndarray, kind: str, f0: float, q: float = 0.707, gain_db: float = 0.0) -> np.ndarray:
    b, a = biquad(kind, f0, q, gain_db)
    return signal.lfilter(b, a, x, axis=0)


def eq_circular(x: np.ndarray, kind: str, f0: float, q: float = 0.707, gain_db: float = 0.0) -> np.ndarray:
    """Apply a biquad's magnitude/phase response circularly (FFT) so loops stay seamless."""
    b, a = biquad(kind, f0, q, gain_db)
    n = len(x)
    w = TAU * np.fft.rfftfreq(n, 1.0 / SR) / SR
    _, h = signal.freqz(b, a, worN=w)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (h if x.ndim == 1 else h[:, None]), n, axis=0)


def filt_circular(x: np.ndarray, sos: np.ndarray) -> np.ndarray:
    """Apply an SOS filter circularly via its frequency response."""
    n = len(x)
    w = TAU * np.fft.rfftfreq(n, 1.0 / SR) / SR
    _, h = signal.sosfreqz(sos, worN=w)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (h if x.ndim == 1 else h[:, None]), n, axis=0)


def lowpass_c(x: np.ndarray, f: float, order: int = 2) -> np.ndarray:
    return filt_circular(x, _sos("lowpass", min(f, SR * 0.49), order))


def highpass_c(x: np.ndarray, f: float, order: int = 2) -> np.ndarray:
    return filt_circular(x, _sos("highpass", f, order))


def bandpass_c(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    return filt_circular(x, _sos("bandpass", [lo, min(hi, SR * 0.49)], order))


def time_varying_lowpass(x: np.ndarray, cutoff: np.ndarray, block: int = 256) -> np.ndarray:
    """One-pole lowpass with a per-sample cutoff curve (block-wise coefficient update)."""
    y = np.empty_like(x)
    z = 0.0
    for i in range(0, len(x), block):
        fc = float(np.mean(cutoff[i:i + block]))
        a = np.exp(-TAU * fc / SR)
        seg, zf = signal.lfilter([1 - a], [1, -a], x[i:i + block], zi=[z * a])
        y[i:i + block] = seg
        z = seg[-1] if len(seg) else z
    return y


# --------------------------------------------------------------------------- envelopes

def env_ad(n: int, attack: float, decay: float, curve: float = 1.0) -> np.ndarray:
    """Attack (raised-cosine) then exponential decay with time constant `decay` seconds."""
    t = tvec(n)
    a = max(attack, 1.0 / SR)
    rise = np.where(t < a, 0.5 - 0.5 * np.cos(np.pi * np.clip(t / a, 0, 1)), 1.0)
    fall = np.exp(-np.maximum(t - a, 0) / max(decay, 1e-5)) ** curve
    return rise * fall


def env_points(n: int, pts: list[tuple[float, float]]) -> np.ndarray:
    """Piecewise-linear envelope from (time_s, value) points, smoothed slightly."""
    t = tvec(n)
    ts = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    return np.interp(t, ts, vs)


def smooth_noise(rng: np.random.Generator, n: int, rate_hz: float, lo: float = 0.0, hi: float = 1.0) -> np.ndarray:
    """Smooth random curve (band-limited to ~rate_hz) scaled to [lo, hi]."""
    k = max(4, int(n / SR * rate_hz) + 4)
    pts = rng.random(k)
    x = np.interp(np.linspace(0, k - 3, n), np.arange(k), pts)
    # cubic-ish smoothing
    w = max(3, int(SR / max(rate_hz, 0.01) / 3))
    if w < n:
        ker = np.hanning(w)
        x = signal.fftconvolve(np.pad(x, (w, w), mode="edge"), ker / ker.sum(), mode="same")[w:-w]
    x = (x - x.min()) / (np.ptp(x) + 1e-12)
    return lo + (hi - lo) * x


def periodic_lfo(rng: np.random.Generator, n: int, max_cycles: int, lo: float = 0.0, hi: float = 1.0,
                 tilt: float = 1.0) -> np.ndarray:
    """Smooth random curve that is exactly periodic over n samples.

    Sum of sinusoids with integer cycle counts 1..max_cycles and random phases,
    amplitudes falling as 1/k^tilt. Scaled to [lo, hi].
    """
    ph = TAU * np.arange(n) / n
    x = np.zeros(n)
    for k in range(1, max_cycles + 1):
        x += rng.uniform(0.3, 1.0) / k ** tilt * np.sin(k * ph + rng.uniform(0, TAU))
    x = (x - x.min()) / (np.ptp(x) + 1e-12)
    return lo + (hi - lo) * x


def fade(x: np.ndarray, fin: float = 0.002, fout: float = 0.01) -> np.ndarray:
    y = x.copy()
    ni, no = samples(fin), samples(fout)
    if ni > 0:
        w = np.sin(np.linspace(0, np.pi / 2, ni)) ** 2
        y[:ni] *= w if y.ndim == 1 else w[:, None]
    if no > 0:
        w = np.cos(np.linspace(0, np.pi / 2, no)) ** 2
        y[-no:] *= w if y.ndim == 1 else w[:, None]
    return y


# --------------------------------------------------------------------------- excitation & resonators

def contact_pulse(width_s: float, n: int | None = None, rng: np.random.Generator | None = None,
                  roughness: float = 0.0) -> np.ndarray:
    """Hertzian-contact force pulse (half-sine^1.5). Wider = softer material.

    roughness adds micro-impacts (grit, fibres) riding on the pulse.
    """
    w = max(3, samples(width_s))
    n = n or w
    t = np.linspace(0, np.pi, w)
    p = np.sin(t) ** 1.5
    if roughness > 0 and rng is not None:
        p = p * (1.0 + roughness * rng.standard_normal(w))
    return pad(p, n)


def resonator_bank(exc: np.ndarray, freqs, t60s, gains, rng: np.random.Generator | None = None,
                   jitter: float = 0.0) -> np.ndarray:
    """Modal synthesis: drive a bank of two-pole resonators with an excitation.

    freqs Hz, t60s seconds (time to decay 60 dB), gains linear. With jitter > 0
    each mode is detuned by up to +-jitter (fraction).
    """
    y = np.zeros_like(exc, dtype=float)
    for f, t60, g in zip(freqs, t60s, gains):
        if rng is not None and jitter > 0:
            f = f * (1.0 + rng.uniform(-jitter, jitter))
        if f >= SR * 0.47:
            continue
        r = np.exp(-6.91 / (max(t60, 1e-4) * SR))
        w = TAU * f / SR
        # (1 - z^-2) / D(z) with b0 = 0.5: impulse response is g * r^n * cos(w n),
        # i.e. a unit impulse rings each mode at amplitude g whatever its Q
        b0 = 0.5
        y += g * signal.lfilter([b0, 0, -b0], [1, -2 * r * np.cos(w), r * r], exc)
    return y


def modal_ring(n: int, freqs, t60s, amps, rng: np.random.Generator, phase_rand: bool = True,
               attack: float = 0.0) -> np.ndarray:
    """Directly summed decaying sinusoids (for very high-Q bodies like glass and bells)."""
    t = tvec(n)
    y = np.zeros(n)
    for f, t60, a in zip(freqs, t60s, amps):
        ph = rng.uniform(0, TAU) if phase_rand else 0.0
        y += a * np.sin(TAU * f * t + ph) * np.exp(-6.91 * t / t60)
    if attack > 0:
        y *= env_ad(n, attack, 1e9)
    return y


def stick_slip(rng: np.random.Generator, n: int, rate: np.ndarray, amp: np.ndarray,
               jitter: float = 0.08, pulse_w: float = 0.0004, irregular: float = 0.0) -> np.ndarray:
    """Friction (stick-slip) excitation: a pulse train whose instantaneous rate
    follows `rate` (Hz per sample) with period jitter, amplitude following `amp`.

    Each slip is a short asymmetric pulse. `irregular` adds random skipped/double
    slips, which is what makes a hinge sound rusty instead of tonal.
    """
    out = np.zeros(n)
    pw = max(2, samples(pulse_w))
    k = np.arange(pw)
    pulse = (1 - k / pw) * np.exp(-3 * k / pw)
    pulse -= pulse.mean() * 0.6
    t = 0.0
    while True:
        i = int(t)
        if i >= n:
            break
        r = max(rate[i], 1.0)
        a = amp[i]
        if a > 1e-4:
            ai = a * (1.0 + 0.35 * rng.standard_normal())
            if irregular > 0 and rng.random() < irregular:
                ai *= rng.uniform(1.5, 2.8)
            mix_at(out, pulse, i, ai)
        period = SR / r * (1.0 + jitter * rng.standard_normal())
        if irregular > 0 and rng.random() < irregular * 0.5:
            period *= rng.uniform(1.5, 2.5)
        t += max(period, 2.0)
    return out


def friction_noise(rng: np.random.Generator, n: int, lo: float, hi: float, grain_rate: float,
                   env: np.ndarray, grain_depth: float = 0.8) -> np.ndarray:
    """Rubbing / sliding noise: band-passed noise amplitude-modulated by a random grain process."""
    x = bandpass(white(rng, n), lo, hi)
    g = np.abs(lowpass(white(rng, n), grain_rate, 1))
    g /= g.max() + 1e-12
    mod = (1 - grain_depth) + grain_depth * g
    return _taper(x * mod * env)


def _taper(x: np.ndarray, frac: float = 0.15) -> np.ndarray:
    """Cosine taper over the last `frac` of a segment so it can never end on a step."""
    k = max(2, int(len(x) * frac))
    y = x.copy()
    y[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return y


def crackle(rng: np.random.Generator, n: int, density: float, env: np.ndarray, lo: float = 1500,
            hi: float = 9000, decay: float = 0.0006, sharpness: float = 2.0) -> np.ndarray:
    """Sparse random micro-impulses (grit, paper fibres, static) with Pareto-ish amplitudes."""
    p = density / SR * env
    hits = rng.random(n) < p
    amps = np.minimum(rng.pareto(sharpness, n) + 0.2, 12.0) * hits * rng.choice([-1, 1], n)
    k = np.exp(-np.arange(samples(decay * 6)) / max(samples(decay), 1))
    x = signal.fftconvolve(amps, k)[:n]
    return _taper(0.1 * bandpass(x, lo, hi), 0.08)


# --------------------------------------------------------------------------- rooms

def room_ir(rng: np.random.Generator, rt60: float = 0.45, dims=(4.2, 3.6, 2.44), src=(1.0, 1.2, 1.0),
            mic=(2.8, 2.2, 1.6), absorb: float = 0.35, hf_damp: float = 2.2, stereo: bool = False,
            length: float | None = None, er_order: int = 2) -> np.ndarray:
    """Synthetic small-room impulse response.

    Early reflections from a shoebox image-source model up to `er_order`, then a
    diffuse exponentially-decaying tail whose decay is frequency dependent
    (high frequencies die `hf_damp` times faster: soft furnishings, carpet).
    Direct sound is NOT included (returns reverb only); mix it yourself.
    """
    length = length or rt60 * 1.2
    n = samples(length)
    chans = 2 if stereo else 1
    out = np.zeros((n, chans))
    c = 343.0
    Lx, Ly, Lz = dims
    direct = np.linalg.norm(np.subtract(src, mic))
    refl = 1.0 - absorb
    for ch in range(chans):
        m = np.array(mic, dtype=float) + (np.array([0.09, 0, 0]) * (1 if ch else -1) if stereo else 0)
        for i in range(-er_order, er_order + 1):
            for j in range(-er_order, er_order + 1):
                for k in range(-er_order, er_order + 1):
                    order = abs(i) + abs(j) + abs(k)
                    if order == 0 or order > er_order:
                        continue
                    ix = i * Lx + (src[0] if i % 2 == 0 else Lx - src[0])
                    iy = j * Ly + (src[1] if j % 2 == 0 else Ly - src[1])
                    iz = k * Lz + (src[2] if k % 2 == 0 else Lz - src[2])
                    d = np.linalg.norm([ix - m[0], iy - m[1], iz - m[2]])
                    delay = (d - direct) / c
                    idx = samples(delay)
                    if 0 <= idx < n:
                        out[idx, ch] += (refl ** order) * direct / d * rng.uniform(0.7, 1.0)
        # early reflections are a bit dull (furniture scattering)
        out[:, ch] = lowpass(out[:, ch], 6500, 1)
    # diffuse tail: three bands with different decay rates
    t = tvec(n)
    start = samples(0.012)
    tail = np.zeros((n, chans))
    bands = [(20, 500, 1.0), (500, 3000, 1.0 / np.sqrt(hf_damp)), (3000, 16000, 1.0 / hf_damp)]
    for lo, hi, rtf in bands:
        rt = rt60 * rtf
        e = np.exp(-6.91 * t / rt)
        for ch in range(chans):
            nz = bandpass(white(rng, n), lo, hi)
            tail[:, ch] += nz * e
    onset = np.clip((np.arange(n) - start) / samples(0.02), 0, 1)
    tail *= onset[:, None]
    tail *= 0.35 * np.sqrt(1.0 / max(rt60, 0.05)) / np.sqrt(SR / 1000)
    ir = out + tail
    ir = fade(ir, 0.0, min(0.05, length * 0.2))
    return ir if stereo else ir[:, 0]


def reverb(x: np.ndarray, ir: np.ndarray, wet: float, dry: float = 1.0, predelay: float = 0.0,
           extra: float = 0.0) -> np.ndarray:
    """Convolve (linear) and mix. Output is longer than input by the IR length + extra seconds."""
    if predelay > 0:
        ir = np.concatenate([np.zeros((samples(predelay),) + ir.shape[1:]), ir])
    n = len(x) + len(ir) + samples(extra)
    if ir.ndim == 2 and x.ndim == 1:
        w = np.stack([signal.fftconvolve(x, ir[:, c]) for c in range(ir.shape[1])], axis=1)
        d = np.stack([x, x], axis=1)
    elif ir.ndim == 2:
        w = np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], axis=1)
        d = x
    else:
        w = signal.fftconvolve(x, ir, axes=0) if x.ndim == 1 else np.stack(
            [signal.fftconvolve(x[:, c], ir) for c in range(x.shape[1])], axis=1)
        d = x
    return pad(dry * d, n) + wet * pad(w, n)


def reverb_circular(x: np.ndarray, ir: np.ndarray, wet: float, dry: float = 1.0) -> np.ndarray:
    """Circular convolution: reverb tail wraps to the start, keeping a loop seamless."""
    n = len(x)
    if len(ir) > n:
        ir = ir[:n]
    X = np.fft.rfft(x, n, axis=0)
    H = np.fft.rfft(ir, n, axis=0)
    if x.ndim == 1 and ir.ndim == 2:
        w = np.fft.irfft(X[:, None] * H, n, axis=0)
        return dry * np.stack([x, x], axis=1) + wet * w
    if x.ndim == 2 and ir.ndim == 1:
        H = H[:, None]
    return dry * x + wet * np.fft.irfft(X * H, n, axis=0)


# --------------------------------------------------------------------------- colour / nonlinearity

def saturate(x: np.ndarray, drive: float = 1.5) -> np.ndarray:
    """Gentle tanh saturation, gain-compensated for small signals."""
    return np.tanh(drive * x) / drive


def asym_saturate(x: np.ndarray, drive: float = 2.0, bias: float = 0.15) -> np.ndarray:
    """Asymmetric saturation (even harmonics): small speakers, rattles."""
    y = np.tanh(drive * (x + bias)) - np.tanh(drive * bias)
    return y / drive


def distance(x: np.ndarray, metres: float, circular: bool = False) -> np.ndarray:
    """Air absorption + loss of presence with distance (outdoors)."""
    fc = float(np.clip(16000.0 / (1.0 + metres / 40.0), 1200, 16000))
    f = lowpass_c if circular else lowpass
    return f(x, fc, 1)


def through_wall(x: np.ndarray, circular: bool = False, closed_window: bool = True) -> np.ndarray:
    """Transmission through a closed 1970s exterior wall / single-pane window.

    Mass-law-ish: low frequencies pass, highs fall off steeply; a slight
    resonance of the glass around 250-400 Hz.
    """
    lp = lowpass_c if circular else lowpass
    e = eq_circular if circular else eq
    y = lp(x, 1400.0 if closed_window else 3000.0, 2)
    y = 0.75 * y + 0.25 * lp(x, 4500.0, 1) * 0.15
    y = e(y, "peak", 320.0, 1.2, 3.0)
    return y


# --------------------------------------------------------------------------- loudness

def _kweight(x: np.ndarray) -> np.ndarray:
    y = eq(x, "highshelf", 1681.0, 0.7071, 4.0)
    b, a = signal.butter(2, 38.0, "highpass", fs=SR)
    return signal.lfilter(b, a, y, axis=0)


def loudness(x: np.ndarray) -> dict:
    """LUFS-ish measurements (BS.1770 K-weighting approximation, ungated)."""
    k = _kweight(x)
    if k.ndim == 2:
        p = np.sum(k ** 2, axis=1)
    else:
        p = k ** 2
    integ = -0.691 + 10 * np.log10(np.mean(p) + 1e-20)
    w = samples(0.4)
    if len(p) > w:
        c = np.cumsum(np.concatenate([[0], p]))
        mom = (c[w:] - c[:-w]) / w
        mmax = -0.691 + 10 * np.log10(mom.max() + 1e-20)
    else:
        mmax = -0.691 + 10 * np.log10(np.sum(p) / w + 1e-20)
    return {"integrated": float(integ), "momentary_max": float(mmax)}


def normalize(x: np.ndarray, target_lufs: float, mode: str, peak_ceiling_db: float = -1.0) -> np.ndarray:
    """Scale to a loudness target (mode: 'integrated' or 'momentary_max'), then
    enforce the peak ceiling with a soft limiter-free gain cap."""
    L = loudness(x)[mode]
    y = x * 10 ** ((target_lufs - L) / 20)
    pk = np.max(np.abs(y)) + 1e-12
    ceil = db(peak_ceiling_db)
    if pk > ceil:
        y *= ceil / pk
    return y


def remove_dc(x: np.ndarray, circular: bool = False) -> np.ndarray:
    if circular:
        return x - np.mean(x, axis=0)
    return highpass(x, 12.0, 1) if x.ndim == 1 else highpass(x, 12.0, 1)


def resonator_bank_c(exc: np.ndarray, freqs, t60s, gains) -> np.ndarray:
    """Circular (FFT-domain) version of resonator_bank, for loops."""
    n = len(exc)
    w = TAU * np.fft.rfftfreq(n, 1.0 / SR) / SR
    H = np.zeros(len(w), dtype=complex)
    for f, t60, g in zip(freqs, t60s, gains):
        r = np.exp(-6.91 / (max(t60, 1e-4) * SR))
        wr = TAU * f / SR
        b0 = 0.5
        _, h = signal.freqz([b0, 0, -b0], [1, -2 * r * np.cos(wr), r * r], worN=w)
        H += g * h
    return np.fft.irfft(np.fft.rfft(exc) * H, n)


def limit(x: np.ndarray, ceiling_db: float = -1.0, max_gr_db: float = 8.0, lookahead: float = 0.0015,
          release: float = 0.04) -> np.ndarray:
    """Look-ahead peak limiter (transparent on transients up to a few dB).

    Required gain is min-filtered over +-lookahead (so the gain is already down
    when a peak arrives), recovers with an exponential release, and is smoothed
    with a Hann window of the same width so the gain change never clicks.
    Gain reduction is capped at max_gr_db; anything left over is the caller's job.
    """
    from scipy.ndimage import minimum_filter1d
    ceil = db(ceiling_db)
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    need = np.clip(ceil / np.maximum(a, 1e-12), db(-max_gr_db), 1.0)
    la = max(1, samples(lookahead))
    g = minimum_filter1d(need, size=2 * la + 1, mode="nearest")
    r = float(np.exp(-1.0 / (release * SR)))
    out = np.empty_like(g)
    cur = 1.0
    for i, gi in enumerate(g.tolist()):
        cur = gi if gi < cur else gi + (cur - gi) * r
        out[i] = cur
    k = np.hanning(2 * la + 1)
    gs = np.minimum(np.convolve(out, k / k.sum(), mode="same"), 1.0)
    return x * (gs if x.ndim == 1 else gs[:, None])
