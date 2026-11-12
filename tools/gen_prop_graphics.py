#!/usr/bin/env python3
"""Generates the printed graphics used by props/ (labels, covers, pages, pictures).

    python3 tools/gen_prop_graphics.py

Writes PNGs into props/textures/. Everything is drawn from scratch with Pillow
and system fonts; every name, title, brand and line of text is invented.
Deterministic: the same script always produces the same images.
After running, re-import:  godot --headless --audio-driver Dummy --path . --import
"""
from __future__ import annotations

import math
import os
import random
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "props", "textures")

FONT_DIRS = [
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/opentype/tlwg",
]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


SANS = "FreeSans.ttf"
SANS_B = "FreeSansBold.ttf"
SANS_O = "FreeSansOblique.ttf"
SERIF = "FreeSerif.ttf"
SERIF_B = "FreeSerifBold.ttf"
SERIF_I = "FreeSerifItalic.ttf"
MONO = "FreeMono.ttf"
COND = "LiberationSansNarrow-Bold.ttf"
HAND = "Loma-Oblique.otf"
HAND_B = "Loma-BoldOblique.otf"

INK_BLUE = (32, 44, 118)
INK_BLACK = (28, 26, 30)
INK_RED = (150, 30, 30)
MARKER = (22, 22, 26)


def save(img: Image.Image, name: str) -> None:
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name), optimize=True)
    print("wrote", name, img.size)


def paper_noise(img: Image.Image, amount: int = 10, seed: int = 0) -> Image.Image:
    """Adds faint grain and slight unevenness so flat colour reads as paper."""
    rnd = random.Random(seed)
    w, h = img.size
    noise = Image.new("L", (w // 4 + 1, h // 4 + 1))
    noise.putdata([128 + rnd.randint(-amount, amount) for _ in range(noise.width * noise.height)])
    noise = noise.resize((w, h), Image.BILINEAR)
    base = img.convert("RGB")
    grey = Image.merge("RGB", (noise, noise, noise))
    out = Image.blend(base, Image.composite(base, grey, Image.new("L", (w, h), 220)), 0.25)
    return out.convert(img.mode) if img.mode == "RGBA" else out


def hand(draw_img: Image.Image, xy: tuple[float, float], text: str, size: int,
         ink: tuple[int, int, int] = INK_BLUE, seed: int = 1, slant: float = -3.0,
         bold: bool = False, jitter: float = 1.0) -> float:
    """Pseudo-handwriting: each glyph jittered in size, angle and baseline.
    Returns the x after the last glyph."""
    rnd = random.Random(seed)
    x, y = xy
    f_name = HAND_B if bold else HAND
    for ch in text:
        if ch == " ":
            x += size * (0.28 + rnd.uniform(-0.03, 0.06))
            continue
        s = int(size * rnd.uniform(0.92, 1.08))
        f = font(f_name, s)
        box = f.getbbox(ch)
        gw, gh = box[2] + 6, s + s // 2
        g = Image.new("L", (gw + 8, gh + 8), 0)
        ImageDraw.Draw(g).text((4, 4), ch, font=f, fill=255,
                               stroke_width=1 if bold else 0, stroke_fill=255)
        g = g.rotate(slant + rnd.uniform(-5, 5) * jitter, resample=Image.BICUBIC, expand=False)
        col = Image.new("RGBA", g.size, ink + (255,))
        dy = rnd.uniform(-1.5, 1.5) * jitter * size / 20.0
        draw_img.paste(col, (int(x), int(y + dy)), g)
        x += (box[2] - box[0]) + size * 0.06 + rnd.uniform(-1, 1)
    return x


def text_w(t: str, f: ImageFont.FreeTypeFont) -> int:
    b = f.getbbox(t)
    return b[2] - b[0]


def centered(d: ImageDraw.ImageDraw, cx: float, y: float, t: str,
             f: ImageFont.FreeTypeFont, fill) -> None:
    d.text((cx - text_w(t, f) / 2, y), t, font=f, fill=fill)


def wrap(d: ImageDraw.ImageDraw, x: float, y: float, w: float, t: str,
         f: ImageFont.FreeTypeFont, fill, lh: float) -> float:
    words = t.split()
    line = ""
    for wd in words:
        trial = (line + " " + wd).strip()
        if text_w(trial, f) > w and line:
            d.text((x, y), line, font=f, fill=fill)
            y += lh
            line = wd
        else:
            line = trial
    if line:
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def greeked(d: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float,
            lh: float, colour, seed: int) -> None:
    """Rows of grey dashes that stand in for body copy too small to read."""
    rnd = random.Random(seed)
    yy = y
    while yy < y + h:
        xx = x
        end = x + w - (rnd.randint(0, int(w * 0.4)) if rnd.random() < 0.15 else 0)
        while xx < end:
            wl = rnd.randint(int(lh * 0.6), int(lh * 2.6))
            d.rectangle([xx, yy, min(xx + wl, end), yy + max(1, lh * 0.42)], fill=colour)
            xx += wl + lh * 0.45
        yy += lh


# ---------------------------------------------------------------------------
# VHS labels (spine + face) and audio cassette labels
# ---------------------------------------------------------------------------

VHS_LABELS = [
    # (spine text, face lines, ink, sticker colour)
    ("LAKE PELL  JULY 4 '91", ["LAKE PELL", "July 4 1991", "SP"], INK_BLUE, (238, 236, 226)),
    ("Recital  5/16/92", ["Spring recital", "5/16/92", "(2nd half only)"], INK_BLACK, (240, 238, 228)),
    ("THANKSGIVING 1990  Aunt Jo's", ["Thanksgiving '90", "at Aunt Jo's"], INK_BLUE, (236, 226, 190)),
    ("Birthday 6-12-93", ["Birthday", "6-12-93", "cake + yard"], INK_RED, (240, 238, 228)),
    ("Sat. movies / weather", ["Sat. movies", "+ weather 11pm", "EP"], INK_BLACK, (230, 232, 236)),
    ("8/20/93", ["8/20/93"], INK_BLUE, (240, 238, 228)),
]


def gen_vhs() -> None:
    for i, (spine, face, ink, sticker) in enumerate(VHS_LABELS, start=1):
        # Spine label: 145 x 18 mm -> 512 x 64
        img = Image.new("RGBA", (512, 64), sticker + (255,))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 511, 63], outline=(200, 196, 186), width=2)
        for yy in (20, 44):
            d.line([(8, yy), (504, yy)], fill=(210, 200, 205), width=1)
        hand(img, (18, 10), spine, 34, ink, seed=i * 11, bold=(i == 1))
        save(paper_noise(img, 8, i), f"vhs_spine_{i:02d}.png")
        # Face label: 80 x 48 mm -> 400 x 240
        img = Image.new("RGBA", (400, 240), sticker + (255,))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 399, 239], outline=(200, 196, 186), width=3)
        d.rectangle([0, 0, 399, 34], fill=(60, 64, 92))
        d.text((12, 6), "T-120   VIDEO CASSETTE", font=font(SANS_B, 20), fill=(232, 232, 236))
        for k in range(5):
            d.line([(14, 76 + k * 34), (386, 76 + k * 34)], fill=(196, 190, 200), width=1)
        y = 44
        for j, line in enumerate(face):
            hand(img, (24, y), line, 36, ink, seed=i * 31 + j)
            y += 52
        save(paper_noise(img, 8, i + 50), f"vhs_face_{i:02d}.png")


