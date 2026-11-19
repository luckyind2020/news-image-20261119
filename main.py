#!/usr/bin/env python3
"""The World Today - 19 November 2026, drawn fresh at run time.

A tiny broadsheet renderer: a hand-built 5x7 bitmap face, a small
canvas of rectangles and rules, and a pure-stdlib PNG writer.  Every
story below is real news from Thursday 19 November 2026, checked
against live reporting the morning it was written.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes: $MAKEFUN_OUTPUT_DIR/entry.png  (1024x1024, deterministic)
"""

import os
import struct
import zlib

PAGE_W = 1024
PAGE_H = 1024
MARGIN = 36

PAPER = (255, 255, 255)
INK = (18, 18, 18)
RED = (168, 32, 32)
GREY = (112, 112, 112)
PALE = (238, 238, 238)


# ---------------------------------------------------------------- font
# A 5-wide, 7-tall bitmap face, drawn from scratch for this page.
# Each glyph is seven rows of five marks; '#' is ink, '.' is paper.
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
}

GLYPHS.update({
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".###."),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".###."),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
    ":": (".....", ".....", ".##..", ".....", ".....", ".##..", "....."),
    ";": (".....", ".....", ".##..", ".....", ".....", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#..#", "#...#", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "*": (".....", "#...#", ".#.#.", ".###.", ".#.#.", "#...#", "....."),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "=": (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", "....."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
})


