#!/usr/bin/env python3
"""News image: one picture of Friday 20 November 2026.

A pure-stdlib program (zlib + struct + math only). It draws a newspaper
front page straight into pixels: a 5x7 bitmap font stored as integers
(each row is a 5-bit value), flat-colour pictograms, and the day's biggest
stories, each checked against the morning's reporting (OneTurn, Argus,
SCMP, Dawn, Dunya News, Morningstar, Bajaj Broking). No network, no
clock, no randomness: two runs write byte-identical PNGs.

Layout (1024 x 1024): masthead with the date, a lead panel on the ICJ
genocide ruling, six story panels in a 3 x 2 grid, an "also today"
ticker and a sources line.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (246, 241, 227)
INK = (22, 35, 58)
RED = (179, 38, 30)
TEAL = (14, 110, 106)
NAVY = (29, 78, 137)
AMBER = (217, 142, 4)
GREEN = (46, 125, 50)
PURPLE = (91, 75, 138)
GREY = (112, 116, 120)
WHITE = (255, 255, 255)
CREAM = (232, 222, 196)
LIGHTRED = (244, 214, 210)
LIGHTTEAL = (205, 232, 228)
LIGHTNAVY = (210, 224, 240)
LIGHTAMBER = (248, 232, 196)
LIGHTGREEN = (214, 236, 214)
LIGHTPURPLE = (226, 220, 240)
DARKGREEN = (27, 94, 32)

# ------------------------------------------------------------------ font
# 5x7 bitmap font: each glyph is 7 integers, one per row, bit 4 = left
# column. Uppercase, digits and the punctuation this page needs.
FONT = {
    'A': (14, 17, 17, 31, 17, 17, 17),
    'B': (30, 17, 17, 30, 17, 17, 30),
    'C': (14, 17, 16, 16, 16, 17, 14),
    'D': (30, 17, 17, 17, 17, 17, 30),
    'E': (31, 16, 16, 30, 16, 16, 31),
    'F': (31, 16, 16, 30, 16, 16, 16),
    'G': (14, 17, 16, 23, 17, 17, 15),
    'H': (17, 17, 17, 31, 17, 17, 17),
    'I': (14, 4, 4, 4, 4, 4, 14),
    'J': (7, 2, 2, 2, 2, 18, 12),
    'K': (17, 18, 20, 24, 20, 18, 17),
    'L': (16, 16, 16, 16, 16, 16, 31),
    'M': (17, 27, 21, 21, 17, 17, 17),
    'N': (17, 25, 21, 19, 17, 17, 17),
    'O': (14, 17, 17, 17, 17, 17, 14),
    'P': (30, 17, 17, 30, 16, 16, 16),
    'Q': (14, 17, 17, 17, 21, 18, 13),
    'R': (30, 17, 17, 30, 20, 18, 17),
    'S': (15, 16, 16, 14, 1, 1, 30),
    'T': (31, 4, 4, 4, 4, 4, 4),
    'U': (17, 17, 17, 17, 17, 17, 14),
    'V': (17, 17, 17, 17, 17, 10, 4),
    'W': (17, 17, 17, 21, 21, 21, 10),
    'X': (17, 17, 10, 4, 10, 17, 17),
    'Y': (17, 17, 10, 4, 4, 4, 4),
    'Z': (31, 1, 2, 4, 8, 16, 31),
    '0': (14, 17, 19, 21, 25, 17, 14),
    '1': (4, 12, 4, 4, 4, 4, 14),
    '2': (14, 17, 1, 6, 8, 16, 31),
    '3': (30, 1, 1, 14, 1, 1, 30),
    '4': (2, 6, 10, 18, 31, 2, 2),
    '5': (31, 16, 30, 1, 1, 17, 14),
    '6': (14, 16, 16, 30, 17, 17, 14),
    '7': (31, 1, 2, 4, 8, 8, 8),
    '8': (14, 17, 17, 14, 17, 17, 14),
    '9': (14, 17, 17, 15, 1, 1, 14),
    ' ': (0, 0, 0, 0, 0, 0, 0),
    '.': (0, 0, 0, 0, 0, 12, 12),
    ',': (0, 0, 0, 0, 12, 4, 8),
    ':': (0, 12, 12, 0, 12, 12, 0),
    ';': (0, 12, 12, 0, 12, 4, 8),
    "'": (4, 4, 8, 0, 0, 0, 0),
    '-': (0, 0, 0, 14, 0, 0, 0),
    '/': (1, 2, 2, 4, 8, 8, 16),
    '%': (25, 26, 2, 4, 8, 11, 19),
    '$': (4, 15, 20, 14, 5, 30, 4),
    '+': (0, 4, 4, 31, 4, 4, 0),
    '(': (2, 4, 8, 8, 8, 4, 2),
    ')': (8, 4, 2, 2, 2, 4, 8),
    '!': (4, 4, 4, 4, 4, 0, 4),
    '?': (14, 17, 1, 6, 4, 0, 4),
    '&': (12, 18, 20, 8, 21, 18, 13),
    '=': (0, 0, 31, 0, 31, 0, 0),
    '"': (10, 10, 10, 0, 0, 0, 0),
}

# ------------------------------------------------------------------ canvas
class Canvas:
    """A flat RGB pixel buffer with tiny drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        r, g, b = c
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def hline(self, x, y, w, c, t=1):
        self.fill_rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.fill_rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill_rect(x0, y0, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            d = r * r - (yy - cy) ** 2
            dx = int(d ** 0.5) if d >= 0 else 0
            self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, c)

    def ring(self, cx, cy, r, c, t=3):
        for k in range(t):
            rr = r - k
            for a in range(0, 360, 2):
                x = cx + int(rr * math.cos(math.radians(a)))
                y = cy + int(rr * math.sin(math.radians(a)))
                self.set(x, y, c)

    def tri(self, pts, c):
        (x0, y0), (x1, y1), (x2, y2) = pts
        for y in range(min(y0, y1, y2), max(y0, y1, y2) + 1):
            xs = []
            for (ax, ay), (bx, by) in (((x0, y0), (x1, y1)),
                                       ((x1, y1), (x2, y2)),
                                       ((x2, y2), (x0, y0))):
                if ay != by and min(ay, by) <= y < max(ay, by):
                    xs.append(ax + (y - ay) * (bx - ax) // (by - ay))
            if len(xs) >= 2:
                self.fill_rect(min(xs), y, max(xs) - min(xs) + 1, 1, c)

    # -- text ------------------------------------------------------
    def text(self, x, y, s, scale, c, align="left"):
        s = s.upper()
        adv = 6 * scale
        width = len(s) * adv - scale
        if align == "center":
            x -= width // 2
        elif align == "right":
            x -= width
        for k, ch in enumerate(s):
            rows = FONT.get(ch, FONT[' '])
            ox = x + k * adv
            for row in range(7):
                bits = rows[row]
                for col in range(5):
                    if bits >> (4 - col) & 1:
                        self.fill_rect(ox + col * scale, y + row * scale,
                                       scale, scale, c)
        return width

    def wrap(self, s, max_chars):
        words = s.upper().split()
        lines, cur = [], ""
        for word in words:
            if cur and len(cur) + 1 + len(word) > max_chars:
                lines.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}".strip()
        if cur:
            lines.append(cur)
        return lines


