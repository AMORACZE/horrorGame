#!/usr/bin/env python3
"""Authoring aid: writes the fixture scenes in fixtures/*.tscn.

    python3 fixtures/tools/build_fixture_scenes.py

The output is plain, editor-friendly .tscn. Once a scene has been edited by
hand or in the editor, treat the scene as the source of truth and stop
re-running this for it (it overwrites). Dimensions are metres; see the
comments on each builder for the origin convention.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tscn import *  # noqa: E402,F403

I = "res://interaction/"
F = "res://fixtures/"
DOOR = I + "door_interactable.gd"
HINGED = I + "hinged_part_interactable.gd"
SLIDING = I + "sliding_part_interactable.gd"
SWITCH = I + "switch_interactable.gd"
DEVICE = I + "device_toggle_interactable.gd"
JAMMED = I + "jammed_interactable.gd"
BASE = I + "interactable.gd"
POWERED = I + "powered_light.gd"
FAN = I + "fan_motor.gd"
LOOP = I + "loop_emitter.gd"

# Profiles (MovingPartInteractable.Profile)
SMOOTH, PUSH, LATCH, LINEAR = 0, 1, 2, 3
SHADOW_OFF, SHADOW_ON, SHADOW_DOUBLE = 0, 1, 2


def comp(sc, parent, name, script, props):
    return sc.node(name, "Node", parent, {"script": sc.ext(script, "Script"), **props})


def look(sc, parent, display, lines, name="Look"):
    return comp(sc, parent, name, BASE, {"display_name": display, "observations": STRS(lines)})


# =============================================================================
# Doors
# =============================================================================

def door_frame(sc, wo, yh, wall, casing_w=0.064, both_sides=True, mat="trim_white"):
    """Jambs, head, casings. Opening wo wide, head underside at yh."""
    jt = 0.019
    fr = static_body(sc, ".", "Frame", LAYER_WORLD)
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (wo / 2 + jt / 2)
        box(sc, fr, "Jamb" + side, (jt, yh + jt, wall), (x, (yh + jt) / 2, 0), mat)
        col_box(sc, fr, "JambShape" + side, (jt, yh + jt, wall), (x, (yh + jt) / 2, 0))
    box(sc, fr, "Head", (wo + 2 * jt, jt, wall), (0, yh + jt / 2, 0), mat)
    col_box(sc, fr, "HeadShape", (wo + 2 * jt, jt, wall), (0, yh + jt / 2, 0))
    ct = 0.016
    rev = 0.005
    h = yh + rev + casing_w
    faces = (1, -1) if both_sides else (1,)
    for fz in faces:
        z = fz * (wall / 2 + ct / 2)
        tag = "Front" if fz > 0 else "Back"
        for side, sx in (("L", -1), ("R", 1)):
            box(sc, fr, "Casing%s%s" % (tag, side), (casing_w, h, ct), (sx * (wo / 2 + rev + casing_w / 2), h / 2, z), mat)
            # Back band: a thin raised bead on the outer edge, the 70s clamshell look.
            box(sc, fr, "Bead%s%s" % (tag, side), (0.012, h, 0.006), (sx * (wo / 2 + rev + casing_w - 0.006), h / 2, z + fz * 0.011), mat)
        box(sc, fr, "CasingHead" + tag, (wo + 2 * (rev + casing_w), casing_w, ct), (0, yh + rev + casing_w / 2, z), mat)
        box(sc, fr, "BeadHead" + tag, (wo + 2 * (rev + casing_w), 0.012, 0.006), (0, yh + rev + casing_w - 0.006, z + fz * 0.011), mat)
    return fr


def knob_set(sc, parent, x, y, t, prefix, mat="metal_brass", deadbolt=False):
    """Knob, rose and shank on both faces of a slab of thickness t (slab spans z 0..t)."""
    for face, sz in (("A", -1), ("B", 1)):
        z0 = 0.0 if sz < 0 else t
        cyl(sc, parent, "%sRose%s" % (prefix, face), 0.027, 0.029, 0.007, (x, y, z0 + sz * 0.0035), mat, rot=(90, 0, 0))
        cyl(sc, parent, "%sShank%s" % (prefix, face), 0.011, 0.013, 0.028, (x, y, z0 + sz * 0.021), mat, rot=(90, 0, 0))
        sphere(sc, parent, "%sKnob%s" % (prefix, face), 0.029, 0.05, (x, y, z0 + sz * 0.052), mat, rot=(90, 0, 0))
        if deadbolt:
            yd = y + 0.14
            cyl(sc, parent, "BoltRose%s" % face, 0.03, 0.031, 0.006, (x, yd, z0 + sz * 0.003), mat, rot=(90, 0, 0))
            cyl(sc, parent, "BoltCylinder%s" % face, 0.017, 0.018, 0.014, (x, yd, z0 + sz * 0.012), mat, rot=(90, 0, 0))
            box(sc, parent, "Keyway%s" % face, (0.0025, 0.012, 0.002), (x, yd - 0.002, z0 + sz * 0.0195), "plastic_black")


def build_door(kind):
    front = kind == "front"
    W = 0.91 if front else 0.81
    H = 2.03
    T = 0.045 if front else 0.035
    wall = 0.30 if front else 0.15
    bottom = 0.022 if front else 0.010  # threshold / carpet undercut
    wo = W + 0.006
    yh = bottom + H + 0.003
    zf = -wall / 2 + 0.003  # swing-side face of the closed slab
    slab_mat = "wood_medium" if front else "wood_light"

    root_props = {"display_name": "Front door" if front else "Door"}
    if front:
        root_props["locked"] = True
        root_props["locked_observations"] = STRS([
            "Locked. The deadbolt takes a key on this side too.",
            "The bolt doesn't move.",
        ])
    sc = Scene("DoorFront" if front else "DoorInterior", script=F + "door_fixture.gd", props=root_props)
    door_frame(sc, wo, yh, wall)
    fr = "Frame"
    # Stops (the slab closes against them from the swing side).
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, fr, "Stop" + side, (0.012, yh, 0.032), (sx * (wo / 2 - 0.006), yh / 2, zf + T + 0.016), "trim_white")
    box(sc, fr, "StopHead", (wo, 0.012, 0.032), (0, yh - 0.006, zf + T + 0.016), "trim_white")
    box(sc, fr, "Strike", (0.0015, 0.07, 0.026), (wo / 2 - 0.0008, 0.91, zf + T / 2), "metal_brass")
    if front:
        box(sc, fr, "Threshold", (wo + 0.04, 0.02, wall), (0, 0.01, 0), "metal_chrome")
        box(sc, fr, "ThresholdRib", (wo, 0.004, 0.01), (0, 0.022, zf + T + 0.01), "rubber_black")
        col_box(sc, fr, "ThresholdShape", (wo + 0.04, 0.02, wall), (0, 0.01, 0))

    slab = anim_body(sc, ".", "Slab", SOLID_INTERACT, pos=(-wo / 2, 0, zf))
    cx = 0.003 + W / 2
    cy = bottom + H / 2
    if not front:
        box(sc, slab, "SlabMesh", (W, H, T), (cx, cy, T / 2), slab_mat)
        # Hollow-core flush door: a slightly lighter edge band shows on the lock edge.
        box(sc, slab, "EdgeBand", (0.002, H, T), (0.003 + W + 0.001, cy, T / 2), "wood_light")
    else:
        wx0, wx1 = 0.003 + W / 2 - 0.205, 0.003 + W / 2 + 0.205
        wy0, wy1 = bottom + 1.30, bottom + 1.70
        x0, x1 = 0.003, 0.003 + W
        y0, y1 = bottom, bottom + H
        box(sc, slab, "SlabLower", (W, wy0 - y0, T), (cx, (y0 + wy0) / 2, T / 2), slab_mat)
        box(sc, slab, "SlabUpper", (W, y1 - wy1, T), (cx, (wy1 + y1) / 2, T / 2), slab_mat)
        box(sc, slab, "SlabLeft", (wx0 - x0, wy1 - wy0, T), ((x0 + wx0) / 2, (wy0 + wy1) / 2, T / 2), slab_mat)
        box(sc, slab, "SlabRight", (x1 - wx1, wy1 - wy0, T), ((wx1 + x1) / 2, (wy0 + wy1) / 2, T / 2), slab_mat)
        box(sc, slab, "Glass", (wx1 - wx0, wy1 - wy0, 0.004), ((wx0 + wx1) / 2, (wy0 + wy1) / 2, T / 2), "glass_window", cast=SHADOW_OFF)
        box(sc, slab, "MuntinV", (0.018, wy1 - wy0, T * 0.5), ((wx0 + wx1) / 2, (wy0 + wy1) / 2, T / 2), slab_mat)
        box(sc, slab, "MuntinH", (wx1 - wx0, 0.018, T * 0.5), ((wx0 + wx1) / 2, (wy0 + wy1) / 2, T / 2), slab_mat)
        # Glazing bead around the lite and raised panels, both faces.
        for fz, tag in ((-1, "In"), (1, "Out")):
            z = (0 if fz < 0 else T) + fz * 0.004
            for nm, size, pos in (
                ("BeadTop", (wx1 - wx0 + 0.04, 0.02, 0.008), ((wx0 + wx1) / 2, wy1 + 0.01, z)),
                ("BeadBot", (wx1 - wx0 + 0.04, 0.02, 0.008), ((wx0 + wx1) / 2, wy0 - 0.01, z)),
                ("BeadL", (0.02, wy1 - wy0, 0.008), (wx0 - 0.01, (wy0 + wy1) / 2, z)),
                ("BeadR", (0.02, wy1 - wy0, 0.008), (wx1 + 0.01, (wy0 + wy1) / 2, z)),
            ):
                box(sc, slab, nm + tag, size, pos, slab_mat)
            pz = (0 if fz < 0 else T) + fz * 0.003
            for i, (px0, px1) in enumerate(((x0 + 0.12, cx - 0.05), (cx + 0.05, x1 - 0.12))):
                for nm, ph_, py_ in (("Panel", 0.78, bottom + 0.63), ("PanelLow", 0.2, bottom + 1.08)):
                    box(sc, slab, "%s%d%s" % (nm, i, tag), (px1 - px0, ph_, 0.004), ((px0 + px1) / 2, py_, (0 if fz < 0 else T) + fz * 0.002), slab_mat)
                    box(sc, slab, "%sGroove%d%s" % (nm, i, tag), (px1 - px0 - 0.036, ph_ - 0.036, 0.006), ((px0 + px1) / 2, py_, (0 if fz < 0 else T) + fz * 0.003), "wood_dark")
                    box(sc, slab, "%sField%d%s" % (nm, i, tag), (px1 - px0 - 0.05, ph_ - 0.05, 0.012), ((px0 + px1) / 2, py_, (0 if fz < 0 else T) + fz * 0.006), slab_mat)
        box(sc, slab, "KickPlate", (W - 0.06, 0.2, 0.0015), (cx, bottom + 0.12, T + 0.0008), "metal_brass")
    # Hinges: knuckles on the hinge line.
    for i, hy in enumerate((bottom + 0.20, bottom + H / 2 + 0.05, bottom + H - 0.18)):
        cyl(sc, slab, "Hinge%d" % i, 0.0065, 0.0065, 0.089, (0, hy, -0.002), "metal_brass", segs=12)
        sphere(sc, slab, "HingeTip%d" % i, 0.0065, 0.008, (0, hy + 0.048, -0.002), "metal_brass", segs=12, rings=6)
    knob_x = 0.003 + W - 0.060
    knob_set(sc, slab, knob_x, 0.91, T, "", deadbolt=front)
    box(sc, slab, "LatchPlate", (0.0015, 0.057, 0.025), (0.003 + W + 0.0008, 0.91, T / 2), "metal_brass")
    col_box(sc, slab, "SlabShape", (W, H, T), (cx, cy, T / 2))
    door_props = {
        "display_name": "Front door" if front else "Door",
        "observations": STRS([
            "Hot air comes in off the porch.",
            "The weatherstrip is coming away along the bottom.",
        ] if front else [
            "The knob turns loose before it catches.",
            "The bottom edge is rubbed pale where it drags on the carpet.",
        ]),
        "locked_observations": STRS(["It's locked.", "Locked. The knob doesn't give at all."]),
    }
    if front:
        door_props["locked"] = True
        door_props["open_duration"] = 1.5
        door_props["close_duration"] = 1.05
    comp(sc, slab, "Door", DOOR, door_props)
    sc.write("fixtures/door_front.tscn" if front else "fixtures/door_interior.tscn")


def build_closet():
    """Bypass sliding closet doors, 1.52 x 2.03 opening in a 0.15 wall.
    Origin floor, centre of opening and wall. Room side is +Z."""
    wo, H, wall = 1.52, 2.03, 0.15
    yh = 2.045
    sc = Scene("ClosetSliding")
    door_frame(sc, wo, yh, wall)
    fr = "Frame"
    box(sc, fr, "Track", (wo, 0.028, 0.09), (0, yh - 0.014, 0), "metal_chrome")
    box(sc, fr, "TrackLip", (wo, 0.004, 0.09), (0, yh - 0.029, 0), "metal_dark")
    box(sc, fr, "FloorGuide", (0.04, 0.012, 0.09), (0, 0.006, 0), "plastic_beige")
    pw, ph, pt = 0.78, 2.0, 0.032
    for name, x, z, axis, pull_x in (
        ("PanelBack", -wo / 2 + pw / 2, -0.025, (1, 0, 0), -pw / 2 + 0.06),
        ("PanelFront", wo / 2 - pw / 2, 0.025, (-1, 0, 0), pw / 2 - 0.06),
    ):
        b = anim_body(sc, ".", name, SOLID_INTERACT, pos=(x, 0.012, z))
        box(sc, b, "Slab", (pw, ph, pt), (0, ph / 2, 0), "wood_light")
        box(sc, b, "EdgeTop", (pw, 0.004, pt + 0.002), (0, ph - 0.002, 0), "wood_medium")
        cyl(sc, b, "Pull", 0.021, 0.021, 0.004, (pull_x, 1.0, pt / 2 + 0.001), "metal_chrome", rot=(90, 0, 0))
        cyl(sc, b, "PullCup", 0.016, 0.016, 0.0045, (pull_x, 1.0, pt / 2 + 0.0012), "metal_dark", rot=(90, 0, 0))
        cyl(sc, b, "PullBack", 0.021, 0.021, 0.004, (pull_x, 1.0, -pt / 2 - 0.001), "metal_chrome", rot=(90, 0, 0))
        for i, rx_ in enumerate((-pw / 2 + 0.08, pw / 2 - 0.08)):
            box(sc, b, "Hanger%d" % i, (0.025, 0.03, 0.012), (rx_, ph + 0.015, 0), "metal_dark")
        col_box(sc, b, "Shape", (pw, ph, pt), (0, ph / 2, 0))
        comp(sc, b, "Slide", SLIDING, {
            "display_name": "Closet door",
            "open_prompt": "Slide open", "close_prompt": "Slide shut",
            "axis": V3(axis), "distance": 0.72,
            "open_duration": 0.95, "close_duration": 0.85,
            "open_profile": LATCH, "close_profile": LATCH, "stop_bump": 0.008,
            "open_sound": SN("drawer_open"), "close_sound": SN("drawer_close"),
            "observations": STRS(["It rolls on a bad wheel and shudders.", "Grit in the track."]),
        })
    sc.write("fixtures/closet_sliding.tscn")


# =============================================================================
# Switch and lights
# =============================================================================

def build_light_switch():
    """Toggle switch plate. Origin on the wall surface at the switch centre; +Z out of the wall."""
    sc = Scene("LightSwitch", script=F + "light_switch.gd")
    b = static_body(sc, ".", "Body", LAYER_INTERACT)
    box(sc, b, "Plate", (0.07, 0.114, 0.004), (0, 0, 0.002), "plastic_beige")
    box(sc, b, "PlateBevel", (0.064, 0.108, 0.003), (0, 0, 0.0045), "plastic_beige")
    box(sc, b, "Slot", (0.011, 0.024, 0.001), (0, 0, 0.0062), "plastic_black")
    for i, sy in enumerate((0.0302, -0.0302)):
        cyl(sc, b, "Screw%d" % i, 0.0034, 0.0036, 0.0014, (0, sy, 0.0063), "plastic_beige", rot=(90, 0, 0), segs=12)
        box(sc, b, "ScrewSlot%d" % i, (0.005, 0.0007, 0.0004), (0, sy, 0.0071), "metal_dark")
    lever = n3d(sc, b, "Lever", (0, 0, 0.006))
    box(sc, lever, "Bat", (0.0085, 0.0065, 0.016), (0, 0, 0.008), "plastic_beige")
    box(sc, lever, "BatTip", (0.009, 0.0075, 0.003), (0, 0, 0.0155), "plastic_beige")
    col_box(sc, b, "Shape", (0.08, 0.125, 0.03), (0, 0, 0.015))
    comp(sc, b, "Switch", SWITCH, {
        "display_name": "Light switch",
        "lever": NP("../Lever"),
        "observations": STRS([
            "The plate is grey around the toggle from fingers.",
            "It snaps over harder than I expect.",
        ]),
    })
    sc.write("fixtures/light_switch.tscn")


def powered(sc, lights, bulbs, glows=(), name="Power", parent=".", extra=None):
    props = {"lights": NPS(lights), "bulb_meshes": NPS(bulbs)}
    if glows:
        props["glow_meshes"] = NPS(glows)
    if extra:
        props.update(extra)
    return comp(sc, parent, name, POWERED, props)


WARM = (1.0, 0.71, 0.42)


def build_table_lamp():
    """80s brass candlestick lamp, pleated empire shade. Origin: base bottom centre."""
    sc = Scene("TableLamp", script=F + "light_fixture.gd")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    br = "metal_brass"
    cyl(sc, b, "Foot", 0.08, 0.086, 0.022, (0, 0.011, 0), br)
    cyl(sc, b, "FootFelt", 0.082, 0.082, 0.002, (0, 0.001, 0), "fabric_corduroy_brown")
    cyl(sc, b, "Step", 0.034, 0.068, 0.034, (0, 0.039, 0), br)
    cyl(sc, b, "Collar0", 0.024, 0.024, 0.008, (0, 0.06, 0), br)
    cyl(sc, b, "Column", 0.015, 0.017, 0.15, (0, 0.139, 0), br)
    sphere(sc, b, "Urn", 0.043, 0.085, (0, 0.25, 0), br)
    cyl(sc, b, "Collar1", 0.021, 0.021, 0.01, (0, 0.297, 0), br)
    cyl(sc, b, "UpperColumn", 0.0135, 0.0135, 0.09, (0, 0.347, 0), br)
    cyl(sc, b, "HarpSaddle", 0.0028, 0.0028, 0.15, (0, 0.395, 0), br, rot=(0, 0, 90), segs=8)
    cyl(sc, b, "Socket", 0.018, 0.02, 0.052, (0, 0.423, 0), br)
    knob = n3d(sc, b, "Knob", (0.02, 0.43, 0))
    cyl(sc, knob, "KnobStem", 0.0035, 0.0035, 0.012, (0.006, 0, 0), br, rot=(0, 0, 90), segs=8)
    cyl(sc, knob, "KnobWing", 0.008, 0.008, 0.005, (0.013, 0, 0), br, rot=(0, 0, 90), segs=12)
    cyl(sc, b, "BulbNeck", 0.012, 0.013, 0.02, (0, 0.457, 0), "fx:bulb_glass", cast=SHADOW_OFF)
    sphere(sc, b, "Bulb", 0.03, 0.068, (0, 0.493, 0), "fx:bulb_glass", cast=SHADOW_OFF)
    ang = math.degrees(math.atan2(0.064, 0.21))
    for side, sx in (("L", -1), ("R", 1)):
        cyl(sc, b, "Harp" + side, 0.0026, 0.0026, 0.2196, (sx * 0.039, 0.505, 0), br, rot=(0, 0, sx * ang), segs=8)
    cyl(sc, b, "HarpTop", 0.006, 0.006, 0.01, (0, 0.615, 0), br, segs=12)
    sphere(sc, b, "Finial", 0.013, 0.024, (0, 0.633, 0), br, segs=14, rings=8)
    res_mesh(sc, b, "Shade", F + "meshes/pleated_shade.res", (0, 0.49, 0), "fabric_lampshade", cast=SHADOW_DOUBLE)
    cyl(sc, b, "Cord", 0.0028, 0.0028, 0.32, (0, 0.003, -0.24), "fabric_corduroy_brown", rot=(90, 0, 0), segs=8)
    omni(sc, b, "Light", (0, 0.49, 0), 1.7, 6.0, WARM, True, 0.04, 1.2)
    omni(sc, b, "ShadeGlow", (0, 0.49, 0), 0.22, 2.4, WARM, False)
    col_cyl(sc, b, "ShapeBase", 0.07, 0.36, (0, 0.18, 0))
    col_cyl(sc, b, "ShapeShade", 0.2, 0.26, (0, 0.49, 0))
    comp(sc, b, "Switch", SWITCH, {
        "display_name": "Lamp", "mode": 1, "targets": NPS(["../../Power"]),
        "on_prompt": "Turn on", "off_prompt": "Turn off",
        "lever": NP("../Knob"), "lever_on_rotation_degrees": V3(90, 0, 0), "lever_off_rotation_degrees": V3(0, 0, 0),
        "on_sound": SN("lamp_click"), "off_sound": SN("lamp_click"),
        "observations": STRS([
            "The switch turns with a dry click.",
            "The shade has gone brown on the side that faced the window.",
        ]),
    })
    powered(sc, ["../Body/Light", "../Body/ShadeGlow"], ["../Body/Bulb", "../Body/BulbNeck"], ["../Body/Shade"],
            extra={"bulb_emission_energy": 9.0, "glow_emission_energy": 0.55})
    sc.write("fixtures/table_lamp.tscn")


def build_floor_lamp():
    """70s arc lamp: marble base, chrome arc, dome shade reaching 1.4 m toward +X.
    Origin: floor, centre of the base."""
    sc = Scene("FloorLamp", script=F + "light_fixture.gd")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    box(sc, b, "Base", (0.30, 0.07, 0.30), (0, 0.037, 0), "ceramic_white")
    box(sc, b, "BaseTop", (0.29, 0.004, 0.29), (0, 0.074, 0), "ceramic_white")
    for i, (fx, fz) in enumerate(((-0.12, -0.12), (0.12, -0.12), (-0.12, 0.12), (0.12, 0.12))):
        cyl(sc, b, "Foot%d" % i, 0.015, 0.015, 0.004, (fx, 0.002, fz), "fabric_corduroy_brown", segs=10)
    cyl(sc, b, "Collar", 0.022, 0.026, 0.035, (0, 0.093, 0), "metal_chrome")
    res_mesh(sc, b, "Pole", F + "meshes/arc_lamp_pole.res", (0, 0, 0), "metal_chrome")
    ex, ey = 0.72 + 0.72 * math.cos(math.radians(18)), 1.18 + 0.72 * 0.95 * math.sin(math.radians(18))
    rim = ey - 0.19
    cyl(sc, b, "ShadeCap", 0.022, 0.03, 0.035, (ex, ey - 0.012, 0), "metal_chrome")
    res_mesh(sc, b, "Shade", F + "meshes/dome_shade.res", (ex, rim, 0), "metal_chrome", cast=SHADOW_DOUBLE)
    cyl(sc, b, "ShadeRim", 0.2, 0.2, 0.006, (ex, rim + 0.003, 0), "metal_chrome", caps=False, segs=32)
    cyl(sc, b, "Socket", 0.02, 0.02, 0.05, (ex, rim + 0.13, 0), "metal_dark", cast=SHADOW_OFF)
    sphere(sc, b, "Bulb", 0.032, 0.07, (ex, rim + 0.075, 0), "fx:bulb_glass", cast=SHADOW_OFF)
    knob = n3d(sc, b, "Knob", (ex + 0.06, rim + 0.155, 0))
    cyl(sc, knob, "KnobMesh", 0.008, 0.009, 0.018, (0, 0.009, 0), "metal_dark", segs=12)
    omni(sc, b, "Light", (ex, rim + 0.07, 0), 2.2, 6.5, WARM, True, 0.04, 1.1)
    col_box(sc, b, "ShapeBase", (0.30, 0.075, 0.30), (0, 0.037, 0))
    col_cyl(sc, b, "ShapePole", 0.03, 1.1, (0, 0.62, 0))
    col_sphere(sc, b, "ShapeShade", 0.2, (ex, rim + 0.08, 0))
    comp(sc, b, "Switch", SWITCH, {
        "display_name": "Floor lamp", "mode": 1, "targets": NPS(["../../Power"]),
        "on_prompt": "Turn on", "off_prompt": "Turn off",
        "lever": NP("../Knob"), "lever_on_rotation_degrees": V3(0, 90, 0), "lever_off_rotation_degrees": V3(0, 0, 0),
        "on_sound": SN("lamp_click"), "off_sound": SN("lamp_click"),
        "observations": STRS([
            "The base is real marble. It doesn't budge.",
            "The chrome is pitted where the arc bends.",
        ]),
    })
    powered(sc, ["../Body/Light"], ["../Body/Bulb"], extra={"bulb_emission_energy": 9.0})
    sc.write("fixtures/floor_lamp.tscn")


def build_ceiling_light():
    """Flush frosted-glass dome. Origin on the ceiling plane; hangs toward -Y."""
    sc = Scene("CeilingLight", script=F + "light_fixture.gd")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    cyl(sc, b, "Pan", 0.165, 0.17, 0.022, (0, -0.011, 0), "metal_painted_white")
    cyl(sc, b, "PanLip", 0.158, 0.158, 0.006, (0, -0.025, 0), "metal_painted_white")
    res_mesh(sc, b, "Glass", F + "meshes/ceiling_dome.res", (0, -0.026, 0), "fx:glass_frosted", rot=(180, 0, 0), cast=SHADOW_OFF)
    cyl(sc, b, "Stud", 0.003, 0.003, 0.03, (0, -0.118, 0), "metal_brass", segs=8)
    sphere(sc, b, "Finial", 0.012, 0.02, (0, -0.122, 0), "metal_brass", segs=14, rings=8)
    cyl(sc, b, "FinialCap", 0.016, 0.012, 0.006, (0, -0.112, 0), "metal_brass", segs=14)
    for i, x in enumerate((-0.045, 0.045)):
        sphere(sc, b, "Bulb%d" % i, 0.027, 0.06, (x, -0.06, 0), "fx:bulb_glass", rot=(0, 0, 180), cast=SHADOW_OFF)
    for i in range(5):
        a = i * 1.7 + 0.4
        box(sc, b, "Fly%d" % i, (0.008, 0.003, 0.004), (math.cos(a) * 0.05 * (1 + i % 2), -0.104, math.sin(a) * 0.04), "plastic_black", rot=(0, i * 47, 0), cast=SHADOW_OFF)
    omni(sc, b, "Light", (0, -0.075, 0), 1.5, 7.5, WARM, True, 0.08, 1.0)
    col_cyl(sc, b, "Shape", 0.17, 0.12, (0, -0.06, 0))
    look(sc, b, "Ceiling light", ["A few dead flies in the bottom of the glass.", "It's on the wall switch."])
    powered(sc, ["../Body/Light"], ["../Body/Glass", "../Body/Bulb0", "../Body/Bulb1"],
            extra={"bulb_emission_energy": 2.2})
    sc.write("fixtures/ceiling_light.tscn")


def build_ceiling_fan():
    """52" five-blade fan with a light kit. Origin on the ceiling; blades 0.27 m down.
    Pull chains: fan (+X) and light (-X)."""
    sc = Scene("CeilingFan", script=F + "ceiling_fan.gd")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    br = "metal_brass"
    cyl(sc, b, "Canopy", 0.05, 0.075, 0.065, (0, -0.0325, 0), br)
    cyl(sc, b, "Downrod", 0.0125, 0.0125, 0.11, (0, -0.115, 0), br, segs=12)
    cyl(sc, b, "Coupler", 0.03, 0.06, 0.03, (0, -0.18, 0), br)
    cyl(sc, b, "Housing", 0.11, 0.105, 0.105, (0, -0.2475, 0), br, segs=32)
    cyl(sc, b, "Band", 0.112, 0.112, 0.014, (0, -0.236, 0), "wood_dark", segs=32)
    cyl(sc, b, "HousingBottom", 0.105, 0.075, 0.025, (0, -0.3125, 0), br, segs=32)
    cyl(sc, b, "SwitchCup", 0.075, 0.06, 0.06, (0, -0.355, 0), br)
    cyl(sc, b, "Fitter", 0.06, 0.06, 0.012, (0, -0.391, 0), br)
    res_mesh(sc, b, "Glass", F + "meshes/bowl_glass.res", (0, -0.396, 0), "fx:glass_frosted", rot=(180, 0, 0), cast=SHADOW_OFF)
    sphere(sc, b, "Finial", 0.011, 0.02, (0, -0.492, 0), br, segs=12, rings=6)
    sphere(sc, b, "Bulb", 0.03, 0.065, (0, -0.43, 0), "fx:bulb_glass", rot=(180, 0, 0), cast=SHADOW_OFF)
    omni(sc, b, "Light", (0, -0.44, 0), 1.6, 7.5, WARM, True, 0.05, 1.0)
    col_cyl(sc, b, "Shape", 0.12, 0.5, (0, -0.25, 0))
    look(sc, b, "Ceiling fan", ["Dust on the leading edge of every blade.", "The brass has gone brown where hands never touched it."])

    rotor = n3d(sc, ".", "Rotor", (0, -0.272, 0))
    for i in range(5):
        arm = n3d(sc, rotor, "Arm%d" % i, rot=(0, i * 72, 0))
        box(sc, arm, "Iron", (0.15, 0.006, 0.034), (0.165, -0.004, 0), br)
        box(sc, arm, "IronDrop", (0.03, 0.012, 0.03), (0.225, -0.01, 0), br)
        blade = n3d(sc, arm, "Pitch", (0.43, -0.018, 0), rot=(12, 0, 0))
        box(sc, blade, "Blade", (0.46, 0.007, 0.14), (0, 0, 0), "wood_dark")
        cyl(sc, blade, "Tip", 0.07, 0.07, 0.007, (0.23, 0, 0), "wood_dark", segs=20)
        box(sc, blade, "Cane", (0.30, 0.0075, 0.09), (0.02, 0, 0), "wood_light")
    for name, x in (("FanChain", 0.035), ("LightChain", -0.035)):
        chain = n3d(sc, ".", name, (x, -0.37, 0.03))
        cyl(sc, chain, "Links", 0.0013, 0.0013, 0.21, (0, -0.105, 0), "metal_brass", segs=6)
        cyl(sc, chain, "Fob", 0.0045, 0.007, 0.03, (0, -0.225, 0), br, segs=10)
        body = static_body(sc, ".", name + "Body", LAYER_INTERACT, pos=(x, -0.48, 0.03))
        col_box(sc, body, "Shape", (0.035, 0.24, 0.035))
        fan = name == "FanChain"
        comp(sc, body, "Pull", SWITCH, {
            "display_name": "Fan chain" if fan else "Light chain", "mode": 1,
            "targets": NPS(["../../Motor" if fan else "../../Power"]),
            "on_prompt": "Pull (fan on)" if fan else "Pull (light on)",
            "off_prompt": "Pull (fan off)" if fan else "Pull (light off)",
            "lever": NP("../../" + name), "lever_on_rotation_degrees": V3(0, 0, 0), "lever_off_rotation_degrees": V3(0, 0, 0),
            "lever_tug_offset": V3(0, -0.018, 0), "cooldown": 0.35,
            "on_sound": SN("lamp_click"), "off_sound": SN("lamp_click"),
            "observations": STRS(["It wobbles a little as it comes up to speed."] if fan else ["The chain is warm."]),
        })
    comp(sc, ".", "Motor", FAN, {"rotor": NP("../Rotor"), "max_rpm": 92.0, "spin_up_time": 6.0, "spin_down_time": 16.0})
    powered(sc, ["../Body/Light"], ["../Body/Glass", "../Body/Bulb"], extra={"bulb_emission_energy": 2.4})
    sc.write("fixtures/ceiling_fan.tscn")


# =============================================================================
# TV, VCR
# =============================================================================

def build_tv():
    """20" early-90s CRT television. Origin: bottom centre of the footprint; screen faces +Z."""
    sc = Scene("TvCrt")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    cab = "plastic_black"
    # Front shell: a bezel around a 0.37 x 0.28 tube opening.
    scr_y = 0.275
    ow_, oh_ = 0.37, 0.28
    y0, y1 = 0.015, 0.465
    box(sc, b, "FrontTop", (0.52, y1 - (scr_y + oh_ / 2), 0.12), (0, (y1 + scr_y + oh_ / 2) / 2, 0.16), cab)
    box(sc, b, "FrontBottom", (0.52, (scr_y - oh_ / 2) - y0, 0.12), (0, (y0 + scr_y - oh_ / 2) / 2, 0.16), cab)
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, b, "Front" + side, ((0.52 - ow_) / 2, oh_, 0.12), (sx * (0.26 - (0.52 - ow_) / 4), scr_y, 0.16), cab)
    box(sc, b, "TubeBack", (ow_, oh_, 0.01), (0, scr_y, 0.11), "plastic_black")
    # Rear tube housing: a 4-sided frustum tapering toward -Z.
    r0, r1, hl = 0.48 / math.sqrt(2), 0.27 / math.sqrt(2), 0.33
    basis = mmul(mmul(rx(-90), diag(1, 1, 0.40 / 0.48)), ry(45))
    sc_mesh = sc.sub("CylinderMesh", top_radius=r1, bottom_radius=r0, height=hl, radial_segments=4, rings=1)
    sc.node("Rear", "MeshInstance3D", b, {"transform": XF((0, 0.235, 0.10 - hl / 2), basis=basis), "mesh": sc_mesh,
                                          "surface_material_override/0": sc.mat(cab)})
    box(sc, b, "RearCap", (0.25, 0.20, 0.02), (0, 0.235, -0.235), cab)
    for i in range(6):
        box(sc, b, "Vent%d" % i, (0.18, 0.006, 0.002), (0, 0.18 + i * 0.022, -0.2455), "plastic_grey")
    # Tube face: a cushion-shaped curved rectangle (fixtures/meshes/crt_face.res).
    res_mesh(sc, b, "ScreenGlass", F + "meshes/crt_face.res", (0, scr_y, 0.214), "crt_screen_off")
    res_mesh(sc, b, "ScreenStatic", F + "meshes/crt_face.res", (0, scr_y, 0.2146), "fx:crt_static", cast=SHADOW_OFF, visible=False)
    for nm, size, pos in (
        ("MaskTop", (ow_ + 0.012, 0.014, 0.006), (0, scr_y + oh_ / 2 + 0.001, 0.223)),
        ("MaskBottom", (ow_ + 0.012, 0.014, 0.006), (0, scr_y - oh_ / 2 - 0.001, 0.223)),
        ("MaskL", (0.014, oh_, 0.006), (-ow_ / 2 - 0.001, scr_y, 0.223)),
        ("MaskR", (0.014, oh_, 0.006), (ow_ / 2 + 0.001, scr_y, 0.223)),
    ):
        box(sc, b, nm, size, pos, "plastic_grey")
    # Control strip.
    box(sc, b, "ControlStrip", (0.48, 0.05, 0.003), (0, 0.068, 0.2215), "plastic_grey")
    for i in range(10):
        box(sc, b, "Grille%d" % i, (0.004, 0.034, 0.002), (-0.21 + i * 0.012, 0.068, 0.2235), cab)
    box(sc, b, "Badge", (0.06, 0.009, 0.0015), (0, 0.068, 0.2235), "metal_chrome")
    for i in range(4):
        box(sc, b, "Button%d" % i, (0.012, 0.008, 0.005), (0.07 + i * 0.018, 0.068, 0.2235), cab)
    box(sc, b, "PowerButton", (0.03, 0.014, 0.008), (0.19, 0.068, 0.2245), cab)
    sphere(sc, b, "LedOn", 0.0028, 0.0056, (0.222, 0.068, 0.2232), "fx:led_red", visible=False, segs=8, rings=4)
    sphere(sc, b, "LedOff", 0.0028, 0.0056, (0.222, 0.068, 0.2232), "fx:led_dark", segs=8, rings=4)
    for i, (fx, fz) in enumerate(((-0.2, 0.17), (0.2, 0.17), (-0.18, -0.02), (0.18, -0.02))):
        cyl(sc, b, "Foot%d" % i, 0.015, 0.016, 0.015, (fx, 0.0075, fz), "rubber_black", segs=10)
    # Rabbit ears.
    box(sc, b, "AntennaBase", (0.09, 0.022, 0.06), (0, 0.476, 0.12), cab)
    for side, sx in (("L", -1), ("R", 1)):
        d = (sx * math.sin(math.radians(28)), math.cos(math.radians(28)) * math.cos(math.radians(12)), -math.cos(math.radians(28)) * math.sin(math.radians(12)))
        L = 0.46
        p = (sx * 0.02 + d[0] * L / 2, 0.487 + d[1] * L / 2, 0.12 + d[2] * L / 2)
        cyl(sc, b, "Ear" + side, 0.0022, 0.003, L, p, "metal_chrome", rot=(-12, 0, -sx * 28), segs=8)
        sphere(sc, b, "EarTip" + side, 0.0042, 0.0084, (sx * 0.02 + d[0] * L, 0.487 + d[1] * L, 0.12 + d[2] * L), "metal_chrome", segs=8, rings=4)
    spill = sc.node("Spill", "SpotLight3D", b, {
        "transform": XF((0, scr_y, 0.26), rot=(0, 180, 0)), "light_color": C(0.78, 0.84, 1.0), "light_energy": 1.4,
        "shadow_enabled": True, "spot_range": 4.5, "spot_angle": 68.0, "spot_attenuation": 1.2, "light_size": 0.3,
        "visible": False})
    col_box(sc, b, "Shape", (0.52, 0.47, 0.47), (0, 0.235, 0.0))
    comp(sc, b, "Power", DEVICE, {
        "display_name": "Television", "on_prompt": "Turn on", "off_prompt": "Turn off",
        "targets": NPS(["../../Screen"]), "show_when_on": NPS(["../LedOn"]), "show_when_off": NPS(["../LedOff"]),
        "moving_part": NP("../PowerButton"), "on_offset": V3(0, 0, -0.004), "move_time": 0.06,
        "on_sound": SN("tv_on"), "off_sound": SN("tv_off"), "loop_sound": SN("tv_static"),
        "loop_volume_db": -10.0, "loop_delay": 0.45, "cooldown": 0.5,
        "observations": STRS(["Nothing but snow.", "The glass crackles with static when I lean in."]),
    })
    comp(sc, ".", "Screen", F + "components/crt_screen.gd", {
        "screen_mesh": NP("../Body/ScreenStatic"), "lights": NPS(["../Body/Spill"]), "flicker": 0.32, "rate": 20.0})
    sc.write("fixtures/tv_crt.tscn")


