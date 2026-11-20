# SPDX-License-Identifier: MIT
"""Build the news-image-20261120 front page: a 1024x1024 newspaper-style
infographic of Friday 20 November 2026 world news.

Pure Python standard library only. No PIL, no network, no external fonts
or images: the PNG encoder is hand-written (zlib + CRCs) and text is
rendered with a bitmap font defined below. Output is deterministic:
no timestamps, no randomness.
"""

import binascii
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- colours
PAPER = (247, 243, 233)     # warm newsprint
PANEL = (255, 255, 255)     # white panel
LEAD_BG = (233, 239, 246)   # pale blue-grey for the lead panel
INK = (22, 32, 48)          # near-black navy text
NAVY = (20, 38, 63)         # masthead
RED = (176, 30, 40)         # accent red
GOLD = (201, 162, 39)       # masthead rule / scales
BORDER = (178, 170, 154)    # panel borders
CAPTION = (64, 64, 64)      # caption grey
GREEN = (30, 123, 52)       # rising chart
BLUE = (36, 84, 160)        # water / cables
DARKGREY = (88, 88, 88)
LIGHTGREY = (210, 210, 210)
ORANGE = (232, 126, 20)     # blast
YELLOW = (245, 196, 40)     # stars / blast core

# ------------------------------------------------------------ bitmap font
# 5x7 pixel font, defined from scratch. Each glyph is 7 rows of 5 bits.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
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
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "•": ("00000", "00000", "01100", "01100", "01100", "00000", "00000"),
}


def normalise(text):
    """Upper-case ASCII only: fold curly quotes and dashes to plain ones."""
    return (
        text.upper()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u00d7", "X")
    )


def text_w(s, scale):
    """Pixel width of a string at a font scale (trailing space dropped)."""
    s = normalise(s)
    return len(s) * 6 * scale - scale if s else 0


def wrap(s, max_w, scale):
    """Greedy word wrap; returns lines that each fit max_w pixels."""
    words = normalise(s).split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self):
        self.px = bytearray(bytes(PAPER) * (W * H))

    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(W, x + w)
        y1 = min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * W + x0) * 3
            self.px[i:i + len(row)] = row

    def rect_outline(self, x, y, w, h, c, t=2):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if t == 1:
                self.set(x0, y0, c)
            else:
                self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def polyline(self, pts, c, t=1):
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], c, t)

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def fill_polygon(self, pts, c):
        ys = [p[1] for p in pts]
        ymin, ymax = min(ys), max(ys)
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa, xb = int(xs[i]), int(xs[i + 1])
                self.fill_rect(xa, y, xb - xa + 1, 1, c)

    def star(self, cx, cy, r_out, r_in, c, n=5, rot=-90.0):
        pts = []
        for i in range(2 * n):
            r = r_out if i % 2 == 0 else r_in
            a = math.radians(rot + i * 180.0 / n)
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        self.fill_polygon(pts, c)

    def text(self, s, x, y, scale, c, align="left"):
        s = normalise(s)
        w = text_w(s, scale)
        if align == "center":
            x -= w // 2
        elif align == "right":
            x -= w
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for gy in range(7):
                row = glyph[gy]
                for gx in range(5):
                    if row[gx] == "1":
                        self.fill_rect(x + gx * scale, y + gy * scale,
                                       scale, scale, c)
            x += 6 * scale
        return y + 7 * scale

    def text_block(self, lines, x, y, scale, c, gap):
        """Draw wrapped lines; returns the y just below the last line."""
        for line in lines:
            y = self.text(line, x, y, scale, c)
            y += gap
        return y - gap if lines else y


# --------------------------------------------------------------- pictograms
def draw_flags(cv, x, y, w, h):
    """Three flags on poles: US, China, Russia (left to right)."""
    fw, fh = 64, 40
    gap = 16
    total = 3 * fw + 2 * gap
    x0 = x + (w - total) // 2
    top = y + 18
    pole_bot = y + h - 22
    for i, kind in enumerate(("us", "cn", "ru")):
        fx = x0 + i * (fw + gap)
        # pole + finial
        cv.fill_rect(fx - 2, top - 6, 3, pole_bot - (top - 6), DARKGREY)
        cv.circle(fx, top - 8, 4, GOLD)
        if kind == "us":
            # red and white stripes
            for s in range(7):
                col = RED if s % 2 == 0 else PANEL
                cv.fill_rect(fx, top + s * 6, fw, 6 if s < 6 else 4, col)
            # blue canton with star dots
            cv.fill_rect(fx, top, 26, 22, NAVY)
            for sy in (top + 5, top + 12, top + 18):
                for sx in (fx + 6, fx + 14, fx + 21):
                    cv.fill_rect(sx, sy, 2, 2, PANEL)
        elif kind == "cn":
            cv.fill_rect(fx, top, fw, fh, RED)
            cv.star(fx + 13, top + 13, 9, 4, YELLOW)
            for sx, sy in ((30, 6), (38, 11), (38, 20), (30, 25)):
                cv.star(fx + sx, top + sy, 3, 1, YELLOW)
        else:
            cv.fill_rect(fx, top, fw, 13, PANEL)
            cv.fill_rect(fx, top + 13, fw, 14, BLUE)
            cv.fill_rect(fx, top + 27, fw, 13, RED)
    # gold base bar
    cv.fill_rect(x0 - 8, pole_bot, total + 16, 6, GOLD)