def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 6)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

# ------------------------------------------------------------------ pictograms
def pic_scales(cv, x, y, w, h):
    """Scales of justice: the ICJ genocide ruling."""
    cv.fill_rect(x, y, w, h, LIGHTNAVY)
    cx, cy = x + w // 2, y + h // 2
    cv.fill_rect(cx - 3, y + 10, 6, 52, INK)
    cv.hline(cx - 52, y + 16, 104, INK, 4)
    cv.circle(cx, y + 12, 5, INK)
    for dx in (-52, 52):
        cv.line(cx + dx, y + 18, cx + dx - 14, y + 44, INK, 2)
        cv.line(cx + dx, y + 18, cx + dx + 14, y + 44, INK, 2)
        cv.tri([(cx + dx - 16, y + 44), (cx + dx + 16, y + 44),
                (cx + dx, y + 60)], AMBER)
    cv.fill_rect(cx - 40, y + h - 12, 80, 6, INK)


def pic_summit(cv, x, y, w, h):
    """Three flags on poles: the Shenzhen three-way summit."""
    cv.fill_rect(x, y, w, h, NAVY)
    cv.fill_rect(x, y + h - 16, w, 16, (18, 52, 96))
    cols = (RED, WHITE, AMBER)
    for k, col in enumerate(cols):
        px = x + 66 + k * 84
        cv.vline(px, y + 12, 52, WHITE, 3)
        cv.tri([(px + 3, y + 12), (px + 52, y + 24), (px + 3, y + 36)], col)
    cv.line(x + 40, y + h - 26, x + w - 40, y + h - 26, WHITE, 3)