def build_vcr():
    """Front-loading VHS deck, 0.43 x 0.09 x 0.30. Origin bottom centre; front +Z."""
    sc = Scene("Vcr")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    box(sc, b, "Case", (0.43, 0.084, 0.30), (0, 0.047, 0), "plastic_black")
    box(sc, b, "Lid", (0.426, 0.004, 0.296), (0, 0.091, -0.002), "plastic_black")
    box(sc, b, "Fascia", (0.428, 0.082, 0.005), (0, 0.047, 0.1525), "plastic_grey")
    box(sc, b, "SlotRecess", (0.196, 0.034, 0.002), (-0.06, 0.059, 0.1555), "plastic_black")
    box(sc, b, "Trim", (0.40, 0.0016, 0.0008), (0, 0.037, 0.1554), "metal_chrome")
    box(sc, b, "DisplayWindow", (0.115, 0.03, 0.002), (0.13, 0.063, 0.1555), "fx:vfd_window")
    sc.node("Clock", "Label3D", b, {
        "transform": XF((0.13, 0.062, 0.1573)), "pixel_size": 0.0006, "text": "12:00", "font_size": 34,
        "outline_size": 0, "modulate": C(0.45, 1.0, 0.86), "shaded": False, "double_sided": False,
        "no_depth_test": False, "fixed_size": False})
    for i in range(6):
        box(sc, b, "Button%d" % i, (0.013, 0.006, 0.004), (0.083 + i * 0.019, 0.029, 0.1565), "plastic_black")
    box(sc, b, "PowerButton", (0.024, 0.011, 0.005), (-0.188, 0.03, 0.1565), "plastic_black")
    box(sc, b, "EjectButton", (0.016, 0.007, 0.004), (0.06, 0.063, 0.1565), "plastic_black")
    for i, (fx, fz) in enumerate(((-0.19, 0.12), (0.19, 0.12), (-0.19, -0.12), (0.19, -0.12))):
        cyl(sc, b, "Foot%d" % i, 0.012, 0.012, 0.005, (fx, 0.0025, fz), "rubber_black", segs=10)
    col_box(sc, b, "Shape", (0.43, 0.093, 0.305), (0, 0.0465, 0))
    comp(sc, b, "Power", DEVICE, {
        "display_name": "VCR", "on_prompt": "Turn on", "off_prompt": "Turn off",
        "targets": NPS(["../../Display"]),
        "moving_part": NP("../PowerButton"), "on_offset": V3(0, 0, -0.002), "move_time": 0.05,
        "on_sound": SN("button_press"), "off_sound": SN("button_press"),
        "observations": STRS(["It whirs, then nothing. There's no tape in it."]),
    })
    flap = anim_body(sc, ".", "Flap", LAYER_INTERACT, pos=(-0.06, 0.0755, 0.1565))
    box(sc, flap, "FlapMesh", (0.19, 0.03, 0.003), (0, -0.015, 0.0015), "plastic_black")
    box(sc, flap, "FlapLine", (0.19, 0.0012, 0.0006), (0, -0.004, 0.0032), "plastic_grey")
    col_box(sc, flap, "Shape", (0.19, 0.03, 0.008), (0, -0.015, 0.004))
    comp(sc, flap, "Flap", HINGED, {
        "display_name": "Tape slot", "open_prompt": "Push the flap", "close_prompt": "Let go",
        "axis": V3(1, 0, 0), "open_angle_degrees": 72.0, "open_duration": 0.18, "close_duration": 0.12,
        "open_profile": SMOOTH, "close_profile": LATCH, "stop_bump": 0.03, "auto_close_after": 0.7,
        "open_sound": SN("button_press"), "close_sound": SN("thud_soft"), "sound_volume_db": -6.0,
        "block_mask": 0,
        "observations": STRS(["Empty. No tape inside.", "The flap snaps back on its spring."]),
    })
    comp(sc, ".", "Display", F + "components/vfd_display.gd", {"label": NP("../Body/Clock")})
    sc.write("fixtures/vcr.tscn")