CASSETTE_LABELS = [
    ("MIX  summer '88", "A", INK_BLUE),
    ("Kitchen radio 3/90", "B", INK_BLACK),
]


def gen_cassette() -> None:
    for i, (title, side, ink) in enumerate(CASSETTE_LABELS, start=1):
        img = Image.new("RGBA", (400, 160), (236, 232, 218, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 399, 26], fill=(196, 64, 40))
        d.text((10, 3), "C-90  LOW NOISE", font=font(SANS_B, 18), fill=(250, 240, 220))
        d.text((360, 2), side, font=font(SANS_B, 22), fill=(250, 240, 220))
        d.line([(16, 74), (384, 74)], fill=(180, 170, 170), width=1)
        hand(img, (20, 34), title, 34, ink, seed=200 + i)
        # the two reel windows
        d.rounded_rectangle([110, 92, 290, 140], 14, fill=(40, 36, 34))
        for cx in (150, 250):
            d.ellipse([cx - 16, 100, cx + 16, 132], fill=(220, 214, 200))
            d.ellipse([cx - 7, 109, cx + 7, 123], fill=(40, 36, 34))
        save(paper_noise(img, 6, 300 + i), f"cassette_label_{i:02d}.png")


# ---------------------------------------------------------------------------
# Book spines (atlas of 16, 64 x 512 each). Colours follow the book_cover_a..d
# palette order (i % 4) so the book bodies match.
# ---------------------------------------------------------------------------

