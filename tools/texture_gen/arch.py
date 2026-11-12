"""Architectural surfaces (world-space triplanar, large tiles, 1024 px)."""
from __future__ import annotations

import math

import numpy as np

from . import draw
from .core import (age, blur, cavity_ao, colorize, fbm, lerp, luminance, norm01, rng,
                   saturate, smoothstep, spectral, srgb, vnoise, white, worley, downsample)
from .wood import fibre_streaks, log_rings, pores, ring_profile, sheet_grain, warp_field

N = 1024


def _rows_height_m(h: int, tile_h_m: float) -> np.ndarray:
    """World height (m) of each image row for a wall tile anchored at y = 0.

    Godot world triplanar maps v = -y * scale, so the bottom row of the image
    sits just above y = 0 and the top row just below y = tile_h_m."""
    return (1.0 - (np.arange(h) + 0.5) / h) * tile_h_m


# ---------------------------------------------------------------------------
# wall_wood_paneling : 4 x 8 ft random-groove walnut-look plywood
# ---------------------------------------------------------------------------

def wall_wood_paneling():
    r = rng('paneling')
    h, w = N, N
    W_MM, H_MM = 1220.0, 2440.0
    pxx, pxy = W_MM / w, H_MM / h
    xmm = (np.arange(w) + 0.5) * pxx
    # irregular "random groove" layout; one wider groove at the sheet joint (x = 0)
    spacings = [152, 102, 203, 127, 152, 102, 178, 204]
    scale = W_MM / sum(spacings)
    pos = np.cumsum([0] + [s * scale for s in spacings[:-1]])
    widths = [9.0] + list(r.uniform(4.5, 7.0, size=len(pos) - 1))
    groove = np.zeros(w)
    plank = np.zeros(w, dtype=int)
    for k, (p, gw) in enumerate(zip(pos, widths)):
        d = np.abs(((xmm - p + W_MM / 2) % W_MM) - W_MM / 2)
        prof = 1 - smoothstep(gw * 0.5 - 0.6, gw * 0.5 + 0.6, d)
        groove = np.maximum(groove, prof)
        plank = np.where(xmm >= p, k, plank)
    G = np.broadcast_to(groove[None, :], (h, w))
    P = np.broadcast_to(plank[None, :], (h, w))
    nplank = len(pos)

    # grain: each simulated board is sliced from its own virtual log
    phase, ring, _ = sheet_grain(h, w, r, W_MM, H_MM, ring_mm=6.5, boards=plank)
    tone = r.uniform(-1, 1, nplank)
    streak = fibre_streaks(h, w, r, 260, 6)
    figure = fbm(h, w, 6, 40, r, 4)
    t = 0.45 + 0.18 * tone[P] + 0.12 * figure + 0.08 * streak
    t = t - 0.2 * ring
    alb = colorize(np.clip(t, 0, 1), [(0.0, '#150b05'), (0.25, '#26150b'), (0.5, '#3c2312'),
                                      (0.72, '#55341c'), (1.0, '#6e4a2e')])
    # dark "pecky" figure streaks typical of printed walnut panelling
    peck = smoothstep(0.62, 0.85, norm01(fbm(h, w, 5, 90, r, 3)))
    alb = alb * (1 - 0.35 * peck[..., None])
    # grooves painted near-black brown
    alb = lerp(alb, srgb('#140b06'), G * 0.92)

    # height (mm): grooves 1.6 mm deep, embossed grain ~0.06 mm
    hmm = -1.6 * G + 0.06 * ring + 0.02 * streak
    # wear anchored to world height (tile is exactly one 8 ft sheet tall)
    yh = _rows_height_m(h, 2.44)[:, None]
    low = (1 - smoothstep(0.05, 0.35, yh)) * smoothstep(0.0, 0.04, yh)   # kick/scuff zone
    hand = np.exp(-((yh - 1.05) / 0.25) ** 2)        # hand height smudges
    lf = norm01(fbm(h, w, 2, 3, r, 3))
    scuff = smoothstep(0.6, 0.9, norm01(fbm(h, w, 90, 8, r, 3))) * low
    alb = lerp(alb, srgb('#7a6450'), scuff * 0.12 * (1 - G))
    # sun fade: lifted, slightly greyed, low frequency
    fade = smoothstep(0.45, 0.9, lf) * 0.18
    alb = lerp(alb, saturate(alb, 0.6) * 1.25, fade)
    alb = age(alb, r, yellow=0.05, fade=0.04, grime=0.1, cells=2)

    rough = 0.42 + 0.06 * figure + 0.1 * ring * 0 + 0.35 * G
    rough = rough + 0.15 * scuff - 0.06 * hand * lf + 0.06 * fade
    ao = cavity_ao(hmm, 6, 1.4, 1.0)
    ao = np.minimum(ao, 1 - 0.55 * G)
    return dict(albedo=alb, height=hmm, px=(pxx, pxy), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# floor_hardwood : 2-1/4" red oak strip flooring, worn finish
# ---------------------------------------------------------------------------

def _strip_floor(seed: str, dusty: bool = False):
    r = rng('hardwood')
    h, w = N, N
    T_MM = 1200.0
    nstrip = 21
    px = T_MM / w
    sw = T_MM / nstrip
    xmm = (np.arange(w) + 0.5) * px
    ymm = (np.arange(h) + 0.5) * px
    col = np.floor(xmm / sw).astype(int)
    xl = xmm - col * sw                         # mm across within the strip
    # board joints per strip column (periodic in y)
    board = np.zeros((h, w), dtype=int)
    yl = np.zeros((h, w))
    blen = np.zeros((h, w))
    joint_d = np.full((h, w), 1e9)
    nb_total = 0
    for c in range(nstrip):
        k = r.integers(1, 4)
        cuts = np.sort(r.uniform(0, T_MM, size=k))
        # make sure boards are not absurdly short
        if k > 1:
            gaps = np.diff(np.r_[cuts, cuts[0] + T_MM])
            if gaps.min() < 220:
                cuts = cuts[:1]
        cs = np.r_[cuts, cuts[0] + T_MM]
        m = col == c
        yy = ymm[:, None] * np.ones((1, m.sum()))
        idx = np.zeros_like(yy, dtype=int)
        loc = np.zeros_like(yy)
        ln = np.zeros_like(yy)
        jd = np.full_like(yy, 1e9)
        yw = (yy - cuts[0]) % T_MM
        rel = np.r_[0, np.cumsum(np.diff(cs))]
        for b in range(len(cuts)):
            inb = (yw >= rel[b]) & (yw < rel[b + 1])
            idx[inb] = nb_total + b
            loc[inb] = yw[inb] - rel[b]
            ln[inb] = rel[b + 1] - rel[b]
        for cu in cuts:
            d = np.abs(((yy - cu + T_MM / 2) % T_MM) - T_MM / 2)
            jd = np.minimum(jd, d)
        board[:, m] = idx
        yl[:, m] = loc
        blen[:, m] = ln
        joint_d[:, m] = jd
        nb_total += len(cuts)
    XL = np.broadcast_to(xl[None, :], (h, w))
    side_d = np.minimum(XL, sw - XL)

    # per-board parameters
    tone = r.normal(0, 1, nb_total)
    redness = r.uniform(-1, 1, nb_total)
    ring_mm = r.uniform(3.5, 7.0, nb_total)
    cath = r.uniform(0, 1, nb_total) ** 2
    off = r.uniform(0, 1500, nb_total)
    yc = r.uniform(0.2, 0.8, nb_total)
    B = board
    # grain phase: lines run along the board, with cathedral arches
    uc = r.uniform(-1.0, 2.0, nb_total) * sw
    depth = r.uniform(8.0, 60.0, nb_total)
    taper = r.uniform(0.005, 0.03, nb_total) * r.choice([-1, 1], nb_total)
    wf = warp_field(h, w, r, 3, 40, 1.5) + warp_field(h, w, r, 10, 120, 0.3)
    phase = log_rings(XL, yl, uc[B], depth[B], taper[B], ring_mm[B], wf) + off[B]
    ring = blur(ring_profile(phase, 0.3), 0.7)
    por = pores(h, w, r, 300, 40, 0.66) * (0.3 + 0.7 * ring)
    streak = fibre_streaks(h, w, r, 300, 8)
    t = 0.6 + 0.13 * tone[B] + 0.05 * streak - 0.3 * ring - 0.12 * por * (0.4 + ring)
    lo = lerp(srgb('#4a3322'), srgb('#553526'), (redness[B] * 0.5 + 0.5))
    hi = lerp(srgb('#a58c6c'), srgb('#a58066'), (redness[B] * 0.5 + 0.5))
    t3 = np.clip(t, 0, 1)[..., None]
    alb = lo * (1 - t3) + hi * t3
    # amber finish, aged
    alb = alb * srgb('#f2dcb0')
    # seams
    seam = np.maximum(1 - smoothstep(0.25, 0.9, side_d), 1 - smoothstep(0.2, 0.8, joint_d))
    bevel = np.maximum(1 - smoothstep(0.0, 1.6, side_d), 1 - smoothstep(0.0, 1.2, joint_d))
    alb = lerp(alb, srgb('#1e130b'), seam * 0.85)
    # wear: traffic path (low freq), finish worn through -> greyer, lighter, rougher
    wear = smoothstep(0.5, 0.85, norm01(fbm(h, w, 2, 2, r, 3)))
    scr = np.zeros((h, w))
    for _ in range(70):
        x0, y0 = r.uniform(0, w), r.uniform(0, h)
        ang = r.normal(0.0, 0.35) + (math.pi / 2 if r.uniform() < 0.7 else 0)
        L = r.uniform(10, 50)
        iy, ix, DX, DY = draw.patch(h, w, x0, y0, L / 2 + 2)
        d, _ = draw.sd_segment(DX, DY, -math.cos(ang) * L / 2, -math.sin(ang) * L / 2,
                               math.cos(ang) * L / 2, math.sin(ang) * L / 2)
        draw.maxinto(scr, iy, ix, (1 - smoothstep(0.1, 0.7, d)) * r.uniform(0.2, 0.7))
    alb = lerp(alb, saturate(alb, 0.55) * 1.18, wear * 0.4)
    alb = lerp(alb, srgb('#c8b08a'), scr * 0.12)
    alb = age(alb, r, yellow=0.04, fade=0.08, grime=0.12, cells=3)
    hmm = 0.05 * (1 - ring) - 0.04 * por - 0.7 * bevel - 0.4 * seam + 0.15 * fbm(h, w, 3, 3, r, 2)
    rough = 0.32 + 0.05 * streak + 0.3 * wear + 0.25 * scr + 0.45 * seam + 0.1 * por
    if dusty:
        dust = norm01(fbm(h, w, 6, 6, r, 5))
        dust = 0.55 + 0.45 * smoothstep(0.2, 0.9, dust)
        dust = np.maximum(dust, seam * 0.9)
        fluff = smoothstep(0.75, 0.95, norm01(white(h, w, r)))
        alb = lerp(alb, srgb('#9c9282'), np.clip(dust * 0.42 + fluff * 0.05, 0, 1))
        rough = np.clip(rough, 0, 1) * (1 - dust * 0.6) + dust * 0.6 * 0.88
    ao = np.minimum(cavity_ao(hmm, 4, 0.6), 1 - 0.5 * seam)
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=ao)


