"""Media and early-90s clutter."""
from __future__ import annotations

import math

from tscn import Scene, Raw
from common import register, tex, ORIGIN_TABLE, ORIGIN_WALL

VHS_W, VHS_H, VHS_D = 0.187, 0.025, 0.103

VHS = [
    ("Lake Pell, July 4 '91",
     "Blue ballpoint on the label: LAKE PELL, JULY 4 1991. SP. The record tab on the back has been snapped off."),
    ("Recital 5/16/92",
     "SPRING RECITAL, 5/16/92, (2nd half only). Wound almost all the way to the end."),
    ("Thanksgiving 1990",
     "THANKSGIVING '90 AT AUNT JO'S. The sticker is lifting at one corner."),
    ("Birthday 6-12-93",
     "BIRTHDAY, 6-12-93, CAKE + YARD, in red felt pen. Rewound to the start."),
    ("Sat. movies / weather",
     "SAT. MOVIES + WEATHER 11PM. Recorded at the slow speed. Older writing under the label shows through."),
    ("8/20/93",
     "Just a date on the label: 8/20/93. The tape is stopped about halfway through."),
]


def _vhs_body(s: Scene, parent: str, idx: int, spine_only: bool = False) -> None:
    s.box("Shell", (VHS_W, VHS_H, VHS_D), (0, VHS_H / 2, 0), "plastic_black", parent=parent)
    s.quad("SpineLabel", (0.150, 0.0185), (0, VHS_H / 2, VHS_D / 2 + 0.0006),
           tex("vhs_spine_%02d.png" % idx, roughness=0.8), parent=parent)
    if not spine_only:
        s.quad("FaceLabel", (0.078, 0.047), (-0.035, VHS_H + 0.0006, 0.004),
               tex("vhs_face_%02d.png" % idx, roughness=0.8), rot=(-90, 0, 0), parent=parent)
        s.quad("Window", (0.062, 0.022), (0.052, VHS_H + 0.0006, -0.006), "glass_dusty", rot=(-90, 0, 0),
               parent=parent)
        for x in (0.032, 0.072):
            s.cyl("Reel", 0.011, 0.001, (x, VHS_H + 0.0001, -0.006), "plastic_white", parent=parent, segs=12)
    s.box("DoorLine", (VHS_W - 0.004, 0.0015, 0.002), (0, VHS_H + 0.0003, -VHS_D / 2 + 0.012), "plastic_grey",
          parent=parent)


def vhs_tapes() -> None:
    for i, (name, desc) in enumerate(VHS, start=1):
        s = Scene("VHSTape", prop_class="tabletop")
        _vhs_body(s, ".", i)
        s.col_box((VHS_W, VHS_H, VHS_D), (0, VHS_H / 2, 0))
        s.interactable("exam", "VHS tape", description=desc, prompt="Pick up",
                       examine_rotation_degrees=(-35, 20, 0))
        register("props/media/vhs_tape_%02d.tscn" % i, s, ORIGIN_TABLE, "Examinable",
                 "Lies flat, spine label toward +Z. Label: %s. To stand it spine-out on a shelf: rotate 90 about Z, offset (0.0125, 0.0935, 0)." % name)


def vhs_stack() -> None:
    s = Scene("VHSStack", prop_class="tabletop")
    layout = [  # (label idx or 0 = unlabelled store tape, sleeve, x, yaw)
        (0, True, 0.004, 2), (3, True, -0.006, -3), (0, False, 0.003, 4), (5, True, -0.002, -1), (1, False, 0.006, 6)]
    y = 0.0
    for k, (idx, sleeve, x, yaw) in enumerate(layout):
        g = s.group("Tape", pos=(x, y, 0), rot=(0, yaw, 0))
        if sleeve:
            s.box("Sleeve", (VHS_W + 0.006, VHS_H + 0.004, VHS_D + 0.004), (0, (VHS_H + 0.004) / 2, -0.002),
                  "paper_white" if k % 2 else "cardboard", parent=g)
            if idx:
                s.quad("SpineLabel", (0.150, 0.0185), (0, (VHS_H + 0.004) / 2, VHS_D / 2 + 0.0008),
                       tex("vhs_spine_%02d.png" % idx, roughness=0.8), parent=g)
            y += VHS_H + 0.004
        else:
            if idx:
                _vhs_body(s, g, idx, spine_only=True)
            else:
                s.box("Shell", (VHS_W, VHS_H, VHS_D), (0, VHS_H / 2, 0), "plastic_black", parent=g)
            y += VHS_H
    s.col_box((0.20, y, 0.11), (0, y / 2, 0))
    s.interactable("base", "Videotapes", [
        "Home tapes. THANKSGIVING '90, SAT. MOVIES, LAKE PELL. Two with no labels at all.",
        "The bottom one is a store-bought movie with the front of the sleeve torn off.",
    ])
    register("props/media/vhs_stack.tscn", s, ORIGIN_TABLE, "Interactable", "Five tapes, ~0.14 m tall.")