BOOK_COLOURS = [(107, 31, 26), (31, 51, 87), (41, 77, 46), (140, 115, 64)]
BOOKS = [
    ("THE SALT YEAR", "R. Whitcombe"),
    ("Home Canning Made Simple", "Dorrit Press"),
    ("WEEKEND CARPENTRY", "H. Lusk"),
    ("Birds of the Eastern Woods", "Field Series"),
    ("THE COPPER HOUR", "Ann Kessel"),
    ("A Quiet County", "M. Farrow"),
    ("Your Lawn, Your Garden", "Greenleaf"),
    ("NORTH OF ELMORE", "J. T. Danner"),
    ("Microwave Cooking for Two", "Kitchen Library"),
    ("THE LONG SHORE", "E. Vantreese"),
    ("Practical Home Wiring", "Revised 1979"),
    ("Hollow Pines", "C. Ambry"),
    ("ROAD ATLAS 1988", "Continental"),
    ("Letters Never Sent", "P. Sorell"),
    ("The Family Medical Guide", "Third Edition"),
    ("Stars Overhead", "L. Oduya"),
]


def gen_spines() -> None:
    atlas = Image.new("RGB", (1024, 512))
    for i, (title, author) in enumerate(BOOKS):
        r, g, b = BOOK_COLOURS[i % 4]
        rnd = random.Random(i)
        shade = rnd.uniform(0.85, 1.15)
        bg = tuple(max(0, min(255, int(c * shade))) for c in (r, g, b))
        sp = Image.new("RGB", (512, 64), bg)  # drawn sideways, rotated after
        d = ImageDraw.Draw(sp)
        light = (226, 210, 160) if i % 3 else (236, 230, 214)
        if i % 2 == 0:
            d.rectangle([10, 6, 14, 57], fill=light)
            d.rectangle([498, 6, 502, 57], fill=light)
        f = font(SERIF_B if i % 2 else SANS_B, 26 if len(title) < 18 else 20)
        d.text((30, 32 - 15), title, font=f, fill=light)
        fa = font(SERIF_I, 18)
        d.text((512 - 26 - text_w(author, fa), 22), author, font=fa, fill=light)
        sp = sp.rotate(-90, expand=True)  # top of book at top of image
        atlas.paste(sp, (i * 64, 0))
    save(paper_noise(atlas, 10, 77), "book_spines.png")


# ---------------------------------------------------------------------------
# Magazines and the TV listings digest
# ---------------------------------------------------------------------------

def gen_magazines() -> None:
    specs = [
        ("hearth & home", "MARCH 1987  $1.95", (178, 62, 52),
         ["Brighten your kitchen for under $50", "12 casseroles the family will ask for", "Quilts: the comeback"]),
        ("TRAIL & TACKLE", "JUNE 1991  $2.50", (40, 88, 70),
         ["Bass on a budget", "The best lakes within a day's drive", "Fixing a leaky canoe"]),
        ("Needlecraft Monthly", "OCT 1984  $1.75", (200, 150, 60),
         ["Granny squares, three ways", "Macrame for the porch", "Holiday patterns inside"]),
    ]
    for k, (name, issue, colour, lines) in enumerate(specs, start=1):
        rnd = random.Random(k * 9)
        img = Image.new("RGB", (300, 400), (232, 226, 210))
        d = ImageDraw.Draw(img)
        # cover photo stand-in: soft blocks of colour
        for _ in range(9):
            x0, y0 = rnd.randint(-40, 260), rnd.randint(70, 360)
            c = tuple(min(255, max(0, v + rnd.randint(-60, 60))) for v in colour)
            d.ellipse([x0, y0, x0 + rnd.randint(80, 200), y0 + rnd.randint(60, 160)], fill=c)
        img = img.filter(ImageFilter.GaussianBlur(6))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 300, 70], fill=colour)
        fs = 40
        while text_w(name, font(SERIF_B, fs)) > 280:
            fs -= 2
        centered(d, 150, 12, name, font(SERIF_B, fs), (250, 246, 236))
        d.text((10, 74), issue, font=font(SANS_B, 14), fill=(30, 30, 30))
        y = 230
        for ln in lines:
            wrap(d, 15, y + 1, 200, ln, font(SANS_B, 18), (20, 20, 20), 22)
            y = wrap(d, 14, y, 200, ln, font(SANS_B, 18), (250, 250, 248), 22) + 8
        save(paper_noise(img, 8, k), f"magazine_{k:02d}.png")

    # TV listings digest cover
    img = Image.new("RGB", (300, 420), (244, 240, 230))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 300, 92], fill=(198, 34, 40))
    centered(d, 150, 4, "SCREEN", font(SANS_B, 52), (255, 255, 255))
    centered(d, 150, 58, "WEEKLY", font(SANS_B, 24), (255, 230, 120))
    d.text((10, 98), "AUG. 21-27, 1993     69c", font=font(SANS_B, 16), fill=(30, 30, 30))
    d.text((10, 118), "TRI-COUNTY EDITION", font=font(SANS, 14), fill=(30, 30, 30))
    # 'photo' of a smiling host, abstracted to shapes
    d.rectangle([20, 146, 280, 330], fill=(120, 150, 190))
    d.ellipse([110, 168, 190, 260], fill=(222, 182, 150))
    d.rectangle([90, 250, 210, 330], fill=(60, 60, 80))
    d.ellipse([104, 156, 196, 210], fill=(90, 60, 40))
    img2 = img.filter(ImageFilter.GaussianBlur(1.2))
    d = ImageDraw.Draw(img2)
    d.text((20, 336), "Fall preview:", font=font(SANS_B, 20), fill=(198, 34, 40))
    d.text((20, 360), "what's new, what's gone", font=font(SANS_B, 18), fill=(30, 30, 30))
    d.text((20, 388), "Complete movie guide inside", font=font(SANS, 15), fill=(30, 30, 30))
    save(paper_noise(img2, 8, 41), "tv_listings_cover.png")


