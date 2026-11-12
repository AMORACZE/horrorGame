"""Prop / furniture / small-surface sets (object-space triplanar, mostly 512 px)."""
from __future__ import annotations

import math

import numpy as np

from . import draw
from .core import (age, blur, cavity_ao, colorize, downsample, fbm, lerp, luminance, norm01,
                   rng, saturate, smoothstep, spectral, srgb, vnoise, white, worley)
from .wood import fibre_streaks, log_rings, pores, ring_profile, sheet_grain, warp_field

S = 512


def _fine(h, w, r, sigma):
    f = blur(white(h, w, r), sigma)
    return f / (np.abs(f).max() + 1e-9)


# ---------------------------------------------------------------------------
# furniture woods: one grain/normal/ORM, three stains
# ---------------------------------------------------------------------------

def _furniture_grain():
    r = rng('furniture_wood')
    h = w = S
    T = 500.0
    px = T / w
    # glued-up boards of varying width, grain vertical
    widths = []
    acc = 0.0
    while acc < T - 60:
        bw = r.uniform(70, 140)
        widths.append(bw)
        acc += bw
    widths[-1] += T - acc
    edges = np.cumsum([0] + widths)
    xmm = (np.arange(w) + 0.5) * px
    boards = np.searchsorted(edges, xmm, side='right') - 1
    phase, late, B = sheet_grain(h, w, r, T, T, ring_mm=4.0, boards=boards)
    streak = fibre_streaks(h, w, r, 160, 6)
    por = pores(h, w, r, 200, 24, 0.66) * (0.3 + 0.7 * late)
    tone = r.normal(0, 1, len(widths))
    fig = fbm(h, w, 4, 16, r, 3)
    t = 0.55 + 0.08 * tone[B] + 0.06 * streak + 0.06 * fig - 0.28 * late - 0.1 * por
    hmm = 0.03 * (1 - late) - 0.03 * por + 0.01 * streak
    rough = 0.42 + 0.06 * late + 0.08 * por + 0.06 * norm01(fbm(h, w, 3, 3, r, 3))
    return r, t, hmm, rough, px


def wood_furniture():
    r, t, hmm, rough, px = _furniture_grain()
    alb = colorize(np.clip(t, 0, 1), [(0, '#3a2414'), (0.5, '#6a4426'), (1, '#9a6c42')])
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=np.ones_like(t), no_albedo=True)


def _stain(stops, seed):
    r, t, hmm, rough, px = _furniture_grain()
    alb = colorize(np.clip(t, 0, 1), stops)
    alb = age(alb, rng(seed), yellow=0.04, fade=0.06, grime=0.06, cells=2)
    return dict(albedo=alb, rough=rough, px=(px, px), no_orm=True)


def wood_dark():
    return _stain([(0, '#120a05'), (0.45, '#2a180c'), (0.75, '#3d2414'), (1, '#55351e')], 'wd')


def wood_medium():
    return _stain([(0, '#2e1a0c'), (0.45, '#5a361a'), (0.75, '#7a4c28'), (1, '#94633a')], 'wm')


def wood_light():
    return _stain([(0, '#6a4a2a'), (0.45, '#a07a4e'), (0.75, '#bf9868'), (1, '#d2ae80')], 'wl')