# =============================================================================
# Casework
# =============================================================================

def bail_pull(sc, parent, prefix, x, y, z, mat="metal_brass"):
    box(sc, parent, prefix + "Plate", (0.10, 0.026, 0.002), (x, y, z + 0.001), mat)
    for i, px in enumerate((-0.038, 0.038)):
        cyl(sc, parent, prefix + "Post%d" % i, 0.003, 0.004, 0.012, (x + px, y + 0.004, z + 0.007), mat, rot=(90, 0, 0), segs=8)
    cyl(sc, parent, prefix + "Bail", 0.0034, 0.0034, 0.082, (x, y - 0.007, z + 0.014), mat, rot=(0, 0, 90), segs=8)


def d_pull(sc, parent, prefix, x, y, z, vertical=False, mat="metal_dark", span=0.076):
    for i, s in enumerate((-span / 2, span / 2)):
        p = (x, y + s, z + 0.012) if vertical else (x + s, y, z + 0.012)
        cyl(sc, parent, prefix + "Post%d" % i, 0.0035, 0.0035, 0.024, p, mat, rot=(90, 0, 0), segs=8)
    cyl(sc, parent, prefix + "Bar", 0.0045, 0.0045, span + 0.012, (x, y, z + 0.026), mat, rot=(0, 0, 0) if vertical else (0, 0, 90), segs=10)


