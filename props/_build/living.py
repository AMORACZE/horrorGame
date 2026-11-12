"""Living room props."""
from __future__ import annotations

import math
import random

from tscn import Scene
from common import register, tex, ORIGIN_FLOOR, ORIGIN_WALL

FLORAL = "fabric_floral_sofa"
CORD = "fabric_corduroy_brown"
OAK = "wood_oak_cabinet"


def sofa() -> None:
    s = Scene("Sofa")
    W, D = 2.10, 0.88
    # Deck and skirt
    s.box("Deck", (W - 0.02, 0.27, D - 0.04), (0, 0.195, 0.0), FLORAL)
    s.box("Skirt", (W - 0.01, 0.13, 0.012), (0, 0.075, D / 2 - 0.012), FLORAL)
    s.box("SkirtWelt", (W - 0.01, 0.012, 0.016), (0, 0.142, D / 2 - 0.01), "fabric_plaid")
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.10)
        s.box("Arm", (0.18, 0.50, D), (x, 0.31, 0), FLORAL)
        s.cyl("ArmRoll", 0.105, D + 0.01, (x, 0.565, 0.005), FLORAL, rot=(90, 0, 0), segs=20)
        s.cyl("ArmScroll", 0.098, 0.018, (x, 0.565, D / 2 + 0.012), FLORAL, rot=(90, 0, 0), segs=20)
        s.box("ArmFront", (0.17, 0.46, 0.018), (x, 0.29, D / 2 + 0.006), FLORAL)
    # Back frame with a rolled top
    s.box("Back", (W - 0.06, 0.44, 0.20), (0, 0.56, -D / 2 + 0.11), FLORAL)
    s.cyl("BackRoll", 0.10, W - 0.06, (0, 0.78, -D / 2 + 0.11), FLORAL, rot=(0, 0, 90), segs=20)
    # Seat cushions, slightly crowned; the left one pressed flatter
    for i, x in enumerate((-0.575, 0.0, 0.575)):
        crown = 0.012 if i == 0 else 0.03
        s.box("SeatCushion", (0.565, 0.12, 0.64), (x, 0.39, 0.085), FLORAL)
        s.sphere("SeatCrown", 0.5, (x, 0.45, 0.085), FLORAL, scale=(0.55, crown * 2, 0.62), segs=20, rings=8)
        s.cyl("SeatFrontRoll", 0.06, 0.565, (x, 0.39, 0.40), FLORAL, rot=(0, 0, 90), segs=12,
              scale=(1, 1, 0.5))
    # Back cushions leaning back
    for i, x in enumerate((-0.575, 0.0, 0.575)):
        g = s.group("BackCushion", pos=(x, 0.45, -0.20), rot=(-9 if i else -12, 0, 0))
        s.box("Pad", (0.56, 0.38, 0.15), (0, 0.19, 0), FLORAL, parent=g)
        s.box("Face", (0.53, 0.34, 0.02), (0, 0.19, 0.08), FLORAL, parent=g)
        s.cyl("TopRoll", 0.075, 0.56, (0, 0.38, 0), FLORAL, rot=(0, 0, 90), scale=(1, 1, 1), parent=g, segs=16)
    # Throw pillow in the right corner
    s.box("ThrowPillow", (0.36, 0.36, 0.11), (0.74, 0.62, -0.05), "fabric_plaid", rot=(-18, -20, 8))
    s.col_box((W, 0.46, D), (0, 0.23, 0))
    s.col_box((W, 0.44, 0.24), (0, 0.67, -D / 2 + 0.12), name="CollisionBack")
    s.col_box((0.21, 0.22, D), (-(W / 2 - 0.105), 0.57, 0), name="CollisionArmL")
    s.col_box((0.21, 0.22, D), ((W / 2 - 0.105), 0.57, 0), name="CollisionArmR")
    s.interactable("base", "Sofa", [
        "The cushion on the left end is pressed flatter than the other two.",
        "Down between the cushions: a dime, a hair elastic, a pen cap.",
        "The fabric is warm where the sun has been on it.",
    ])
    register("props/living/sofa_floral.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Three-seat, seat height 0.45 m. Back against a wall; leave 0.45 m in front for the coffee table.")


