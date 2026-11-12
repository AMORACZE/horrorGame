"""Hallway and miscellaneous props, plus architecture dressing (blinds, curtains)."""
from __future__ import annotations

import math
import random

from tscn import Scene, Raw
from common import register, tex, ORIGIN_FLOOR, ORIGIN_WALL


def coat_rack() -> None:
    s = Scene("CoatRack")
    WD = "wood_dark"
    s.cyl("Post", 0.022, 1.74, (0, 0.89, 0), WD, r_bottom=0.026, segs=16)
    s.sphere("Finial", 0.034, (0, 1.79, 0), WD, scale=(1, 1.2, 1))
    s.torus("Collar", 0.02, 0.034, (0, 1.70, 0), WD, ring_segs=6)
    for k in range(4):
        a = math.radians(45 + k * 90)
        c, sn = math.cos(a), math.sin(a)
        s.rod("Leg", (0, 0.20, 0), (c * 0.27, 0.012, sn * 0.27), 0.017, WD, segs=8)
        s.sphere("LegFoot", 0.02, (c * 0.27, 0.012, sn * 0.27), "rubber_black", scale=(1, 0.6, 1), segs=10, rings=5)
    hooks = []
    for k in range(4):
        a = math.radians(90 + k * 90)  # first hook faces +Z
        c, sn = math.cos(a), math.sin(a)
        p0, p1, p2 = (0, 1.62, 0), (c * 0.11, 1.64, sn * 0.11), (c * 0.15, 1.71, sn * 0.15)
        s.rod("Hook", p0, p1, 0.007, "metal_brass", segs=8)
        s.rod("Hook", p1, p2, 0.007, "metal_brass", segs=8)
        s.sphere("HookTip", 0.012, p2, "metal_brass", segs=10, rings=5)
        hooks.append((c, sn))
    # Jacket on the front hook (+Z)
    j = s.group("Jacket", pos=(0, 1.70, 0.19), rot=(3, 0, 0))
    PL = "fabric_plaid"
    s.torus("Collar", 0.03, 0.058, (0, -0.025, -0.01), "fabric_corduroy_brown", scale=(1.25, 0.6, 1.0), parent=j)
    s.prism("Shoulders", (0.46, 0.10, 0.12), (0, -0.085, 0), PL, parent=j)
    s.box("Body", (0.46, 0.62, 0.12), (0, -0.445, 0), PL, parent=j)
    s.box("Hem", (0.465, 0.06, 0.125), (0, -0.73, 0), "fabric_corduroy_brown", parent=j)
    s.box("Placket", (0.03, 0.62, 0.004), (0, -0.445, 0.061), PL, parent=j)
    for sx in (-1, 1):
        s.capsule("Sleeve", 0.052, 0.60, (sx * 0.225, -0.40, 0.012), PL, rot=(0, 0, sx * 3), parent=j)
        s.box("Cuff", (0.10, 0.05, 0.10), (sx * 0.235, -0.69, 0.012), "fabric_corduroy_brown", rot=(0, 0, sx * 3),
              parent=j)
        s.box("Pocket", (0.11, 0.09, 0.004), (sx * 0.11, -0.25, 0.062), PL, parent=j)
        s.box("PocketFlap", (0.115, 0.03, 0.006), (sx * 0.11, -0.205, 0.064), "fabric_corduroy_brown", parent=j)
    for k in range(5):
        s.sphere("Button", 0.008, (0, -0.17 - k * 0.12, 0.064), "plastic_black", scale=(1, 1, 0.4), parent=j,
                 segs=8, rings=4)
    # Cap on the side hook (-X)
    c = s.group("Cap", pos=(-0.16, 1.66, 0.0), rot=(0, 90, 70))
    s.sphere("Crown", 0.085, (0, 0, 0), "fabric_corduroy_brown", hemi=True, parent=c, segs=16, rings=6)
    s.cyl("Brim", 0.07, 0.006, (0, 0.002, 0.08), "fabric_corduroy_brown", parent=c, scale=(1, 1, 0.8))
    s.col_cyl(0.30, 0.05, (0, 0.025, 0))
    s.col_box((0.06, 1.8, 0.06), (0, 0.9, 0), name="CollisionPost")
    s.col_box((0.56, 0.80, 0.16), (0, 1.32, 0.19), name="CollisionJacket")
    s.interactable("base", "Coat rack", [
        "A flannel jacket on the front hook. Too warm for August.",
        "In the jacket pocket: a pencil stub and a receipt from Pell's Market, dated 8/19.",
        "A cap on the side hook, with a salt line inside the band.",
    ])
    register("props/hallway/coat_rack.tscn", s, ORIGIN_FLOOR, "Interactable",
             "1.80 m tall; jacket hangs on the +Z side. Feet span 0.55 m.")