def drawer(sc, parent, name, pos, ow, oh, depth, travel, front_mat, box_mat, pull, display, lines, front_t=0.02, overlay=-0.003, liner="paper_yellowed"):
    """Drawer body origin: centre-bottom of the opening, on the case's front plane.
    overlay < 0 = inset with a gap; > 0 = overlay past the opening."""
    b = anim_body(sc, parent, name, SOLID_INTERACT, pos=pos)
    fw, fh = ow + 2 * overlay, oh + 2 * overlay
    zf = front_t / 2 if overlay > 0 else -front_t / 2
    box(sc, b, "Front", (fw, fh, front_t), (0, oh / 2, zf), front_mat)
    zface = zf + front_t / 2
    bh = oh - 0.045
    bw = ow - 0.03
    z0 = zf - front_t / 2
    box(sc, b, "SideL", (0.012, bh, depth), (-bw / 2 + 0.006, 0.012 + bh / 2, z0 - depth / 2), box_mat)
    box(sc, b, "SideR", (0.012, bh, depth), (bw / 2 - 0.006, 0.012 + bh / 2, z0 - depth / 2), box_mat)
    box(sc, b, "Back", (bw, bh, 0.012), (0, 0.012 + bh / 2, z0 - depth + 0.006), box_mat)
    box(sc, b, "Bottom", (bw, 0.005, depth), (0, 0.0125, z0 - depth / 2), box_mat)
    box(sc, b, "Liner", (bw - 0.026, 0.0012, depth - 0.016), (0, 0.0156, z0 - depth / 2), liner)
    pull(sc, b, "Pull", 0, oh / 2 + 0.005, zface)
    col_box(sc, b, "Shape", (fw, fh, depth + front_t), (0, oh / 2, z0 - depth / 2 + front_t / 2))
    comp(sc, b, "Drawer", SLIDING, {
        "display_name": display, "axis": V3(0, 0, 1), "distance": travel,
        "open_duration": 0.42, "close_duration": 0.36, "open_profile": LATCH, "close_profile": LATCH,
        "stop_bump": 0.012, "open_sound": SN("drawer_open"), "close_sound": SN("drawer_close"),
        "observations": STRS(lines),
    })
    return b


def build_dresser():
    """70s six-drawer... (here: two half-width over two full) dresser 1.14 x 0.46 x 0.80.
    Origin: floor, centre of the back face; front toward +Z."""
    W, D, H = 1.14, 0.46, 0.80
    sc = Scene("DresserDrawers")
    c = static_body(sc, ".", "Carcass", SOLID_INTERACT)
    m = "wood_medium"
    box(sc, c, "Top", (W + 0.03, 0.025, D + 0.015), (0, H - 0.0125, (D + 0.015) / 2), m)
    box(sc, c, "TopEdge", (W + 0.03, 0.008, 0.004), (0, H - 0.029, D + 0.013), "wood_dark")
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, c, "Side" + side, (0.02, 0.715, D), (sx * (W / 2 - 0.01), 0.0575 + 0.3575 + 0.002, D / 2), m)
    box(sc, c, "Plinth", (W - 0.02, 0.06, D - 0.02), (0, 0.03, (D - 0.02) / 2), "wood_dark")
    box(sc, c, "Bottom", (W - 0.04, 0.015, D), (0, 0.0675, D / 2), m)
    box(sc, c, "Back", (W - 0.04, 0.715, 0.006), (0, 0.4175, 0.003), "wood_light")
    rails = (0.30, 0.543)
    for i, ry_ in enumerate(rails):
        box(sc, c, "Rail%d" % i, (W - 0.04, 0.02, 0.02), (0, ry_, D - 0.01), m)
        box(sc, c, "Dust%d" % i, (W - 0.04, 0.006, D - 0.03), (0, ry_, (D - 0.03) / 2 + 0.006), "wood_light")
    box(sc, c, "Divider", (0.02, 0.222, D - 0.006), (0, 0.664, (D - 0.006) / 2 + 0.006), m)
    col_box(sc, c, "ShapeTop", (W + 0.03, 0.025, D + 0.015), (0, H - 0.0125, (D + 0.015) / 2))
    col_box(sc, c, "ShapeSideL", (0.02, 0.74, D), (-(W / 2 - 0.01), 0.41, D / 2))
    col_box(sc, c, "ShapeSideR", (0.02, 0.74, D), ((W / 2 - 0.01), 0.41, D / 2))
    col_box(sc, c, "ShapeBase", (W - 0.02, 0.075, D - 0.02), (0, 0.0375, (D - 0.02) / 2))
    col_box(sc, c, "ShapeBack", (W - 0.04, 0.715, 0.006), (0, 0.4175, 0.003))
    look(sc, c, "Dresser", ["Rings on the top where glasses sat.", "The veneer is lifting at one corner."])
    iw = W - 0.04
    rows = [(0.075, 0.29), (0.31, 0.533), (0.553, 0.775)]
    lines_set = [
        ["Empty. Lined with old shelf paper."],
        ["Empty. It smells like cedar and dust."],
        ["Nothing in it. The paper has a pattern of little roses."],
        ["Empty. The runners squeak."],
    ]

    def front_with_inlay(name):
        return name

    k = 0
    for r, (y0, y1) in enumerate(rows):
        oh = y1 - y0
        cols = [(-iw / 4 - 0.005, iw / 2 - 0.01), (iw / 4 + 0.005, iw / 2 - 0.01)] if r == 2 else [(0, iw)]
        for ci, (cx, ow) in enumerate(cols):
            name = "Drawer%d" % k
            bdy = drawer(sc, ".", name, (cx, y0, D), ow, oh, 0.40, 0.30, m, "wood_light",
                         lambda s, p, pre, x, y, z: bail_pull(s, p, pre, x, y, z), "Drawer", lines_set[k % 4])
            box(sc, bdy, "Inlay", (ow - 0.07, oh - 0.07, 0.003), (0, oh / 2, 0.0015), "wood_dark")
            box(sc, bdy, "InlayFace", (ow - 0.08, oh - 0.08, 0.007), (0, oh / 2, 0.0035), m)
            k += 1
    sc.write("fixtures/dresser_drawers.tscn")


def cab_door(sc, name, hinge_x, y0, w, h, z, left_hinge, angle, display, lines, mat="wood_oak_cabinet", groove="wood_dark", pull_y=None, open_sound="cabinet_open", close_sound="cabinet_close"):
    """Overlay frame-and-panel cabinet door. Body origin on the hinge line at the
    door's back face; the door extends toward +X (left hinge) or -X (right hinge)."""
    s = 1 if left_hinge else -1
    b = anim_body(sc, ".", name, SOLID_INTERACT, pos=(hinge_x, y0, z))
    t = 0.019
    cx = s * w / 2
    box(sc, b, "Slab", (w, h, t), (cx, h / 2, t / 2), mat)
    m = 0.062
    box(sc, b, "Groove", (w - 2 * m + 0.012, h - 2 * m + 0.012, 0.001), (cx, h / 2, t + 0.0005), groove)
    box(sc, b, "Panel", (w - 2 * m, h - 2 * m, 0.006), (cx, h / 2, t + 0.003), mat)
    box(sc, b, "PanelBevel", (w - 2 * m - 0.03, h - 2 * m - 0.03, 0.003), (cx, h / 2, t + 0.0065), mat)
    for i, hy in enumerate((0.07, h - 0.07)):
        box(sc, b, "HingeLeaf%d" % i, (0.014, 0.05, 0.002), (s * 0.008, hy, t + 0.001), "metal_dark")
        cyl(sc, b, "HingeKnuckle%d" % i, 0.0035, 0.0035, 0.05, (-s * 0.001, hy, t + 0.0005), "metal_dark", segs=8)
    py = pull_y if pull_y is not None else (h - 0.09 if h > 0.4 else h / 2)
    d_pull(sc, b, "Pull", s * (w - 0.032), py, t, vertical=True)
    col_box(sc, b, "Shape", (w, h, t), (cx, h / 2, t / 2))
    comp(sc, b, "Hinge", HINGED, {
        "display_name": display, "axis": V3(0, 1, 0), "open_angle_degrees": angle,
        "open_duration": 0.55, "close_duration": 0.42, "open_profile": PUSH, "close_profile": LATCH,
        "stop_bump": 0.006, "open_sound": SN(open_sound), "close_sound": SN(close_sound),
        "observations": STRS(lines),
    })
    return b