def tape_rewinder() -> None:
    s = Scene("TapeRewinder", prop_class="tabletop")
    s.box("Body", (0.23, 0.05, 0.135), (0, 0.025, 0), "plastic_black")
    s.box("Bevel", (0.226, 0.006, 0.131), (0, 0.053, 0), "plastic_grey")
    g = s.group("Tape", pos=(0, 0.043, -0.003))
    s.box("Shell", (VHS_W, VHS_H * 0.5, VHS_D), (0, VHS_H * 0.25, 0), "plastic_black", parent=g)
    s.box("Lid", (0.215, 0.022, 0.122), (0, 0.067, -0.002), "p:smoked_plastic")
    s.cyl("Button", 0.009, 0.006, (0.085, 0.03, 0.068), "p:plastic_red", rot=(90, 0, 0), segs=12)
    s.box("Led", (0.006, 0.004, 0.002), (0.06, 0.035, 0.0685), "p:ir_window")
    s.rod("Cord", (-0.08, 0.01, -0.068), (-0.12, 0.004, -0.16), 0.0022, "rubber_black")
    s.col_box((0.23, 0.08, 0.14), (0, 0.04, 0))
    s.interactable("exam", "Tape rewinder", prompt="Pick up",
                   description="A rewinder with a smoked lid. A tape inside, rewound. The red button on the "
                               "front says EJECT.")
    register("props/media/tape_rewinder.tscn", s, ORIGIN_TABLE, "Examinable", "Next to the VCR.")