# ---------------------------------------------------------------------------
# Newspaper front (top half, as seen folded on a table)
# ---------------------------------------------------------------------------

def gen_newspaper() -> None:
    w, h = 600, 760
    img = Image.new("RGB", (w, h), (226, 222, 208))
    d = ImageDraw.Draw(img)
    ink = (34, 32, 30)
    centered(d, w / 2, 18, "The Calder Falls Register", font(SERIF_B, 50), ink)
    d.line([(20, 82), (w - 20, 82)], fill=ink, width=3)
    d.text((22, 88), "SATURDAY, AUGUST 21, 1993", font=font(SANS_B, 15), fill=ink)
    d.text((w / 2 - 20, 88), "Vol. 112, No. 233", font=font(SANS, 15), fill=ink)
    d.text((w - 105, 88), "35 CENTS", font=font(SANS_B, 15), fill=ink)
    d.line([(20, 110), (w - 20, 110)], fill=ink, width=1)
    y = 122
    y = wrap(d, 22, y, w - 44, "Council delays vote on Route 9 stoplight", font(SERIF_B, 40), ink, 44)
    d.text((22, y + 2), "Residents to be heard again Sept. 7", font=font(SERIF_I, 20), fill=ink)
    y += 34
    greeked(d, 22, y, 270, 210, 9, (120, 116, 108), 3)
    # photo block
    d.rectangle([310, y, w - 22, y + 170], fill=(150, 146, 136))
    for k in range(14):
        d.line([(310, y + 120 - k), (w - 22, y + 108 - k * 2)], fill=(130, 126, 118))
    d.rectangle([380, y + 70, 420, y + 150], fill=(96, 92, 86))
    d.text((310, y + 176), "Fairgrounds crew readies the grandstand.", font=font(SERIF_I, 13), fill=ink)
    y += 220
    d.line([(20, y), (w - 20, y)], fill=ink, width=1)
    y += 8
    col_w = (w - 44 - 20) / 2
    yl = wrap(d, 22, y, col_w, "Heat advisory extended through Tuesday", font(SERIF_B, 24), ink, 27)
    greeked(d, 22, yl + 4, col_w, 120, 9, (120, 116, 108), 5)
    yr = wrap(d, 22 + col_w + 20, y, col_w, "Pie contest winners named by fair board",
              font(SERIF_B, 24), ink, 27)
    greeked(d, 22 + col_w + 20, yr + 4, col_w, 120, 9, (120, 116, 108), 7)
    y += 190
    d.line([(20, y), (w - 20, y)], fill=ink, width=1)
    y += 8
    yl = wrap(d, 22, y, col_w, "Library roof work to begin in September", font(SERIF_B, 20), ink, 23)
    greeked(d, 22, yl + 4, col_w, 80, 9, (120, 116, 108), 9)
    d.rectangle([22 + col_w + 20, y, w - 22, y + 110], outline=ink, width=2)
    d.text((32 + col_w + 20, y + 8), "INSIDE", font=font(SANS_B, 16), fill=ink)
    for k, t in enumerate(["Obituaries .... 4", "Weather ....... 2", "Classifieds .. 9",
                           "Farm report ... 6"]):
        d.text((32 + col_w + 20, y + 30 + k * 19), t, font=font(MONO, 15), fill=ink)
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    save(paper_noise(img, 12, 9), "newspaper_front.png")