def pic_chart(cv, x, y, w, h):
    """Falling market bars with one green debut bar."""
    cv.fill_rect(x, y, w, h, LIGHTRED)
    bx0, base = x + 24, y + 44
    cv.hline(bx0 - 8, base, w - 32, INK, 3)
    bars = [("DOW", -2.19, RED), ("S&P", -2.02, RED),
            ("NAS", -2.25, RED), ("ANT", 17.07, GREEN)]
    for k, (name, pct, col) in enumerate(bars):
        bx = bx0 + k * 68
        if pct < 0:
            hgt = min(24, max(8, int(abs(pct) * 6)))
            cv.fill_rect(bx, base, 44, hgt, col)
        else:
            hgt = min(38, max(10, int(abs(pct) * 2)))
            cv.fill_rect(bx, base - hgt, 44, hgt, col)
        cv.text(bx + 22, y + 74, name, 2, INK, "center")


def pic_tower(cv, x, y, w, h):
    """A skyscraper struck by a missile: the Riyadh attack."""
    cv.fill_rect(x, y, w, h, INK)
    for k in range(24):
        cv.set(x + 14 + (k * 113) % (w - 28), y + 8 + (k * 47) % 20,
               (140, 160, 200))
    cx = x + w // 2
    cv.fill_rect(cx - 26, y + 26, 52, 58, (120, 130, 150))
    for yy in range(y + 30, y + 80, 8):
        cv.hline(cx - 22, yy, 44, (200, 210, 225), 2)
    cv.fill_rect(cx - 26, y + 20, 52, 6, AMBER)
    cv.line(cx + 60, y + 6, cx + 8, y + 30, AMBER, 4)
    cv.circle(cx + 8, y + 30, 10, (255, 180, 60))
    cv.circle(cx + 8, y + 30, 5, RED)
    cv.fill_rect(x, y + h - 14, w, 14, (60, 52, 40))


def pic_tanker(cv, x, y, w, h):
    """A tanker on fire in the Strait of Hormuz."""
    cv.fill_rect(x, y, w, h, LIGHTAMBER)
    cv.fill_rect(x, y + h - 30, w, 30, NAVY)
    for k in range(5):
        cv.hline(x + 10 + k * 60, y + h - 22, 34, WHITE, 2)
    cx, cy = x + w // 2, y + h // 2 - 4
    cv.fill_rect(cx - 92, cy - 4, 184, 22, (120, 40, 30))
    cv.fill_rect(cx + 52, cy - 26, 26, 24, (90, 30, 22))
    cv.vline(cx + 64, cy - 38, 14, INK, 3)
    cv.tri([(cx - 30, cy - 4), (cx - 14, cy - 30), (cx + 2, cy - 4)], AMBER)
    cv.tri([(cx + 6, cy - 4), (cx + 18, cy - 26), (cx + 32, cy - 4)], RED)
    cv.circle(cx - 22, cy - 32, 5, (255, 180, 60))