def wood_oak_cabinet():
    """Golden-oak finish (1980s kitchen cabinets): bold cathedral grain, open pores."""
    r = rng('oak_cab')
    h = w = S
    T = 600.0
    px = T / w
    boards = (((np.arange(w) + 0.5) * px) // 150).astype(int)
    phase, late, B = sheet_grain(h, w, r, T, T, ring_mm=5.0, boards=boards)
    por = pores(h, w, r, 260, 30, 0.6) * (0.25 + 0.75 * late)
    ray = smoothstep(0.8, 0.95, norm01(vnoise(h, w, 120, 30, r, cubic=False))) * 0.5
    streak = fibre_streaks(h, w, r, 180, 6)
    t = 0.62 + 0.05 * streak - 0.3 * late - 0.18 * por + 0.05 * ray
    alb = colorize(np.clip(t, 0, 1), [(0, '#5a3614'), (0.45, '#93622c'), (0.75, '#b7843f'), (1, '#cc9d58')])
    alb = age(alb, r, yellow=0.06, fade=0.05, grime=0.1, cells=2)
    hmm = 0.03 * (1 - late) - 0.06 * por
    rough = 0.38 + 0.12 * por + 0.05 * late + 0.06 * norm01(fbm(h, w, 3, 3, r, 3))
    ao = 1 - 0.3 * por
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# laminate_formica : warm beige speckle ("sand / gold fleck") countertop
# ---------------------------------------------------------------------------

def laminate_formica():
    r = rng('formica')
    h = w = S
    T = 300.0
    px = T / w
    base = np.broadcast_to(srgb('#d5c5a0'), (h, w, 3)).copy()
    cloud = norm01(fbm(h, w, 6, 6, r, 4))
    base = lerp(base, srgb('#c7b38a'), cloud * 0.5)
    img = base
    # speckles of several sizes/colours
    for col, n, rad in (('#7a5a34', 2200, 0.9), ('#a8844e', 2600, 1.1), ('#f2e8d2', 2000, 0.8),
                        ('#4e3a26', 700, 0.7), ('#c9a35a', 900, 1.5)):
        c = srgb(col)
        for _ in range(n):
            x, y = r.uniform(0, w), r.uniform(0, h)
            rr = rad * r.uniform(0.6, 1.4)
            iy, ix, DX, DY = draw.patch(h, w, x, y, rr + 2)
            a = r.uniform(0, math.pi)
            RX, RY = draw.rot(DX, DY, a)
            d = draw.sd_ellipse(RX, RY, rr * r.uniform(1, 1.8), rr)
            draw.composite(img, iy, ix, draw.cover(d, 0.6), c)
    img = age(img, r, yellow=0.08, fade=0.04, grime=0.04, cells=2)
    hmm = 0.01 * _fine(h, w, r, 1.0)
    # wiped areas are glossier, edges of use duller; tiny knife marks
    rough = 0.32 + 0.08 * norm01(fbm(h, w, 4, 4, r, 3))
    cuts = np.zeros((h, w))
    for _ in range(40):
        x0, y0 = r.uniform(0, w), r.uniform(0, h)
        ang = r.uniform(0, math.pi)
        L = r.uniform(8, 40)
        iy, ix, DX, DY = draw.patch(h, w, x0, y0, L / 2 + 2)
        d, _ = draw.sd_segment(DX, DY, -math.cos(ang) * L / 2, -math.sin(ang) * L / 2,
                               math.cos(ang) * L / 2, math.sin(ang) * L / 2)
        draw.maxinto(cuts, iy, ix, (1 - smoothstep(0.1, 0.6, d)) * r.uniform(0.3, 1))
    rough = rough + 0.25 * cuts
    hmm = hmm - 0.01 * cuts
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=np.ones((h, w)))


# ---------------------------------------------------------------------------
# plastics: shared moulded-stipple normal/ORM, yellowed beige ABS albedo
# ---------------------------------------------------------------------------

def plastic_texture():
    r = rng('plastic')
    h = w = S
    T = 200.0
    px = T / w
    stip = _fine(h, w, r, 0.9)
    stip2 = _fine(h, w, r, 2.0)
    hmm = 0.012 * stip + 0.01 * stip2
    rough = 0.48 + 0.05 * stip2 - 0.03 * norm01(fbm(h, w, 6, 6, r, 3))
    alb = np.ones((h, w, 3)) * (1 + 0.02 * fbm(h, w, 8, 8, r, 3))[..., None] * 0.98
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=np.ones((h, w)))


def plastic_beige():
    r = rng('plastic_beige')
    h = w = S
    T = 200.0
    base = np.broadcast_to(srgb('#cfc4a6'), (h, w, 3)).copy()
    # UV yellowing is blotchy and stronger where the sun hit
    y1 = norm01(fbm(h, w, 2, 2, r, 4))
    base = lerp(base, srgb('#cbb886'), smoothstep(0.2, 0.9, y1) * 0.35)
    base = base * (1 + 0.012 * fbm(h, w, 30, 30, r, 3))[..., None]
    grime = smoothstep(0.6, 0.9, norm01(fbm(h, w, 6, 6, r, 3)))
    base = lerp(base, base * srgb('#9a8c72'), grime * 0.08)
    return dict(albedo=base, rough=np.zeros((h, w)), px=(T / w, T / w), no_orm=True)


# ---------------------------------------------------------------------------
# metals
# ---------------------------------------------------------------------------

def metal_brass():
    r = rng('brass')
    h = w = S
    T = 300.0
    px = T / w
    brushed = vnoise(h, w, 2, 300, r) * 0.5 + 0.5 * vnoise(h, w, 4, 160, r)
    tarn = norm01(fbm(h, w, 4, 4, r, 5))
    tarn = smoothstep(0.35, 0.85, tarn)
    spots = smoothstep(0.75, 0.9, norm01(fbm(h, w, 24, 24, r, 3)))
    alb = lerp(srgb('#dcb878'), srgb('#a88a58'), tarn * 0.5)
    alb = lerp(alb, srgb('#6d5a3a'), spots * 0.2)
    alb = alb * (1 + 0.03 * brushed[..., None])
    rough = 0.25 + 0.2 * tarn + 0.12 * spots + 0.04 * brushed
    hmm = 0.004 * brushed
    metal = 1 - 0.25 * spots
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=np.ones((h, w)), metal=metal)