def floor_hardwood():
    return _strip_floor('hardwood')


def floor_hardwood_dusty():
    return _strip_floor('hardwood', dusty=True)


# ---------------------------------------------------------------------------
# carpets
# ---------------------------------------------------------------------------

def _shag_like(seed, tile_mm, palette, n_tufts, length_mm, rad_mm, lean_bias, trample_amt,
               plies=2, pile_mm=25.0, tip_light=1.15, base_dark=0.45, size=N,
               segs=1, curl=0.0, bg=0.25):
    r = rng(seed)
    h = w = size
    px = tile_mm / w
    zbuf = np.full((h, w), -1.0)
    rgb = np.zeros((h, w, 3)) + srgb(palette[0][1]) * bg
    # low-frequency fields: trampling, flow direction
    tr = norm01(fbm(h, w, 2, 2, r, 3))
    tr = smoothstep(0.45, 0.85, tr) * trample_amt
    flow = fbm(h, w, 3, 3, r, 2) * math.pi
    pal_w = np.array([p[0] for p in palette], dtype=float)
    pal_w /= pal_w.sum()
    pal_c = np.array([srgb(p[1]) for p in palette])
    xs = r.uniform(0, w, n_tufts)
    ys = r.uniform(0, h, n_tufts)
    iy = ys.astype(int) % h
    ix = xs.astype(int) % w
    trs = tr[iy, ix]
    flw = flow[iy, ix]
    # elevation of each tuft: upright (shows as a dot) .. lying flat (long stroke)
    lean = np.clip(lean_bias + 0.35 * r.standard_normal(n_tufts) + 0.6 * trs, 0.05, 1.0)
    L = length_mm * r.uniform(0.7, 1.3, n_tufts)
    Lp = L * np.sqrt(lean) / px                         # projected length (px)
    ang = np.where(r.uniform(size=n_tufts) < 0.4 + 0.5 * trs, flw + r.normal(0, 0.5, n_tufts),
                   r.uniform(0, 2 * math.pi, n_tufts))
    cidx = r.choice(len(pal_c), size=n_tufts, p=pal_w)
    col = pal_c[cidx] * r.uniform(0.85, 1.12, (n_tufts, 1))
    # sun-faded / soiled tips in trampled areas
    col = col * (1 - 0.18 * trs[:, None]) + srgb('#6d5a40') * 0.18 * trs[:, None]
    zb = pile_mm * (1 - lean) * r.uniform(0.6, 1.0, n_tufts) * (1 - 0.5 * trs)
    zt = zb + L * np.sqrt(1 - lean ** 2) * 0.35 + 2.0
    order = np.argsort(zt)
    strands = dict(x=[], y=[], ang=[], length=[], rad=[], z0=[], z1=[], col=[], s0=[], s1=[], zr=[])
    for i in order:
        for p in range(plies):
            dxy = r.normal(0, rad_mm * 0.6 / px, 2)
            x0, y0 = xs[i] + dxy[0], ys[i] + dxy[1]
            a = ang[i] + r.normal(0, 0.2)
            c = r.normal(0, curl)                      # curvature per segment (rad)
            seg_len = max(1.0, Lp[i] * r.uniform(0.8, 1.05)) / segs
            rad = max(0.9, rad_mm / px * r.uniform(0.6, 0.85))
            z1 = zt[i] * r.uniform(0.9, 1.05)
            cc = col[i] * r.uniform(0.93, 1.07)
            for sgi in range(segs):
                t0, t1 = sgi / segs, (sgi + 1) / segs
                strands['x'].append(x0)
                strands['y'].append(y0)
                strands['ang'].append(a)
                strands['length'].append(seg_len)
                # frayed, thinner tips
                strands['rad'].append(rad * (1 - 0.35 * t0))
                strands['z0'].append(zb[i] + (z1 - zb[i]) * t0)
                strands['z1'].append(zb[i] + (z1 - zb[i]) * t1)
                strands['col'].append(cc)
                strands['s0'].append(base_dark + (tip_light - base_dark) * t0)
                strands['s1'].append(base_dark + (tip_light - base_dark) * t1)
                strands['zr'].append(px * 0.8)
                x0 += math.cos(a) * seg_len
                y0 += math.sin(a) * seg_len
                a += c
    for k in strands:
        strands[k] = np.array(strands[k])
    draw.render_strands(h, w, strands, zbuf, rgb)
    zbuf = np.where(zbuf < 0, 0, zbuf)
    return rgb, zbuf, tr, px, r


