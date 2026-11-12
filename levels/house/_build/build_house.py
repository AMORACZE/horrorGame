#!/usr/bin/env python3
"""Builds levels/house/house.tscn: 1418 Wren Hollow Rd, ground floor slice.

    python3 levels/house/_build/build_house.py
    godot --headless --audio-driver Dummy --path . --import

GENERATED OUTPUT: house.tscn is overwritten every time this runs. Do not edit
the scene by hand or in the editor; change the data below and rebuild.

Conventions: 1 unit = 1 m, -Z north, +X east, +Y up. Interior floor at y = 0,
ceiling 2.44. The house sits on a 0.40 m foundation above the lawn.

Plan (interior faces, metres):

    x: 0                        6.0 6.15                         10.35
 z 0  +--[FRONT]--+==CLOSET==+--[BEDRM]--+   basement   | pantry |   (mass)
      | HALL  (wood)                  [BASEMENT]                   |
 1.5  +-----===== OPENING =====--phone--+---------+--[PANTRY]--+-----+
 1.65 |W                     shelf boxes|          fridge             |
      |W  sofa    rug/coffee      TV   [OPEN]                         [BACK]
      |W                                |  dinette    sink run        |
 6.25 +------[win]------[win]-----------+---[win]--------[win]--------+

Everything is plain MeshInstance3D + StaticBody3D. Walls are split around each
fixture's wall cut and built as two half-thickness skins so each room gets its
own finish. Real mass above the ceiling, under the floor and around the shell
keeps sunlight and GI out of places it should not reach.
"""
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tscn import *  # noqa: E402,F403

OUT = "levels/house/house.tscn"
# HOUSE_DEBUG_FLAT=1: write a flat-lit inspection copy (no GI, strong ambient)
# to _shots/debug_house.tscn instead, for checking geometry in screenshots.
DEBUG_FLAT = os.environ.get("HOUSE_DEBUG_FLAT") == "1"
F = "res://fixtures/"
P = "res://props/"
A = "res://audio/"
I = "res://interaction/"
LOOK = I + "interactable.gd"
ATMOS_RIG = "res://atmosphere/afternoon_atmosphere.tscn"
DUST_SCENE = "res://atmosphere/dust_motes.tscn"
HAZE_SCENE = "res://atmosphere/haze_volume.tscn"

H = 2.44            # ceiling
EXT = 0.30          # exterior wall
INT = 0.15          # interior wall
GRADE = -0.40       # lawn level
SKIN_BOT, SKIN_TOP = -0.05, H + 0.05

# Openings in walls: (centre along the wall, width, y0, y1). Sizes = each
# fixture's required wall cut (see fixtures/tools/build_fixture_scenes.py).
CUT_FRONT = (0.954, 0.0, 2.075)
CUT_DOOR = (0.854, 0.0, 2.064)
CUT_CLOSET = (1.558, 0.0, 2.064)
CUT_WIN_W = 0.90
CUT_WIN_H = 1.39
SILL = 0.76
SILL_SINK = 0.95
CASED_HEAD = 2.10

# Rooms: interior rectangles (x0, x1, z0, z1) and finishes.
ROOMS = {
    "Hall": dict(rect=(0.0, 6.0, 0.0, 1.5), floor="floor_hardwood", surface="wood", reverb=4,  # HALLWAY
                 base_mat="trim_white"),
    "Living": dict(rect=(0.0, 6.0, 1.65, 6.25), floor="carpet_shag_gold", surface="carpet", reverb=0,  # LIVING_ROOM
                   base_mat="wood_medium"),
    "Kitchen": dict(rect=(6.15, 10.35, 1.65, 6.25), floor="linoleum_kitchen", surface="linoleum", reverb=2,  # KITCHEN
                    base_mat="trim_white"),
}

# Window and door positions (world).
FRONT_DOOR_X = 1.0
CLOSET_X = 3.05
BEDROOM_DOOR_X = 5.1
BASEMENT_DOOR_Z = 0.6
PANTRY_DOOR_X = 8.3
BACK_DOOR_Z = 3.4
HALL_OPEN = (0.75, 2.75)            # x range, hall -> living
KITCHEN_OPEN = (2.6, 4.0)           # z range, living -> kitchen
WEST_WINDOWS_Z = [3.43, 4.40, 5.37]  # three-window picture group, 0.07 mullions
SOUTH_LIVING_X = [1.6, 4.4]
DINETTE_WINDOW_X = 6.75
SINK_X = 8.975

# Sun used until the atmosphere rig exists (WSW, ~37 degrees up).
SUN_AZIMUTH_TRAVEL = 62.0   # compass degrees the light travels toward (ENE-ish)
SUN_ELEVATION = 37.0

FLOOR_MATS = {}


# =============================================================================
# Helpers
# =============================================================================

def lp(origin, rot_y, local):
    """Local point -> world for a frame at origin rotated rot_y degrees about +Y."""
    t = math.radians(rot_y)
    c, s = math.cos(t), math.sin(t)
    x, y, z = local
    return (origin[0] + c * x + s * z, origin[1] + y, origin[2] - s * x + c * z)


# --- Rim workaround -----------------------------------------------------------
# Several palette fabrics (art/materials) enable `rim` with roughness 1. In
# Godot's shader the rim term is added per light WITHOUT shadow attenuation, and
# at roughness 1 its falloff exponent is 0, so it becomes a flat, unshadowed
# glow from the sun on every face: carpets and sofas blow out and a jacket in
# the dark hall glows. Until the palette changes, this level uses copies of
# those materials with the rim lines removed (levels/house/materials/*_norim.tres,
# regenerated from art/materials on every build) on its own geometry and as
# per-instance overrides on props and fixtures.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
NORIM_DIR = "levels/house/materials"
RIM_MATS = {}  # "res://art/materials/x.tres" -> "res://levels/house/materials/x_norim.tres"


def make_norim_materials():
    os.makedirs(os.path.join(ROOT, NORIM_DIR), exist_ok=True)
    adir = os.path.join(ROOT, "art", "materials")
    for fn in sorted(os.listdir(adir)):
        if not fn.endswith(".tres"):
            continue
        with open(os.path.join(adir, fn)) as f:
            text = f.read()
        if "rim_enabled = true" not in text:
            continue
        out = []
        for line in text.splitlines():
            if line.startswith("rim"):
                continue
            if line.startswith("[gd_resource"):
                line = re.sub(r' uid="[^"]*"', "", line)
            out.append(line)
        name = fn[:-5] + "_norim.tres"
        with open(os.path.join(ROOT, NORIM_DIR, name), "w") as f:
            f.write("\n".join(out) + "\n")
        RIM_MATS["res://art/materials/" + fn] = "res://%s/%s" % (NORIM_DIR, name)


_orig_mat = Scene.mat


def _mat_norim(self, name):
    if name.startswith("res://"):
        path = name
    elif name.startswith("fx:"):
        path = None
    else:
        path = "res://art/materials/%s.tres" % name
    if path in RIM_MATS:
        return self.ext(RIM_MATS[path], "Material")
    return _orig_mat(self, name)


Scene.mat = _mat_norim

_scan_cache = {}


