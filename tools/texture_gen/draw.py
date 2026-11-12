"""Periodic drawing primitives: wrapped stamps, SDF shapes, strand (fibre)
rendering and woven-cloth synthesis. All drawing wraps around the tile edges so
the results stay seamless."""
from __future__ import annotations

import math

import numpy as np

from .core import smoothstep


def patch(h: int, w: int, cx: float, cy: float, rx: float, ry: float | None = None):
    """Wrapped pixel window around (cx, cy). Returns (iy, ix, DX, DY) where DX/DY
    are pixel-centre offsets from the centre and iy/ix are wrapped indices."""
    if ry is None:
        ry = rx
    x0, x1 = int(math.floor(cx - rx)), int(math.ceil(cx + rx)) + 1
    y0, y1 = int(math.floor(cy - ry)), int(math.ceil(cy + ry)) + 1
    xs = np.arange(x0, x1)
    ys = np.arange(y0, y1)
    DX, DY = np.meshgrid(xs + 0.5 - cx, ys + 0.5 - cy)
    return ys % h, xs % w, DX, DY


def composite(canvas: np.ndarray, iy, ix, alpha: np.ndarray, value) -> None:
    """Alpha-over a constant colour/value (or per-pixel array) into canvas."""
    sub = canvas[np.ix_(iy, ix)]
    a = alpha[..., None] if canvas.ndim == 3 else alpha
    val = np.asarray(value)
    canvas[np.ix_(iy, ix)] = sub * (1 - a) + val * a


def maxinto(canvas: np.ndarray, iy, ix, value: np.ndarray) -> None:
    sub = canvas[np.ix_(iy, ix)]
    canvas[np.ix_(iy, ix)] = np.maximum(sub, value)


def cover(sdf_px: np.ndarray, aa: float = 0.75) -> np.ndarray:
    """Anti-aliased coverage from a signed distance in pixels (negative inside)."""
    return np.clip(0.5 - sdf_px / (2 * aa), 0, 1)


def rot(DX, DY, ang):
    c, s = math.cos(ang), math.sin(ang)
    return DX * c + DY * s, -DX * s + DY * c


def sd_ellipse(DX, DY, a, b):
    """Approximate SDF of an axis-aligned ellipse (good enough for small shapes)."""
    k = np.sqrt((DX / a) ** 2 + (DY / b) ** 2)
    return (k - 1) * min(a, b)


def sd_leaf(DX, DY, length, width):
    """Pointed leaf (vesica) along +X from the origin, in local coordinates."""
    # map so leaf spans x in [0, length]
    x = DX - length * 0.5
    y = DY
    # vesica: intersection of two circles
    half = length * 0.5
    rr = (half * half + width * width) / (2 * width)
    d1 = np.sqrt(x * x + (y + (rr - width)) ** 2) - rr
    d2 = np.sqrt(x * x + (y - (rr - width)) ** 2) - rr
    return np.maximum(d1, d2)


def sd_segment(DX, DY, ax, ay, bx, by):
    pax, pay = DX - ax, DY - ay
    bax, bay = bx - ax, by - ay
    t = np.clip((pax * bax + pay * bay) / (bax * bax + bay * bay + 1e-9), 0, 1)
    ex, ey = pax - bax * t, pay - bay * t
    return np.sqrt(ex * ex + ey * ey), t


# ---------------------------------------------------------------------------
# strands
# ---------------------------------------------------------------------------