def pic_leaf(cv, x, y, w, h):
    """A leaf crossed out: the fossil phase-out dropped at COP31."""
    cv.fill_rect(x, y, w, h, LIGHTGREEN)
    cx, cy = x + w // 2, y + h // 2
    cv.circle(cx, cy, 30, GREEN)
    cv.line(cx - 20, cy + 18, cx + 20, cy - 18, WHITE, 4)
    cv.line(cx - 22, cy - 16, cx - 8, cy + 4, WHITE, 3)


def pic_cyber(cv, x, y, w, h):
    """A monitor with a warning triangle: the fired cyber chief."""
    cv.fill_rect(x, y, w, h, LIGHTPURPLE)
    cx, cy = x + w // 2, y + h // 2 - 6
    cv.fill_rect(cx - 62, cy - 30, 124, 56, INK)
    cv.fill_rect(cx - 56, cy - 24, 112, 44, (40, 60, 90))
    cv.tri([(cx, cy - 16), (cx - 20, cy + 14), (cx + 20, cy + 14)], AMBER)
    cv.text(cx, cy - 8, "!", 3, INK, "center")
    cv.fill_rect(cx - 24, cy + 30, 48, 6, INK)
    cv.fill_rect(cx - 40, cy + 36, 80, 4, INK)


PICS = {"scales": pic_scales, "summit": pic_summit, "chart": pic_chart,
        "tower": pic_tower, "tanker": pic_tanker, "leaf": pic_leaf,
        "cyber": pic_cyber}

# ------------------------------------------------------------------ stories
# Each story: kicker, headline lines (pre-wrapped, <= 12 chars a line at
# scale 4), summary (wrapped by the renderer), pictogram, panel tint.
STORIES = [
    {"kicker": "DIPLOMACY - SHENZHEN", "pic": "summit", "tint": LIGHTNAVY,
     "head": ["TRUMP, XI,", "PUTIN SIGN", "PEACE PACT"],
     "sum": "FIRST THREE-WAY SUMMIT; NUCLEAR RISK, UN REFORM, ENERGY"},
    {"kicker": "MARKETS - NEW YORK", "pic": "chart", "tint": LIGHTRED,
     "head": ["DOW -1,101;", "S&P FALLS", "6TH DAY"],
     "sum": "BELOW 50,000; ANTHROPIC DEBUT +17% TO $97.17"},
    {"kicker": "CONFLICT - RIYADH", "pic": "tower", "tint": LIGHTPURPLE,
     "head": ["HOUTHI", "MISSILE HITS", "SAUDI TOWER"],
     "sum": "PIF SKYSCRAPER DAMAGED IN RIYADH FINANCIAL DISTRICT"},
    {"kicker": "GULF - HORMUZ", "pic": "tanker", "tint": LIGHTAMBER,
     "head": ["TWO TANKERS", "HIT MINES,", "ON FIRE"],
     "sum": "IRAN WAR ENTERS 9TH MONTH; BRENT $90"},
    {"kicker": "CLIMATE - ANTALYA", "pic": "leaf", "tint": LIGHTGREEN,
     "head": ["COP31 DRAFT", "DROPS FOSSIL", "PHASE-OUT"],
     "sum": "NEGOTIATORS STRIP CALL TO END FOSSIL FUELS"},
    {"kicker": "US - WASHINGTON", "pic": "cyber", "tint": LIGHTTEAL,
     "head": ["WHITE HOUSE", "FIRES CYBER", "CHIEF"],
     "sum": "AFTER WEEK OF TECH OUTAGES RATTLES US"},
]

