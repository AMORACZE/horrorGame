"""Kitchen and dining props."""
from __future__ import annotations

import math
import random

from tscn import Scene
from common import register, tex, ORIGIN_FLOOR, ORIGIN_TABLE, ORIGIN_WALL

CHROME = "metal_chrome"
VINYL = "p:vinyl_mustard"


def dinette_table() -> None:
    s = Scene("DinetteTable")
    W, D, H = 1.07, 0.76, 0.74
    s.box("Top", (W, 0.028, D), (0, H - 0.014, 0), "laminate_formica")
    for sz in (-1, 1):
        s.box("Band", (W + 0.004, 0.03, 0.004), (0, H - 0.014, sz * (D / 2 + 0.002)), CHROME)
    for sx in (-1, 1):
        s.box("Band", (0.004, 0.03, D + 0.008), (sx * (W / 2 + 0.002), H - 0.014, 0), CHROME)
    s.box("Apron", (W - 0.14, 0.05, D - 0.14), (0, H - 0.053, 0), "metal_dark")
    s.box("LeafSeam", (0.002, 0.0006, D - 0.01), (0, H + 0.0003, 0), "wood_dark")
    s.cyl("Burn", 0.011, 0.0008, (0.41, H + 0.0004, 0.27), "wood_dark", segs=12)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * 0.45, sz * 0.30
            s.rod("Leg", (x * 1.03, 0.012, z * 1.03), (x, H - 0.04, z), 0.019, CHROME, segs=14)
            s.cyl("Foot", 0.021, 0.012, (x * 1.03, 0.006, z * 1.03), "rubber_black", segs=12)
            s.box("Bracket", (0.06, 0.02, 0.06), (x, H - 0.04, z), CHROME)
            s.col_cyl(0.02, H - 0.03, (x, (H - 0.03) / 2, z), name="CollisionLeg")
    s.col_box((W, 0.06, D), (0, H - 0.03, 0))
    s.interactable("base", "Kitchen table", [
        "Formica with a chrome edge. A small round burn near one corner.",
        "Crumbs caught in the seam down the middle, where the leaf would go.",
        "One leg is short. The table rocks toward me when I lean on it.",
    ])
    register("props/kitchen/dinette_table.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Top surface y = 0.74 m. Seats four; chairs tuck in at +-0.45 (x) / +-0.30 (z).")


def dinette_chair() -> None:
    s = Scene("DinetteChair")
    seat_y = 0.45
    s.box("SeatPan", (0.40, 0.02, 0.38), (0, seat_y - 0.05, 0.01), "metal_dark")
    s.box("Seat", (0.42, 0.055, 0.40), (0, seat_y - 0.027, 0.01), VINYL)
    s.cyl("SeatRoll", 0.028, 0.42, (0, seat_y - 0.027, 0.21), VINYL, rot=(0, 0, 90), segs=12)
    s.sphere("SeatCrown", 0.5, (0, seat_y - 0.002, 0.01), VINYL, scale=(0.40, 0.022, 0.38))
    s.box("TapeRepair", (0.10, 0.0012, 0.026), (-0.06, seat_y + 0.0095, 0.06), "p:packing_tape", rot=(0, 25, 0))
    for sx in (-1, 1):
        s.rod("FrontLeg", (sx * 0.19, 0.0, 0.18), (sx * 0.18, seat_y - 0.05, 0.16), 0.011, CHROME, segs=10)
        s.rod("BackLeg", (sx * 0.19, 0.0, -0.20), (sx * 0.18, seat_y - 0.05, -0.17), 0.011, CHROME, segs=10)
        s.rod("Upright", (sx * 0.18, seat_y - 0.05, -0.17), (sx * 0.17, 0.93, -0.25), 0.011, CHROME, segs=10)
        s.rod("SideRail", (sx * 0.18, seat_y - 0.06, 0.16), (sx * 0.18, seat_y - 0.06, -0.17), 0.008, CHROME, segs=8)
        for z in (0.18, -0.20):
            s.cyl("Glide", 0.013, 0.008, (sx * 0.19, 0.004, z), "rubber_black", segs=10)
    g = s.group("BackPad", pos=(0, 0.80, -0.235), rot=(-10, 0, 0))
    s.box("Pad", (0.40, 0.18, 0.045), (0, 0, 0), VINYL, parent=g)
    s.cyl("PadTop", 0.022, 0.40, (0, 0.09, 0), VINYL, rot=(0, 0, 90), parent=g, segs=12)
    s.cyl("PadBottom", 0.022, 0.40, (0, -0.09, 0), VINYL, rot=(0, 0, 90), parent=g, segs=12)
    s.col_box((0.44, seat_y, 0.42), (0, seat_y / 2, 0))
    s.col_box((0.42, 0.48, 0.08), (0, 0.69, -0.22), name="CollisionBack")
    s.interactable("base", "Kitchen chair", [
        "Mustard vinyl on chrome. The seat is split and mended with packing tape.",
        "The vinyl is hot from the sun and sticks to the back of my hand.",
    ])
    register("props/kitchen/dinette_chair.tscn", s, ORIGIN_FLOOR, "Interactable", "Seat height 0.45 m.")