def recliner() -> None:
    s = Scene("Recliner")
    s.box("Plinth", (0.78, 0.04, 0.70), (0, 0.02, 0), "wood_dark")
    s.box("Base", (0.90, 0.32, 0.84), (0, 0.20, 0.02), CORD)
    s.box("Footrest", (0.56, 0.24, 0.05), (0, 0.24, 0.455), CORD)
    s.box("FootrestSeam", (0.565, 0.006, 0.052), (0, 0.365, 0.455), "wood_dark")
    for sx in (-1, 1):
        x = sx * 0.37
        s.box("Arm", (0.16, 0.28, 0.86), (x, 0.50, 0.02), CORD)
        s.cyl("ArmPad", 0.088, 0.86, (x, 0.64, 0.025), CORD, rot=(90, 0, 0), segs=16)
        s.cyl("ArmEnd", 0.084, 0.02, (x, 0.64, 0.46), CORD, rot=(90, 0, 0), segs=16)
    s.box("SeatCushion", (0.58, 0.12, 0.62), (0, 0.42, 0.10), CORD)
    s.sphere("SeatCrown", 0.5, (0, 0.475, 0.10), CORD, scale=(0.56, 0.05, 0.6))
    g = s.group("Back", pos=(0, 0.40, -0.30), rot=(-11, 0, 0))
    s.box("Frame", (0.66, 0.64, 0.20), (0, 0.32, 0), CORD, parent=g)
    for k, (y, r) in enumerate(((0.12, 0.08), (0.30, 0.085), (0.50, 0.095))):
        s.cyl("Bolster", r, 0.60, (0, y, 0.11), CORD, rot=(0, 0, 90), parent=g, segs=16)
    s.box("Lever", (0.02, 0.13, 0.035), (0.463, 0.43, 0.24), "wood_dark", rot=(-25, 0, 0))
    s.sphere("LeverKnob", 0.018, (0.463, 0.49, 0.27), "wood_dark")
    s.col_box((0.92, 0.50, 0.88), (0, 0.25, 0.02))
    s.col_box((0.70, 0.64, 0.26), (0, 0.72, -0.33), rot=(-11, 0, 0), name="CollisionBack")
    s.col_box((0.92, 0.20, 0.86), (0, 0.62, 0.02), name="CollisionArms")
    s.interactable("base", "Recliner", [
        "Brown corduroy. The ribs are rubbed flat along both arms.",
        "A dent in the headrest, the shape of the back of a head.",
        "The lever on the side moves halfway and stops.",
    ])
    register("props/living/recliner_corduroy.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Seat height 0.48 m. Footrest folded (static).")


def coffee_table() -> None:
    s = Scene("CoffeeTable")
    W, D, H = 1.20, 0.60, 0.42
    for sx in (-1, 1):
        for sz in (-1, 1):
            s.box("Leg", (0.055, H - 0.02, 0.055), (sx * 0.55, (H - 0.02) / 2, sz * 0.25), OAK)
    for sz in (-1, 1):
        s.box("Apron", (1.04, 0.07, 0.022), (0, H - 0.055, sz * 0.25), OAK)
        s.box("TopRail", (W, 0.026, 0.08), (0, H - 0.013, sz * 0.26), OAK)
        s.box("Chamfer", (W - 0.01, 0.006, 0.012), (0, H - 0.026, sz * 0.296), "wood_medium")
    for sx in (-1, 1):
        s.box("Apron", (0.022, 0.07, 0.44), (sx * 0.55, H - 0.055, 0), OAK)
        s.box("TopRail", (0.08, 0.026, 0.44), (sx * 0.56, H - 0.013, 0), OAK)
    s.box("Glass", (1.04, 0.008, 0.44), (0, H - 0.012, 0), "glass_dusty")
    s.box("Shelf", (1.10, 0.018, 0.50), (0, 0.09, 0), OAK)
    s.cyl("Coaster", 0.045, 0.005, (0.32, 0.1015, 0.08), "cardboard", segs=16)
    s.col_box((W, 0.03, D), (0, H - 0.015, 0))
    s.col_box((1.10, 0.02, 0.50), (0, 0.09, 0), name="CollisionShelf")
    for sx in (-1, 1):
        for sz in (-1, 1):
            s.col_box((0.055, H - 0.03, 0.055), (sx * 0.55, (H - 0.03) / 2, sz * 0.25), name="CollisionLeg")
    s.interactable("base", "Coffee table", [
        "Oak and glass. Dust on the glass, except one clean rectangle about the size of a book.",
        "Rings where glasses stood, overlapping each other.",
        "A coaster on the lower shelf, face down.",
    ])
    register("props/living/coffee_table_oak_glass.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Top surface y = 0.42 m (glass at 0.414). Lower shelf top y = 0.099 m.")


def end_table() -> None:
    s = Scene("EndTable")
    H = 0.58
    for sx in (-1, 1):
        for sz in (-1, 1):
            s.box("Leg", (0.045, H - 0.03, 0.045), (sx * 0.235, (H - 0.03) / 2, sz * 0.235), OAK)
    s.box("Top", (0.56, 0.03, 0.56), (0, H - 0.015, 0), OAK)
    s.box("TopEdge", (0.54, 0.008, 0.54), (0, H - 0.034, 0), "wood_medium")
    s.box("Case", (0.46, 0.11, 0.46), (0, H - 0.09, 0), OAK)
    s.box("DrawerFront", (0.40, 0.085, 0.014), (0, H - 0.09, 0.236), OAK)
    s.sphere("Knob", 0.013, (0, H - 0.09, 0.252), "metal_brass")
    s.box("Shelf", (0.48, 0.018, 0.48), (0, 0.12, 0), OAK)
    s.box("PhoneBook", (0.21, 0.045, 0.27), (-0.06, 0.1515, 0.02), "paper_yellowed", rot=(0, 8, 0))
    s.box("PhoneBookCover", (0.212, 0.002, 0.272), (-0.06, 0.175, 0.02), "plastic_white", rot=(0, 8, 0))
    s.col_box((0.56, 0.15, 0.56), (0, H - 0.075, 0))
    s.col_box((0.48, 0.02, 0.48), (0, 0.12, 0), name="CollisionShelf")
    for sx in (-1, 1):
        for sz in (-1, 1):
            s.col_box((0.045, H - 0.15, 0.045), (sx * 0.235, (H - 0.15) / 2, sz * 0.235), name="CollisionLeg")
    s.interactable("base", "End table", [
        "The drawer opens an inch and catches on something inside.",
        "A white water ring in the varnish on top.",
        "On the lower shelf, the county phone book. 1991.",
    ])
    register("props/living/end_table_oak.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Top surface y = 0.58 m (lamp height). Drawer is a dummy face.")