def render_strands(h: int, w: int, strands: dict, zbuf: np.ndarray, rgb: np.ndarray,
                   tip_round: float = 1.0) -> None:
    """Z-buffered capsule strands (yarn tufts, fibres).

    strands: dict of equal-length arrays
      x, y      base position (px)
      ang       direction (radians, image space)
      length    projected length (px)
      rad       radius (px)
      z0, z1    height (mm) at base and tip of the strand axis
      col       (N, 3) colour
      s0, s1    brightness multiplier at base / tip
    zbuf/rgb are modified in place.
    """
    n = len(strands['x'])
    for i in range(n):
        x, y = strands['x'][i], strands['y'][i]
        ang, L, r = strands['ang'][i], strands['length'][i], strands['rad'][i]
        dx, dy = math.cos(ang) * L, math.sin(ang) * L
        cx, cy = x + dx * 0.5, y + dy * 0.5
        ext = abs(dx) * 0.5 + r + 1, abs(dy) * 0.5 + r + 1
        iy, ix, DX, DY = patch(h, w, cx, cy, ext[0], ext[1])
        d, t = sd_segment(DX, DY, -dx * 0.5, -dy * 0.5, dx * 0.5, dy * 0.5)
        inside = d < r
        if not inside.any():
            continue
        prof = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
        z = strands['z0'][i] + (strands['z1'][i] - strands['z0'][i]) * t + prof * r * strands.get('zr', np.full(n, 0.1))[i]
        zsub = zbuf[np.ix_(iy, ix)]
        m = inside & (z > zsub)
        if not m.any():
            continue
        zsub = np.where(m, z, zsub)
        zbuf[np.ix_(iy, ix)] = zsub
        shade = (strands['s0'][i] + (strands['s1'][i] - strands['s0'][i]) * t) * (0.72 + 0.28 * prof)
        col = strands['col'][i][None, None, :] * shade[..., None]
        sub = rgb[np.ix_(iy, ix)]
        rgb[np.ix_(iy, ix)] = np.where(m[..., None], col, sub)


# ---------------------------------------------------------------------------
# weave
# ---------------------------------------------------------------------------

PLAIN = np.array([[1, 0], [0, 1]])
TWILL22 = np.array([[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1], [1, 0, 0, 1]])
BASKET = np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]])


def weave(h: int, w: int, nx: int, ny: int, pattern: np.ndarray, r: np.random.Generator,
          warp_cols: np.ndarray | None = None, weft_cols: np.ndarray | None = None,
          thread_fill: float = 0.85, fuzz: float = 0.15):
    """Woven cloth. nx warp (vertical) threads and ny weft (horizontal) threads
    across the tile. pattern[j % p, i % p] == 1 means the warp is on top.

    Returns (height 0..1, rgb or None, top_is_warp mask).
    """
    xs = (np.arange(w) + 0.5) * nx / w
    ys = (np.arange(h) + 0.5) * ny / h
    i = np.floor(xs).astype(int)
    j = np.floor(ys).astype(int)
    fx = xs - i
    fy = ys - j
    # per-thread wobble in thickness
    tw = 1 + 0.12 * r.standard_normal(nx)
    th = 1 + 0.12 * r.standard_normal(ny)
    wx = np.clip(np.abs(2 * fx - 1) / (thread_fill * tw[i]), 0, 1)   # warp cross-section
    wy = np.clip(np.abs(2 * fy - 1) / (thread_fill * th[j]), 0, 1)   # weft cross-section
    prof_warp = np.sqrt(1 - wx ** 2)[None, :]
    prof_weft = np.sqrt(1 - wy ** 2)[:, None]
    p = pattern.shape[0]
    top = pattern[(j % p)[:, None], (i % p)[None, :]].astype(bool)
    # undulation: the thread on top arches over the crossing
    arch_warp = (0.55 + 0.45 * np.sin(math.pi * fy))[:, None]
    arch_weft = (0.55 + 0.45 * np.sin(math.pi * fx))[None, :]
    hw = prof_warp * arch_warp
    hf = prof_weft * arch_weft
    height = np.where(top, 0.35 + 0.65 * hw, 0.35 + 0.65 * hf)
    gap = np.where(top, prof_warp, prof_weft) <= 0
    height = np.where(gap, np.minimum(hw, hf) * 0.3, height)
    rgb = None
    if warp_cols is not None and weft_cols is not None:
        cw = warp_cols[i % len(warp_cols)][None, :, :]
        cf = weft_cols[j % len(weft_cols)][:, None, :]
        rgb = np.where(top[..., None], np.broadcast_to(cw, (h, w, 3)), np.broadcast_to(cf, (h, w, 3)))
        sh = (0.78 + 0.22 * np.where(top, hw, hf))[..., None]
        rgb = rgb * sh
    if fuzz > 0:
        height = height + fuzz * r.uniform(-1, 1, size=(h, w)) * 0.5
    return height, rgb, top