def base_cabinet(sc, W=0.91, sink=False):
    """Base cabinet carcass, face frame, countertop. Origin floor, back centre; front +Z."""
    c = static_body(sc, ".", "Carcass", SOLID_INTERACT)
    oak, inner = "wood_oak_cabinet", "wood_light"
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, c, "Side" + side, (0.018, 0.872, 0.59), (sx * (W / 2 - 0.009), 0.436, 0.295), oak)
    box(sc, c, "ToeKick", (W - 0.036, 0.10, 0.012), (0, 0.05, 0.528), "wood_dark")
    box(sc, c, "Deck", (W - 0.036, 0.018, 0.59), (0, 0.109, 0.295), inner)
    box(sc, c, "Back", (W - 0.036, 0.754, 0.006), (0, 0.118 + 0.377, 0.003), inner)
    if not sink:
        box(sc, c, "Shelf", (W - 0.036, 0.018, 0.30), (0, 0.40, 0.31), inner)
    # Face frame.
    ff = 0.6
    box(sc, c, "StileL", (0.038, 0.772, 0.02), (-(W / 2 - 0.019), 0.486, ff), oak)
    box(sc, c, "StileR", (0.038, 0.772, 0.02), ((W / 2 - 0.019), 0.486, ff), oak)
    box(sc, c, "Mullion", (0.038, 0.528, 0.02), (0, 0.402, ff), oak)
    box(sc, c, "RailTop", (W - 0.076, 0.038, 0.02), (0, 0.853, ff), oak)
    box(sc, c, "RailMid", (W - 0.076, 0.038, 0.02), (0, 0.685, ff), oak)
    box(sc, c, "RailBottom", (W - 0.076, 0.038, 0.02), (0, 0.119, ff), oak)
    # Countertop.
    ctop = "laminate_formica"
    if not sink:
        box(sc, c, "Counter", (W, 0.038, 0.635), (0, 0.891, 0.3175), ctop)
        col_box(sc, c, "ShapeCounter", (W, 0.038, 0.635), (0, 0.891, 0.3175))
    box(sc, c, "CounterEdge", (W, 0.04, 0.003), (0, 0.89, 0.6365), "metal_chrome")
    box(sc, c, "Backsplash", (W, 0.10, 0.012), (0, 0.96, 0.006), ctop)
    col_box(sc, c, "ShapeSideL", (0.018, 0.872, 0.59), (-(W / 2 - 0.009), 0.436, 0.295))
    col_box(sc, c, "ShapeSideR", (0.018, 0.872, 0.59), ((W / 2 - 0.009), 0.436, 0.295))
    col_box(sc, c, "ShapeDeck", (W - 0.036, 0.118, 0.59), (0, 0.059, 0.295))
    col_box(sc, c, "ShapeBack", (W - 0.036, 0.754, 0.006), (0, 0.495, 0.003))
    col_box(sc, c, "ShapeFrameTop", (W, 0.21, 0.02), (0, 0.767, ff))
    # Frame-side hinge leaves (70s exposed hinges).
    for side, sx in (("L", -1), ("R", 1)):
        for i, hy in enumerate((0.125 + 0.07, 0.125 + 0.553 - 0.07)):
            box(sc, c, "FrameLeaf%s%d" % (side, i), (0.012, 0.05, 0.002), (sx * (W / 2 - 0.0075), hy, 0.611), "metal_dark")
    # Doors.
    dw, dh = 0.423, 0.553
    hx = W / 2 - 0.0253
    lines = (["The pipes under here are sweating.", "It smells like old damp wood."] if sink else
             ["Empty shelves. Shelf paper, and crumbs in the corners.", "The hinge squeals a little."])
    cab_door(sc, "DoorL", -hx, 0.1253, dw, dh, 0.61, True, -105.0, "Cabinet", lines)
    cab_door(sc, "DoorR", hx, 0.1253, dw, dh, 0.61, False, 105.0, "Cabinet", lines[::-1])
    if sink:
        box(sc, c, "FalseFront", (W - 0.051, 0.155, 0.019), (0, 0.769, 0.6195), oak)
        box(sc, c, "FalseFrontPanel", (W - 0.18, 0.06, 0.004), (0, 0.769, 0.631), oak)
        d_pull(sc, c, "FalsePull", 0, 0.769, 0.629)
        look(sc, c, "Sink", ["A rust ring around the drain.", "The counter is warm where the sun lands on it."])
    else:
        drawer(sc, ".", "Drawer", (0, 0.704, 0.61), 0.834, 0.13, 0.48, 0.38, oak, inner,
               lambda s, p, pre, x, y, z: d_pull(s, p, pre, x, y, z), "Drawer",
               ["Twist ties, a dead battery, a book of matches.", "Crumbs in the seams."], front_t=0.019, overlay=0.0125)
        look(sc, c, "Counter", ["The laminate is lifting at the seam.", "A burn mark the shape of a pot bottom."])
    return c


def build_kitchen_base():
    sc = Scene("KitchenCabinetBase")
    base_cabinet(sc)
    sc.write("fixtures/kitchen_cabinet_base.tscn")


def build_kitchen_wall():
    """Upper cabinet 0.76 x 0.76 x 0.305. Origin: bottom of the case, centre of the back
    (the mounting point; hang it at 1.37 m over a counter)."""
    W, H, D = 0.76, 0.76, 0.305
    sc = Scene("KitchenCabinetWall")
    c = static_body(sc, ".", "Carcass", SOLID_INTERACT)
    oak, inner = "wood_oak_cabinet", "wood_light"
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, c, "Side" + side, (0.018, H, D - 0.02), (sx * (W / 2 - 0.009), H / 2, (D - 0.02) / 2), oak)
    box(sc, c, "Bottom", (W - 0.036, 0.018, D - 0.02), (0, 0.009 + 0.018, (D - 0.02) / 2), oak)
    box(sc, c, "Top", (W - 0.036, 0.018, D - 0.02), (0, H - 0.009, (D - 0.02) / 2), inner)
    box(sc, c, "Back", (W - 0.036, H, 0.006), (0, H / 2, 0.003), inner)
    for i, sy in enumerate((0.27, 0.51)):
        box(sc, c, "Shelf%d" % i, (W - 0.036, 0.016, D - 0.04), (0, sy, (D - 0.04) / 2 + 0.006), inner)
        box(sc, c, "ShelfPaper%d" % i, (W - 0.05, 0.001, D - 0.06), (0, sy + 0.0085, (D - 0.06) / 2 + 0.01), "paper_yellowed")
    ff = D - 0.01
    box(sc, c, "StileL", (0.038, H, 0.02), (-(W / 2 - 0.019), H / 2, ff), oak)
    box(sc, c, "StileR", (0.038, H, 0.02), ((W / 2 - 0.019), H / 2, ff), oak)
    box(sc, c, "Mullion", (0.038, H - 0.076, 0.02), (0, H / 2, ff), oak)
    box(sc, c, "RailTop", (W - 0.076, 0.038, 0.02), (0, H - 0.019, ff), oak)
    box(sc, c, "RailBottom", (W - 0.076, 0.038, 0.02), (0, 0.019, ff), oak)
    box(sc, c, "Valance", (W, 0.03, 0.02), (0, -0.0, ff + 0.0), oak)
    col_box(sc, c, "ShapeSides", (W, H, 0.02), (0, H / 2, 0.003))
    col_box(sc, c, "ShapeSideL", (0.018, H, D - 0.02), (-(W / 2 - 0.009), H / 2, (D - 0.02) / 2))
    col_box(sc, c, "ShapeSideR", (0.018, H, D - 0.02), ((W / 2 - 0.009), H / 2, (D - 0.02) / 2))
    col_box(sc, c, "ShapeBottom", (W, 0.036, D), (0, 0.018, D / 2))
    col_box(sc, c, "ShapeTop", (W, 0.018, D), (0, H - 0.009, D / 2))
    look(sc, c, "Cabinet", ["Grease has gone sticky along the bottom edge."])
    dw, dh = 0.348, H - 0.076 + 0.025
    hx = W / 2 - 0.0253
    for side, sx in (("L", -1), ("R", 1)):
        for i, hy in enumerate((0.0255 + 0.07, 0.0255 + dh - 0.07)):
            box(sc, c, "FrameLeaf%s%d" % (side, i), (0.012, 0.05, 0.002), (sx * (W / 2 - 0.0075), hy, D + 0.001), "metal_dark")
    lines = ["Empty. A ring on the shelf paper where a jar stood.", "The shelf paper is curling at the front."]
    cab_door(sc, "DoorL", -hx, 0.0255, dw, dh, D, True, -105.0, "Cabinet", lines, pull_y=0.09)
    cab_door(sc, "DoorR", hx, 0.0255, dw, dh, D, False, 105.0, "Cabinet", lines[::-1], pull_y=0.09)
    sc.write("fixtures/kitchen_cabinet_wall.tscn")


# =============================================================================
# Appliances
# =============================================================================

def build_fridge():
    """Top-freezer refrigerator, harvest gold, 0.76 x 1.66, 0.70 deep + 0.065 doors.
    Origin: floor, centre of the back. Doors hinge on the right (+X)."""
    sc = Scene("Fridge")
    c = static_body(sc, ".", "Cabinet", SOLID_INTERACT)
    g, liner = "appliance_harvest_gold", "plastic_white"
    W, D = 0.76, 0.70
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, c, "Side" + side, (0.012, 1.56, D), (sx * (W / 2 - 0.006), 0.88, D / 2), g)
        box(sc, c, "Liner" + side, (0.038, 0.98, D - 0.06), (sx * 0.349, 0.61, (D - 0.06) / 2 + 0.06), liner)
        box(sc, c, "FzLiner" + side, (0.038, 0.44, D - 0.06), (sx * 0.349, 1.39, (D - 0.06) / 2 + 0.06), liner)
    box(sc, c, "Top", (W, 0.012, D), (0, 1.654, D / 2), g)
    box(sc, c, "Back", (W - 0.024, 1.56, 0.012), (0, 0.88, 0.006), "metal_dark")
    box(sc, c, "Base", (W, 0.10, D - 0.04), (0, 0.05, (D - 0.04) / 2), "plastic_black")
    box(sc, c, "Grille", (W - 0.04, 0.07, 0.004), (0, 0.05, D - 0.038), "metal_dark")
    for i in range(6):
        box(sc, c, "GrilleSlat%d" % i, (W - 0.06, 0.005, 0.004), (0, 0.022 + i * 0.011, D - 0.034), g)
    box(sc, c, "LinerBottom", (W - 0.024, 0.05, D - 0.06), (0, 0.125, (D - 0.06) / 2 + 0.06), liner)
    box(sc, c, "LinerBack", (0.66, 0.98, 0.05), (0, 0.61, 0.037), liner)
    box(sc, c, "FzLinerBack", (0.66, 0.44, 0.05), (0, 1.39, 0.037), liner)
    box(sc, c, "FzLinerTop", (W - 0.024, 0.036, D - 0.06), (0, 1.63, (D - 0.06) / 2 + 0.06), liner)
    box(sc, c, "Divider", (W - 0.024, 0.09, D - 0.012), (0, 1.125, (D - 0.012) / 2 + 0.012), liner)
    box(sc, c, "DividerFace", (W, 0.036, 0.004), (0, 1.14, D - 0.002), g)
    # Wire shelves.
    for si, sy in enumerate((0.52, 0.80)):
        cyl(sc, c, "Shelf%dFront" % si, 0.004, 0.004, 0.66, (0, sy, D - 0.04), "metal_chrome", rot=(0, 0, 90), segs=8)
        cyl(sc, c, "Shelf%dBack" % si, 0.003, 0.003, 0.66, (0, sy, 0.08), "metal_chrome", rot=(0, 0, 90), segs=8)
        for ri in range(10):
            x = -0.315 + ri * 0.07
            cyl(sc, c, "Shelf%dRod%d" % (si, ri), 0.0022, 0.0022, D - 0.12, (x, sy + 0.002, (D - 0.12) / 2 + 0.08), "metal_chrome", rot=(90, 0, 0), segs=6)
    # Crispers.
    box(sc, c, "CrisperLid", (0.66, 0.012, 0.58), (0, 0.38, 0.36), "glass_dusty")
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, c, "Crisper" + side, (0.315, 0.20, 0.54), (sx * 0.165, 0.255, 0.36), "glass_dusty")
        box(sc, c, "CrisperHandle" + side, (0.12, 0.02, 0.012), (sx * 0.165, 0.33, 0.636), "plastic_white")
    box(sc, c, "BakingSoda", (0.07, 0.10, 0.045), (-0.22, 0.86, 0.22), "fx:baking_soda_box", rot=(0, 12, 0))
    box(sc, c, "IceTray", (0.11, 0.028, 0.29), (-0.14, 1.184, 0.34), "plastic_white")
    box(sc, c, "Frost", (0.66, 0.006, 0.6), (0, 1.172, 0.36), "ceramic_white")
    box(sc, c, "LightCover", (0.11, 0.028, 0.055), (0.2, 1.064, 0.12), "fx:glass_frosted", cast=SHADOW_OFF)
    omni(sc, c, "InteriorLamp", (0.2, 1.03, 0.16), 0.9, 1.7, (1.0, 0.82, 0.62), True, 0.03, 1.0)
    col_box(sc, c, "ShapeSideL", (0.04, 1.66, D), (-(W / 2 - 0.02), 0.83, D / 2))
    col_box(sc, c, "ShapeSideR", (0.04, 1.66, D), ((W / 2 - 0.02), 0.83, D / 2))
    col_box(sc, c, "ShapeTop", (W, 0.05, D), (0, 1.635, D / 2))
    col_box(sc, c, "ShapeBase", (W, 0.15, D), (0, 0.075, D / 2))
    col_box(sc, c, "ShapeBack", (W, 1.66, 0.06), (0, 0.83, 0.03))
    col_box(sc, c, "ShapeDivider", (W, 0.09, D), (0, 1.125, D / 2))
    look(sc, c, "Refrigerator", ["It hums, then clicks, then hums.", "The side is warm. That's the coils."])
    comp(sc, ".", "InteriorLight", POWERED, {"lights": NPS(["../Cabinet/InteriorLamp"]), "bulb_meshes": NPS(["../Cabinet/LightCover"]),
                                              "bulb_emission_energy": 2.5, "warm_up_time": 0.05, "temperature_kelvin": 2800.0})
    sc.node("Hum", "Node3D", ".", {"transform": XF((0, 0.08, 0.1)), "script": sc.ext(LOOP, "Script"),
                                   "sound_id": SN("fridge_hum"), "autoplay_loop": True, "volume_db": -14.0})
    for name, y0, h, lines, disp, shelves, handle_y in (
        ("FreshDoor", 0.10, 1.03, ["Cold air spills out over my feet.", "Nothing in here but a box of baking soda."], "Refrigerator", (0.18, 0.46, 0.76), (0.62, 0.92)),
        ("FreezerDoor", 1.15, 0.51, ["Frost on the walls, thick as a finger.", "An ice tray with no ice in it."], "Freezer", (0.2,), (0.08, 0.30)),
    ):
        b = anim_body(sc, ".", name, SOLID_INTERACT, pos=(W / 2, y0, D))
        box(sc, b, "Outer", (W, h, 0.055), (-W / 2, h / 2, 0.0375), g)
        box(sc, b, "Inner", (0.68, h - 0.08, 0.01), (-W / 2, h / 2, 0.005), liner)
        box(sc, b, "GasketTop", (0.72, 0.02, 0.012), (-W / 2, h - 0.03, 0.004), "rubber_black")
        box(sc, b, "GasketBottom", (0.72, 0.02, 0.012), (-W / 2, 0.03, 0.004), "rubber_black")
        box(sc, b, "GasketL", (0.02, h - 0.04, 0.012), (-W / 2 - 0.35, h / 2, 0.004), "rubber_black")
        box(sc, b, "GasketR", (0.02, h - 0.04, 0.012), (-W / 2 + 0.35, h / 2, 0.004), "rubber_black")
        for i, sy in enumerate(shelves):
            box(sc, b, "Bin%d" % i, (0.60, 0.012, 0.085), (-W / 2, sy, -0.0425), liner)
            box(sc, b, "BinRail%d" % i, (0.60, 0.05, 0.005), (-W / 2, sy + 0.025, -0.083), liner)
        for i, py in enumerate(handle_y):
            box(sc, b, "HandlePost%d" % i, (0.022, 0.022, 0.035), (-W + 0.045, py, 0.0825), "metal_chrome")
        box(sc, b, "HandleGrip", (0.026, abs(handle_y[1] - handle_y[0]) + 0.05, 0.02), (-W + 0.045, sum(handle_y) / 2, 0.11), "metal_chrome")
        box(sc, b, "HandleInsert", (0.012, abs(handle_y[1] - handle_y[0]) + 0.03, 0.002), (-W + 0.045, sum(handle_y) / 2, 0.1205), "wood_medium")
        col_box(sc, b, "Shape", (W, h, 0.065), (-W / 2, h / 2, 0.0325))
        props = {
            "display_name": disp, "axis": V3(0, 1, 0), "open_angle_degrees": 110.0,
            "open_duration": 1.0, "close_duration": 0.7, "open_profile": PUSH, "close_profile": LATCH,
            "stop_bump": 0.005, "open_sound": SN("fridge_open"), "close_sound": SN("fridge_close"),
            "observations": STRS(lines),
        }
        if name == "FreshDoor":
            props["lit_while_open"] = NPS(["../../InteriorLight"])
        comp(sc, b, "Hinge", HINGED, props)
    sc.write("fixtures/fridge.tscn")