def entertainment_center() -> None:
    s = Scene("EntertainmentCenter")
    D = 0.55
    zb, zf = -D / 2, D / 2
    T = 0.025
    xs = [-0.76, -0.735, -0.435, -0.41, 0.41, 0.435, 0.735, 0.76]
    top_y = 1.155
    # Carcass verticals
    for k, (a, b) in enumerate(((xs[0], xs[1]), (xs[2], xs[3]), (xs[4], xs[5]), (xs[6], xs[7]))):
        nm = "Side" if k in (0, 3) else "Divider"
        s.box(nm, (b - a, top_y - 0.06, D), ((a + b) / 2, 0.06 + (top_y - 0.06) / 2, 0), OAK)
        s.col_box((b - a, top_y, D), ((a + b) / 2, top_y / 2, 0), name="Collision" + nm)
    s.box("Top", (1.56, 0.03, D + 0.02), (0, top_y + 0.015, 0.01), OAK)
    s.box("TopEdge", (1.56, 0.012, 0.012), (0, top_y + 0.004, D / 2 + 0.016), "wood_medium")
    s.col_box((1.56, 0.03, D + 0.02), (0, top_y + 0.015, 0.01), name="CollisionTop")
    s.box("Plinth", (1.48, 0.06, D - 0.05), (0, 0.03, -0.02), "wood_dark")
    s.box("Bottom", (1.52, T, D), (0, 0.06 + T / 2, 0), OAK)
    s.col_box((1.52, 0.085, D), (0, 0.0425, 0), name="CollisionBase")
    s.box("BackPanel", (1.50, top_y - 0.06, 0.01), (0, 0.06 + (top_y - 0.06) / 2, zb + 0.005), "wood_dark")
    s.col_box((1.50, top_y - 0.06, 0.01), (0, 0.06 + (top_y - 0.06) / 2, zb + 0.005), name="CollisionBack")
    s.cyl("CableHole", 0.035, 0.004, (0, 0.80, zb + 0.0105), "plastic_black", rot=(90, 0, 0))
    s.cyl("CableHole", 0.035, 0.004, (0, 0.40, zb + 0.0105), "plastic_black", rot=(90, 0, 0))
    sd = D - 0.03  # shelves stop short of the front edge
    sz = (zb + 0.01 + zf - 0.02) / 2
    # Centre bay shelves: below VCR bay, below TV bay
    for y in (0.285, 0.47):
        s.box("CentreShelf", (0.82, T, sd), (0, y + T / 2, sz), OAK)
        s.box("ShelfLip", (0.82, 0.03, 0.012), (0, y + T / 2 - 0.003, zf - 0.02), OAK)
        s.col_box((0.82, T, sd), (0, y + T / 2, sz), name="CollisionShelf")
    # Side column shelves
    for sx in (-1, 1):
        cx = sx * 0.585
        for y in (0.40, 0.72):
            s.box("SideShelf", (0.30, T, sd), (cx, y + T / 2, sz), OAK)
            s.col_box((0.30, T, sd), (cx, y + T / 2, sz), name="CollisionShelf")
    # Empty hinge holes where glass doors used to be
    for sx in (-1, 1):
        for y in (0.20, 1.02):
            s.cyl("HingeHole", 0.004, 0.003, (sx * 0.743, y, zf + 0.001), "plastic_black", rot=(90, 0, 0), segs=8)
    s.interactable("base", "Entertainment centre", [
        "Oak veneer. It's lifting a little at one corner of the top.",
        "Cables run out through a hole in the back. More cables than things plugged in.",
        "Hinge holes down the sides where glass doors used to hang.",
    ])
    register("props/living/entertainment_center_oak.tscn", s, ORIGIN_FLOOR, "Interactable",
             "TV bay 0.82 W x 0.66 H x 0.52 D, floor of bay y = 0.495. VCR bay 0.82 x 0.16 x 0.52, "
             "floor y = 0.31. Lower bay 0.82 x 0.20, floor y = 0.085. Side columns 0.30 wide, shelves "
             "at y = 0.085 / 0.425 / 0.745. Compound collision: things placed in the bays are hittable.")