# ---------------------------------------------------------------------------
# Wall calendar, August 1993
# ---------------------------------------------------------------------------

CAL_ENTRIES = {4: "Dentist 2:30", 10: "pay gas", 14: "Carol b-day", 18: "oil chg",
               27: "Library bk due"}
CAL_CIRCLED = 24


def gen_calendar() -> None:
    w, h = 512, 784
    img = Image.new("RGBA", (w, h), (240, 237, 226, 255))
    d = ImageDraw.Draw(img)
    # picture: a lake at a boat dock, painted simply
    pic = Image.new("RGB", (w - 40, 330), (150, 190, 220))
    pd = ImageDraw.Draw(pic)
    for yy in range(160):
        c = (int(150 + yy * 0.4), int(190 + yy * 0.2), int(220 - yy * 0.1))
        pd.line([(0, yy), (pic.width, yy)], fill=c)
    pd.polygon([(0, 170), (90, 120), (170, 150), (260, 100), (380, 160), (472, 130), (472, 190), (0, 190)],
               fill=(70, 100, 80))
    pd.rectangle([0, 180, pic.width, 330], fill=(60, 110, 150))
    rnd = random.Random(4)
    for _ in range(60):
        x = rnd.randint(0, pic.width)
        y = rnd.randint(190, 320)
        pd.line([(x, y), (x + rnd.randint(8, 30), y)], fill=(120, 160, 190))
    pd.polygon([(180, 330), (230, 220), (250, 220), (260, 330)], fill=(120, 90, 60))
    for k in range(6):
        pd.line([(232 - k * 9, 230 + k * 18), (252 + k * 2, 230 + k * 18)], fill=(80, 60, 40), width=3)
    pic = pic.filter(ImageFilter.GaussianBlur(1.5))
    img.paste(pic, (20, 20))
    d.rectangle([20, 20, w - 20, 350], outline=(60, 60, 60), width=1)
    centered(d, w / 2, 362, "AUGUST  1993", font(SERIF_B, 42), (40, 40, 60))
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    gx, gy, cw, ch = 20, 420, (w - 40) / 7, 50
    for k, dn in enumerate(days):
        centered(d, gx + cw * k + cw / 2, gy, dn, font(SANS_B, 14), (150, 30, 30) if k == 0 else (40, 40, 60))
    gy += 22
    # Aug 1, 1993 is a Sunday
    fnum = font(SANS_B, 16)
    for day in range(1, 32):
        idx = day - 1
        row, col = idx // 7, idx % 7
        x0, y0 = gx + col * cw, gy + row * ch
        d.rectangle([x0, y0, x0 + cw, y0 + ch], outline=(150, 150, 150), width=1)
        d.text((x0 + 4, y0 + 2), str(day), font=fnum, fill=(150, 30, 30) if col == 0 else (40, 40, 60))
        if day in CAL_ENTRIES:
            txt = CAL_ENTRIES[day]
            words = txt.split()
            lines = [" ".join(words[:2]), " ".join(words[2:])] if len(txt) > 9 else [txt]
            for li, ln in enumerate(lines):
                if ln:
                    hand(img, (x0 + 4, y0 + 20 + li * 13), ln, 13, INK_BLUE, seed=day, jitter=0.6)
        if day == CAL_CIRCLED:
            d.ellipse([x0 + 2, y0 + 1, x0 + 28, y0 + 22], outline=INK_RED + (255,), width=2)
            d.arc([x0, y0 - 1, x0 + 30, y0 + 24], 300, 40, fill=INK_RED + (255,), width=2)
    centered(d, w / 2, h - 36, "Compliments of HOLLIS HARDWARE & FEED  -  Calder Falls",
             font(SANS_B, 14), (40, 40, 60))
    save(paper_noise(img, 6, 12), "calendar_aug_1993.png")


# ---------------------------------------------------------------------------
# Mail
# ---------------------------------------------------------------------------