def build_sink():
    """Sink base cabinet with countertop, stainless bowl and a two-handle faucet.
    Origin floor, back centre; front +Z. 0.91 wide like the base cabinet."""
    sc = Scene("KitchenSink")
    c = base_cabinet(sc, sink=True)
    W = 0.91
    ctop = "laminate_formica"
    hx0, hx1, hz0, hz1 = -0.29, 0.29, 0.13, 0.55
    y = 0.891
    box(sc, c, "CounterBack", (W, 0.038, hz0), (0, y, hz0 / 2), ctop)
    box(sc, c, "CounterFront", (W, 0.038, 0.635 - hz1), (0, y, (hz1 + 0.635) / 2), ctop)
    box(sc, c, "CounterL", (hx0 + W / 2, 0.038, hz1 - hz0), ((hx0 - W / 2) / 2, y, (hz0 + hz1) / 2), ctop)
    box(sc, c, "CounterR", (W / 2 - hx1, 0.038, hz1 - hz0), ((hx1 + W / 2) / 2, y, (hz0 + hz1) / 2), ctop)
    col_box(sc, c, "ShapeCounterBack", (W, 0.038, hz0), (0, y, hz0 / 2))
    col_box(sc, c, "ShapeCounterFront", (W, 0.038, 0.635 - hz1), (0, y, (hz1 + 0.635) / 2))
    col_box(sc, c, "ShapeCounterL", (hx0 + W / 2, 0.038, hz1 - hz0), ((hx0 - W / 2) / 2, y, (hz0 + hz1) / 2))
    col_box(sc, c, "ShapeCounterR", (W / 2 - hx1, 0.038, hz1 - hz0), ((hx1 + W / 2) / 2, y, (hz0 + hz1) / 2))
    st = "metal_chrome"
    depth = 0.19
    bot = 0.91 - depth
    zc = (hz0 + hz1) / 2
    box(sc, c, "BowlBottom", (hx1 - hx0, 0.004, hz1 - hz0), (0, bot, zc), st)
    box(sc, c, "BowlL", (0.004, depth, hz1 - hz0), (hx0, bot + depth / 2, zc), st)
    box(sc, c, "BowlR", (0.004, depth, hz1 - hz0), (hx1, bot + depth / 2, zc), st)
    box(sc, c, "BowlBack", (hx1 - hx0, depth, 0.004), (0, bot + depth / 2, hz0), st)
    box(sc, c, "BowlFront", (hx1 - hx0, depth, 0.004), (0, bot + depth / 2, hz1), st)
    col_box(sc, c, "ShapeBowl", (hx1 - hx0, 0.01, hz1 - hz0), (0, bot, zc))
    for nm, size, pos in (
        ("RimBack", (hx1 - hx0 + 0.024, 0.004, 0.012), (0, 0.912, hz0 - 0.006)),
        ("RimFront", (hx1 - hx0 + 0.024, 0.004, 0.012), (0, 0.912, hz1 + 0.006)),
        ("RimL", (0.012, 0.004, hz1 - hz0), (hx0 - 0.006, 0.912, zc)),
        ("RimR", (0.012, 0.004, hz1 - hz0), (hx1 + 0.006, 0.912, zc)),
    ):
        box(sc, c, nm, size, pos, st)
    cyl(sc, c, "Drain", 0.045, 0.045, 0.004, (0, bot + 0.003, zc + 0.02), st)
    cyl(sc, c, "DrainBasket", 0.03, 0.03, 0.002, (0, bot + 0.0055, zc + 0.02), "metal_dark")
    sphere(sc, c, "RustRing", 0.05, 0.002, (0, bot + 0.0024, zc + 0.02), "brick_red", scale=(1, 1, 1), segs=20, rings=4)
    cyl(sc, c, "Tailpiece", 0.019, 0.019, 0.24, (0, bot - 0.12, zc + 0.02), st, segs=14)
    sphere(sc, c, "Trap", 0.026, 0.06, (0, bot - 0.245, zc + 0.02), st, segs=14, rings=8)
    cyl(sc, c, "TrapArm", 0.019, 0.019, zc + 0.02, (0, bot - 0.245, (zc + 0.02) / 2), st, rot=(90, 0, 0), segs=14)
    for i, sx in enumerate((-0.1, 0.1)):
        cyl(sc, c, "Supply%d" % i, 0.005, 0.005, 0.5, (sx, 0.55, 0.03), st, segs=8)
        cyl(sc, c, "Valve%d" % i, 0.012, 0.012, 0.04, (sx, 0.30, 0.03), st, rot=(90, 0, 0), segs=10)
        box(sc, c, "ValveHandle%d" % i, (0.028, 0.012, 0.008), (sx, 0.30, 0.055), "plastic_white")
    # Faucet: its own body so it can be aimed at separately.
    fz = 0.065
    f = static_body(sc, ".", "Faucet", LAYER_INTERACT)
    box(sc, f, "DeckPlate", (0.21, 0.018, 0.055), (0, 0.919, fz), st)
    cyl(sc, f, "SpoutBase", 0.02, 0.022, 0.04, (0, 0.948, fz), st)
    spout_len = 0.20
    sx_, sy_ = 0.165, 0.952
    cyl(sc, f, "Spout", 0.011, 0.011, spout_len, (0, sy_, sx_), st, rot=(97.3, 0, 0), segs=14)
    cyl(sc, f, "Aerator", 0.0125, 0.012, 0.02, (0, 0.932, 0.262), st, segs=14)
    cyl(sc, f, "AeratorMesh", 0.009, 0.009, 0.001, (0, 0.9215, 0.262), "metal_dark", segs=12)
    for nm, x, dot in (("HotHandle", -0.08, "brick_red"), ("ColdHandle", 0.08, "fx:index_blue")):
        cyl(sc, f, nm + "Base", 0.016, 0.018, 0.022, (x, 0.939, fz), st)
        h = n3d(sc, f, nm, (x, 0.962, fz))
        box(sc, h, "Cross0", (0.062, 0.013, 0.013), (0, 0, 0), "glass_dusty")
        box(sc, h, "Cross1", (0.013, 0.013, 0.062), (0, 0, 0), "glass_dusty")
        cyl(sc, h, "Hub", 0.011, 0.011, 0.018, (0, 0.002, 0), st, segs=12)
        cyl(sc, h, "Index", 0.006, 0.006, 0.0015, (0, 0.0115, 0), dot, segs=10)
    water_len = 0.9215 - (bot + 0.002)
    cyl(sc, f, "Water", 0.0055, 0.0045, water_len, (0, bot + 0.002 + water_len / 2, 0.262), "fx:water_stream", segs=10, cast=SHADOW_OFF, visible=False, caps=False)
    sphere(sc, f, "Splash", 0.028, 0.007, (0, bot + 0.004, 0.262), "fx:water_stream", segs=14, rings=4, cast=SHADOW_OFF, visible=False)
    col_box(sc, f, "Shape", (0.22, 0.08, 0.25), (0, 0.95, 0.15))
    comp(sc, f, "Tap", DEVICE, {
        "display_name": "Faucet", "on_prompt": "Turn on", "off_prompt": "Turn off",
        "show_when_on": NPS(["../Water", "../Splash"]),
        "moving_part": NP("../ColdHandle"), "on_rotation_degrees": V3(0, 80, 0), "move_time": 0.35,
        "on_sound": SN("faucet_squeak"), "off_sound": SN("faucet_squeak"), "loop_sound": SN("faucet_run"),
        "loop_anchor": NP("../Water"), "loop_volume_db": -8.0, "cooldown": 0.45,
        "observations": STRS(["It runs brown for a second, then clear.", "The water's warm. The pipes sat in the sun all day."]),
    })
    sc.write("fixtures/kitchen_sink.tscn")


def build_telephone():
    """80s push-button desk phone. Origin: bottom centre; keypad faces +Z (toward the user)."""
    sc = Scene("Telephone")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    bg = "plastic_beige"
    box(sc, b, "Base", (0.19, 0.03, 0.22), (0, 0.015, 0), bg)
    prism(sc, b, "Wedge", (0.22, 0.045, 0.19), 1.0, (0, 0.0525, 0), bg, rot=(0, 90, 0))
    slope = math.degrees(math.atan2(0.045, 0.22))

    def surf_y(z):
        return 0.03 + 0.045 * (0.11 - z) / 0.22

    kp = n3d(sc, b, "Keypad", (0, surf_y(0.052), 0.052), rot=(slope, 0, 0))
    box(sc, kp, "Bezel", (0.074, 0.003, 0.094), (0, 0.0015, 0), "plastic_grey")
    keys = 0
    for row in range(4):
        for col in range(3):
            box(sc, kp, "Key%d" % keys, (0.0165, 0.006, 0.0135), ((col - 1) * 0.022, 0.004, (row - 1.5) * 0.021), "plastic_white")
            keys += 1
    card = n3d(sc, b, "NumberCard", (0, surf_y(0.097), 0.097), rot=(slope, 0, 0))
    box(sc, card, "CardWindow", (0.06, 0.0015, 0.016), (0, 0.00075, 0), "glass_dusty")
    box(sc, card, "Card", (0.056, 0.001, 0.012), (0, 0.0003, 0), "paper_white")
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, b, "Horn" + side, (0.036, 0.03, 0.056), (sx * 0.07, 0.077, -0.055), bg)
    pl = n3d(sc, b, "Plungers", (0, 0, -0.055))
    for i, sx in enumerate((-0.036, 0.036)):
        box(sc, pl, "Plunger%d" % i, (0.013, 0.012, 0.013), (sx, 0.084, 0), "plastic_white")
    hs = n3d(sc, b, "Handset", (0, 0.112, -0.055))
    box(sc, hs, "Handle", (0.13, 0.022, 0.036), (0, 0.006, 0), bg)
    box(sc, hs, "HandleTop", (0.14, 0.008, 0.032), (0, 0.019, 0), bg)
    for nm, x in (("Earpiece", 0.087), ("Mouthpiece", -0.087)):
        cyl(sc, hs, nm, 0.026, 0.028, 0.034, (x, -0.003, 0), bg, segs=20)
        cyl(sc, hs, nm + "Face", 0.022, 0.022, 0.001, (x, -0.0205, 0), "plastic_grey", segs=20)
    res_mesh(sc, b, "Cord", F + "meshes/phone_cord.res", (0, 0, 0), bg)
    cyl(sc, b, "LineCord", 0.0022, 0.0022, 0.30, (0.04, 0.003, -0.26), "plastic_grey", rot=(90, 0, 0), segs=6)
    for i, (fx, fz) in enumerate(((-0.08, 0.09), (0.08, 0.09), (-0.08, -0.09), (0.08, -0.09))):
        cyl(sc, b, "Foot%d" % i, 0.008, 0.008, 0.003, (fx, 0.0015, fz), "rubber_black", segs=8)
    col_box(sc, b, "Shape", (0.21, 0.13, 0.22), (0, 0.065, 0))
    comp(sc, b, "Phone", DEVICE, {
        "display_name": "Telephone", "on_prompt": "Pick up", "off_prompt": "Hang up",
        "show_when_off": NPS(["../Handset", "../Cord"]),
        "moving_part": NP("../Plungers"), "on_offset": V3(0, 0.008, 0), "move_time": 0.06,
        "on_sound": SN("phone_pickup"), "off_sound": SN("phone_hangup"), "loop_sound": SN("phone_dial_tone"),
        "loop_volume_db": -14.0, "loop_unit_size": 1.0, "loop_delay": 0.3, "cooldown": 0.5,
        "observations": STRS(["Dial tone.", "The earpiece is warm from sitting in the sun."]),
    })
    sc.write("fixtures/telephone.tscn")


