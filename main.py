#!/usr/bin/env python3
"""ai-excited-01 - "Survived The Drop"

A pure-stdlib Python renderer (no PIL, no network, no fonts on disk) that
paints one souvenir roller-coaster ticket: a giant loop against a burning
sunset sky, a coaster train screaming down the drop, and a cream ticket
stub stamped I SURVIVED THE DROP, with the ride stats printed on it.

Writes a 1024x1024 PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).
Fully deterministic: every mark is placed from fixed numbers, so two runs
write byte-identical files.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# --- palette: sunset sky, hot ticket -------------------------------------
SKY_TOP = (38, 16, 92)
SKY_MID = (150, 32, 110)
SKY_LOW = (255, 94, 44)
SUN_CORE = (255, 214, 90)
SUN_HALO = (255, 158, 64)
RAY = (255, 190, 110)
CLOUD = (255, 205, 180)
TRACK = (28, 20, 64)
TRACK_LITE = (255, 255, 255)
CAR_RED = (232, 30, 60)
CAR_YEL = (255, 205, 30)
TICKET = (255, 248, 226)
TICKET_SHADE = (238, 222, 182)
TICKET_EDGE = (178, 24, 38)
INK = (26, 18, 58)
RED = (208, 24, 44)
BLUE = (24, 74, 178)
TEAL = (10, 148, 138)
WHITE = (255, 255, 255)
BLACK = (12, 10, 24)
YELLOW = (255, 214, 40)


class Board:
    """RGB pixel board backed by one bytearray; everything clips."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def dot(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = (y * self.w + x) * 3
            self.px[o:o + 3] = bytes(color)

    def mix(self, x, y, color, alpha):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = (y * self.w + x) * 3
            for i in range(3):
                self.px[o + i] = round(
                    self.px[o + i] + (color[i] - self.px[o + i]) * alpha)

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            o = (yy * self.w + x0) * 3
            self.px[o:o + len(row)] = row

    def bar(self, x0, y0, x1, y1, color, thick):
        """Thick straight segment between two points."""
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        r = thick // 2
        for i in range(steps + 1):
            t = i / steps
            cx = round(x0 + dx * t)
            cy = round(y0 + dy * t)
            self.rect(cx - r, cy - r, thick, thick, color)

    def ring(self, cx, cy, r, color, thick=4):
        for deg in range(720):
            a = math.radians(deg * 0.5)
            for rr in range(r - thick // 2, r + thick // 2 + 1):
                self.dot(int(cx + rr * math.cos(a)),
                         int(cy + rr * math.sin(a)), color)

    def disc(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            yy = cy + dy
            if yy < 0 or yy >= self.h:
                continue
            half = math.isqrt(max(0, r * r - dy * dy))
            self.rect(cx - half, yy, 2 * half + 1, 1, color)

    def tri(self, x0, y0, x1, y1, x2, y2, color):
        """Filled triangle, scanline fill."""
        pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        for y in range(ay, cy + 1):
            def edge(px, py, qx, qy):
                if qy == py:
                    return px
                return px + (qx - px) * (y - py) / (qy - py)
            xs = [edge(ax, ay, cx, cy)]
            if y < by:
                xs.append(edge(ax, ay, bx, by))
            else:
                xs.append(edge(bx, by, cx, cy))
            lo, hi = int(min(xs)), int(max(xs))
            self.rect(lo, y, hi - lo + 1, 1, color)

# --- 5x7 block font, drawn fresh for this ticket ('#' = ink) -------------
GLYPHS = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    'J': ("00111", "00001", "00001", "00001", "00001", "10001", "01110"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "00100", "00100", "00100"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "00000", "01100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    '/': ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '*': ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
}


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def put_text(bd, s, x, y, scale, color):
    """Left-aligned text; x,y is the top-left of the first glyph."""
    for ch in s:
        g = GLYPHS.get(ch)
        if g:
            for r, line in enumerate(g):
                for c, bit in enumerate(line):
                    if bit == '1':
                        bd.rect(x + c * scale, y + r * scale,
                                scale, scale, color)
        x += 6 * scale


def put_text_c(bd, s, cx, y, scale, color):
    put_text(bd, s, cx - text_w(s, scale) // 2, y, scale, color)


def put_text_shadow(bd, s, cx, y, scale, color, sh, dx=3, dy=3):
    put_text_c(bd, s, cx + dx, y + dy, scale, sh)
    put_text_c(bd, s, cx, y, scale, color)


def png_bytes(rgb, w, h):
    raw = b''.join(b'\x00' + bytes(rgb[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

# --- sky ------------------------------------------------------------------
def paint_sky(bd):
    for y in range(H):
        t = y / (H - 1)
        if t < 0.45:
            f = t / 0.45
            col = tuple(round(SKY_TOP[i] + (SKY_MID[i] - SKY_TOP[i]) * f)
                        for i in range(3))
        else:
            f = (t - 0.45) / 0.55
            col = tuple(round(SKY_MID[i] + (SKY_LOW[i] - SKY_MID[i]) * f)
                        for i in range(3))
        o = y * W * 3
        bd.px[o:o + W * 3] = bytes(col) * W
    # sunburst rays: short, only around the sun, never crossing the loop
    sx, sy = 830, 118
    for k in range(16):
        ang = math.radians(k * 22.5)
        ex = sx + int(215 * math.cos(ang))
        ey = sy + int(215 * math.sin(ang))
        bx = sx + int(118 * math.cos(ang))
        by = sy + int(118 * math.sin(ang))
        bd.bar(bx, by, ex, ey, RAY, 12 if k % 2 == 0 else 6)
    # sun: halo then blazing core
    bd.disc(sx, sy, 96, SUN_HALO)
    bd.disc(sx, sy, 68, SUN_CORE)
    bd.ring(sx, sy, 80, WHITE, 5)
    # soft clouds, low and fast
    for cx, cy, s in ((150, 120, 46), (330, 92, 34), (120, 250, 30),
                      (900, 300, 36), (600, 80, 26)):
        bd.disc(cx, cy, s, CLOUD)
        bd.disc(cx + s, cy + 8, int(s * 0.7), CLOUD)
        bd.disc(cx - s, cy + 10, int(s * 0.65), CLOUD)


def speed_lines(bd):
    """Short diagonal streaks parallel to the drop, clustered by the train."""
    streaks = ((600, 250, 90), (560, 330, 70), (700, 330, 110),
               (640, 430, 80), (800, 420, 100), (760, 520, 70),
               (360, 300, 70), (470, 250, 60))
    for x, y, ln in streaks:
        bd.bar(x, y, x + ln, y + ln, WHITE, 6)
        bd.bar(x + 14, y + 26, x + ln - 10, y + ln + 16, YELLOW, 4)


# --- coaster: lift hill, giant loop, screaming drop ------------------------
def rail(bd, x0, y0, x1, y1):
    """One stretch of track: two parallel dark rails, 16 apart."""
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    ox, oy = round(-dy / ln * 8), round(dx / ln * 8)
    bd.bar(x0 + ox, y0 + oy, x1 + ox, y1 + oy, TRACK, 9)
    bd.bar(x0 - ox, y0 - oy, x1 - ox, y1 - oy, TRACK, 9)
    # cross-ties between the rails
    steps = int(ln // 34)
    for i in range(1, steps):
        t = i / steps
        cx = int(x0 + dx * t)
        cy = int(y0 + dy * t)
        bd.bar(cx + ox, cy + oy, cx - ox, cy - oy, TRACK, 5)


def paint_track(bd):
    # lift hill: bottom-left, rising to the loop's lower-left side
    rail(bd, 24, 648, 302, 432)
    # the loop: two concentric rails, bold and dark
    bd.ring(430, 340, 172, TRACK, 13)
    bd.ring(430, 340, 150, TRACK, 10)
    bd.ring(430, 340, 172, TRACK_LITE, 3)
    # support pillars under the loop, down to the ticket
    bd.bar(344, 478, 344, 648, TRACK, 12)
    bd.bar(516, 500, 516, 648, TRACK, 12)
    # the drop: out of the loop's top-right, plunging to bottom-right
    rail(bd, 552, 218, 986, 648)


def paint_train(bd):
    """Three big cars diving down the drop, riders' arms thrown up."""
    cars = ((648, 306), (742, 402), (836, 498))
    for i, (cx, cy) in enumerate(cars):
        col = CAR_RED if i % 2 == 0 else CAR_YEL
        bd.rect(cx - 42, cy - 18, 84, 38, col)
        bd.rect(cx - 42, cy - 18, 84, 6, BLACK)
        bd.rect(cx - 42, cy + 14, 84, 6, BLACK)
        bd.rect(cx - 6, cy - 18, 6, 38, BLACK)
        bd.rect(cx + 24, cy - 18, 6, 38, BLACK)
        # wheels on the rails
        bd.disc(cx - 26, cy + 24, 8, BLACK)
        bd.disc(cx + 26, cy + 24, 8, BLACK)
        # rider: big head, both arms up, screaming
        bd.disc(cx, cy - 30, 12, (255, 214, 170))
        bd.disc(cx, cy - 26, 4, BLACK)
        bd.bar(cx - 10, cy - 22, cx - 28, cy - 52, INK, 6)
        bd.bar(cx + 10, cy - 22, cx + 28, cy - 52, INK, 6)
        bd.disc(cx - 29, cy - 54, 5, (255, 214, 170))
        bd.disc(cx + 29, cy - 54, 5, (255, 214, 170))
    # yellow burst behind the front car, where the drop begins
    for k in range(5):
        ang = math.radians(200 + k * 18)
        bd.bar(600, 260, 600 + int(64 * math.cos(ang)),
               260 + int(64 * math.sin(ang)), YELLOW, 6)


def paint_bubble(bd):
    """Shout bubble bursting out of the loop: WOW!"""
    bx, by = 150, 120
    bd.disc(bx, by, 78, WHITE)
    bd.disc(bx + 62, by - 18, 52, WHITE)
    bd.disc(bx - 58, by + 22, 44, WHITE)
    bd.ring(bx, by, 78, RED, 6)
    bd.tri(bx + 30, by + 62, bx + 78, by + 118, bx + 66, by + 52, WHITE)
    bd.bar(bx + 30, by + 62, bx + 78, by + 118, RED, 5)
    bd.bar(bx + 66, by + 52, bx + 78, by + 118, RED, 5)
    put_text_c(bd, "WOW!", bx + 6, by - 30, 6, RED)

# --- the ticket stub --------------------------------------------------------
def paint_ticket(bd):
    x0, y0, x1, y1 = 48, 648, 976, 972
    bd.rect(x0 - 8, y0 - 6, x1 - x0 + 16, y1 - y0 + 12, (20, 8, 40))
    bd.rect(x0, y0, x1 - x0, y1 - y0, TICKET)
    # warm shade at the bottom of the stub
    for y in range(y1 - 90, y1):
        t = (y - (y1 - 90)) / 90.0
        col = tuple(round(TICKET[i] + (TICKET_SHADE[i] - TICKET[i]) * t)
                    for i in range(3))
        o = y * W * 3
        bd.px[o + x0 * 3:o + x1 * 3] = bytes(col) * (x1 - x0)
    # double red border
    bd.rect(x0, y0, x1 - x0, 6, TICKET_EDGE)
    bd.rect(x0, y1 - 6, x1 - x0, 6, TICKET_EDGE)
    bd.rect(x0, y0, 6, y1 - y0, TICKET_EDGE)
    bd.rect(x1 - 6, y0, 6, y1 - y0, TICKET_EDGE)
    bd.rect(x0 + 14, y0 + 14, x1 - x0 - 28, 3, RED)
    # perforation: dashed line splitting off the stub on the left
    for y in range(y0 + 18, y1 - 14, 18):
        bd.rect(196, y, 4, 10, TICKET_EDGE)
    put_text(bd, "ADMIT", 76, 700, 2, RED)
    put_text(bd, "ONE", 92, 730, 2, RED)
    put_text(bd, "NO. 0007", 76, 790, 2, INK)
    put_text(bd, "ONE RIDE", 76, 880, 2, INK)
    put_text(bd, "ONLY", 92, 910, 2, INK)
    # headline, big and red, with a hard shadow
    put_text_shadow(bd, "I SURVIVED", 600, 668, 6, RED, INK)
    put_text_shadow(bd, "THE DROP", 600, 716, 8, RED, INK)
    # the rider's own words, in blue ink
    put_text_c(bd, "SCREAMED THE WHOLE WAY DOWN", 600, 800, 2, BLUE)
    put_text_c(bd, "BEST 90 SECONDS OF MY LIFE", 600, 828, 2, BLUE)
    # ride stats: three boxed facts
    boxes = (("HEIGHT", "91 M"), ("SPEED", "128 KM/H"), ("DROP", "80 DEG"))
    for i, (label, val) in enumerate(boxes):
        bx = 230 + i * 248
        bd.rect(bx, 862, 228, 84, WHITE)
        bd.rect(bx, 862, 228, 4, TEAL)
        bd.rect(bx, 862, 4, 84, TEAL)
        bd.rect(bx + 224, 862, 4, 84, TEAL)
        bd.rect(bx, 942, 228, 4, TEAL)
        put_text_c(bd, label, bx + 114, 872, 2, TEAL)
        put_text_c(bd, val, bx + 114, 900, 3, INK)


def paint_stamp(bd):
    """Big red SURVIVED stamp crashing over the ticket's top-right corner."""
    cx, cy = 880, 692
    bd.ring(cx, cy, 80, RED, 7)
    bd.ring(cx, cy, 66, RED, 3)
    put_text_c(bd, "I", cx, cy - 36, 2, RED)
    put_text_c(bd, "SURVIVED", cx, cy - 12, 2, RED)
    put_text_c(bd, "THE DROP", cx, cy + 12, 2, RED)
    put_text_c(bd, "* * *", cx, cy + 36, 2, RED)


def paint_loop_car(bd):
    """The money shot: a car upside-down at the very top of the loop,
    riders hanging, hair and arms dangling toward the ground."""
    cx = 430
    # car body hanging below the top rail
    bd.rect(cx - 42, 196, 84, 36, CAR_RED)
    bd.rect(cx - 42, 196, 84, 6, BLACK)
    bd.rect(cx - 42, 226, 84, 6, BLACK)
    bd.rect(cx - 6, 196, 6, 36, BLACK)
    bd.rect(cx + 24, 196, 6, 36, BLACK)
    # wheels pressed against the rail above the car
    bd.disc(cx - 26, 192, 8, BLACK)
    bd.disc(cx + 26, 192, 8, BLACK)
    # two riders hanging upside-down: heads below the car, arms dangling
    for rx in (cx - 20, cx + 20):
        bd.disc(rx, 256, 12, (255, 214, 170))
        bd.disc(rx, 260, 4, BLACK)
        bd.bar(rx - 8, 236, rx - 20, 268, INK, 6)
        bd.bar(rx + 8, 236, rx + 20, 268, INK, 6)
        bd.disc(rx - 21, 270, 5, (255, 214, 170))
        bd.disc(rx + 21, 270, 5, (255, 214, 170))


def sparkles(bd):
    """Tiny yellow starbursts in the empty sky, upper-left."""
    for sx, sy, s in ((300, 92, 12), (420, 78, 9), (252, 168, 9),
                      (690, 210, 9)):
        bd.bar(sx - s, sy, sx + s, sy, YELLOW, 4)
        bd.bar(sx, sy - s, sx, sy + s, YELLOW, 4)


def main():
    bd = Board(W, H)
    paint_sky(bd)
    speed_lines(bd)
    sparkles(bd)
    paint_track(bd)
    paint_train(bd)
    paint_loop_car(bd)
    paint_bubble(bd)
    paint_ticket(bd)
    paint_stamp(bd)
    data = png_bytes(bd.px, W, H)
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, 'entry.png')
    with open(out, 'wb') as f:
        f.write(data)
    print("wrote", out, len(data), "bytes")


if __name__ == '__main__':
    main()