def gen_mail() -> None:
    # utility window envelope 240 x 105 mm
    img = Image.new("RGB", (480, 210), (236, 234, 226))
    d = ImageDraw.Draw(img)
    d.text((18, 14), "CALDER FALLS WATER & LIGHT", font=font(SANS_B, 18), fill=(30, 60, 110))
    d.text((18, 36), "P.O. Box 40  Calder Falls", font=font(SANS, 13), fill=(30, 60, 110))
    d.rectangle([380, 14, 460, 66], outline=(90, 90, 90), width=1)
    d.text((388, 22), "BULK RATE", font=font(SANS_B, 11), fill=(60, 60, 60))
    d.text((388, 38), "U.S. POSTAGE", font=font(SANS, 10), fill=(60, 60, 60))
    d.text((388, 50), "PAID", font=font(SANS, 10), fill=(60, 60, 60))
    d.rectangle([60, 100, 320, 170], fill=(214, 216, 212), outline=(170, 170, 170))
    for k, t in enumerate(["R. OSTRANDER", "1418 WREN HOLLOW RD", "CALDER FALLS"]):
        d.text((72, 108 + k * 19), t, font=font(MONO, 16), fill=(30, 30, 30))
    d.text((18, 186), "IMPORTANT ACCOUNT INFORMATION ENCLOSED", font=font(SANS_B, 12), fill=(150, 40, 40))
    save(paper_noise(img, 8, 21), "envelope_utility.png")
    # handwritten personal letter
    img = Image.new("RGBA", (400, 180), (232, 222, 196, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([330, 12, 384, 72], fill=(170, 60, 60, 255))
    d.rectangle([336, 18, 378, 66], fill=(230, 200, 150, 255))
    d.ellipse([300, 18, 360, 62], outline=(60, 60, 60, 255), width=2)
    hand(img, (110, 82), "R. Ostrander", 26, INK_BLACK, seed=5)
    hand(img, (110, 112), "1418 Wren Hollow Rd", 22, INK_BLACK, seed=6)
    hand(img, (110, 138), "Calder Falls", 22, INK_BLACK, seed=7)
    save(paper_noise(img, 8, 22), "envelope_letter.png")
    # grocery flyer
    img = Image.new("RGB", (400, 260), (246, 236, 120))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 400, 60], fill=(200, 40, 30))
    centered(d, 200, 8, "PELL'S MARKET", font(SANS_B, 40), (255, 255, 255))
    d.text((14, 70), "BACK TO SCHOOL SAVINGS", font=font(SANS_B, 22), fill=(200, 40, 30))
    items = [("Ground chuck lb", "1.39"), ("Sweet corn 6 ears", ".99"), ("Lunch bags 50ct", "1.09"),
             ("Cola 2 ltr", ".89")]
    for k, (a, b) in enumerate(items):
        d.text((14, 104 + k * 36), a, font=font(SANS_B, 20), fill=(30, 30, 30))
        d.text((300, 100 + k * 36), b, font=font(SANS_B, 26), fill=(200, 40, 30))
    d.text((14, 240), "Prices good thru 8/24/93", font=font(SANS, 13), fill=(30, 30, 30))
    save(paper_noise(img, 8, 23), "flyer_market.png")


# ---------------------------------------------------------------------------
# Cereal box
# ---------------------------------------------------------------------------

