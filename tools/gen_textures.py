#!/usr/bin/env python3
"""Procedural texture + material generator for the house palette.

    python3 tools/gen_textures.py                 # all texture sets + all materials
    python3 tools/gen_textures.py --only carpet_shag_gold,linoleum_kitchen
    python3 tools/gen_textures.py --materials-only    # rewrite art/materials/*.tres only
    python3 tools/gen_textures.py --preview       # also write lit 3x3 tiled previews to _shots/tex/
    python3 tools/gen_textures.py --check         # verify tileability of the PNGs on disk

Then: godot --headless --audio-driver Dummy --path . --import

Deterministic: every set uses its own named seed, so regenerating one set never
changes another. Output per set (art/textures/<set>/):
    <set>_albedo.png   sRGB colour (RGBA if the set has alpha)
    <set>_normal.png   tangent-space normal, OpenGL convention (green = +Y up)
    <set>_orm.png      R = ambient occlusion, G = roughness, B = metallic
Every PNG gets a hand-written .import (VRAM compressed, mipmaps, normal-map
flag for normals) unless one exists already; existing uids are preserved.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from texture_gen import arch, props  # noqa: E402
from texture_gen.core import (blur, height_to_normal, normal_to_rgb, save_png,  # noqa: E402
                              tile_seam_ratio, to8)
from texture_gen import materials  # noqa: E402

TEX_DIR = os.path.join(ROOT, 'art', 'textures')
SHOT_DIR = os.path.join(ROOT, '_shots', 'tex')

REGISTRY = {}
REGISTRY.update(arch.REGISTRY)
REGISTRY.update(props.REGISTRY)

# Sets that reuse another set's normal map (same height field)
SHARED_NORMAL = materials.SHARED_NORMAL

IMPORT_TMPL = """[remap]

importer="texture"
type="CompressedTexture2D"
{uid}path.s3tc="res://.godot/imported/{fname}-{h}.s3tc.ctex"
metadata={{
"imported_formats": ["s3tc_bptc"],
"vram_texture": true
}}

[deps]

source_file="res://{rel}"

[params]

compress/mode=2
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map={normal}
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


def write_import(png_path: str, is_normal: bool) -> None:
    """Write a .import that asks Godot for VRAM-compressed, mipmapped textures.

    Godot fills in the uid/dest hashes on the next --import. If a .import is
    already there we only make sure the params we care about are set."""
    imp = png_path + '.import'
    rel = os.path.relpath(png_path, ROOT).replace(os.sep, '/')
    if os.path.exists(imp):
        txt = open(imp).read()
        want = {'compress/mode': '2', 'mipmaps/generate': 'true', 'detect_3d/compress_to': '0',
                'compress/normal_map': '1' if is_normal else '0'}
        changed = False
        for k, v in want.items():
            pat = re.compile(r'^' + re.escape(k) + r'=.*$', re.M)
            if pat.search(txt):
                new = pat.sub(f'{k}={v}', txt)
            else:
                new = txt.rstrip('\n') + f'\n{k}={v}\n'
            if new != txt:
                txt, changed = new, True
        if changed:
            open(imp, 'w').write(txt)
        return
    # minimal file; Godot completes it
    txt = IMPORT_TMPL.format(uid='', fname=os.path.basename(png_path), h='0', rel=rel,
                             normal='1' if is_normal else '0')
    # drop the speculative remap paths: Godot regenerates them
    txt = re.sub(r'path\.s3tc=.*\n', '', txt)
    txt = re.sub(r'metadata=\{[^}]*\}\n', '', txt)
    open(imp, 'w').write(txt)


def build_set(name: str, preview: bool) -> dict:
    t0 = time.time()
    d = REGISTRY[name]()
    out = os.path.join(TEX_DIR, name)
    os.makedirs(out, exist_ok=True)
    written = []
    alb = np.clip(d['albedo'], 0, 1)
    if d.get('alpha') is not None:
        alb = np.concatenate([alb, np.clip(d['alpha'], 0, 1)[..., None]], -1)
    if not d.get('no_albedo'):
        p = os.path.join(out, f'{name}_albedo.png')
        save_png(p, alb)
        written.append((p, False))
    n = None
    if d.get('height') is not None and name not in SHARED_NORMAL:
        pxx, pxy = d['px']
        n = height_to_normal(d['height'], pxx, pxy, d.get('nstrength', 1.0))
        p = os.path.join(out, f'{name}_normal.png')
        save_png(p, normal_to_rgb(n))
        written.append((p, True))
    if not d.get('no_orm'):
        h, w = d['rough'].shape
        ao = d.get('ao')
        ao = np.ones((h, w)) if ao is None else ao
        met = d.get('metal')
        met = np.zeros((h, w)) if met is None else met
        orm = np.stack([np.clip(ao, 0, 1), np.clip(d['rough'], 0, 1), np.clip(met, 0, 1)], -1)
        p = os.path.join(out, f'{name}_orm.png')
        save_png(p, orm)
        written.append((p, False))
    for p, isn in written:
        write_import(p, isn)
    if preview:
        write_preview(name, d, n)
    sizes = sum(os.path.getsize(p) for p, _ in written) / 1e6
    print(f'  {name:28s} {alb.shape[1]}x{alb.shape[0]}  {len(written)} files  {sizes:5.1f} MB  {time.time() - t0:5.1f}s')
    return d


