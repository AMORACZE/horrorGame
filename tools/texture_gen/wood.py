"""Wood grain synthesis shared by panelling, floors, furniture woods and oak.

The grain model slices a virtual log: a board's surface is a plane at depth
``d`` from the pith, offset ``uc`` sideways. The growth-ring radius at a surface
point is sqrt((u-uc)^2 + d^2) plus a slow change along the board (taper),
giving straight grain near the edges and cathedral arches over the pith.
"""
from __future__ import annotations

import math

import numpy as np

from .core import blur, fbm, norm01, smoothstep, vnoise


_RING_TABLE = None


def _ring_table():
    """Cumulative table of irregular ring widths (mean 1): real growth rings
    vary year to year, which is what stops grain looking like a contour plot."""
    global _RING_TABLE
    if _RING_TABLE is None:
        r = np.random.default_rng(1971)
        wdt = np.exp(r.normal(0, 0.4, 4000))
        wdt = wdt * (1 + 0.5 * np.sin(np.arange(4000) / 23.0))  # slow good/bad decades
        wdt /= wdt.mean()
        _RING_TABLE = np.r_[0, np.cumsum(wdt)]
    return _RING_TABLE


def log_rings(u_mm, v_mm, uc, depth, taper, ring_mm, warp_mm, period_mm=None):
    """Ring phase for board-local coordinates.

    u_mm/v_mm: across/along the board (arrays). uc/depth/taper/ring_mm may be
    per-pixel arrays (gathered per board). If ``period_mm`` is given the taper
    term is made periodic along v (for continuous tiling sheets)."""
    du = u_mm - uc
    rad = np.sqrt(du * du + depth * depth)
    if period_mm:
        along = taper * period_mm / (2 * math.pi) * np.sin(2 * math.pi * v_mm / period_mm)
    else:
        along = taper * v_mm
    x = (rad + along + warp_mm) / ring_mm + 40.0
    tab = _ring_table()
    return np.interp(x, tab, np.arange(len(tab)))


def ring_profile(phase, sharp=0.5):
    """0..1 latewood density from ring phase (1 = dark latewood)."""
    f = phase - np.floor(phase)
    late = smoothstep(0.35 + 0.3 * sharp, 0.86, f) * (1 - smoothstep(0.88, 1.0, f))
    return late


def pores(h: int, w: int, r: np.random.Generator, across: int, along: int, thresh: float = 0.55) -> np.ndarray:
    """Elongated pore flecks (oak, walnut). 0..1, 1 = pore."""
    n = vnoise(h, w, along, across, r, cubic=False)
    n += 0.5 * vnoise(h, w, along * 2, across * 2, r, cubic=False)
    return smoothstep(thresh, thresh + 0.35, norm01(n))


def fibre_streaks(h: int, w: int, r: np.random.Generator, across: int, along: int) -> np.ndarray:
    """Fine longitudinal fibre streaking (-1..1)."""
    return vnoise(h, w, along, across, r) * 0.6 + 0.4 * vnoise(h, w, along * 2, across * 2, r)


def warp_field(h: int, w: int, r: np.random.Generator, along: int, across: int, amp_mm: float):
    """Smooth grain wander (mm), stretched along the grain."""
    return amp_mm * (fbm(h, w, along, across, r, 3, 0.5))


def sheet_grain(h, w, r, w_mm, h_mm, ring_mm=4.0, boards=None):
    """Grain for a continuous tileable sheet whose grain runs vertically.

    ``boards``: optional per-column board index (w,) to give each strip its own
    log. Returns (phase, late, board_index_map)."""
    xmm = (np.arange(w) + 0.5) * w_mm / w
    ymm = (np.arange(h) + 0.5) * h_mm / h
    X = np.broadcast_to(xmm[None, :], (h, w))
    Y = np.broadcast_to(ymm[:, None], (h, w))
    if boards is None:
        boards = np.zeros(w, dtype=int)
    B = np.broadcast_to(boards[None, :], (h, w))
    nb = int(boards.max()) + 1
    # board extents
    left = np.array([xmm[boards == b].min() if (boards == b).any() else 0 for b in range(nb)])
    right = np.array([xmm[boards == b].max() if (boards == b).any() else 0 for b in range(nb)])
    bw = right - left + 1e-3
    uc = left + bw * r.uniform(0.1, 0.9, nb)
    depth = r.uniform(25.0, 90.0, nb)
    taper = r.uniform(0.001, 0.004, nb) * r.choice([-1, 1], nb)
    rmm = ring_mm * r.uniform(0.75, 1.3, nb)
    wf = warp_field(h, w, r, 2, max(2, int(w_mm / 150)), 7.0) + warp_field(h, w, r, 6, max(4, int(w_mm / 40)), 0.8)
    phase = log_rings(X, Y, uc[B], depth[B], taper[B] * 40.0, rmm[B], wf, period_mm=h_mm)
    phase = phase + r.uniform(0, 50, nb)[B]
    late = blur(ring_profile(phase), 0.8)
    return phase, late, B