def mug() -> None:
    s = Scene("Mug", root_type="RigidBody3D", prop_class="loose", root_props=[("mass", 0.32)])
    s.cyl("Body", 0.041, 0.094, (0, 0.047, 0), "appliance_harvest_gold", segs=24)
    s.cyl("Stripe", 0.0413, 0.011, (0, 0.072, 0), "p:glaze_brown", segs=24)
    s.torus("Rim", 0.0375, 0.0418, (0, 0.094, 0), "appliance_harvest_gold", ring_segs=6)
    s.cyl("Coffee", 0.0378, 0.002, (0, 0.0925, 0), "p:coffee_dried", segs=24)
    s.torus("Handle", 0.017, 0.025, (0.046, 0.05, 0), "appliance_harvest_gold", rot=(90, 0, 0),
            scale=(0.95, 1, 1.35), ring_segs=8)
    s.col_cyl(0.042, 0.094, (0, 0.047, 0))
    s.interactable("exam", "Mug", prompt="Pick up",
                   description="A harvest-gold mug with a brown stripe. Cold coffee in the bottom with a skin "
                               "on it. The handle has been glued back on.")
    register("props/kitchen/mug.tscn", s, ORIGIN_TABLE, "Examinable (RigidBody3D)", "Loose, nudgeable.")


def drinking_glass() -> None:
    s = Scene("DrinkingGlass", root_type="RigidBody3D", prop_class="loose", root_props=[("mass", 0.22)])
    s.cyl("Body", 0.036, 0.12, (0, 0.06, 0), "glass_dusty", r_bottom=0.031, segs=24, cap_top=False)
    s.cyl("Base", 0.031, 0.012, (0, 0.006, 0), "glass_dusty", segs=24)
    s.torus("Rim", 0.0335, 0.038, (0, 0.12, 0), "glass_dusty", ring_segs=5, rings=24)
    s.cyl("Residue", 0.029, 0.0008, (0, 0.0125, 0), "paper_white", segs=20)
    s.col_cyl(0.035, 0.12, (0, 0.06, 0))
    s.interactable("exam", "Glass", prompt="Pick up",
                   description="An empty tumbler. A dried white ring in the bottom, and a fingerprint near "
                               "the top.")
    register("props/kitchen/drinking_glass.tscn", s, ORIGIN_TABLE, "Examinable (RigidBody3D)", "Loose, nudgeable.")


def _plate(s: Scene, parent: str, band: bool = True) -> None:
    s.cyl("Foot", 0.07, 0.006, (0, 0.003, 0), "ceramic_white", segs=24, parent=parent)
    s.cyl("Body", 0.13, 0.014, (0, 0.013, 0), "ceramic_white", r_bottom=0.085, segs=32, parent=parent)
    if band:
        s.torus("Band", 0.112, 0.121, (0, 0.0202, 0), "p:glaze_brown", scale=(1, 0.12, 1), ring_segs=4,
                rings=32, parent=parent)