def rim_overrides(scene_path):
    """[(node path inside the scene or '.', property, replacement)] for every
    property in the scene that points at a rim material."""
    if scene_path in _scan_cache:
        return _scan_cache[scene_path]
    out = []
    ids = {}
    node = None
    with open(os.path.join(ROOT, scene_path.replace("res://", ""))) as f:
        for line in f:
            line = line.strip()
            m = re.match(r'\[ext_resource type="Material" path="([^"]+)" id="([^"]+)"\]', line)
            if m:
                if m.group(1) in RIM_MATS:
                    ids[m.group(2)] = RIM_MATS[m.group(1)]
                continue
            m = re.match(r'\[node name="([^"]+)"(?: type="[^"]+")?(?: parent="([^"]+)")?', line)
            if m:
                nm, par = m.group(1), m.group(2)
                node = "." if par is None else (nm if par == "." else par + "/" + nm)
                continue
            m = re.match(r'([\w/]+) = ExtResource\("([^"]+)"\)', line)
            if m and node is not None and m.group(2) in ids:
                out.append((node, m.group(1), ids[m.group(2)]))
    _scan_cache[scene_path] = out
    return out


def inst(sc, parent, name, path, pos, rot_y=0.0, props=None, rot=None):
    p = {"transform": XF(pos, rot if rot is not None else (0, rot_y, 0))}
    over = rim_overrides(path)
    for node, prop, rep in over:
        if node == ".":
            p[prop] = sc.ext(rep, "Material")
    if props:
        p.update(props)
    ipath = sc.node(name, None, parent, p, instance=sc.ext(path, "PackedScene"))
    for node, prop, rep in over:
        if node != ".":
            nm = node.rsplit("/", 1)[-1]
            par = ipath + ("/" + node.rsplit("/", 1)[0] if "/" in node else "")
            sc.nodes.append(('[node name="%s" parent="%s"]' % (nm, par), {prop: sc.ext(rep, "Material")}))
    return ipath


def look(sc, body, display, lines, prompt=None):
    props = {"script": sc.ext(LOOK, "Script"), "display_name": display, "observations": STRS(lines)}
    if prompt:
        props["prompt"] = prompt
    sc.node("Interactable", "Node", body, props)


def thing(sc, parent, name, pos, rot_y, parts, display, lines, layer=SOLID_INTERACT, collide=True):
    """A built object that answers: parts = [(kind, size/dims, local pos, material[, rot])]."""
    b = static_body(sc, parent, name, layer, pos=pos, rot=(0, rot_y, 0))
    for i, part in enumerate(parts):
        kind, dims, p, mat = part[:4]
        r = part[4] if len(part) > 4 else (0, 0, 0)
        if kind == "box":
            box(sc, b, "P%d" % i, dims, p, mat, rot=r)
            if collide:
                col_box(sc, b, "C%d" % i, dims, p, r)
        elif kind == "cyl":
            rt, rb, h = dims
            cyl(sc, b, "P%d" % i, rt, rb, h, p, mat, rot=r, segs=16)
            if collide:
                col_cyl(sc, b, "C%d" % i, max(rt, rb), h, p, r)
        elif kind == "sph":
            sphere(sc, b, "P%d" % i, dims, None, p, mat, segs=12, rings=6)
            if collide:
                col_sphere(sc, b, "C%d" % i, dims, p)
    look(sc, b, display, lines)
    return b


def split_segments(a0, a1, openings, y_bot, y_top):
    segs = []
    cur = a0
    for cx, w, y0, y1 in sorted(openings):
        a, b = cx - w / 2, cx + w / 2
        if a > cur + 1e-6:
            segs.append((cur, a, y_bot, y_top))
        if y0 > 1e-6:
            segs.append((a, b, y_bot, y0))
        if y1 < y_top - 1e-6:
            segs.append((a, b, y1, y_top))
        cur = b
    if cur < a1 - 1e-6:
        segs.append((cur, a1, y_bot, y_top))
    return segs


def wall(sc, parent, name, axis, a0, a1, c, thick, openings, mat_neg, mat_pos,
         y_bot=SKIN_BOT, y_top=SKIN_TOP):
    """A wall along `axis` ('x' or 'z') from a0 to a1, centred on c (the other
    horizontal coordinate). mat_neg skins the -Z (or -X) half, mat_pos the other."""
    body = static_body(sc, parent, name, LAYER_WORLD)
    for i, (a, b, y0, y1) in enumerate(split_segments(a0, a1, openings, y_bot, y_top)):
        L, hgt, ym, am = b - a, y1 - y0, (y0 + y1) / 2, (a + b) / 2
        if axis == "x":
            col_box(sc, body, "S%d" % i, (L, hgt, thick), (am, ym, c))
        else:
            col_box(sc, body, "S%d" % i, (thick, hgt, L), (c, ym, am))
        halves = [(mat_neg, -1), (mat_pos, 1)] if mat_neg != mat_pos else [(mat_neg, 0)]
        for mat, sgn in halves:
            t = thick / 2 if sgn else thick
            off = sgn * thick / 4
            tag = {-1: "N", 1: "P", 0: ""}[sgn]
            if axis == "x":
                box(sc, body, "M%d%s" % (i, tag), (L, hgt, t), (am, ym, c + off), mat)
            else:
                box(sc, body, "M%d%s" % (i, tag), (t, hgt, L), (c + off, ym, am), mat)
    return body


def cased_opening(sc, parent, name, axis, a0, a1, c, thick, head=CASED_HEAD, mat="trim_white"):
    """Jamb liners and casings on both faces of a plain cased opening."""
    body = static_body(sc, parent, name, LAYER_WORLD)
    jt, cw, ct = 0.019, 0.064, 0.016
    w = a1 - a0
    parts = [
        ((jt, head, thick + 0.004), (a0 + jt / 2, head / 2, 0)),
        ((jt, head, thick + 0.004), (a1 - jt / 2, head / 2, 0)),
        ((w, jt, thick + 0.004), ((a0 + a1) / 2, head - jt / 2, 0)),
    ]
    for f in (-1, 1):
        z = f * (thick / 2 + ct / 2)
        hh = head + cw
        parts += [
            ((cw, hh, ct), (a0 - cw / 2 + 0.004, hh / 2, z)),
            ((cw, hh, ct), (a1 + cw / 2 - 0.004, hh / 2, z)),
            ((w + 2 * cw - 0.008, cw, ct), ((a0 + a1) / 2, head + cw / 2, z)),
        ]
    for i, (size, (u, y, v)) in enumerate(parts):
        if axis == "x":
            box(sc, body, "T%d" % i, size, (u, y, c + v), mat)
        else:
            box(sc, body, "T%d" % i, (size[2], size[1], size[0]), (c + v, y, u), mat)
    # Only the jamb liners collide (casings are flush trim).
    for i, (size, (u, y, v)) in enumerate(parts[:2]):
        if axis == "x":
            col_box(sc, body, "J%d" % i, size, (u, y, c + v))
        else:
            col_box(sc, body, "J%d" % i, (size[2], size[1], size[0]), (c + v, y, u))
    return body


def baseboard_run(sc, parent, name, axis, a0, a1, face, inward, gaps, mat, h=0.09, t=0.014):
    """Baseboard along a wall face (face = plane coordinate, inward = +1/-1 into the room)."""
    cur = a0
    runs = []
    for g0, g1 in sorted(gaps):
        if g0 > cur:
            runs.append((cur, min(g0, a1)))
        cur = max(cur, g1)
    if cur < a1:
        runs.append((cur, a1))
    for i, (a, b) in enumerate(runs):
        if b - a < 0.02:
            continue
        if axis == "x":
            box(sc, parent, "%s%d" % (name, i), (b - a, h, t), ((a + b) / 2, h / 2, face + inward * t / 2), mat)
        else:
            box(sc, parent, "%s%d" % (name, i), (t, h, b - a), (face + inward * t / 2, h / 2, (a + b) / 2), mat)


def gap(centre, width, casing=0.075):
    return (centre - width / 2 - casing, centre + width / 2 + casing)