def metal_chrome():
    r = rng('chrome')
    h = w = S
    T = 300.0
    px = T / w
    smudge = smoothstep(0.45, 0.85, norm01(fbm(h, w, 5, 5, r, 5)))
    prints = np.zeros((h, w))
    for _ in range(14):
        x, y = r.uniform(0, w), r.uniform(0, h)
        rad = r.uniform(14, 22)
        iy, ix, DX, DY = draw.patch(h, w, x, y, rad)
        rr = np.sqrt(DX ** 2 + (DY * 1.3) ** 2)
        whorl = 0.5 + 0.5 * np.sin(rr * 1.3)
        m = (1 - smoothstep(rad * 0.6, rad, rr)) * whorl
        draw.maxinto(prints, iy, ix, m)
    pits = smoothstep(0.985, 1.0, norm01(white(h, w, r)))
    alb = np.broadcast_to(srgb('#d8d8d6'), (h, w, 3)) * (1 - 0.06 * smudge - 0.4 * pits)[..., None]
    rough = 0.06 + 0.18 * smudge + 0.2 * prints + 0.4 * pits
    return dict(albedo=alb, height=-0.01 * pits, px=(px, px), rough=rough, ao=np.ones((h, w)),
                metal=np.ones((h, w)) - 0.5 * pits)


def metal_dark():
    """Dark cast iron / blued steel: radiator, stove grate, tools."""
    r = rng('metal_dark')
    h = w = S
    T = 300.0
    px = T / w
    cast = _fine(h, w, r, 1.3)
    blot = norm01(fbm(h, w, 6, 6, r, 4))
    rust = smoothstep(0.78, 0.92, norm01(fbm(h, w, 16, 16, r, 4)))
    alb = colorize(blot, [(0, '#1a1a1b'), (1, '#2c2b29')])
    alb = lerp(alb, srgb('#5a3a22'), rust * 0.6)
    rough = 0.45 + 0.15 * blot + 0.35 * rust
    metal = 0.85 - 0.75 * rust
    hmm = 0.05 * cast + 0.04 * rust
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=np.ones((h, w)), metal=metal)


# ---------------------------------------------------------------------------
# enamel : baked appliance enamel (orange peel) - harvest gold, avocado, white
# ---------------------------------------------------------------------------

def enamel():
    r = rng('enamel')
    h = w = S
    T = 400.0
    px = T / w
    peel = _fine(h, w, r, 3.0) * 0.7 + 0.3 * _fine(h, w, r, 1.5)
    hmm = 0.02 * peel
    wipe = smoothstep(0.5, 0.9, norm01(fbm(h, w, 3, 6, r, 4)))
    prints = smoothstep(0.7, 0.9, norm01(fbm(h, w, 14, 14, r, 3)))
    rough = 0.16 + 0.12 * wipe + 0.15 * prints
    alb = np.ones((h, w, 3)) * (1 - 0.025 * wipe - 0.03 * prints)[..., None]
    alb = alb * (1 + 0.01 * fbm(h, w, 6, 6, r, 3))[..., None]
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=np.ones((h, w)))


# ---------------------------------------------------------------------------
# fabrics
# ---------------------------------------------------------------------------