def game_console() -> None:
    s = Scene("GameConsole", prop_class="tabletop")
    G, B, R = "plastic_grey", "plastic_black", "rubber_black"
    s.box("Body", (0.25, 0.05, 0.20), (0, 0.027, 0), G)
    s.box("Feet", (0.23, 0.004, 0.18), (0, 0.002, 0), R)
    s.box("TopDeck", (0.18, 0.014, 0.15), (0, 0.059, -0.012), G)
    for k in range(5):
        s.box("Vent", (0.05, 0.002, 0.004), (0.10, 0.0525, -0.06 + k * 0.012), B)
    s.box("BadgeRidge", (0.07, 0.004, 0.018), (0, 0.068, 0.05), G)
    s.box("Slot", (0.125, 0.002, 0.024), (0, 0.0665, -0.03), B)
    s.box("Cartridge", (0.11, 0.075, 0.019), (0, 0.098, -0.03), B)
    s.quad("CartLabelResidue", (0.07, 0.04), (0.004, 0.11, -0.0203), "paper_white")
    s.box("PowerSlider", (0.016, 0.008, 0.012), (-0.07, 0.057, 0.07), "p:plastic_red")
    s.box("ResetButton", (0.016, 0.006, 0.012), (0.07, 0.056, 0.07), B)
    for x in (-0.05, 0.05):
        s.box("Port", (0.028, 0.014, 0.002), (x, 0.022, 0.1005), B)
    pads = [((-0.13, 0.0, 0.32), 14, "straight"), ((0.19, 0.0, 0.40), -32, "coiled")]
    for k, (pos, yaw, cord) in enumerate(pads):
        g = s.group("Controller", pos=pos, rot=(0, yaw, 0))
        s.capsule("Body", 0.03, 0.15, (0, 0.0126, 0), G, rot=(0, 0, 90), scale=(0.42, 1, 1), parent=g)
        s.box("Face", (0.085, 0.004, 0.042), (0, 0.0235, 0), B, parent=g)
        s.box("DpadH", (0.022, 0.004, 0.007), (-0.04, 0.026, 0), B, parent=g)
        s.box("DpadV", (0.007, 0.004, 0.022), (-0.04, 0.026, 0), B, parent=g)
        s.cyl("ButtonA", 0.0065, 0.004, (0.045, 0.026, 0.004), "p:plastic_red", parent=g, segs=12)
        s.cyl("ButtonB", 0.0065, 0.004, (0.028, 0.026, 0.008), "p:plastic_red", parent=g, segs=12)
        s.box("Start", (0.009, 0.003, 0.004), (0.004, 0.0255, 0.004), G, parent=g)
        s.box("Select", (0.009, 0.003, 0.004), (-0.012, 0.0255, 0.004), G, parent=g)
    # Cords from the front ports
    p_port1 = (-0.05, 0.02, 0.10)
    c1 = (-0.13 + 0.0, 0.008, 0.32 - 0.03)
    s.rod("Cord", p_port1, (-0.08, 0.004, 0.16), 0.0025, R, segs=6)
    s.rod("Cord", (-0.08, 0.004, 0.16), c1, 0.0025, R, segs=6)
    p_port2 = (0.05, 0.02, 0.10)
    s.rod("Cord", p_port2, (0.08, 0.004, 0.18), 0.0025, R, segs=6)
    s.rod("Cord", (0.08, 0.004, 0.18), (0.11, 0.004, 0.30), 0.0025, R, segs=6)
    for k, (dx, dz) in enumerate(((0.10, 0.30), (0.115, 0.31), (0.105, 0.325))):
        s.torus("CordCoil", 0.036 + k * 0.002, 0.041 + k * 0.002, (dx, 0.003 + k * 0.004, dz), R,
                rot=(0, 0, 4 * k), ring_segs=5, rings=16)
    s.rod("Cord", (0.13, 0.004, 0.33), (0.17, 0.008, 0.37), 0.0025, R, segs=6)
    s.col_box((0.25, 0.14, 0.20), (0, 0.07, 0))
    s.col_box((0.20, 0.04, 0.10), (-0.13, 0.02, 0.32), rot=(0, 14, 0), name="CollisionPad1")
    s.col_box((0.20, 0.04, 0.12), (0.17, 0.02, 0.38), rot=(0, -32, 0), name="CollisionPad2")
    s.interactable("base", "Game console", [
        "A grey console with no name on it, just a raised strip where a badge would go.",
        "A cartridge in the slot. The label has been peeled off, leaving white fuzz.",
        "Both controllers are plugged in. One cord is pulled straight. The other is still coiled.",
    ])
    register("props/media/game_console.tscn", s, ORIGIN_TABLE, "Interactable",
             "Console 0.25 x 0.20; controllers lie up to 0.45 m in front (+Z). Floor in front of the TV, or the lower bay.")


CASSETTES = [
    "MIX, SUMMER '88 in blue ballpoint. Side A. A loop of tape is pulled loose at the bottom edge.",
    "KITCHEN RADIO 3/90. Side B. The tabs on top have been pushed in so it can't be recorded over.",
]


def _cassette(s: Scene, parent: str, idx: int) -> None:
    s.box("Shell", (0.1003, 0.0125, 0.0635), (0, 0.00625, 0), "plastic_black", parent=parent)
    s.quad("Label", (0.092, 0.052), (0, 0.0131, -0.002), tex("cassette_label_%02d.png" % idx), rot=(-90, 0, 0),
           parent=parent)
    s.box("Edge", (0.06, 0.0045, 0.003), (0, 0.0045, 0.0322), "plastic_grey", parent=parent)