TICKER = [
    "KENYA DISCHARGES LAST EBOLA PATIENT, 37 DAYS AFTER FIRST CASE",
    "ISRAEL CROSSES YELLOW LINE IN CENTRAL GAZA; 3 KILLED",
    "DENMARK RATIFIES US-GREENLAND SECURITY DEAL",
    "GOLD AT 14-MONTH LOW, $3,685; SILVER -4.8%",
]

# ------------------------------------------------------------------ page
def lead_panel(cv, lx, ly, lw, lh):
    cv.fill_rect(lx, ly, lw, lh, LIGHTNAVY)
    for t in range(2):
        cv.hline(lx, ly + t, lw, INK, 1)
        cv.hline(lx, ly + lh - 1 - t, lw, INK, 1)
        cv.vline(lx + t, ly, lh, INK, 1)
        cv.vline(lx + lw - 1 - t, ly, lh, INK, 1)
    pic_scales(cv, lx + 2, ly + 2, 200, lh - 4)
    tx = lx + 222
    cv.text(tx, ly + 14, "JUSTICE - THE HAGUE", 2, RED)
    cv.text(tx, ly + 38, "COURT: MYANMAR", 5, INK)
    cv.text(tx, ly + 80, "COMMITTED GENOCIDE", 5, RED)
    cv.text(tx, ly + 128, "FIRST SUCH RULING AGAINST A STATE", 2, INK)
    cv.text(tx, ly + 148, "ROHINGYA CASE AT THE WORLD COURT", 2, INK)


def render():
    cv = Canvas(W, H, PAPER)
    # masthead
    cv.text(W // 2, 26, "THE WORLD IN ONE DAY", 3, GREY, "center")
    cv.text(W // 2, 56, "FRIDAY, 20 NOVEMBER 2026", 6, INK, "center")
    cv.hline(28, 116, W - 56, INK, 4)
    cv.hline(28, 124, W - 56, INK, 1)

    # lead: the ICJ genocide ruling
    lead_panel(cv, 28, 134, W - 56, 176)

    # grid of six stories
    gx, gy = 28, 322
    cw, ch, gap = 312, 268, 15
    for n, st in enumerate(STORIES):
        px = gx + (n % 3) * (cw + gap)
        py = gy + (n // 3) * (ch + 8)
        cv.fill_rect(px, py, cw, ch, st["tint"])
        for t in range(2):
            cv.hline(px, py + t, cw, INK, 1)
            cv.hline(px, py + ch - 1 - t, cw, INK, 1)
            cv.vline(px + t, py, ch, INK, 1)
            cv.vline(px + cw - 1 - t, py, ch, INK, 1)
        PICS[st["pic"]](cv, px + 2, py + 2, cw - 4, 88)
        cv.text(px + 14, py + 98, st["kicker"], 2, RED)
        yy = py + 120
        for line in st["head"]:
            cv.text(px + 14, yy, line, 4, INK)
            yy += 32
        for line in cv.wrap(st["sum"], 24):
            cv.text(px + 14, yy, line, 2, INK)
            yy += 15

    # ticker
    ty = 878
    cv.fill_rect(28, ty, W - 56, 112, INK)
    cv.text(48, ty + 12, "ALSO TODAY", 3, AMBER)
    for k, item in enumerate(TICKER):
        ix = 48 + (k % 2) * 484
        iy = ty + 44 + (k // 2) * 34
        cv.fill_rect(ix, iy + 3, 10, 10, AMBER)
        for j, line in enumerate(cv.wrap(item, 38)[:2]):
            cv.text(ix + 18, iy + j * 15, line, 2, WHITE)

    # footer
    cv.hline(28, 1000, W - 56, INK, 1)
    cv.text(W // 2, 1008, "REPORTED ON 20 NOVEMBER 2026 - ONETURN, ARGUS, SCMP, DAWN, DUNYA NEWS",
            2, GREY, "center")
    return cv


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    png = encode_png(render())
    with open(os.path.join(out, "entry.png"), "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