def floor_slab(sc, parent, name, rect, mat, surface, y0=-0.30):
    x0, x1, z0, z1 = rect
    b = static_body(sc, parent, name, LAYER_WORLD)
    sc.nodes[-1][1]["metadata/surface"] = SN(surface)
    box(sc, b, "Mesh", (x1 - x0, -y0, z1 - z0), ((x0 + x1) / 2, y0 / 2, (z0 + z1) / 2), mat)
    col_box(sc, b, "Shape", (x1 - x0, -y0, z1 - z0), ((x0 + x1) / 2, y0 / 2, (z0 + z1) / 2))
    return b


def solid(sc, parent, name, x0, x1, y0, y1, z0, z1, mat, collide=True):
    if collide:
        b = static_body(sc, parent, name, LAYER_WORLD)
        box(sc, b, "Mesh", (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat)
        col_box(sc, b, "Shape", (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        return b
    return box(sc, parent, name, (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat)


# =============================================================================
# Shell
# =============================================================================

def build_shell(sc, root):
    sh = n3d(sc, root, "Shell")
    wl = n3d(sc, sh, "Walls")
    hall_w, liv_w, kit_w = "wallpaper_stripe", "wallpaper_floral", "wall_plaster_cream"
    panel, plaster, siding, mass = "wall_wood_paneling", "wall_plaster_cream", "brick_red", "wall_plaster_cream"

    fw, fy0, fy1 = CUT_FRONT
    dw, dy0, dy1 = CUT_DOOR
    cw_, cy0, cy1 = CUT_CLOSET
    win = lambda c, sill=SILL: (c, CUT_WIN_W, sill, sill + CUT_WIN_H)

    # --- Exterior walls (outer half siding, inner half the room's finish).
    # West: hall end (stripe) then living (plaster), split at the partition.
    wall(sc, wl, "WestHall", "z", -0.30, 1.575, -0.15, EXT, [], siding, hall_w, y_bot=GRADE)
    wall(sc, wl, "WestLiving", "z", 1.575, 6.55, -0.15, EXT, [win(z) for z in WEST_WINDOWS_Z], siding, plaster, y_bot=GRADE)
    # South: living (plaster) then kitchen (plaster).
    wall(sc, wl, "SouthLiving", "x", -0.30, 6.075, 6.40, EXT, [win(x) for x in SOUTH_LIVING_X], plaster, siding, y_bot=GRADE)
    wall(sc, wl, "SouthKitchen", "x", 6.075, 10.65, 6.40, EXT, [win(DINETTE_WINDOW_X), win(SINK_X, SILL_SINK)], kit_w, siding, y_bot=GRADE)
    # East: kitchen with the back door; north part closes the mass.
    wall(sc, wl, "EastKitchen", "z", 1.575, 6.55, 10.50, EXT, [(BACK_DOOR_Z, fw, fy0, fy1)], kit_w, siding, y_bot=GRADE)
    wall(sc, wl, "EastNorth", "z", -1.40, 1.575, 10.50, EXT, [], mass, siding, y_bot=GRADE)
    # North: the front-door section is exterior; east of it the hall backs onto
    # the closet and the bedroom wing (interior partitions with mass behind).
    wall(sc, wl, "NorthFront", "x", -0.30, 2.12, -0.15, EXT, [(FRONT_DOOR_X, fw, fy0, fy1)], siding, hall_w, y_bot=GRADE)
    wall(sc, wl, "NorthHall", "x", 2.12, 6.075, -0.075, INT, [(CLOSET_X, cw_, cy0, cy1), (BEDROOM_DOOR_X, dw, dy0, dy1)], mass, hall_w)
    # --- Interior partitions.
    wall(sc, wl, "HallLiving", "x", 0.0, 6.075, 1.575, INT, [((HALL_OPEN[0] + HALL_OPEN[1]) / 2, HALL_OPEN[1] - HALL_OPEN[0], 0.0, CASED_HEAD)], hall_w, liv_w)
    wall(sc, wl, "HallEast", "z", -0.15, 1.575, 6.075, INT, [(BASEMENT_DOOR_Z, dw, dy0, dy1)], hall_w, mass)
    wall(sc, wl, "LivingKitchen", "z", 1.575, 6.25, 6.075, INT, [((KITCHEN_OPEN[0] + KITCHEN_OPEN[1]) / 2, KITCHEN_OPEN[1] - KITCHEN_OPEN[0], 0.0, CASED_HEAD)], panel, kit_w)
    wall(sc, wl, "KitchenNorth", "x", 6.075, 10.35, 1.575, INT, [(PANTRY_DOOR_X, dw, dy0, dy1)], mass, kit_w)
    # Mullions between the west picture windows are part of WestLiving (the gaps
    # between cuts). Cased openings:
    cased_opening(sc, wl, "HallLivingCasing", "x", HALL_OPEN[0], HALL_OPEN[1], 1.575, INT)
    cased_opening(sc, wl, "KitchenCasing", "z", KITCHEN_OPEN[0], KITCHEN_OPEN[1], 6.075, INT)

    # --- Mass behind the locked doors / around the niches (never seen lit).
    ms = n3d(sc, sh, "Mass")
    # Closet niche: x 2.25..3.85, z -0.80..-0.15 (open toward the hall).
    solid(sc, ms, "ClosetWest", 2.12, 2.25, SKIN_BOT, SKIN_TOP, -1.40, -0.15, plaster)
    solid(sc, ms, "ClosetBack", 2.12, 3.98, SKIN_BOT, SKIN_TOP, -1.40, -0.80, plaster)
    solid(sc, ms, "BedroomWing", 3.85, 6.20, SKIN_BOT, SKIN_TOP, -1.40, -0.15, mass)
    # North of the kitchen: basement stair (behind the hall door) and pantry niche.
    solid(sc, ms, "Basement", 6.15, 7.85, SKIN_BOT, SKIN_TOP, -1.40, 1.50, mass)
    solid(sc, ms, "PantryBack", 7.85, 8.75, SKIN_BOT, SKIN_TOP, -1.40, 0.95, plaster)
    solid(sc, ms, "NorthEast", 8.75, 10.35, SKIN_BOT, SKIN_TOP, -1.40, 1.50, mass)

    # --- Floors (surface metadata on each body), foundation, ceiling, attic.
    fl = n3d(sc, sh, "Floors")
    floor_slab(sc, fl, "HallFloor", (-0.15, 6.075, -0.80, 1.575), ROOMS["Hall"]["floor"], "wood")
    floor_slab(sc, fl, "LivingFloor", (-0.15, 6.075, 1.575, 6.40), ROOMS["Living"]["floor"], "carpet")
    floor_slab(sc, fl, "KitchenFloor", (6.075, 10.50, 1.575, 6.40), ROOMS["Kitchen"]["floor"], "linoleum")
    floor_slab(sc, fl, "PantryFloor", (7.85, 8.75, 0.95, 1.575), ROOMS["Kitchen"]["floor"], "linoleum")
    # Thresholds under the front and back doors sit on the slab edge.
    solid(sc, fl, "Foundation", -0.30, 10.65, GRADE - 0.2, -0.30, -1.40, 6.55, "concrete")
    ce = n3d(sc, sh, "Ceiling")
    solid(sc, ce, "CeilingSlab", -0.30, 10.65, H, H + 0.30, -1.40, 6.55, "ceiling_popcorn")
    solid(sc, ce, "Attic", -0.30, 10.65, H + 0.30, H + 0.80, -1.40, 6.55, "wood_dark", collide=False)
    # Roof: overhanging eaves (soffit + fascia) and a low hip, outside only.
    rf = n3d(sc, sh, "Roof")
    ov = 0.45
    solid(sc, rf, "Soffit", -0.30 - ov, 10.65 + ov, H + 0.30, H + 0.42, -1.40 - ov, 6.55 + ov, "trim_white", collide=False)
    prism(sc, rf, "Hip", (11.0 + 2 * ov, 1.6, 8.0 + 2 * ov), 0.5, (5.175, H + 0.42 + 0.8, 2.575), "wood_dark", rot=(0, 0, 0))

    # --- Baseboards.
    bb = n3d(sc, sh, "Baseboards")
    hall, liv, kit = ROOMS["Hall"]["base_mat"], ROOMS["Living"]["base_mat"], ROOMS["Kitchen"]["base_mat"]
    baseboard_run(sc, bb, "HallN", "x", 0.0, 6.0, 0.0, 1, [gap(FRONT_DOOR_X, fw), gap(CLOSET_X, cw_), gap(BEDROOM_DOOR_X, dw)], hall)
    baseboard_run(sc, bb, "HallS", "x", 0.0, 6.0, 1.5, -1, [(HALL_OPEN[0] - 0.06, HALL_OPEN[1] + 0.06)], hall)
    baseboard_run(sc, bb, "HallW", "z", 0.0, 1.5, 0.0, 1, [], hall)
    baseboard_run(sc, bb, "HallE", "z", 0.0, 1.5, 6.0, -1, [gap(BASEMENT_DOOR_Z, dw)], hall)
    baseboard_run(sc, bb, "LivN", "x", 0.0, 6.0, 1.65, 1, [(HALL_OPEN[0] - 0.06, HALL_OPEN[1] + 0.06)], liv)
    baseboard_run(sc, bb, "LivS", "x", 0.0, 6.0, 6.25, -1, [], liv)
    baseboard_run(sc, bb, "LivW", "z", 1.65, 6.25, 0.0, 1, [], liv)
    baseboard_run(sc, bb, "LivE", "z", 1.65, 6.25, 6.0, -1, [(KITCHEN_OPEN[0] - 0.06, KITCHEN_OPEN[1] + 0.06)], liv)
    baseboard_run(sc, bb, "KitN", "x", 6.15, 10.35, 1.65, 1, [gap(PANTRY_DOOR_X, dw)], kit)
    baseboard_run(sc, bb, "KitW", "z", 1.65, 6.25, 6.15, 1, [(KITCHEN_OPEN[0] - 0.06, KITCHEN_OPEN[1] + 0.06)], kit)
    baseboard_run(sc, bb, "KitE", "z", 1.65, 6.25, 10.35, -1, [gap(BACK_DOOR_Z, fw)], kit)
    baseboard_run(sc, bb, "KitS", "x", 6.15, 8.53, 6.25, -1, [], kit)
    # Kitchen backsplash behind the counter run.
    box(sc, bb, "Backsplash", (1.82, 0.10, 0.012), (9.435, 0.96, 6.244), "laminate_formica")


# =============================================================================
# Fixtures (doors, windows, lights)
# =============================================================================

def override(sc, parent, name, props):
    """Set properties on a node inside an instanced scene (an 'editable child'
    override in .tscn terms)."""
    sc.nodes.append(('[node name="%s" parent="%s"]' % (name, parent), dict(props)))


def glass_out_of_gi(sc, inst_path, glass_parents):
    """Fixture glass casts no shadow but still blocks SDFGI (fixtures do not set
    gi_mode); switch it off per placement so sun bounce gets through."""
    for gp in glass_parents:
        override(sc, inst_path + "/" + gp, "Glass", {"gi_mode": 0})


def window(sc, parent, name, pos, rot_y, blinds=None, sill=SILL):
    """Window fixture + optional venetian blinds mounted inside the head."""
    path = inst(sc, parent, name, F + "window_double_hung.tscn", pos, rot_y)
    glass_out_of_gi(sc, path, ["Window/LowerSash", "Window/UpperSash"])
    if blinds is not None:
        raised, angle, bent = blinds
        bp = lp(pos, rot_y, (0, 1.365, 0.085))
        inst(sc, parent, name + "Blinds", P + "architecture/venetian_blinds.tscn", bp, rot_y, {
            "width": 0.84, "height": 1.33, "raised": raised, "slat_angle": angle, "bent_slat": bent})


def build_openings(sc, root):
    fx = n3d(sc, root, "Fixtures")
    hall = n3d(sc, fx, "Hall")
    p = inst(sc, hall, "FrontDoor", F + "door_front.tscn", (FRONT_DOOR_X, 0, -0.15), 180.0, {
        "locked": True, "display_name": "Front door"})
    glass_out_of_gi(sc, p, ["Slab"])
    inst(sc, hall, "BedroomDoor", F + "door_interior.tscn", (BEDROOM_DOOR_X, 0, -0.075), 0.0, {
        "locked": True, "display_name": "Bedroom hall door",
        "locked_observations": STRS(["It's locked.", "The knob turns a little and stops."])})
    inst(sc, hall, "BasementDoor", F + "door_interior.tscn", (6.075, 0, BASEMENT_DOOR_Z), 90.0, {
        "locked": True, "display_name": "Basement door",
        "locked_observations": STRS(["Locked.", "Cooler air comes under it, and the smell of concrete."])})
    inst(sc, hall, "Closet", F + "closet_sliding.tscn", (CLOSET_X, 0, -0.075), 0.0)
    inst(sc, hall, "HallLight", F + "ceiling_light.tscn", (3.0, H, 0.75), 0.0, {"dead_bulb": True})
    inst(sc, hall, "HallSwitch", F + "light_switch.tscn", (1.66, 1.2, 0.0), 0.0, {
        "targets": NPS(["../HallLight"]), "display_name": "Hall light switch"})

    liv = n3d(sc, fx, "Living")
    for i, z in enumerate(WEST_WINDOWS_Z):
        window(sc, liv, "WestWindow%d" % i, (-0.15, SILL, z), 90.0, blinds=(0.0, 30.0 + 4 * i, 3 + 2 * i))
    for i, x in enumerate(SOUTH_LIVING_X):
        window(sc, liv, "SouthWindow%d" % i, (x, SILL, 6.40), 180.0, blinds=(0.35 if i == 0 else 0.0, 22.0, 5))
    inst(sc, liv, "CeilingFan", F + "ceiling_fan.tscn", (3.2, H, 3.95), 0.0)
    inst(sc, liv, "FanSwitch", F + "light_switch.tscn", (3.16, 1.2, 1.65), 0.0, {
        "targets": NPS(["../CeilingFan/Motor"]), "display_name": "Fan switch"})
    inst(sc, liv, "LampNorth", F + "table_lamp.tscn", (1.95, 0.58, 3.05), 0.0)
    inst(sc, liv, "LampSouth", F + "table_lamp.tscn", (1.95, 0.58, 5.75), 0.0)

    kit = n3d(sc, fx, "Kitchen")
    window(sc, kit, "DinetteWindow", (DINETTE_WINDOW_X, SILL, 6.40), 180.0, blinds=(0.55, 10.0, 2))
    window(sc, kit, "SinkWindow", (SINK_X, SILL_SINK, 6.40), 180.0, blinds=None)
    p = inst(sc, kit, "BackDoor", F + "door_front.tscn", (10.50, 0, BACK_DOOR_Z), 90.0, {
        "locked": True, "display_name": "Back door",
        "locked_observations": STRS(["The deadbolt is thrown.", "Locked. Through the glass: the side yard and the garbage cans."])})
    glass_out_of_gi(sc, p, ["Slab"])
    inst(sc, kit, "PantryDoor", F + "door_interior.tscn", (PANTRY_DOOR_X, 0, 1.575), 180.0, {
        "start_state": 2, "display_name": "Pantry door", "open_angle_degrees": 30.0,
        "observations": STRS(["It doesn't stay shut on its own.", "The bottom edge is rubbed pale where it drags."])})
    inst(sc, kit, "KitchenLight", F + "ceiling_light.tscn", (8.25, H, 3.95), 0.0)
    inst(sc, kit, "KitchenSwitch", F + "light_switch.tscn", (6.15, 1.2, 2.40), 90.0, {
        "targets": NPS(["../KitchenLight"]), "display_name": "Kitchen light switch"})
    # Cabinet run along the south wall (backs on the wall at z = 6.25, fronts north).
    inst(sc, kit, "Sink", F + "kitchen_sink.tscn", (SINK_X, 0, 6.25), 180.0)
    inst(sc, kit, "BaseEast", F + "kitchen_cabinet_base.tscn", (9.885, 0, 6.25), 180.0)
    inst(sc, kit, "WallCabEast", F + "kitchen_cabinet_wall.tscn", (9.885, 1.37, 6.25), 180.0)
    inst(sc, kit, "Fridge", F + "fridge.tscn", (9.93, 0, 1.65), 0.0)


# =============================================================================
# Dressing
# =============================================================================

def build_hall(sc, root):
    g = n3d(sc, root, "Hall")
    # Phone table on the south wall, east of the opening.
    thing(sc, g, "PhoneTable", (3.85, 0, 1.30), 0.0, [
        ("box", (0.62, 0.03, 0.36), (0, 0.735, 0), "wood_medium"),
        ("box", (0.56, 0.02, 0.30), (0, 0.25, 0), "wood_medium"),
        ("box", (0.035, 0.72, 0.035), (-0.28, 0.36, -0.15), "wood_dark"),
        ("box", (0.035, 0.72, 0.035), (0.28, 0.36, -0.15), "wood_dark"),
        ("box", (0.035, 0.72, 0.035), (-0.28, 0.36, 0.15), "wood_dark"),
        ("box", (0.035, 0.72, 0.035), (0.28, 0.36, 0.15), "wood_dark"),
    ], "Telephone table", ["A little telephone table with a shelf under it.", "Rings on the top from glasses set down wet."])
    inst(sc, g, "Telephone", F + "telephone.tscn", (3.95, 0.75, 1.30), 175.0)
    inst(sc, g, "GuttersNote", P + "media/note.tscn", (3.66, 0.75, 1.36), 168.0, {"preset": 2})
    thing(sc, g, "PhoneBook", (3.85, 0.26, 1.30), 4.0, [
        ("box", (0.21, 0.05, 0.28), (0, 0.025, 0), "paper_yellowed"),
        ("box", (0.215, 0.002, 0.285), (0, 0.051, 0), "book_cover_c"),
    ], "Phone book", ["Calder Falls and vicinity, 1992. The corner is soft from thumbing.",
                      "Pell's Market has a quarter-page ad in the yellow pages, circled once in pen."], layer=LAYER_INTERACT)
    thing(sc, g, "Thermostat", (4.55, 1.45, 1.5), 180.0, [
        ("box", (0.09, 0.12, 0.03), (0, 0, 0.015), "plastic_beige"),
        ("box", (0.05, 0.004, 0.002), (0, 0.02, 0.031), "metal_dark"),
    ], "Thermostat", ["Set to 78. The needle on the thermometer says 84.", "The dial is stiff and I leave it."], layer=LAYER_INTERACT)
    inst(sc, g, "Mirror", P + "hallway/wall_mirror.tscn", (0.0, 1.05, 0.75), 90.0)
    inst(sc, g, "KeyHooks", P + "hallway/key_hooks.tscn", (0.24, 1.45, 0.0), 0.0)
    inst(sc, g, "UmbrellaStand", P + "hallway/umbrella_stand.tscn", (0.20, 0, 0.22), 0.0)
    inst(sc, g, "Shoes", P + "hallway/shoes_pair.tscn", (1.62, 0, 0.30), 200.0)
    inst(sc, g, "ShoesKids", P + "hallway/shoes_pair.tscn", (0.42, 0, 1.25), 75.0)
    inst(sc, g, "CoatRack", P + "hallway/coat_rack.tscn", (5.66, 0, 0.40), 160.0)
    thing(sc, g, "SmokeDetector", (2.0, H, 0.75), 0.0, [
        ("cyl", (0.065, 0.07, 0.035), (0, -0.0175, 0), "plastic_white"),
    ], "Smoke detector", ["The little test light doesn't come on.", "Dust in the vents."], layer=LAYER_INTERACT)
    # Closet interior: shelf, rod, coats, a box.
    cl = n3d(sc, g, "ClosetInside")
    thing(sc, cl, "Shelf", (CLOSET_X, 0, -0.50), 0.0, [
        ("box", (1.58, 0.02, 0.32), (0, 1.74, -0.13), "wood_light"),
        ("cyl", (0.012, 0.012, 1.58), (0, 1.66, 0.0), "metal_chrome", (0, 0, 90)),
    ], "Closet shelf", ["Mittens in a bag, a folded bedsheet, a box.", "It smells like mothballs and rain boots."], layer=LAYER_INTERACT)
    coats = [
        (-0.55, "fabric_plaid", 1.00, "Wool coat", ["A heavy plaid coat. Far too warm to have been worn lately.", "The pockets are empty and turned out."]),
        (-0.30, "leather_brown", 0.78, "Leather jacket", ["A brown leather jacket, stiff at the elbows.", "A book of matches in the pocket, unused."]),
        (-0.08, "fabric_corduroy_brown", 0.92, "Barn coat", ["A corduroy-collared barn coat.", "Sawdust in the cuffs."]),
        (0.40, "fabric_curtain_heavy", 1.10, "Raincoat", ["A long raincoat. It's dry.", "Folded in the pocket: a church bulletin from April."]),
    ]
    for i, (x, mat, ln, name, lines) in enumerate(coats):
        thing(sc, cl, "Coat%d" % i, (CLOSET_X + x, 0, -0.50), 90.0 + (i * 7 - 10), [
            ("box", (0.12, 0.05, 0.44), (0, 1.60, 0), mat),
            ("box", (0.10, ln, 0.46), (0, 1.60 - 0.05 - ln / 2, 0), mat),
            ("box", (0.004, 0.08, 0.004), (0, 1.645, 0), "metal_chrome"),
        ], name, lines, layer=LAYER_INTERACT)
    thing(sc, cl, "ShelfBox", (CLOSET_X + 0.35, 1.75, -0.62), 6.0, [
        ("box", (0.42, 0.20, 0.28), (0, 0.10, 0), "cardboard"),
    ], "Box", ["Christmas lights, wound neatly around a piece of cardboard.", "A note on the lid in marker: 'TREE - TOP FIRST'."], layer=LAYER_INTERACT)
    inst(sc, cl, "LaundryBasket", P + "hallway/laundry_basket.tscn", (CLOSET_X + 0.45, 0, -0.45), 90.0)


def build_living(sc, root):
    g = n3d(sc, root, "Living")
    inst(sc, g, "Rug", P + "living/area_rug.tscn", (3.55, 0, 4.40), 90.0)
    inst(sc, g, "Sofa", P + "living/sofa_floral.tscn", (2.15, 0.0, 4.40), 90.0)
    inst(sc, g, "EndTableNorth", P + "living/end_table_oak.tscn", (1.95, 0, 3.05), 90.0)
    inst(sc, g, "EndTableSouth", P + "living/end_table_oak.tscn", (1.95, 0, 5.75), 90.0)
    inst(sc, g, "CoffeeTable", P + "living/coffee_table_oak_glass.tscn", (3.40, 0.012, 4.40), 90.0)
    ec, ecr = (5.715, 0.0, 4.93), -90.0
    inst(sc, g, "EntertainmentCenter", P + "living/entertainment_center_oak.tscn", ec, ecr)
    inst(sc, g, "Tv", F + "tv_crt.tscn", lp(ec, ecr, (0, 0.495, 0.02)), ecr)
    inst(sc, g, "Vcr", F + "vcr.tscn", lp(ec, ecr, (0, 0.31, 0.04)), ecr)
    inst(sc, g, "VhsStack", P + "media/vhs_stack.tscn", lp(ec, ecr, (-0.22, 0.085, 0.05)), ecr)
    inst(sc, g, "TapeRewinder", P + "media/tape_rewinder.tscn", lp(ec, ecr, (0.20, 0.085, 0.05)), ecr)
    # Tapes standing spine-out on the side column shelves.
    for i, (lx, ly, tape) in enumerate(((-0.66, 0.425, 1), (-0.63, 0.425, 2), (-0.60, 0.425, 3), (0.60, 0.745, 5))):
        r = math.radians(ecr)
        pos = lp(ec, ecr, (lx + 0.0125, ly + 0.0935, 0.0))
        inst(sc, g, "ShelfTape%d" % i, P + "media/vhs_tape_%02d.tscn" % tape, pos, 0.0, rot=(0, ecr, 90))
    inst(sc, g, "TvListings", P + "media/tv_listings.tscn", lp(ec, ecr, (0.55, 1.18, 0.05)), ecr + 8)
    inst(sc, g, "GameConsole", P + "media/game_console.tscn", (5.05, 0.012, 4.95), -90.0)
    inst(sc, g, "Remote", P + "media/tv_remote.tscn", (3.30, 0.426, 4.15), 70.0)
    inst(sc, g, "TapeOnTable", P + "media/vhs_tape_06.tscn", (3.45, 0.426, 4.70), 100.0)
    inst(sc, g, "TapeBirthday", P + "media/vhs_tape_04.tscn", (3.25, 0.111, 4.55), 84.0)
    inst(sc, g, "AshtrayLiving", P + "kitchen/ashtray_amber.tscn", (1.95, 0.58, 5.62), 0.0)
    inst(sc, g, "MugLiving", P + "kitchen/mug.tscn", (1.88, 0.58, 3.22), 40.0)
    inst(sc, g, "Recliner", P + "living/recliner_corduroy.tscn", (4.25, 0, 5.40), 118.0)
    inst(sc, g, "MagazineRack", P + "living/magazine_rack.tscn", (3.55, 0, 5.95), 180.0)
    inst(sc, g, "Stereo", F + "stereo_console.tscn", (3.0, 0, 6.25), 180.0)
    inst(sc, g, "Cassettes", P + "media/audio_cassette_pile.tscn", (2.62, 0.66, 6.05), 172.0)
    inst(sc, g, "Clock", P + "living/sunburst_clock.tscn", (3.0, 1.85, 6.25), 180.0)
    inst(sc, g, "Bookshelf", P + "living/bookshelf.tscn", (4.10, 0, 1.655 + 0.155), 0.0)
    inst(sc, g, "PictureLake", P + "living/framed_picture_lake.tscn", (5.15, 1.55, 1.65), 0.0)
    inst(sc, g, "PictureBarn", P + "living/framed_picture_barn.tscn", (6.0, 1.50, 2.08), -90.0)
    inst(sc, g, "PictureAbstract", P + "living/framed_picture_abstract.tscn", (0.0, 1.52, 2.22), 90.0)
    inst(sc, g, "PlantCorner", P + "living/potted_plant_dry.tscn", (0.48, 0, 5.85), 30.0)
    inst(sc, g, "HangingPlant", P + "living/macrame_plant_hanger.tscn", (1.6, H, 5.92), 0.0)
    inst(sc, g, "BoxClosed", P + "hallway/moving_box_closed.tscn", (5.66, 0, 1.96), 8.0)
    inst(sc, g, "BoxClosedTop", P + "hallway/moving_box_closed.tscn", (5.64, 0.41, 1.98), -6.0)
    inst(sc, g, "BoxOpen", P + "hallway/moving_box_open.tscn", (5.02, 0, 2.02), 172.0)
    inst(sc, g, "Fan", P + "hallway/floor_fan.tscn", (0.55, 0, 2.05), 140.0)
    # Drapes on the west group (drawn back), sheers on the south windows.
    inst(sc, g, "WestDrapes", P + "architecture/heavy_drapes.tscn", (0.0, 2.30, 4.40), 90.0, {
        "width": 3.60, "height": 2.05, "open_amount": 1.0})
    for i, x in enumerate(SOUTH_LIVING_X):
        inst(sc, g, "SouthSheers%d" % i, P + "architecture/sheer_curtains.tscn", (x, 2.27, 6.25), 180.0, {
            "width": 1.20, "height": 1.62, "open_amount": 0.72 if i == 0 else 0.55})


def build_kitchen(sc, root):
    g = n3d(sc, root, "Kitchen")
    t = (7.25, 0, 4.85)
    inst(sc, g, "Table", P + "kitchen/dinette_table.tscn", t, 0.0)
    inst(sc, g, "ChairWest", P + "kitchen/dinette_chair.tscn", (6.58, 0, 4.85), 90.0)
    inst(sc, g, "ChairNorth", P + "kitchen/dinette_chair.tscn", (7.30, 0, 4.27), 0.0)
    inst(sc, g, "ChairEast", P + "kitchen/dinette_chair.tscn", (7.98, 0, 4.92), -74.0)
    inst(sc, g, "ChairSouth", P + "kitchen/dinette_chair.tscn", (7.18, 0, 5.43), 180.0)
    ty = 0.74
    inst(sc, g, "PlateWest", P + "kitchen/plate.tscn", (6.92, ty, 4.86), 90.0)
    inst(sc, g, "PlateNorth", P + "kitchen/plate.tscn", (7.32, ty, 4.62), 0.0)
    inst(sc, g, "MugWest", P + "kitchen/mug.tscn", (6.95, ty, 4.60), 20.0)
    inst(sc, g, "MugNorth", P + "kitchen/mug.tscn", (7.55, ty, 4.62), 200.0)
    inst(sc, g, "Mail", P + "media/mail_stack.tscn", (7.55, ty, 5.08), 12.0)
    inst(sc, g, "Newspaper", P + "media/newspaper.tscn", (7.23, ty, 5.03), -8.0)
    inst(sc, g, "Ashtray", P + "kitchen/ashtray_amber.tscn", (6.88, ty, 5.13), 0.0)
    inst(sc, g, "FruitBowl", P + "kitchen/fruit_bowl.tscn", (9.85, 1.66, 2.05), 0.0)
    cy = 0.91
    inst(sc, g, "DishRack", P + "kitchen/dish_rack.tscn", (9.68, cy, 5.98), 180.0)
    inst(sc, g, "Glass", P + "kitchen/drinking_glass.tscn", (8.78, SILL_SINK, 6.22), 0.0)
    inst(sc, g, "Percolator", P + "kitchen/percolator.tscn", (10.15, cy, 5.98), 180.0)
    inst(sc, g, "Cereal", P + "kitchen/cereal_box.tscn", (7.62, ty, 4.86), 200.0)
    inst(sc, g, "PaperTowels", P + "kitchen/paper_towel_holder.tscn", (9.885, 1.33, 6.25), 180.0)
    inst(sc, g, "Calendar", P + "media/wall_calendar_aug_1993.tscn", (9.10, 1.72, 1.65), 0.0)
    inst(sc, g, "FridgeNote", P + "media/note.tscn", (9.78, 1.32, 2.418), 0.0, {"preset": 1}, rot=(90, 0, 0))
    inst(sc, g, "TrashCan", P + "kitchen/trash_can.tscn", (6.42, 0, 2.02), 90.0)
    inst(sc, g, "BoxKitchen", P + "hallway/moving_box_closed.tscn", (10.06, 0, 5.08), -84.0)
    # Pantry shelves with a few things on them.
    pt = thing(sc, g, "PantryShelves", (8.30, 0, 1.22), 0.0, [
        ("box", (0.86, 0.02, 0.50), (0, y, -0.02), "wood_light") for y in (0.45, 0.95, 1.40, 1.82)
    ] + [
        ("cyl", (0.038, 0.038, 0.11), (-0.30 + 0.085 * i, 0.965 + 0.055, -0.08), "metal_chrome") for i in range(5)
    ] + [
        ("cyl", (0.042, 0.042, 0.12), (0.12 + 0.09 * i, 1.415 + 0.06, -0.10), "metal_chrome") for i in range(3)
    ] + [
        ("box", (0.20, 0.28, 0.07), (-0.22, 0.465 + 0.14, -0.10), "cardboard"),
        ("box", (0.17, 0.24, 0.06), (0.05, 0.465 + 0.12, -0.12), "paper_white"),
        ("box", (0.30, 0.22, 0.25), (0.20, 1.835 + 0.11, -0.05), "cardboard"),
    ], "Pantry shelves", ["Soup, creamed corn, two cans of peaches. All the labels face out.",
                          "A sack of flour folded over and clipped with a clothespin.",
                          "The top shelf is lined with contact paper, curling at the corners."], collide=True)
    # Garbage cans outside the back door (seen through its glass).
    out = n3d(sc, g, "BackStep")
    solid(sc, out, "Step", 10.65, 11.6, GRADE, -0.03, 2.8, 4.0, "concrete")
    for i, z in enumerate((4.6, 5.25)):
        cyl(sc, out, "Can%d" % i, 0.28, 0.26, 0.85, (11.1, GRADE + 0.425, z), "metal_chrome")
        cyl(sc, out, "Lid%d" % i, 0.30, 0.30, 0.04, (11.1, GRADE + 0.87, z), "metal_chrome")


# =============================================================================
# Outside
# =============================================================================

def tree(sc, parent, name, base, height, canopy, seed, leaf_count=46):
    """Trunk + overlapping leaf clusters with real gaps so the shadow dapples."""
    g = n3d(sc, parent, name, base)
    rng = random.Random(seed)
    cyl(sc, g, "Trunk", 0.16, 0.24, height, (0, height / 2, 0), "wood_dark", segs=10)
    cx, cy, cz, rx_, ry_, rz_ = canopy
    for i in range(5):
        a = rng.uniform(0, 360)
        l = rng.uniform(1.0, 1.8)
        y = height - rng.uniform(0.4, 1.4)
        cyl(sc, g, "Limb%d" % i, 0.05, 0.09, l, (math.cos(math.radians(a)) * l * 0.35, y + l * 0.3, math.sin(math.radians(a)) * l * 0.35),
            "wood_dark", rot=(rng.uniform(25, 50) * math.sin(math.radians(a)), 0, -rng.uniform(25, 50) * math.cos(math.radians(a))), segs=6)
    for i in range(leaf_count):
        while True:
            u, v, w = rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)
            if u * u + v * v + w * w <= 1.0:
                break
        r = rng.uniform(0.28, 0.62)
        sphere(sc, g, "Leaves%d" % i, r, r * rng.uniform(1.4, 2.0), (cx + u * rx_, cy + v * ry_, cz + w * rz_), "plant_green",
               rot=(rng.uniform(-20, 20), rng.uniform(0, 180), rng.uniform(-20, 20)), segs=10, rings=5)


def neighbour_house(sc, parent, name, x0, x1, z0, z1, height, mat, roof_mat, windows):
    g = n3d(sc, parent, name)
    solid(sc, g, "Body", x0, x1, GRADE, GRADE + height, z0, z1, mat, collide=False)
    prism(sc, g, "Roof", (x1 - x0 + 0.8, 1.8, z1 - z0 + 0.8), 0.5, ((x0 + x1) / 2, GRADE + height + 0.9, (z0 + z1) / 2), roof_mat)
    for i, (p, size) in enumerate(windows):
        box(sc, g, "Win%d" % i, size, p, "glass_dusty")


def build_outside(sc, root):
    g = n3d(sc, root, "Outside")
    # Lawn: one big slab at grade, the yard mass under it.
    solid(sc, g, "Lawn", -60.0, 60.0, GRADE - 0.5, GRADE, -60.0, 60.0, "plant_green")
    # West side yard: our strip of lawn, a low hedge, the neighbour's drive and house.
    solid(sc, g, "Hedge", -7.2, -6.2, GRADE, GRADE + 1.15, -4.0, 15.0, "plant_green", collide=False)
    solid(sc, g, "Driveway", -10.5, -7.6, GRADE, GRADE + 0.02, -30.0, 9.0, "concrete", collide=False)
    neighbour_house(sc, g, "WestNeighbour", -20.0, -11.0, -6.0, 9.0, 3.0, "wall_plaster_cream", "wood_dark",
                    [((-10.98, GRADE + 1.7, 0.5), (0.05, 1.1, 0.9)), ((-10.98, GRADE + 1.7, 4.8), (0.05, 1.1, 0.9))])
    # South: back yard, a board fence, the house behind.
    for i in range(48):
        x = -6.0 + i * 0.5
        box(sc, g, "Fence%d" % i, (0.14, 1.8, 0.03), (x, GRADE + 0.9, 17.0 + (0.01 if i % 2 else 0)), "wood_light")
    box(sc, g, "FenceRail", (24.0, 0.09, 0.05), (5.75, GRADE + 1.5, 17.04), "wood_medium")
    neighbour_house(sc, g, "SouthNeighbour", 0.0, 14.0, 23.0, 31.0, 3.0, "wood_light", "wood_dark",
                    [((4.0, GRADE + 1.8, 22.98), (1.2, 1.0, 0.05)), ((9.5, GRADE + 1.8, 22.98), (1.2, 1.0, 0.05))])
    box(sc, g, "Clothesline", (6.0, 0.01, 0.01), (5.0, GRADE + 1.9, 11.0), "metal_chrome")
    for x in (2.0, 8.0):
        cyl(sc, g, "LinePost%d" % int(x), 0.03, 0.03, 1.95, (x, GRADE + 0.975, 11.0), "metal_chrome", segs=8)
    # The tree that breaks up the sun on the west windows, and one out back.
    tree(sc, g, "WestTree", (-4.2, GRADE, 9.6), 4.0, (0.0, 5.4, 0.0, 2.2, 1.2, 1.9), seed=1418, leaf_count=30)
    tree(sc, g, "BackTree", (9.0, GRADE, 13.5), 4.2, (0.0, 5.4, 0.0, 2.6, 1.5, 2.6), seed=93)
    # Front: street-side lawn, a walk to the door.
    solid(sc, g, "FrontWalk", 0.4, 1.6, GRADE, GRADE + 0.03, -12.0, -0.30, "concrete", collide=False)
    solid(sc, g, "FrontStoop", 0.2, 1.8, GRADE, -0.03, -1.4, -0.30, "concrete", collide=False)


# =============================================================================
# Lighting (temporary sun until atmosphere/ lands) and sound
# =============================================================================

def sun_rotation():
    return (-SUN_ELEVATION, -SUN_AZIMUTH_TRAVEL, 0.0)


# Atmosphere rig knobs (see atmosphere/README.md). Azimuth = bearing the light
# comes FROM: 236 is south-west by west: the west group still throws long shafts
# across the shag, and the south windows (0.30 m deep reveals) are not so
# grazing that their jambs swallow the light, so the dinette window lands a
# patch on the lino. (At 245+ the south patches shrink to slivers.)
ATMOSPHERE = {"sun_azimuth": 236.0, "sun_elevation": 36.0, "exposure_bias": -0.25}

# Dust and haze: one box per sunlit window, covering the shaft from the glass
# to where its patch lands. (centre, size)
DUST = [
    ("DustWestGroup", (1.3, 1.0, 3.9), (2.4, 1.9, 3.2), 40.0),
    ("DustSouthWest", (2.2, 0.9, 5.7), (1.6, 1.6, 1.0), 30.0),
    ("DustSouthEast", (5.0, 0.9, 5.7), (1.6, 1.6, 1.0), 30.0),
    ("DustDinette", (7.8, 0.9, 5.6), (1.8, 1.6, 1.2), 35.0),
]
HAZE = [
    ("HazeWestGroup", (0.9, 1.3, 4.2), (1.6, 2.0, 3.2), 0.014),
    ("HazeSouthLiving", (3.0, 1.3, 5.7), (4.4, 2.0, 1.0), 0.010),
    ("HazeDinette", (7.5, 1.2, 5.6), (1.6, 1.8, 1.0), 0.012),
    ("HazeHallClear", (3.0, 1.2, 0.75), (6.0, 2.4, 1.5), -0.006),
]
PROBES = [
    # name, centre, size (room interior), why
    ("ProbeKitchen", (8.25, 1.22, 3.95), (4.2, 2.44, 4.6)),    # glossy lino
    ("ProbeHall", (3.0, 1.22, 0.75), (6.0, 2.44, 1.5)),        # the mirror
]


def build_air(sc, g):
    for name, c, size, density in DUST:
        inst(sc, g, name, DUST_SCENE, c, 0.0, {"box_size": V3(size), "density": density})
    for name, c, size, density in HAZE:
        inst(sc, g, name, HAZE_SCENE, c, 0.0, {"size": V3(size), "haze_density": density})
    for name, c, size in PROBES:
        sc.node(name, "ReflectionProbe", g, {
            "transform": XF(c), "update_mode": 0, "size": V3(size), "box_projection": True,
            "interior": True, "ambient_mode": 0, "max_distance": 0.0})


def build_lighting(sc, root):
    g = n3d(sc, root, "Lighting")
    rig = os.path.join(os.path.dirname(__file__), "..", "..", "..", "atmosphere", "afternoon_atmosphere.tscn")
    if os.path.exists(rig) and not DEBUG_FLAT:
        inst(sc, g, "Atmosphere", ATMOS_RIG, (0, 0, 0), 0.0, ATMOSPHERE)
        build_air(sc, g)
        return
    sky = sc.sub("ProceduralSkyMaterial", sky_top_color=C(0.38, 0.56, 0.80), sky_horizon_color=C(0.86, 0.84, 0.78),
                 ground_horizon_color=C(0.62, 0.58, 0.48), ground_bottom_color=C(0.3, 0.3, 0.22), sun_angle_max=20.0)
    skyr = sc.sub("Sky", sky_material=sky)
    env = sc.sub("Environment", background_mode=2, sky=skyr, ambient_light_source=3, ambient_light_energy=0.25,
                 tonemap_mode=2, tonemap_exposure=1.7, tonemap_white=6.0, ssao_enabled=True, glow_enabled=True,
                 glow_intensity=0.4, sdfgi_enabled=True, sdfgi_use_occlusion=True, sdfgi_cascades=3,
                 sdfgi_min_cell_size=0.1, sdfgi_energy=2.2, sdfgi_bounce_feedback=0.8)
    if DEBUG_FLAT:
        env = sc.sub("Environment", background_mode=2, sky=skyr, ambient_light_source=2, ambient_light_color=C(1, 1, 1),
                     ambient_light_energy=0.9, tonemap_mode=2)
    sc.node("TempEnvironment", "WorldEnvironment", g, {"environment": env})
    sc.node("TempSun", "DirectionalLight3D", g, {
        "transform": XF((5, 10, 3), sun_rotation()), "light_color": C(1.0, 0.89, 0.74), "light_energy": 3.0,
        "shadow_enabled": True, "directional_shadow_max_distance": 40.0, "light_angular_distance": 0.5})


def build_audio(sc, root):
    g = n3d(sc, root, "Audio")
    inst(sc, g, "AmbienceBed", A + "ambience_bed.tscn", (5.0, 1.5, 3.0), 0.0)
    for name, (x0, x1, z0, z1) in (("Hall", ROOMS["Hall"]["rect"]), ("Living", ROOMS["Living"]["rect"]), ("Kitchen", ROOMS["Kitchen"]["rect"])):
        inst(sc, g, "Reverb" + name, A + "reverb_zone.tscn", ((x0 + x1) / 2, H / 2, (z0 + z1) / 2), 0.0, {
            "preset": ROOMS[name]["reverb"], "size": V3(x1 - x0, H, z1 - z0)})
    inst(sc, g, "ReverbCloset", A + "reverb_zone.tscn", (CLOSET_X, H / 2, -0.48), 0.0, {"preset": 5, "size": V3(1.6, H, 0.65)})
    inst(sc, g, "ReverbPantry", A + "reverb_zone.tscn", (8.30, H / 2, 1.25), 0.0, {"preset": 5, "size": V3(0.9, H, 0.55)})
    # One fly, on the sunny south pane of the west group.
    inst(sc, g, "Fly", A + "ambient_emitter.tscn", (-0.06, 1.48, WEST_WINDOWS_Z[2] + 0.2), 0.0, {
        "sound_id": SN("fly_buzz"), "pitch_drift": 0.008, "volume_db": -4.0})
    inst(sc, g, "HouseSettle", A + "random_oneshot_emitter.tscn", (5.2, 1.8, 3.0), 0.0, {
        "sound_ids": Raw('Array[StringName]([&"house_settle"])'), "min_gap": 20.0, "max_gap": 90.0,
        "volume_min_db": -8.0, "volume_max_db": -2.0, "box_size": V3(10.4, 1.2, 7.6), "initial_delay_max": 30.0})
    inst(sc, g, "Neighbourhood", A + "random_oneshot_emitter.tscn", (-18.0, 2.0, 40.0), 0.0, {
        "sound_ids": Raw('Array[StringName]([&"distant_dog", &"distant_car", &"distant_mower"])'),
        "min_gap": 40.0, "max_gap": 150.0, "area": 1, "radius": 22.0, "initial_delay_max": 45.0,
        "volume_min_db": -4.0, "volume_max_db": 0.0})


def build():
    make_norim_materials()
    sc = Scene("House")
    root = "."
    build_shell(sc, root)
    build_openings(sc, root)
    build_hall(sc, root)
    build_living(sc, root)
    build_kitchen(sc, root)
    build_outside(sc, root)
    build_lighting(sc, root)
    build_audio(sc, root)
    sc.node("PlayerSpawn", "Marker3D", root, {"transform": XF((FRONT_DOOR_X, 0.0, 0.50), (0, 180, 0))}, groups=["player_spawn"])
    sc.write("_shots/debug_house.tscn" if DEBUG_FLAT else OUT)


if __name__ == "__main__":
    build()