def plate() -> None:
    s = Scene("Plate", prop_class="tabletop")
    _plate(s, ".")
    rnd = random.Random(3)
    for k in range(9):
        a, r = rnd.uniform(0, 6.28), rnd.uniform(0.01, 0.08)
        s.box("Crumb", (0.004, 0.002, 0.003), (math.cos(a) * r, 0.0212, math.sin(a) * r), "wood_light",
              rot=(0, rnd.uniform(0, 180), 0))
    s.box("Butter", (0.04, 0.0008, 0.02), (-0.03, 0.0208, -0.02), "appliance_harvest_gold", rot=(0, 20, 0))
    g = s.group("Knife", pos=(0.0, 0.0225, 0.0), rot=(0, 28, 0))
    s.box("Blade", (0.016, 0.002, 0.11), (0, 0, -0.04), CHROME, parent=g)
    s.box("Handle", (0.016, 0.006, 0.09), (0, 0.001, 0.06), CHROME, parent=g)
    s.col_cyl(0.13, 0.03, (0, 0.015, 0))
    s.interactable("exam", "Plate", prompt="Pick up",
                   description="Toast crumbs and a smear of butter. The knife is laid across it, handle "
                               "toward the chair.")
    register("props/kitchen/plate.tscn", s, ORIGIN_TABLE, "Examinable", "With crumbs and a knife.")


def ashtray() -> None:
    s = Scene("Ashtray", prop_class="tabletop")
    AMB = "p:glass_amber"
    s.cyl("Body", 0.078, 0.034, (0, 0.017, 0), AMB, r_bottom=0.072, segs=8)
    s.cyl("Bowl", 0.056, 0.003, (0, 0.016, 0), AMB, segs=24)
    s.torus("Rim", 0.064, 0.08, (0, 0.034, 0), AMB, ring_segs=6, rings=8)
    s.cyl("Ash", 0.03, 0.002, (0.005, 0.0185, -0.004), "plastic_grey", segs=16, scale=(1.3, 1, 0.9))
    g = s.group("Cigarette", pos=(0.03, 0.026, 0.01), rot=(0, 30, -12))
    s.cyl("Paper", 0.0042, 0.03, (-0.012, 0, 0), "paper_white", rot=(0, 0, 90), segs=8, parent=g)
    s.cyl("Filter", 0.0043, 0.02, (0.013, 0, 0), "paper_yellowed", rot=(0, 0, 90), segs=8, parent=g)
    s.col_cyl(0.078, 0.035, (0, 0.0175, 0))
    s.interactable("exam", "Ashtray", prompt="Pick up",
                   description="Heavy amber glass. One cigarette, smoked halfway and put out carefully.")
    register("props/kitchen/ashtray_amber.tscn", s, ORIGIN_TABLE, "Examinable", "70s amber glass.")


CEREAL = """GOLDEN HOOPS
Toasted oat & honey rings
Prairie Mills  -  Net wt 15 oz

FREE glow ruler inside!

Side panel: Nutrition information per serving. Best if used by MAR 94.

Back panel: "HOOP HUNT! How many hoops can you find hiding on the farm?" The answer coupon in the bottom corner has been cut out."""


def cereal_box() -> None:
    s = Scene("CerealBox", prop_class="tabletop")
    W, H, D = 0.19, 0.28, 0.07
    s.box("Box", (W, H, D), (0, H / 2, 0), "cardboard")
    front = tex("cereal_front.png", roughness=0.6)
    side = tex("cereal_side.png", roughness=0.6)
    s.quad("Front", (W, H), (0, H / 2, D / 2 + 0.0005), front)
    s.quad("Back", (W, H), (0, H / 2, -D / 2 - 0.0005), front, rot=(0, 180, 0))
    s.quad("SideR", (D, H), (W / 2 + 0.0005, H / 2, 0), side, rot=(0, 90, 0))
    s.quad("SideL", (D, H), (-W / 2 - 0.0005, H / 2, 0), side, rot=(0, -90, 0))
    s.box("FlapBack", (W, 0.002, D * 0.55), (0, H + 0.012, -D / 2 + 0.012), "cardboard", rot=(-25, 0, 0))
    s.box("FlapFront", (W, 0.002, D * 0.5), (0, H + 0.008, D / 2 - 0.004), "cardboard", rot=(18, 0, 0))
    s.box("Bag", (W - 0.02, 0.03, D - 0.012), (0, H - 0.005, 0), "paper_white")
    s.col_box((W, H + 0.02, D), (0, (H + 0.02) / 2, 0))
    s.interactable("read", "Cereal box", title="Golden Hoops", body=CEREAL, style="print",
                   observations=["The top is folded open. The inner bag is rolled down and clipped."])
    register("props/kitchen/cereal_box.tscn", s, ORIGIN_TABLE, "Readable", "Front faces +Z.")