def gen_cereal() -> None:
    w, h = 380, 560
    img = Image.new("RGB", (w, h), (238, 186, 40))
    d = ImageDraw.Draw(img)
    for r in range(260, 0, -20):  # sunburst behind the bowl
        d.ellipse([w / 2 - r, 330 - r, w / 2 + r, 330 + r], fill=(246, 206 - r // 8, 70))
    for k in range(24):
        a = k * math.pi / 12
        d.polygon([(w / 2, 330), (w / 2 + math.cos(a) * 300, 330 + math.sin(a) * 300),
                   (w / 2 + math.cos(a + 0.12) * 300, 330 + math.sin(a + 0.12) * 300)],
                  fill=(250, 220, 90))
    d.rounded_rectangle([20, 22, w - 20, 170], 28, fill=(170, 30, 40))
    centered(d, w / 2, 30, "GOLDEN", font(SANS_B, 64), (255, 236, 150))
    centered(d, w / 2, 96, "HOOPS", font(SANS_B, 64), (255, 255, 255))
    d.text((30, 178), "PRAIRIE MILLS", font=font(SANS_B, 18), fill=(120, 20, 30))
    d.text((w - 150, 178), "NET WT 15 OZ", font=font(SANS_B, 16), fill=(120, 20, 30))
    # bowl with hoops
    d.ellipse([60, 380, w - 60, 470], fill=(240, 240, 250))
    d.pieslice([60, 330, w - 60, 520], 0, 180, fill=(70, 120, 190))
    rnd = random.Random(8)
    for _ in range(40):
        x = rnd.randint(90, w - 110)
        y = rnd.randint(360, 420)
        d.ellipse([x, y, x + 26, y + 20], fill=(214, 150, 50), outline=(160, 100, 30), width=3)
        d.ellipse([x + 9, y + 7, x + 17, y + 13], fill=(240, 240, 250))
    d.ellipse([w - 120, 200, w - 20, 300], fill=(30, 120, 60))
    centered(d, w - 70, 222, "FREE", font(SANS_B, 22), (255, 255, 255))
    centered(d, w - 70, 248, "glow ruler", font(SANS_B, 13), (255, 255, 255))
    centered(d, w - 70, 266, "inside!", font(SANS_B, 13), (255, 255, 255))
    d.text((20, h - 30), "Toasted oat & honey rings", font=font(SANS_B, 18), fill=(120, 20, 30))
    save(paper_noise(img, 8, 31), "cereal_front.png")
    # side panel (nutrition)
    img = Image.new("RGB", (140, 560), (238, 186, 40))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 20, 130, 380], fill=(250, 248, 240), outline=(30, 30, 30), width=2)
    d.text((16, 26), "NUTRITION", font=font(SANS_B, 16), fill=(30, 30, 30))
    d.text((16, 44), "INFORMATION", font=font(SANS_B, 13), fill=(30, 30, 30))
    d.text((16, 62), "PER SERVING", font=font(SANS, 11), fill=(30, 30, 30))
    greeked(d, 16, 84, 108, 280, 10, (90, 90, 90), 4)
    d.rectangle([10, 400, 130, 540], fill=(170, 30, 40))
    d.text((18, 410), "Best if used", font=font(SANS_B, 14), fill=(255, 255, 255))
    d.text((18, 428), "by MAR 94", font=font(SANS_B, 14), fill=(255, 255, 255))
    save(paper_noise(img, 8, 32), "cereal_side.png")


# ---------------------------------------------------------------------------
# Framed pictures (invented paintings)
# ---------------------------------------------------------------------------

def gen_pictures() -> None:
    # A: mountain lake at evening, 70s motel-art style
    w, h = 600, 450
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        c = (int(232 - 60 * t), int(150 - 30 * t), int(90 + 40 * t))
        d.line([(0, y), (w, y)], fill=c)
    d.ellipse([400, 120, 470, 190], fill=(252, 220, 150))
    d.polygon([(0, 260), (120, 120), (210, 200), (330, 80), (470, 230), (600, 150), (600, 300), (0, 300)],
              fill=(90, 70, 100))
    d.polygon([(0, 280), (90, 220), (200, 260), (300, 210), (420, 270), (600, 230), (600, 300), (0, 300)],
              fill=(60, 60, 70))
    for y in range(300, h):
        t = (y - 300) / 150
        d.line([(0, y), (w, y)], fill=(int(160 - 80 * t), int(110 - 50 * t), int(110 - 20 * t)))
    rnd = random.Random(5)
    for _ in range(120):
        x, y = rnd.randint(0, w), rnd.randint(305, h)
        d.line([(x, y), (x + rnd.randint(10, 40), y)], fill=(230, 180, 130))
    for k in range(9):  # pines on the left shore
        x = 10 + k * 22
        d.polygon([(x, 440), (x + 14, 300 + rnd.randint(-20, 20)), (x + 28, 440)], fill=(30, 40, 34))
    img = img.filter(ImageFilter.GaussianBlur(1.6))
    d = ImageDraw.Draw(img)
    hand(img, (w - 90, h - 36), "D. Ruhl", 20, (30, 20, 20), seed=3)
    save(paper_noise(img, 14, 51), "picture_lake.png")

    # B: abstract, 70s rounded stripes in harvest colours
    w, h = 400, 500
    img = Image.new("RGB", (w, h), (232, 220, 196))
    d = ImageDraw.Draw(img)
    cols = [(196, 92, 40), (222, 156, 50), (120, 80, 40), (160, 120, 60), (90, 50, 30)]
    for k, c in enumerate(cols):
        r = 300 - k * 50
        d.pieslice([-r + 40, h - r - 40, r + 40, h + r - 40], 270, 360, fill=c)
    for k, c in enumerate(reversed(cols)):
        r = 160 - k * 28
        d.ellipse([w - 150 - r / 2, 90 - r / 2, w - 150 + r / 2, 90 + r / 2], fill=c)
    d.rectangle([w - 70, 0, w - 50, h], fill=(120, 80, 40))
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    save(paper_noise(img, 10, 52), "picture_abstract.png")

    # C: barn in a field, small print
    w, h = 350, 280
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        if y < 150:
            d.line([(0, y), (w, y)], fill=(int(170 + 50 * t), int(200 + 20 * t), 226))
        else:
            d.line([(0, y), (w, y)], fill=(int(150 - 40 * t), int(160 - 30 * t), 70))
    d.polygon([(0, 160), (120, 140), (240, 155), (350, 138), (350, 170), (0, 175)], fill=(110, 130, 80))
    d.rectangle([180, 100, 270, 170], fill=(150, 50, 40))
    d.polygon([(172, 102), (225, 66), (278, 102)], fill=(90, 70, 60))
    d.rectangle([212, 128, 238, 170], fill=(70, 40, 30))
    d.line([(212, 128), (238, 170)], fill=(220, 210, 190), width=2)
    d.line([(238, 128), (212, 170)], fill=(220, 210, 190), width=2)
    d.rectangle([150, 90, 166, 170], fill=(170, 170, 160))
    d.ellipse([146, 82, 170, 98], fill=(150, 150, 150))
    rnd = random.Random(6)
    for _ in range(300):
        x, y = rnd.randint(0, w), rnd.randint(176, h)
        d.line([(x, y), (x + rnd.randint(-2, 2), y - rnd.randint(4, 10))], fill=(180, 170, 90))
    img = img.filter(ImageFilter.GaussianBlur(1.0))
    save(paper_noise(img, 14, 53), "picture_barn.png")