BOOK_MATS = ["book_cover_a", "book_cover_b", "book_cover_c", "book_cover_d"]


def bookshelf() -> None:
    s = Scene("Bookshelf")
    W, D, H = 0.90, 0.30, 1.80
    WM = "wood_medium"
    for sx in (-1, 1):
        s.box("Side", (0.02, H, D), (sx * (W / 2 - 0.01), H / 2, 0), WM)
        s.col_box((0.02, H, D), (sx * (W / 2 - 0.01), H / 2, 0), name="CollisionSide")
    s.box("Top", (W + 0.02, 0.022, D + 0.01), (0, H - 0.011, 0.005), WM)
    s.col_box((W, 0.022, D), (0, H - 0.011, 0), name="CollisionTop")
    s.box("Kick", (W - 0.04, 0.07, 0.02), (0, 0.035, D / 2 - 0.02), WM)
    s.box("Back", (W - 0.04, H - 0.02, 0.006), (0, H / 2, -D / 2 + 0.003), "wood_dark")
    s.col_box((W - 0.04, H, 0.01), (0, H / 2, -D / 2 + 0.005), name="CollisionBack")
    shelf_tops = [0.09, 0.46, 0.81, 1.16, 1.49]
    for y in shelf_tops:
        s.box("Shelf", (W - 0.04, 0.02, D - 0.01), (0, y - 0.01, -0.005), WM)
        s.col_box((W - 0.04, 0.02, D - 0.01), (0, y - 0.01, -0.005), name="CollisionShelf")
    # Spine materials: one atlas, 16 cells
    spines = [s.mat(tex("book_spines.png", uv_scale=(1 / 16, 1), uv_offset=(i / 16, 0), roughness=0.8))
              for i in range(16)]
    rnd = random.Random(1993)
    front = D / 2 - 0.015
    inner_l, inner_r = -W / 2 + 0.025, W / 2 - 0.025

    def row(y0: float, x_start: float, x_end: float, hmin: float, hmax: float, gap_at: float | None = None,
            upside_down: int = -1, lean_end: bool = False) -> None:
        x = x_start
        n = 0
        gapped = False
        while True:
            t = rnd.uniform(0.022, 0.048)
            if x + t > x_end:
                break
            if gap_at is not None and not gapped and x > gap_at:
                x += 0.075  # the gap, two books wide
                gapped = True
                continue
            h = rnd.uniform(hmin, hmax)
            d = rnd.uniform(0.15, 0.21)
            i = rnd.randrange(16)
            g = s.group("Book", pos=(x + t / 2, y0, front - d / 2))
            s.box("Body", (t, h, d), (0, h / 2, 0), BOOK_MATS[i % 4], parent=g)
            s.quad("Spine", (t * 0.98, h * 0.98), (0, h / 2, d / 2 + 0.0008), spines[i], parent=g,
                   rot=(0, 0, 180 if n == upside_down else 0))
            x += t + rnd.uniform(0.0, 0.003)
            n += 1
        if lean_end:
            t, h, d = 0.03, hmax, 0.19
            i = 7
            ang = 14
            g = s.group("BookLeaning", pos=(x + 0.02, y0, front - d / 2), rot=(0, 0, ang))
            s.box("Body", (t, h, d), (0, h / 2, 0), BOOK_MATS[i % 4], parent=g)
            s.quad("Spine", (t * 0.98, h * 0.98), (0, h / 2, d / 2 + 0.0008), spines[i], parent=g)

    row(shelf_tops[0], inner_l, inner_r - 0.01, 0.24, 0.30)
    row(shelf_tops[1], inner_l, inner_r - 0.12, 0.19, 0.25, gap_at=-0.12, lean_end=True)
    row(shelf_tops[2], inner_l, inner_r - 0.02, 0.18, 0.24, upside_down=9)
    row(shelf_tops[3], inner_l + 0.30, inner_r, 0.18, 0.22)
    # Flat stack on the left of shelf 3 and on the top shelf
    for base_y, x0, count in ((shelf_tops[3], inner_l + 0.13, 4), (shelf_tops[4], -0.18, 3)):
        y = base_y
        for k in range(count):
            t = 0.03 + 0.008 * (k % 2)
            w = 0.24 - k * 0.018
            i = (k * 5 + 3) % 16
            g = s.group("BookFlat", pos=(x0 + k * 0.006, y, front - 0.09), rot=(0, (k - 1) * 4, 0))
            s.box("Body", (w, t, 0.18), (0, t / 2, 0), BOOK_MATS[i % 4], parent=g)
            s.quad("Spine", (w * 0.98, t * 0.95), (0, t / 2, 0.0908), spines[i], parent=g, rot=(0, 0, 90))
            y += t
    s.interactable("base", "Bookshelf", [
        "Paperbacks, a road atlas, a medical guide. One book is back on the shelf upside down.",
        "A gap on the second shelf, two books wide. The dust stops at the edges of it.",
        "The spines on the top shelf have faded where the afternoon sun reaches them.",
    ])
    register("props/living/bookshelf.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Shelf tops y = 0.09 / 0.46 / 0.81 / 1.16 / 1.49, top 1.80. Back against a wall.")