def _shoe(s: Scene, parent: str, crushed: bool) -> None:
    W, B = "plastic_white", "plastic_grey"
    s.box("Sole", (0.095, 0.025, 0.27), (0, 0.0125, 0), "rubber_black", parent=parent)
    for j in range(3):
        s.box("Grass", (0.02, 0.003, 0.004), (0.02 * (j - 1), 0.0005, 0.06 * (j - 1)), "plant_green",
              rot=(0, j * 50, 0), parent=parent)
    s.box("Midsole", (0.098, 0.018, 0.272), (0, 0.032, 0), W, parent=parent)
    s.capsule("Toe", 0.048, 0.20, (0, 0.06, 0.035), W, rot=(90, 0, 0), scale=(1, 1, 0.72), parent=parent)
    if crushed:
        s.box("HeelCrushed", (0.09, 0.03, 0.08), (0, 0.055, -0.095), W, rot=(-30, 0, 0), parent=parent)
    else:
        s.box("Heel", (0.09, 0.08, 0.08), (0, 0.075, -0.095), W, parent=parent)
        s.cyl("Collar", 0.035, 0.012, (0, 0.11, -0.085), "rubber_black", scale=(1, 1, 1.3), parent=parent)
    s.box("Stripe", (0.1, 0.022, 0.12), (0, 0.06, -0.02), B, rot=(0, 0, 0), parent=parent)
    for k in range(4):
        s.box("Lace", (0.05, 0.004, 0.006), (0, 0.098 - k * 0.006, 0.03 + k * 0.02), W, rot=(-25, 0, 0),
              parent=parent)
    s.torus("Bow", 0.006, 0.014, (0.012, 0.104, 0.02), W, rot=(70, 20, 0), parent=parent, rings=10, ring_segs=4)


def shoes() -> None:
    s = Scene("Shoes", prop_class="tabletop")
    for k, (x, z, yaw, crushed) in enumerate(((-0.065, 0.0, 6, False), (0.075, 0.03, -10, True))):
        g = s.group("Shoe", pos=(x, 0, z), rot=(0, yaw, 0))
        _shoe(s, g, crushed)
    s.col_box((0.28, 0.12, 0.31), (0, 0.06, 0.01))
    s.interactable("base", "Sneakers", [
        "White sneakers, laces still tied. The heel of one is crushed flat.",
        "Dried grass stuck in the treads.",
    ])
    register("props/hallway/shoes_pair.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Small floor clutter: layer 3 only, player walks through. Toes +Z.")


