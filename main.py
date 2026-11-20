#!/usr/bin/env python3
"""One picture of Friday 20 November 2026, drawn from nothing but code.

This program paints a newspaper front page into a pixel buffer using
only the Python standard library. A 5x7 bitmap alphabet lives here as
integers (five bits per row), seven flat-colour pictograms illustrate
the stories, and a small PNG writer turns the buffer into bytes. The
stories are the day's biggest, checked against the morning's reporting
(OneTurn, Argus, SCMP, Dawn, Dunya News, Morningstar, Bajaj Broking).
There is no network, no clock and no randomness in here, so running
the program twice produces the same file byte for byte.

The page is 1024 by 1024: a masthead naming the day, a lead panel on
the World Court's genocide ruling, six stories in a three-by-two grid,
an "also today" strip and a line naming the sources.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

PAL = {
    "paper": (246, 241, 227), "ink": (22, 35, 58),
    "red": (179, 38, 30), "teal": (14, 110, 106),
    "navy": (29, 78, 137), "amber": (217, 142, 4),
    "green": (46, 125, 50), "purple": (91, 75, 138),
    "grey": (112, 116, 120), "white": (255, 255, 255),
    "cream": (232, 222, 196), "rose": (244, 214, 210),
    "mint": (205, 232, 228), "sky": (210, 224, 240),
    "sand": (248, 232, 196), "leaf": (214, 236, 214),
    "lilac": (226, 220, 240), "pine": (27, 94, 32),
}

# ------------------------------------------------------------------ alphabet
# 5x7 bitmap alphabet: every glyph is seven integers, one per row, with
# bit 4 as the left column. Capitals, digits and the punctuation the
# page needs.
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

# ------------------------------------------------------------------ board
class Board:
    """An RGB pixel buffer with a handful of drawing primitives."""

    def __init__(self, width, height, colour):
        self.w, self.h = width, height
        self.buf = bytearray(width * height * 3)
        self.rect(0, 0, width, height, colour)

    def dot(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            off = (y * self.w + x) * 3
            self.buf[off:off + 3] = bytes(colour)

    def rect(self, x, y, w, h, colour):
        xa, ya = max(0, x), max(0, y)
        xb, yb = min(self.w, x + w), min(self.h, y + h)
        row = bytes(colour) * (xb - xa)
        for yy in range(ya, yb):
            off = (yy * self.w + xa) * 3
            self.buf[off:off + len(row)] = row

    def hbar(self, x, y, w, colour, thick=1):
        self.rect(x, y, w, thick, colour)

    def vbar(self, x, y, h, colour, thick=1):
        self.rect(x, y, thick, h, colour)

    def seg(self, x0, y0, x1, y1, colour, thick=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        stepx = 1 if x0 < x1 else -1
        stepy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.rect(x0, y0, thick, thick, colour)
            if x0 == x1 and y0 == y1:
                return
            twice = 2 * err
            if twice >= dy:
                err += dy
                x0 += stepx
            if twice <= dx:
                err += dx
                y0 += stepy

    def disc(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            span = r * r - (yy - cy) ** 2
            half = int(span ** 0.5) if span >= 0 else 0
            self.rect(cx - half, yy, half * 2 + 1, 1, colour)

    def ring(self, cx, cy, r, colour, thick=3):
        for k in range(thick):
            rr = r - k
            for deg in range(0, 360, 2):
                rad = math.radians(deg)
                self.dot(cx + int(rr * math.cos(rad)),
                         cy + int(rr * math.sin(rad)), colour)

    def tri(self, corners, colour):
        (x0, y0), (x1, y1), (x2, y2) = corners
        edges = (((x0, y0), (x1, y1)), ((x1, y1), (x2, y2)),
                 ((x2, y2), (x0, y0)))
        for y in range(min(y0, y1, y2), max(y0, y1, y2) + 1):
            hits = []
            for (ax, ay), (bx, by) in edges:
                if ay != by and min(ay, by) <= y < max(ay, by):
                    hits.append(ax + (y - ay) * (bx - ax) // (by - ay))
            if len(hits) >= 2:
                self.rect(min(hits), y, max(hits) - min(hits) + 1, 1, colour)

    # -- lettering ---------------------------------------------------
    def draw_text(self, x, y, text, scale, colour, align="left"):
        text = text.upper()
        step = 6 * scale
        total = len(text) * step - scale
        if align == "center":
            x -= total // 2
        elif align == "right":
            x -= total
        for pos, ch in enumerate(text):
            rows = FONT.get(ch, FONT[' '])
            ox = x + pos * step
            for row in range(7):
                bits = rows[row]
                for col in range(5):
                    if bits >> (4 - col) & 1:
                        self.rect(ox + col * scale, y + row * scale,
                                  scale, scale, colour)
        return total

    def wrap_text(self, text, width):
        out, cur = [], ""
        for word in text.upper().split():
            if cur and len(cur) + 1 + len(word) > width:
                out.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        if cur:
            out.append(cur)
        return out


def png_bytes(board):
    """Encode the board as a PNG: signature, IHDR, one IDAT, IEND."""
    def piece(tag, data):
        body = struct.pack(">I", len(data)) + tag + data
        return body + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", board.w, board.h, 8, 2, 0, 0, 0)
    stride = board.w * 3
    scanlines = bytearray()
    for y in range(board.h):
        scanlines.append(0)
        scanlines += board.buf[y * stride:(y + 1) * stride]
    blob = zlib.compress(bytes(scanlines), 6)
    return (b"\x89PNG\r\n\x1a\n" + piece(b"IHDR", header)
            + piece(b"IDAT", blob) + piece(b"IEND", b""))

# ------------------------------------------------------------------ pictures
def draw_scales(bd, x, y, w, h):
    """Scales of justice for the World Court ruling."""
    ink, amber = PAL["ink"], PAL["amber"]
    bd.rect(x, y, w, h, PAL["sky"])
    cx, cy = x + w // 2, y + h // 2
    bd.vbar(cx - 2, y + 12, 48, ink, 4)
    bd.hbar(cx - 54, y + 18, 108, ink, 4)
    bd.disc(cx, y + 13, 5, ink)
    for side in (-54, 54):
        bd.seg(cx + side, y + 20, cx + side - 15, y + 46, ink, 2)
        bd.seg(cx + side, y + 20, cx + side + 15, y + 46, ink, 2)
        bd.tri([(cx + side - 17, y + 46), (cx + side + 17, y + 46),
                (cx + side, y + 62)], amber)
    bd.rect(cx - 42, y + h - 12, 84, 6, ink)


def draw_summit(bd, x, y, w, h):
    """Three flags on poles for the Shenzhen summit."""
    bd.rect(x, y, w, h, PAL["navy"])
    bd.rect(x, y + h - 16, w, 16, (18, 52, 96))
    for k, colour in enumerate((PAL["red"], PAL["white"], PAL["amber"])):
        pole = x + 66 + k * 84
        bd.vbar(pole, y + 12, 52, PAL["white"], 3)
        bd.tri([(pole + 3, y + 12), (pole + 52, y + 24),
                (pole + 3, y + 36)], colour)
    bd.seg(x + 40, y + h - 26, x + w - 40, y + h - 26, PAL["white"], 3)


def draw_chart(bd, x, y, w, h):
    """Market bars: three red falls, one green debut."""
    bd.rect(x, y, w, h, PAL["rose"])
    axis = y + 44
    bd.hbar(x + 16, axis, w - 32, PAL["ink"], 3)
    for k, (name, pct, colour) in enumerate(
            (("DOW", -2.19, PAL["red"]), ("S&P", -2.02, PAL["red"]),
             ("NAS", -2.25, PAL["red"]), ("ANT", 17.07, PAL["green"]))):
        bx = x + 24 + k * 68
        if pct < 0:
            tall = min(24, max(8, int(abs(pct) * 6)))
            bd.rect(bx, axis, 44, tall, colour)
        else:
            tall = min(38, max(10, int(abs(pct) * 2)))
            bd.rect(bx, axis - tall, 44, tall, colour)
        bd.draw_text(bx + 22, y + 74, name, 2, PAL["ink"], "center")


def draw_tower(bd, x, y, w, h):
    """A tower struck by a missile over Riyadh."""
    bd.rect(x, y, w, h, PAL["ink"])
    for k in range(24):
        bd.dot(x + 14 + (k * 113) % (w - 28), y + 8 + (k * 47) % 20,
               (140, 160, 200))
    cx = x + w // 2
    bd.rect(cx - 26, y + 26, 52, 58, (120, 130, 150))
    for yy in range(y + 30, y + 80, 8):
        bd.hbar(cx - 22, yy, 44, (200, 210, 225), 2)
    bd.rect(cx - 26, y + 20, 52, 6, PAL["amber"])
    bd.seg(cx + 60, y + 6, cx + 8, y + 30, PAL["amber"], 4)
    bd.disc(cx + 8, y + 30, 10, (255, 180, 60))
    bd.disc(cx + 8, y + 30, 5, PAL["red"])
    bd.rect(x, y + h - 14, w, 14, (60, 52, 40))


def draw_tanker(bd, x, y, w, h):
    """A tanker burning in the Strait of Hormuz."""
    bd.rect(x, y, w, h, PAL["sand"])
    bd.rect(x, y + h - 30, w, 30, PAL["navy"])
    for k in range(5):
        bd.hbar(x + 10 + k * 60, y + h - 22, 34, PAL["white"], 2)
    cx, cy = x + w // 2, y + h // 2 - 4
    bd.rect(cx - 92, cy - 4, 184, 22, (120, 40, 30))
    bd.rect(cx + 52, cy - 26, 26, 24, (90, 30, 22))
    bd.vbar(cx + 64, cy - 38, 14, PAL["ink"], 3)
    bd.tri([(cx - 30, cy - 4), (cx - 14, cy - 30), (cx + 2, cy - 4)],
           PAL["amber"])
    bd.tri([(cx + 6, cy - 4), (cx + 18, cy - 26), (cx + 32, cy - 4)],
           PAL["red"])
    bd.disc(cx - 22, cy - 32, 5, (255, 180, 60))


def draw_leaf(bd, x, y, w, h):
    """A leaf for the COP31 climate talks in Antalya."""
    bd.rect(x, y, w, h, PAL["leaf"])
    cx, cy = x + w // 2, y + h // 2
    bd.disc(cx, cy, 30, PAL["green"])
    bd.seg(cx - 20, cy + 18, cx + 20, cy - 18, PAL["white"], 4)
    bd.seg(cx - 22, cy - 16, cx - 8, cy + 4, PAL["white"], 3)


def draw_cyber(bd, x, y, w, h):
    """A monitor flashing a warning for the fired cyber chief."""
    bd.rect(x, y, w, h, PAL["lilac"])
    cx, cy = x + w // 2, y + h // 2 - 6
    bd.rect(cx - 62, cy - 30, 124, 56, PAL["ink"])
    bd.rect(cx - 56, cy - 24, 112, 44, (40, 60, 90))
    bd.tri([(cx, cy - 16), (cx - 20, cy + 14), (cx + 20, cy + 14)],
           PAL["amber"])
    bd.draw_text(cx, cy - 8, "!", 3, PAL["ink"], "center")
    bd.rect(cx - 24, cy + 30, 48, 6, PAL["ink"])
    bd.rect(cx - 40, cy + 36, 80, 4, PAL["ink"])


DRAW = {"scales": draw_scales, "summit": draw_summit, "chart": draw_chart,
        "tower": draw_tower, "tanker": draw_tanker, "leaf": draw_leaf,
        "cyber": draw_cyber}

# ------------------------------------------------------------------ stories
# Every story is one tuple: kicker, picture key, panel tint, headline
# lines (already wrapped, at most 12 characters each at scale 4) and a
# one-line summary the renderer wraps itself.
STORIES = [
    ("DIPLOMACY - SHENZHEN", "summit", "sky",
     ("TRUMP, XI,", "PUTIN SIGN", "PEACE PACT"),
     "FIRST THREE-WAY SUMMIT; NUCLEAR RISK, UN REFORM, ENERGY"),
    ("MARKETS - NEW YORK", "chart", "rose",
     ("DOW -1,101;", "S&P FALLS", "6TH DAY"),
     "BELOW 50,000; ANTHROPIC DEBUT +17% TO $97.17"),
    ("CONFLICT - RIYADH", "tower", "lilac",
     ("HOUTHI", "MISSILE HITS", "SAUDI TOWER"),
     "PIF SKYSCRAPER DAMAGED IN RIYADH FINANCIAL DISTRICT"),
    ("GULF - HORMUZ", "tanker", "sand",
     ("TWO TANKERS", "HIT MINES,", "ON FIRE"),
     "IRAN WAR ENTERS 9TH MONTH; BRENT $90"),
    ("CLIMATE - ANTALYA", "leaf", "leaf",
     ("COP31 DRAFT", "DROPS FOSSIL", "PHASE-OUT"),
     "NEGOTIATORS STRIP CALL TO END FOSSIL FUELS"),
    ("US - WASHINGTON", "cyber", "mint",
     ("WHITE HOUSE", "FIRES CYBER", "CHIEF"),
     "AFTER WEEK OF TECH OUTAGES RATTLES US"),
]

ALSO = [
    "KENYA DISCHARGES LAST EBOLA PATIENT, 37 DAYS AFTER FIRST CASE",
    "ISRAEL CROSSES YELLOW LINE IN CENTRAL GAZA; 3 KILLED",
    "DENMARK RATIFIES US-GREENLAND SECURITY DEAL",
    "GOLD AT 14-MONTH LOW, $3,685; SILVER -4.8%",
]

# ------------------------------------------------------------------ page
def frame(bd, x, y, w, h):
    """A double-ruled ink border around a panel."""
    ink = PAL["ink"]
    for t in range(2):
        bd.hbar(x, y + t, w, ink)
        bd.hbar(x, y + h - 1 - t, w, ink)
        bd.vbar(x + t, y, h, ink)
        bd.vbar(x + w - 1 - t, y, h, ink)


def lead_story(bd, x, y, w, h):
    bd.rect(x, y, w, h, PAL["sky"])
    frame(bd, x, y, w, h)
    draw_scales(bd, x + 2, y + 2, 200, h - 4)
    tx = x + 222
    bd.draw_text(tx, y + 14, "JUSTICE - THE HAGUE", 2, PAL["red"])
    bd.draw_text(tx, y + 38, "COURT: MYANMAR", 5, PAL["ink"])
    bd.draw_text(tx, y + 80, "COMMITTED GENOCIDE", 5, PAL["red"])
    bd.draw_text(tx, y + 128, "FIRST SUCH RULING AGAINST A STATE", 2,
                 PAL["ink"])
    bd.draw_text(tx, y + 148, "ROHINGYA CASE AT THE WORLD COURT", 2,
                 PAL["ink"])


def story_panel(bd, x, y, w, h, story):
    kicker, pic, tint, head, summary = story
    bd.rect(x, y, w, h, PAL[tint])
    frame(bd, x, y, w, h)
    DRAW[pic](bd, x + 2, y + 2, w - 4, 88)
    bd.draw_text(x + 14, y + 98, kicker, 2, PAL["red"])
    yy = y + 120
    for line in head:
        bd.draw_text(x + 14, yy, line, 4, PAL["ink"])
        yy += 32
    for line in bd.wrap_text(summary, 24):
        bd.draw_text(x + 14, yy, line, 2, PAL["ink"])
        yy += 15


def build_page():
    bd = Board(W, H, PAL["paper"])
    ink, grey, amber = PAL["ink"], PAL["grey"], PAL["amber"]
    bd.draw_text(W // 2, 26, "THE WORLD IN ONE DAY", 3, grey, "center")
    bd.draw_text(W // 2, 56, "FRIDAY, 20 NOVEMBER 2026", 6, ink, "center")
    bd.hbar(28, 116, W - 56, ink, 4)
    bd.hbar(28, 124, W - 56, ink)

    lead_story(bd, 28, 134, W - 56, 176)

    cw, ch, gap = 312, 268, 15
    for n, story in enumerate(STORIES):
        px = 28 + (n % 3) * (cw + gap)
        py = 322 + (n // 3) * (ch + 8)
        story_panel(bd, px, py, cw, ch, story)

    ty = 878
    bd.rect(28, ty, W - 56, 112, ink)
    bd.draw_text(48, ty + 12, "ALSO TODAY", 3, amber)
    for k, item in enumerate(ALSO):
        ix = 48 + (k % 2) * 484
        iy = ty + 44 + (k // 2) * 34
        bd.rect(ix, iy + 3, 10, 10, amber)
        for j, line in enumerate(bd.wrap_text(item, 38)[:2]):
            bd.draw_text(ix + 18, iy + j * 15, line, 2, PAL["white"])

    bd.hbar(28, 1000, W - 56, ink)
    bd.draw_text(W // 2, 1008,
                 "REPORTED ON 20 NOVEMBER 2026 - ONETURN, ARGUS, SCMP, "
                 "DAWN, DUNYA NEWS",
                 2, grey, "center")
    return bd


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "entry.png"), "wb") as fh:
        fh.write(png_bytes(build_page()))


if __name__ == "__main__":
    main()
