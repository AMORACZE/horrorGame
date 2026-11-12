"""Core helpers for the procedural texture generator.

Everything here is *periodic*: noise lattices wrap, blurs are done in the
frequency domain (circular convolution), derivatives use np.roll. Anything
built only from these primitives tiles seamlessly by construction.

Conventions
-----------
* Arrays are float32/float64, shape (H, W) or (H, W, 3), values 0..1 unless noted.
* Row 0 is the TOP of the image. In Godot triplanar mapping the image's
  vertical axis maps to world -Y on walls, so "up in the image" is "up on the
  wall".
* Heights are in millimetres; ``px_mm`` is the size of one pixel in mm. Normal
  maps are therefore physically scaled and materials use normal_scale ~ 1.
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# random / noise
# ---------------------------------------------------------------------------

def rng(seed: int | str) -> np.random.Generator:
    if isinstance(seed, str):
        seed = sum((i + 1) * ord(c) for i, c in enumerate(seed)) * 7919
    return np.random.default_rng(seed)


def _interp_axis(grid: np.ndarray, n_out: int, axis: int, cubic: bool = True) -> np.ndarray:
    """Periodically resample ``grid`` along ``axis`` to ``n_out`` samples."""
    n_in = grid.shape[axis]
    t = (np.arange(n_out) + 0.5) * n_in / n_out - 0.5
    i0 = np.floor(t).astype(int)
    f = t - i0
    g = np.moveaxis(grid, axis, 0)
    if cubic:
        # Catmull-Rom on the periodic lattice
        p0 = g[(i0 - 1) % n_in]
        p1 = g[i0 % n_in]
        p2 = g[(i0 + 1) % n_in]
        p3 = g[(i0 + 2) % n_in]
        shape = (-1,) + (1,) * (g.ndim - 1)
        f = f.reshape(shape)
        out = 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f
                     + (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f)
    else:
        a = g[i0 % n_in]
        b = g[(i0 + 1) % n_in]
        shape = (-1,) + (1,) * (g.ndim - 1)
        f = f.reshape(shape)
        f = f * f * (3 - 2 * f)
        out = a + (b - a) * f
    return np.moveaxis(out, 0, axis)


def vnoise(h: int, w: int, cy: int, cx: int, r: np.random.Generator, cubic: bool = True) -> np.ndarray:
    """Periodic value noise with ``cy`` x ``cx`` lattice cells over the tile. ~[-1, 1]."""
    grid = r.uniform(-1.0, 1.0, size=(max(1, cy), max(1, cx)))
    out = _interp_axis(grid, h, 0, cubic)
    out = _interp_axis(out, w, 1, cubic)
    return out


def fbm(h: int, w: int, cy: int, cx: int, r: np.random.Generator, octaves: int = 5,
        gain: float = 0.5, lac: int = 2) -> np.ndarray:
    """Periodic fractal noise, normalised to roughly [-1, 1]."""
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        fy, fx = cy * lac ** o, cx * lac ** o
        if fy > h or fx > w:
            break
        out += amp * vnoise(h, w, fy, fx, r)
        tot += amp
        amp *= gain
    return out / tot


def white(h: int, w: int, r: np.random.Generator) -> np.ndarray:
    return r.uniform(-1.0, 1.0, size=(h, w))


def blur(img: np.ndarray, sigma_y: float, sigma_x: float | None = None) -> np.ndarray:
    """Periodic gaussian blur via FFT (sigma in pixels)."""
    if sigma_x is None:
        sigma_x = sigma_y
    if sigma_x <= 0 and sigma_y <= 0:
        return img
    h, w = img.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    k = np.exp(-2 * (math.pi ** 2) * ((fy * sigma_y) ** 2 + (fx * sigma_x) ** 2))
    if img.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(img) * k, s=(h, w))
    return np.stack([np.fft.irfft2(np.fft.rfft2(img[..., c]) * k, s=(h, w)) for c in range(img.shape[2])], -1)


def spectral(h: int, w: int, r: np.random.Generator, beta: float = 2.0, fmin: float = 1.0,
             fmax: float | None = None, aniso: tuple[float, float] = (1.0, 1.0)) -> np.ndarray:
    """Periodic 1/f^beta noise via FFT. ``aniso`` scales frequency per axis (y, x)."""
    fy = np.fft.fftfreq(h)[:, None] * h * aniso[0]
    fx = np.fft.fftfreq(w)[None, :] * w * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    amp = np.where(f >= fmin, 1.0 / np.maximum(f, 1e-6) ** (beta / 2), 0.0)
    if fmax is not None:
        amp *= np.exp(-(f / fmax) ** 2)
    ph = r.uniform(0, 2 * math.pi, size=(h, w))
    spec = amp * np.exp(1j * ph)
    out = np.real(np.fft.ifft2(spec))
    out -= out.mean()
    return out / (np.abs(out).max() + 1e-9)


def worley(h: int, w: int, cy: int, cx: int, r: np.random.Generator, jitter: float = 1.0):
    """Periodic Worley noise. Returns (F1, F2, cell_id) with distances in cell units."""
    pts = r.uniform(0.5 - 0.5 * jitter, 0.5 + 0.5 * jitter, size=(cy, cx, 2))
    ids = r.permutation(cy * cx).reshape(cy, cx)
    ys = (np.arange(h) + 0.5) * cy / h
    xs = (np.arange(w) + 0.5) * cx / w
    gy = np.floor(ys).astype(int)
    gx = np.floor(xs).astype(int)
    fy = ys - gy
    fx = xs - gx
    f1 = np.full((h, w), 9.0)
    f2 = np.full((h, w), 9.0)
    cid = np.zeros((h, w), dtype=int)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cyi = (gy + dy) % cy
            cxi = (gx + dx) % cx
            p = pts[cyi[:, None], cxi[None, :]]
            ddy = dy + p[..., 0] - fy[:, None]
            ddx = dx + p[..., 1] - fx[None, :]
            d = np.sqrt(ddy * ddy + ddx * ddx)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, ids[cyi[:, None], cxi[None, :]], cid)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid


def warp(img: np.ndarray, dy: np.ndarray, dx: np.ndarray) -> np.ndarray:
    """Periodic domain warp (displacements in pixels), bilinear sampling."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    sy = yy + dy
    sx = xx + dx
    y0 = np.floor(sy).astype(int)
    x0 = np.floor(sx).astype(int)
    fy = sy - y0
    fx = sx - x0
    y0m, y1m = y0 % h, (y0 + 1) % h
    x0m, x1m = x0 % w, (x0 + 1) % w
    if img.ndim == 3:
        fy = fy[..., None]
        fx = fx[..., None]
    a = img[y0m, x0m]
    b = img[y0m, x1m]
    c = img[y1m, x0m]
    d = img[y1m, x1m]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def sample_periodic(img: np.ndarray, sy: np.ndarray, sx: np.ndarray) -> np.ndarray:
    """Bilinear periodic lookup of ``img`` at fractional pixel coords."""
    h, w = img.shape[:2]
    y0 = np.floor(sy).astype(int)
    x0 = np.floor(sx).astype(int)
    fy = sy - y0
    fx = sx - x0
    y0m, y1m = y0 % h, (y0 + 1) % h
    x0m, x1m = x0 % w, (x0 + 1) % w
    return ((img[y0m, x0m] * (1 - fx) + img[y0m, x1m] * fx) * (1 - fy)
            + (img[y1m, x0m] * (1 - fx) + img[y1m, x1m] * fx) * fy)