def umbrella_stand() -> None:
    s = Scene("UmbrellaStand")
    s.cyl("Stand", 0.11, 0.46, (0, 0.23, 0), "metal_brass", r_bottom=0.10, segs=24, cap_top=False)
    s.cyl("Floor", 0.10, 0.01, (0, 0.006, 0), "metal_dark", segs=24)
    s.torus("Lip", 0.103, 0.118, (0, 0.46, 0), "metal_brass", ring_segs=6, rings=24)
    s.torus("Band", 0.103, 0.115, (0, 0.08, 0), "metal_brass", ring_segs=6, rings=24)
    g = s.group("Umbrella", pos=(0.02, 0.012, -0.01), rot=(-6, 0, 7))
    s.cyl("Canopy", 0.014, 0.62, (0, 0.33, 0), "p:umbrella_navy", r_bottom=0.034, segs=12, parent=g)
    s.cyl("Tip", 0.004, 0.03, (0, 0.012, 0), "metal_chrome", r_bottom=0.002, segs=6, parent=g)
    s.box("Strap", (0.05, 0.03, 0.004), (0.0, 0.52, 0.028), "p:umbrella_navy", rot=(0, 0, 0), parent=g)
    s.cyl("Shaft", 0.005, 0.18, (0, 0.72, 0), "metal_chrome", segs=6, parent=g)
    s.torus("Crook", 0.026, 0.04, (0.032, 0.82, 0), "wood_medium", rot=(90, 0, 0), parent=g, rings=16, ring_segs=6)
    s.col_cyl(0.12, 0.47, (0, 0.235, 0))
    s.col_box((0.1, 0.4, 0.1), (0.05, 0.68, 0), name="CollisionUmbrella")
    s.interactable("base", "Umbrella stand", [
        "One umbrella, closed and strapped. The bottom of the stand is dry and dusty.",
    ])
    register("props/hallway/umbrella_stand.tscn", s, ORIGIN_FLOOR, "Interactable", "By the front door.")


def key_hooks() -> None:
    s = Scene("KeyHooks", prop_class="wall")
    s.box("Plaque", (0.34, 0.11, 0.016), (0, 0, 0.008), "wood_medium")
    s.box("Panel", (0.32, 0.09, 0.004), (0, 0, 0.018), "wood_light")
    s.quad("Labels", (0.30, 0.028), (0, -0.026, 0.0205), tex("key_dymo_labels.png", transparent=True, roughness=0.4))
    for k in range(4):
        x = -0.1125 + k * 0.075
        s.rod("Hook", (x, 0.012, 0.02), (x, 0.012, 0.045), 0.0028, "metal_brass", segs=6)
        s.rod("HookUp", (x, 0.012, 0.045), (x, 0.026, 0.05), 0.0028, "metal_brass", segs=6)
        s.cyl("Screw", 0.004, 0.002, (x, 0.035, 0.021), "metal_brass", rot=(90, 0, 0), segs=8)
        if k == 3:
            s.box("WornArc", (0.03, 0.022, 0.0008), (x, -0.004, 0.0205), "wood_dark")
            continue
        g = s.group("Keys", pos=(x, 0.006, 0.044))
        s.torus("Ring", 0.009, 0.0115, (0, -0.008, 0), "metal_chrome", rot=(90, 0, 10 * k), parent=g, ring_segs=4,
                rings=12)
        for j in range(2 + (k == 1)):
            ang = (j - 0.5) * 14
            kk = s.group("Key", pos=(0, -0.018, 0.002 * j), rot=(0, 0, ang), parent=g)
            head = "plastic_black" if (k == 1 and j == 0) else "metal_brass"
            s.cyl("Bow", 0.011, 0.0025, (0, -0.008, 0), head, rot=(90, 0, 0), parent=kk, segs=10)
            s.box("Blade", (0.007, 0.036, 0.002), (0, -0.036, 0), "metal_chrome" if j else "metal_brass", parent=kk)
        if k == 1:
            s.box("Tag", (0.02, 0.03, 0.002), (0.008, -0.04, 0.006), "paper_white", rot=(0, 0, -20), parent=g)
    s.col_box((0.34, 0.16, 0.06), (0, -0.02, 0.03))
    s.interactable("base", "Key hooks", [
        "Four hooks with label tape: HOUSE, CAR, SHED, GARAGE. The GARAGE hook is empty.",
        "The car keys have a paper tag from Dorsey Motors.",
        "Under the empty hook, the varnish is rubbed into a little arc where a key used to swing.",
    ])
    register("props/hallway/key_hooks.tscn", s, ORIGIN_WALL, "Interactable", "Beside the front door at ~1.45 m.")