def area_rug() -> None:
    s = Scene("AreaRug", root_props=[("metadata/surface", _sn("rug"))])
    W, D = 2.40, 1.70
    s.box("Base", (W, 0.008, D), (0, 0.004, 0), "carpet_beige")
    s.box("Field", (W - 0.26, 0.003, D - 0.26), (0, 0.0095, 0), "fabric_plaid")
    s.box("Inner", (W - 0.40, 0.002, D - 0.40), (0, 0.011, 0), "carpet_beige")
    s.box("Border", (W - 0.52, 0.002, D - 0.52), (0, 0.0118, 0), "carpet_shag_gold")
    s.box("BorderInner", (W - 0.60, 0.002, D - 0.60), (0, 0.0122, 0), "carpet_beige")
    m = s.group("Medallion", pos=(0, 0.0, 0), scale=(1.5, 1, 0.9))
    s.box("Diamond", (0.50, 0.002, 0.50), (0, 0.0128, 0), "carpet_shag_gold", rot=(0, 45, 0), parent=m)
    s.box("Core", (0.28, 0.002, 0.28), (0, 0.0134, 0), "fabric_plaid", rot=(0, 45, 0), parent=m)
    s.box("Eye", (0.10, 0.002, 0.10), (0, 0.014, 0), "carpet_beige", rot=(0, 45, 0), parent=m)
    for sx in (-1, 1):
        for k in range(14):
            z = -D / 2 + 0.06 + k * (D - 0.12) / 13
            s.box("Fringe", (0.07, 0.003, 0.012), (sx * (W / 2 + 0.033), 0.0015, z), "paper_yellowed",
                  rot=(0, (k % 3 - 1) * 9, 0), shadow=False)
    s.col_box((W, 0.012, D), (0, 0.006, 0))
    s.interactable("base", "Rug", [
        "The pile is worn down in a path from the hall to the sofa.",
        "One corner curls up off the floor.",
    ])
    register("props/living/area_rug.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Walkable, 12 mm thick, metadata surface = &\"rug\" on the body. Furniture can stand on it.")


def _sn(v: str):
    from tscn import Raw
    return Raw('&"%s"' % v)


def sunburst_clock() -> None:
    s = Scene("SunburstClock", prop_class="wall", script="res://props/living/sunburst_clock.gd")
    s.cyl("BackPlate", 0.118, 0.026, (0, 0, 0.013), "wood_dark", rot=(90, 0, 0), segs=32)
    s.cyl("Bezel", 0.104, 0.018, (0, 0, 0.032), "metal_brass", rot=(90, 0, 0), segs=32)
    s.cyl("Dial", 0.092, 0.004, (0, 0, 0.042), "plastic_white", rot=(90, 0, 0), segs=32)
    for k in range(12):
        a = math.radians(90 - k * 30)
        big = k % 3 == 0
        s.box("Marker", (0.006 if big else 0.004, 0.016 if big else 0.01, 0.002),
              (math.cos(a) * 0.078, math.sin(a) * 0.078, 0.0445), "plastic_black", rot=(0, 0, k * -30))
    for k in range(24):
        a = math.radians(k * 15)
        c, sn = math.cos(a), math.sin(a)
        if k % 2 == 0:
            r0, r1 = 0.115, 0.30
            s.rod("Ray", (c * r0, sn * r0, 0.02), (c * r1, sn * r1, 0.02), 0.0035, "metal_brass")
            s.sphere("RayTip", 0.013, (c * (r1 + 0.008), sn * (r1 + 0.008), 0.02), "metal_brass", segs=12, rings=6)
        else:
            rm = 0.17
            s.prism("Spike", (0.032, 0.12, 0.008), (c * rm, sn * rm, 0.016), "wood_dark",
                    rot=(0, 0, math.degrees(a) - 90))
    hands = s.group("Hands", pos=(0, 0, 0.047))
    hh = s.group("HourHand", parent=hands)
    s.box("Blade", (0.011, 0.056, 0.0018), (0, 0.022, 0), "plastic_black", parent=hh)
    mh = s.group("MinuteHand", parent=hands, pos=(0, 0, 0.0025))
    s.box("Blade", (0.0075, 0.082, 0.0015), (0, 0.033, 0), "plastic_black", parent=mh)
    sh = s.group("SecondHand", parent=hands, pos=(0, 0, 0.0048))
    s.box("Blade", (0.0022, 0.094, 0.0012), (0, 0.032, 0), "p:plastic_red", parent=sh)
    s.cyl("Cap", 0.0065, 0.006, (0, 0, 0.0075), "metal_brass", rot=(90, 0, 0), parent=hands, segs=12)
    s.col_box((0.62, 0.62, 0.05), (0, 0, 0.025), rot=(0, 0, 0))
    s.interactable("base", "Wall clock", [
        "A sunburst clock. Brass rays and teak spikes. It's running.",
        "The second hand lands a little short of each mark, every time.",
        "Ten to four, near enough.",
    ])
    register("props/living/sunburst_clock.tscn", s, ORIGIN_WALL, "Interactable (scripted)",
             "Hang with centre ~1.9 m. Script: start_hour/start_minute (15:47), stopped, time_scale, "
             "follow_camcorder_clock, tick_sound.")