def cassettes() -> None:
    for i, desc in enumerate(CASSETTES, start=1):
        s = Scene("AudioCassette", root_type="RigidBody3D", prop_class="loose",
                  root_props=[("mass", 0.05)])
        _cassette(s, ".", i)
        s.col_box((0.1003, 0.0125, 0.0635), (0, 0.00625, 0))
        s.interactable("exam", "Cassette", description=desc, prompt="Pick up")
        register("props/media/audio_cassette_%02d.tscn" % i, s, ORIGIN_TABLE, "Examinable (RigidBody3D)",
                 "Loose, nudgeable. Layer 3+4.")
    s = Scene("AudioCassettePile", prop_class="tabletop")
    y = 0.0
    for k, yaw in enumerate((3, -6, 9)):
        g = s.group("Case", pos=(0.004 * k, y, 0), rot=(0, yaw, 0))
        s.box("Card", (0.104, 0.013, 0.066), (0, 0.0085, 0), ("p:plastic_teal", "paper_white", "p:plastic_red")[k],
              parent=g)
        s.box("Case", (0.109, 0.017, 0.07), (0, 0.0085, 0), "glass_dusty", parent=g)
        y += 0.017
    g = s.group("Loose", pos=(0.11, 0, 0.03), rot=(0, 28, 0))
    _cassette(s, g, 1)
    g = s.group("Loose", pos=(-0.10, 0, 0.05), rot=(0, -12, 0))
    _cassette(s, g, 2)
    s.col_box((0.33, 0.055, 0.15), (0, 0.0275, 0.02))
    s.interactable("base", "Cassettes", [
        "Three cases and two loose tapes. The loose ones are out of the wrong cases.",
        "Handwritten mixes. Nothing store-bought.",
    ])
    register("props/media/audio_cassette_pile.tscn", s, ORIGIN_TABLE, "Interactable", "")


def tv_remote() -> None:
    s = Scene("TVRemote", root_type="RigidBody3D", prop_class="loose", root_props=[("mass", 0.12)])
    s.box("Body", (0.05, 0.02, 0.20), (0, 0.011, 0), "plastic_black")
    s.cyl("Rounded", 0.025, 0.20, (0, 0.011, 0), "plastic_black", rot=(90, 0, 0), scale=(1, 0.45, 1), segs=12)
    s.box("IRWindow", (0.03, 0.012, 0.002), (0, 0.012, 0.1005), "p:ir_window")
    s.box("Power", (0.012, 0.004, 0.009), (0.012, 0.0225, 0.078), "p:plastic_red")
    for r in range(5):
        for c in range(3):
            s.box("Key", (0.010, 0.003, 0.007), (-0.014 + c * 0.014, 0.0222, 0.05 - r * 0.014), "plastic_grey")
    s.box("Rocker", (0.012, 0.004, 0.026), (-0.012, 0.0225, -0.04), "plastic_grey")
    s.box("Rocker", (0.012, 0.004, 0.026), (0.012, 0.0225, -0.04), "plastic_grey")
    s.box("Tape", (0.052, 0.001, 0.035), (0, 0.0003, -0.06), "p:packing_tape")
    s.col_box((0.05, 0.022, 0.20), (0, 0.011, 0))
    s.interactable("exam", "Remote control", prompt="Pick up",
                   description="The TV remote. The numbers have worn off the 3 and the 4. The battery door is "
                               "held on with tape.",
                   examine_rotation_degrees=(-50, 25, 0))
    register("props/media/tv_remote.tscn", s, ORIGIN_TABLE, "Examinable (RigidBody3D)", "Loose, nudgeable.")


LISTINGS = """SATURDAY AFTERNOON, AUGUST 21

12:00   2  Farm & Market Report
        7  MOVIE: "The Hollow Road" (1958) Two drifters work a ranch for the summer. 2 hrs.
       11  Bowling Showcase
 1:00   4  Calder County Fair Preview
       22  MOVIE: "Pennies for April" (1961) A widow opens a roadside diner. 2 hrs.
 2:00   2  Garden Doctor: late tomatoes
        7  Saturday Matinee: "Captain Orbit and the Glass Moon" (1966)
 3:00   4  Auto Racing: Tri-State 200 (live)
       11  Fix It With Frank: storm doors
 3:30   2  Wildlife Trails
 4:00   7  The Grady Family (rerun) Stan loses the car keys before the reunion.
          (circled in ballpoint)
       38  Cartoon Corner
 5:00   2  4  7  Local News
 5:30   4  Weekend Weather Watch"""