def _box_shell(s: Scene, W: float, H: float, D: float, open_top: bool) -> None:
    CB = "cardboard"
    t = 0.006
    if open_top:
        s.box("Bottom", (W, t, D), (0, t / 2, 0), CB)
        for sz in (-1, 1):
            s.box("Wall", (W, H, t), (0, H / 2, sz * (D / 2 - t / 2)), CB)
        for sx in (-1, 1):
            s.box("Wall", (t, H, D - 2 * t), (sx * (W / 2 - t / 2), H / 2, 0), CB)
    else:
        s.box("Box", (W, H, D), (0, H / 2, 0), CB)
        s.box("Seam", (0.003, 0.0012, D), (0, H + 0.0004, 0), "wood_dark")
        s.box("Tape", (0.05, 0.0015, D + 0.002), (0, H + 0.0006, 0), "p:packing_tape")
        for sz in (-1, 1):
            s.box("TapeDown", (0.05, 0.08, 0.0015), (0, H - 0.04, sz * (D / 2 + 0.0006)), "p:packing_tape")
    marker = tex("box_marker_kitchen.png", transparent=True, roughness=0.9)
    s.quad("MarkerFront", (0.34, 0.133), (0, H * 0.55, D / 2 + 0.0008), marker)
    s.quad("MarkerSide", (0.34, 0.133), (W / 2 + 0.0008, H * 0.6, 0), marker, rot=(0, 90, 0))
    s.quad("MarkerOld", (0.30, 0.117), (-W / 2 - 0.0008, H * 0.5, 0.02),
           tex("box_marker_den.png", transparent=True, roughness=0.9), rot=(0, -90, 0))
    for sx in (-1, 1):
        s.box("HandHole", (0.002, 0.03, 0.09), (sx * (W / 2 + 0.0004), H - 0.07, 0), "plastic_black")


def moving_boxes() -> None:
    W, H, D = 0.46, 0.41, 0.46
    s = Scene("MovingBoxClosed")
    _box_shell(s, W, H, D, False)
    s.col_box((W, H, D), (0, H / 2, 0))
    s.interactable("base", "Box", [
        "Taped shut. KITCHEN in marker on two sides.",
        "On a third side, DEN, crossed out.",
        "Heavy. Something inside shifts with a clink of glass.",
    ])
    register("props/hallway/moving_box_closed.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Stackable: top at y = 0.41. KITCHEN on +Z and +X.")

    s = Scene("MovingBoxOpen")
    _box_shell(s, W, H, D, True)
    for name, axis, sgn, rot in (("FlapFront", "z", 1, (-115, 0, 0)), ("FlapBack", "z", -1, (100, 0, 0)),
                                 ("FlapLeft", "x", -1, (0, 0, 105)), ("FlapRight", "x", 1, (0, 0, -120))):
        if axis == "z":
            g = s.group(name, pos=(0, H, sgn * D / 2), rot=rot if sgn > 0 else rot)
            s.box("Flap", (W - 0.004, 0.004, D / 2), (0, 0, sgn * D / 4), "cardboard", parent=g)
        else:
            g = s.group(name, pos=(sgn * W / 2, H, 0), rot=rot)
            s.box("Flap", (W / 2, 0.004, D - 0.004), (sgn * W / 4, 0, 0), "cardboard", parent=g)
    rnd = random.Random(86)
    NP = "p:newsprint"
    for k in range(7):
        x, z = rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15)
        r = rnd.uniform(0.06, 0.09)
        s.sphere("Crumple", r, (x, H - 0.06 + rnd.uniform(-0.02, 0.03), z), NP,
                 scale=(rnd.uniform(0.9, 1.3), rnd.uniform(0.7, 1.0), rnd.uniform(0.9, 1.2)),
                 rot=(rnd.uniform(0, 40), rnd.uniform(0, 180), 0), segs=8, rings=5)
    s.cyl("WrappedGlass", 0.05, 0.16, (-0.09, H - 0.04, 0.08), NP, rot=(70, 30, 0), segs=10, r_bottom=0.045)
    s.sphere("WrappedBowl", 0.10, (0.08, H - 0.07, -0.06), NP, scale=(1.1, 0.55, 1.0), segs=10, rings=6)
    s.box("WrappedFrame", (0.22, 0.03, 0.17), (0.05, H + 0.0, 0.10), NP, rot=(12, -20, 8))
    s.col_box((W, H, D), (0, H / 2, 0))
    s.interactable("base", "Open box", [
        "Half unpacked, or half packed. Things wrapped in newspaper.",
        "The newspaper is from March 1986.",
        "One bundle has been unwrapped and wrapped again, more neatly than the rest.",
    ])
    register("props/hallway/moving_box_open.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Flaps spread ~0.2 m beyond the box on each side.")