def _frame(s: Scene, outer_w: float, outer_h: float, fw: float, depth: float, mat: str, parent: str) -> None:
    for sy in (-1, 1):
        s.box("Rail", (outer_w, fw, depth), (0, sy * (outer_h - fw) / 2, depth / 2), mat, parent=parent)
    for sx in (-1, 1):
        s.box("Stile", (fw, outer_h - 2 * fw, depth), (sx * (outer_w - fw) / 2, 0, depth / 2), mat, parent=parent)


def pictures() -> None:
    # A: lake painting in a heavy dark wood frame with a brass lip
    s = Scene("FramedPictureLake", prop_class="wall")
    g = s.group("Frame")
    _frame(s, 0.74, 0.59, 0.07, 0.035, "wood_dark", g)
    _frame(s, 0.61, 0.46, 0.008, 0.038, "metal_brass", g)
    s.box("Backing", (0.62, 0.47, 0.01), (0, 0, 0.012), "cardboard", parent=g)
    s.quad("Canvas", (0.60, 0.45), (0, 0, 0.0175), tex("picture_lake.png", roughness=0.7), parent=g)
    s.col_box((0.74, 0.59, 0.04), (0, 0, 0.02))
    s.interactable("base", "Painting", [
        "A lake at sunset, pines on the near shore. Signed D. Ruhl in the corner.",
        "The colours have gone orange on the side nearer the window.",
        "A lighter rectangle on the wall beside it, where something else used to hang.",
    ])
    register("props/living/framed_picture_lake.tscn", s, ORIGIN_WALL, "Interactable",
             "0.74 x 0.59. Hang centre ~1.55 m.")

    # B: abstract print, thin brass frame and white mat
    s = Scene("FramedPictureAbstract", prop_class="wall")
    g = s.group("Frame")
    _frame(s, 0.50, 0.62, 0.012, 0.022, "metal_brass", g)
    s.box("Mat", (0.48, 0.60, 0.006), (0, 0, 0.012), "paper_white", parent=g)
    s.quad("Print", (0.38, 0.47), (0, 0.005, 0.0154), tex("picture_abstract.png", roughness=0.6), parent=g)
    s.box("Glass", (0.48, 0.60, 0.002), (0, 0, 0.019), "glass_window", parent=g)
    s.box("PriceSticker", (0.03, 0.018, 0.001), (0.215, -0.296, 0.0225), "paper_white")
    s.col_box((0.50, 0.62, 0.03), (0, 0, 0.015))
    s.interactable("base", "Print", [
        "Brown and orange half-circles. It doesn't look like anything.",
        "A price sticker still on the bottom of the frame. $14.99.",
    ])
    register("props/living/framed_picture_abstract.tscn", s, ORIGIN_WALL, "Interactable",
             "0.50 x 0.62, glazed.")

    # C: small barn picture, oak frame, hanging crooked
    s = Scene("FramedPictureBarn", prop_class="wall")
    g = s.group("Frame", rot=(0, 0, -3.5))
    _frame(s, 0.43, 0.36, 0.04, 0.025, OAK, g)
    s.box("Backing", (0.36, 0.29, 0.008), (0, 0, 0.01), "cardboard", parent=g)
    s.quad("Picture", (0.35, 0.28), (0, 0, 0.0145), tex("picture_barn.png", roughness=0.7), parent=g)
    s.box("Glass", (0.355, 0.285, 0.002), (0, 0, 0.017), "glass_window", parent=g)
    s.col_box((0.45, 0.39, 0.03), (0, 0, 0.015), rot=(0, 0, -3.5))
    s.interactable("base", "Picture", [
        "A red barn and a silo. It hangs crooked.",
        "A thumbprint on the glass, low on the left.",
    ])
    register("props/living/framed_picture_barn.tscn", s, ORIGIN_WALL, "Interactable",
             "0.43 x 0.36, hangs 3.5 degrees crooked (built into the scene).")