# ---------------------------------------------------------------------------
# Notes (sticky note / pad sheet)
# ---------------------------------------------------------------------------

NOTES = {
    "back_by_4": ["Back by 4."],
    "shopping": ["milk", "eggs", "D batteries", "film 24 exp", "foil?"],
    "gutters": ["Call about", "gutters - Tues", "ask for Wes"],
    "dentist": ["Dr. Amsel", "moved to Thurs", "10:15"],
    "blank": [],
}


def gen_notes() -> None:
    for key, lines in NOTES.items():
        img = Image.new("RGBA", (256, 256), (246, 228, 120, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 255, 34], fill=(238, 216, 104, 255))
        if not lines:
            rnd = random.Random(99)
            for k in range(4):  # illegible scribble for custom text
                y = 60 + k * 40
                pts = [(20 + j * 9, y + math.sin(j * 1.3 + k) * 6 + rnd.uniform(-3, 3))
                       for j in range(rnd.randint(14, 24))]
                d.line(pts, fill=INK_BLUE + (255,), width=3)
        else:
            size = 44 if len(lines) == 1 else (28 if len(lines) <= 3 else 28)
            y = 70 if len(lines) == 1 else 42
            for k, ln in enumerate(lines):
                hand(img, (16, y), ln, size, INK_BLUE, seed=sum(map(ord, key)) + k, bold=True)
                y += size + 8
        save(paper_noise(img, 6, len(key)), f"note_{key}.png")


# ---------------------------------------------------------------------------
# Marker on cardboard (transparent), Dymo key labels
# ---------------------------------------------------------------------------

def gen_markers() -> None:
    for name, text, cross in [("kitchen", "KITCHEN", False), ("den", "DEN", True)]:
        img = Image.new("RGBA", (512, 200), (0, 0, 0, 0))
        hand(img, (24, 40), text, 84, MARKER, seed=len(text) * 3, bold=True, slant=-2)
        d = ImageDraw.Draw(img)
        if cross:
            d.line([(20, 110), (330, 96)], fill=MARKER + (255,), width=14)
            d.line([(24, 128), (320, 116)], fill=MARKER + (255,), width=10)
        save(img, f"box_marker_{name}.png")


def gen_dymo() -> None:
    img = Image.new("RGBA", (512, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(SANS_B, 26)
    for k, t in enumerate(["HOUSE", "CAR", "SHED", "GARAGE"]):
        cx = 64 + k * 128
        tw = text_w(t, f) + 16
        d.rounded_rectangle([cx - tw / 2, 6, cx + tw / 2, 42], 4, fill=(20, 22, 26, 255))
        centered(d, cx, 9, t, f, (236, 236, 236, 255))
    save(img, "key_dymo_labels.png")


def main() -> None:
    gen_vhs()
    gen_cassette()
    gen_spines()
    gen_magazines()
    gen_newspaper()
    gen_calendar()
    gen_mail()
    gen_cereal()
    gen_pictures()
    gen_notes()
    gen_markers()
    gen_dymo()


if __name__ == "__main__":
    main()