def fabric_floral_sofa():
    """1980s upholstery: large dusty-rose and mauve blooms with teal-sage
    leaves on an oatmeal woven ground."""
    r = rng('sofa')
    h = w = 1024
    T = 600.0
    px = T / w
    SS = 1
    img = np.broadcast_to(srgb('#d9cbb0'), (h, w, 3)).copy()
    # background faint trellis/leaf shadows
    shadow = smoothstep(0.55, 0.75, norm01(fbm(h, w, 6, 6, r, 4)))
    img = lerp(img, srgb('#c4b394'), shadow * 0.4)
    petal = [srgb('#b06a72'), srgb('#8e4f66'), srgb('#c48a84'), srgb('#7e4660')]
    leaves = [srgb('#5a7a68'), srgb('#456455'), srgb('#7a967e')]
    mot = []
    for gx in range(2):
        for gy in range(2):
            x = (gx + 0.5 + 0.5 * (gy % 2)) * w / 2 + r.normal(0, 25)
            y = (gy + 0.5) * h / 2 + r.normal(0, 25)
            mot.append((x, y, 1.0))
            mot.append((x + w / 4 + r.normal(0, 20), y + h / 4 * 0.9 + r.normal(0, 20), 0.55))
    # leaves first
    for (x, y, sc) in mot:
        for k in range(r.integers(5, 8)):
            a = r.uniform(0, 2 * math.pi)
            dist = r.uniform(130, 210) * sc
            lx, ly = x + math.cos(a) * dist * 0.4, y + math.sin(a) * dist * 0.4
            L, W = r.uniform(190, 270) * sc, r.uniform(55, 80) * sc
            iy, ix, DX, DY = draw.patch(h, w, lx, ly, L + 4)
            RX, RY = draw.rot(DX, DY, a)
            d = draw.sd_leaf(RX, RY, L, W)
            c = leaves[r.integers(0, 3)]
            draw.composite(img, iy, ix, draw.cover(d), c)
            draw.composite(img, iy, ix, draw.cover(np.maximum(np.abs(RY) - 2.0, d + 4)) * 0.7, c * 0.65)
            draw.composite(img, iy, ix, draw.cover(np.abs(d) - 1.2) * 0.5, c * 0.6)
    for (x, y, sc) in mot:
        R = r.uniform(150, 180) * sc
        pc = petal[r.integers(0, 4)]
        iy, ix, DX, DY = draw.patch(h, w, x, y, R * 1.4)
        for ring_i, (rr, npet) in enumerate(((1.0, 8), (0.75, 7), (0.5, 6), (0.28, 5))):
            for p in range(npet):
                a = p * 2 * math.pi / npet + ring_i * 0.37 + r.uniform(-0.15, 0.15)
                ex, ey = draw.rot(DX - math.cos(a) * R * rr * 0.5, DY - math.sin(a) * R * rr * 0.5, a)
                d = draw.sd_ellipse(ex, ey, R * rr * 0.5, R * rr * 0.4)
                col = np.clip(pc * (0.85 + 0.12 * ring_i), 0, 1)
                draw.composite(img, iy, ix, draw.cover(d), col)
                draw.composite(img, iy, ix, draw.cover(np.abs(d) - 1.5) * 0.6, pc * 0.55)
    # small buds scattered
    for _ in range(26):
        x, y = r.uniform(0, w), r.uniform(0, h)
        iy, ix, DX, DY = draw.patch(h, w, x, y, 18)
        d = np.sqrt(DX ** 2 + DY ** 2) - r.uniform(6, 10)
        draw.composite(img, iy, ix, draw.cover(d), petal[r.integers(0, 4)] * 1.05)
    # woven ground: printed design sits on a basket weave
    ht, _, top = draw.weave(h, w, 400, 400, draw.BASKET, r, fuzz=0.25)
    img = img * (0.86 + 0.14 * ht)[..., None]
    img = age(img, r, yellow=0.08, fade=0.2, grime=0.12, cells=2)
    hmm = 0.35 * ht + 0.25 * fbm(h, w, 6, 6, r, 3)
    rough = 0.9 + 0.05 * ht
    ao = 0.75 + 0.25 * ht
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


def fabric_corduroy_brown():
    r = rng('corduroy')
    h = w = S
    T = 200.0
    px = T / w
    nw = 50                         # 4 mm wide wales, running vertically
    x = (np.arange(w) + 0.5) / w * nw
    f = x - np.floor(x)
    prof = np.sqrt(np.clip(1 - (2 * f - 1) ** 2 / 0.85, 0, 1))
    prof = np.broadcast_to(prof[None, :], (h, w))
    pile = _fine(h, w, r, 0.7)
    crush = smoothstep(0.55, 0.9, norm01(fbm(h, w, 8, 4, r, 4))) * 0.5
    hmm = 1.1 * prof + 0.06 * pile - 0.3 * crush * prof
    base = srgb('#6a4428')
    t = 0.45 + 0.55 * prof ** 0.7 + 0.08 * pile
    img = base * t[..., None]
    # worn wale tops go lighter and flatter
    img = lerp(img, srgb('#8a6a4c'), crush * prof * 0.3)
    img = age(img, r, yellow=0.02, fade=0.12, grime=0.08, cells=2)
    rough = 0.92 - 0.12 * crush * prof
    ao = 0.55 + 0.45 * prof
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


def fabric_plaid():
    """Brown / rust / cream / mustard tartan in a 2/2 twill."""
    r = rng('plaid')
    h = w = S
    T = 250.0
    px = T / w
    sett = [('#4a2c1c', 17), ('#9a4a24', 6), ('#4a2c1c', 4), ('#d8c49a', 2), ('#4a2c1c', 4),
            ('#b88a34', 10), ('#2c2118', 3), ('#b88a34', 10), ('#4a2c1c', 4), ('#d8c49a', 2),
            ('#4a2c1c', 4), ('#9a4a24', 6)]
    cols = []
    for c, n in sett:
        cols += [srgb(c)] * n
    cols = np.array(cols)       # 71 threads per sett
    reps = 2
    n = len(cols) * reps
    ht, rgb, top = draw.weave(h, w, n, n, draw.TWILL22, r, warp_cols=cols, weft_cols=cols, fuzz=0.2)
    rgb = rgb * (1 + 0.05 * _fine(h, w, r, 0.8))[..., None]
    rgb = age(rgb, r, yellow=0.04, fade=0.12, grime=0.1, cells=2)
    hmm = 0.3 * ht
    rough = 0.9 + 0.05 * ht
    ao = 0.7 + 0.3 * ht
    return dict(albedo=rgb, height=hmm, px=(px, px), rough=rough, ao=ao)