def macrame_hanger() -> None:
    s = Scene("MacrameHanger", prop_class="wall")
    J = "p:jute"
    s.torus("Ring", 0.022, 0.03, (0, -0.03, 0), "wood_light", rot=(90, 0, 0))
    s.sphere("TopKnot", 0.026, (0, -0.075, 0), J, scale=(1, 1.3, 1))
    pot_top, pot_bot = -0.60, -0.73
    gather = -0.80
    for k in range(4):
        a = math.radians(45 + k * 90)
        ca, sa = math.cos(a), math.sin(a)
        for j, off in enumerate((-0.012, 0.012)):
            px, pz = -sa * off, ca * off
            p0 = (px * 0.3, -0.09, pz * 0.3)
            p1 = (ca * 0.06 + px, -0.32, sa * 0.06 + pz)
            p2 = (ca * 0.112 + px, pot_top - 0.01, sa * 0.112 + pz)
            p3 = (ca * 0.09 + px, pot_bot + 0.01, sa * 0.09 + pz)
            p4 = (0, gather, 0)
            for name, a0, a1 in (("Cord", p0, p1), ("Cord", p1, p2), ("Cord", p2, p3), ("Cord", p3, p4)):
                s.rod(name, a0, a1, 0.0045, J, segs=6)
        # square-knot sinnet along each group
        for t in (0.35, 0.5, 0.65):
            y = -0.09 + (pot_top + 0.09) * t
            r = 0.112 * t
            s.sphere("Knot", 0.013, (ca * r, y, sa * r), J, segs=8, rings=4)
    s.cyl("Pot", 0.10, pot_top - pot_bot, (0, (pot_top + pot_bot) / 2, 0), "brick_red", r_bottom=0.072)
    s.torus("PotRim", 0.092, 0.108, (0, pot_top, 0), "brick_red", ring_segs=6)
    s.cyl("Soil", 0.093, 0.01, (0, pot_top - 0.012, 0), "p:soil_dry")
    s.sphere("GatherKnot", 0.03, (0, gather, 0), J, scale=(1, 1.4, 1))
    for k in range(9):
        a = math.radians(k * 40)
        s.rod("Tassel", (0, gather - 0.02, 0), (math.cos(a) * 0.03, gather - 0.24, math.sin(a) * 0.03), 0.004, J,
              segs=5)
    # Dried fern: a mop of arching fronds that droop over the rim
    from tscn import align_y, mmul, euler
    rnd = random.Random(7)
    for k in range(15):
        a = math.radians(k * 24 + rnd.uniform(-9, 9))
        ca, sa = math.cos(a), math.sin(a)
        reach = rnd.uniform(0.75, 1.1)
        p0 = (ca * 0.02, pot_top - 0.005, sa * 0.02)
        p1 = (ca * 0.11 * reach, pot_top + rnd.uniform(0.05, 0.11), sa * 0.11 * reach)
        p2 = (ca * 0.21 * reach, pot_top + rnd.uniform(-0.02, 0.04), sa * 0.21 * reach)
        p3 = (ca * 0.26 * reach, pot_top - rnd.uniform(0.12, 0.26), sa * 0.26 * reach)
        mat = "p:dried_leaf" if k % 3 else "p:dried_leaf_dark"
        for q0, q1, w0 in ((p0, p1, 0.07), (p1, p2, 0.06), (p2, p3, 0.04)):
            d = [y - x for x, y in zip(q0, q1)]
            ln = math.sqrt(sum(c * c for c in d))
            b = mmul(align_y(d), euler((0, math.degrees(-a) + 90, 0)))
            s.box("Frond", (w0, ln + 0.01, 0.018), [(x + y) / 2 for x, y in zip(q0, q1)], mat, basis=b)
    s.col_cyl(0.24, 0.40, (0, -0.62, 0))
    s.col_box((0.08, 0.5, 0.08), (0, -0.28, 0), name="CollisionCords")
    s.interactable("base", "Macrame hanger", [
        "A macrame hanger with a fern in it. The fern is dry enough to rattle.",
        "The knots are tight and even. Someone took their time over them.",
        "Brown bits of frond on the floor underneath.",
    ])
    register("props/living/macrame_plant_hanger.tscn", s, "hook point (top)", "Interactable",
             "Origin at the ceiling hook; hangs 1.05 m. Ceiling 2.44 m -> pot bottom ~1.7 m.")