def write_preview(name: str, d: dict, n) -> None:
    """Lit 3x3 tiled preview with a low raking light from the upper left, so
    seams, repetition and normal response can be judged without Godot."""
    from PIL import Image
    alb = np.clip(d['albedo'], 0, 1)
    h, w = alb.shape[:2]
    if n is None:
        if d.get('height') is not None:
            n = height_to_normal(d['height'], *d['px'])
        else:
            n = np.zeros((h, w, 3)); n[..., 2] = 1
    L = np.array([-0.75, 0.35, 0.45]); L /= np.linalg.norm(L)
    ndl = np.clip((n * L).sum(-1), 0, 1)
    ao = d.get('ao') if d.get('ao') is not None else np.ones((h, w))
    rough = np.clip(d['rough'], 0.03, 1)
    H = L + np.array([0, 0, 1.0]); H /= np.linalg.norm(H)
    ndh = np.clip((n * H).sum(-1), 0, 1)
    spec = (1 - rough) ** 3 * ndh ** (2 / rough ** 2 + 2) * 0.6
    lin = alb ** 2.2
    lit = lin * (ndl * 2.2 + 0.25 * ao)[..., None] + spec[..., None]
    img = np.clip(lit, 0, 1) ** (1 / 2.2)
    tiled = np.tile(img, (3, 3, 1))
    im = Image.fromarray(to8(tiled))
    side = 1200
    im = im.resize((side, int(side * tiled.shape[0] / tiled.shape[1])), Image.LANCZOS)
    os.makedirs(SHOT_DIR, exist_ok=True)
    im.save(os.path.join(SHOT_DIR, f'{name}.png'))
    # also a 1:1 crop of a single tile corner region (detail)
    crop = Image.fromarray(to8(np.tile(img, (2, 2, 1))[h // 2:h // 2 + min(h, 600), w // 2:w // 2 + min(w, 600)]))
    crop.save(os.path.join(SHOT_DIR, f'{name}_crop.png'))


# Seams that are part of the design, not wrap errors
SEAM_ALLOWED = {
    'window_blown_out': 'anchored to world height (sky above, lawn below); only tiles horizontally',
    'wallpaper_floral': 'roll seam drawn at the tile edge (one roll width per tile)',
    'wallpaper_stripe': 'roll seam drawn at the tile edge (one roll width per tile)',
    'wall_wood_paneling': 'sheet joint groove at the tile edge (one 4x8 sheet per tile)',
}


def check_all() -> bool:
    from PIL import Image
    ok = True
    total = 0
    count = 0
    for root, _, files in os.walk(TEX_DIR):
        for f in sorted(files):
            if not f.endswith('.png'):
                continue
            p = os.path.join(root, f)
            total += os.path.getsize(p)
            count += 1
            a = np.asarray(Image.open(p)).astype(np.float64)
            ratio = tile_seam_ratio(a[..., :3] if a.ndim == 3 else a)
            setname = os.path.basename(root)
            if ratio <= 1.25:
                flag = 'OK '
            elif setname in SEAM_ALLOWED:
                flag = 'ok*'
            else:
                flag, ok = 'BAD', False
            note = f'  ({SEAM_ALLOWED[setname]})' if flag == 'ok*' else ''
            print(f'  {flag} seam/max-interior = {ratio:5.2f}  {os.path.relpath(p, ROOT)}{note}')
    print(f'{count} textures, {total / 1e6:.1f} MB')
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--materials-only', action='store_true')
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check_all() else 1)
    if not a.materials_only:
        names = [s for s in a.only.split(',') if s] or list(REGISTRY)
        for nm in names:
            if nm not in REGISTRY:
                sys.exit(f'unknown set {nm}; known: {", ".join(REGISTRY)}')
        print(f'generating {len(names)} texture sets')
        for nm in names:
            build_set(nm, a.preview)
    if not a.only:
        materials.write_all(ROOT)


if __name__ == '__main__':
    main()