def fabric_lampshade():
    r = rng('lampshade')
    h = w = S
    T = 150.0
    px = T / w
    ht, _, _ = draw.weave(h, w, 170, 150, draw.PLAIN, r, fuzz=0.15)
    slub = vnoise(h, w, 150, 8, r)                     # slubby linen yarn, horizontal
    slub2 = vnoise(h, w, 10, 170, r)
    img = np.broadcast_to(srgb('#e2d2ae'), (h, w, 3)) * (0.9 + 0.1 * ht + 0.04 * slub + 0.03 * slub2)[..., None]
    img = age(img, r, yellow=0.2, fade=0.0, grime=0.05, cells=2)
    hmm = 0.12 * ht + 0.04 * slub
    return dict(albedo=img, height=hmm, px=(px, px), rough=np.full((h, w), 0.92), ao=0.8 + 0.2 * ht)


def _pleats(h, w, r, n_pleats, depth_mm, T):
    """Vertical folds: a wandering sinusoid across x (n_pleats per tile)."""
    x = (np.arange(w) + 0.5) / w
    wob = fbm(h, w, 2, n_pleats, r, 3) * 0.025
    ph = (x[None, :] + wob) * n_pleats * 2 * math.pi
    amp = 1 + 0.25 * vnoise(h, w, 1, n_pleats, r)
    return depth_mm * amp * (0.5 + 0.5 * np.sin(ph)), 0.5 + 0.5 * np.sin(ph)


def fabric_curtain_heavy():
    """Lined drapery in a textured rust/mustard slub weave with deep pleats."""
    r = rng('curtain_heavy')
    h = w = 1024
    T = 600.0
    px = T / w
    ht, _, _ = draw.weave(h, w, 400, 300, draw.BASKET, r, fuzz=0.2)
    slub = vnoise(h, w, 300, 10, r)
    pl, s = _pleats(h, w, r, 4, 30.0, T)
    base = colorize(norm01(fbm(h, w, 4, 8, r, 3)), [(0, '#8c7034'), (1, '#9c7e3e')])
    img = base * (0.85 + 0.12 * ht + 0.05 * slub)[..., None]
    # sun-faded on the outward folds (the parts facing the window), low frequency
    img = lerp(img, saturate(img, 0.6) * 1.15, (s * 0.25 + 0.15 * norm01(fbm(h, w, 2, 2, r, 3))))
    img = age(img, r, yellow=0.02, fade=0.08, grime=0.06, cells=2)
    hmm = pl + 0.25 * ht + 0.1 * slub
    ao = (0.8 + 0.2 * s) * (0.85 + 0.15 * ht)
    return dict(albedo=img, height=hmm, px=(px, px), rough=np.full((h, w), 0.95), ao=ao)


def fabric_curtain_sheer():
    """Ivory voile: open weave (alpha) with soft vertical folds."""
    r = rng('curtain_sheer')
    h = w = S
    T = 600.0
    px = T / w
    pl, s = _pleats(h, w, r, 6, 20.0, T)
    slub = vnoise(h, w, 200, 6, r) * 0.5 + 0.5 * vnoise(h, w, 6, 220, r)
    # gathered fabric reads denser in the fold troughs
    dens = 0.42 + 0.18 * (1 - s) + 0.05 * slub
    dust = norm01(fbm(h, w, 3, 3, r, 3))
    img = np.broadcast_to(srgb('#ece4cf'), (h, w, 3)) * (0.95 + 0.05 * slub)[..., None]
    img = lerp(img, srgb('#d8c9a0'), dust * 0.3)
    hmm = pl + 0.05 * slub
    return dict(albedo=img, alpha=dens, height=hmm, px=(px, px), rough=np.full((h, w), 0.95),
                ao=0.85 + 0.15 * s)