def build_stereo():
    """70s console stereo, 1.52 x 0.66 x 0.43, walnut, lift-up lid over a turntable
    and receiver. Origin floor, back centre; front +Z."""
    W, H, D = 1.52, 0.66, 0.43
    sc = Scene("StereoConsole")
    b = static_body(sc, ".", "Body", SOLID_INTERACT)
    wd = "wood_dark"
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, b, "Side" + side, (0.022, 0.54, D), (sx * (W / 2 - 0.011), 0.39, D / 2), wd)
        box(sc, b, "Top" + side, (0.48, 0.022, D + 0.01), (sx * 0.52, H - 0.011, (D + 0.01) / 2), wd)
        box(sc, b, "SpeakerFrame" + side, (0.48, 0.50, 0.018), (sx * 0.52, 0.39, D - 0.009), wd)
        box(sc, b, "Cloth" + side, (0.42, 0.42, 0.004), (sx * 0.52, 0.39, D + 0.001), "fabric_corduroy_brown")
        for i in range(3):
            box(sc, b, "FretV%s%d" % (side, i), (0.014, 0.42, 0.012), (sx * 0.52 + (i - 1) * 0.12, 0.39, D + 0.007), wd)
            box(sc, b, "FretH%s%d" % (side, i), (0.42, 0.014, 0.012), (sx * 0.52, 0.39 + (i - 1) * 0.12, D + 0.007), wd)
        box(sc, b, "FretRim" + side, (0.43, 0.43, 0.004), (sx * 0.52, 0.39, D - 0.0005), wd)
    box(sc, b, "Bottom", (W - 0.044, 0.02, D - 0.01), (0, 0.13, D / 2), wd)
    box(sc, b, "Back", (W - 0.044, 0.52, 0.01), (0, 0.39, 0.005), "wood_medium")
    box(sc, b, "CentreFront", (0.52, 0.27, 0.02), (0, 0.255, D - 0.01), wd)
    box(sc, b, "CentreLip", (0.52, 0.02, D - 0.01), (0, 0.39 + 0.0, (D - 0.01) / 2), wd)
    box(sc, b, "CentreTrim", (0.48, 0.008, 0.004), (0, 0.33, D + 0.001), "metal_brass")
    box(sc, b, "CentreTrim2", (0.48, 0.008, 0.004), (0, 0.18, D + 0.001), "metal_brass")
    box(sc, b, "WellFront", (0.52, 0.27, 0.02), (0, 0.525, D - 0.01), wd)
    box(sc, b, "WellBack", (0.52, 0.27, 0.02), (0, 0.525, 0.02), wd)
    box(sc, b, "Deck", (0.476, 0.01, D - 0.04), (0, 0.405, D / 2), "plastic_grey")
    for i, (lx, lz) in enumerate(((-0.68, 0.06), (0.68, 0.06), (-0.68, 0.37), (0.68, 0.37))):
        cyl(sc, b, "Leg%d" % i, 0.024, 0.015, 0.12, (lx, 0.06, lz), wd, segs=12)
        cyl(sc, b, "Ferrule%d" % i, 0.016, 0.016, 0.014, (lx, 0.007, lz), "metal_brass", segs=12)
    # Turntable.
    tx, tz = -0.07, 0.255
    cyl(sc, b, "Platter", 0.15, 0.15, 0.018, (tx, 0.419, tz), "metal_chrome", segs=40)
    cyl(sc, b, "Mat", 0.145, 0.145, 0.003, (tx, 0.4295, tz), "rubber_black", segs=40)
    cyl(sc, b, "Spindle", 0.003, 0.003, 0.016, (tx, 0.437, tz), "metal_chrome", segs=8)
    cyl(sc, b, "ArmBase", 0.02, 0.022, 0.025, (0.16, 0.422, 0.33), "metal_chrome", segs=16)
    box(sc, b, "Tonearm", (0.006, 0.006, 0.21), (0.15, 0.44, 0.24), "metal_chrome", rot=(0, 8, 0))
    box(sc, b, "Headshell", (0.016, 0.006, 0.028), (0.135, 0.437, 0.135), "plastic_black", rot=(0, 20, 0))
    cyl(sc, b, "ArmRest", 0.004, 0.004, 0.03, (0.19, 0.425, 0.18), "metal_chrome", segs=8)
    col_box(sc, b, "ShapeL", (0.50, 0.55, D), (-0.51, 0.385, D / 2))
    col_box(sc, b, "ShapeR", (0.50, 0.55, D), (0.51, 0.385, D / 2))
    col_box(sc, b, "ShapeCentre", (0.52, 0.28, D), (0, 0.26, D / 2))
    col_box(sc, b, "ShapeWellFront", (0.52, 0.27, 0.02), (0, 0.525, D - 0.01))
    col_box(sc, b, "ShapeWellBack", (0.52, 0.27, 0.03), (0, 0.525, 0.015))
    look(sc, b, "Stereo", ["The speaker cloth is faded in a stripe where the sun hits it.", "Dust in the carved grooves."])
    # Receiver panel at the back of the well, tilted up toward the viewer.
    r = static_body(sc, ".", "Receiver", LAYER_INTERACT, pos=(0, 0.47, 0.075), rot=(-35, 0, 0))
    box(sc, r, "Plate", (0.47, 0.09, 0.006), (0, 0, 0), "metal_brass")
    box(sc, r, "DialGlass", (0.27, 0.024, 0.002), (-0.07, 0.016, 0.004), "fx:glass_amber_dial")
    for i in range(9):
        box(sc, r, "Tick%d" % i, (0.0012, 0.008, 0.0006), (-0.19 + i * 0.03, 0.022, 0.0052), "plastic_black")
    box(sc, r, "Pointer", (0.0016, 0.022, 0.0008), (-0.03, 0.016, 0.0055), "brick_red")
    for i, kx in enumerate((0.11, 0.16)):
        cyl(sc, r, "Knob%d" % i, 0.012, 0.013, 0.016, (kx, -0.014, 0.011), "metal_chrome", rot=(90, 0, 0), segs=16)
    kp = n3d(sc, r, "PowerKnob", (0.205, -0.014, 0.003))
    cyl(sc, kp, "KnobMesh", 0.012, 0.013, 0.016, (0, 0, 0.008), "metal_chrome", rot=(90, 0, 0), segs=16)
    box(sc, kp, "KnobMark", (0.002, 0.009, 0.0008), (0, 0.006, 0.0165), "plastic_white")
    omni(sc, r, "DialLight", (-0.07, 0.016, 0.04), 0.06, 0.5, (1.0, 0.7, 0.35), False)
    col_box(sc, r, "Shape", (0.47, 0.09, 0.03), (0, 0, 0.01))
    comp(sc, r, "Radio", DEVICE, {
        "display_name": "Stereo", "on_prompt": "Turn on", "off_prompt": "Turn off",
        "targets": NPS(["../../DialLamp"]),
        "moving_part": NP("../PowerKnob"), "on_rotation_degrees": V3(0, 0, -70), "move_time": 0.12,
        "on_sound": SN("switch_on"), "off_sound": SN("switch_off"), "loop_sound": SN("tape_hiss"),
        "loop_anchor": NP("../../Body"), "loop_volume_db": -12.0, "loop_unit_size": 3.0, "loop_delay": 0.6,
        "observations": STRS(["Hiss between stations. Nothing tuned in.", "The dial light has gone yellow behind the glass."]),
    })
    powered(sc, ["../Receiver/DialLight"], ["../Receiver/DialGlass"], name="DialLamp",
            extra={"bulb_emission_energy": 0.6, "temperature_kelvin": 2300.0, "warm_up_time": 0.4})
    lid = anim_body(sc, ".", "Lid", SOLID_INTERACT, pos=(0, H - 0.022, 0.01))
    box(sc, lid, "LidMesh", (0.52, 0.022, D), (0, 0.011, D / 2), wd)
    box(sc, lid, "LidInlay", (0.46, 0.002, D - 0.06), (0, 0.0225, D / 2), "wood_medium")
    box(sc, lid, "LidUnder", (0.50, 0.002, D - 0.02), (0, -0.001, D / 2), "fabric_corduroy_brown")
    col_box(sc, lid, "Shape", (0.52, 0.022, D), (0, 0.011, D / 2))
    comp(sc, lid, "Hinge", HINGED, {
        "display_name": "Stereo lid", "open_prompt": "Lift the lid", "close_prompt": "Close the lid",
        "axis": V3(1, 0, 0), "open_angle_degrees": -84.0, "open_duration": 0.9, "close_duration": 0.6,
        "open_profile": SMOOTH, "close_profile": LATCH, "stop_bump": 0.006,
        "open_sound": SN("cabinet_open"), "close_sound": SN("cabinet_close"),
        "observations": STRS(["A record player. No record on it.", "The felt under the lid smells like old cigarettes."]),
    })
    sc.write("fixtures/stereo_console.tscn")


def build_window():
    """Double-hung 6-over-6 window in a 0.30 exterior wall. Clear opening between
    jambs 0.86 W x 1.37 H. Origin: bottom centre of the opening, centred in the
    wall's thickness; interior (room) side is +Z."""
    ow, oh, wall = 0.86, 1.37, 0.30
    sc = Scene("WindowDoubleHung")
    b = static_body(sc, ".", "Window", SOLID_INTERACT)
    t = "trim_white"
    for side, sx in (("L", -1), ("R", 1)):
        box(sc, b, "Jamb" + side, (0.02, oh + 0.02, wall), (sx * (ow / 2 + 0.01), (oh + 0.02) / 2, 0), t)
        box(sc, b, "Stop" + side, (0.012, oh, 0.018), (sx * (ow / 2 - 0.006), oh / 2, 0.044), t)
        box(sc, b, "Parting" + side, (0.012, oh, 0.008), (sx * (ow / 2 - 0.006), oh / 2, -0.001), t)
        box(sc, b, "Blind" + side, (0.012, oh, 0.02), (sx * (ow / 2 - 0.006), oh / 2, -0.05), t)
        box(sc, b, "Casing" + side, (0.064, oh + 0.069, 0.016), (sx * (ow / 2 + 0.005 + 0.032), (oh + 0.069) / 2, wall / 2 + 0.008), t)
        box(sc, b, "Brickmould" + side, (0.05, oh + 0.07, 0.025), (sx * (ow / 2 + 0.035), (oh + 0.07) / 2, -wall / 2 - 0.0125), t)
    box(sc, b, "Head", (ow + 0.04, 0.02, wall), (0, oh + 0.01, 0), t)
    box(sc, b, "CasingHead", (ow + 0.138, 0.064, 0.016), (0, oh + 0.005 + 0.032, wall / 2 + 0.008), t)
    box(sc, b, "BrickmouldHead", (ow + 0.12, 0.05, 0.025), (0, oh + 0.045, -wall / 2 - 0.0125), t)
    box(sc, b, "Sill", (ow + 0.04, 0.03, 0.17), (0, -0.012, -0.08), t, rot=(-8, 0, 0))
    box(sc, b, "Stool", (ow + 0.16, 0.022, 0.21), (0, -0.011, 0.045 + 0.105 - 0.045), t)
    box(sc, b, "Apron", (ow + 0.10, 0.07, 0.016), (0, -0.022 - 0.035, wall / 2 + 0.008), t)

    def sash(name, z, y0, y1, bottom_rail, top_rail):
        s = n3d(sc, b, name, (0, 0, z))
        h = y1 - y0
        st = 0.05
        box(sc, s, "StileL", (st, h, 0.035), (-(ow / 2 - st / 2), y0 + h / 2, 0), t)
        box(sc, s, "StileR", (st, h, 0.035), ((ow / 2 - st / 2), y0 + h / 2, 0), t)
        box(sc, s, "RailBottom", (ow - 2 * st, bottom_rail, 0.035), (0, y0 + bottom_rail / 2, 0), t)
        box(sc, s, "RailTop", (ow - 2 * st, top_rail, 0.035), (0, y1 - top_rail / 2, 0), t)
        gy0, gy1 = y0 + bottom_rail, y1 - top_rail
        gw = ow - 2 * st
        box(sc, s, "Glass", (gw, gy1 - gy0, 0.003), (0, (gy0 + gy1) / 2, 0), "glass_window", cast=SHADOW_OFF)
        for i in (1, 2):
            box(sc, s, "MuntinV%d" % i, (0.016, gy1 - gy0, 0.02), (-gw / 2 + gw * i / 3, (gy0 + gy1) / 2, 0), t)
        box(sc, s, "MuntinH", (gw, 0.016, 0.02), (0, (gy0 + gy1) / 2, 0), t)
        return s

    lower = sash("LowerSash", 0.0175, 0.0, 0.70, 0.07, 0.04)
    sash("UpperSash", -0.0225, 0.66, oh, 0.04, 0.05)
    box(sc, lower, "LockBase", (0.05, 0.006, 0.02), (0, 0.703, 0.0), "metal_brass")
    cyl(sc, lower, "LockCam", 0.016, 0.016, 0.005, (0.008, 0.708, -0.012), "metal_brass", segs=16)
    for i, lx in enumerate((-0.25, 0.25)):
        box(sc, lower, "Lift%d" % i, (0.03, 0.012, 0.014), (lx, 0.04, 0.024), "metal_brass")
    # Paint has bridged the sash and the stop: a few drips on the stool.
    for i, (px, pz) in enumerate(((-0.31, 0.06), (0.12, 0.08), (0.36, 0.05))):
        sphere(sc, b, "PaintDrip%d" % i, 0.006, 0.003, (px, 0.0005, pz), t, segs=8, rings=4)
    col_box(sc, b, "ShapeOpening", (ow + 0.04, oh + 0.02, 0.10), (0, (oh + 0.02) / 2, 0))
    col_box(sc, b, "ShapeStool", (ow + 0.16, 0.022, 0.21), (0, -0.011, 0.105))
    comp(sc, b, "Sash", JAMMED, {
        "display_name": "Window", "prompt": "Open", "tried_prompt": "Try again",
        "shake_node": NP("../LowerSash"), "shake_offset": V3(0, 0.0025, 0.0008), "sound": SN("window_rattle"),
        "observations": STRS(["It's painted shut.", "The sash rattles in the frame but won't lift.", "Heat comes off the glass."]),
    })
    sc.write("fixtures/window_double_hung.tscn")


