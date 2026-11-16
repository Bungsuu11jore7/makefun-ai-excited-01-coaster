#!/usr/bin/env python3
"""Survived The Drop -- souvenir roller-coaster ticket, re-authored.

A 1024x1024 picture drawn with nothing but the Python standard library:
a bytearray RGB sheet, a 5x7 bitmap alphabet, and a hand-rolled PNG
writer. Every mark comes from fixed numbers, so two runs produce the
same bytes. No files are read, no network, no third-party code.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
NAVY = (26, 16, 64)
DEEP = (46, 10, 72)
PLUM = (150, 28, 108)
EMBER = (232, 84, 42)
ORANGE = (244, 120, 40)
GOLD = (255, 190, 60)
SUN = (255, 214, 90)
CREAM = (255, 243, 212)
PAPER = (255, 250, 232)
RED = (206, 28, 44)
DARKRED = (140, 16, 30)
BLUE = (28, 80, 168)
TEAL = (14, 130, 120)
SKIN = (255, 214, 170)
YELLOW = (255, 226, 40)
WHITE = (255, 255, 255)
PEACH = (255, 198, 168)


def mix(a, b, t):
    """Linear blend of two RGB triples, t in [0, 1]."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ------------------------------------------------------------------- sheet
class Sheet:
    """A flat RGB canvas with a handful of drawing verbs."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def blot(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def bar(self, x, y, w, h, c):
        """Solid axis-aligned rectangle, clipped to the sheet."""
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def disc(self, cx, cy, r, c):
        """Filled circle via horizontal scanlines."""
        if r < 0:
            return
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            dx = int(math.isqrt(max(0, r * r - dy * dy)))
            self.bar(cx - dx, yy, dx * 2 + 1, 1, c)

    def ring(self, cx, cy, r, c, th=2):
        """Circle outline: walk the circumference, stamping small discs."""
        steps = max(48, int(6.28318 * r))
        dot = max(1, th // 2)
        for k in range(steps):
            a = 6.28318 * k / steps
            self.disc(cx + int(r * math.cos(a)), cy + int(r * math.sin(a)),
                      dot, c)

    def stroke(self, x0, y0, x1, y1, c, th=1):
        """Bresenham line; thickness comes from stamping discs."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        rad = max(0, th // 2)
        while True:
            self.disc(x, y, rad, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def tri(self, ax, ay, bx, by, cx, cy, c):
        """Filled triangle, barycentric edge test over its bounding box."""
        x0 = max(0, min(ax, bx, cx))
        x1 = min(self.w - 1, max(ax, bx, cx))
        y0 = max(0, min(ay, by, cy))
        y1 = min(self.h - 1, max(ay, by, cy))
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if d == 0:
            return
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                w0 = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / d
                w1 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / d
                w2 = 1.0 - w0 - w1
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    self.blot(xx, yy, c)

    def poly(self, pts, c):
        """Filled convex polygon, fanned into triangles."""
        for k in range(1, len(pts) - 1):
            self.tri(pts[0][0], pts[0][1], pts[k][0], pts[k][1],
                     pts[k + 1][0], pts[k + 1][1], c)

    def frame(self, x, y, w, h, c, th=3):
        """Rectangle outline built from four bars."""
        self.bar(x, y, w, th, c)
        self.bar(x, y + h - th, w, th, c)
        self.bar(x, y, th, h, c)
        self.bar(x + w - th, y, th, h, c)


# ------------------------------------------------------------- bitmap font
# Each glyph is 7 rows of 5 bits, "1" = ink. Authored by hand here.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00010", "00100", "00100", "00100"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "*": ("00000", "01010", "00100", "11111", "00100", "01010", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
}