def dust_sheet():
    """Unbleached muslin drop cloth thrown over furniture."""
    r = rng('dust_sheet')
    h = w = S
    T = 500.0
    px = T / w
    ht, _, _ = draw.weave(h, w, 340, 340, draw.PLAIN, r, fuzz=0.3)
    folds = fbm(h, w, 3, 3, r, 4)
    creases = 1 - np.abs(fbm(h, w, 5, 5, r, 3))
    creases = smoothstep(0.85, 1.0, creases)
    img = np.broadcast_to(srgb('#ddd6c4'), (h, w, 3)) * (0.92 + 0.08 * ht)[..., None]
    img = age(img, r, yellow=0.1, fade=0.0, grime=0.2, cells=2)
    hmm = 18.0 * folds + 0.4 * creases + 0.08 * ht
    return dict(albedo=img, height=hmm, px=(px, px), rough=np.full((h, w), 0.96),
                ao=cavity_ao(hmm, 30, 6.0) * (0.9 + 0.1 * ht))


def leather_brown():
    r = rng('leather')
    h = w = S
    T = 250.0
    px = T / w
    f1, f2, _ = worley(h, w, 150, 150, r)
    grain = smoothstep(0.0, 0.35, f2 - f1)
    f1b, f2b, _ = worley(h, w, 60, 60, r)
    grain2 = smoothstep(0.0, 0.25, f2b - f1b)
    creases = smoothstep(0.95, 1.0, 1 - np.abs(fbm(h, w, 4, 6, r, 4))) * 0.5
    wear = smoothstep(0.5, 0.9, norm01(fbm(h, w, 3, 3, r, 4))) * 0.4
    hmm = 0.06 * grain + 0.05 * grain2 - 0.12 * creases
    t = 0.5 + 0.12 * grain - 0.1 * (1 - grain2) - 0.12 * creases + 0.15 * wear
    img = colorize(np.clip(t, 0, 1), [(0, '#1e100a'), (0.5, '#45281a'), (1, '#7a5034')])
    img = age(img, r, yellow=0.0, fade=0.1, grime=0.06, cells=2)
    rough = 0.45 + 0.1 * (1 - grain) + 0.15 * creases - 0.12 * wear
    ao = 0.8 + 0.2 * grain
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


def rubber_black():
    r = rng('rubber')
    h = w = S
    T = 150.0
    px = T / w
    stip = _fine(h, w, r, 1.0)
    bloom = smoothstep(0.4, 0.9, norm01(fbm(h, w, 12, 12, r, 4)))   # grey sulphur bloom / dust
    img = lerp(np.broadcast_to(srgb('#141414'), (h, w, 3)), srgb('#3a3834'), bloom * 0.25)
    return dict(albedo=img, height=0.01 * stip, px=(px, px), rough=0.85 + 0.1 * bloom,
                ao=np.ones((h, w)))


# ---------------------------------------------------------------------------
# glass
# ---------------------------------------------------------------------------

def glass_dusty():
    r = rng('glass_dusty')
    h = w = S
    T = 500.0
    px = T / w
    film = norm01(fbm(h, w, 3, 3, r, 5))
    specks = smoothstep(0.93, 0.99, norm01(white(h, w, r)))
    streak = smoothstep(0.5, 0.9, norm01(fbm(h, w, 2, 14, r, 4)))   # old wipe streaks
    a = 0.1 + 0.16 * film + 0.06 * streak + 0.3 * specks
    img = np.broadcast_to(srgb('#c9c2ae'), (h, w, 3)).copy()
    img = lerp(img, srgb('#9a9280'), specks * 0.6)
    rough = 0.2 + 0.35 * film + 0.3 * specks
    return dict(albedo=img, alpha=a, height=None, px=(px, px), rough=rough, ao=np.ones((h, w)))


# ---------------------------------------------------------------------------
# ceramic, paper, cardboard, books, plant
# ---------------------------------------------------------------------------

def ceramic_white():
    r = rng('ceramic')
    h = w = S
    T = 200.0
    px = T / w
    wav = fbm(h, w, 5, 5, r, 3)
    # fine crazing in the glaze: Worley cell borders, faint and stained
    f1, f2, _ = worley(h, w, 18, 18, r)
    craze = 1 - smoothstep(0.0, 0.025, f2 - f1)
    craze *= smoothstep(0.4, 0.8, norm01(fbm(h, w, 3, 3, r, 3)))
    img = np.broadcast_to(srgb('#ebe7dc'), (h, w, 3)) * (1 - 0.06 * craze)[..., None]
    img = age(img, r, yellow=0.06, fade=0.0, grime=0.04, cells=2)
    return dict(albedo=img, height=0.05 * wav - 0.003 * craze, px=(px, px),
                rough=0.07 + 0.04 * norm01(wav) + 0.2 * craze, ao=np.ones((h, w)))


def paper_texture():
    r = rng('paper')
    h = w = S
    T = 300.0
    px = T / w
    fib = _fine(h, w, r, 0.8) * 0.5 + 0.5 * _fine(h, w, r, 2.5)
    cockle = fbm(h, w, 3, 3, r, 3)
    alb = np.ones((h, w, 3)) * (0.97 + 0.03 * fib)[..., None]
    return dict(albedo=alb, height=0.01 * fib + 0.4 * cockle, px=(px, px),
                rough=0.85 + 0.06 * fib, ao=np.ones((h, w)), no_albedo=True)