def write_material(rel, body):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, rel), "w") as f:
        f.write(body)


def build_materials():
    simple = {
        "glass_frosted": "transparency = 1\nalbedo_color = Color(0.96, 0.94, 0.88, 0.88)\nroughness = 0.35",
        "glass_amber_dial": "albedo_color = Color(0.55, 0.42, 0.2, 1)\nroughness = 0.3",
        "bulb_glass": "albedo_color = Color(0.95, 0.93, 0.88, 1)\nroughness = 0.25",
        "vfd_window": "albedo_color = Color(0.02, 0.04, 0.05, 1)\nroughness = 0.12",
        "led_red": "albedo_color = Color(0.9, 0.08, 0.04, 1)\nemission_enabled = true\nemission = Color(1, 0.1, 0.05, 1)\nemission_energy_multiplier = 3.0",
        "led_dark": "albedo_color = Color(0.18, 0.03, 0.02, 1)\nroughness = 0.3",
        "baking_soda_box": "albedo_color = Color(0.85, 0.4, 0.08, 1)\nroughness = 0.85",
        "index_blue": "albedo_color = Color(0.1, 0.25, 0.75, 1)\nroughness = 0.4",
    }
    for name, body in simple.items():
        write_material("fixtures/materials/%s.tres" % name,
                       '[gd_resource type="StandardMaterial3D" format=3]\n\n[resource]\n%s\n' % body)
    for name, shader, params in (
        ("crt_static", "crt_static.gdshader", "shader_parameter/brightness = 1.15\nshader_parameter/screen_size = Vector2(0.37, 0.28)\nshader_parameter/resolution = Vector2(220, 165)\nshader_parameter/frame_rate = 30.0\nshader_parameter/tint = Color(0.86, 0.9, 1, 1)"),
        ("water_stream", "water_stream.gdshader", "shader_parameter/water_color = Color(0.82, 0.88, 0.9, 0.55)\nshader_parameter/speed = 2.6\nshader_parameter/streaks = 14.0\nshader_parameter/wobble = 0.0006"),
    ):
        write_material("fixtures/materials/%s.tres" % name,
                       '[gd_resource type="ShaderMaterial" format=3]\n\n[ext_resource type="Shader" path="res://fixtures/shaders/%s" id="1"]\n\n[resource]\nshader = ExtResource("1")\n%s\n' % (shader, params))


def wall_x(sc, parent, name, x0, x1, z, thick, height, openings, mat):
    """Wall running along X from x0 to x1, centred on z. openings: [(cx, w, y0, y1)]."""
    segs = []
    cur = x0
    for cx, w, y0, y1 in sorted(openings):
        a, b = cx - w / 2, cx + w / 2
        if a > cur:
            segs.append((cur, a, 0, height))
        if y0 > 0:
            segs.append((a, b, 0, y0))
        if y1 < height:
            segs.append((a, b, y1, height))
        cur = b
    if cur < x1:
        segs.append((cur, x1, 0, height))
    body = static_body(sc, parent, name, LAYER_WORLD)
    for i, (a, b, y0, y1) in enumerate(segs):
        size = (b - a, y1 - y0, thick)
        pos = ((a + b) / 2, (y0 + y1) / 2, z)
        box(sc, body, "Seg%d" % i, size, pos, mat)
        col_box(sc, body, "SegShape%d" % i, size, pos)
    return body


def inst(sc, name, path, pos, rot_y=0.0, props=None):
    p = {"transform": XF(pos, (0, rot_y, 0))}
    if props:
        p.update(props)
    return sc.node(name, None, ".", p, instance=sc.ext(path, "PackedScene"))


def build_sandbox():
    """tests/fixtures/fixtures_sandbox.tscn: every fixture in a lit 10 x 8 m room."""
    sc = Scene("FixturesSandbox", script="res://tests/fixtures/fixtures_sandbox.gd")
    sky = sc.sub("ProceduralSkyMaterial", sky_top_color=C(0.36, 0.55, 0.82), sky_horizon_color=C(0.82, 0.8, 0.74),
                 ground_horizon_color=C(0.6, 0.55, 0.45), ground_bottom_color=C(0.3, 0.27, 0.22), sun_angle_max=20.0)
    skyr = sc.sub("Sky", sky_material=sky)
    env = sc.sub("Environment", background_mode=2, sky=skyr, ambient_light_source=3, ambient_light_color=C(0.95, 0.88, 0.76),
                 ambient_light_sky_contribution=0.35, ambient_light_energy=0.55, tonemap_mode=2, tonemap_exposure=1.0,
                 ssao_enabled=True, glow_enabled=True, glow_intensity=0.35, glow_bloom=0.05)
    sc.node("WorldEnvironment", "WorldEnvironment", ".", {"environment": env})
    sc.node("Sun", "DirectionalLight3D", ".", {
        "transform": XF((0, 6, 0), rot=(-24, 72, 0)), "light_color": C(1.0, 0.9, 0.76), "light_energy": 2.2,
        "shadow_enabled": True, "directional_shadow_max_distance": 30.0})
    # Shell.
    fl = static_body(sc, ".", "Floor", LAYER_WORLD)
    sc.nodes[-1][1]["metadata/surface"] = SN("wood")
    box(sc, fl, "Mesh", (10.0, 0.1, 10.0), (0, -0.05, -1.0), "floor_hardwood")
    col_box(sc, fl, "Shape", (10.0, 0.1, 10.0), (0, -0.05, -1.0))
    box(sc, fl, "Outside", (8.0, 0.1, 12.0), (9.4, -0.06, 0), "plant_green")
    col_box(sc, fl, "OutsideShape", (8.0, 0.1, 12.0), (9.4, -0.06, 0))
    ce = static_body(sc, ".", "Ceiling", LAYER_WORLD)
    box(sc, ce, "Mesh", (10.0, 0.1, 10.0), (0, 2.49, -1.0), "ceiling_popcorn")
    col_box(sc, ce, "Shape", (10.0, 0.1, 10.0), (0, 2.49, -1.0))
    H = 2.44
    walls = n3d(sc, ".", "Walls")
    wall_x(sc, walls, "North", -5.0, 5.0, -4.075, 0.15, H, [(-3.2, 0.854, 0.0, 2.064), (2.8, 1.558, 0.0, 2.064)], "wall_plaster_cream")
    wall_x(sc, walls, "South", -5.3, 5.3, 4.15, 0.30, H, [], "wall_wood_paneling")
    wall_x(sc, walls, "HallBack", -5.0, 5.0, -5.8, 0.15, H, [], "wallpaper_stripe")
    # East (exterior) wall along Z, built as an X wall rotated -90 about Y (its local x -> world +z).
    east = n3d(sc, walls, "EastFrame", (5.15, 0, 0), (0, -90, 0))
    wall_x(sc, east, "East", -5.9, 4.3, 0, 0.30, H, [(-2.5, 0.954, 0.0, 2.075), (0.5, 0.90, 0.76, 0.76 + 1.39)], "wall_plaster_cream")
    west = n3d(sc, walls, "WestFrame", (-5.075, 0, 0), (0, -90, 0))
    wall_x(sc, west, "West", -5.9, 4.3, 0, 0.15, H, [], "wallpaper_floral")
    # Closet niche behind the sliding doors.
    cl = static_body(sc, ".", "ClosetNiche", LAYER_WORLD)
    box(sc, cl, "Back", (1.6, H, 0.05), (2.8, H / 2, -4.8), "wall_plaster_cream")
    box(sc, cl, "Shelf", (1.5, 0.02, 0.35), (2.8, 1.72, -4.6), "wood_light")
    cyl(sc, cl, "Rod", 0.012, 0.012, 1.5, (2.8, 1.65, -4.5), "metal_chrome", rot=(0, 0, 90))
    for i, sx in enumerate((2.0, 3.6)):
        box(sc, cl, "Side%d" % i, (0.05, H, 0.65), (sx, H / 2, -4.475), "wall_plaster_cream")
    # Furniture to stand things on.
    tb = static_body(sc, ".", "Table", LAYER_WORLD, pos=(0.2, 0, 0.6))
    box(sc, tb, "Top", (1.0, 0.03, 0.65), (0, 0.725, 0), "wood_medium")
    for i, (lx, lz) in enumerate(((-0.45, -0.28), (0.45, -0.28), (-0.45, 0.28), (0.45, 0.28))):
        box(sc, tb, "Leg%d" % i, (0.045, 0.71, 0.045), (lx, 0.355, lz), "wood_medium")
    col_box(sc, tb, "Shape", (1.0, 0.74, 0.65), (0, 0.37, 0))
    st = static_body(sc, ".", "TvStand", LAYER_WORLD, pos=(1.5, 0, 3.72))
    box(sc, st, "Top", (0.9, 0.025, 0.5), (0, 0.5375, 0), "wood_dark")
    box(sc, st, "Shelf", (0.86, 0.02, 0.48), (0, 0.06, 0), "wood_dark")
    for i, sx in enumerate((-0.44, 0.44)):
        box(sc, st, "Side%d" % i, (0.02, 0.55, 0.5), (sx, 0.275, 0), "wood_dark")
    col_box(sc, st, "Shape", (0.9, 0.55, 0.5), (0, 0.275, 0))
    # Fixtures.
    inst(sc, "DoorInterior", F + "door_interior.tscn", (-3.2, 0, -4.075), 0.0, {"start_state": 1})
    inst(sc, "Closet", F + "closet_sliding.tscn", (2.8, 0, -4.075))
    inst(sc, "DoorFront", F + "door_front.tscn", (5.15, 0, -2.5), 90.0, {"required_flag": SN("has_house_key"), "opened_flag": SN("front_door_opened")})
    inst(sc, "Window", F + "window_double_hung.tscn", (5.15, 0.76, 0.5), -90.0)
    inst(sc, "DresserDrawers", F + "dresser_drawers.tscn", (0.0, 0, -4.0))
    inst(sc, "SwitchCeiling", F + "light_switch.tscn", (-2.62, 1.2, -4.0), 0.0, {"targets": NPS(["../CeilingLight"])})
    inst(sc, "SwitchFan", F + "light_switch.tscn", (-2.53, 1.2, -4.0), 0.0, {"targets": NPS(["../CeilingFan/Motor", "../CeilingFan/Power"]), "display_name": "Fan switch"})
    inst(sc, "CeilingLight", F + "ceiling_light.tscn", (-2.0, H, -1.6))
    inst(sc, "CeilingFan", F + "ceiling_fan.tscn", (1.6, H, 1.2))
    inst(sc, "TableLamp", F + "table_lamp.tscn", (-0.05, 0.74, 0.45))
    inst(sc, "Telephone", F + "telephone.tscn", (0.45, 0.74, 0.65), 15.0)
    inst(sc, "FloorLamp", F + "floor_lamp.tscn", (-3.9, 0, 2.6))
    inst(sc, "Fridge", F + "fridge.tscn", (-5.0, 0, -2.6), 90.0)
    inst(sc, "KitchenBase", F + "kitchen_cabinet_base.tscn", (-5.0, 0, -1.76), 90.0)
    inst(sc, "KitchenSink", F + "kitchen_sink.tscn", (-5.0, 0, -0.85), 90.0)
    inst(sc, "KitchenBase2", F + "kitchen_cabinet_base.tscn", (-5.0, 0, 0.06), 90.0)
    inst(sc, "KitchenWall", F + "kitchen_cabinet_wall.tscn", (-5.0, 1.37, -1.76), 90.0)
    inst(sc, "KitchenWall2", F + "kitchen_cabinet_wall.tscn", (-5.0, 1.37, 0.06), 90.0)
    inst(sc, "StereoConsole", F + "stereo_console.tscn", (-1.8, 0, 4.0), 180.0)
    inst(sc, "TvCrt", F + "tv_crt.tscn", (1.5, 0.55, 3.72), 180.0)
    inst(sc, "Vcr", F + "vcr.tscn", (1.5, 0.07, 3.68), 180.0)
    sc.node("Spawn", "Marker3D", ".", {"transform": XF((0, 0, 2.5))}, groups=["player_spawn"])
    sc.write("tests/fixtures/fixtures_sandbox.tscn")


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "materials"), exist_ok=True)
    build_materials()
    build_door("interior")
    build_door("front")
    build_closet()
    build_light_switch()
    build_table_lamp()
    build_floor_lamp()
    build_ceiling_light()
    build_ceiling_fan()
    build_tv()
    build_vcr()
    build_dresser()
    build_kitchen_base()
    build_kitchen_wall()
    build_fridge()
    build_sink()
    build_telephone()
    build_stereo()
    build_window()
    build_sandbox()