# ---------------------------------------------------------------- canvas
class Sheet:
    """A flat RGB canvas with a few newspaper tools on top."""

    def __init__(self, width, height, base):
        self.width = width
        self.height = height
        self.pixels = bytearray(base * width * height)

    def _set(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            at = (y * self.width + x) * 3
            self.pixels[at:at + 3] = bytes(colour)

    def block(self, x, y, w, h, colour):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self._set(xx, yy, colour)

    def frame(self, x, y, w, h, colour, thick=1):
        self.block(x, y, w, thick, colour)
        self.block(x, y + h - thick, w, thick, colour)
        self.block(x, y, thick, h, colour)
        self.block(x + w - thick, y, thick, h, colour)

    def hline(self, x, y, w, colour, thick=1):
        self.block(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.block(x, y, thick, h, colour)

    def disc(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self._set(xx, yy, colour)

    def glyph(self, ch, x, y, scale, colour):
        rows = GLYPHS.get(ch)
        if rows is None:
            rows = GLYPHS["?"]
        for r, row in enumerate(rows):
            for c, mark in enumerate(row):
                if mark == "#":
                    self.block(x + c * scale, y + r * scale,
                               scale, scale, colour)

    def text(self, x, y, line, scale, colour=INK):
        cx = x
        for ch in line:
            self.glyph(ch, cx, y, scale, colour)
            cx += 6 * scale
        return cx

    def text_width(self, line, scale):
        return len(line) * 6 * scale

    def wrap(self, words, width, scale):
        """Split a sentence into lines that fit width pixels."""
        lines = []
        cur = ""
        for word in words.split():
            trial = word if not cur else cur + " " + word
            if self.text_width(trial, scale) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, width, words, scale, leading, colour=INK):
        for line in self.wrap(words, width, scale):
            self.text(x, y, line, scale, colour)
            y += leading
        return y

    def headline(self, x, y, width, title, scale, leading=None):
        if leading is None:
            leading = 8 * scale + 2
        return self.para(x, y, width, title, scale, leading)


def _chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


def write_png(sheet, path):
    raw = bytearray()
    for yy in range(sheet.height):
        raw.append(0)
        start = yy * sheet.width * 3
        raw += sheet.pixels[start:start + sheet.width * 3]
    blob = (b"\x89PNG\r\n\x1a\n" +
            _chunk(b"IHDR", struct.pack(">IIBBBBB", sheet.width,
                                        sheet.height, 8, 2, 0, 0, 0)) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)


# ---------------------------------------------------------------- stories
# Real news of Thursday 19 November 2026, as reported that morning
# (AP / Reuters / BBC / NDTV / Financial Times / The Hindu / NASA).
LEAD = {
    "tag": "GAMING",
    "title": "GTA VI BEGINS GLOBAL ROLLOUT",
    "body": ("After a 13-year wait, Rockstar's Grand Theft Auto VI went "
             "on sale at midnight market by market, starting in New "
             "Zealand and rolling around the world. The return to Vice "
             "City, in the fictional state of Leonida, runs on "
             "PlayStation 5 and Xbox Series X and S. Pre-orders alone "
             "are put near 16 million copies, worth more than "
             "1.5 billion dollars, before a single American player "
             "had even unlocked it."),
}

COLUMNS = [
    {
        "tag": "WASHINGTON",
        "title": "JEFFRIES SET TO BE FIRST BLACK SPEAKER",
        "body": ("Democrats nominated Hakeem Jeffries to lead the US "
                 "House of Representatives. If elected, he would be the "
                 "first African-American Speaker in the chamber's "
                 "history, after a vote that ran late into Wednesday "
                 "night."),
    },
    {
        "tag": "SPACE",
        "title": "VOYAGER 1 REACHES ONE LIGHT-DAY",
        "body": ("Nearly 50 years after launch, NASA's Voyager 1 probe "
                 "has flown about one light-day from Earth, a record "
                 "for any human-made object. NASA was due to confirm "
                 "the milestone at a briefing on Thursday."),
    },
    {
        "tag": "BRUSSELS",
        "title": "EU PROPOSES 45BN EURO UKRAINE LOAN",
        "body": ("The European Commission put forward a 45 billion "
                 "euro loan for Ukraine, raised on the capital "
                 "markets. Kyiv would repay it only once Russia has "
                 "paid reparations, under the plan shown to EU "
                 "leaders this week."),
    },
    {
        "tag": "INDIA",
        "title": "CYCLONE AKVAN NEARS INDIAN COAST",
        "body": ("Cyclone Akvan was expected to cross the coast "
                 "between Machilipatnam and Puri, with railways on "
                 "alert and heavy rain forecast. Officials tracked "
                 "the storm through the night as it closed in."),
    },
]

BRIEFS = [
    ("HEALTH", "US loses measles-free status after 26 years as cases hit a record."),
    ("GAZA", "Israeli tanks cross the Yellow Line in a rare ground push into central Gaza."),
    ("FAITH", "Pew: Islam on track to become the world's largest religion by 2035."),
    ("TRADE", "Canada reworks China ties as Carney chases the right deal with the US."),
]


# ---------------------------------------------------------------- layout
def draw_skyline(sheet, x, y, w, h):
    """A dusk skyline for Vice City: sun, towers, lit windows."""
    sheet.block(x, y, w, h, (24, 28, 44))
    sheet.disc(x + w - 52, y + 34, 20, (244, 178, 74))
    towers = [(0, 96), (34, 128), (78, 84), (118, 140), (160, 102),
              (200, 132), (238, 78), (274, 118), (306, 96)]
    for bx, th in towers:
        sheet.block(x + bx, y + h - th, 30, th, INK)
    for wy in range(y + h - 120, y + h - 8, 14):
        for wx in range(x + 6, x + w - 10, 18):
            if (wx * 7 + wy * 13) % 5 < 2:
                sheet.block(wx, wy, 5, 6, (244, 196, 96))
    sheet.block(x, y + h - 6, w, 6, (64, 32, 48))


def build_page():
    page = Sheet(PAGE_W, PAGE_H, PAPER)
    left = MARGIN
    right = PAGE_W - MARGIN
    span = right - left

    # Masthead.
    name = "THE WORLD TODAY"
    page.text((PAGE_W - page.text_width(name, 8)) // 2, 30, name, 8)
    page.hline(left, 108, span, INK, 3)
    page.hline(left, 114, span, INK, 1)
    y = 126
    page.text(left, y, "THURSDAY, 19 NOVEMBER 2026", 2)
    tail = "WORLD EDITION - ONE IMAGE, THE WHOLE DAY"
    page.text(right - page.text_width(tail, 2), y, tail, 2, GREY)
    y = 158

    # Lead story.
    page.text(left, y, LEAD["tag"], 2, RED)
    y += 22
    y = page.headline(left, y, span, LEAD["title"], 4)
    y += 10
    pic_w = 360
    pic_h = 168
    pic_x = right - pic_w
    draw_skyline(page, pic_x, y, pic_w, pic_h)
    body_w = span - pic_w - 28
    after = page.para(left, y, body_w, LEAD["body"], 2, 17)
    cap = "Vice City at dusk: the fictional city at the heart of GTA VI."
    page.para(pic_x, y + pic_h + 8, pic_w, cap, 1, 10, GREY)
    y = max(after, y + pic_h + 34)
    page.hline(left, y, span, INK, 2)
    y += 18

    # Two columns, two stories each.
    col_w = (span - 28) // 2
    col_x = [left, left + col_w + 28]
    top = y
    ends = []
    for ci, story in enumerate(COLUMNS):
        cx = col_x[ci % 2]
        cy = top if ci < 2 else ends[ci - 2] + 16
        page.text(cx, cy, story["tag"], 2, RED)
        cy += 22
        cy = page.headline(cx, cy, col_w, story["title"], 3)
        cy += 6
        cy = page.para(cx, cy, col_w, story["body"], 2, 16)
        ends.append(cy)
    page.vline(left + col_w + 14, top, max(ends) - top, GREY)
    y = max(ends) + 6
    page.hline(left, y, span, INK, 2)
    y += 16

    # In brief: four short items in a row.
    page.text(left, y, "IN BRIEF", 2, RED)
    y += 24
    bw = (span - 3 * 20) // 4
    bottom = y
    for bi, (tag, line) in enumerate(BRIEFS):
        bx = left + bi * (bw + 20)
        page.text(bx, y, tag, 2)
        end = page.para(bx, y + 20, bw, line, 2, 15, GREY)
        bottom = max(bottom, end)
        if bi < 3:
            page.vline(bx + bw + 10, y, end - y, PALE)
    y = bottom + 20
    page.hline(left, y, span, INK, 1)
    y += 14
    foot = ("Sources: AP, Reuters, BBC, NDTV, Financial Times, The Hindu, "
            "NASA. Compiled on 19 November 2026.")
    page.text(left, y, foot, 1, GREY)
    return page


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    page = build_page()
    target = os.path.join(out_dir, "entry.png")
    write_png(page, target)
    print("wrote", target, os.path.getsize(target), "bytes")


if __name__ == "__main__":
    main()