def laundry_basket() -> None:
    s = Scene("LaundryBasket")
    P = "plastic_white"
    W, H, D = 0.60, 0.27, 0.42
    s.box("Floor", (W - 0.02, 0.012, D - 0.02), (0, 0.006, 0), P)
    for sz in (-1, 1):
        z = sz * (D / 2 - 0.006)
        s.box("Rim", (W, 0.03, 0.014), (0, H - 0.015, z), P)
        s.box("BaseRail", (W, 0.04, 0.012), (0, 0.02, z), P)
        s.box("MidRail", (W, 0.014, 0.01), (0, 0.14, z), P)
        for k in range(11):
            s.box("Bar", (0.016, H - 0.06, 0.01), (-W / 2 + 0.03 + k * (W - 0.06) / 10, H / 2, z), P)
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.006)
        s.box("Rim", (0.014, 0.05, D), (x, H - 0.025, 0), P)
        s.box("BaseRail", (0.012, 0.04, D), (x, 0.02, 0), P)
        s.box("HandleHole", (0.0145, 0.022, 0.12), (x, H - 0.026, 0), "plastic_black")
        for k in range(7):
            s.box("Bar", (0.01, H - 0.08, 0.016), (x, (H - 0.08) / 2 + 0.03, -D / 2 + 0.03 + k * (D - 0.06) / 6), P)
    # folded on one side, a heap on the other
    for k in range(4):
        s.box("Towel", (0.25, 0.04, 0.30), (-0.14, 0.035 + k * 0.042, 0.0), ("p:towel_blue", "paper_white")[k % 2],
              rot=(0, (k % 2) * 3 - 1, 0))
    rnd = random.Random(12)
    for k in range(6):
        s.sphere("Heap", 0.08, (0.12 + rnd.uniform(-0.06, 0.06), 0.12 + rnd.uniform(0, 0.08),
                                rnd.uniform(-0.1, 0.1)),
                 ("fabric_plaid", "p:towel_blue", "paper_white", "fabric_corduroy_brown")[k % 4],
                 scale=(1.4, 0.7, 1.1), rot=(0, rnd.uniform(0, 180), rnd.uniform(-20, 20)), segs=10, rings=6)
    s.capsule("Sock", 0.018, 0.16, (0.20, H - 0.02, D / 2 + 0.01), "paper_white", rot=(0, 0, 95))
    s.capsule("SockHang", 0.018, 0.12, (0.25, H - 0.07, D / 2 + 0.02), "paper_white", rot=(8, 0, 0))
    s.col_box((W, H, D), (0, H / 2, 0))
    s.interactable("base", "Laundry basket", [
        "Clean laundry. Folded on one side, not on the other.",
        "A single sock hangs over the rim.",
    ])
    register("props/hallway/laundry_basket.tscn", s, ORIGIN_FLOOR, "Interactable", "")