def carpet_shag_gold():
    pal = [(4, '#c08a34'), (3, '#a86e26'), (2, '#d29c48'), (1.4, '#8a5620'), (0.8, '#6a4018'),
           (0.6, '#ddb060'), (0.5, '#b4742e')]
    rgb, z, tr, px, r = _shag_like('shag', 750.0, pal, n_tufts=8000, length_mm=42, rad_mm=4.2,
                                   lean_bias=0.6, trample_amt=0.6, plies=2, pile_mm=30,
                                   segs=3, curl=0.3, tip_light=1.12, base_dark=0.5)
    h, w = z.shape
    rgb = age(np.clip(rgb, 0, 1), r, yellow=0.03, fade=0.12, grime=0.18, cells=2)
    hmm = blur(z, 0.9)
    rough = 0.93 - 0.08 * tr
    ao = cavity_ao(hmm, 5, 9.0, 1.3) * (0.55 + 0.45 * norm01(blur(z, 2)))
    return dict(albedo=rgb, height=hmm, px=(px, px), rough=rough, ao=ao)


def carpet_beige():
    pal = [(4, '#a8977a'), (3, '#b8a687'), (2, '#9a886c'), (1, '#c4b394'), (0.6, '#8a7a60')]
    rgb, z, tr, px, r = _shag_like('beige', 500.0, pal, n_tufts=34000, length_mm=8, rad_mm=1.3,
                                   lean_bias=0.15, trample_amt=0.5, plies=2, pile_mm=10,
                                   tip_light=1.05, base_dark=0.7, bg=0.6, segs=2, curl=0.4)
    h, w = z.shape
    # faint pile shading (cut pile brushed in different directions shows as light/dark patches)
    shade = fbm(h, w, 3, 3, r, 3)
    rgb = rgb * (1 + 0.06 * shade[..., None])
    rgb = age(np.clip(rgb, 0, 1), r, yellow=0.05, fade=0.05, grime=0.2, cells=2)
    rough = 0.95 - 0.05 * tr
    ao = cavity_ao(z, 3, 3.0, 1.1)
    return dict(albedo=rgb, height=z, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# linoleum_kitchen : 1970s sheet vinyl, 12" star-and-medallion repeat
# ---------------------------------------------------------------------------

def linoleum_kitchen():
    r = rng('linoleum')
    SS = 2
    h = w = N * SS
    T_MM = 610.0                       # 2 x 2 repeats of a 305 mm (12") motif
    px = T_MM / N
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    u = (xx + 0.5) / w * 2.0
    v = (yy + 0.5) / h * 2.0
    lx = (u - np.floor(u)) - 0.5       # local motif coords -0.5..0.5
    ly = (v - np.floor(v)) - 0.5
    cell_px = w / 2.0
    ax, ay = np.abs(lx), np.abs(ly)
    # SDFs in motif units
    sq = np.maximum(ax, ay)
    dia = (ax + ay) / math.sqrt(2)
    star = np.minimum(sq - 0.27, dia - 0.27)                        # 8-pointed star
    octa = np.maximum(sq, dia) - 0.16                               # inner octagon
    circ = np.sqrt(lx * lx + ly * ly)
    quat = np.min(np.stack([np.sqrt((lx - ox) ** 2 + (ly - oy) ** 2) for ox, oy in
                            ((0.07, 0), (-0.07, 0), (0, 0.07), (0, -0.07))]), 0) - 0.055
    # corner diamonds (centred on the motif corners)
    cx_, cy_ = 0.5 - ax, 0.5 - ay
    cdia = (cx_ + cy_) - 0.16
    cdot = np.sqrt(cx_ ** 2 + cy_ ** 2) - 0.035
    # edge band
    band = np.abs(sq - 0.5)
    pp = 1.0 / cell_px                       # one pixel in motif units
    def cov(d, aa=1.0):
        return np.clip(0.5 - d / (2 * aa * pp), 0, 1)
    cream = srgb('#d8c79c')
    cream2 = srgb('#c9b07a')
    gold = srgb('#b98a34')
    ochre = srgb('#a8742a')
    brown = srgb('#5e3a1c')
    rust = srgb('#8e4a22')
    # mottled vinyl "chips" texture inside fills
    mott = norm01(fbm(h, w, 24, 24, r, 4))
    chips = smoothstep(0.62, 0.7, norm01(vnoise(h, w, 180, 180, r, cubic=False)))
    base = lerp(cream, cream2, mott * 0.6)
    img = base.copy()
    # thin brown border lines along the motif edge
    img = lerp(img, brown, cov(band - 0.012))
    inset = np.abs(sq - 0.43)
    img = lerp(img, ochre, cov(inset - 0.006) * (1 - cov(star + 0.02)) * (1 - cov(cdia + 0.02)))
    mids = np.min(np.stack([np.sqrt((ax - 0.43) ** 2 + ly ** 2), np.sqrt(lx ** 2 + (ay - 0.43) ** 2)]), 0)
    img = lerp(img, rust, cov(mids - 0.018))
    img = lerp(img, lerp(ochre, gold, mott), cov(star))
    img = lerp(img, brown, cov(np.abs(star) - 0.006))               # star outline
    img = lerp(img, lerp(cream, cream2, mott), cov(octa))
    img = lerp(img, brown, cov(np.abs(octa) - 0.005))
    img = lerp(img, rust, cov(quat))
    img = lerp(img, gold, cov(circ - 0.025))
    img = lerp(img, lerp(brown, rust, mott * 0.5), cov(cdia))
    img = lerp(img, cream, cov(cdot))
    img = lerp(img, img * 0.85 + 0.15 * srgb('#f4ead0'), chips * 0.5)
    img = downsample(img, SS)
    # emboss: the printed lines are slightly debossed, plus fine pebble grain
    lines = (cov(np.abs(star) - 0.006) + cov(np.abs(octa) - 0.005) + cov(band - 0.012)
             + cov(np.abs(cdia) - 0.005))
    lines = downsample(np.clip(lines, 0, 1), SS)
    h, w = N, N
    pebble = blur(white(h, w, r), 1.2)
    pebble = pebble / (np.abs(pebble).max() + 1e-9)
    hmm = -0.12 * lines + 0.025 * pebble
    # wear: traffic dulls the gloss and fades the print, grime collects in lines
    wear = smoothstep(0.5, 0.9, norm01(fbm(h, w, 2, 2, r, 3)))
    img = lerp(img, saturate(img, 0.6) * 1.05, wear * 0.35)
    img = lerp(img, img * srgb('#7a6a50'), lines * 0.35)
    img = age(img, r, yellow=0.12, fade=0.06, grime=0.15, cells=3)
    scuff = smoothstep(0.7, 0.9, norm01(fbm(h, w, 30, 30, r, 3))) * (0.3 + 0.7 * wear)
    img = lerp(img, img * 0.82, scuff * 0.4)
    rough = 0.22 + 0.06 * norm01(pebble) + 0.28 * wear + 0.2 * scuff + 0.15 * lines
    ao = 1 - 0.25 * lines
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# tile_bathroom : 4-1/4" glazed ceramic, pale seafoam, dingy grout
# ---------------------------------------------------------------------------

def tile_bathroom():
    r = rng('bathtile')
    h = w = N
    n = 8
    T_MM = 108.0 * n
    px = T_MM / w
    xmm = (np.arange(w) + 0.5) * px
    ymm = (np.arange(h) + 0.5) * px
    lx = xmm % 108.0
    ly = ymm % 108.0
    ix = (xmm // 108.0).astype(int)
    iy = (ymm // 108.0).astype(int)
    LX = np.broadcast_to(lx[None, :], (h, w))
    LY = np.broadcast_to(ly[:, None], (h, w))
    ID = iy[:, None] * n + ix[None, :]
    g = 1.6                                 # grout half-width-ish (mm)
    ed = np.minimum(np.minimum(LX, 108 - LX), np.minimum(LY, 108 - LY))
    grout = 1 - smoothstep(g * 0.5, g, ed)
    cushion = smoothstep(g * 0.5, g + 4.0, ed)       # rounded pillow edge
    tone = r.normal(0, 1, n * n)
    base = srgb('#c9d6c8')
    tile = base * (1 + 0.025 * tone[ID])[..., None]
    mott = fbm(h, w, 16, 16, r, 4)
    tile = tile * (1 + 0.02 * mott[..., None])
    gcol = lerp(srgb('#a9a393'), srgb('#7d7666'), norm01(fbm(h, w, 12, 12, r, 3)))
    alb = lerp(tile, gcol, grout)
    alb = age(alb, r, yellow=0.08, fade=0.0, grime=0.1, cells=3)
    wav = fbm(h, w, 8, 8, r, 3)
    hmm = 0.9 * cushion ** 0.5 - 0.5 * grout + 0.03 * wav
    gloss_var = norm01(fbm(h, w, 6, 6, r, 3))
    rough = 0.07 + 0.06 * gloss_var + 0.85 * grout
    ao = 1 - 0.4 * grout
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# ceiling_popcorn : sprayed acoustic ceiling
# ---------------------------------------------------------------------------

def _popcorn_height(r, h, w, k=1.0):
    """Lumpy sprayed texture from layered periodic Worley domes (mm).
    ``k`` scales the lattice counts for larger tiles at the same pixel count."""
    f1a, _, _ = worley(h, w, int(120 * k), int(120 * k), r)
    f1c, _, _ = worley(h, w, int(55 * k), int(55 * k), r)
    big = np.clip(1 - f1c * 1.4, 0, 1) ** 0.8
    a = np.clip(1 - f1a * 1.25, 0, 1) ** 0.7
    sz = norm01(fbm(h, w, 6, 6, r, 3))
    hmm = 1.6 * a * (0.6 + 0.6 * sz) + 1.2 * big * sz
    if k <= 1.5:
        f1b, _, _ = worley(h, w, int(260 * k), int(260 * k), r)
        b = np.clip(1 - f1b * 1.2, 0, 1) ** 0.7
        hmm = hmm + 0.7 * b
    return hmm + 0.03 * blur(white(h, w, r), 0.6)


def ceiling_popcorn():
    r = rng('popcorn')
    h = w = N
    T_MM = 600.0
    px = T_MM / w
    hmm = _popcorn_height(r, h, w)
    ao = cavity_ao(hmm, 3, 0.9, 1.3)
    t = norm01(hmm)
    alb = colorize(t, [(0, '#b9b19c'), (0.5, '#d9d2bf'), (1, '#e7e2d3')])
    # glittery vermiculite flecks were common; keep them as tiny bright specks
    glit = smoothstep(0.985, 1.0, norm01(white(h, w, r)))
    alb = lerp(alb, srgb('#f6f2e6'), glit * 0.6)
    alb = age(alb, r, yellow=0.22, fade=0.0, grime=0.08, cells=2)
    rough = 0.96 - 0.25 * glit
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=ao)


def ceiling_popcorn_stained():
    """Popcorn ceiling with one old roof-leak stain per 2.4 m tile (stain centred
    in the tile, clean edges, so a tile-aligned patch shows one stain)."""
    r = rng('popcorn_big')
    h = w = N
    T_MM = 2400.0
    px = T_MM / w
    hmm = _popcorn_height(r, h, w, k=2.0)
    r2 = rng('popstain')
    ao = cavity_ao(hmm, 2, 0.9, 1.3)
    t = norm01(hmm)
    alb = colorize(t, [(0, '#b9b19c'), (0.5, '#d9d2bf'), (1, '#e7e2d3')])
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5) / w - 0.5
    v = (yy + 0.5) / h - 0.52
    wob = fbm(h, w, 4, 4, r2, 4)
    d = np.sqrt((u * 1.15) ** 2 + v ** 2) + 0.07 * wob     # warped radius
    stain = 1 - smoothstep(0.12, 0.3, d)
    tide = np.zeros_like(d)
    for lvl, k in ((0.3, 1.0), (0.24, 0.7), (0.17, 0.5)):
        tide = np.maximum(tide, k * np.exp(-((d - lvl) / 0.006) ** 2))
    mott = norm01(fbm(h, w, 16, 16, r2, 4))
    alb = lerp(alb, alb * srgb('#d2b07c'), stain * (0.35 + 0.25 * mott))
    tide = blur(tide, 1.2)
    alb = lerp(alb, alb * srgb('#9a7448'), tide * 0.4)
    alb = age(alb, r2, yellow=0.22, fade=0.0, grime=0.08, cells=2)
    rough = np.full((h, w), 0.96)
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# wall_plaster_cream : painted drywall, roller stipple, nicotine
# ---------------------------------------------------------------------------

def wall_plaster_cream():
    r = rng('plaster')
    h = w = N
    W_MM, H_MM = 1220.0, 2440.0             # anchored to wall height
    pxx, pxy = W_MM / w, H_MM / h
    stip = blur(white(h, w, r), 1.3, 0.65)
    stip = stip / (np.abs(stip).max() + 1e-9)
    stip2 = blur(white(h, w, r), 3.0, 1.5)
    stip2 = stip2 / (np.abs(stip2).max() + 1e-9)
    waves = fbm(h, w, 3, 6, r, 3)
    hmm = 0.05 * stip + 0.07 * stip2 + 0.25 * waves
    base = srgb('#d8ceb4')
    alb = np.broadcast_to(base, (h, w, 3)).copy()
    alb = alb * (1 + 0.015 * stip2[..., None])
    yh = _rows_height_m(h, 2.44)[:, None]
    # nicotine heavier near the ceiling, scuffs/dirty band near the floor, hand smudges
    # ramps return to zero right at y = 0 / 2.44 so stacked storeys do not seam
    top = smoothstep(1.6, 2.3, yh) * (1 - smoothstep(2.3, 2.44, yh))
    low = (1 - smoothstep(0.03, 0.4, yh)) * smoothstep(0.0, 0.03, yh)
    hand = np.exp(-((yh - 1.1) / 0.3) ** 2)
    lf = norm01(fbm(h, w, 2, 3, r, 3))
    alb = alb * (1 - (0.06 + 0.1 * top * lf)[..., None]) + alb * srgb('#d8b878') * (0.06 + 0.1 * top * lf)[..., None]
    sc = smoothstep(0.55, 0.9, norm01(fbm(h, w, 60, 6, r, 3))) * low
    alb = lerp(alb, alb * srgb('#9d8f7a'), sc * 0.25)
    sm = smoothstep(0.55, 0.85, norm01(fbm(h, w, 14, 10, r, 3))) * hand
    alb = lerp(alb, alb * srgb('#c8bca2'), sm * 0.12)
    alb = age(alb, r, yellow=0.12, fade=0.06, grime=0.03, cells=2)
    rough = 0.82 + 0.06 * stip2 - 0.12 * sm + 0.05 * sc
    ao = cavity_ao(hmm, 2, 0.1, 1.0)
    return dict(albedo=alb, height=hmm, px=(pxx, pxy), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# wallpaper
# ---------------------------------------------------------------------------

def _paper_height(r, h, w):
    f = blur(white(h, w, r), 1.0)
    f = f / (np.abs(f).max() + 1e-9)
    lf = fbm(h, w, 4, 4, r, 3)
    return 0.012 * f + 0.06 * lf


def wallpaper_floral():
    r = rng('floral')
    SS = 2
    N2 = N * SS
    h = w = N2
    T_MM = 533.0                       # one 21" roll width, two half-dropped repeats
    pxp = T_MM / N2
    ground = srgb('#e9dfc6')
    img = np.broadcast_to(ground, (h, w, 3)).copy()
    # faint vertical "moire" stripe printed in the ground
    xx = (np.arange(w) + 0.5) / w
    moire = 0.5 + 0.5 * np.sin(xx * 2 * math.pi * 48)
    img = img * (1 - 0.025 * moire[None, :, None])
    rose = [srgb('#b86a6a'), srgb('#c98884'), srgb('#9e4f55')]
    leafc = [srgb('#7b8a5c'), srgb('#93a070'), srgb('#5f6e46')]
    blue = srgb('#7f8fae')
    cream = srgb('#f1e7cf')
    hgt = np.zeros((h, w))
    # lattice of sprigs: 2 columns x 3 rows per repeat, half-drop between columns
    cols, rows = 4, 6
    cw, ch = w / cols, h / rows
    sprigs = []
    for c in range(cols):
        for k in range(rows):
            x = (c + 0.5) * cw + r.normal(0, cw * 0.05)
            y = (k + 0.5 + 0.5 * (c % 2)) * ch + r.normal(0, ch * 0.05)
            sprigs.append((x, y, r.uniform(0, 2 * math.pi), r.integers(0, 3)))
    # scattered tiny filler motifs (dots, forget-me-nots)
    for _ in range(70):
        x, y = r.uniform(0, w), r.uniform(0, h)
        rad = r.uniform(4, 6.5) * SS * 1.6
        iy, ix, DX, DY = draw.patch(h, w, x, y, rad * 2)
        for p in range(5):
            a = p * 2 * math.pi / 5
            d = np.sqrt((DX - math.cos(a) * rad * 0.7) ** 2 + (DY - math.sin(a) * rad * 0.7) ** 2) - rad * 0.5
            draw.composite(img, iy, ix, draw.cover(d, SS * 0.7) * 0.9, blue)
        d = np.sqrt(DX ** 2 + DY ** 2) - rad * 0.3
        draw.composite(img, iy, ix, draw.cover(d, SS * 0.7), srgb('#e8c96a'))
    pxs = SS * 2.3  # draw sizes: design units -> supersampled pixels
    for (x, y, a0, kind) in sprigs:
        # stem: a gentle curve of capsules
        L = r.uniform(55, 75) * pxs
        pts = []
        for i in range(9):
            t = i / 8
            ang = a0 + 0.6 * math.sin(t * 2.5)
            pts.append((x + math.cos(ang) * (t - 0.5) * L, y + math.sin(ang) * (t - 0.5) * L))
        for (ax_, ay_), (bx_, by_) in zip(pts[:-1], pts[1:]):
            cx_, cy_ = (ax_ + bx_) / 2, (ay_ + by_) / 2
            iy, ix, DX, DY = draw.patch(h, w, cx_, cy_, L / 8 + 6)
            d, _ = draw.sd_segment(DX, DY, ax_ - cx_, ay_ - cy_, bx_ - cx_, by_ - cy_)
            draw.composite(img, iy, ix, draw.cover(d - 1.2 * pxs, SS * 0.7), leafc[2])
        # leaves along the stem
        for i in (1, 3, 5, 7):
            px_, py_ = pts[i]
            side = 1 if i % 4 == 1 else -1
            ang = a0 + side * r.uniform(0.7, 1.2)
            ll, lw = r.uniform(16, 24) * pxs, r.uniform(5, 7) * pxs
            iy, ix, DX, DY = draw.patch(h, w, px_, py_, ll + 4)
            RX, RY = draw.rot(DX, DY, ang)
            d = draw.sd_leaf(RX, RY, ll, lw)
            lc = leafc[r.integers(0, 2)]
            draw.composite(img, iy, ix, draw.cover(d, SS * 0.7), lc)
            vein = np.abs(RY) - 0.5 * pxs
            draw.composite(img, iy, ix, draw.cover(np.maximum(vein, d + 1.5 * pxs), SS * 0.7) * 0.6, leafc[2])
        # blooms: cabbage-rose clusters made of layered petals
        for bi, (bx, by) in enumerate([pts[-1], pts[0]] if kind == 0 else [pts[-1]]):
            R = r.uniform(11, 15) * pxs * (0.75 if bi else 1.0)
            iy, ix, DX, DY = draw.patch(h, w, bx, by, R * 1.5)
            pc = rose[r.integers(0, 3)]
            for ring_i, (rr, npet) in enumerate(((1.0, 7), (0.72, 6), (0.45, 5))):
                for p in range(npet):
                    a = p * 2 * math.pi / npet + ring_i * 0.4 + r.uniform(-0.2, 0.2)
                    ex, ey = draw.rot(DX - math.cos(a) * R * rr * 0.45, DY - math.sin(a) * R * rr * 0.45, a)
                    d = draw.sd_ellipse(ex, ey, R * rr * 0.48, R * rr * 0.36)
                    shade = 0.8 + 0.25 * ring_i
                    draw.composite(img, iy, ix, draw.cover(d, SS * 0.7), np.clip(pc * shade, 0, 1))
                    draw.composite(img, iy, ix, draw.cover(np.abs(d) - 0.5 * pxs, SS * 0.7) * 0.5, pc * 0.6)
            d = np.sqrt(DX ** 2 + DY ** 2) - R * 0.14
            draw.composite(img, iy, ix, draw.cover(d, SS * 0.7), pc * 0.55)
            hgt[np.ix_(iy, ix)] = np.maximum(hgt[np.ix_(iy, ix)], draw.cover(np.sqrt(DX ** 2 + DY ** 2) - R, SS))
        # small buds
        for i in (2, 6):
            bx, by = pts[i]
            ang = a0 + (1.6 if i == 2 else -1.6)
            bx += math.cos(ang) * 14 * pxs
            by += math.sin(ang) * 14 * pxs
            iy, ix, DX, DY = draw.patch(h, w, bx, by, 10 * pxs)
            RX, RY = draw.rot(DX, DY, ang)
            d = draw.sd_ellipse(RX, RY, 5.5 * pxs, 4 * pxs)
            draw.composite(img, iy, ix, draw.cover(d, SS * 0.7), rose[2])
            d2 = draw.sd_leaf(RX + 6 * pxs, RY, 9 * pxs, 3 * pxs)
            draw.composite(img, iy, ix, draw.cover(d2, SS * 0.7), leafc[0])
    img = downsample(img, SS)
    hgt = downsample(hgt, SS)
    h = w = N
    px = T_MM / N
    # print slightly off-register softness; paper texture; fade and yellow
    img = img * 0.6 + 0.4 * np.stack([blur(img[..., c], 0.8) for c in range(3)], -1)
    ph = _paper_height(r, h, w)
    # roll seam at the tile edge (x = 0): faint lifted, darkened line
    xs = (np.arange(w) + 0.5) * px
    sd = np.minimum(xs, T_MM - xs)
    seam = np.broadcast_to((1 - smoothstep(0.0, 0.8, sd))[None, :], (h, w))
    img = lerp(img, img * 0.8, seam * 0.6)
    img = age(img, r, yellow=0.14, fade=0.18, grime=0.05, cells=2)
    hmm = ph + 0.02 * hgt + 0.08 * seam
    rough = 0.82 - 0.06 * hgt
    ao = 1 - 0.15 * seam
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


def wallpaper_stripe():
    r = rng('stripe')
    h = w = N
    T_MM = 533.0
    px = T_MM / w
    xmm = (np.arange(w) + 0.5) * px
    # 1980s pastel regency stripe: dusty rose / cream / sage with pinstripes
    seq = [('#e9dcc0', 38), ('#d8b4ac', 30), ('#e9dcc0', 6), ('#a9b49a', 4), ('#e9dcc0', 6),
           ('#d8b4ac', 30), ('#e9dcc0', 38), ('#b9c4c4', 18), ('#e9dcc0', 4), ('#c7a07a', 2),
           ('#e9dcc0', 4), ('#b9c4c4', 18)]
    total = sum(s[1] for s in seq)
    scale = (T_MM / 2) / total
    edges = np.cumsum([0] + [s[1] * scale for s in seq])
    xm = xmm % (T_MM / 2)
    row = np.zeros((w, 3))
    for (c, _), a, b in zip(seq, edges[:-1], edges[1:]):
        cov = smoothstep(a - 0.3, a + 0.3, xm) * (1 - smoothstep(b - 0.3, b + 0.3, xm))
        row += cov[:, None] * srgb(c)
    img = np.broadcast_to(row[None, :, :], (h, w, 3)).copy()
    # damask-ish satin sheen stripe: the cream bands are printed with a pearly glaze
    sheen = np.broadcast_to(np.isclose(row, srgb('#e9dcc0'), atol=0.02).all(-1)[None, :], (h, w)).astype(float)
    sheen = blur(sheen, 0.5)
    ph = _paper_height(r, h, w)
    sd = np.minimum(xmm, T_MM - xmm)
    seam = np.broadcast_to((1 - smoothstep(0.0, 0.8, sd))[None, :], (h, w))
    img = img * (1 + 0.02 * fbm(h, w, 40, 40, r, 2)[..., None])
    img = lerp(img, img * 0.8, seam * 0.6)
    img = age(img, r, yellow=0.2, fade=0.2, grime=0.05, cells=2)
    hmm = ph + 0.08 * seam
    rough = 0.85 - 0.25 * sheen
    ao = 1 - 0.15 * seam
    return dict(albedo=img, height=hmm, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# brick_red : common brick, running bond (fireplace, exterior)
# ---------------------------------------------------------------------------

def brick_red():
    r = rng('brick')
    h = w = N
    BW, BH, M = 203.0, 57.0, 10.0
    nx, ny = 4, 12
    W_MM, H_MM = nx * (BW + M), ny * (BH + M)
    pxx, pxy = W_MM / w, H_MM / h
    xmm = (np.arange(w) + 0.5) * pxx
    ymm = (np.arange(h) + 0.5) * pxy
    X = np.broadcast_to(xmm[None, :], (h, w))
    Y = np.broadcast_to(ymm[:, None], (h, w))
    course = (Y // (BH + M)).astype(int)
    xo = X + (course % 2) * (BW + M) / 2
    bi = (xo // (BW + M)).astype(int) % nx
    lx = xo % (BW + M)
    ly = Y % (BH + M)
    ID = course * nx + bi
    # mortar distance (wobbly brick edges)
    wob = fbm(h, w, 40, 20, r, 3) * 1.6
    ex = np.minimum(lx - M / 2, BW + M / 2 - lx) + wob
    ey = np.minimum(ly - M / 2, BH + M / 2 - ly) + wob * 0.7
    e = np.minimum(ex, ey)
    brick = smoothstep(-0.5, 1.5, e)
    tone = r.normal(0, 1, nx * ny)
    dark = (r.uniform(size=nx * ny) < 0.12).astype(float)
    rough_f = fbm(h, w, 60, 30, r, 4)
    pits = smoothstep(0.72, 0.85, norm01(vnoise(h, w, 160, 120, r)))
    t = 0.5 + 0.12 * tone[ID] + 0.1 * rough_f
    bc = colorize(np.clip(t, 0, 1), [(0, '#5a2418'), (0.5, '#8a3c26'), (1, '#b0583a')])
    bc = lerp(bc, srgb('#3c1d16'), dark[ID] * 0.55)
    bc = lerp(bc, bc * 0.6, pits * 0.6)
    # flashing: darker ends of some bricks
    fl = smoothstep(0.6, 1.0, np.abs((lx - (BW + M) / 2) / ((BW + M) / 2))) * (tone[ID] > 0.5)
    bc = lerp(bc, bc * 0.7, fl * 0.5)
    mort = lerp(srgb('#9b9284'), srgb('#7e766a'), norm01(fbm(h, w, 30, 30, r, 3)))
    alb = lerp(mort, bc, brick)
    alb = age(alb, r, yellow=0.05, fade=0.08, grime=0.2, cells=2)
    hmm = 6.0 * smoothstep(-1.0, 3.0, e) + 0.8 * rough_f - 0.6 * pits * brick + 0.2 * white(h, w, r) * (1 - brick)
    rough = 0.82 + 0.1 * (1 - brick) + 0.04 * rough_f
    ao = np.minimum(cavity_ao(hmm, 6, 4.0, 1.0), 0.55 + 0.45 * brick)
    return dict(albedo=alb, height=hmm, px=(pxx, pxy), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# trim_white : yellowed oil-based gloss enamel
# ---------------------------------------------------------------------------

def trim_white():
    r = rng('trim')
    h = w = 512
    T_MM = 500.0
    px = T_MM / w
    peel = blur(white(h, w, r), 2.2)
    peel = peel / (np.abs(peel).max() + 1e-9)
    brush = vnoise(h, w, 60, 3, r) * 0.6 + 0.4 * vnoise(h, w, 140, 6, r)
    hmm = 0.03 * peel + 0.025 * brush
    alb = np.broadcast_to(srgb('#e0dacb'), (h, w, 3)).copy()
    alb = alb * (1 + 0.012 * brush[..., None])
    alb = age(alb, r, yellow=0.16, fade=0.0, grime=0.03, cells=2)
    chips = smoothstep(0.93, 0.95, norm01(fbm(h, w, 30, 30, r, 3)))
    alb = lerp(alb, srgb('#8c7a62'), chips * 0.5)
    rough = 0.28 + 0.05 * norm01(peel) + 0.3 * chips + 0.08 * norm01(fbm(h, w, 4, 4, r, 3))
    ao = np.ones((h, w))
    return dict(albedo=alb, height=hmm - 0.05 * chips, px=(px, px), rough=rough, ao=ao)


# ---------------------------------------------------------------------------
# concrete : garage / basement slab, also usable for grout bands and steps
# ---------------------------------------------------------------------------

def concrete():
    r = rng('concrete')
    h = w = N
    T_MM = 1500.0
    px = T_MM / w
    agg = spectral(h, w, r, beta=1.6, fmin=2)
    f1, _, cid = worley(h, w, 140, 140, r)
    stones = smoothstep(0.5, 0.25, f1) * (r.uniform(size=140 * 140)[cid] > 0.7)
    pores_ = smoothstep(0.9, 0.97, norm01(white(h, w, r))) * 0.0 + smoothstep(0.78, 0.86, norm01(vnoise(h, w, 400, 400, r, cubic=False)))
    lf = norm01(fbm(h, w, 3, 3, r, 4))
    alb = colorize(np.clip(0.5 + 0.25 * agg + 0.2 * (lf - 0.5), 0, 1),
                   [(0, '#6c675e'), (0.5, '#8f897d'), (1, '#aaa394')])
    alb = lerp(alb, srgb('#7a7468'), stones * 0.25)
    alb = lerp(alb, alb * 0.55, pores_ * 0.7)
    oil = smoothstep(0.7, 0.9, norm01(fbm(h, w, 2, 2, r, 4)))
    alb = lerp(alb, alb * srgb('#5c564c'), oil * 0.25)
    alb = age(alb, r, yellow=0.04, fade=0.0, grime=0.15, cells=2)
    hmm = 0.4 * agg + 0.3 * stones - 0.5 * pores_
    rough = 0.85 + 0.08 * norm01(agg) - 0.25 * oil
    ao = cavity_ao(hmm, 3, 0.4)
    return dict(albedo=alb, height=hmm, px=(px, px), rough=rough, ao=ao)


REGISTRY = {
    'wall_wood_paneling': wall_wood_paneling,
    'floor_hardwood': floor_hardwood,
    'floor_hardwood_dusty': floor_hardwood_dusty,
    'carpet_shag_gold': carpet_shag_gold,
    'carpet_beige': carpet_beige,
    'linoleum_kitchen': linoleum_kitchen,
    'tile_bathroom': tile_bathroom,
    'ceiling_popcorn': ceiling_popcorn,
    'ceiling_popcorn_stained': ceiling_popcorn_stained,
    'wall_plaster_cream': wall_plaster_cream,
    'wallpaper_floral': wallpaper_floral,
    'wallpaper_stripe': wallpaper_stripe,
    'brick_red': brick_red,
    'trim_white': trim_white,
    'concrete': concrete,
}