def text_w(s, scale):
    """Pixel width of a string at a given scale (no trailing gap)."""
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def draw_text(sh, x, y, s, scale, color, align="left"):
    """Draw a string; align left / center / right around x."""
    if align == "center":
        x -= text_w(s, scale) // 2
    elif align == "right":
        x -= text_w(s, scale)
    cx = x
    for ch in s:
        rows = GLYPHS.get(ch, GLYPHS[" "])
        for ry, bits in enumerate(rows):
            for rx, bit in enumerate(bits):
                if bit == "1":
                    sh.bar(cx + rx * scale, y + ry * scale,
                           scale, scale, color)
        cx += 6 * scale


# --------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def save_png(sh, path):
    raw = bytearray()
    stride = sh.w * 3
    for y in range(sh.h):
        raw.append(0)  # filter: none
        raw += sh.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", sh.w, sh.h, 8, 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


# ---- scene painters follow in the second half of this file ----

# ------------------------------------------------------------ scene: sky
def paint_sky(sh):
    stops = [(0, DEEP), (330, PLUM), (660, EMBER), (1024, (238, 110, 36))]
    for y in range(H):
        for k in range(len(stops) - 1):
            y0, c0 = stops[k]
            y1, c1 = stops[k + 1]
            if y0 <= y < y1:
                sh.bar(0, y, W, 1, mix(c0, c1, (y - y0) / (y1 - y0)))
                break
        else:
            sh.bar(0, y, W, 1, stops[-1][1])


def paint_sun(sh):
    cx, cy = 800, 150
    for k in range(12):
        a = math.radians(k * 30 + 15)
        r0, r1 = 122, 178 if k % 2 == 0 else 160
        sh.stroke(cx + int(r0 * math.cos(a)), cy + int(r0 * math.sin(a)),
                  cx + int(r1 * math.cos(a)), cy + int(r1 * math.sin(a)),
                  GOLD, 7)
    sh.ring(cx, cy, 110, GOLD, 12)
    sh.disc(cx, cy, 96, SUN)
    sh.disc(cx, cy, 70, (255, 230, 140))