def floor_fan() -> None:
    s = Scene("FloorFan")
    BG = "plastic_beige"
    s.cyl("Base", 0.17, 0.035, (0, 0.0175, 0), BG, r_bottom=0.18, segs=28)
    s.sphere("BaseDome", 0.08, (0, 0.035, 0), BG, hemi=True, scale=(1, 0.5, 1))
    for k in range(3):
        s.box("SpeedKey", (0.022, 0.012, 0.03), (-0.03 + k * 0.03, 0.04, 0.11), "plastic_white" if k else BG,
              rot=(-15, 0, 0))
    s.cyl("Pole", 0.016, 0.80, (0, 0.44, 0), "metal_chrome", segs=12)
    s.cyl("Collar", 0.024, 0.06, (0, 0.85, 0), BG, segs=12)
    head = s.group("Head", pos=(0, 0.98, 0.0), rot=(-6, 0, 0))
    s.capsule("Motor", 0.065, 0.20, (0, 0, -0.06), BG, rot=(90, 0, 0), parent=head)
    s.cyl("Knob", 0.012, 0.03, (0, 0.07, -0.11), BG, parent=head, segs=10)
    s.box("Yoke", (0.04, 0.12, 0.03), (0, -0.07, -0.05), BG, parent=head)
    s.cyl("Hub", 0.035, 0.03, (0, 0, 0.045), BG, rot=(90, 0, 0), parent=head)
    for k in range(3):
        b = s.group("Blade", parent=head, pos=(0, 0, 0.045), rot=(0, 0, k * 120 + 15))
        s.box("Blade", (0.085, 0.16, 0.003), (0, 0.105, 0), "plastic_grey", rot=(0, 18, 0), parent=b)
    R = 0.2
    for z, nm in ((0.085, "FrontRing"), (-0.005, "BackRing")):
        s.torus(nm, R - 0.005, R + 0.004, (0, 0, z), "metal_chrome", rot=(90, 0, 0), parent=head, rings=32,
                ring_segs=5)
    s.torus("InnerRing", 0.12, 0.126, (0, 0, 0.088), "metal_chrome", rot=(90, 0, 0), parent=head, rings=24,
            ring_segs=4)
    for k in range(16):
        a = math.radians(k * 22.5)
        c, sn = math.cos(a), math.sin(a)
        s.rod("Spoke", (c * 0.035, sn * 0.035, 0.09), (c * R, sn * R, 0.086), 0.0018, "metal_chrome", parent=head,
              segs=4)
        s.rod("BackSpoke", (c * 0.06, sn * 0.06, -0.012), (c * R, sn * R, -0.006), 0.0018, "metal_chrome",
              parent=head, segs=4)
        if k % 2 == 0:
            s.rod("Rib", (c * R, sn * R, -0.006), (c * R, sn * R, 0.086), 0.002, "metal_chrome", parent=head, segs=4)
    s.cyl("Badge", 0.034, 0.006, (0, 0, 0.093), BG, rot=(90, 0, 0), parent=head)
    s.rod("Cord", (0, 0.01, -0.17), (0.05, 0.004, -0.45), 0.003, "rubber_black", segs=6)
    s.col_cyl(0.18, 0.04, (0, 0.02, 0))
    s.col_box((0.04, 0.85, 0.04), (0, 0.45, 0), name="CollisionPole")
    s.col_cyl(0.21, 0.24, (0, 0.98, -0.0), rot=(90, 0, 0), name="CollisionHead")
    s.interactable("base", "Fan", [
        "A pedestal fan, switched off and turned to face the wall.",
        "Grey fur of dust along the leading edge of every blade.",
    ])
    register("props/hallway/floor_fan.tscn", s, ORIGIN_FLOOR, "Interactable", "Static. Head 0.98 m, faces +Z.")


def wall_mirror() -> None:
    s = Scene("WallMirror", prop_class="wall")
    W, H, F = 0.60, 0.90, 0.065
    for sy in (-1, 1):
        s.box("Rail", (W, F, 0.035), (0, sy * (H - F) / 2, 0.0175), "wood_dark")
        s.box("Bead", (W - 2 * F + 0.012, 0.01, 0.04), (0, sy * (H / 2 - F), 0.02), "metal_brass")
    for sx in (-1, 1):
        s.box("Stile", (F, H - 2 * F, 0.035), (sx * (W - F) / 2, 0, 0.0175), "wood_dark")
        s.box("Bead", (0.01, H - 2 * F + 0.012, 0.04), (sx * (W / 2 - F), 0, 0.02), "metal_brass")
    s.box("Backing", (W - 2 * F + 0.01, H - 2 * F + 0.01, 0.01), (0, 0, 0.008), "wood_dark")
    s.quad("Glass", (W - 2 * F + 0.004, H - 2 * F + 0.004), (0, 0, 0.0145), "p:mirror_dull")
    rnd = random.Random(2)
    for cx, cy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        for k in range(3):
            s.quad("Desilver", (rnd.uniform(0.006, 0.018), rnd.uniform(0.006, 0.014)),
                   (cx * (W / 2 - F - 0.03 - k * 0.015), cy * (H / 2 - F - 0.025 - k * 0.012), 0.0148),
                   "wood_dark", rot=(0, 0, rnd.uniform(0, 90)))
    s.col_box((W, H, 0.04), (0, 0, 0.02))
    s.interactable("base", "Mirror", [
        "The silvering has gone grey at the corners.",
        "A smudge on the glass at about head height.",
    ])
    register("props/hallway/wall_mirror.tscn", s, ORIGIN_WALL, "Interactable",
             "Dull metallic quad, not a true mirror. Add a ReflectionProbe in the level for a better image.")