def draw_scales(cv, x, y, w, h):
    """Scales of justice, gold on white."""
    cx = x + w // 2
    top = y + 10
    bot = y + h - 10
    # base and pole
    cv.fill_rect(cx - 26, bot - 4, 52, 4, GOLD)
    cv.fill_rect(cx - 2, top + 14, 4, bot - top - 18, GOLD)
    cv.circle(cx, top + 6, 5, GOLD)
    # crossbar
    cv.fill_rect(cx - 52, top + 14, 104, 4, GOLD)
    for side in (-1, 1):
        px = cx + side * 52
        # hanging cords
        cv.line(px, top + 18, px - 16, top + 44, GOLD, 2)
        cv.line(px, top + 18, px + 16, top + 44, GOLD, 2)
        # pan: shallow triangle
        cv.fill_polygon([(px - 18, top + 44), (px + 18, top + 44),
                         (px, top + 58)], GOLD)


def draw_rising_chart(cv, x, y, w, h, colour=GREEN):
    """Ascending bars with a rising trend arrow."""
    ox, oy = x + 26, y + h - 16          # origin (bottom-left)
    cv.line(ox, y + 10, ox, oy, INK, 2)  # y axis
    cv.line(ox, oy, x + w - 12, oy, INK, 2)  # x axis
    heights = [16, 30, 46, 62]
    bw = 30
    step = (w - 26 - 12 - bw) // 3
    tops = []
    for i, hh in enumerate(heights):
        bx = ox + 12 + i * step
        cv.fill_rect(bx, oy - hh, bw, hh, colour)
        tops.append((bx + bw // 2, oy - hh))
    # trend line with arrowhead
    pts = [(tops[0][0] - 14, tops[0][1] + 8)] + tops
    cv.polyline(pts, INK, 2)
    ex, ey = tops[-1]
    cv.fill_polygon([(ex + 16, ey - 14), (ex + 2, ey - 12),
                     (ex + 10, ey - 2)], INK)


def draw_falling_chart(cv, x, y, w, h):
    """Descending red bars with a falling trend arrow."""
    ox, oy = x + 26, y + h - 16
    cv.line(ox, y + 10, ox, oy, INK, 2)
    cv.line(ox, oy, x + w - 12, oy, INK, 2)
    heights = [62, 46, 30, 16]
    bw = 30
    step = (w - 26 - 12 - bw) // 3
    tops = []
    for i, hh in enumerate(heights):
        bx = ox + 12 + i * step
        cv.fill_rect(bx, oy - hh, bw, hh, RED)
        tops.append((bx + bw // 2, oy - hh))
    pts = [(tops[0][0] - 14, tops[0][1] - 8)] + tops
    cv.polyline(pts, INK, 2)
    ex, ey = tops[-1]
    cv.fill_polygon([(ex + 16, ey + 12), (ex + 2, ey + 10),
                     (ex + 10, ey - 2)], INK)


def draw_tower(cv, x, y, w, h):
    """Tall skyscraper with a blast star and smoke at its top."""
    cx = x + w // 2 - 46
    base = y + h - 8
    tw, th = 46, h - 30
    # tower body, slightly stepped
    cv.fill_rect(cx, base - th, tw, th, NAVY)
    cv.fill_rect(cx - 5, base - th - 10, tw + 10, 10, NAVY)
    cv.line(cx + tw // 2, base - th - 26, cx + tw // 2, base - th - 10,
            NAVY, 2)
    # windows
    for row in range(5):
        for col in range(3):
            cv.fill_rect(cx + 7 + col * 13, base - th + 8 + row * 9,
                         6, 4, (190, 205, 225))
    # ground line
    cv.line(x + 8, base, x + w - 8, base, INK, 2)
    # blast starburst just right of the tower top
    bx, by = cx + tw + 26, base - th + 4
    cv.star(bx, by, 22, 9, ORANGE, n=8)
    cv.star(bx, by, 12, 5, YELLOW, n=8)
    # smoke puffs, kept inside the pictogram region
    cv.circle(bx - 24, by - 20, 9, LIGHTGREY)
    cv.circle(bx - 10, by - 26, 7, LIGHTGREY)
    cv.circle(bx + 10, by - 22, 6, DARKGREY)


def draw_bridge(cv, x, y, w, h):
    """A suspension bridge with a broken middle span and smoke."""
    deck_y = y + h // 2 + 6
    pylon_l = x + 18
    pylon_r = x + w - 26
    mid = (pylon_l + pylon_r) // 2
    # pylons
    cv.fill_rect(pylon_l, y + 14, 8, deck_y - y - 14, INK)
    cv.fill_rect(pylon_r, y + 14, 8, deck_y - y - 14, INK)
    # cables
    cv.line(pylon_l + 4, y + 14, mid - 12, deck_y, BLUE, 2)
    cv.line(pylon_r + 4, y + 14, mid + 12, deck_y, BLUE, 2)
    # deck, broken in the middle
    cv.fill_rect(x + 4, deck_y, mid - 12 - (x + 4), 6, INK)
    cv.fill_rect(mid + 12, deck_y, x + w - 4 - (mid + 12), 6, INK)
    # jagged broken edges
    cv.fill_polygon([(mid - 12, deck_y), (mid - 4, deck_y - 8),
                     (mid - 2, deck_y + 6)], INK)
    cv.fill_polygon([(mid + 12, deck_y), (mid + 4, deck_y - 8),
                     (mid + 2, deck_y + 6)], INK)
    # blast + smoke at the break
    cv.star(mid, deck_y - 6, 16, 7, ORANGE, n=8)
    cv.star(mid, deck_y - 6, 9, 4, YELLOW, n=8)
    cv.circle(mid - 16, deck_y - 30, 8, LIGHTGREY)
    cv.circle(mid + 10, deck_y - 36, 6, DARKGREY)
    # water below
    for i, wy in enumerate((deck_y + 18, deck_y + 28, deck_y + 38)):
        cv.line(x + 10 + (i % 2) * 14, wy, x + w - 10 - (i % 2) * 10, wy,
                BLUE, 2)


# ------------------------------------------------------------------ layout
def small_panel(cv, x, y, w, h, kicker, headline, caption, picture):
    """One grid panel: pictogram on top, kicker, headline, caption."""
    cv.fill_rect(x, y, w, h, PANEL)
    cv.rect_outline(x, y, w, h, BORDER, 2)
    picture(cv, x + 16, y + 12, w - 32, 78)
    cv.text(kicker, x + 16, y + 98, 2, RED)
    lines = wrap(headline, w - 32, 3)
    assert len(lines) <= 2, (headline, lines)
    cv.text_block(lines, x + 16, y + 120, 3, INK, 6)
    cap = wrap(caption, w - 32, 2)
    assert len(cap) <= 3, (caption, cap)
    cv.text_block(cap, x + 16, y + 180, 2, CAPTION, 5)


def wide_panel(cv, x, y, w, h, kicker, headline, caption, picture):
    """Wide panel: pictogram left, text right."""
    cv.fill_rect(x, y, w, h, PANEL)
    cv.rect_outline(x, y, w, h, BORDER, 2)
    picture(cv, x + 16, y + 20, 150, h - 40)
    tx = x + 182
    tw = w - 182 - 16
    cv.text(kicker, tx, y + 20, 2, RED)
    lines = wrap(headline, tw, 3)
    assert len(lines) <= 3, (headline, lines)
    end = cv.text_block(lines, tx, y + 44, 3, INK, 6)
    cap = wrap(caption, tw, 2)
    assert len(cap) <= 3, (caption, cap)
    cv.text_block(cap, tx, end + 16, 2, CAPTION, 5)


def build():
    cv = Canvas()

    # ---- masthead ------------------------------------------------------
    cv.fill_rect(0, 0, W, 150, NAVY)
    cv.text("TODAY IN THE WORLD", 512, 32, 6, PANEL, align="center")
    cv.text("FRIDAY, 20 NOVEMBER 2026", 512, 94, 4, PANEL, align="center")
    dw = text_w("FRIDAY, 20 NOVEMBER 2026", 4)
    cv.fill_rect(512 - dw // 2, 130, dw, 5, RED)
    cv.fill_rect(0, 150, W, 4, GOLD)

    # ---- lead panel: Shenzhen summit ------------------------------------
    lx, ly, lw, lh = 24, 170, 976, 216
    cv.fill_rect(lx, ly, lw, lh, LEAD_BG)
    cv.rect_outline(lx, ly, lw, lh, BORDER, 2)
    draw_flags(cv, lx + 16, ly + 20, 260, 176)
    tx = lx + 320
    cv.fill_rect(tx, ly + 16, 128, 26, RED)
    cv.text("TOP STORY", tx + 64, ly + 22, 2, PANEL, align="center")
    # explicit two-line break so neither line is a single word
    lead_head = ["TRUMP, XI AND PUTIN", "MEET IN SHENZHEN"]
    cv.text_block(lead_head, tx, ly + 58, 4, INK, 8)
    lead_cap = wrap(
        "FIRST-EVER THREE-WAY SUMMIT ISSUES JOINT FOUR-POINT "
        "PEACE DECLARATION", 640, 2)
    assert len(lead_cap) == 2, lead_cap
    cv.text_block(lead_cap, tx, ly + 140, 2, CAPTION, 6)

    # ---- row A: three panels -------------------------------------------
    small_panel(cv, 24, 402, 312, 252, "WORLD COURT",
                "MYANMAR GUILTY OF GENOCIDE",
                "WORLD COURT RULES 9-6 OVER ROHINGYA - FIRST SUCH RULING",
                draw_scales)
    small_panel(cv, 356, 402, 312, 252, "AI IPO",
                "ANTHROPIC LISTS ON NASDAQ",
                "CLAUDE MAKER LISTS AS ANT - PRICED $83, CLOSED NEAR "
                "$97, UP 17%",
                lambda c, x, y, w, h: draw_rising_chart(c, x, y, w, h))
    small_panel(cv, 688, 402, 312, 252, "MIDDLE EAST",
                "HOUTHI MISSILES HIT RIYADH",
                "MISSILES STRIKE FINANCIAL DISTRICT - PIF TOWER DAMAGED",
                draw_tower)

    # ---- row B: two wide panels -----------------------------------------
    wide_panel(cv, 24, 670, 478, 200, "UKRAINE WAR",
               "KERCH BRIDGE STRUCK AGAIN",
               "THIRD STRIKE IN FOUR DAYS - RAIL HALTED, KYIV HIT AGAIN",
               draw_bridge)
    wide_panel(cv, 522, 670, 478, 200, "MARKETS",
               "MARKETS FALL FOR FIFTH DAY",
               "S&P 500 DOWN ABOUT 2% - NIKKEI FALLS 4.8%, SOFTBANK "
               "DOWN OVER 16%",
               lambda c, x, y, w, h: draw_falling_chart(c, x, y, w, h))

    # ---- "also today" strip ---------------------------------------------
    sx, sy, sw, sh = 24, 886, 976, 104
    cv.fill_rect(sx, sy, sw, sh, PANEL)
    cv.rect_outline(sx, sy, sw, sh, BORDER, 2)
    cv.text("ALSO TODAY", sx + 16, sy + 12, 2, RED)
    items = [
        "IRAN WAR ENTERS NINTH MONTH - TANKER HIT BY MINE NEAR HORMUZ",
        "US SENATE REJECTS IRAN WAR-POWERS RESOLUTION 51-48",
        "KENYA DISCHARGES ITS LAST EBOLA PATIENT 37 DAYS AFTER ITS 1ST CASE",
    ]
    for i, item in enumerate(items):
        ix = sx + 16 + i * 325
        cv.fill_rect(ix, sy + 42, 10, 10, RED)
        lines = wrap(item, 282, 2)
        assert len(lines) <= 3, (item, lines)
        cv.text_block(lines, ix + 18, sy + 38, 2, INK, 5)

    # ---- footer ----------------------------------------------------------
    cv.fill_rect(24, 996, 976, 2, BORDER)
    cv.text("ALL STORIES AS REPORTED ON FRIDAY, 20 NOVEMBER 2026",
            512, 1002, 2, CAPTION, align="center")
    return cv


# -------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    for yy in range(H):
        raw.append(0)  # filter: None
        raw += cv.px[yy * W * 3:(yy + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "news.png")
    cv = build()
    size = write_png(out, cv)
    print("wrote %s (%d bytes, %dx%d)" % (out, size, W, H))


if __name__ == "__main__":
    main()