def paint_cloud(sh, cx, cy, s):
    for dx, dy, r in ((-34, 6, 22), (0, -6, 28), (34, 6, 22), (0, 10, 24)):
        sh.disc(cx + dx * s // 10, cy + dy * s // 10, r * s // 10, PEACH)


def paint_plus(sh, x, y, arm, color):
    sh.stroke(x - arm, y, x + arm, y, color, 4)
    sh.stroke(x, y - arm, x, y + arm, color, 4)


# ---------------------------------------------------------- scene: track
LOOP_C = (400, 360)
LOOP_R = 200


def paint_rail(sh, x0, y0, x1, y1):
    """Two parallel rails with cross ties between two points."""
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    for sgn in (-8, 8):
        sh.stroke(int(x0 + nx * sgn), int(y0 + ny * sgn),
                  int(x1 + nx * sgn), int(y1 + ny * sgn), NAVY, 6)
    step = 0
    while step < ln:
        px, py = x0 + ux * step, y0 + uy * step
        sh.stroke(int(px - nx * 9), int(py - ny * 9),
                  int(px + nx * 9), int(py + ny * 9), NAVY, 4)
        step += 26


def paint_track(sh):
    sh.ring(LOOP_C[0], LOOP_C[1], LOOP_R, NAVY, 7)
    sh.ring(LOOP_C[0], LOOP_C[1], LOOP_R - 17, NAVY, 5)
    sh.ring(LOOP_C[0], LOOP_C[1], LOOP_R - 9, CREAM, 2)
    paint_rail(sh, 40, 620, 212, 372)      # approach, up to the loop
    paint_rail(sh, 541, 219, 968, 642)     # the drop, down to the right
    sh.bar(300, 470, 12, 198, NAVY)       # supports
    sh.bar(520, 470, 12, 198, NAVY)
    sh.bar(300, 556, 232, 10, NAVY)


# ---------------------------------------------------------- scene: riders
def paint_loop_car(sh):
    """One car upside-down at the very top of the loop, riders hanging."""
    sh.bar(340, 176, 120, 32, RED)
    sh.frame(340, 176, 120, 32, NAVY, 3)
    sh.bar(352, 184, 40, 14, WHITE)
    sh.bar(408, 184, 40, 14, WHITE)
    sh.disc(362, 172, 8, NAVY)
    sh.disc(438, 172, 8, NAVY)
    for hx in (375, 425):
        sh.bar(hx - 9, 208, 18, 16, NAVY)          # hanging torso
        sh.disc(hx, 236, 11, SKIN)                 # head, pointing down
        sh.stroke(hx, 244, hx - 17, 270, NAVY, 5)  # arms flailing down
        sh.stroke(hx, 244, hx + 17, 270, NAVY, 5)


def paint_burst(sh, cx, cy):
    for k in range(8):
        a = math.radians(k * 45)
        ln = 48 if k % 2 == 0 else 30
        sh.stroke(cx, cy, cx + int(ln * math.cos(a)),
                  cy + int(ln * math.sin(a)), YELLOW, 6)
    sh.disc(cx, cy, 10, YELLOW)


# Drop direction (unit) and the "up" normal for the 45-degree descent.
DROP_D = (0.7105, 0.7038)
DROP_N = (0.7038, -0.7105)
DROP_S = (541, 219)
DROP_E = (968, 642)


def _along(cx, cy, a, b):
    """Point a units along the drop, b units up off the track."""
    return (int(cx + a * DROP_D[0] + b * DROP_N[0]),
            int(cy + a * DROP_D[1] + b * DROP_N[1]))


def paint_tilted_car(sh, cx, cy, color):
    """One train car slanted along the drop, riders with arms thrown up."""
    corners = [_along(cx, cy, a, b)
               for a, b in ((-52, -17), (52, -17), (52, 17), (-52, 17))]
    sh.poly(corners, color)
    win = [_along(cx, cy, a, b)
           for a, b in ((-38, 15), (38, 15), (38, 4), (-38, 4))]
    sh.poly(win, WHITE)
    for k in range(4):
        p, q = corners[k], corners[(k + 1) % 4]
        sh.stroke(p[0], p[1], q[0], q[1], NAVY, 3)
    for sgn in (-34, 34):
        wx, wy = _along(cx, cy, sgn, -19)
        sh.disc(wx, wy, 7, NAVY)
    for a in (-26, 26):
        hx, hy = _along(cx, cy, a, 30)
        tx, ty = _along(cx, cy, a, 8)
        sh.stroke(hx, hy, tx, ty, NAVY, 9)          # torso
        sh.disc(hx, hy, 11, SKIN)                   # head
        ax, ay = _along(cx, cy, a - 15, 54)
        bx, by = _along(cx, cy, a + 15, 54)
        sh.stroke(hx, hy, ax, ay, NAVY, 5)          # arms thrown up
        sh.stroke(hx, hy, bx, by, NAVY, 5)


def paint_train(sh):
    paint_tilted_car(sh, 669, 346, RED)
    paint_tilted_car(sh, 763, 439, YELLOW)
    paint_tilted_car(sh, 857, 532, RED)


def paint_speed(sh):
    def at(t, off):
        return (int(DROP_S[0] + t * (DROP_E[0] - DROP_S[0]) + off * DROP_N[0]),
                int(DROP_S[1] + t * (DROP_E[1] - DROP_S[1]) + off * DROP_N[1]))
    for t0, t1, off, col, th in (
            (0.16, 0.30, 68, WHITE, 5), (0.40, 0.52, 68, YELLOW, 4),
            (0.60, 0.74, 68, WHITE, 5), (0.80, 0.93, 68, YELLOW, 4),
            (0.24, 0.36, -52, WHITE, 4), (0.66, 0.78, -52, YELLOW, 4)):
        ax, ay = at(t0, off)
        bx, by = at(t1, off)
        sh.stroke(ax, ay, bx, by, col, th)


def paint_bubble(sh):
    for cx, cy, r in ((150, 108, 64), (100, 118, 42), (200, 118, 42),
                      (150, 66, 44), (110, 80, 36), (190, 80, 36)):
        sh.disc(cx, cy, r, WHITE)
    sh.ring(150, 108, 66, RED, 5)
    sh.tri(185, 158, 232, 208, 158, 166, WHITE)
    sh.stroke(185, 158, 232, 208, RED, 4)
    sh.stroke(232, 208, 158, 166, RED, 4)
    draw_text(sh, 152, 94, "WOW!", 5, RED, align="center")


# ---------------------------------------------------------- scene: ticket
def paint_stub(sh):
    sh.bar(0, 968, W, 56, ORANGE)                  # ground strip
    sh.bar(36, 668, 952, 300, NAVY)                # outer edge
    sh.bar(48, 680, 928, 276, PAPER)               # cream paper
    sh.frame(56, 688, 912, 260, RED, 4)
    for y in range(692, 944, 16):                   # perforation dashes
        sh.bar(210, y, 4, 9, RED)
    draw_text(sh, 130, 716, "ADMIT", 3, RED, align="center")
    draw_text(sh, 130, 752, "ONE", 3, RED, align="center")
    draw_text(sh, 130, 824, "NO. 0007", 2, NAVY, align="center")
    draw_text(sh, 130, 872, "ONE RIDE", 2, NAVY, align="center")
    draw_text(sh, 130, 900, "ONLY", 2, NAVY, align="center")
    draw_text(sh, 604, 708, "I SURVIVED", 6, DARKRED, align="center")
    draw_text(sh, 600, 704, "I SURVIVED", 6, RED, align="center")
    draw_text(sh, 604, 766, "THE DROP", 8, DARKRED, align="center")
    draw_text(sh, 600, 762, "THE DROP", 8, RED, align="center")
    draw_text(sh, 600, 836, "SCREAMED THE WHOLE WAY DOWN", 2, BLUE,
              align="center")
    draw_text(sh, 600, 862, "BEST 90 SECONDS OF MY LIFE", 2, BLUE,
              align="center")
    for bx, label, value in ((250, "HEIGHT", "91 M"),
                             (500, "SPEED", "128 KM/H"),
                             (750, "DROP", "80 DEG")):
        sh.bar(bx, 890, 200, 56, WHITE)
        sh.frame(bx, 890, 200, 56, TEAL, 3)
        draw_text(sh, bx + 100, 896, label, 2, TEAL, align="center")
        draw_text(sh, bx + 100, 918, value, 3, NAVY, align="center")


def paint_stamp(sh):
    cx, cy = 878, 742
    sh.ring(cx, cy, 82, RED, 5)
    sh.ring(cx, cy, 70, RED, 2)
    draw_text(sh, cx, 700, "I", 2, RED, align="center")
    draw_text(sh, cx, 726, "SURVIVED", 2, RED, align="center")
    draw_text(sh, cx, 752, "THE DROP", 2, RED, align="center")
    draw_text(sh, cx, 778, "***", 2, RED, align="center")


# ------------------------------------------------------------------ render
def render():
    sh = Sheet(W, H)
    paint_sky(sh)
    paint_sun(sh)
    for cx, cy, s in ((180, 120, 10), (560, 92, 9), (880, 308, 11),
                      (120, 255, 8)):
        paint_cloud(sh, cx, cy, s)
    for x, y in ((300, 64), (470, 150), (660, 60), (950, 230), (60, 330)):
        paint_plus(sh, x, y, 12, GOLD)
    paint_track(sh)
    paint_loop_car(sh)
    paint_burst(sh, 541, 219)
    paint_train(sh)
    paint_speed(sh)
    paint_bubble(sh)
    paint_stub(sh)
    paint_stamp(sh)
    return sh


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = save_png(render(), path)
    print("wrote %s %d bytes" % (path, size))


if __name__ == "__main__":
    main()