def blinds() -> None:
    s = Scene("VenetianBlinds", prop_class="wall", script="res://props/architecture/venetian_blinds.gd")
    s.interactable("base", "Blinds", [
        "Venetian blinds, tilted half open. Dust lies along the top of every slat.",
        "One slat near the bottom is bent, as if someone pinched it to look out.",
    ])
    s.bounds = [[-0.45, -1.2, 0.0], [0.45, 0.0, 0.065]]
    register("props/architecture/venetian_blinds.tscn", s, "top centre of head rail, back (wall)",
             "Interactable (scripted, @tool)",
             "Mount inside the window head, origin at the top centre. Exports width, height, raised, "
             "slat_angle, slat_width, slat_pitch, bent_slat, materials. Real slats (MultiMesh) cast striped shadows.")


def curtains() -> None:
    s = Scene("SheerCurtains", prop_class="wall", script="res://props/architecture/curtain_panels.gd",
              root_props=[("width", 1.6), ("height", 1.75), ("rod_offset", 0.07), ("open_amount", 0.0),
                          ("fullness", 2.2), ("pleat_width", 0.08), ("pinch_pleat_header", False)])
    s.nodes[0].props.append(("fabric_material", s.mat("fabric_curtain_sheer")))
    s.nodes[0].props.append(("rod_material", s.mat("metal_painted_white")))
    s.interactable("base", "Sheer curtains", [
        "Sheer curtains. The sun comes straight through them.",
        "The hem is grey where it has brushed the sill for years.",
    ])
    s.bounds = [[-0.84, -1.75, 0.0], [0.84, 0.02, 0.12]]
    register("props/architecture/sheer_curtains.tscn", s, "top centre at the wall, rod height",
             "Interactable (scripted, @tool)",
             "Exports width, height, rod_offset, open_amount, fullness, pleat_width, pinch_pleat_header, "
             "fabric_material, rod_material, show_rod. Transparent: casts no shadow.")
    s = Scene("HeavyDrapes", prop_class="wall", script="res://props/architecture/curtain_panels.gd",
              root_props=[("width", 1.8), ("height", 1.9), ("rod_offset", 0.14), ("open_amount", 0.7),
                          ("fullness", 2.0), ("pleat_width", 0.13), ("pinch_pleat_header", True)])
    s.nodes[0].props.append(("fabric_material", s.mat("fabric_curtain_heavy")))
    s.nodes[0].props.append(("rod_material", s.mat("metal_brass")))
    s.interactable("base", "Drapes", [
        "Heavy rust drapes, pinch-pleated, pulled back to the sides.",
        "The fabric facing the window has faded three shades lighter than the side facing the room.",
    ])
    s.bounds = [[-1.0, -1.9, 0.0], [1.0, 0.03, 0.22]]
    register("props/architecture/heavy_drapes.tscn", s, "top centre at the wall, rod height",
             "Interactable (scripted, @tool)",
             "Same script as sheers. Pair with sheer_curtains (rod_offset 0.07) on the same window.")


def build() -> None:
    coat_rack()
    shoes()
    umbrella_stand()
    key_hooks()
    moving_boxes()
    laundry_basket()
    floor_fan()
    wall_mirror()
    blinds()
    curtains()