def paper_white():
    r = rng('paper_white')
    h = w = S
    fib = _fine(h, w, r, 0.8)
    img = np.broadcast_to(srgb('#e6e2d6'), (h, w, 3)) * (0.97 + 0.03 * fib)[..., None]
    img = age(img, r, yellow=0.06, fade=0.0, grime=0.03, cells=2)
    return dict(albedo=img, rough=np.zeros((h, w)), px=(1, 1), no_orm=True)


def paper_yellowed():
    r = rng('paper_yellowed')
    h = w = S
    fib = _fine(h, w, r, 0.8)
    img = np.broadcast_to(srgb('#d9c99a'), (h, w, 3)) * (0.96 + 0.04 * fib)[..., None]
    img = lerp(img, srgb('#c4a668'), smoothstep(0.4, 0.9, norm01(fbm(h, w, 3, 3, r, 4))) * 0.5)
    # foxing: small rusty spots
    for _ in range(60):
        x, y = r.uniform(0, w), r.uniform(0, h)
        rad = r.uniform(1.0, 5.0)
        iy, ix, DX, DY = draw.patch(h, w, x, y, rad * 2 + 2)
        d = np.sqrt(DX ** 2 + DY ** 2)
        a = np.exp(-(d / rad) ** 2) * r.uniform(0.2, 0.6)
        draw.composite(img, iy, ix, a, srgb('#9a6a38'))
    return dict(albedo=img, rough=np.zeros((h, w)), px=(1, 1), no_orm=True)


def cardboard():
    r = rng('cardboard')
    h = w = S
    T = 300.0
    px = T / w
    flute_mm = 8.0                                 # C-flute pitch shows through the liner
    y = (np.arange(h) + 0.5) * px
    n = round(T / flute_mm)
    fl = 0.5 + 0.5 * np.cos(2 * math.pi * (np.arange(h) + 0.5) / h * n)
    FL = np.broadcast_to(fl[:, None], (h, w))
    fib = _fine(h, w, r, 0.8) * 0.6 + 0.4 * _fine(h, w, r, 2.0)
    blot = norm01(fbm(h, w, 4, 4, r, 4))
    img = colorize(np.clip(0.5 + 0.15 * fib + 0.2 * (blot - 0.5), 0, 1),
                   [(0, '#8a6a42'), (0.5, '#a8885a'), (1, '#c0a072')])
    img = img * (0.96 + 0.04 * FL)[..., None]
    # water marks / scuffs
    img = age(img, r, yellow=0.0, fade=0.1, grime=0.1, cells=2)
    hmm = 0.18 * FL + 0.02 * fib
    return dict(albedo=img, height=hmm, px=(px, px), rough=0.9 + 0.05 * fib, ao=0.92 + 0.08 * FL)


def book_cloth():
    """Buckram book cloth: shared normal/ORM; albedo is neutral and tinted per book."""
    r = rng('bookcloth')
    h = w = S
    T = 100.0
    px = T / w
    ht, _, _ = draw.weave(h, w, 220, 200, draw.PLAIN, r, fuzz=0.2)
    wear = smoothstep(0.55, 0.9, norm01(fbm(h, w, 3, 3, r, 4)))
    img = np.ones((h, w, 3)) * (0.86 + 0.1 * ht)[..., None]
    img = lerp(img, srgb('#c8bca4') * 1.25, wear * 0.25)          # rubbed, faded cloth
    img = img * (1 + 0.04 * fbm(h, w, 8, 8, r, 3))[..., None]
    return dict(albedo=np.clip(img, 0, 1), height=0.05 * ht, px=(px, px), rough=0.8 + 0.1 * ht - 0.15 * wear,
                ao=0.85 + 0.15 * ht)