# ---------------------------------------------------------------------------
# shaping helpers
# ---------------------------------------------------------------------------

def norm01(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo + 1e-9)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    if isinstance(t, np.ndarray) and t.ndim == 2 and np.ndim(a) >= 1 and np.shape(a)[-1:] == (3,):
        t = t[..., None]
    return a + (np.asarray(b) - np.asarray(a)) * t


def srgb(c) -> np.ndarray:
    """Hex '#rrggbb' or tuple 0..255 / 0..1 -> np.array(3) in 0..1 (sRGB)."""
    if isinstance(c, str):
        c = c.lstrip('#')
        return np.array([int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    c = np.asarray(c, dtype=np.float64)
    return c / 255.0 if c.max() > 1.0 else c


def colorize(t: np.ndarray, stops: list[tuple[float, str]]) -> np.ndarray:
    """Map scalar field t (0..1) through a colour ramp."""
    pos = np.array([s[0] for s in stops])
    cols = np.array([srgb(s[1]) for s in stops])
    out = np.empty(t.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(t, pos, cols[:, ch])
    return out


def tint(rgb: np.ndarray, field: np.ndarray, color, amount: float) -> np.ndarray:
    """Multiply-blend toward ``color`` by field*amount (field 0..1)."""
    col = srgb(color)
    k = np.clip(field * amount, 0, 1)[..., None]
    return rgb * (1 - k) + rgb * col * k


def overlay_toward(rgb: np.ndarray, field: np.ndarray, color, amount: float) -> np.ndarray:
    col = srgb(color)
    k = np.clip(field * amount, 0, 1)[..., None]
    return rgb * (1 - k) + col * k


def age(rgb: np.ndarray, r: np.random.Generator, yellow: float = 0.25, fade: float = 0.1,
        grime: float = 0.08, cells: int = 3) -> np.ndarray:
    """Low-frequency 'thirty years' overlay: nicotine yellowing, sun fade, grime.

    Everything is low frequency (a few lattice cells per tile) so tiling repeats
    are not obvious.
    """
    h, w = rgb.shape[:2]
    n1 = norm01(fbm(h, w, cells, cells, r, 3))
    n2 = norm01(fbm(h, w, cells, cells, r, 3))
    n3 = norm01(fbm(h, w, cells * 2, cells * 2, r, 4))
    out = rgb.copy()
    # nicotine: multiply toward a warm yellow-brown, strongest on light colours
    lum = luminance(out)[..., None]
    nic = srgb('#e8cf8a')
    k = (yellow * (0.6 + 0.4 * n1))[..., None] * (0.4 + 0.6 * lum)
    out = out * (1 - k) + out * nic * k
    # sun fade: desaturate + lift slightly
    g = luminance(out)[..., None]
    kf = (fade * smoothstep(0.35, 0.8, n2))[..., None]
    out = out * (1 - kf) + (g * 0.85 + 0.15 * srgb('#efe6d0')) * kf
    # grime: darken slightly, warm
    kg = (grime * smoothstep(0.4, 0.9, n3))[..., None]
    out = out * (1 - kg) + out * srgb('#6f5a42') * kg
    return out


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def saturate(rgb: np.ndarray, s: float) -> np.ndarray:
    g = luminance(rgb)[..., None]
    return g + (rgb - g) * s


def downsample(a: np.ndarray, f: int) -> np.ndarray:
    """Box-filter downsample by integer factor (for supersampled drawing)."""
    if f == 1:
        return a
    h, w = a.shape[:2]
    if a.ndim == 2:
        return a.reshape(h // f, f, w // f, f).mean(axis=(1, 3))
    return a.reshape(h // f, f, w // f, f, a.shape[2]).mean(axis=(1, 3))


def resize(a: np.ndarray, h: int, w: int) -> np.ndarray:
    """Periodic resample (cubic) to a new size; keeps tileability."""
    out = _interp_axis(a, h, 0, True)
    return _interp_axis(out, w, 1, True)


# ---------------------------------------------------------------------------
# height -> normal / AO
# ---------------------------------------------------------------------------

def height_to_normal(h_mm: np.ndarray, px_mm_x: float, px_mm_y: float | None = None,
                     strength: float = 1.0) -> np.ndarray:
    """OpenGL-convention (+Y up / green up) tangent-space normal map from a
    periodic height field in millimetres."""
    if px_mm_y is None:
        px_mm_y = px_mm_x
    dx = (np.roll(h_mm, -1, 1) - np.roll(h_mm, 1, 1)) / (2 * px_mm_x)
    drow = (np.roll(h_mm, -1, 0) - np.roll(h_mm, 1, 0)) / (2 * px_mm_y)
    # image rows run downward; tangent-space +Y is up the image => dh/dv_up = -drow
    nx = -dx * strength
    ny = drow * strength
    nz = np.ones_like(h_mm)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], -1)


def normal_to_rgb(n: np.ndarray) -> np.ndarray:
    return n * 0.5 + 0.5


def cavity_ao(h_mm: np.ndarray, radius_px: float, depth_mm: float, power: float = 1.0) -> np.ndarray:
    """Cheap periodic AO: how far below its blurred neighbourhood each texel sits."""
    b = blur(h_mm, radius_px)
    occ = np.clip((b - h_mm) / depth_mm, 0, 1)
    return np.clip(1 - occ, 0, 1) ** power


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def to8(a: np.ndarray) -> np.ndarray:
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def save_png(path: str, a: np.ndarray) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = to8(a)
    mode = 'L' if img.ndim == 2 else ('RGBA' if img.shape[2] == 4 else 'RGB')
    Image.fromarray(img, mode).save(path, optimize=True)


def tile_seam_ratio(a: np.ndarray) -> float:
    """Edge-continuity check. The mean jump across the wrap seam (last column ->
    first column, last row -> first row) divided by the LARGEST mean jump
    between any two neighbouring interior columns/rows. Designed features that
    also occur inside the tile (grout, grooves, stripe edges) therefore do not
    count as seams; a real wrap discontinuity gives a ratio well above 1."""
    a = a.astype(np.float64)
    if a.ndim == 3:
        a = a.mean(-1)
    jx = np.abs(np.diff(a, axis=1)).mean(0)
    jy = np.abs(np.diff(a, axis=0)).mean(1)
    seam_x = np.abs(a[:, 0] - a[:, -1]).mean()
    seam_y = np.abs(a[0, :] - a[-1, :]).mean()
    rx = seam_x / (jx.max() + 1e-9)
    ry = seam_y / (jy.max() + 1e-9)
    return float(max(rx, ry))