def tv_listings() -> None:
    s = Scene("TVListings", prop_class="tabletop")
    s.box("Pages", (0.135, 0.005, 0.19), (0, 0.0025, 0), "paper_white", rot=(0, -6, 0))
    s.box("Spine", (0.004, 0.0055, 0.19), (-0.0655, 0.00275, -0.007), "paper_yellowed", rot=(0, -6, 0))
    s.quad("Cover", (0.135, 0.19), (0, 0.0052, 0), tex("tv_listings_cover.png"), rot=(-90, -6, 0))
    s.col_box((0.15, 0.01, 0.20), (0, 0.005, 0))
    s.interactable("read", "Screen Weekly", title="Screen Weekly  -  Aug. 21-27, 1993", body=LISTINGS,
                   style="print")
    register("props/media/tv_listings.tscn", s, ORIGIN_TABLE, "Readable", "Digest size, lies flat.")


NEWS = """THE CALDER FALLS REGISTER
Saturday, August 21, 1993  -  35 cents

COUNCIL DELAYS VOTE ON ROUTE 9 STOPLIGHT
Residents to be heard again Sept. 7
The town council put off a decision Thursday on a signal for the Route 9 and Mill Street crossing, after more than forty residents filled the meeting room. "We'd like to hear from the people who drive it every day," council chair Ed Pruitt said.

HEAT ADVISORY EXTENDED THROUGH TUESDAY
Highs in the mid-nineties are expected through the weekend. The county asks residents to check on elderly neighbors and to water lawns only before 8 a.m.

PIE CONTEST WINNERS NAMED BY FAIR BOARD
Ruth Kalb of Orchard Lane took first in fruit pies for the third year running.

LIBRARY ROOF WORK TO BEGIN IN SEPTEMBER
The reading room will close for two weeks while the roof is replaced.

INSIDE: Obituaries 4  -  Weather 2  -  Farm report 6  -  Classifieds 9"""


def newspaper() -> None:
    s = Scene("Newspaper", prop_class="tabletop")
    s.box("Fold", (0.30, 0.008, 0.38), (0, 0.004, 0), "paper_white", rot=(0, 4, 0))
    s.box("Section", (0.295, 0.004, 0.375), (0.01, 0.002, 0.012), "paper_yellowed", rot=(0, -3, 0))
    s.cyl("FoldEdge", 0.004, 0.38, (-0.15, 0.004, 0), "paper_white", rot=(90, 4, 0), segs=8)
    s.quad("Front", (0.30, 0.38), (0, 0.0082, 0), tex("newspaper_front.png", roughness=0.95), rot=(-90, 4, 0))
    s.col_box((0.32, 0.012, 0.40), (0, 0.006, 0))
    s.interactable("read", "Newspaper", title="The Calder Falls Register", body=NEWS, style="print")
    register("props/media/newspaper.tscn", s, ORIGIN_TABLE, "Readable", "Folded once, lies flat.")


CALENDAR = """AUGUST 1993
Compliments of Hollis Hardware & Feed, Calder Falls

Wed 4    Dentist 2:30
Tue 10   pay gas
Sat 14   Carol b-day
Wed 18   oil chg
Tue 24   (circled in red. Nothing written.)
Fri 27   Library bk due"""