def potted_plant() -> None:
    s = Scene("PottedPlantDry")
    s.cyl("Saucer", 0.165, 0.02, (0, 0.01, 0), "brick_red", r_bottom=0.15)
    s.cyl("Pot", 0.17, 0.31, (0, 0.175, 0), "appliance_harvest_gold", r_bottom=0.13, segs=28)
    s.torus("Rim", 0.16, 0.182, (0, 0.33, 0), "appliance_harvest_gold", ring_segs=8, rings=28)
    s.cyl("Soil", 0.158, 0.01, (0, 0.31, 0), "p:soil_dry", segs=28)
    s.cyl("SoilGap", 0.166, 0.012, (0, 0.305, 0), "plastic_black", segs=28, r_bottom=0.16)
    rnd = random.Random(11)
    stems = [((0.03, 0.31, 0.01), (0.07, 1.08, -0.03)), ((-0.04, 0.31, 0.0), (-0.2, 0.92, 0.05)),
             ((0.0, 0.31, -0.04), (0.14, 0.80, -0.15)), ((-0.01, 0.31, 0.04), (-0.03, 0.66, 0.2)),
             ((0.02, 0.31, 0.03), (0.2, 0.7, 0.12))]
    from tscn import align_y
    for si, (p0, p1) in enumerate(stems):
        s.rod("Stem", p0, p1, 0.007, "wood_medium", r1=0.004, segs=6)
        for k in range(7):
            t = 0.3 + k * 0.115
            if t > 1.0:
                break
            at = [a + (b - a) * t for a, b in zip(p0, p1)]
            yaw = math.radians(rnd.uniform(0, 360))
            th = math.radians(rnd.uniform(8, 40) if k < 6 else rnd.uniform(60, 100))
            d = (math.cos(yaw) * math.sin(th), -math.cos(th), math.sin(yaw) * math.sin(th))
            ln = rnd.uniform(0.15, 0.22)
            mat = "p:dried_leaf" if rnd.random() < 0.55 else "p:dried_leaf_dark"
            s.rod("Petiole", at, [a + c * 0.02 for a, c in zip(at, d)], 0.0025, mat, segs=4)
            from tscn import mmul, euler
            basis = mmul(align_y(d), euler((0, rnd.uniform(0, 180), 0)))
            # curl: dried leaves fold along the midrib, so squash the width a little
            s.prism("Leaf", (0.085, ln, 0.004), [a + c * (0.02 + ln / 2) for a, c in zip(at, d)], mat,
                    basis=basis, scale=(rnd.uniform(0.6, 1.0), 1, 1))
    for k in range(5):
        a = rnd.uniform(0, 360)
        r = rnd.uniform(0.22, 0.38)
        s.prism("FallenLeaf", (0.05, 0.13, 0.004), (math.cos(math.radians(a)) * r, 0.003, math.sin(math.radians(a)) * r),
              "p:dried_leaf", rot=(90 + rnd.uniform(-6, 6), rnd.uniform(0, 180), rnd.uniform(-8, 8)))
    s.col_cyl(0.18, 0.34, (0, 0.17, 0))
    s.col_box((0.4, 0.8, 0.4), (0, 0.72, 0), name="CollisionStems")
    s.interactable("base", "Dead plant", [
        "The soil has shrunk away from the sides of the pot.",
        "Leaves on the floor around it, curled up like paper.",
        "A plastic plant tag in the soil, sun-bleached blank.",
    ])
    register("props/living/potted_plant_dry.tscn", s, ORIGIN_FLOOR, "Interactable",
             "Fallen leaves extend ~0.4 m around the pot.")


def magazine_rack() -> None:
    s = Scene("MagazineRack")
    WM = "wood_medium"
    s.box("Base", (0.42, 0.022, 0.28), (0, 0.04, 0), WM)
    for sx in (-1, 1):
        for sz in (-1, 1):
            s.cyl("Foot", 0.014, 0.03, (sx * 0.18, 0.015, sz * 0.11), WM, r_bottom=0.01, segs=10)
        s.box("End", (0.02, 0.34, 0.30), (sx * 0.20, 0.22, 0), WM)
        s.cyl("EndTop", 0.15, 0.02, (sx * 0.20, 0.39, 0), WM, rot=(0, 0, 90), scale=(1, 1, 0.45), segs=24)
    s.box("Divider", (0.38, 0.30, 0.012), (0, 0.20, 0), WM)
    s.cyl("Handle", 0.012, 0.40, (0, 0.44, 0), "metal_brass", rot=(0, 0, 90), segs=12)
    for sx in (-1, 1):
        s.rod("HandlePost", (sx * 0.17, 0.35, 0), (sx * 0.17, 0.44, 0), 0.006, "metal_brass")
    for k, (z, tilt, x) in enumerate(((0.06, 10, -0.02), (0.085, 15, 0.01), (0.11, 20, 0.0))):
        g = s.group("Magazine", pos=(x, 0.051, z), rot=(tilt, 0, 0))
        s.box("Pages", (0.21, 0.28, 0.006), (0, 0.14, 0), "paper_white", parent=g)
        s.quad("Cover", (0.21, 0.28), (0, 0.14, 0.0032), tex("magazine_%02d.png" % (k + 1)), parent=g)
    for k, z in enumerate((-0.06, -0.09)):
        g = s.group("MagazineBack", pos=(0.01 * k, 0.051, z), rot=(-12 - k * 6, 0, 0))
        s.box("Pages", (0.21, 0.28, 0.008), (0, 0.14, 0), "paper_yellowed", parent=g)
    s.col_box((0.42, 0.46, 0.30), (0, 0.23, 0))
    s.interactable("base", "Magazine rack", [
        "Hearth & Home, March 1987. A page corner is folded down at a casserole recipe.",
        "Trail & Tackle, June 1991. The address label has been torn off.",
        "Needlecraft Monthly, 1984. Pattern pieces cut out of the middle pages.",
    ])
    register("props/living/magazine_rack.tscn", s, ORIGIN_FLOOR, "Interactable", "Beside the recliner.")


def build() -> None:
    sofa()
    recliner()
    coffee_table()
    end_table()
    entertainment_center()
    bookshelf()
    area_rug()
    sunburst_clock()
    pictures()
    macrame_hanger()
    potted_plant()
    magazine_rack()