def plant_green():
    """Dense houseplant foliage (pothos / philodendron) for primitive plant shapes."""
    r = rng('plant')
    h = w = S
    T = 300.0
    px = T / w
    zbuf = np.full((h, w), -10.0)
    img = np.zeros((h, w, 3)) + srgb('#0e160a')
    hmm = np.zeros((h, w)) - 10.0
    rough = np.full((h, w), 0.9)
    greens = [srgb(c) for c in ('#3f6a2a', '#4f7a32', '#2f5420', '#5e8a3a', '#6a7e2e')]
    n = 260
    zs = np.sort(r.uniform(0, 10, n))
    for i in range(n):
        x, y = r.uniform(0, w), r.uniform(0, h)
        a = r.uniform(0, 2 * math.pi)
        L, W = r.uniform(45, 80), r.uniform(18, 30)
        iy, ix, DX, DY = draw.patch(h, w, x, y, L + 3)
        RX, RY = draw.rot(DX, DY, a)
        d = draw.sd_leaf(RX, RY, L, W)
        inside = d < 0
        if not inside.any():
            continue
        t = np.clip(RX / L, 0, 1)
        tilt = r.uniform(-0.3, 0.3)
        z = zs[i] + tilt * (t - 0.5) * 6 - 2.0 * (RY / W) ** 2 + 0.6 * np.exp(-(RY / 1.5) ** 2)
        zsub = zbuf[np.ix_(iy, ix)]
        m = inside & (z > zsub)
        zbuf[np.ix_(iy, ix)] = np.where(m, z, zsub)
        c = greens[r.integers(0, len(greens))] * r.uniform(0.85, 1.15)
        vein = np.exp(-(RY / 1.2) ** 2) * 0.3
        variegate = smoothstep(0.7, 0.9, norm01(np.sin(RX * 0.2 + RY * 0.35 + r.uniform(0, 6))))
        col = c[None, None, :] * (0.8 + 0.3 * t)[..., None] + vein[..., None] * srgb('#a8b870')
        col = lerp(col, srgb('#b8c070'), variegate * 0.25)
        sub = img[np.ix_(iy, ix)]
        img[np.ix_(iy, ix)] = np.where(m[..., None], col, sub)
        rs = rough[np.ix_(iy, ix)]
        rough[np.ix_(iy, ix)] = np.where(m, 0.45 + 0.1 * r.uniform(), rs)
    hmm = np.where(zbuf < -5, -2, zbuf) * 2.0
    hmm = blur(hmm, 0.8)
    ao = cavity_ao(hmm, 10, 6.0, 1.2)
    img = age(np.clip(img, 0, 1), r, yellow=0.06, fade=0.08, grime=0.15, cells=2)
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# window_blown_out : overexposed exterior seen through a window (emissive)
# ---------------------------------------------------------------------------

def window_blown_out():
    r = rng('blown_out')
    h = w = S
    # world tile 4 m wide x 4.88 m tall, anchored to y = 0 (bottom = ground)
    yh = (1.0 - (np.arange(h) + 0.5) / h) * 4.88
    sky = colorize(np.clip((yh - 0.5) / 4.0, 0, 1), [(0, '#f4f2e8'), (0.6, '#eef2f2'), (1, '#dde8ef')])
    img = np.broadcast_to(sky[:, None, :], (h, w, 3)).copy()
    # soft blown-out hedge / lawn / tree masses
    tree = norm01(fbm(h, w, 6, 10, r, 5))
    horizon = 1.4 + 1.0 * norm01(fbm(1, w, 1, 8, r, 3))[0]
    mass = smoothstep(-0.25, 0.25, horizon[None, :] - yh[:, None] + 0.9 * (tree - 0.5))
    mass = blur(mass, 6)
    green = colorize(tree, [(0, '#a4ae84'), (1, '#c8cca4')])
    img = lerp(img, green, mass * 0.6)
    lawn = 1 - smoothstep(0.2, 0.7, yh)
    img = lerp(img, srgb('#c8d0a0'), lawn[:, None] * 0.5)
    return dict(albedo=img, height=None, px=(1, 1), rough=np.ones((h, w)), no_orm=True)


REGISTRY = {
    'wood_furniture': wood_furniture,
    'wood_dark': wood_dark,
    'wood_medium': wood_medium,
    'wood_light': wood_light,
    'wood_oak_cabinet': wood_oak_cabinet,
    'laminate_formica': laminate_formica,
    'plastic': plastic_texture,
    'plastic_beige': plastic_beige,
    'metal_brass': metal_brass,
    'metal_chrome': metal_chrome,
    'metal_dark': metal_dark,
    'enamel': enamel,
    'fabric_floral_sofa': fabric_floral_sofa,
    'fabric_corduroy_brown': fabric_corduroy_brown,
    'fabric_plaid': fabric_plaid,
    'fabric_lampshade': fabric_lampshade,
    'fabric_curtain_heavy': fabric_curtain_heavy,
    'fabric_curtain_sheer': fabric_curtain_sheer,
    'dust_sheet': dust_sheet,
    'leather_brown': leather_brown,
    'rubber_black': rubber_black,
    'glass_dusty': glass_dusty,
    'ceramic_white': ceramic_white,
    'paper': paper_texture,
    'paper_white': paper_white,
    'paper_yellowed': paper_yellowed,
    'cardboard': cardboard,
    'book_cloth': book_cloth,
    'plant_green': plant_green,
    'window_blown_out': window_blown_out,
}