def wall_calendar() -> None:
    s = Scene("WallCalendar", prop_class="wall")
    W, H = 0.30, 0.46
    s.cyl("Nail", 0.0025, 0.02, (0, 0.005, 0.01), "metal_dark", rot=(90, 0, 0), segs=6)
    for k in range(3):  # pages behind, slightly fanned
        s.box("Page", (W, H, 0.0008), (0.0, -H / 2 + 0.0, 0.002 + k * 0.001), "paper_white",
              rot=(0, 0, (k - 1) * 0.6))
    s.box("Sheet", (W, H, 0.001), (0, -H / 2, 0.0055), "paper_white")
    s.quad("Face", (W, H), (0, -H / 2, 0.0062), tex("calendar_aug_1993.png", roughness=0.9))
    s.cyl("Binding", 0.003, W - 0.02, (0, -0.004, 0.007), "metal_chrome", rot=(0, 0, 90), segs=8)
    s.col_box((W, H, 0.012), (0, -H / 2, 0.006))
    s.interactable("read", "Calendar", title="August 1993", body=CALENDAR, style="print")
    register("props/media/wall_calendar_aug_1993.tscn", s, "top centre at the nail (wall)", "Readable",
             "Hangs from a nail; origin at the nail, sheet hangs 0.46 m below. Nail ~1.7 m.")


MAIL = """CALDER FALLS WATER & LIGHT
Municipal Utilities Department  -  P.O. Box 40  -  Calder Falls

ACCOUNT  0071-4418-02
SERVICE ADDRESS  1418 WREN HOLLOW RD
BILLING PERIOD  JUL 9 - AUG 9, 1993

PREVIOUS BALANCE ............... 41.06
PAYMENT RECEIVED 07/28 ......... -41.06
CURRENT CHARGES ................ 38.92
AMOUNT DUE BY SEP 3, 1993 ...... 38.92

NOTICE: A meter reader will be on your street on or about August 24. Please leave gates unlocked and keep pets indoors.

Thank you for paying promptly."""


def mail_stack() -> None:
    s = Scene("MailStack", prop_class="tabletop")
    y = 0.0
    items = [("Catalog", (0.21, 0.004, 0.27), "paper_yellowed", None, (0.01, -0.01), 7),
             ("Flyer", (0.20, 0.0008, 0.13), "paper_white", "flyer_market.png", (-0.02, 0.03), -9),
             ("Letter", (0.20, 0.0015, 0.09), "paper_yellowed", "envelope_letter.png", (0.015, -0.02), 4),
             ("Bill", (0.241, 0.0015, 0.105), "paper_white", "envelope_utility.png", (0.0, 0.005), -2)]
    for name, size, mat, t, (x, z), yaw in items:
        g = s.group(name, pos=(x, y, z), rot=(0, yaw, 0))
        s.box("Paper", size, (0, size[1] / 2, 0), mat, parent=g)
        if t:
            s.quad("Print", (size[0], size[2]), (0, size[1] + 0.0004, 0), tex(t), rot=(-90, 0, 0), parent=g)
        y += size[1]
    s.col_box((0.27, 0.02, 0.29), (0, 0.01, 0))
    s.interactable("read", "Mail", title="Calder Falls Water & Light", body=MAIL, style="typed",
                   observations=["A bill on top, a letter under it, a grocery flyer, a catalog."])
    register("props/media/mail_stack.tscn", s, ORIGIN_TABLE, "Readable",
             "Unopened utility bill on top (the reader shows its contents), personal letter, flyer, catalog.")


def note() -> None:
    s = Scene("Note", prop_class="tabletop", script="res://props/media/note.gd")
    s.box("Paper", (0.076, 0.0008, 0.076), (0, 0.0004, 0), "paper_yellowed")
    s.quad("Face", (0.076, 0.076), (0, 0.00085, 0), tex("note_back_by_4.png", roughness=0.9), rot=(-90, 0, 0))
    s.col_box((0.08, 0.006, 0.08), (0, 0.003, 0))
    s.interactable("read", "Note", title="Note", body="Back by 4.", style="handwritten",
                   observations=["A sticky note. Three words in blue ballpoint."])
    register("props/media/note.tscn", s, ORIGIN_TABLE, "Readable (scripted)",
             "Export preset: BACK_BY_4 / SHOPPING_LIST / GUTTERS / DENTIST / CUSTOM (+custom_text, custom_title). "
             "On a wall or fridge: rotate +90 about X (face then points +Z).")


def build() -> None:
    vhs_tapes()
    vhs_stack()
    tape_rewinder()
    game_console()
    cassettes()
    tv_remote()
    tv_listings()
    newspaper()
    wall_calendar()
    mail_stack()
    note()