def fruit_bowl() -> None:
    s = Scene("FruitBowl", prop_class="tabletop")
    s.cyl("Foot", 0.06, 0.012, (0, 0.006, 0), "wood_light")
    s.cyl("Bowl", 0.15, 0.075, (0, 0.0495, 0), "wood_light", r_bottom=0.075, segs=28)
    s.torus("Rim", 0.142, 0.156, (0, 0.087, 0), "wood_light", ring_segs=6, rings=28)
    s.cyl("Inside", 0.142, 0.002, (0, 0.082, 0), "wood_medium", segs=28)
    s.sphere("Apple", 0.038, (-0.05, 0.11, 0.03), "p:fruit_red", scale=(1, 0.92, 1))
    s.sphere("Apple", 0.037, (0.035, 0.105, 0.05), "p:fruit_red", scale=(1, 0.9, 1))
    s.cyl("Bite", 0.017, 0.004, (0.035, 0.105, 0.087), "p:banana_brown", rot=(90, 0, 0), segs=12)
    s.rod("Stem", (-0.05, 0.142, 0.03), (-0.047, 0.158, 0.033), 0.002, "wood_dark", segs=5)
    s.sphere("Orange", 0.041, (0.04, 0.11, -0.05), "p:fruit_orange")
    for k in range(3):
        g = s.group("Banana", pos=(-0.02, 0.135 + k * 0.012, -0.03 + k * 0.012), rot=(0, 30 + k * 8, 4))
        pts = [(-0.10, 0.03), (-0.05, 0.0), (0.02, -0.008), (0.09, 0.012)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            s.rod("Seg", (x0, y0, 0), (x1, y1, 0), 0.017, "p:banana_brown", parent=g, segs=8)
            s.sphere("Joint", 0.017, (x1, y1, 0), "p:banana_brown", parent=g, segs=8, rings=4)
        s.rod("Tip", (-0.10, 0.03, 0), (-0.115, 0.045, 0), 0.006, "wood_dark", parent=g, segs=5)
    s.col_cyl(0.16, 0.18, (0, 0.09, 0))
    s.interactable("base", "Fruit bowl", [
        "The bananas have gone brown all over.",
        "One apple has a single bite out of it. The bite has turned brown.",
        "Fruit flies lift off when I lean close, and settle again.",
    ])
    register("props/kitchen/fruit_bowl.tscn", s, ORIGIN_TABLE, "Interactable", "")


def dish_rack() -> None:
    s = Scene("DishRack", prop_class="tabletop")
    WR = "metal_painted_white"
    W, D = 0.44, 0.32
    s.box("DrainTray", (W + 0.03, 0.018, D + 0.04), (0, 0.009, 0), "plastic_beige")
    s.box("TrayWell", (W - 0.01, 0.002, D), (0, 0.0185, 0), "plastic_white")
    h0 = 0.035
    for sz in (-1, 1):
        s.rod("Rail", (-W / 2, h0, sz * D / 2), (W / 2, h0, sz * D / 2), 0.0035, WR, segs=6)
        s.rod("TopRail", (-W / 2, h0 + 0.10, sz * D / 2), (W / 2, h0 + 0.10, sz * D / 2), 0.003, WR, segs=6)
    for sx in (-1, 1):
        s.rod("EndRail", (sx * W / 2, h0, -D / 2), (sx * W / 2, h0, D / 2), 0.0035, WR, segs=6)
        s.rod("EndTop", (sx * W / 2, h0 + 0.10, -D / 2), (sx * W / 2, h0 + 0.10, D / 2), 0.003, WR, segs=6)
        for sz in (-1, 1):
            s.rod("Post", (sx * W / 2, 0.018, sz * D / 2), (sx * W / 2, h0 + 0.10, sz * D / 2), 0.0035, WR, segs=6)
    for k in range(10):
        x = -W / 2 + 0.02 + k * (W - 0.04) / 9
        s.rod("Rib", (x, h0, -D / 2), (x, h0, D / 2), 0.0025, WR, segs=5)
        for sz in (-0.06, 0.06):
            s.rod("Tine", (x, h0, sz), (x, h0 + 0.075, sz * 1.15), 0.0022, WR, segs=5)
    for k, x in enumerate((-0.17, -0.13, -0.09)):
        g = s.group("Plate", pos=(x + 0.016, h0 + 0.128, 0.0), rot=(0, 0, -78 + k * 4))
        s.cyl("Body", 0.125, 0.014, (0, 0, 0), "ceramic_white", r_bottom=0.085, segs=28, parent=g)
        s.torus("Band", 0.108, 0.117, (0, 0.0068, 0), "p:glaze_brown", scale=(1, 0.12, 1), ring_segs=4,
                rings=28, parent=g)
    s.cyl("Mug", 0.041, 0.094, (0.08, h0 + 0.047 + 0.004, -0.06), "appliance_harvest_gold", rot=(180, 0, 0))
    s.cyl("Glass", 0.036, 0.12, (0.08, h0 + 0.064, 0.07), "glass_dusty", r_bottom=0.031, rot=(180, 0, 0))
    g = s.group("Caddy", pos=(0.175, h0, 0.08))
    s.box("Cup", (0.07, 0.10, 0.07), (0, 0.05, 0), WR, parent=g)
    for k in range(4):
        s.box("Fork", (0.014, 0.12, 0.003), (-0.02 + k * 0.013, 0.12, -0.01 + (k % 2) * 0.02), "metal_chrome",
              rot=(0, k * 20, (k - 1.5) * 4), parent=g)
    s.col_box((W + 0.03, 0.20, D + 0.04), (0, 0.10, 0))
    s.interactable("base", "Dish rack", [
        "Three plates, a glass, a mug. All dry.",
        "A ring of hard-water scale in the drain tray where the water stood.",
    ])
    register("props/kitchen/dish_rack.tscn", s, ORIGIN_TABLE, "Interactable",
             "For the counter (0.91 m) beside the sink; drain lip toward the sink.")


def paper_towel_holder() -> None:
    s = Scene("PaperTowelHolder", prop_class="wall")
    for sx in (-1, 1):
        s.box("Bracket", (0.016, 0.06, 0.06), (sx * 0.152, 0.0, 0.03), "wood_medium")
        s.cyl("BracketEnd", 0.04, 0.016, (sx * 0.152, -0.01, 0.065), "wood_medium", rot=(0, 0, 90), segs=20)
    s.cyl("Rod", 0.011, 0.29, (0, -0.01, 0.07), "wood_medium", rot=(0, 0, 90), segs=12)
    s.cyl("Roll", 0.045, 0.275, (0, -0.01, 0.07), "paper_white", rot=(0, 0, 90), segs=24)
    s.cyl("Core", 0.021, 0.277, (0, -0.01, 0.07), "cardboard", rot=(0, 0, 90), segs=16)
    s.box("Sheet", (0.274, 0.12, 0.0015), (0.0, -0.07, 0.116), "paper_white", rot=(4, 0, 2))
    s.box("TornEdge", (0.27, 0.004, 0.0016), (0.0, -0.132, 0.12), "paper_white", rot=(4, 0, 6))
    s.col_box((0.34, 0.15, 0.13), (0, -0.04, 0.065))
    s.interactable("base", "Paper towels", [
        "Down to the last few sheets on the roll.",
        "The end sheet is torn off crooked.",
    ])
    register("props/kitchen/paper_towel_holder.tscn", s, ORIGIN_WALL, "Interactable",
             "Under a wall cabinet or on the wall at ~1.3 m.")


def percolator() -> None:
    s = Scene("Percolator", prop_class="tabletop")
    s.cyl("Base", 0.08, 0.03, (0, 0.015, 0), "plastic_black", r_bottom=0.085, segs=24)
    s.box("Switch", (0.016, 0.01, 0.006), (0, 0.016, 0.083), "plastic_white")
    s.cyl("Body", 0.056, 0.27, (0, 0.165, 0), "metal_chrome", r_bottom=0.068, segs=28)
    s.torus("Bead", 0.052, 0.06, (0, 0.30, 0), "metal_chrome", ring_segs=6)
    s.cyl("Lid", 0.04, 0.02, (0, 0.31, 0), "metal_chrome", r_bottom=0.056, segs=28)
    s.sphere("Knob", 0.02, (0, 0.335, 0), "glass_dusty", scale=(1, 1.2, 1))
    s.cyl("KnobBase", 0.013, 0.006, (0, 0.321, 0), "plastic_black", segs=12)
    s.box("Handle", (0.022, 0.19, 0.03), (-0.104, 0.18, 0), "plastic_black")
    for y in (0.09, 0.27):
        s.box("HandleArm", (0.05, 0.02, 0.024), (-0.078, y, 0), "plastic_black")
    s.rod("Spout", (0.045, 0.24, 0), (0.088, 0.305, 0), 0.014, "metal_chrome", r1=0.007, segs=10)
    s.rod("Cord", (-0.02, 0.01, -0.08), (-0.06, 0.004, -0.2), 0.003, "rubber_black", segs=6)
    s.rod("Cord", (-0.06, 0.004, -0.2), (-0.03, 0.004, -0.34), 0.003, "rubber_black", segs=6)
    s.col_cyl(0.085, 0.35, (0, 0.175, 0))
    s.interactable("base", "Percolator", [
        "An electric percolator. Coffee still in it, cold, with a skin of oil on top.",
        "The switch on the base is off.",
        "The chrome shows the window, stretched sideways.",
    ])
    register("props/kitchen/percolator.tscn", s, ORIGIN_TABLE, "Interactable", "Cord trails 0.34 m behind (-Z).")


def trash_can() -> None:
    s = Scene("TrashCan")
    s.cyl("Ring", 0.145, 0.025, (0, 0.0125, 0), "metal_dark", segs=28)
    s.cyl("Body", 0.14, 0.40, (0, 0.225, 0), "appliance_avocado", r_bottom=0.135, segs=28)
    s.torus("Bead", 0.136, 0.146, (0, 0.425, 0), "metal_chrome", ring_segs=6, rings=28)
    s.sphere("Lid", 0.145, (0, 0.428, 0), "appliance_avocado", hemi=True, scale=(1, 0.28, 1), segs=28, rings=8)
    s.box("Hinge", (0.06, 0.02, 0.025), (0, 0.43, -0.145), "metal_dark")
    s.box("Pedal", (0.09, 0.012, 0.06), (0, 0.03, 0.165), "metal_chrome", rot=(8, 0, 0))
    s.box("PedalArm", (0.02, 0.012, 0.04), (0, 0.03, 0.13), "metal_dark")
    s.col_cyl(0.15, 0.47, (0, 0.235, 0))
    s.interactable("base", "Trash can", [
        "A step can. The lid won't stay up on its own.",
        "Inside: coffee grounds, an egg carton, the paper backing off a roll of film.",
    ])
    register("props/kitchen/trash_can.tscn", s, ORIGIN_FLOOR, "Interactable", "Pedal faces +Z.")


def build() -> None:
    dinette_table()
    dinette_chair()
    mug()
    drinking_glass()
    plate()
    ashtray()
    cereal_box()
    fruit_bowl()
    dish_rack()
    paper_towel_holder()
    percolator()
    trash_can()
